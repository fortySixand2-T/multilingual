"""Speaking latency levers: STT device/compute wiring + examiner reply-length cap.

These are unit-level (no real Whisper model is loaded — the adapter is stubbed),
so they run in CI without the heavy speech deps.
"""

from __future__ import annotations

import asyncio
import tempfile
from types import SimpleNamespace

from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

import app.speech.tables  # noqa: F401
import app.usage.models  # noqa: F401
from app.ai.accounting import make_usage
from app.ai.interfaces import LLMResult, Transcript
from app.api.auth import get_current_user
from app.api.deps import get_ai_router, get_storage
from app.db.session import get_session
from app.main import create_app
from app.speech.examiner import SpeakingExaminer
from app.speech.factory import build_stt
from app.users.models import Base

_DB = f"sqlite+aiosqlite:///{tempfile.mkdtemp()}/speed.db"
_engine = create_async_engine(_DB)
_Session = async_sessionmaker(_engine, expire_on_commit=False)


def _run(coro):
    return asyncio.run(coro)


async def _create():
    async with _engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


_run(_create())


def test_build_stt_forwards_device_and_compute_type(monkeypatch):
    captured = {}

    class _StubWhisper:
        def __init__(self, *, model, device, compute_type):
            captured.update(model=model, device=device, compute_type=compute_type)

    monkeypatch.setattr("app.ai.adapters.faster_whisper_adapter.FasterWhisperAdapter", _StubWhisper)
    settings = SimpleNamespace(
        stt_backend="faster-whisper",
        whisper_model="small",
        whisper_device="cuda",
        whisper_compute_type="float16",
    )
    build_stt(settings)
    assert captured == {"model": "small", "device": "cuda", "compute_type": "float16"}


def test_build_stt_disabled_returns_none():
    assert build_stt(SimpleNamespace(stt_backend="disabled")) is None


class _FakeSTT:
    name = "fake"

    def transcribe(self, *, audio, lang="fr"):
        return Transcript(text="Bonjour.", provider=self.name)


class _CapRouter:
    def __init__(self):
        self.max_tokens = None

    def run(self, profile, *, system, messages, max_tokens=1024, **kw):
        self.max_tokens = max_tokens
        return LLMResult(
            text="Et vous ?",
            provider="ollama",
            model="llama3.1",
            usage=make_usage(input_tokens=5, output_tokens=3),
        )


def test_examiner_forwards_max_tokens_to_router():
    router = _CapRouter()

    async def go():
        async with _Session() as s:
            await SpeakingExaminer(_FakeSTT(), None, router).turn(
                s, 1, audio=b"x", daily_budget=100000, want_audio=False, max_tokens=220
            )
            await s.commit()

    _run(go())
    assert router.max_tokens == 220


def test_examiner_defaults_max_tokens_when_unset():
    router = _CapRouter()

    async def go():
        async with _Session() as s:
            await SpeakingExaminer(_FakeSTT(), None, router).turn(
                s, 2, audio=b"x", daily_budget=100000, want_audio=False
            )
            await s.commit()

    _run(go())
    assert router.max_tokens == 1024  # unchanged default when caller doesn't cap


def test_turn_endpoint_caps_reply_with_examiner_max_tokens_setting():
    router = _CapRouter()

    async def _override_session():
        async with _Session() as s:
            yield s

    class _U:
        id = 77

    class _Storage:
        def put(self, key, data, content_type="application/octet-stream"):
            return f"mem://{key}"

        def get(self, key):
            return b""

    app = create_app()
    app.state.stt = _FakeSTT()
    app.state.tts = None
    app.dependency_overrides[get_session] = _override_session
    app.dependency_overrides[get_current_user] = lambda: _U()
    app.dependency_overrides[get_ai_router] = lambda: router
    app.dependency_overrides[get_storage] = lambda: _Storage()

    client = TestClient(app)
    r = client.post("/speech/turn", files={"audio": ("a.wav", b"x", "audio/wav")})
    assert r.status_code == 200
    # default Settings.examiner_max_tokens (220) flows through the endpoint
    assert router.max_tokens == 220
