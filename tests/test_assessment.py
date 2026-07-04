"""Phase 3 — writing assessment: schema, JSON parsing, grading, API, calibration."""

import asyncio
import json
import tempfile
from datetime import date
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

import app.assessment.tables  # noqa: F401
import app.usage.models  # noqa: F401
from app.ai.accounting import make_usage
from app.ai.interfaces import LLMResult
from app.api.auth import get_current_user
from app.api.deps import get_ai_router
from app.assessment.calibration import agreement, load_calibration
from app.assessment.grader import GradingError, WritingGrader, extract_json, parse_feedback
from app.assessment.loader import WritingError, load_tasks
from app.assessment.models import WritingFeedback, WritingTask
from app.assessment.sync import sync_tasks
from app.db.session import get_session
from app.main import create_app
from app.users.models import Base

CONTENT_ROOT = Path(__file__).resolve().parents[1] / "content"
_DB = f"sqlite+aiosqlite:///{tempfile.mkdtemp()}/assess.db"
_engine = create_async_engine(_DB)
_Session = async_sessionmaker(_engine, expire_on_commit=False)

_GOOD = {
    "clb_estimate": 7,
    "criteria": [{"name": "grammar", "score": 7, "comment": "solid"}],
    "corrections": [
        {
            "excerpt": "à le parc",
            "correction": "au parc",
            "explanation": "à+le=au",
            "reference": "prepositions",
        }
    ],
    "overall": "Clear and on-task.",
}


def _run(coro):
    return asyncio.run(coro)


async def _setup():
    async with _engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    async with _Session() as s:
        await sync_tasks(s, CONTENT_ROOT, "a1")


_run(_setup())


class GoodRouter:
    def __init__(self, payload=None):
        self.calls = []
        self._payload = payload or _GOOD

    def run(self, profile, *, system, messages, **kw):
        self.calls.append({"profile": profile, "kw": kw})
        return LLMResult(
            text="```json\n" + json.dumps(self._payload) + "\n```",
            provider="anthropic",
            model="claude-opus-4-8",
            usage=make_usage(input_tokens=300, output_tokens=120, cost_usd=0.02),
        )


class BadRouter:
    def run(self, profile, *, system, messages, **kw):
        return LLMResult(
            text="Sorry, I cannot produce JSON here.",
            provider="x",
            model="y",
            usage=make_usage(input_tokens=10, output_tokens=5),
        )


# --- schema -------------------------------------------------------------------


def test_clb_is_clamped():
    fb = WritingFeedback(clb_estimate=99, criteria=[], corrections=[], overall="x")
    assert fb.clb_estimate == 12
    assert (
        WritingFeedback(clb_estimate=-3, criteria=[], corrections=[], overall="x").clb_estimate == 1
    )


def test_writing_task_requires_section():
    with pytest.raises(ValidationError):
        WritingTask(id="t", level="a1", section="Z", title="t", prompt="p", min_words=10)


# --- JSON extraction / parsing ------------------------------------------------


def test_extract_json_handles_fences_and_prose():
    assert extract_json('```json\n{"a": 1}\n```') == {"a": 1}
    assert extract_json('Here you go: {"a": 2} thanks') == {"a": 2}


def test_extract_json_raises_on_garbage():
    with pytest.raises(GradingError):
        extract_json("no json at all")


def test_parse_feedback_valid():
    fb = parse_feedback("```json\n" + json.dumps(_GOOD) + "\n```")
    assert fb.clb_estimate == 7 and fb.corrections[0].reference == "prepositions"


# --- grader -------------------------------------------------------------------


def test_grade_routes_through_writing_feedback_profile():
    fake = GoodRouter()

    async def go():
        async with _Session() as s:
            res = await WritingGrader(fake).grade(
                s, 1, task_prompt="p", section="A", submission="un texte", daily_budget=100000
            )
            await s.commit()
            return res

    res = _run(go())
    assert fake.calls[0]["profile"] == "writing_feedback"
    assert fake.calls[0]["kw"]["temperature"] == 0.1  # low temp for stability (R3)
    assert res.over_budget is False and res.feedback.clb_estimate == 7
    assert res.word_count == 2


def test_grade_budget_blocks_second_call():
    fake = GoodRouter()

    async def go():
        async with _Session() as s:
            today = date(2026, 6, 15)
            first = await WritingGrader(fake).grade(
                s, 2, task_prompt="p", section="A", submission="x", daily_budget=100, today=today
            )
            await s.commit()
        async with _Session() as s:
            second = await WritingGrader(fake).grade(
                s, 2, task_prompt="p", section="A", submission="x", daily_budget=100, today=today
            )
            await s.commit()
        return first, second

    first, second = _run(go())
    assert first.over_budget is False
    assert second.over_budget is True and second.feedback is None
    assert len(fake.calls) == 1


# --- API ----------------------------------------------------------------------


def _client(router):
    async def _override_session():
        async with _Session() as s:
            yield s

    class _U:
        id = 50

    app = create_app()
    app.dependency_overrides[get_session] = _override_session
    app.dependency_overrides[get_current_user] = lambda: _U()
    app.dependency_overrides[get_ai_router] = lambda: router
    return TestClient(app)


def test_list_and_get_tasks():
    client = _client(GoodRouter())
    tasks = client.get("/assessment/tasks", params={"level": "a1"}).json()["tasks"]
    assert {"write-a-invite", "write-b-opinion"} <= {t["id"] for t in tasks}
    # the list response carries target_vocab so the UI can show it (issue 442)
    assert all("target_vocab" in t for t in tasks)
    b = client.get("/assessment/tasks", params={"level": "a1", "section": "B"}).json()["tasks"]
    b_ids = [t["id"] for t in b]
    assert "write-b-opinion" in b_ids and "write-a-invite" not in b_ids
    assert client.get("/assessment/tasks/write-a-invite").json()["section"] == "A"


