"""Personal vocab deck API (Slice E): preview an enrichment, add a card, list "My
deck", and serve a card's pronunciation (synthesized lazily).

The add flow is two steps so the learner confirms before anything is stored:
  POST /vocab/personal/preview  {word}      -> enriched {fr,en,pos,gender,ipa} (no write)
  POST /vocab/personal          {fr,en,...}  -> stores the card + seeds its SRS review

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
from app.content.enrich import GenderTable, enrich
from app.content.forms import generate_examples, generate_forms, merge_examples
from app.content.personal import (
    EmptyLemmaError,
    add_personal,
    card_payload,
    get_personal,
    list_personal,
)
from app.content.tables import UserVocab
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


@router.post("/preview")
async def preview(
    body: PreviewBody,
    session: AsyncSession = Depends(get_session),
    user: User = Depends(get_current_user),
    ai_router: AIRouter = Depends(get_ai_router),
    settings: Settings = Depends(get_settings),
) -> dict:
    """Enrich a bare French word into a dictionary entry (Slice D) for the learner to
    review before adding. Read-only. Metered on the daily 'vocab' budget."""
    used = await tokens_used_today(session, user.id, "vocab", date.today())
    if used >= settings.vocab_daily_token_budget:
        return {"enrichment": None, "over_budget": True}

    result, llm = await enrich(ai_router, body.word, table=_GENDER_TABLE)
    if llm is not None:
        await add_usage(
            session, user.id, "vocab", llm.usage.input_tokens, llm.usage.output_tokens, date.today()
        )
        await session.commit()
    if result is None:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "empty word")
    return {
        "enrichment": {
            "fr": result.fr,
            "en": result.en,
            "pos": result.pos,
            "gender": result.gender,
            "ipa": result.ipa,
            "gender_source": result.gender_source,
        }
    }


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
    seeded = await seed_cards(session, user.id, [row.card_key])
    await session.commit()
    return {"card": card_payload(row), "added": created, "review_seeded": seeded > 0}


class FromWordBody(BaseModel):
    word: str = Field(min_length=1, max_length=80)
    source: str = Field(default="speaking", max_length=32)


@router.post("/from-word")
async def add_from_word(
    body: FromWordBody,
    session: AsyncSession = Depends(get_session),
    user: User = Depends(get_current_user),
    ai_router: AIRouter = Depends(get_ai_router),
    settings: Settings = Depends(get_settings),
) -> dict:
    """One-click enrich-and-add: look a word up (Slice D) and store it as a personal card
    in a single call — the Speaking rich tier (Slice 3c) uses this to add a spoken word
    the learner reached for. Metered on the daily 'vocab' budget like /preview."""
    used = await tokens_used_today(session, user.id, "vocab", date.today())
    if used >= settings.vocab_daily_token_budget:
        return {"card": None, "added": False, "over_budget": True}

    result, llm = await enrich(ai_router, body.word, table=_GENDER_TABLE)
    if llm is not None:
        await add_usage(
            session, user.id, "vocab", llm.usage.input_tokens, llm.usage.output_tokens, date.today()
        )
    if result is None or not result.en:
        await session.commit()  # persist any usage billed before bailing
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "couldn't look that word up")
    if await find_content_match(session, result.fr) is not None:
        # Already a real content-bank word — the intended Speaking UI flow never offers
        # these (resolve_new_words filters them out first), but a caller hitting this
        # endpoint directly must not mint a duplicate `uv:` card for it.
        await session.commit()  # persist any usage billed before bailing
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_ENTITY, "word is already in the content bank"
        )
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
    except EmptyLemmaError:
        await session.commit()
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_ENTITY, "word has no letters to make a card from"
        ) from None
    seeded = await seed_cards(session, user.id, [row.card_key])
    await session.commit()
    return {"card": card_payload(row), "added": created, "review_seeded": seeded > 0}


class CardBody(BaseModel):
    card_key: str = Field(min_length=1, max_length=64)


async def _load_card(session: AsyncSession, user_id: int, card_key: str) -> UserVocab:
    card = await get_personal(session, user_id, card_key)
    if card is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "no such card")
    return card


@router.post("/forms")
async def card_forms(
    body: CardBody,
    session: AsyncSession = Depends(get_session),
    user: User = Depends(get_current_user),
    ai_router: AIRouter = Depends(get_ai_router),
    settings: Settings = Depends(get_settings),
) -> dict:
    """The word's morphological forms (noun plural, verb conjugations, adjective m/f/pl).
    Stable, so generated once and cached on the card — a second request returns the
    stored forms with no LLM call. Metered on the daily 'vocab' budget."""
    card = await _load_card(session, user.id, body.card_key)
    if card.forms is not None:  # already generated (even if empty) — free, no model call
        return {"forms": card.forms, "cached": True}

    used = await tokens_used_today(session, user.id, "vocab", date.today())
    if used >= settings.vocab_daily_token_budget:
        return {"forms": [], "over_budget": True}

    forms, llm = await generate_forms(ai_router, card.fr, card.pos, card.gender)
    if llm is not None:
        await add_usage(
            session, user.id, "vocab", llm.usage.input_tokens, llm.usage.output_tokens, date.today()
        )
    card.forms = forms  # persist even when empty so we don't retry a non-inflecting word
    await session.commit()
    return {"forms": forms, "cached": False}


@router.post("/examples")
async def card_examples(
    body: CardBody,
    session: AsyncSession = Depends(get_session),
    user: User = Depends(get_current_user),
    ai_router: AIRouter = Depends(get_ai_router),
    settings: Settings = Depends(get_settings),
) -> dict:
    """Fresh usage sentences for the word — new ones each press (uncached), prepended to
    the card's small rolling history so past sentences stay visible. The recent history
    is fed to the model as `avoid` to push it off repeats. Metered on 'vocab' budget."""
    card = await _load_card(session, user.id, body.card_key)
    used = await tokens_used_today(session, user.id, "vocab", date.today())
    if used >= settings.vocab_daily_token_budget:
        return {"examples": card.examples or [], "over_budget": True}

    history = card.examples or []
    fresh, llm = await generate_examples(
        ai_router, card.fr, card.en, avoid=[e.get("fr", "") for e in history]
    )
    if llm is not None:
        await add_usage(
            session, user.id, "vocab", llm.usage.input_tokens, llm.usage.output_tokens, date.today()
        )
    merged = merge_examples(history, fresh)
    card.examples = merged
    await session.commit()
    return {"examples": merged, "fresh": fresh}


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

    if card.audio_key:
        try:
            data = await anyio.to_thread.run_sync(lambda: storage.get(card.audio_key))
            return Response(content=data, media_type="audio/wav")
        except Exception:
            pass  # cached key missing — fall through and re-synthesize

    tts = request.app.state.tts
    if tts is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "no audio available")
    data = await anyio.to_thread.run_sync(
        lambda: tts.synthesize(text=card.fr, voice=settings.piper_voice, lang="fr")
    )
    key = f"uservocab/{user.id}/{card.id}.wav"
    await anyio.to_thread.run_sync(lambda: storage.put(key, data, "audio/wav"))
    card.audio_key = key
    await session.commit()
    return Response(content=data, media_type="audio/wav")
