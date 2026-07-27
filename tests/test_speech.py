"""Phase 4 — speaking loop: transcribe -> examiner -> TTS, honoring R1/R2/R10."""

import asyncio
import tempfile
from datetime import date

from fastapi.testclient import TestClient
from sqlalchemy import select
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
from app.speech.tables import SpeechTurn
from app.users.models import Base

_DB = f"sqlite+aiosqlite:///{tempfile.mkdtemp()}/speech.db"
_engine = create_async_engine(_DB)
_Session = async_sessionmaker(_engine, expire_on_commit=False)


def _run(coro):
    return asyncio.run(coro)


async def _create():
    async with _engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


_run(_create())


class FakeSTT:
    name = "fake-stt"

    def __init__(self):
        self.calls = 0

    def transcribe(self, *, audio, lang="fr"):
        self.calls += 1
        return Transcript(text="Je voudrais un café, s'il vous plaît.", provider=self.name)


class FakeTTS:
    name = "fake-tts"

    def synthesize(self, *, text, voice="", lang="fr"):
        return b"RIFFfakewavbytes"


class FakeRouter:
    def __init__(self):
        self.calls = []

    def run(self, profile, *, system, messages, **kw):
        self.calls.append({"profile": profile, "system": system, "messages": messages})
        return LLMResult(
            text="Très bien ! Et qu'est-ce que vous aimez boire le matin ?",
            provider="ollama",
            model="llama3.1",
            usage=make_usage(input_tokens=80, output_tokens=30),
        )


class FakeStorage:
    name = "fake"

    def __init__(self):
        self.objects = {}

    def put(self, key, data, content_type="application/octet-stream"):
        self.objects[key] = data
        return f"mem://{key}"

    def get(self, key):
        return self.objects[key]

    def delete(self, key):
        self.objects.pop(key, None)

    def url(self, key):
        return f"mem://{key}"


# --- examiner orchestration (no HTTP) -----------------------------------------


def test_prompt_excludes_pronunciation_and_uses_transcript():
    p = SpeakingExaminer(FakeSTT(), FakeTTS(), FakeRouter()).system_prompt("examiner").lower()
    assert "transcript" in p
    assert "pronunciation" in p and ("do not" in p or "never" in p)  # R2
    assert "content" in p


def test_turn_returns_transcript_and_reply_and_records_usage():
    fake_router = FakeRouter()

    async def go():
        async with _Session() as s:
            res = await SpeakingExaminer(FakeSTT(), FakeTTS(), fake_router).turn(
                s, 1, audio=b"audio-bytes", daily_budget=100000
            )
            await s.commit()
            return res

    res = _run(go())
    assert res.over_budget is False
    assert res.transcript.startswith("Je voudrais")  # R1: transcript surfaced
    assert "?" in res.reply_text
    assert res.reply_audio == b"RIFFfakewavbytes"
    assert fake_router.calls[0]["profile"] == "examiner_roleplay"


def test_budget_blocks_without_calling_stt():
    stt = FakeSTT()

    async def go():
        async with _Session() as s:
            today = date(2026, 6, 16)
            await SpeakingExaminer(stt, FakeTTS(), FakeRouter()).turn(
                s, 7, audio=b"x", daily_budget=100, today=today
            )
            await s.commit()
        async with _Session() as s:
            second = await SpeakingExaminer(stt, FakeTTS(), FakeRouter()).turn(
                s, 7, audio=b"x", daily_budget=100, today=today
            )
            await s.commit()
        return second

    second = _run(go())
    assert second.over_budget is True
    assert stt.calls == 1  # second turn never transcribed


# --- HTTP + R10 (no raw audio stored) -----------------------------------------


def _client(*, stt=None, tts=None, uid=99, router=None):
    storage = FakeStorage()

    async def _override_session():
        async with _Session() as s:
            yield s

    class _U:
        id = uid

    app = create_app()
    app.state.stt = stt
    app.state.tts = tts
    app.dependency_overrides[get_session] = _override_session
    app.dependency_overrides[get_current_user] = lambda: _U()
    app.dependency_overrides[get_ai_router] = lambda: router or FakeRouter()
    app.dependency_overrides[get_storage] = lambda: storage
    return TestClient(app), storage


