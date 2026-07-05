"""Phase 5 — exam simulation: CLB mapping, blueprint loading, and the mock flow."""

import asyncio
import tempfile
from contextlib import contextmanager
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

import app.exam.tables  # noqa: F401
import app.progress.models  # noqa: F401
from app.api.auth import get_current_user
from app.db.session import get_session
from app.exam.api import EXAM_XP
from app.exam.clb import aggregate_report, clb_from_fraction
from app.exam.loader import ExamError, _check_references, load_blueprints
from app.exam.models import ExamBlueprint, ExamSection
from app.exam.sync import sync_blueprints
from app.main import create_app
from app.users.models import Base

CONTENT_ROOT = Path(__file__).resolve().parents[1] / "content"
_DB = f"sqlite+aiosqlite:///{tempfile.mkdtemp()}/exam.db"
_engine = create_async_engine(_DB)
_Session = async_sessionmaker(_engine, expire_on_commit=False)


def _run(coro):
    return asyncio.run(coro)


async def _setup():
    async with _engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    async with _Session() as s:
        await sync_blueprints(s, CONTENT_ROOT, "a1")


_run(_setup())


async def _override_session():
    async with _Session() as s:
        yield s


class _U:
    id = 314


app = create_app()
app.dependency_overrides[get_session] = _override_session
app.dependency_overrides[get_current_user] = lambda: _U()
client = TestClient(app)


# --- pure CLB logic -----------------------------------------------------------


def test_clb_from_fraction():
    assert clb_from_fraction(0.95) == 9
    assert clb_from_fraction(0.72) == 7
    assert clb_from_fraction(0.4) == 5
    assert clb_from_fraction(0.0) == 3
    assert clb_from_fraction(1.5) == 9  # clamped


def test_aggregate_overall_is_floor_across_skills():
    rep = aggregate_report({"reading": 8, "listening": 7, "writing": 6, "speaking": 7})
    assert rep["overall"] == 6 and rep["target_met"] is False
    assert "estimate" in rep["note"].lower()
    rep2 = aggregate_report({"reading": 7, "listening": 7, "writing": 7, "speaking": 8})
    assert rep2["overall"] == 7 and rep2["target_met"] is True


# --- blueprint schema / loader ------------------------------------------------


def test_loads_example_blueprint():
    bps = load_blueprints(CONTENT_ROOT, "a1")
    assert "mock-1" in bps
    skills = [s.skill for s in bps["mock-1"].sections]
    assert skills == ["reading", "listening", "writing", "speaking"]


def test_section_requires_matching_refs():
    with pytest.raises(ValidationError):
        ExamSection(skill="reading", time_limit_seconds=60)  # missing comprehension_set_id
    with pytest.raises(ValidationError):
        ExamSection(skill="writing", time_limit_seconds=60)  # missing writing_task_ids


# --- blueprint reference validation (composed of other modules' content) ------


def _bp(section: ExamSection) -> dict[str, ExamBlueprint]:
    return {"x": ExamBlueprint(id="x", level="a1", title="t", sections=[section])}


def test_loads_three_blueprints_per_level():
    for lvl, last in (("a1", "mock-3"), ("a2", "a2-mock-3")):
        bps = load_blueprints(CONTENT_ROOT, lvl)
        assert len(bps) == 3 and last in bps


def test_dangling_comprehension_ref_fails():
    sec = ExamSection(skill="reading", time_limit_seconds=60, comprehension_set_id="nope-xyz")
    with pytest.raises(ExamError, match="nope-xyz"):
        _check_references(_bp(sec), CONTENT_ROOT, "a1")


def test_comprehension_skill_mismatch_fails():
    # listen-greet-01 is a listening set; using it in a reading section must fail
    sec = ExamSection(
        skill="reading", time_limit_seconds=60, comprehension_set_id="listen-greet-01"
    )
    with pytest.raises(ExamError, match="listening set"):
        _check_references(_bp(sec), CONTENT_ROOT, "a1")


