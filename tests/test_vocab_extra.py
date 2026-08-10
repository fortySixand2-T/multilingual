"""Generic vocab study-extras API (/vocab/forms, /vocab/examples, /vocab/extra):
word forms (cached per user) + fresh usage sentences (rolling history), served for BOTH
banks — personal `uv:` cards and shared content-bank cards — from one `vocab_extra` row.

DB is a temp SQLite from Base.metadata; the LLM is faked, so this runs offline.
"""

import asyncio
import json
import tempfile

from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

import app.content.tables  # noqa: F401  (register content_vocab / user_vocab / vocab_extra)
import app.srs.models  # noqa: F401
import app.usage.models  # noqa: F401
from app.ai.accounting import make_usage
from app.ai.interfaces import LLMResult
from app.api.auth import get_current_user
from app.api.deps import get_ai_router
from app.content.tables import ContentVocab
from app.db.session import get_session
from app.main import create_app
from app.usage.service import add_usage
from app.users.models import Base

_DB = f"sqlite+aiosqlite:///{tempfile.mkdtemp()}/vocab_extra.db"
_engine = create_async_engine(_DB)
_Session = async_sessionmaker(_engine, expire_on_commit=False)


def _run(coro):
    return asyncio.run(coro)


async def _create():
    async with _engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


_run(_create())


class ProfileRouter:
    """Per-profile JSON payloads; records profiles called. A profile's value may be a
    dict (fixed) or a list of dicts returned in order across calls (last repeats) — lets
    us test that examples genuinely differ each press."""

    def __init__(self, by_profile: dict[str, object]):
        self.by_profile = by_profile
        self.calls: list[str] = []
        self._n: dict[str, int] = {}

    def run(self, profile, *, system, messages, **kw):
        self.calls.append(profile)
        payload = self.by_profile.get(profile, {})
        if isinstance(payload, list):
            i = min(self._n.get(profile, 0), len(payload) - 1)
            self._n[profile] = i + 1
            payload = payload[i]
        return LLMResult(
            text=json.dumps(payload),
            provider="ollama",
            model="llama3.1",
            usage=make_usage(input_tokens=10, output_tokens=6),
        )


def _client(*, uid=7, router=None):
    async def _override_session():
        async with _Session() as s:
            yield s

    class _U:
        id = uid

    app = create_app()
    app.state.tts = None
    app.state.stt = None
    app.dependency_overrides[get_session] = _override_session
    app.dependency_overrides[get_current_user] = lambda: _U()
    app.dependency_overrides[get_ai_router] = lambda: router or ProfileRouter({})
    return TestClient(app)


def _seed_content(**cards):
    """Seed ContentVocab rows: _seed_content(chat={'fr':'chat','en':'cat',...})."""

    async def go():
        async with _Session() as s:
            for cid, data in cards.items():
                s.add(ContentVocab(id=cid, level=data.pop("level", "a1"), data={"id": cid, **data}))
            await s.commit()

    _run(go())


def _add_personal(client, fr, en, pos="", gender=""):
    return client.post(
        "/vocab/personal", json={"fr": fr, "en": en, "pos": pos, "gender": gender}
    ).json()["card"]["card_key"]


def _burn_budget(uid):
    from datetime import date

    async def go():
        async with _Session() as s:
            await add_usage(s, uid, "vocab", 999_999, 0, date.today())
            await s.commit()

    _run(go())


# --- forms: works for a CONTENT card (the new surface) ------------------------


def test_forms_for_content_card_generates_then_caches():
    _seed_content(manger_cv={"fr": "manger", "en": "to eat", "pos": "verb", "level": "a2"})
    router = ProfileRouter({"vocab_forms": {"forms": [{"label": "présent", "fr": "je mange"}]}})
    client = _client(uid=70, router=router)

    r1 = client.post("/vocab/forms", json={"card_key": "manger_cv"})
    assert r1.status_code == 200
    assert r1.json() == {"forms": [{"label": "présent", "fr": "je mange"}], "cached": False}
    assert router.calls == ["vocab_forms"]

    # cached per user — no second model call
    r2 = client.post("/vocab/forms", json={"card_key": "manger_cv"})
    assert r2.json()["cached"] is True
    assert router.calls == ["vocab_forms"]


def test_forms_unknown_card_is_404_for_either_bank():
    client = _client(uid=71)
    assert client.post("/vocab/forms", json={"card_key": "no_such_content"}).status_code == 404
    assert client.post("/vocab/forms", json={"card_key": "uv:ghost"}).status_code == 404


