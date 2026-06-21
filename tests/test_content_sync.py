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
from app.api.auth import get_current_user
from app.content.api import compute_unit_status
from app.content.loader import load_content
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


app = create_app()
app.dependency_overrides[get_session] = _override_session
app.dependency_overrides[get_current_user] = lambda: _FakeUser()
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

    assert _run(go()) == len(load_content(CONTENT_ROOT, "a1").path.units)  # replaced, not duplicated


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
    # finishing u1's lesson completes u1 and unlocks u2
    u1_done = compute_unit_status(us, {"greetings-01"})
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