def test_dangling_writing_ref_fails():
    sec = ExamSection(skill="writing", time_limit_seconds=60, writing_task_ids=["write-nope"])
    with pytest.raises(ExamError, match="write-nope"):
        _check_references(_bp(sec), CONTENT_ROOT, "a1")


def test_cross_level_writing_ref_fails():
    # an A2 writing task referenced from an A1 blueprint isn't in A1's task set
    sec = ExamSection(skill="writing", time_limit_seconds=60, writing_task_ids=["write-a2-hotel"])
    with pytest.raises(ExamError, match="write-a2-hotel"):
        _check_references(_bp(sec), CONTENT_ROOT, "a1")


# --- full mock flow over HTTP -------------------------------------------------


def test_full_mock_start_sections_finish_history():
    bps = client.get("/exam/blueprints", params={"level": "a1"}).json()["blueprints"]
    assert bps[0]["id"] == "mock-1" and bps[0]["sections"] == 4

    aid = client.post("/exam/start", json={"blueprint_id": "mock-1"}).json()["attempt_id"]

    client.post(
        f"/exam/{aid}/section", json={"skill": "reading", "correct": 8, "total": 10}
    )  # 0.8 -> 8
    client.post(
        f"/exam/{aid}/section", json={"skill": "listening", "correct": 7, "total": 10}
    )  # ->7
    client.post(f"/exam/{aid}/section", json={"skill": "writing", "clb_estimate": 7})
    r = client.post(f"/exam/{aid}/section", json={"skill": "speaking", "clb_estimate": 6})
    assert set(r.json()["recorded"]) == {"reading", "listening", "writing", "speaking"}

    report = client.post(f"/exam/{aid}/finish").json()["report"]
    assert report["per_skill"] == {"reading": 8, "listening": 7, "writing": 7, "speaking": 6}
    assert report["overall"] == 6  # floor
    assert report["target_met"] is False

    hist = client.get("/exam/history").json()["attempts"]
    assert hist[0]["attempt_id"] == aid and hist[0]["status"] == "finished"
    assert hist[0]["clb_report"]["overall"] == 6
    assert hist[0]["level"] == "a1"  # qa-220: level must be serialized


@contextmanager
def _acting_as(uid: int):
    """Route auth to a specific user id for the block, so its exam attempts are
    isolated from the module's shared default user (id 314)."""
    prev = app.dependency_overrides[get_current_user]
    app.dependency_overrides[get_current_user] = lambda: type("U", (), {"id": uid})()
    try:
        yield
    finally:
        app.dependency_overrides[get_current_user] = prev


def _finish_mock(scores: dict[str, int]) -> None:
    """Start mock-1, record all 4 sections and finish. reading/listening take
    correct/total (correct/10 maps to that CLB band); writing/speaking take clb."""
    aid = client.post("/exam/start", json={"blueprint_id": "mock-1"}).json()["attempt_id"]
    client.post(
        f"/exam/{aid}/section", json={"skill": "reading", "correct": scores["reading"], "total": 10}
    )
    client.post(
        f"/exam/{aid}/section",
        json={"skill": "listening", "correct": scores["listening"], "total": 10},
    )
    client.post(
        f"/exam/{aid}/section", json={"skill": "writing", "clb_estimate": scores["writing"]}
    )
    client.post(
        f"/exam/{aid}/section", json={"skill": "speaking", "clb_estimate": scores["speaking"]}
    )
    client.post(f"/exam/{aid}/finish")


def test_readiness_empty_when_no_finished_mock():
    with _acting_as(9001):
        body = client.get("/exam/readiness").json()
    assert body == {
        "attempts": 0,
        "per_skill": {},
        "overall": None,
        "target_met": False,
        "weakest_skill": None,
        "target_clb": 7,
    }


def test_readiness_aggregates_best_recent_and_trend():
    with _acting_as(9002):
        # two finished mocks; reading improves 6→8, speaking stays weakest
        _finish_mock({"reading": 6, "listening": 7, "writing": 7, "speaking": 5})
        _finish_mock({"reading": 8, "listening": 7, "writing": 8, "speaking": 6})
        body = client.get("/exam/readiness").json()
    assert body["attempts"] == 2
    assert body["per_skill"]["reading"] == {"best": 8, "recent": 8, "trend": [6, 8]}
    assert body["per_skill"]["speaking"] == {"best": 6, "recent": 6, "trend": [5, 6]}
    # overall = weakest skill's best (speaking=6); not yet at CLB 7
    assert body["overall"] == 6
    assert body["target_met"] is False
    assert body["weakest_skill"] == "speaking"


