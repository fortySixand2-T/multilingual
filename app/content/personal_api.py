"""Personal vocab deck API (Slice E): preview an enrichment, add a card, list "My
deck", and serve a card's pronunciation (synthesized lazily).

The add flow is two steps so the learner confirms before anything is stored:
  POST /vocab/personal/preview  {word}      -> {fr,en,pos,gender,ipa,audio_url}
  POST /vocab/personal          {fr,en,...}  -> stores the card + seeds its SRS review

Lookups are cached durably and shared (`vocab_lookup`, see app/content/lookup.py), so a
repeat lookup is a DB read and an added card reuses the lookup's pronunciation clip.

Personal cards then appear in the normal review queue (/srs/queue routes `uv:` keys to
the user_vocab table) and ride the same FSRS loop as content cards.
"""

from __future__ import annotations

from datetime import date

import anyio
from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.router import AIRouter
from app.api.auth import get_current_user
from app.api.deps import get_ai_router, get_storage
from app.config.settings import Settings, get_settings
from app.content.enrich import GenderTable
from app.content.lookup import cached_lookup, fresh_lookup, lookup_payload
from app.content.personal import (
    EmptyLemmaError,
    add_personal,
    card_payload,
    get_personal,
    list_personal,
    slugify,
)
from app.content.tables import UserVocab, VocabLookup
from app.db.session import get_session
from app.speech.vocab_review import find_content_match
from app.srs.service import seed_cards
from app.storage.interface import ObjectStorage
from app.usage.service import add_usage, tokens_used_today
from app.users.models import User

router = APIRouter(prefix="/vocab/personal", tags=["personal-vocab"])

# The gender table is process-wide and read-only — load once, not per request.
_GENDER_TABLE = GenderTable.load()


class PreviewBody(BaseModel):
    word: str = Field(min_length=1, max_length=80)


class AddBody(BaseModel):
    fr: str = Field(min_length=1, max_length=128)
    en: str = Field(min_length=1, max_length=255)
    gender: str = Field(default="", max_length=2)
    pos: str = Field(default="", max_length=16)
    ipa: str = Field(default="", max_length=64)
    source: str = Field(default="manual", max_length=32)


async def _lookup(
    request: Request,
    session: AsyncSession,
    user: User,
    ai_router: AIRouter,
    storage: ObjectStorage,
    settings: Settings,
    word: str,
) -> tuple[VocabLookup | None, bool]:
    """(row, over_budget). A word anyone looked up before is a free DB read; a new one
    costs one LLM call + one Piper run, metered on the daily 'vocab' budget, then cached."""
    try:
        row = await cached_lookup(session, word)
    except EmptyLemmaError:
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_ENTITY, "word has no letters to make a card from"
        ) from None
    if row is not None:
        return row, False
    used = await tokens_used_today(session, user.id, "vocab", date.today())
    if used >= settings.vocab_daily_token_budget:
        return None, True
    row, llm = await fresh_lookup(
        session,
        ai_router,
        getattr(request.app.state, "tts", None),
        storage,
        word,
        voice=settings.piper_voice,
        table=_GENDER_TABLE,
    )
    if llm is not None:
        await add_usage(
            session, user.id, "vocab", llm.usage.input_tokens, llm.usage.output_tokens, date.today()
        )
    await session.commit()
    return row, False


def _not_found(word: str) -> HTTPException:
    return HTTPException(
        status.HTTP_422_UNPROCESSABLE_ENTITY,
        f"Couldn't find a meaning for \u201c{word.strip()}\u201d"
        " \u2014 check the spelling and try again.",
    )


@router.post("/preview")
async def preview(
    body: PreviewBody,
    request: Request,
    session: AsyncSession = Depends(get_session),
    user: User = Depends(get_current_user),
    ai_router: AIRouter = Depends(get_ai_router),
    storage: ObjectStorage = Depends(get_storage),
    settings: Settings = Depends(get_settings),
) -> dict:
    """Look a French word up (meaning, gender, IPA, pronunciation) for the learner to
    review before adding. A word already in the course vocab is returned from the content
    bank as `in_course` (no model call, nothing to add — it's in their reviews already)."""
    match = await find_content_match(session, body.word)
    if match is not None:
        d = match.data
        return {
            "enrichment": {
                "fr": d.get("fr", ""),
                "en": d.get("en", ""),
                "pos": d.get("pos", ""),
                "gender": d.get("gender", ""),
                "ipa": "",
                "gender_source": "course",
                "audio_url": f"/content/audio/{d['audio']}" if d.get("audio") else None,
            },
            "in_course": match.level,
        }
    row, over_budget = await _lookup(
        request, session, user, ai_router, storage, settings, body.word
    )
    if over_budget:
        return {"enrichment": None, "over_budget": True}
    if row is None:
        raise _not_found(body.word)
    return {"enrichment": lookup_payload(row)}


