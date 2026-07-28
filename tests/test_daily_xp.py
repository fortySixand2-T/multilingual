"""Daily XP ledger: streak/XP coverage for repeatable activities + the daily-goal
ring. Repeatable bonuses (review/drill) are once-per-day (anti-farm); per-unit
awards (lesson/comprehension/exam) accumulate; the ring sums a day's XP."""

import asyncio
import tempfile
from datetime import date, timedelta

from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

import app.progress.models  # noqa: F401 — register tables
from app.progress.service import (
    DAILY_XP_GOAL,
    record_activity,
    xp_earned_today,
)
from app.users.models import Base

_DB = f"sqlite+aiosqlite:///{tempfile.mkdtemp()}/daily_xp.db"
_engine = create_async_engine(_DB)
_Session = async_sessionmaker(_engine, expire_on_commit=False)


def _run(coro):
    return asyncio.run(coro)


async def _create():
    async with _engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


_run(_create())

_TODAY = date(2026, 7, 27)
_TOMORROW = _TODAY + timedelta(days=1)


def test_once_per_day_bonus_is_farm_proof():
    async def go():
        async with _Session() as s:
            for _ in range(5):  # grind the review queue five times
                await record_activity(
                    s, 10, xp_award=10, source="review", once_per_day=True, today=_TODAY
                )
            await s.commit()
            return await xp_earned_today(s, 10, _TODAY)

    # five reviews, one bonus
    assert _run(go()) == 10


def test_streak_counts_every_day_even_when_bonus_is_capped():
    async def go():
        async with _Session() as s:
            first = await record_activity(
                s, 11, xp_award=10, source="review", once_per_day=True, today=_TODAY
            )
            second = await record_activity(
                s, 11, xp_award=10, source="review", once_per_day=True, today=_TODAY
            )
            await s.commit()
            await s.refresh(second)
            return first.streak, second.streak, second.xp

    s1, s2, xp = _run(go())
    assert s1 == 1 and s2 == 1  # same day → streak unchanged, still counted
    assert xp == 10  # only one bonus despite two reviews


def test_daily_ring_sums_across_sources():
    async def go():
        async with _Session() as s:
            await record_activity(s, 12, xp_award=10, source="lesson", today=_TODAY)
            await record_activity(s, 12, xp_award=10, source="lesson", today=_TODAY)  # 2nd lesson
            await record_activity(
                s, 12, xp_award=10, source="review", once_per_day=True, today=_TODAY
            )
            await s.commit()
            return await xp_earned_today(s, 12, _TODAY)

    # per-unit lessons accumulate (20) + one review bonus (10)
    assert _run(go()) == 30


def test_bonus_resets_the_next_day_and_advances_streak():
    async def go():
        async with _Session() as s:
            await record_activity(
                s, 13, xp_award=10, source="drill", once_per_day=True, today=_TODAY
            )
            today_xp = await xp_earned_today(s, 13, _TODAY)
            prog = await record_activity(
                s, 13, xp_award=10, source="drill", once_per_day=True, today=_TOMORROW
            )
            await s.commit()
            await s.refresh(prog)
            return today_xp, await xp_earned_today(s, 13, _TOMORROW), prog.streak, prog.xp

    today_xp, tomorrow_xp, streak, total = _run(go())
    assert today_xp == 10 and tomorrow_xp == 10  # a fresh bonus each day
    assert streak == 2  # consecutive days
    assert total == 20  # both bonuses in lifetime xp


def test_goal_is_a_positive_target():
    assert DAILY_XP_GOAL > 0
