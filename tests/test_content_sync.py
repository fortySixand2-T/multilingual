"""AC1.1 (DB sync) + the content API.

Uses a local engine and FastAPI dependency overrides so it's independent of the
global engine and of real auth.
"""

import asyncio
import tempfile
from pathlib import Path

from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

import app.content.tables  # noqa: F401 - register tables on Base.metadata
import app.srs.models  # noqa: F401 - register srs_cards (vocab in_review join)
from app.api.auth import get_current_user
from app.content.api import compute_unit_status, get_storage
from app.content.loader import load_content
from app.content.models import GRAMMAR_CATEGORIES
from app.content.sync import sync_bundle
from app.content.tables import ContentLesson, ContentUnit, ContentVocab
from app.db.session import get_session
from app.main import create_app
from app.users.models import Base

CONTENT_ROOT = Path(__file__).resolve().parents[1] / "content"
_DB = f"sqlite+aiosqlite:///{tempfile.mkdtemp()}/content.db"
_engine = create_async_engine(_DB)
_Session = async_sessionmaker(_engine, expire_on_commit=False)


def _run(coro):
    return asyncio.run(coro)


async def _setup():
    async with _engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    async with _Session() as session:
        await sync_bundle(session, load_content(CONTENT_ROOT, "a1"))


_run(_setup())


# --- app with overridden session + auth ---------------------------------------


class _FakeUser:
    id = 1


async def _override_session():
    async with _Session() as session:
        yield session


class _FakeStorage:
    objects = {"a1/audio/bonjour.mp3": b"ID3fakeaudio"}

    def get(self, key: str) -> bytes:
        return self.objects[key]  # KeyError -> 404 in the route


app = create_app()
app.dependency_overrides[get_session] = _override_session
app.dependency_overrides[get_current_user] = lambda: _FakeUser()
app.dependency_overrides[get_storage] = lambda: _FakeStorage()
client = TestClient(app)


def test_sync_wrote_expected_rows():
    async def go():
        async with _Session() as s:
            units = (
                (await s.execute(select(ContentUnit).order_by(ContentUnit.ordinal))).scalars().all()
            )
            lessons = (await s.execute(select(ContentLesson))).scalars().all()
            vocab = (await s.execute(select(ContentVocab))).scalars().all()
            return [u.id for u in units], {lz.id for lz in lessons}, {v.id for v in vocab}

    unit_ids, lesson_ids, vocab_ids = _run(go())
    assert unit_ids[:2] == ["a1.u1", "a1.u2"]  # ordinal-ordered
    assert {"greetings-01", "cafe-01"} <= lesson_ids
    assert {"bonjour", "salut", "bonsoir", "cafe", "eau"} <= vocab_ids


def test_resync_is_idempotent():
    async def go():
        async with _Session() as s:
            await sync_bundle(s, load_content(CONTENT_ROOT, "a1"))
        async with _Session() as s:
            return len((await s.execute(select(ContentUnit))).scalars().all())

    # replaced, not duplicated
    assert _run(go()) == len(load_content(CONTENT_ROOT, "a1").path.units)


def test_gating_function():
    async def units():
        async with _Session() as s:
            return (
                (await s.execute(select(ContentUnit).order_by(ContentUnit.ordinal))).scalars().all()
            )

    us = _run(units())
    # nothing completed -> first unit open, gated unit locked
    none_done = compute_unit_status(us, set())
    assert none_done["a1.u1"] == "available" and none_done["a1.u2"] == "locked"
    # finishing ALL of u1's lessons completes u1 and unlocks u2
    u1_done = compute_unit_status(us, {"greetings-01", "greetings-02", "greetings-03"})
    assert u1_done["a1.u1"] == "complete" and u1_done["a1.u2"] == "available"


def test_path_endpoint_reports_gating():
    r = client.get("/content/path", params={"level": "a1"})
    assert r.status_code == 200
    body = r.json()
    statuses = {u["id"]: u["status"] for u in body["units"]}
    assert statuses["a1.u1"] == "available" and statuses["a1.u2"] == "locked"
    assert body["units"][0]["unlock"] == {"type": "none", "requires": []}


