"""Escape hatch: after WAIVE_AFTER_ATTEMPTS failed tries a learner may waive a
lesson to unlock the next unit; the lesson stays flagged for review (not passed),
earns no XP, and can still be passed later to earn its star. Isolated harness so the
shared-state tests in test_progress.py are untouched."""

import asyncio
import tempfile
from pathlib import Path

from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

import app.content.tables  # noqa: F401
import app.progress.models  # noqa: F401
import app.srs.models  # noqa: F401
from app.api.auth import get_current_user
from app.content.loader import load_content
from app.content.sync import sync_bundle
from app.db.session import get_session
from app.main import create_app
from app.progress.api import WAIVE_AFTER_ATTEMPTS
from app.users.models import Base, User

CONTENT_ROOT = Path(__file__).resolve().parents[1] / "content"
_DB = f"sqlite+aiosqlite:///{tempfile.mkdtemp()}/waive.db"
_engine = create_async_engine(_DB)
_Session = async_sessionmaker(_engine, expire_on_commit=False)


async def _setup():
    async with _engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    async with _Session() as s:
        await sync_bundle(s, load_content(CONTENT_ROOT, "a1"))
        s.add(User(id=1, email="w@x.com", display_name="W", password_hash="x"))
        await s.commit()


asyncio.run(_setup())


class _FakeUser:
    id = 1


async def _override_session():
    async with _Session() as s:
        yield s


app = create_app()
app.dependency_overrides[get_session] = _override_session
app.dependency_overrides[get_current_user] = lambda: _FakeUser()
client = TestClient(app)


def _statuses():
    path = client.get("/content/path", params={"level": "a1"}).json()
    return path, {u["id"]: u["status"] for u in path["units"]}


def test_escape_hatch_full_flow():
    # Pass the first two lessons of unit 1; unit 2 is still gated by the third.
    for lid in ("greetings-01", "greetings-02"):
        assert client.post(f"/progress/lessons/{lid}/result", json={"score": 9.5}).json()["passed"]
    _, st = _statuses()
    assert st["a1.u2"] == "locked"

    # First failure: attempt counted, no waive offered yet, still no unlock.
    r = client.post("/progress/lessons/greetings-03/result", json={"score": 3.0}).json()
    assert r["passed"] is False and r["attempts"] == 1 and r["can_waive"] is False
    assert client.post("/progress/lessons/greetings-03/waive").status_code == 409  # too early

    # Second failure reaches the threshold and offers the hatch — but unit 2 is
    # still locked until the learner actually waives.
    r = client.post("/progress/lessons/greetings-03/result", json={"score": 3.0}).json()
    assert r["attempts"] == WAIVE_AFTER_ATTEMPTS and r["can_waive"] is True
    _, st = _statuses()
    assert st["a1.u2"] == "locked"

    # Waiving no-XP unlocks unit 2 and flags the lesson for review (not a pass).
    xp_before = client.get("/progress/me").json()["xp"]
    w = client.post("/progress/lessons/greetings-03/waive")
    assert w.status_code == 200 and w.json()["waived"] is True and w.json()["passed"] is False
    assert client.get("/progress/me").json()["xp"] == xp_before  # waiving earns nothing
    path, st = _statuses()
    assert st["a1.u2"] == "available"
    assert "greetings-03" in path["waived_lessons"]
    assert "greetings-03" not in path["passed_lessons"]
    assert {"greetings-01", "greetings-02"} <= set(path["passed_lessons"])

    # A never-attempted, now-unlocked lesson can't be waived.
    assert client.post("/progress/lessons/cafe-01/waive").status_code == 409

    # Retrying a waived lesson and passing upgrades it to a real star.
    assert client.post("/progress/lessons/greetings-03/result", json={"score": 9.5}).json()[
        "passed"
    ]
    path, _ = _statuses()
    assert "greetings-03" in path["passed_lessons"]
    assert "greetings-03" not in path["waived_lessons"]
