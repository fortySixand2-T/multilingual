"""Phase 5 — exam simulation: CLB mapping, blueprint loading, and the mock flow."""
import asyncio
import tempfile
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

import app.exam.tables  # noqa: F401
from app.api.auth import get_current_user
from app.db.session import get_session
from app.exam.clb import aggregate_report, clb_from_fraction
from app.exam.loader import load_blueprints
from app.exam.models import ExamSection
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


# --- full mock flow over HTTP -------------------------------------------------

def test_full_mock_start_sections_finish_history():
    bps = client.get("/exam/blueprints", params={"level": "a1"}).json()["blueprints"]
    assert bps[0]["id"] == "mock-1" and bps[0]["sections"] == 4

    aid = client.post("/exam/start", json={"blueprint_id": "mock-1"}).json()["attempt_id"]

    client.post(f"/exam/{aid}/section", json={"skill": "reading", "correct": 8, "total": 10})    # 0.8 -> 8
    client.post(f"/exam/{aid}/section", json={"skill": "listening", "correct": 7, "total": 10})  # ->7
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


def test_section_validation_and_finished_guard():
    aid = client.post("/exam/start", json={"blueprint_id": "mock-1"}).json()["attempt_id"]
    # comprehension needs correct+total
    assert client.post(f"/exam/{aid}/section", json={"skill": "reading"}).status_code == 422
    # writing needs clb
    assert client.post(f"/exam/{aid}/section", json={"skill": "writing"}).status_code == 422
    client.post(f"/exam/{aid}/finish")
    # can't record after finishing
    assert client.post(f"/exam/{aid}/section", json={"skill": "writing", "clb_estimate": 7}).status_code == 409


def test_start_unknown_blueprint_404():
    assert client.post("/exam/start", json={"blueprint_id": "nope"}).status_code == 404
