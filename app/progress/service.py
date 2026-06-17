"""Progress queries + mutations other modules depend on.

Exposing functions (not ORM tables) keeps callers — content gating, comprehension
— decoupled from the progress schema. `record_activity` is the single source of
truth for the daily streak + XP, shared by lessons and comprehension.
"""

from __future__ import annotations

from datetime import date

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.progress.models import LessonCompletion, UserProgress, compute_streak


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
        prog = UserProgress(user_id=user_id, level=level, xp=0, streak=0, last_active=None)
        session.add(prog)
        await session.flush()
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
    prog.streak = compute_streak(prog.streak, prog.last_active, today)
    prog.last_active = today
    prog.xp += xp_award
    return prog
