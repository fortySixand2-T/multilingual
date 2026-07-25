"""Progress queries + mutations other modules depend on.

Exposing functions (not ORM tables) keeps callers — content gating, comprehension
— decoupled from the progress schema. `record_activity` is the single source of
truth for the daily streak + XP, shared by lessons and comprehension.
"""

from __future__ import annotations

from collections.abc import Iterable
from datetime import UTC, date, datetime

from sqlalchemy import select, update
from sqlalchemy.dialects.sqlite import insert as sqlite_insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.progress.models import LessonCompletion, UserProgress, WeakSpot, compute_streak

_LEVEL_ORDER = ["a1", "a2", "b1", "b2", "c1", "c2"]


async def completed_lesson_ids(session: AsyncSession, user_id: int) -> set[str]:
    """Lessons that satisfy gating — passed OR waived (the escape hatch). A row that
    only holds failed `attempts` does NOT unlock the next unit."""
    rows = await session.execute(
        select(LessonCompletion.lesson_id).where(
            LessonCompletion.user_id == user_id,
            (LessonCompletion.passed | LessonCompletion.waived),
        )
    )
    return set(rows.scalars())


async def lesson_states(session: AsyncSession, user_id: int) -> tuple[set[str], set[str]]:
    """(passed, waived) lesson-id sets, so the path can mark a ⭐ pass vs a
    review-flagged waive per lesson."""
    rows = (
        await session.execute(
            select(
                LessonCompletion.lesson_id, LessonCompletion.passed, LessonCompletion.waived
            ).where(LessonCompletion.user_id == user_id)
        )
    ).all()
    passed = {lid for lid, p, _ in rows if p}
    waived = {lid for lid, p, w in rows if w and not p}
    return passed, waived


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


async def sync_weak_spots(
    session: AsyncSession,
    user_id: int,
    set_id: str,
    graded: Iterable[tuple[str, bool]],
) -> None:
    """Given (question_id, correct) pairs from a comprehension submit, record the
    misses for re-practice: a wrong answer upserts a weak-spot (increment the miss
    count, re-open if previously resolved); a correct answer resolves any existing
    one. Idempotent per submit; caller commits."""
    now = datetime.now(UTC).replace(tzinfo=None)
    for ref_id, correct in graded:
        if correct:
            await session.execute(
                update(WeakSpot)
                .where(WeakSpot.user_id == user_id, WeakSpot.ref_id == ref_id)
                .values(resolved=True)
            )
        else:
            stmt = sqlite_insert(WeakSpot).values(
                user_id=user_id,
                kind="comprehension",
                ref_id=ref_id,
                set_id=set_id,
                times_missed=1,
                last_missed=now,
                resolved=False,
            )
            await session.execute(
                stmt.on_conflict_do_update(
                    index_elements=["user_id", "ref_id"],
                    set_={
                        "times_missed": WeakSpot.times_missed + 1,
                        "last_missed": now,
                        "resolved": False,
                    },
                )
            )
