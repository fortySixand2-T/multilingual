"""AC1.3/1.4/1.5 — tutor level gate, drill_a1 routing, and daily budget."""
import asyncio
import tempfile
from datetime import date
from pathlib import Path

from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

import app.content.tables  # noqa: F401
import app.tutor.models  # noqa: F401
from app.ai.accounting import make_usage
from app.ai.interfaces import LLMResult
from app.api.auth import get_current_user
from app.content.loader import load_content
from app.content.sync import sync_bundle
from app.db.session import get_session
from app.main import create_app
from app.tutor.api import get_ai_router
from app.tutor.orchestrator import OVER_BUDGET_MESSAGE, Tutor
from app.users.models import Base

CONTENT_ROOT = Path(__file__).resolve().parents[1] / "content"
_DB = f"sqlite+aiosqlite:///{tempfile.mkdtemp()}/tutor.db"
_engine = create_async_engine(_DB)
_Session = async_sessionmaker(_engine, expire_on_commit=False)


def _run(coro):
    return asyncio.run(coro)


async def _setup():
    async with _engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    async with _Session() as s:
        await sync_bundle(s, load_content(CONTENT_ROOT, "a1"))


_run(_setup())


class FakeRouter:
    """Captures router.run calls; returns a canned scaffolded drill."""

    def __init__(self):
        self.calls = []

    def run(self, profile, *, system, messages, **kw):
        self.calls.append({"profile": profile, "system": system, "messages": messages})
        return LLMResult(
            text="Model: « Bonjour. » (Hello.)\nTask: change « Bonjour » to the casual greeting.",
            provider="ollama",
            model="llama3.1",
            usage=make_usage(input_tokens=120, output_tokens=40, cost_usd=0.0),
        )


# --- the level gate (no LLM, no DB) -------------------------------------------

def test_a1_prompt_forbids_open_conversation_and_free_form():
    p = Tutor(FakeRouter()).system_prompt.lower()
    assert "model" in p and "sentence" in p          # scaffolds with a model sentence
    assert "one" in p or "single" in p               # one small manipulation
    assert "not a conversation" in p or ("do not" in p and "conversation" in p)
    assert "free-form" in p or "free form" in p      # explicitly bans free production


def test_build_messages_requests_a_single_scaffolded_drill():
    system, messages = Tutor(FakeRouter()).build_messages(
        grammar_point="formal vs informal greeting", vocab=["bonjour", "salut"]
    )
    user = messages[0].content
    assert "Grammar point: formal vs informal greeting" in user
    assert "bonjour" in user and "salut" in user
    assert "exactly ONE scaffolded micro-drill" in user
    # the gate must not solicit open-ended production
    assert "conversation" not in user.lower()


def test_unsupported_level_rejected():
    try:
        Tutor(FakeRouter(), level="c1")
        raise AssertionError("expected ValueError")
    except ValueError:
        pass


# --- routing + budget (DB) ----------------------------------------------------

def test_drill_routes_through_drill_a1_profile():
    fake = FakeRouter()

    async def go():
        async with _Session() as s:
            res = await Tutor(fake).drill(
                s, user_id=100, grammar_point="g", vocab=["bonjour"], daily_budget=50000
            )
            await s.commit()
            return res

    res = _run(go())
    assert fake.calls[0]["profile"] == "drill_a1"     # AC1.4
    assert res.profile == "drill_a1"
    assert res.over_budget is False
    assert res.tokens_used_today == 160               # 120 + 40 recorded


def test_daily_budget_blocks_next_call_gracefully():
    fake = FakeRouter()

    async def go():
        async with _Session() as s:
            today = date(2026, 6, 15)
            first = await Tutor(fake).drill(
                s, user_id=200, grammar_point="g", vocab=["x"], daily_budget=100, today=today
            )
            await s.commit()
        async with _Session() as s:
            second = await Tutor(fake).drill(
                s, user_id=200, grammar_point="g", vocab=["x"], daily_budget=100, today=today
            )
            await s.commit()
        return first, second

    first, second = _run(go())
    assert first.over_budget is False                 # 160 tokens spent (> budget 100)
    assert second.over_budget is True                 # next call blocked
    assert second.text == OVER_BUDGET_MESSAGE
    assert len(fake.calls) == 1                        # no provider call when over budget


# --- HTTP endpoint with injected fake router ----------------------------------

def _make_client(fake):
    async def _override_session():
        async with _Session() as s:
            yield s

    class _U:
        id = 300

    app = create_app()
    app.dependency_overrides[get_session] = _override_session
    app.dependency_overrides[get_current_user] = lambda: _U()
    app.dependency_overrides[get_ai_router] = lambda: fake
    return TestClient(app)


def test_drill_endpoint_returns_scaffolded_drill():
    client = _make_client(FakeRouter())
    r = client.post("/tutor/drill", json={"lesson_id": "greetings-01"})
    assert r.status_code == 200
    body = r.json()
    assert body["over_budget"] is False
    assert "Model:" in body["drill"]
    assert body["provider"] == "ollama"


def test_drill_endpoint_unknown_lesson_404():
    client = _make_client(FakeRouter())
    assert client.post("/tutor/drill", json={"lesson_id": "nope"}).status_code == 404
