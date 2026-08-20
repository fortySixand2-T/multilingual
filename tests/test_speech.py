"""Phase 4 — speaking loop: transcribe -> examiner -> TTS, honoring R1/R2/R10."""

import asyncio
import tempfile
from datetime import date

from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

import app.content.tables  # noqa: F401  (register content_vocab for create_all)
import app.speech.tables  # noqa: F401
import app.srs.models  # noqa: F401  (register srs_cards for create_all)
import app.usage.models  # noqa: F401
from app.ai.accounting import make_usage
from app.ai.interfaces import LLMResult, Transcript
from app.api.auth import get_current_user
from app.api.deps import get_ai_router, get_storage
from app.db.session import get_session
from app.main import create_app
from app.speech.examiner import SpeakingExaminer
from app.speech.tables import SpeakingTopicRow, SpeechTurn
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

    def __init__(self):
        self.calls = 0

    def synthesize(self, *, text, voice="", lang="fr"):
        self.calls += 1
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


def _add_topic(tid, *, level="a1", section="A", title="T", prompt="Parlez-en", points=None):
    async def go():
        async with _Session() as s:
            s.add(
                SpeakingTopicRow(
                    id=tid,
                    level=level,
                    section=section,
                    data={
                        "id": tid,
                        "level": level,
                        "section": section,
                        "title": title,
                        "prompt": prompt,
                        "points": points or [],
                    },
                )
            )
            await s.commit()

    _run(go())


def test_turn_endpoint_stores_transcript_not_audio_and_serves_reply():
    tts = FakeTTS()
    client, storage = _client(stt=FakeSTT(), tts=tts)
    r = client.post(
        "/speech/turn",
        files={"audio": ("a.wav", b"rawaudio", "audio/wav")},
        data={"mode": "examiner"},
    )
    assert r.status_code == 200
    body = r.json()
    assert body["transcript"].startswith("Je voudrais")
    assert body["reply_audio_url"] == f"/speech/audio/{body['turn_id']}"

    # Lazy audio: the POST does NOT synthesize — nothing stored, TTS untouched yet.
    assert tts.calls == 0
    assert storage.objects == {}

    async def get_turn():
        async with _Session() as s:
            return (
                await s.execute(select(SpeechTurn).where(SpeechTurn.id == body["turn_id"]))
            ).scalar_one()

    turn = _run(get_turn())
    assert turn.transcript and turn.reply_text
    assert turn.reply_audio_key is None  # not synthesized at POST time

    # First play synthesizes on demand and serves audio/wav...
    audio = client.get(body["reply_audio_url"])
    assert audio.status_code == 200 and audio.headers["content-type"] == "audio/wav"
    assert audio.content == b"RIFFfakewavbytes"
    assert tts.calls == 1

    # ...and caches it: the turn now has a key, storage holds only the TTS reply
    # (never the uploaded audio — R10), and a second play is served from cache.
    turn = _run(get_turn())
    assert turn.reply_audio_key
    assert storage.objects[turn.reply_audio_key] == b"RIFFfakewavbytes"
    assert all(b"rawaudio" not in v for v in storage.objects.values())
    client.get(body["reply_audio_url"])
    assert tts.calls == 1  # cached — not re-synthesized


def test_turn_without_tts_advertises_no_audio_and_audio_404s():
    client, _ = _client(stt=FakeSTT(), tts=None, uid=101)
    body = client.post("/speech/turn", files={"audio": ("a.wav", b"x", "audio/wav")}).json()
    assert body["reply_audio_url"] is None  # nothing to play without TTS
    r = client.get(f"/speech/audio/{body['turn_id']}")
    assert r.status_code == 404  # no key, and no TTS to synthesize one


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


# --- examiner opener: the agent speaks first on a fresh session --------------


def test_opener_returns_reply_and_persists_empty_transcript_turn():
    client, _ = _client(stt=FakeSTT(), tts=FakeTTS(), uid=300)
    r = client.post("/speech/opener", data={"mode": "conversation", "session_id": "s-open"})
    assert r.status_code == 200
    body = r.json()
    assert body["over_budget"] is False
    assert "?" in body["reply_text"]  # opens with a question to invite the learner
    assert body["reply_audio_url"] == f"/speech/audio/{body['turn_id']}"
    # Persisted as a turn with no learner utterance so it shows in history.
    hist = client.get("/speech/history").json()["turns"]
    assert len(hist) == 1
    assert hist[0]["transcript"] == ""
    assert hist[0]["reply_text"] == body["reply_text"]