def test_section_validation():
    aid = client.post("/exam/start", json={"blueprint_id": "mock-1"}).json()["attempt_id"]
    # comprehension needs correct+total
    assert client.post(f"/exam/{aid}/section", json={"skill": "reading"}).status_code == 422
    # writing needs clb
    assert client.post(f"/exam/{aid}/section", json={"skill": "writing"}).status_code == 422
    # correct cannot exceed total (qa issue 005)
    r = client.post(f"/exam/{aid}/section", json={"skill": "reading", "correct": 50, "total": 10})
    assert r.status_code == 422


def test_no_score_until_all_sections_complete():
    # qa issue 004: finishing early must not produce a score
    aid = client.post("/exam/start", json={"blueprint_id": "mock-1"}).json()["attempt_id"]
    early = client.post(f"/exam/{aid}/finish")
    assert early.status_code == 409
    # resume shows what's left
    state = client.get(f"/exam/attempts/{aid}").json()
    assert state["status"] == "in_progress"
    assert set(state["remaining"]) == {"reading", "listening", "writing", "speaking"}

    # complete every section, then finish works and is idempotent
    client.post(f"/exam/{aid}/section", json={"skill": "reading", "correct": 8, "total": 10})
    client.post(f"/exam/{aid}/section", json={"skill": "listening", "correct": 7, "total": 10})
    client.post(f"/exam/{aid}/section", json={"skill": "writing", "clb_estimate": 7})
    client.post(f"/exam/{aid}/section", json={"skill": "speaking", "clb_estimate": 6})
    assert client.post(f"/exam/{aid}/finish").json()["report"]["overall"] == 6
    assert client.post(f"/exam/{aid}/finish").json()["report"]["overall"] == 6  # idempotent

    # can't record after finishing
    after = client.post(f"/exam/{aid}/section", json={"skill": "writing", "clb_estimate": 9})
    assert after.status_code == 409


def test_start_and_get_attempt_include_started_at():
    """qa-250: start and get_attempt must include started_at for client-side timers."""
    r = client.post("/exam/start", json={"blueprint_id": "mock-1"})
    body = r.json()
    assert "started_at" in body
    aid = body["attempt_id"]
    detail = client.get(f"/exam/attempts/{aid}").json()
    assert "started_at" in detail
    # both should be valid ISO timestamps
    from datetime import datetime

    datetime.fromisoformat(body["started_at"])
    datetime.fromisoformat(detail["started_at"])


def test_start_unknown_blueprint_404():
    assert client.post("/exam/start", json={"blueprint_id": "nope"}).status_code == 404


def test_start_resumes_in_progress_instead_of_duplicating():
    # qa-150: starting the same blueprint while one is in progress resumes it, so the
    # resume list / history can't fill with duplicate in-progress attempts.
    a = client.post("/exam/start", json={"blueprint_id": "mock-1"}).json()["attempt_id"]
    b = client.post("/exam/start", json={"blueprint_id": "mock-1"}).json()["attempt_id"]
    assert a == b


def test_finish_awards_xp():
    """qa-252: completing a mock exam must award XP via record_activity."""
    from app.progress.models import UserProgress

    aid = client.post("/exam/start", json={"blueprint_id": "mock-1"}).json()["attempt_id"]
    client.post(f"/exam/{aid}/section", json={"skill": "reading", "correct": 8, "total": 10})
    client.post(f"/exam/{aid}/section", json={"skill": "listening", "correct": 7, "total": 10})
    client.post(f"/exam/{aid}/section", json={"skill": "writing", "clb_estimate": 7})
    client.post(f"/exam/{aid}/section", json={"skill": "speaking", "clb_estimate": 6})
    r = client.post(f"/exam/{aid}/finish")
    assert r.status_code == 200

    async def check():
        async with _Session() as s:
            return await s.get(UserProgress, _U.id)

    prog = _run(check())
    assert prog is not None
    assert prog.xp >= 25  # EXAM_XP = 25


