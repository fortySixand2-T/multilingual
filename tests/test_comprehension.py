"""Phase 2 — comprehension delivery, grading, and the audio pipeline."""

import asyncio
import tempfile
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

import app.comprehension.tables  # noqa: F401
import app.progress.models  # noqa: F401
from app.api.auth import get_current_user
from app.comprehension.api import get_storage
from app.comprehension.loader import load_sets
from app.comprehension.models import ComprehensionSet
from app.comprehension.sync import sync_comprehension, upload_audio
from app.db.session import get_session
from app.main import create_app
from app.users.models import Base

CONTENT_ROOT = Path(__file__).resolve().parents[1] / "content"
_DB = f"sqlite+aiosqlite:///{tempfile.mkdtemp()}/comp.db"
_engine = create_async_engine(_DB)
_Session = async_sessionmaker(_engine, expire_on_commit=False)


def _run(coro):
    return asyncio.run(coro)


class FakeStorage:
    name = "fake"

    def __init__(self):
        self.objects: dict[str, bytes] = {}

    def put(self, key, data, content_type="application/octet-stream"):
        self.objects[key] = data
        return f"mem://{key}"

    def get(self, key):
        return self.objects[key]

    def delete(self, key):
        self.objects.pop(key, None)

    def url(self, key):
        return f"mem://{key}"


_storage = FakeStorage()


async def _setup():
    async with _engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    async with _Session() as s:
        await sync_comprehension(s, _storage, CONTENT_ROOT, "a1")


_run(_setup())


class _FakeUser:
    id = 42


async def _override_session():
    async with _Session() as s:
        yield s


app = create_app()
app.dependency_overrides[get_session] = _override_session
app.dependency_overrides[get_current_user] = lambda: _FakeUser()
app.dependency_overrides[get_storage] = lambda: _storage
client = TestClient(app)


# --- schema / loader (no DB) --------------------------------------------------


def test_loads_example_sets():
    sets = load_sets(CONTENT_ROOT, "a1")
    assert set(sets) == {"read-cafe-01", "listen-greet-01"}
    assert sets["read-cafe-01"].skill == "reading" and sets["read-cafe-01"].passage
    assert sets["listen-greet-01"].skill == "listening" and sets["listen-greet-01"].audio_ref
    assert sets["listen-greet-01"].allow_replay is False
    assert sets["listen-greet-01"].accent == "qc"


def test_reading_without_passage_rejected():
    with pytest.raises(ValidationError):
        ComprehensionSet(
            id="x",
            level="a1",
            skill="reading",
            title="t",
            questions=[{"id": "q", "prompt": "p", "options": ["a"], "answer": "a"}],
        )


def test_question_answer_must_be_in_options():
    with pytest.raises(ValidationError):
        ComprehensionSet(
            id="x",
            level="a1",
            skill="reading",
            title="t",
            passage="p",
            questions=[{"id": "q", "prompt": "p", "options": ["a"], "answer": "z"}],
        )


# --- delivery (no answers leaked) ---------------------------------------------


def test_list_sets_filters_by_skill():
    listening = client.get(
        "/comprehension/sets", params={"level": "a1", "skill": "listening"}
    ).json()["sets"]
    assert [s["id"] for s in listening] == ["listen-greet-01"]
    assert listening[0]["allow_replay"] is False
    all_sets = client.get("/comprehension/sets", params={"level": "a1"}).json()["sets"]
    assert len(all_sets) == 2


def test_get_set_does_not_leak_answers():
    body = client.get("/comprehension/sets/read-cafe-01").json()
    assert body["passage"]
    assert body["time_limit_seconds"] == 120
    for q in body["questions"]:
        assert "answer" not in q and "explain" not in q
        assert "options" in q


def test_listening_set_exposes_audio_url_not_ref():
    body = client.get("/comprehension/sets/listen-greet-01").json()
    assert body["audio_url"] == "/comprehension/audio/listen-greet-01"
    assert body["accent"] == "qc" and body["allow_replay"] is False


