"""Review-queue API: fetch due cards, submit a review."""

from __future__ import annotations

from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.auth import get_current_user
from app.content.personal import is_personal_key, resolve_queue_vocab
from app.content.tables import ContentVocab
from app.db.session import get_session
from app.progress.service import DAILY_XP_GOAL, record_activity, xp_earned_today
from app.srs.fsrs import RATINGS
from app.srs.service import due_cards, review_card, seed_cards
from app.users.models import User

router = APIRouter(prefix="/srs", tags=["srs"])

REVIEW_XP = 10  # bonus for the day's first review (once per day — see record_activity)


class ReviewBody(BaseModel):
    card_key: str
    rating: Literal["again", "hard", "good", "easy"]


class AddBody(BaseModel):
    card_key: str = Field(min_length=1)


@router.get("/queue")
async def get_queue(
    limit: int = 20,
    session: AsyncSession = Depends(get_session),
    user: User = Depends(get_current_user),
) -> dict:
    cards = await due_cards(session, user.id, limit=limit)
    vocab: dict[str, dict] = {}
    keys = [c.card_key for c in cards]
    if keys:
        # Personal cards (`uv:` keys) live in user_vocab and carry a lazy-TTS audio_url;
        # everything else resolves against the shared content bank.
        vocab = await resolve_queue_vocab(session, user.id, keys)
        content_keys = [k for k in keys if not is_personal_key(k)]
        rows = (
            (await session.execute(select(ContentVocab).where(ContentVocab.id.in_(content_keys))))
            .scalars()
            .all()
        )
        # Attach the pronunciation key by the same convention the vocab endpoint uses
        # (app/content/api.py get_vocab) so review cards can play audio too — otherwise
        # the Review screen never shows the play button for cards without an explicit
        # `audio:` field (i.e. almost all of them).
        for r in rows:
            vocab[r.id] = {
                **r.data,
                "level": r.level,
                "audio": r.data.get("audio") or f"{r.level}/audio/{r.id}.mp3",
            }
    return {
        "due": [
            {"card_key": c.card_key, "due": c.due.isoformat(), "vocab": vocab.get(c.card_key)}
            for c in cards
        ]
    }


@router.post("/add")
async def add_card(
    body: AddBody,
    session: AsyncSession = Depends(get_session),
    user: User = Depends(get_current_user),
) -> dict:
    """Add a vocab card to the user's review queue (e.g. from a study deck).
    Idempotent — `added` is False if the card was already in review.

    The key must name a real vocab card. Unlike the internal lesson-completion
    seeding path (which only ever passes known ids), this endpoint is user-driven,
    so we validate against the content catalog to keep phantom cards — entries with
    no word/translation/audio — out of the queue. The srs↔content decoupling stays
    at the DB level (still no FK); the check lives here, at the user-facing edge."""
    exists = await session.scalar(select(ContentVocab.id).where(ContentVocab.id == body.card_key))
    if exists is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, f"no vocab card {body.card_key!r}")
    created = await seed_cards(session, user.id, [body.card_key])
    await session.commit()
    return {"card_key": body.card_key, "added": created > 0}


@router.post("/review")
async def post_review(
    body: ReviewBody,
    session: AsyncSession = Depends(get_session),
    user: User = Depends(get_current_user),
) -> dict:
    new_due = await review_card(session, user.id, body.card_key, body.rating)
    if new_due is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, f"no card {body.card_key!r} for user")
    # Reviewing counts toward the streak every day; the XP bonus is claimed once per
    # day so grinding the queue can't inflate XP.
    prog = await record_activity(
        session, user.id, xp_award=REVIEW_XP, source="review", once_per_day=True
    )
    await session.commit()
    await session.refresh(prog)
    return {
        "card_key": body.card_key,
        "rating": body.rating,
        "due": new_due.isoformat(),
        "streak": prog.streak,
        "xp": prog.xp,
        "xp_today": await xp_earned_today(session, user.id),
        "daily_goal": DAILY_XP_GOAL,
    }


# Exposed so callers/tests can introspect valid ratings without importing the engine.
VALID_RATINGS = RATINGS