def test_turn_endpoint_stores_transcript_not_audio_and_serves_reply():
    client, storage = _client(stt=FakeSTT(), tts=FakeTTS())
    r = client.post(
        "/speech/turn",
        files={"audio": ("a.wav", b"rawaudio", "audio/wav")},
        data={"mode": "examiner"},
    )
    assert r.status_code == 200
    body = r.json()
    assert body["transcript"].startswith("Je voudrais")
    assert body["reply_audio_url"] == f"/speech/audio/{body['turn_id']}"

    # R10: stored turn has the transcript, never the uploaded audio bytes
    async def check():
        async with _Session() as s:
            turn = (
                await s.execute(select(SpeechTurn).where(SpeechTurn.id == body["turn_id"]))
            ).scalar_one()
            return turn

    turn = _run(check())
    assert turn.transcript and turn.reply_text
    assert b"rawaudio" not in (
        storage.objects.get(turn.reply_audio_key) or b""
    )  # only TTS reply stored
    assert storage.objects[turn.reply_audio_key] == b"RIFFfakewavbytes"

    # examiner audio is served back
    audio = client.get(body["reply_audio_url"])
    assert audio.status_code == 200 and audio.headers["content-type"] == "audio/wav"


def test_history_grows_and_feeds_back():
    client, _ = _client(stt=FakeSTT(), tts=None, uid=100)
    client.post("/speech/turn", files={"audio": ("a.wav", b"one", "audio/wav")})
    client.post("/speech/turn", files={"audio": ("a.wav", b"two", "audio/wav")})
    hist = client.get("/speech/history").json()["turns"]
    assert len(hist) == 2
    assert all(t["transcript"] for t in hist)


def test_speech_disabled_returns_503():
    client, _ = _client(stt=None, tts=None)
    r = client.post("/speech/turn", files={"audio": ("a.wav", b"x", "audio/wav")})
    assert r.status_code == 503


# --- input hardening (H9): bad audio must 4xx cleanly, never 500 or a billed turn ---


class RaisingSTT:
    """Stands in for whisper failing to decode a corrupt / non-audio upload."""

    name = "raising-stt"

    def transcribe(self, *, audio, lang="fr"):
        from app.ai.errors import TranscriptionError

        raise TranscriptionError("bad audio")


class SilentSTT:
    """Decodes fine but there's no speech — an empty transcript."""

    name = "silent-stt"

    def transcribe(self, *, audio, lang="fr"):
        return Transcript(text="   ", provider=self.name)  # whitespace only


class BoomRouter:
    """Fails the test if the LLM is invoked (it must not be, on empty/bad input)."""

    def run(self, *a, **k):
        raise AssertionError("the LLM must not be called for empty/undecodable audio")


def test_empty_upload_rejected_400():
    client, _ = _client(stt=FakeSTT(), tts=FakeTTS(), router=BoomRouter())
    r = client.post("/speech/turn", files={"audio": ("a.wav", b"", "audio/wav")})
    assert r.status_code == 400


def test_oversized_upload_rejected_413():
    client, _ = _client(stt=FakeSTT(), tts=FakeTTS(), router=BoomRouter())
    big = b"x" * (10 * 1024 * 1024 + 5)
    r = client.post("/speech/turn", files={"audio": ("a.wav", big, "audio/wav")})
    assert r.status_code == 413


def test_undecodable_audio_returns_422_not_500():
    client, _ = _client(stt=RaisingSTT(), tts=FakeTTS(), router=BoomRouter())
    r = client.post(
        "/speech/turn",
        files={"audio": ("a.bin", b"not really audio", "application/octet-stream")},
    )
    assert r.status_code == 422  # not 500, and BoomRouter proves the LLM wasn't called


def test_empty_transcript_returns_422_without_billing_or_saving_a_turn():
    client, _ = _client(stt=SilentSTT(), tts=FakeTTS(), uid=123, router=BoomRouter())
    r = client.post("/speech/turn", files={"audio": ("a.wav", b"silence", "audio/wav")})
    assert r.status_code == 422  # BoomRouter (not called) proves no LLM turn was billed

    async def count():
        async with _Session() as s:
            rows = (
                (await s.execute(select(SpeechTurn).where(SpeechTurn.user_id == 123)))
                .scalars()
                .all()
            )
            return len(rows)

    assert _run(count()) == 0  # no blank turn persisted