# --- grading ------------------------------------------------------------------


def test_submit_grades_and_reveals_explanations():
    r = client.post(
        "/comprehension/sets/read-cafe-01/submit",
        json={
            "answers": {"read-cafe-01.q1": "Dans un café", "read-cafe-01.q2": "Non"},
            "elapsed_seconds": 40,
        },
    )
    body = r.json()
    assert body["score"] == 1.0 and body["passed"] and body["correct"] == 2
    assert body["over_time"] is False
    assert body["first_pass"] is True
    assert all(res["explain"] for res in body["results"])  # explanations revealed
    assert body["results"][0]["correct_answer"] == "Dans un café"


def test_second_pass_is_not_first_pass():
    r = client.post(
        "/comprehension/sets/read-cafe-01/submit",
        json={
            "answers": {"read-cafe-01.q1": "Dans un café", "read-cafe-01.q2": "Non"},
        },
    )
    assert r.json()["first_pass"] is False  # no double XP


def test_partial_and_over_time():
    r = client.post(
        "/comprehension/sets/read-cafe-01/submit",
        json={
            "answers": {"read-cafe-01.q1": "Au parc", "read-cafe-01.q2": "Non"},
            "elapsed_seconds": 999,
        },
    )
    body = r.json()
    assert body["correct"] == 1 and body["score"] == 0.5
    assert body["over_time"] is True


def test_concurrent_passes_award_xp_once():
    # qa-100: firing the same passing submit concurrently must award COMPREHENSION_XP once,
    # not once per request — the unique (user, set) pass marker makes the award atomic.
    from app.comprehension.api import SubmitBody, submit
    from app.progress.models import UserProgress

    class _U:
        id = 99

    answers = {"listen-greet-01.q1": "Bonjour", "listen-greet-01.q2": "Formal"}

    async def one():
        async with _Session() as s:
            return await submit(
                "listen-greet-01", SubmitBody(answers=answers, elapsed_seconds=10), s, _U()
            )

    async def run():
        results = await asyncio.gather(one(), one(), one(), one(), one())
        async with _Session() as s:
            prog = await s.get(UserProgress, 99)
        return results, (prog.xp if prog else 0)

    results, xp = _run(run())
    assert sum(r["first_pass"] for r in results) == 1  # exactly one award
    assert xp == 15  # COMPREHENSION_XP, not multiplied


def test_over_time_pass_earns_no_xp():
    # qa-040: a fully-correct but over-time run shows its score yet must not award XP
    # (first_pass False), so the shared-board XP can't be gamed by ignoring the timer.
    r = client.post(
        "/comprehension/sets/listen-greet-01/submit",
        json={
            "answers": {"listen-greet-01.q1": "Bonjour", "listen-greet-01.q2": "Formal"},
            "elapsed_seconds": 99999,
        },
    )
    body = r.json()
    assert body["passed"] is True and body["over_time"] is True
    assert body["first_pass"] is False  # no XP for an over-time run


# --- audio pipeline -----------------------------------------------------------


def test_audio_streams_from_storage():
    r = client.get("/comprehension/audio/listen-greet-01")
    assert r.status_code == 200
    assert r.headers["content-type"] == "audio/mpeg"
    assert r.content == _storage.objects["a1/audio/greet-qc.mp3"]


def test_audio_404_for_reading_set():
    assert client.get("/comprehension/audio/read-cafe-01").status_code == 404


def test_upload_audio_uses_level_prefixed_keys(tmp_path):
    (tmp_path / "a1" / "audio").mkdir(parents=True)
    (tmp_path / "a1" / "audio" / "clip.mp3").write_bytes(b"xyz")
    store = FakeStorage()
    n = upload_audio(store, tmp_path, "a1")
    assert n == 1
    assert store.objects["a1/audio/clip.mp3"] == b"xyz"
