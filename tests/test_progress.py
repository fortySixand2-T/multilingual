"""AC1.6 — progress (streak/XP/board) and the full completion chain:
lesson result → completion recorded → content gating unlocks → SRS seeded.
"""
import asyncio
import tempfile
from datetime import date, timedelta
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
from app.progress.models import compute_streak
from app.users.models import Base, User

CONTENT_ROOT = Path(__file__).resolve().parents[1] / "content"
_DB = f"sqlite+aiosqlite:///{tempfile.mkdtemp()}/progress.db"
_engine = create_async_engine(_DB)
_Session = async_sessionmaker(_engine, expire_on_commit=False)


def _run(coro):
    return asyncio.run(coro)


async def _setup():
    async with _engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    async with _Session() as s:
        await sync_bundle(s, load_content(CONTENT_ROOT, "a1"))
        s.add(User(id=1, email="me@x.com", display_name="Me", password_hash="x"))
        await s.commit()


_run(_setup())


class _FakeUser:
    id = 1


async def _override_session():
    async with _Session() as s:
        yield s


app = create_app()
app.dependency_overrides[get_session] = _override_session
app.dependency_overrides[get_current_user] = lambda: _FakeUser()
client = TestClient(app)


# --- pure streak logic --------------------------------------------------------

def test_compute_streak():
    today = date(2026, 6, 15)
    assert compute_streak(0, None, today) == 1                       # first ever
    assert compute_streak(3, today, today) == 3                      # same day, no change
    assert compute_streak(3, today - timedelta(days=1), today) == 4  # consecutive day
    assert compute_streak(9, today - timedelta(days=2), today) == 1  # gap resets


# --- full chain over HTTP -----------------------------------------------------

def test_failing_score_does_not_complete():
    r = client.post("/progress/lessons/greetings-01/result", json={"score": 0.5})
    assert r.status_code == 200
    body = r.json()
    assert body["passed"] is False and body["first_time"] is False
    # gating unchanged: u2 still locked
    path = client.get("/content/path", params={"level": "a1"}).json()
    statuses = {u["id"]: u["status"] for u in path["units"]}
    assert statuses == {"a1.u1": "available", "a1.u2": "locked"}


def test_passing_completes_and_lights_up_gating_streak_and_srs():
    r = client.post("/progress/lessons/greetings-01/result", json={"score": 0.95})
    body = r.json()
    assert body["passed"] and body["first_time"]
    assert body["streak"] == 1 and body["xp"] == 10

    # content gating: completing u1's only lesson unlocks u2
    path = client.get("/content/path", params={"level": "a1"}).json()
    statuses = {u["id"]: u["status"] for u in path["units"]}
    assert statuses == {"a1.u1": "complete", "a1.u2": "available"}

    # SRS: the lesson's new_vocab is now in the review queue
    queue = client.get("/srs/queue").json()["due"]
    assert {"bonjour", "salut", "bonsoir"} <= {c["card_key"] for c in queue}
    assert any(c["vocab"] and c["vocab"]["fr"] == "bonjour" for c in queue)

    # progress + board reflect it
    me = client.get("/progress/me").json()
    assert me["streak"] == 1 and me["xp"] == 10
    board = client.get("/progress/board").json()["members"]
    assert any(m["user_id"] == 1 and m["xp"] == 10 for m in board)


def test_recompletion_same_day_is_idempotent():
    r = client.post("/progress/lessons/greetings-01/result", json={"score": 0.99})
    body = r.json()
    assert body["first_time"] is False
    assert body["xp"] == 10 and body["streak"] == 1  # no double XP / streak bump


def test_review_endpoint_reschedules_a_card():
    r = client.post("/srs/review", json={"card_key": "bonjour", "rating": "good"})
    assert r.status_code == 200 and r.json()["card_key"] == "bonjour"
    assert client.post("/srs/review", json={"card_key": "ghost", "rating": "good"}).status_code == 404
