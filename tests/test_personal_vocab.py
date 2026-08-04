"""Personal vocab decks (Slice E): the user_vocab service, the /vocab/personal API,
lazy pronunciation, and that personal cards flow through the shared /srs review queue.

DB is a temp SQLite built from Base.metadata; the LLM/TTS/storage are faked, so the
whole thing runs offline and deterministically.
"""

import asyncio
import json
import tempfile

from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

import app.content.tables  # noqa: F401  (register user_vocab / content_vocab for create_all)
import app.srs.models  # noqa: F401  (register srs_cards)
import app.usage.models  # noqa: F401  (register daily_usage)
from app.ai.accounting import make_usage
from app.ai.interfaces import LLMResult
from app.api.auth import get_current_user
from app.api.deps import get_ai_router, get_storage
from app.content import personal as P
from app.content.tables import UserVocab
from app.db.session import get_session
from app.main import create_app
from app.users.models import Base

_DB = f"sqlite+aiosqlite:///{tempfile.mkdtemp()}/personal.db"
_engine = create_async_engine(_DB)
_Session = async_sessionmaker(_engine, expire_on_commit=False)


def _run(coro):
    return asyncio.run(coro)


async def _create():
    async with _engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


_run(_create())


class FakeRouter:
    """Returns a fixed dictionary-entry JSON; records calls."""

    def __init__(self, payload: dict):
        self.payload = payload
        self.calls: list[str] = []

    def run(self, profile, *, system, messages, **kw):
        self.calls.append(profile)
        return LLMResult(
            text=json.dumps(self.payload),
            provider="ollama",
            model="llama3.1",
            usage=make_usage(input_tokens=10, output_tokens=6),
        )


class FakeTTS:
    name = "fake-tts"

    def __init__(self):
        self.calls = 0

    def synthesize(self, *, text, voice, lang="fr"):
        self.calls += 1
        return b"RIFFfakewav-" + text.encode("utf-8")


class FakeStorage:
    name = "fake"

    def __init__(self):
        self.objects: dict[str, bytes] = {}

    def put(self, key, data, content_type="application/octet-stream"):
        self.objects[key] = data
        return f"mem://{key}"

    def get(self, key):
        return self.objects[key]


def _client(*, uid=7, router=None, tts=None):
    storage = FakeStorage()

    async def _override_session():
        async with _Session() as s:
            yield s

    class _U:
        id = uid

    app = create_app()
    app.state.tts = tts
    app.state.stt = None
    app.dependency_overrides[get_session] = _override_session
    app.dependency_overrides[get_current_user] = lambda: _U()
    app.dependency_overrides[get_ai_router] = lambda: router or FakeRouter({})
    app.dependency_overrides[get_storage] = lambda: storage
    return TestClient(app), storage


# --- pure helpers -------------------------------------------------------------


def test_key_namespacing():
    assert P.personal_key("café") == "uv:cafe"
    assert P.personal_key("l'ordinateur") == "uv:l_ordinateur"
    assert P.is_personal_key("uv:cafe")
    assert not P.is_personal_key("cafe")  # a content id is not personal


def test_add_personal_is_idempotent_per_user():
    async def go():
        async with _Session() as s:
            row1, created1 = await P.add_personal(s, 1, fr="ordinateur", en="computer", gender="m")
            row2, created2 = await P.add_personal(s, 1, fr="ordinateur", en="different gloss")
            await s.commit()
            return row1, created1, row2, created2

    row1, created1, row2, created2 = _run(go())
    assert created1 is True and created2 is False
    assert row1.card_key == row2.card_key == "uv:ordinateur"
    assert row2.en == "computer"  # re-add did NOT overwrite the original


# --- API: preview -------------------------------------------------------------