def test_path_endpoint_unknown_level_404():
    assert client.get("/content/path", params={"level": "zz"}).status_code == 404


def test_levels_endpoint_lists_synced_levels():
    body = client.get("/content/levels").json()
    # fixture syncs only a1; the endpoint reflects what's actually in the DB
    assert body["levels"] == ["a1"]


def test_lesson_endpoint_returns_exercises():
    r = client.get("/content/lessons/greetings-01")
    assert r.status_code == 200
    body = r.json()
    assert body["id"] == "greetings-01"
    assert [e["type"] for e in body["exercises"]] == [
        "mcq",
        "word_bank",
        "listen_type",
        "match_pairs",
    ]


def test_lesson_endpoint_404():
    assert client.get("/content/lessons/nope").status_code == 404


def test_grammar_endpoint_lists_points_in_path_order():
    body = client.get("/content/grammar", params={"level": "a1"}).json()
    assert body["level"] == "a1"
    items = body["items"]
    assert items and all(i["grammar_point"].strip() for i in items)
    assert {
        "unit_id",
        "unit_title",
        "lesson_id",
        "lesson_title",
        "grammar_point",
    } <= items[0].keys()
    # items follow path order: unit ordinals never decrease down the list
    path = client.get("/content/path", params={"level": "a1"}).json()["units"]
    order = {u["id"]: idx for idx, u in enumerate(path)}
    seq = [order[i["unit_id"]] for i in items]
    assert seq == sorted(seq)
    # completeness: every path-lesson with a non-empty grammar_point must appear
    bundle = load_content(CONTENT_ROOT, "a1")
    expected = sum(
        1
        for unit in bundle.path.units
        for lid in unit.lessons
        if (lesson := bundle.lessons.get(lid)) and lesson.grammar_point.strip()
    )
    assert len(items) == expected


def test_grammar_endpoint_items_carry_valid_category():
    """Every grammar item exposes a grammar_category from the controlled set — the
    grouping/filter axis the reference UI relies on. a1 content is fully categorized,
    so none should be empty."""
    items = client.get("/content/grammar", params={"level": "a1"}).json()["items"]
    assert items
    for it in items:
        assert it["grammar_category"] in GRAMMAR_CATEGORIES, it


def test_grammar_endpoint_unknown_level_404():
    assert client.get("/content/grammar", params={"level": "zz"}).status_code == 404


# --- content audio delivery ---------------------------------------------------


def test_content_audio_serves_asset():
    r = client.get("/content/audio/a1/audio/bonjour.mp3")
    assert r.status_code == 200
    assert r.headers["content-type"] == "audio/mpeg"
    assert r.content == b"ID3fakeaudio"


def test_content_audio_missing_is_404():
    assert client.get("/content/audio/a1/audio/nope.mp3").status_code == 404


def test_content_audio_rejects_bad_key_shape():
    # no /audio/ segment, not an .mp3 -> fails the key guard before touching storage
    assert client.get("/content/audio/a1/secret.txt").status_code == 404
    assert client.get("/content/audio/etc/passwd").status_code == 404


# --- vocabulary deck ----------------------------------------------------------


def test_vocab_returns_deck_for_level():
    cards = client.get("/content/vocab", params={"level": "a1"}).json()["cards"]
    ids = {c["id"] for c in cards}
    assert {"bonjour", "cafe"} <= ids
    bonjour = next(c for c in cards if c["id"] == "bonjour")
    assert bonjour["fr"] == "bonjour" and bonjour["en"] and "greeting" in bonjour["tags"]


def test_vocab_filters_by_tag():
    cards = client.get("/content/vocab", params={"level": "a1", "tag": "greeting"}).json()["cards"]
    ids = {c["id"] for c in cards}
    assert "bonjour" in ids and "cafe" not in ids
    assert all("greeting" in c["tags"] for c in cards)


def test_vocab_unknown_level_404():
    assert client.get("/content/vocab", params={"level": "zz"}).status_code == 404


def test_vocab_all_levels_attaches_level():
    # no level param → every level; each card carries its level (only a1 in this fixture)
    cards = client.get("/content/vocab").json()["cards"]
    assert cards and all(c["level"] == "a1" for c in cards)
    assert any(c["id"] == "bonjour" for c in cards)


