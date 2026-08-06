"""Speaking practice API: one spoken turn (audio in → transcript + examiner reply),
the examiner's TTS audio, and turn history.

STT/TTS providers come from app.state (built from config). With speech disabled,
endpoints return a clear 503. Raw audio is read into memory, transcribed, and
discarded — never written to disk or DB (R10).
"""

from __future__ import annotations

from datetime import UTC, date, datetime

import anyio
from fastapi import (
    APIRouter,
    Depends,
    File,
    Form,
    HTTPException,
    Request,
    Response,
    UploadFile,
    status,
)
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.errors import TranscriptionError
from app.ai.router import AIRouter
from app.api.auth import get_current_user
from app.api.deps import get_ai_router, get_storage
from app.config.settings import Settings, get_settings
from app.db.session import get_session
from app.speech.examiner import SpeakingExaminer, SpeechNotConfigured
from app.speech.tables import SpeakingTopicRow, SpeechTurn
from app.speech.topics import SpeakingTopic, framing
from app.speech.vocab_review import extract_review_words, resolve_new_words, resolve_to_vocab
from app.storage.interface import ObjectStorage
from app.usage.service import add_usage, tokens_used_today
from app.users.models import User

router = APIRouter(prefix="/speech", tags=["speech"])

_HISTORY_TURNS = 3  # how many prior turns to feed back as conversation context
_MAX_AUDIO_BYTES = 10 * 1024 * 1024  # 10 MB — a spoken turn is seconds of audio, not this


async def _recent_history(session: AsyncSession, user_id: int, session_id: str = ""):
    from app.ai.interfaces import Msg

    q = select(SpeechTurn).where(SpeechTurn.user_id == user_id)
    # Scope context to the current conversation so changing topic (= new session)
    # starts fresh — prior-topic turns don't bleed into the examiner's context.
    if session_id:
        q = q.where(SpeechTurn.session_id == session_id)
    rows = (
        (await session.execute(q.order_by(SpeechTurn.id.desc()).limit(_HISTORY_TURNS)))
        .scalars()
        .all()
    )
    msgs: list[Msg] = []
    for turn in reversed(rows):  # oldest first
        msgs.append(Msg("user", turn.transcript))
        msgs.append(Msg("assistant", turn.reply_text))
    return msgs


@router.get("/topics")
async def list_topics(
    level: str,
    section: str | None = None,
    session: AsyncSession = Depends(get_session),
    user: User = Depends(get_current_user),
) -> dict:
    """Authored speaking topics for a level (optionally one section), so the learner
    can pick one to frame the session. Mirrors GET /assessment/tasks."""
    q = select(SpeakingTopicRow).where(SpeakingTopicRow.level == level)
    if section:
        q = q.where(SpeakingTopicRow.section == section)
    rows = (await session.execute(q.order_by(SpeakingTopicRow.id))).scalars().all()
    return {
        "topics": [
            {
                "id": r.id,
                "section": r.section,
                "title": r.data["title"],
                "prompt": r.data["prompt"],
                "points": r.data.get("points", []),
            }
            for r in rows
        ]
    }


@router.get("/status")
async def speech_status(request: Request) -> dict:
    """Lightweight capability check so the frontend can hide/disable the Record
    button (and skip the mic-permission prompt) before speech is even attempted,
    instead of only learning it's unconfigured after a wasted record round-trip.
    `/speech/history` always 200s regardless of STT/TTS config, so it can't be
    reused for this — this is a dedicated, no-DB-query signal.
    """
    return {"available": request.app.state.stt is not None}