def test_topic_opener_directs_the_model_to_start_the_conversation():
    router = FakeRouter()
    client, _ = _client(stt=FakeSTT(), tts=None, uid=301, router=router)
    _add_topic("t-op-301")
    client.post(
        "/speech/opener",
        data={"mode": "conversation", "topic_id": "t-op-301", "session_id": "s"},
    )
    # A topic opener adds a start directive + the topic framing, and sends only a
    # stage-direction cue (no learner audio), so the model produces the first line.
    call = router.calls[0]
    assert "start the conversation" in call["system"].lower()
    assert "expression orale" in call["system"].lower()  # topic framing applied
    assert len(call["messages"]) == 1 and call["messages"][0].role == "user"


def test_free_conversation_opener_is_canned_and_never_calls_the_llm():
    tts = FakeTTS()
    # BoomRouter raises if the LLM is invoked — the free-conversation opener must not.
    client, _ = _client(stt=FakeSTT(), tts=tts, uid=310, router=BoomRouter())
    r1 = client.post("/speech/opener", data={"mode": "conversation", "session_id": "s1"})
    r2 = client.post("/speech/opener", data={"mode": "conversation", "session_id": "s2"})
    b1, b2 = r1.json(), r2.json()
    assert b1["over_budget"] is False and b1["reply_text"]
    assert b1["reply_text"] == b2["reply_text"]  # same canned greeting every session
    # Audio is synthesized once and shared across sessions (cached by mode).
    assert tts.calls == 1
    assert b1["reply_audio_url"] and b2["reply_audio_url"]
    audio = client.get(b1["reply_audio_url"])
    assert audio.status_code == 200 and audio.content == b"RIFFfakewavbytes"
    assert tts.calls == 1  # serving the cached clip doesn't re-synthesize


def test_canned_opener_persists_empty_transcript_turn():
    client, _ = _client(stt=FakeSTT(), tts=FakeTTS(), uid=311, router=BoomRouter())
    client.post("/speech/opener", data={"mode": "conversation", "session_id": "s"})
    hist = client.get("/speech/history").json()["turns"]
    assert len(hist) == 1 and hist[0]["transcript"] == ""


def test_opener_then_turn_feeds_greeting_back_without_blank_user_message():
    router = FakeRouter()
    client, _ = _client(stt=FakeSTT(), tts=None, uid=302, router=router)
    client.post("/speech/opener", data={"mode": "conversation", "session_id": "s"})
    client.post(
        "/speech/turn",
        data={"mode": "conversation", "session_id": "s"},
        files={"audio": ("a.wav", b"reply", "audio/wav")},
    )
    # The turn's context includes the opener as an assistant message, but the empty
    # opener transcript must not leak in as a blank user message.
    turn_msgs = router.calls[-1]["messages"]
    assert any(m.role == "assistant" for m in turn_msgs)
    assert all(m.content.strip() for m in turn_msgs if m.role == "user")


def test_opener_over_budget_skips_the_llm():
    router = FakeRouter()

    async def go():
        today = date(2026, 6, 20)
        async with _Session() as s:
            await SpeakingExaminer(FakeSTT(), FakeTTS(), FakeRouter()).turn(
                s, 44, audio=b"x", daily_budget=100, today=today
            )
            await s.commit()
        async with _Session() as s:
            res = await SpeakingExaminer(FakeSTT(), FakeTTS(), router).opener(
                s, 44, daily_budget=100, today=today
            )
            await s.commit()
            return res

    res = _run(go())
    assert res.over_budget is True
    assert router.calls == []  # over-budget opener never bills the LLM


def test_opener_speech_disabled_returns_503():
    client, _ = _client(stt=None, tts=None)
    r = client.post("/speech/opener", data={"mode": "conversation", "session_id": "s"})
    assert r.status_code == 503


# --- capability preflight (qa-540): let the frontend know before requesting mic ---