def test_submit_grades_stores_and_retrieves():
    client = _client(GoodRouter())
    r = client.post(
        "/assessment/tasks/write-a-invite/submit",
        json={"text": " ".join(["Salut merci pour ton invitation et je vais bien"] * 6)},
    )
    assert r.status_code == 200
    body = r.json()
    assert body["over_budget"] is False
    assert body["feedback"]["clb_estimate"] == 7
    assert body["feedback"]["corrections"][0]["reference"] == "prepositions"
    sid = body["submission_id"]

    got = client.get(f"/assessment/submissions/{sid}")
    assert got.status_code == 200
    assert got.json()["clb_estimate"] == 7


def test_malformed_grade_is_502():
    client = _client(BadRouter())
    r = client.post(
        "/assessment/tasks/write-a-invite/submit",
        json={"text": " ".join(["du texte de test pour la soumission valide"] * 6)},
    )
    assert r.status_code == 502


def test_empty_submission_rejected():
    client = _client(GoodRouter())
    assert (
        client.post("/assessment/tasks/write-a-invite/submit", json={"text": "   "}).status_code
        == 422
    )


def test_too_few_words_rejected_before_grading():
    """qa-240: submissions below min_words must be rejected without calling the LLM."""
    fake = GoodRouter()
    c = _client(fake)
    r = c.post("/assessment/tasks/write-a-invite/submit", json={"text": "Oui merci."})
    assert r.status_code == 422
    assert "minimum" in r.json()["detail"].lower()
    assert len(fake.calls) == 0  # LLM never called


def test_too_many_words_rejected_before_grading():
    """qa-240: submissions above max_words must be rejected without calling the LLM."""
    fake = GoodRouter()
    c = _client(fake)
    long_text = " ".join(["mot"] * 200)
    r = c.post("/assessment/tasks/write-a-invite/submit", json={"text": long_text})
    assert r.status_code == 422
    assert "maximum" in r.json()["detail"].lower()
    assert len(fake.calls) == 0


# --- calibration (R3) ---------------------------------------------------------


def test_agreement_within_tolerance():
    rep = agreement([(7, 7), (4, 5), (8, 6)], tolerance=1)
    assert rep.total == 3 and rep.within == 2
    assert abs(rep.ratio - 2 / 3) < 1e-9


def test_load_calibration_reads_samples():
    samples = load_calibration(CONTENT_ROOT, "a1")
    assert len(samples) == 2
    assert {s.expected_clb for s in samples} == {4, 7}
    assert all(s.text and s.task_id for s in samples)


# --- target_vocab blend (within-level constraint) -----------------------------


def _write_level(root: Path, level: str, *, vocab_ids: list[str], target_vocab: list[str]) -> None:
    (root / level / "vocab").mkdir(parents=True)
    (root / level / "writing").mkdir(parents=True)
    cards = "\n".join(
        f"- id: {v}\n  fr: {v}\n  en: {v}\n  pos: noun\n  tags: [t]" for v in vocab_ids
    )
    (root / level / "vocab" / "deck.yaml").write_text(cards, encoding="utf-8")
    targets = ", ".join(target_vocab)
    (root / level / "writing" / "t.yaml").write_text(
        f"id: write-x\nlevel: {level}\nsection: A\ntitle: T\nprompt: p\nmin_words: 10\n"
        f"target_vocab: [{targets}]\n",
        encoding="utf-8",
    )


def test_target_vocab_in_level_loads():
    with tempfile.TemporaryDirectory() as d:
        root = Path(d)
        _write_level(root, "a1", vocab_ids=["bonjour", "merci"], target_vocab=["bonjour"])
        tasks = load_tasks(root, "a1")
        assert tasks["write-x"].target_vocab == ["bonjour"]


def test_target_vocab_out_of_level_rejected():
    """A target_vocab id absent from *this* level's vocab fails the load — this is
    what enforces the within-level constraint (a word from another level isn't here)."""
    with tempfile.TemporaryDirectory() as d:
        root = Path(d)
        _write_level(root, "a1", vocab_ids=["bonjour"], target_vocab=["ordinateur"])
        with pytest.raises(WritingError, match="ordinateur"):
            load_tasks(root, "a1")


def test_real_writing_tasks_target_vocab_within_level():
    """Authoring guard: every shipped task's target_vocab resolves in its own level."""
    for level in ("a1", "a2"):
        tasks = load_tasks(CONTENT_ROOT, level)
        assert tasks  # non-empty
        # load_tasks would have raised on any out-of-level id; assert the blend exists.
        assert any(t.target_vocab for t in tasks.values())


def test_grader_includes_target_words_when_present():
    system, msgs = WritingGrader(GoodRouter()).build_messages(
        task_prompt="p", section="A", submission="s", target_vocab_fr=["soleil", "pluie"]
    )
    assert "soleil, pluie" in msgs[0].content
    assert "Target vocabulary" in msgs[0].content


def test_grader_prompt_unchanged_without_target_words():
    grader = WritingGrader(GoodRouter())
    _, with_empty = grader.build_messages(task_prompt="p", section="A", submission="s")
    _, with_none = grader.build_messages(
        task_prompt="p", section="A", submission="s", target_vocab_fr=[]
    )
    assert with_empty[0].content == with_none[0].content
    assert "Target vocabulary" not in with_empty[0].content