@router.post("/turn")
async def speech_turn(
    request: Request,
    audio: UploadFile = File(...),
    mode: str = Form("examiner"),
    topic_id: str = Form(""),
    session_id: str = Form(""),
    session: AsyncSession = Depends(get_session),
    user: User = Depends(get_current_user),
    ai_router: AIRouter = Depends(get_ai_router),
    storage: ObjectStorage = Depends(get_storage),
    settings: Settings = Depends(get_settings),
) -> dict:
    stt = request.app.state.stt
    tts = request.app.state.tts
    if stt is None:
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, "speech is not configured")

    # Bound how much we pull into memory (reads at most the cap + 1 byte), and reject
    # an empty upload before touching the model — a clean 4xx, never a 500.
    data = await audio.read(_MAX_AUDIO_BYTES + 1)
    if len(data) > _MAX_AUDIO_BYTES:
        raise HTTPException(status.HTTP_413_REQUEST_ENTITY_TOO_LARGE, "audio upload too large")
    if not data:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "empty audio upload")

    # An optional topic focuses the session: its framing is appended to the system
    # prompt. Unknown/absent id → free conversation (no framing), never an error.
    system_extra = ""
    if topic_id:
        row = await session.get(SpeakingTopicRow, topic_id)
        if row is not None:
            system_extra = framing(SpeakingTopic.model_validate(row.data))

    examiner = SpeakingExaminer(stt, tts, ai_router)
    history = await _recent_history(session, user.id, session_id)
    try:
        result = await examiner.turn(
            session,
            user.id,
            audio=data,
            mode=mode,
            history=history,
            daily_budget=settings.speaking_daily_token_budget,
            voice=settings.piper_voice,
            system_extra=system_extra,
            max_tokens=settings.examiner_max_tokens,
            want_audio=False,  # lazy: synthesized on demand by GET /speech/audio
        )
    except SpeechNotConfigured:
        raise HTTPException(
            status.HTTP_503_SERVICE_UNAVAILABLE, "speech is not configured"
        ) from None
    except TranscriptionError:
        # Corrupt / not-audio upload — the model couldn't decode it. Nothing billed.
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_ENTITY, "could not decode the audio"
        ) from None

    if result.over_budget:
        return {"over_budget": True, "transcript": "", "reply_text": result.reply_text}

    # Silence → no transcript. The examiner already skipped the LLM/billing; reject
    # cleanly so we never persist a blank turn. (H9)
    if result.no_speech:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "no speech detected in the audio")

    turn = SpeechTurn(
        user_id=user.id,
        session_id=session_id or None,
        mode=mode,
        transcript=result.transcript,
        reply_text=result.reply_text,
        reply_audio_key=None,
        created_at=datetime.now(UTC).replace(tzinfo=None),
    )
    session.add(turn)
    await session.flush()

    # Lazy audio: don't synthesize here — advertise the audio URL whenever TTS is
    # configured and there's something to speak, and let GET /speech/audio produce
    # (and then cache) the WAV on first play. Returning the reply text without
    # waiting on synthesis is the perceived-latency win.
    reply_audio_url = (
        f"/speech/audio/{turn.id}" if tts is not None and result.reply_text.strip() else None
    )

    await session.commit()
    return {
        "turn_id": turn.id,
        "over_budget": False,
        "transcript": result.transcript,  # R1: learner sees what was transcribed
        "reply_text": result.reply_text,
        "reply_audio_url": reply_audio_url,
        "provider": result.provider,
        "model": result.model,
    }