@router.get("/lookup-audio/{slug}")
async def lookup_audio(
    request: Request,
    slug: str,
    session: AsyncSession = Depends(get_session),
    storage: ObjectStorage = Depends(get_storage),
    user: User = Depends(get_current_user),
    settings: Settings = Depends(get_settings),
) -> Response:
    """Pronunciation of a looked-up word, so the learner can hear it before adding."""
    row = await session.get(VocabLookup, slug)
    if row is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "no such word")
    return await _serve_audio(request, session, storage, settings, row, f"vocablookup/{slug}.wav")


@router.post("")
async def add(
    body: AddBody,
    session: AsyncSession = Depends(get_session),
    user: User = Depends(get_current_user),
) -> dict:
    """Store a personal card and seed its SRS review. Idempotent per word — re-adding
    returns the existing card without resetting its progress (`added` is False)."""
    try:
        row, created = await add_personal(
            session,
            user.id,
            fr=body.fr,
            en=body.en,
            gender=body.gender,
            pos=body.pos,
            ipa=body.ipa,
            source=body.source or "manual",
        )
    except EmptyLemmaError:
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_ENTITY, "word has no letters to make a card from"
        ) from None
    if row.audio_key is None:
        looked_up = await session.get(VocabLookup, slugify(row.fr)[:64])
        row.audio_key = looked_up.audio_key if looked_up else None
    seeded = await seed_cards(session, user.id, [row.card_key])
    await session.commit()
    return {"card": card_payload(row), "added": created, "review_seeded": seeded > 0}


class FromWordBody(BaseModel):
    word: str = Field(min_length=1, max_length=80)
    source: str = Field(default="speaking", max_length=32)


@router.post("/from-word")
async def add_from_word(
    body: FromWordBody,
    request: Request,
    session: AsyncSession = Depends(get_session),
    user: User = Depends(get_current_user),
    ai_router: AIRouter = Depends(get_ai_router),
    storage: ObjectStorage = Depends(get_storage),
    settings: Settings = Depends(get_settings),
) -> dict:
    """One-click look-up-and-add: the Speaking rich tier (Slice 3c) uses this to add a
    spoken word the learner reached for. Shares /preview's cached lookup."""
    if await find_content_match(session, body.word) is not None:
        # Already a real content-bank word — the intended Speaking UI flow never offers
        # these (resolve_new_words filters them out first), but a caller hitting this
        # endpoint directly must not mint a duplicate `uv:` card for it.
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_ENTITY, "word is already in the content bank"
        )
    result, over_budget = await _lookup(
        request, session, user, ai_router, storage, settings, body.word
    )
    if over_budget:
        return {"card": None, "added": False, "over_budget": True}
    if result is None:
        raise _not_found(body.word)
    try:
        row, created = await add_personal(
            session,
            user.id,
            fr=result.fr,
            en=result.en,
            gender=result.gender,
            pos=result.pos,
            ipa=result.ipa,
            source=body.source or "speaking",
        )
        row.audio_key = row.audio_key or result.audio_key
    except EmptyLemmaError:
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_ENTITY, "word has no letters to make a card from"
        ) from None
    seeded = await seed_cards(session, user.id, [row.card_key])
    await session.commit()
    return {"card": card_payload(row), "added": created, "review_seeded": seeded > 0}


@router.get("")
async def my_deck(
    session: AsyncSession = Depends(get_session),
    user: User = Depends(get_current_user),
) -> dict:
    rows = await list_personal(session, user.id)
    return {"cards": [card_payload(v) for v in rows]}


@router.get("/audio/{card_key}")
async def personal_audio(
    request: Request,
    card_key: str,
    session: AsyncSession = Depends(get_session),
    storage: ObjectStorage = Depends(get_storage),
    user: User = Depends(get_current_user),
    settings: Settings = Depends(get_settings),
) -> Response:
    """Pronunciation for a personal card, synthesized on first play and cached (lazy
    TTS, same pattern as GET /speech/audio). No pre-built clip for user words."""
    card = await get_personal(session, user.id, card_key)
    if card is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "no such card")
    return await _serve_audio(
        request, session, storage, settings, card, f"uservocab/{user.id}/{card.id}.wav"
    )


async def _serve_audio(
    request: Request,
    session: AsyncSession,
    storage: ObjectStorage,
    settings: Settings,
    row: UserVocab | VocabLookup,
    key: str,
) -> Response:
    """Serve `row`'s stored clip, or synthesize `row.fr` once, store it at `key`, and
    remember it on the row (lazy TTS, same pattern as GET /speech/audio)."""
    if row.audio_key:
        try:
            data = await anyio.to_thread.run_sync(lambda: storage.get(row.audio_key))
            return Response(content=data, media_type="audio/wav")
        except Exception:
            pass  # cached key missing — fall through and re-synthesize

    tts = request.app.state.tts
    if tts is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "no audio available")
    data = await anyio.to_thread.run_sync(
        lambda: tts.synthesize(text=row.fr, voice=settings.piper_voice, lang="fr")
    )
    await anyio.to_thread.run_sync(lambda: storage.put(key, data, "audio/wav"))
    row.audio_key = key
    await session.commit()
    return Response(content=data, media_type="audio/wav")
