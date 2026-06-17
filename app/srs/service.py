"""SRS persistence: seed new cards, fetch the due queue, apply a review.

Datetimes are stored as naive UTC so comparisons work uniformly on SQLite and
Postgres; the FSRS engine works in tz-aware UTC, and we convert at the boundary.
"""

from __future__ import annotations

from collections.abc import Iterable
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.srs.fsrs import FSRSEngine
from app.srs.models import ReviewCard

_engine = FSRSEngine()


def _now_aware() -> datetime:
    return datetime.now(UTC)


def _naive_utc(dt: datetime) -> datetime:
    if dt.tzinfo is not None:
        dt = dt.astimezone(UTC)
    return dt.replace(tzinfo=None)


async def seed_cards(
    session: AsyncSession, user_id: int, card_keys: Iterable[str], *, now: datetime | None = None
) -> int:
    """Create a new card for each vocab id the user doesn't already have.
    Returns how many were created. Idempotent — existing cards are left untouched
    so re-completing a lesson never resets review progress."""
    keys = list(dict.fromkeys(card_keys))  # de-dup, keep order
    if not keys:
        return 0
    now = now or _now_aware()
    existing = set(
        (
            await session.execute(
                select(ReviewCard.card_key).where(
                    ReviewCard.user_id == user_id, ReviewCard.card_key.in_(keys)
                )
            )
        ).scalars()
    )
    created = 0
    for key in keys:
        if key in existing:
            continue
        cs = _engine.new(now=now)
        session.add(
            ReviewCard(user_id=user_id, card_key=key, due=_naive_utc(cs.due), state=cs.state)
        )
        created += 1
    return created


async def due_cards(
    session: AsyncSession, user_id: int, *, limit: int = 20, now: datetime | None = None
) -> list[ReviewCard]:
    cutoff = _naive_utc(now or _now_aware())
    result = await session.execute(
        select(ReviewCard)
        .where(ReviewCard.user_id == user_id, ReviewCard.due <= cutoff)
        .order_by(ReviewCard.due)
        .limit(limit)
    )
    return list(result.scalars().all())


async def review_card(
    session: AsyncSession, user_id: int, card_key: str, rating: str, *, now: datetime | None = None
) -> datetime | None:
    """Apply a rating; returns the new due date, or None if the card doesn't exist."""
    result = await session.execute(
        select(ReviewCard).where(ReviewCard.user_id == user_id, ReviewCard.card_key == card_key)
    )
    card = result.scalar_one_or_none()
    if card is None:
        return None
    cs = _engine.review(card.state, rating, now=now or _now_aware())
    card.state = cs.state
    card.due = _naive_utc(cs.due)
    return card.due