def test_vocab_cards_carry_audio_key():
    cards = client.get("/content/vocab", params={"level": "a1"}).json()["cards"]
    bonjour = next(c for c in cards if c["id"] == "bonjour")
    assert bonjour["audio"] == "a1/audio/bonjour.mp3"
    cafe = next(c for c in cards if c["id"] == "cafe")
    assert cafe["audio"] == "a1/audio/cafe.mp3"  # convention fills it in


def test_vocab_cards_carry_gender():
    rows = client.get("/content/vocab", params={"level": "a1"}).json()["cards"]
    cards = {c["id"]: c for c in rows}
    assert cards["cafe"]["gender"] == "m"
    assert cards["eau"]["gender"] == "f"
    assert cards["un"]["gender"] == ""  # numeral: not gendered
    # dual-gender word carries its feminine form + a feminine audio key
    serveur = cards["serveur"]
    assert serveur["gender"] == "mf"
    assert serveur["fem"] == "serveuse"
    assert serveur["fem_audio"] == "a1/audio/serveur_f.mp3"
    # non-mf words get no fem_audio
    assert "fem_audio" not in cards["cafe"]


def test_vocab_known_mark_and_reset():
    # default: nothing known
    cards = client.get("/content/vocab", params={"level": "a1"}).json()["cards"]
    assert next(c for c in cards if c["id"] == "cafe")["known"] is False
    # mark known
    r = client.post("/content/vocab/known", json={"card_key": "cafe", "known": True})
    assert r.status_code == 200 and r.json() == {"card_key": "cafe", "known": True}
    cards = client.get("/content/vocab", params={"level": "a1"}).json()["cards"]
    assert next(c for c in cards if c["id"] == "cafe")["known"] is True
    # reset (press "don't know" again)
    client.post("/content/vocab/known", json={"card_key": "cafe", "known": False})
    cards = client.get("/content/vocab", params={"level": "a1"}).json()["cards"]
    assert next(c for c in cards if c["id"] == "cafe")["known"] is False


def test_vocab_add_to_review_sets_in_review_flag():
    # not in review yet
    cards = client.get("/content/vocab", params={"level": "a1"}).json()["cards"]
    assert next(c for c in cards if c["id"] == "salut")["in_review"] is False
    # add to review (seeds an SRS card)
    r = client.post("/srs/add", json={"card_key": "salut"})
    assert r.status_code == 200 and r.json() == {"card_key": "salut", "added": True}
    # idempotent — already there
    assert client.post("/srs/add", json={"card_key": "salut"}).json()["added"] is False
    # reflected in the vocab deck
    cards = client.get("/content/vocab", params={"level": "a1"}).json()["cards"]
    assert next(c for c in cards if c["id"] == "salut")["in_review"] is True


def test_srs_add_rejects_empty_card_key():
    # empty string is not a valid id — 422, same as null/missing (qa issue 310)
    assert client.post("/srs/add", json={"card_key": ""}).status_code == 422
    assert client.post("/srs/add", json={}).status_code == 422


def test_srs_add_rejects_nonexistent_card_key():
    # an arbitrary key that names no vocab card must not seed a phantom (qa issue 311)
    r = client.post("/srs/add", json={"card_key": "zzz_fake_not_real"})
    assert r.status_code == 404
    # and it never reached the queue
    due = client.get("/srs/queue").json()["due"]
    assert all(c["card_key"] != "zzz_fake_not_real" for c in due)


def test_srs_queue_attaches_audio_key():
    # The review queue must apply the same <level>/audio/<id>.mp3 convention as the
    # vocab endpoint, so the Review screen can play pronunciation (qa issue 350).
    # "bonsoir" has no explicit `audio:` field — exercises the fallback.
    client.post("/srs/add", json={"card_key": "bonsoir"})
    due = client.get("/srs/queue", params={"limit": 100}).json()["due"]
    card = next(c for c in due if c["card_key"] == "bonsoir")
    assert card["vocab"]["audio"] == "a1/audio/bonsoir.mp3"