def test_speech_status_reports_unavailable_when_stt_not_configured():
    client, _ = _client(stt=None, tts=None)
    r = client.get("/speech/status")
    assert r.status_code == 200
    assert r.json() == {"available": False}


def test_speech_status_reports_available_when_stt_configured():
    client, _ = _client(stt=FakeSTT(), tts=FakeTTS())
    r = client.get("/speech/status")
    assert r.status_code == 200
    assert r.json() == {"available": True}


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


# --- Slice 3a: end-of-conversation vocab review (Speaking -> SRS loop) ---------

from app.content.tables import ContentVocab  # noqa: E402
from app.speech.vocab_review import _norm, _parse_words  # noqa: E402
from app.srs.models import ReviewCard  # noqa: E402


class JsonRouter:
    """Extraction model: returns a strict-JSON word list (what vocab_extract asks for)."""

    def __init__(self, words):
        self._words = words

    def run(self, profile, *, system, messages, **kw):
        import json

        return LLMResult(
            text=json.dumps({"words": self._words}),
            provider="ollama",
            model="llama3.1",
            usage=make_usage(input_tokens=40, output_tokens=10),
        )


async def _seed_vocab(cards):
    async with _Session() as s:
        for cid, fr, en, level in cards:
            s.add(ContentVocab(id=cid, level=level, data={"fr": fr, "en": en}))
        await s.commit()


def test_parse_words_tolerates_fences_and_shapes():
    assert _parse_words('{"words": ["café", "eau"]}') == ["café", "eau"]
    assert _parse_words('```json\n{"words": ["thé"]}\n```') == ["thé"]
    assert _parse_words('["pain", "vin"]') == ["pain", "vin"]  # bare list
    assert _parse_words("not json at all") == []


def test_norm_strips_articles_and_case():
    assert _norm("Le café") == "café"
    assert _norm("l'eau") == "eau"
    assert _norm("  VIN.  ") == "vin"


def test_vocab_review_suggests_known_words_from_the_session():
    _run(_seed_vocab([("cafe", "café", "coffee", "a1"), ("eau", "eau", "water", "a1")]))
    router = JsonRouter(["café", "eau", "montréal"])  # montréal has no vocab card -> dropped
    client, _ = _client(stt=FakeSTT(), tts=None, uid=201, router=router)

    sid = "sess-201"
    client.post(
        "/speech/turn",
        files={"audio": ("a.wav", b"x", "audio/wav")},
        data={"mode": "examiner", "session_id": sid},
    )
    r = client.post(f"/speech/session/{sid}/vocab-review")
    assert r.status_code == 200
    keys = {c["card_key"] for c in r.json()["candidates"]}
    assert keys == {"cafe", "eau"}  # only lemmas resolving to real vocab ids


def test_vocab_review_excludes_words_already_in_review():
    _run(_seed_vocab([("pain", "pain", "bread", "a1")]))

    async def already_reviewing():
        async with _Session() as s:
            from datetime import UTC, datetime

            due = datetime.now(UTC).replace(tzinfo=None)
            s.add(ReviewCard(user_id=202, card_key="pain", due=due, state={}))
            await s.commit()

    _run(already_reviewing())
    client, _ = _client(stt=FakeSTT(), tts=None, uid=202, router=JsonRouter(["pain"]))
    sid = "sess-202"
    client.post(
        "/speech/turn",
        files={"audio": ("a.wav", b"x", "audio/wav")},
        data={"mode": "examiner", "session_id": sid},
    )
    r = client.post(f"/speech/session/{sid}/vocab-review")
    assert r.json()["candidates"] == []  # already in the deck -> not re-suggested


def test_vocab_review_empty_for_unknown_session_makes_no_llm_call():
    # BoomRouter proves we never invoke the model when the session has no turns.
    client, _ = _client(stt=FakeSTT(), tts=None, uid=203, router=BoomRouter())
    r = client.post("/speech/session/does-not-exist/vocab-review")
    assert r.status_code == 200
    assert r.json() == {"candidates": []}