@router.post("/session/{session_id}/vocab-review")
async def session_vocab_review(
    session_id: str,
    session: AsyncSession = Depends(get_session),
    user: User = Depends(get_current_user),
    ai_router: AIRouter = Depends(get_ai_router),
    settings: Settings = Depends(get_settings),
) -> dict:
    """End-of-conversation debrief: mine this session's transcript for French words
    worth reviewing and return the ones that map to real vocab cards (and aren't
    already in the learner's review deck). Read-only — the learner confirms which to
    add, then the client seeds them via POST /srs/add. Empty/unknown session → [].

    Re-runnable for a past session_id (transcripts persist), which is what lets a
    later slice resurface "words from your last conversation" if they skipped this."""
    rows = (
        (
            await session.execute(
                select(SpeechTurn)
                .where(SpeechTurn.user_id == user.id, SpeechTurn.session_id == session_id)
                .order_by(SpeechTurn.id)
            )
        )
        .scalars()
        .all()
    )
    if not rows:
        return {"candidates": []}

    # Same "speaking" daily ledger as /speech/turn — skip the extraction LLM entirely
    # once the day's budget is exhausted rather than billing without limit.
    used = await tokens_used_today(session, user.id, "speaking", date.today())
    if used >= settings.speaking_daily_token_budget:
        return {"candidates": [], "over_budget": True}

    words, result = await extract_review_words(ai_router, rows)
    if result is not None:
        # Bill the extraction against the same daily ledger as spoken turns.
        await add_usage(
            session,
            user.id,
            "speaking",
            result.usage.input_tokens,
            result.usage.output_tokens,
            date.today(),
        )
        await session.commit()
    candidates = await resolve_to_vocab(session, user.id, words)
    # Rich tier (Slice 3c): words the learner used that aren't in the content bank and
    # aren't already personal cards — offered for one-click enrich-and-add to their deck.
    new_words = await resolve_new_words(session, user.id, words)
    return {"candidates": candidates, "new_words": new_words}


@router.get("/last-session")
async def last_session(
    exclude: str = "",
    session: AsyncSession = Depends(get_session),
    user: User = Depends(get_current_user),
) -> dict:
    """The learner's most recent prior conversation (session_id), so the client can
    offer to resurface its review words — "words from your last conversation" — when
    they skipped the end-of-conversation review. Cheap (no LLM); pass `exclude` to
    skip the session they're currently in. None → no prior session."""
    q = select(SpeechTurn.session_id).where(
        SpeechTurn.user_id == user.id, SpeechTurn.session_id.is_not(None)
    )
    if exclude:
        q = q.where(SpeechTurn.session_id != exclude)
    sid = await session.scalar(q.order_by(SpeechTurn.id.desc()).limit(1))
    return {"session_id": sid}


@router.get("/audio/{turn_id}")
async def speech_audio(
    request: Request,
    turn_id: int,
    session: AsyncSession = Depends(get_session),
    storage: ObjectStorage = Depends(get_storage),
    user: User = Depends(get_current_user),
    settings: Settings = Depends(get_settings),
) -> Response:
    turn = await session.get(SpeechTurn, turn_id)
    if turn is None or turn.user_id != user.id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "no audio for this turn")

    # Cache hit: audio was already synthesized on a prior play — serve it.
    if turn.reply_audio_key:
        try:
            data = await anyio.to_thread.run_sync(lambda: storage.get(turn.reply_audio_key))
        except Exception:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "audio asset not found") from None
        return Response(content=data, media_type="audio/wav")

    # Cache miss: synthesize now (lazy), persist so repeat plays are instant.
    tts = request.app.state.tts
    if tts is None or not turn.reply_text.strip():
        raise HTTPException(status.HTTP_404_NOT_FOUND, "no audio for this turn")
    data = await anyio.to_thread.run_sync(
        lambda: tts.synthesize(text=turn.reply_text, voice=settings.piper_voice, lang="fr")
    )
    key = f"speech/{turn.id}.wav"
    await anyio.to_thread.run_sync(lambda: storage.put(key, data, "audio/wav"))
    turn.reply_audio_key = key
    await session.commit()
    return Response(content=data, media_type="audio/wav")


@router.get("/history")
async def speech_history(
    session: AsyncSession = Depends(get_session),
    user: User = Depends(get_current_user),
) -> dict:
    rows = (
        (
            await session.execute(
                select(SpeechTurn).where(SpeechTurn.user_id == user.id).order_by(SpeechTurn.id)
            )
        )
        .scalars()
        .all()
    )
    return {
        "turns": [
            {
                "turn_id": t.id,
                "mode": t.mode,
                "transcript": t.transcript,
                "reply_text": t.reply_text,
                "reply_audio_url": f"/speech/audio/{t.id}" if t.reply_audio_key else None,
            }
            for t in rows
        ]
    }
