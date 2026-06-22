"""Progress queries + mutations other modules depend on.

Exposing functions (not ORM tables) keeps callers — content gating, comprehension
— decoupled from the progress schema. `record_activity` is the single source of
truth for the daily streak + XP, shared by lessons and comprehension.
"""

from __future__ import annotations

from datetime import date

from sqlalchemy import select
from sqlalchemy.dialects.sqlite import insert as sqlite_insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.progress.models import LessonCompletion, UserProgress, compute_streak

_LEVEL_ORDER = ["a1", "a2", "b1", "b2", "c1", "c2"]


async def completed_lesson_ids(session: AsyncSession, user_id: int) -> set[str]:
    rows = await session.execute(
        select(LessonCompletion.lesson_id).where(LessonCompletion.user_id == user_id)
    )
    return set(rows.scalars())


async def get_or_create_progress(
    session: AsyncSession, user_id: int, level: str = "a1"
) -> UserProgress:
    prog = await session.get(UserProgress, user_id)
    if prog is None:
        # insert-or-ignore so two concurrent first-activities don't collide on the PK,
        # then read the row back (ours or the racer's) — see qa-070.
        await session.execute(
            sqlite_insert(UserProgress)
            .values(user_id=user_id, level=level, xp=0, streak=0, last_active=None)
            .on_conflict_do_nothing(index_elements=["user_id"])
        )
        prog = await session.get(UserProgress, user_id)
    return prog


async def record_activity(
    session: AsyncSession,
    user_id: int,
    *,
    xp_award: int = 0,
    level: str = "a1",
    today: date | None = None,
) -> UserProgress:
    """Bump the daily streak (once per day) and add XP. The shared write path for
    any learning activity that should count toward streak/XP."""
    today = today or date.today()
    prog = await get_or_create_progress(session, user_id, level)
    # streak is idempotent within a day, so concurrent writers converge; xp uses an
    # atomic SQL increment so a concurrent activity can't clobber the award (qa-070).
    # Promote level if the incoming activity is at a higher level (qa-260).
    cur = _LEVEL_ORDER.index(prog.level) if prog.level in _LEVEL_ORDER else -1
    new = _LEVEL_ORDER.index(level) if level in _LEVEL_ORDER else -1
    if new > cur:
        prog.level = level
    prog.streak = compute_streak(prog.streak, prog.last_active, today)
    prog.last_active = today
    if xp_award:
        prog.xp = UserProgress.xp + xp_award
    return prog
