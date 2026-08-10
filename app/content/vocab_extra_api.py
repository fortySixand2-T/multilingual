"""Generic vocab study-extras API: word forms + on-demand usage examples for ANY card.

One endpoint set serves both banks — a `card_key` is a content vocab id or a personal
`uv:<slug>` key, resolved by `vocab_extra.resolve_card_meta`:

  POST /vocab/extra     {card_key}  -> stored {forms, examples} (no LLM; hydrate on open)
  POST /vocab/forms     {card_key}  -> forms, generated once then cached (per user)
  POST /vocab/examples  {card_key}  -> FRESH sentences each press, prepended to history

`forms`/`examples` persist in the shared `vocab_extra` table (per user+card). Forms are
stable so a second /forms request returns the stored table with no model call; examples
are deliberately regenerated every press. Both meter the daily 'vocab' token budget and
degrade to a graceful 200 (`over_budget`) rather than erroring.
"""

from __future__ import annotations

from datetime import date

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.router import AIRouter
from app.api.auth import get_current_user
from app.api.deps import get_ai_router
from app.config.settings import Settings, get_settings
from app.content.forms import generate_examples, generate_forms, merge_examples
from app.content.vocab_extra import get_extra, get_or_create_extra, resolve_card_meta
from app.db.session import get_session
from app.usage.service import add_usage, tokens_used_today
from app.users.models import User

router = APIRouter(prefix="/vocab", tags=["vocab-extras"])


class CardBody(BaseModel):
    card_key: str = Field(min_length=1, max_length=64)


async def _require_card(session: AsyncSession, user_id: int, card_key: str):
    meta = await resolve_card_meta(session, user_id, card_key)
    if meta is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "no such card")
    return meta


@router.post("/extra")
async def read_extra(
    body: CardBody,
    session: AsyncSession = Depends(get_session),
    user: User = Depends(get_current_user),
) -> dict:
    """Stored extras for a card, without generating anything (free). The client calls
    this when the study panel opens to show already-generated forms and past example
    sentences. `forms: null` means "never generated" so the UI can then request them."""
    await _require_card(session, user.id, body.card_key)
    row = await get_extra(session, user.id, body.card_key)
    return {
        "forms": row.forms if row else None,
        "examples": (row.examples if row else None) or [],
    }


@router.post("/forms")
async def card_forms(
    body: CardBody,
    session: AsyncSession = Depends(get_session),
    user: User = Depends(get_current_user),
    ai_router: AIRouter = Depends(get_ai_router),
    settings: Settings = Depends(get_settings),
) -> dict:
    """The word's morphological forms (noun plural, verb conjugations, adjective m/f/pl).
    Stable, so generated once and cached per user — a second request returns the stored
    forms with no LLM call. Metered on the daily 'vocab' budget."""
    meta = await _require_card(session, user.id, body.card_key)
    row = await get_extra(session, user.id, body.card_key)
    if row is not None and row.forms is not None:
        # already generated (even []) — free, no model call
        return {"forms": row.forms, "cached": True}

    used = await tokens_used_today(session, user.id, "vocab", date.today())
    if used >= settings.vocab_daily_token_budget:
        return {"forms": [], "over_budget": True}

    forms, llm = await generate_forms(ai_router, meta.fr, meta.pos, meta.gender)
    if llm is not None:
        await add_usage(
            session, user.id, "vocab", llm.usage.input_tokens, llm.usage.output_tokens, date.today()
        )
    row = await get_or_create_extra(session, user.id, body.card_key)
    row.forms = forms  # persist even when empty so we don't retry a non-inflecting word
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
    a small rolling history so past sentences stay visible. The recent history is fed to
    the model as `avoid` to push it off repeats. Metered on the daily 'vocab' budget."""
    meta = await _require_card(session, user.id, body.card_key)
    row = await get_extra(session, user.id, body.card_key)
    history = (row.examples if row else None) or []

    used = await tokens_used_today(session, user.id, "vocab", date.today())
    if used >= settings.vocab_daily_token_budget:
        return {"examples": history, "over_budget": True}

    fresh, llm = await generate_examples(
        ai_router, meta.fr, meta.en, avoid=[e.get("fr", "") for e in history]
    )
    if llm is not None:
        await add_usage(
            session, user.id, "vocab", llm.usage.input_tokens, llm.usage.output_tokens, date.today()
        )
    merged = merge_examples(history, fresh)
    row = await get_or_create_extra(session, user.id, body.card_key)
    row.examples = merged
    await session.commit()
    return {"examples": merged, "fresh": fresh}
