"""Daily-budget read/write, shared by every metered AI feature."""

from __future__ import annotations

from datetime import date

from sqlalchemy.ext.asyncio import AsyncSession

from app.usage.models import DailyUsage


async def tokens_used_today(session: AsyncSession, user_id: int, feature: str, day: date) -> int:
    row = await session.get(DailyUsage, (user_id, day, feature))
    return (row.input_tokens + row.output_tokens) if row else 0


async def add_usage(
    session: AsyncSession,
    user_id: int,
    feature: str,
    input_tokens: int,
    output_tokens: int,
    day: date,
) -> None:
    row = await session.get(DailyUsage, (user_id, day, feature))
    if row is None:
        row = DailyUsage(user_id=user_id, day=day, feature=feature, input_tokens=0, output_tokens=0)
        session.add(row)
        await session.flush()
    row.input_tokens += input_tokens
    row.output_tokens += output_tokens
