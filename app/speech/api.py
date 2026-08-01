"""Speaking practice API: one spoken turn (audio in → transcript + examiner reply),
the examiner's TTS audio, and turn history.

STT/TTS providers come from app.state (built from config). With speech disabled,
endpoints return a clear 503. Raw audio is read into memory, transcribed, and
discarded — never written to disk or DB (R10).
"""

from __future__ import annotations

from datetime import UTC, datetime

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
from app.storage.interface import ObjectStorage
from app.users.models import User

router = APIRouter(prefix="/speech", tags=["speech"])

_HISTORY_TURNS = 3  # how many prior turns to feed back as conversation context
_MAX_AUDIO_BYTES = 10 * 1024 * 1024  # 10 MB — a spoken turn is seconds of audio, not this


async def _recent_history(session: AsyncSession, user_id: int):
    from app.ai.interfaces import Msg

    rows = (
        (
            await session.execute(
                select(SpeechTurn)
                .where(SpeechTurn.user_id == user_id)
                .order_by(SpeechTurn.id.desc())
                .limit(_HISTORY_TURNS)
            )
        )
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
    history = await _recent_history(session, user.id)
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
        mode=mode,
        transcript=result.transcript,
        reply_text=result.reply_text,
        reply_audio_key=None,
        created_at=datetime.now(UTC).replace(tzinfo=None),
    )
    session.add(turn)
    await session.flush()

    reply_audio_url = None
    if result.reply_audio:
        key = f"speech/{turn.id}.wav"
        await anyio.to_thread.run_sync(lambda: storage.put(key, result.reply_audio, "audio/wav"))
        turn.reply_audio_key = key
        reply_audio_url = f"/speech/audio/{turn.id}"

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


@router.get("/audio/{turn_id}")
async def speech_audio(
    turn_id: int,
    session: AsyncSession = Depends(get_session),
    storage: ObjectStorage = Depends(get_storage),
    user: User = Depends(get_current_user),
) -> Response:
    turn = await session.get(SpeechTurn, turn_id)
    if turn is None or turn.user_id != user.id or not turn.reply_audio_key:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "no audio for this turn")
    try:
        data = await anyio.to_thread.run_sync(lambda: storage.get(turn.reply_audio_key))
    except Exception:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "audio asset not found") from None
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