def test_forms_over_budget_returns_gracefully():
    _seed_content(livre_cv={"fr": "livre", "en": "book", "pos": "noun", "gender": "m"})
    router = ProfileRouter({"vocab_forms": {"forms": [{"label": "x", "fr": "y"}]}})
    client = _client(uid=72, router=router)
    _burn_budget(72)
    r = client.post("/vocab/forms", json={"card_key": "livre_cv"})
    assert r.json() == {"forms": [], "over_budget": True}
    assert router.calls == []


def test_forms_empty_result_cached_for_non_inflecting_pos():
    # regression for qa-660, at the generic layer: a persisted `[]` (non-inflecting pos)
    # counts as "already generated" and stays free even after the budget is exhausted.
    _seed_content(vite_cv={"fr": "vite", "en": "quickly", "pos": "adverb"})
    router = ProfileRouter({"vocab_forms": {"forms": [{"label": "x", "fr": "y"}]}})
    client = _client(uid=73, router=router)

    r1 = client.post("/vocab/forms", json={"card_key": "vite_cv"})
    assert r1.json() == {"forms": [], "cached": False}
    assert router.calls == []  # non-inflecting pos never calls the model

    _burn_budget(73)
    r2 = client.post("/vocab/forms", json={"card_key": "vite_cv"})
    assert r2.json() == {"forms": [], "cached": True}  # not over_budget


# --- examples: fresh each press, rolling history, per user -------------------


def test_examples_for_content_card_are_fresh_and_accumulate():
    _seed_content(chat_cv={"fr": "chat", "en": "cat", "pos": "noun", "gender": "m"})
    router = ProfileRouter(
        {
            "vocab_examples": [
                {"examples": [{"fr": "Le chat dort.", "en": "The cat sleeps."}]},
                {"examples": [{"fr": "Un chat noir.", "en": "A black cat."}]},
            ]
        }
    )
    client = _client(uid=74, router=router)

    r1 = client.post("/vocab/examples", json={"card_key": "chat_cv"})
    assert [e["fr"] for e in r1.json()["examples"]] == ["Le chat dort."]

    r2 = client.post("/vocab/examples", json={"card_key": "chat_cv"})
    assert [e["fr"] for e in r2.json()["examples"]] == ["Un chat noir.", "Le chat dort."]
    assert router.calls == ["vocab_examples", "vocab_examples"]  # uncached: called each press

    # persisted history surfaces via the read endpoint (no model call)
    r3 = client.post("/vocab/extra", json={"card_key": "chat_cv"})
    assert [e["fr"] for e in r3.json()["examples"]] == ["Un chat noir.", "Le chat dort."]
    assert router.calls == ["vocab_examples", "vocab_examples"]  # /extra didn't generate


def test_examples_over_budget_keeps_existing_history():
    _seed_content(livre2_cv={"fr": "livre", "en": "book", "pos": "noun", "gender": "m"})
    router = ProfileRouter(
        {"vocab_examples": {"examples": [{"fr": "Je lis un livre.", "en": "I read a book."}]}}
    )
    client = _client(uid=75, router=router)
    client.post("/vocab/examples", json={"card_key": "livre2_cv"})  # seed one

    _burn_budget(75)
    r = client.post("/vocab/examples", json={"card_key": "livre2_cv"})
    assert r.json()["over_budget"] is True
    assert [e["fr"] for e in r.json()["examples"]] == ["Je lis un livre."]  # kept


# --- both banks share the resolver + one row per (user, card) ----------------


def test_forms_work_for_personal_card_too():
    router = ProfileRouter({"vocab_forms": {"forms": [{"label": "présent", "fr": "je mange"}]}})
    client = _client(uid=76, router=router)
    key = _add_personal(client, "manger", "to eat", pos="verb")  # -> uv:manger
    r = client.post("/vocab/forms", json={"card_key": key})
    assert r.json()["forms"] == [{"label": "présent", "fr": "je mange"}]
    assert router.calls == ["vocab_forms"]


def test_extra_is_scoped_per_user():
    # user A generates examples for a content card; user B sees none for the same card.
    _seed_content(mer_cv={"fr": "mer", "en": "sea", "pos": "noun", "gender": "f"})
    router = ProfileRouter(
        {"vocab_examples": {"examples": [{"fr": "La mer est calme.", "en": "The sea is calm."}]}}
    )
    a = _client(uid=80, router=router)
    b = _client(uid=81, router=router)
    a.post("/vocab/examples", json={"card_key": "mer_cv"})

    assert b.post("/vocab/extra", json={"card_key": "mer_cv"}).json() == {
        "forms": None,
        "examples": [],
    }