def test_concurrent_sections_all_persist():
    # qa-170: recording all four sections concurrently must keep all four — a
    # read-modify-write on the JSON column silently dropped the racing ones.
    from app.exam.api import SectionResultBody, record_section

    aid = client.post("/exam/start", json={"blueprint_id": "mock-1"}).json()["attempt_id"]
    bodies = [
        SectionResultBody(skill="reading", correct=20, total=40),
        SectionResultBody(skill="listening", correct=20, total=40),
        SectionResultBody(skill="writing", clb_estimate=7),
        SectionResultBody(skill="speaking", clb_estimate=7),
    ]

    async def one(b):
        async with _Session() as s:
            return await record_section(aid, b, s, _U())

    async def run():
        await asyncio.gather(*(one(b) for b in bodies))
        async with _Session() as s:
            from app.exam.tables import ExamAttempt

            return (await s.get(ExamAttempt, aid)).sections

    sections = _run(run())
    assert sorted(sections) == ["listening", "reading", "speaking", "writing"]


def test_concurrent_finish_xp_not_multiplied():
    """qa-390: concurrent finish requests must not multiply XP — only one wins."""
    from app.exam.api import finish
    from app.progress.models import UserProgress

    aid = client.post("/exam/start", json={"blueprint_id": "mock-1"}).json()["attempt_id"]
    client.post(f"/exam/{aid}/section", json={"skill": "reading", "correct": 8, "total": 10})
    client.post(f"/exam/{aid}/section", json={"skill": "listening", "correct": 7, "total": 10})
    client.post(f"/exam/{aid}/section", json={"skill": "writing", "clb_estimate": 7})
    client.post(f"/exam/{aid}/section", json={"skill": "speaking", "clb_estimate": 6})

    # Snapshot XP before finishing
    async def get_xp():
        async with _Session() as s:
            p = await s.get(UserProgress, _U.id)
            return p.xp if p else 0

    xp_before = _run(get_xp())

    # Fire 10 concurrent finish requests
    async def one():
        async with _Session() as s:
            return await finish(aid, s, _U())

    async def run_all():
        return await asyncio.gather(*(one() for _ in range(10)), return_exceptions=True)

    results = _run(run_all())
    # All should succeed (idempotent), none should raise
    for r in results:
        assert not isinstance(r, Exception), f"unexpected error: {r}"

    xp_after = _run(get_xp())
    assert xp_after - xp_before == EXAM_XP  # exactly 25, not 250


def test_get_attempt_includes_finished_at():
    """qa-280: detail endpoint must include finished_at for completed attempts."""
    from datetime import datetime

    aid = client.post("/exam/start", json={"blueprint_id": "mock-1"}).json()["attempt_id"]

    # In-progress attempt: finished_at should be None
    detail = client.get(f"/exam/attempts/{aid}").json()
    assert "finished_at" in detail
    assert detail["finished_at"] is None

    # Complete all sections and finish
    client.post(f"/exam/{aid}/section", json={"skill": "reading", "correct": 8, "total": 10})
    client.post(f"/exam/{aid}/section", json={"skill": "listening", "correct": 7, "total": 10})
    client.post(f"/exam/{aid}/section", json={"skill": "writing", "clb_estimate": 7})
    client.post(f"/exam/{aid}/section", json={"skill": "speaking", "clb_estimate": 6})
    client.post(f"/exam/{aid}/finish")

    # Finished attempt: finished_at should be a valid ISO timestamp
    detail = client.get(f"/exam/attempts/{aid}").json()
    assert detail["finished_at"] is not None
    datetime.fromisoformat(detail["finished_at"])

    # Consistency: history endpoint should return the same value
    hist = client.get("/exam/history").json()["attempts"]
    match = [a for a in hist if a["attempt_id"] == aid][0]
    assert match["finished_at"] == detail["finished_at"]