def test_preview_enriches_without_writing():
    router = FakeRouter({"en": "computer", "pos": "noun", "gender": "x", "ipa": "/ɔʁdinatœʁ/"})
    client, _ = _client(router=router)
    r = client.post("/vocab/personal/preview", json={"word": "le silence"})
    assert r.status_code == 200
    enr = r.json()["enrichment"]
    assert enr["fr"] == "silence"  # article stripped
    assert enr["en"] == "computer"
    # "silence" is in the seed gender table as masculine — table beats the model's junk 'x'
    assert enr["gender"] == "m" and enr["gender_source"] == "table"
    assert router.calls == ["vocab_enrich"]
    # preview is read-only: nothing persisted
    assert client.get("/vocab/personal").json()["cards"] == []


def test_preview_respects_daily_budget():
    router = FakeRouter({"en": "x", "pos": "noun", "gender": "m", "ipa": ""})
    client, _ = _client(uid=42, router=router)
    # exhaust the vocab budget directly via the usage ledger
    from datetime import date

    async def burn():
        async with _Session() as s:
            from app.usage.service import add_usage

            await add_usage(s, 42, "vocab", 999_999, 0, date.today())
            await s.commit()

    _run(burn())
    r = client.post("/vocab/personal/preview", json={"word": "chat"})
    assert r.json() == {"enrichment": None, "over_budget": True}
    assert router.calls == []  # no LLM call once over budget


# --- API: add + list + queue integration --------------------------------------


def test_add_card_seeds_review_and_appears_in_queue():
    client, _ = _client(uid=8)
    r = client.post(
        "/vocab/personal",
        json={"fr": "épanouissement", "en": "fulfillment", "gender": "m", "pos": "noun"},
    )
    body = r.json()
    assert body["added"] is True and body["review_seeded"] is True
    key = body["card"]["card_key"]
    assert key == "uv:epanouissement"
    assert body["card"]["audio_url"] == f"/vocab/personal/audio/{key}"

    # it's in "My deck"
    cards = client.get("/vocab/personal").json()["cards"]
    assert [c["card_key"] for c in cards] == [key]

    # ...and in the shared review queue, resolved from user_vocab (not content_vocab)
    due = client.get("/srs/queue").json()["due"]
    entry = next(d for d in due if d["card_key"] == key)
    assert entry["vocab"]["fr"] == "épanouissement"
    assert entry["vocab"]["personal"] is True
    assert entry["vocab"]["audio_url"] == f"/vocab/personal/audio/{key}"


def test_add_card_is_idempotent():
    client, _ = _client(uid=9)
    first = client.post("/vocab/personal", json={"fr": "loisir", "en": "leisure"}).json()
    second = client.post("/vocab/personal", json={"fr": "loisir", "en": "hobby"}).json()
    assert first["added"] is True and second["added"] is False
    # only one card, original gloss kept
    cards = client.get("/vocab/personal").json()["cards"]
    assert len(cards) == 1 and cards[0]["en"] == "leisure"


# --- API: lazy pronunciation --------------------------------------------------


def test_personal_audio_synthesizes_once_and_caches():
    tts = FakeTTS()
    client, storage = _client(uid=10, tts=tts)
    key = client.post("/vocab/personal", json={"fr": "papillon", "en": "butterfly"}).json()["card"][
        "card_key"
    ]

    r1 = client.get(f"/vocab/personal/audio/{key}")
    assert r1.status_code == 200 and r1.content == b"RIFFfakewav-papillon"
    assert tts.calls == 1

    # second play is served from the cached key — no re-synthesis
    r2 = client.get(f"/vocab/personal/audio/{key}")
    assert r2.status_code == 200 and r2.content == r1.content
    assert tts.calls == 1

    # the cache key was persisted on the row
    async def fetch():
        async with _Session() as s:
            return await s.scalar(select(UserVocab).where(UserVocab.card_key == key))

    row = _run(fetch())
    assert row.audio_key is not None


def test_personal_audio_unknown_card_is_404():
    client, _ = _client(uid=11, tts=FakeTTS())
    assert client.get("/vocab/personal/audio/uv:nope").status_code == 404
