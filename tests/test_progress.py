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
        # a legacy row with a blank name — the board must not expose its email (qa-010)
        s.add(User(id=2, email="leak@secret.com", display_name="", password_hash="x"))
        s.add(User(id=3, email="race@x.com", display_name="Race", password_hash="x"))
        # qa-231: a pre-fix user with an oversized display_name (SQLite doesn't enforce length)
        s.add(User(id=4, email="long@x.com", display_name="X" * 200, password_hash="x"))
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
    assert compute_streak(0, None, today) == 1  # first ever
    assert compute_streak(3, today, today) == 3  # same day, no change
    assert compute_streak(3, today - timedelta(days=1), today) == 4  # consecutive day
    assert compute_streak(9, today - timedelta(days=2), today) == 1  # gap resets


# --- full chain over HTTP -----------------------------------------------------


def test_failing_score_does_not_complete():
    r = client.post("/progress/lessons/greetings-01/result", json={"score": 3.0})
    assert r.status_code == 200
    body = r.json()
    # first_pass is about passing (it gates XP/SRS), so a failing score is never a
    # first pass — even on a genuine first attempt (issue 428: field renamed from
    # the misleading `first_time` to match the comprehension endpoint).
    assert body["passed"] is False and body["first_pass"] is False
    assert "first_time" not in body  # old, misleading key is gone
    # gating unchanged: u2 still locked
    path = client.get("/content/path", params={"level": "a1"}).json()
    statuses = {u["id"]: u["status"] for u in path["units"]}
    assert statuses["a1.u1"] == "available" and statuses["a1.u2"] == "locked"


def test_locked_lesson_result_is_rejected_server_side():
    # qa issue 006: u2 is still locked here (u1 not yet completed), so recording a
    # result for cafe-01 (in u2) must be refused — gating is enforced on write, not
    # just rendered in the path. Runs before the u1-completing test below.
    path = client.get("/content/path", params={"level": "a1"}).json()
    statuses = {u["id"]: u["status"] for u in path["units"]}
    assert statuses["a1.u2"] == "locked"
    r = client.post("/progress/lessons/cafe-01/result", json={"score": 9.0})
    assert r.status_code == 409
    # and nothing was recorded: u2 stays locked
    path = client.get("/content/path", params={"level": "a1"}).json()
    assert {u["id"]: u["status"] for u in path["units"]}["a1.u2"] == "locked"


def test_passing_completes_and_lights_up_gating_streak_and_srs():
    r = client.post("/progress/lessons/greetings-01/result", json={"score": 9.5})
    body = r.json()
    assert body["passed"] and body["first_pass"]
    assert body["streak"] == 1 and body["xp"] == 10

    # u1 now has three lessons: one completion is not enough — u1 stays open, u2 locked
    path = client.get("/content/path", params={"level": "a1"}).json()
    statuses = {u["id"]: u["status"] for u in path["units"]}
    assert statuses["a1.u1"] == "available" and statuses["a1.u2"] == "locked"

    # SRS: the lesson's new_vocab is now in the review queue
    queue = client.get("/srs/queue").json()["due"]
    assert {"bonjour", "salut", "bonsoir"} <= {c["card_key"] for c in queue}
    assert any(c["vocab"] and c["vocab"]["fr"] == "bonjour" for c in queue)

    # finishing the rest of u1 completes the unit and unlocks u2
    for lid in ("greetings-02", "greetings-03"):
        client.post(f"/progress/lessons/{lid}/result", json={"score": 9.0})
    statuses = {
        u["id"]: u["status"]
        for u in client.get("/content/path", params={"level": "a1"}).json()["units"]
    }
    assert statuses["a1.u1"] == "complete" and statuses["a1.u2"] == "available"

    # progress + board reflect the three completed lessons (10 XP each)
    me = client.get("/progress/me").json()
    assert me["streak"] == 1 and me["xp"] == 30
    board = client.get("/progress/board").json()["members"]
    assert any(m["user_id"] == 1 and m["xp"] == 30 for m in board)


def test_recompletion_same_day_is_idempotent():
    r = client.post("/progress/lessons/greetings-01/result", json={"score": 9.9})
    body = r.json()
    assert body["first_pass"] is False
    assert body["xp"] == 30 and body["streak"] == 1  # no double XP / streak bump (3 lessons done)


def test_score_is_range_validated_0_to_10():
    # 0–10 scale: out-of-range scores are rejected (qa issue 003)
    assert (
        client.post("/progress/lessons/greetings-01/result", json={"score": 50}).status_code == 422
    )
    assert (
        client.post("/progress/lessons/greetings-01/result", json={"score": -1}).status_code == 422
    )


def test_board_never_exposes_email():
    # qa issue 010: the shared board fell back to email for a blank display_name
    members = client.get("/progress/board").json()["members"]
    assert all("@" not in m["display_name"] for m in members)
    blank = next(m for m in members if m["user_id"] == 2)
    assert blank["display_name"] == "Learner"


def test_board_truncates_oversized_display_name():
    # qa-231: pre-fix rows with >80-char display_name must be truncated at read time
    members = client.get("/progress/board").json()["members"]
    long_user = next(m for m in members if m["user_id"] == 4)
    assert len(long_user["display_name"]) == 80
    assert long_user["display_name"] == "X" * 80


def test_concurrent_completions_count_once_no_500():
    # qa-070: firing the same completion concurrently must not 500 or double XP — the
    # atomic insert-or-ignore lets exactly one win, and XP is counted once.
    from app.progress.api import LessonResultBody, submit_result
    from app.progress.models import UserProgress

    class _U:
        id = 3

    async def one():
        async with _Session() as s:
            return await submit_result("greetings-01", LessonResultBody(score=9.0), s, _U())

    async def run():
        # gather propagates any exception (the old code 500'd here)
        results = await asyncio.gather(one(), one(), one(), one())
        async with _Session() as s:
            prog = await s.get(UserProgress, 3)
        return results, prog.xp

    results, final_xp = asyncio.run(run())
    assert sum(r["first_pass"] for r in results) == 1  # exactly one counted it
    assert final_xp == 10  # XP awarded once, never doubled


def test_level_updates_to_highest_active():
    """qa-260: record_activity must promote prog.level when a higher level is active."""
    from app.progress.service import record_activity

    async def go():
        async with _Session() as s:
            prog = await record_activity(s, 1, xp_award=0, level="a1")
            assert prog.level == "a1"
            await s.commit()
        async with _Session() as s:
            prog = await record_activity(s, 1, xp_award=0, level="a2")
            assert prog.level == "a2"
            await s.commit()
        # a1 activity should NOT downgrade
        async with _Session() as s:
            prog = await record_activity(s, 1, xp_award=0, level="a1")
            assert prog.level == "a2"
            await s.commit()

    _run(go())


def test_review_endpoint_reschedules_a_card():
    r = client.post("/srs/review", json={"card_key": "bonjour", "rating": "good"})
    assert r.status_code == 200 and r.json()["card_key"] == "bonjour"
    assert (
        client.post("/srs/review", json={"card_key": "ghost", "rating": "good"}).status_code == 404
    )


def test_vocab_known_rejects_phantom_card_key():
    # qa-321: /content/vocab/known must validate the key against the catalog (like
    # srs/add qa-311), else phantom keys accumulate silently.
    ok = client.post("/content/vocab/known", json={"card_key": "bonjour", "known": True})
    assert ok.status_code == 200 and ok.json()["known"] is True
    ghost = client.post("/content/vocab/known", json={"card_key": "ghost", "known": True})
    assert ghost.status_code == 404
