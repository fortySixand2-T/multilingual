"""Progress queries other modules depend on.

Exposing functions (not ORM tables) keeps callers — e.g. content gating —
decoupled from the progress schema: they depend on this contract, not on
`LessonCompletion`'s columns.
"""
from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.progress.models import LessonCompletion


async def completed_lesson_ids(session: AsyncSession, user_id: int) -> set[str]:
    rows = await session.execute(
        select(LessonCompletion.lesson_id).where(LessonCompletion.user_id == user_id)
    )
    return set(rows.scalars())