def test_vocab_review_new_words_rich_tier():
    # Slice 3c: words used but NOT in the content bank (and not already a personal card)
    # come back as `new_words` for one-click enrich-and-add; content words go to
    # `candidates`, and an already-owned personal card is excluded.
    from app.content.tables import UserVocab

    _run(_seed_vocab([("miel", "miel", "honey", "a1")]))  # unique id (not seeded elsewhere)

    async def own_personal():
        async with _Session() as s:
            s.add(UserVocab(user_id=204, card_key="uv:flaner", fr="flâner", en="to stroll"))
            await s.commit()

    _run(own_personal())
    # miel -> content candidate; flâner -> already owned (excluded); dépaysement -> new
    router = JsonRouter(["miel", "flâner", "dépaysement"])
    client, _ = _client(stt=FakeSTT(), tts=None, uid=204, router=router)
    sid = "sess-204"
    client.post(
        "/speech/turn",
        files={"audio": ("a.wav", b"x", "audio/wav")},
        data={"mode": "examiner", "session_id": sid},
    )
    body = client.post(f"/speech/session/{sid}/vocab-review").json()
    assert {c["card_key"] for c in body["candidates"]} == {"miel"}
    assert body["new_words"] == ["dépaysement"]  # not in bank, not already owned


def test_vocab_review_over_budget_skips_llm_and_stops_billing():
    # qa-580: once the "speaking" daily ledger is at/over the budget, vocab-review
    # must not call the extraction LLM (or bill further) — same gate as /speech/turn.
    from app.config.settings import get_settings
    from app.usage.models import DailyUsage

    _run(_seed_vocab([("cafe-580", "café", "coffee", "a1")]))
    sid = "sess-580"

    # Seed a turn (with budget untouched, via a plain FakeRouter) so the review has
    # a real transcript to work with — before we exhaust the ledger below.
    seed_client, _ = _client(stt=FakeSTT(), tts=None, uid=580, router=FakeRouter())
    seed_client.post(
        "/speech/turn",
        files={"audio": ("a.wav", b"x", "audio/wav")},
        data={"mode": "examiner", "session_id": sid},
    )

    async def exhaust_budget():
        async with _Session() as s:
            row = await s.get(DailyUsage, (580, date.today(), "speaking"))
            budget = get_settings().speaking_daily_token_budget
            row.input_tokens = budget
            row.output_tokens = 0
            await s.commit()

    _run(exhaust_budget())

    # Now vocab-review must not touch the LLM at all — BoomRouter raises if it does.
    client, _ = _client(stt=FakeSTT(), tts=None, uid=580, router=BoomRouter())
    r = client.post(f"/speech/session/{sid}/vocab-review")
    assert r.status_code == 200
    assert r.json() == {"candidates": [], "over_budget": True}
    # BoomRouter would have raised AssertionError had extract_review_words run it.

    async def usage_row():
        async with _Session() as s:
            return await s.get(DailyUsage, (580, date.today(), "speaking"))

    row = _run(usage_row())
    budget = get_settings().speaking_daily_token_budget
    assert row.input_tokens + row.output_tokens == budget  # unchanged — nothing re-billed


def test_last_session_returns_most_recent_prior_excluding_current():
    client, _ = _client(stt=FakeSTT(), tts=None, uid=206)
    for sid in ("s1", "s2"):  # s2 posted last -> most recent
        client.post(
            "/speech/turn",
            files={"audio": ("a.wav", b"x", "audio/wav")},
            data={"mode": "examiner", "session_id": sid},
        )
    # No exclude -> the latest conversation.
    assert client.get("/speech/last-session").json()["session_id"] == "s2"
    # Excluding the current (s2) -> the one before it.
    assert client.get("/speech/last-session?exclude=s2").json()["session_id"] == "s1"


def test_last_session_null_when_no_prior_conversation():
    client, _ = _client(stt=FakeSTT(), tts=None, uid=207)
    assert client.get("/speech/last-session").json()["session_id"] is None


def test_session_id_scopes_history_and_persists_on_turn():
    client, _ = _client(stt=FakeSTT(), tts=None, uid=204)
    body = client.post(
        "/speech/turn",
        files={"audio": ("a.wav", b"x", "audio/wav")},
        data={"mode": "examiner", "session_id": "sess-204"},
    ).json()

    async def get_turn():
        async with _Session() as s:
            return (
                await s.execute(select(SpeechTurn).where(SpeechTurn.id == body["turn_id"]))
            ).scalar_one()

    assert _run(get_turn()).session_id == "sess-204"
