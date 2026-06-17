"""Per-user/day/feature token usage — the shared daily-budget ledger.

One mechanism for every metered AI feature (tutor drills, writing grading, …),
keyed by `feature` so each can have its own budget while sharing the table and
service. Replaces feature-specific usage tables.
"""

from __future__ import annotations

from datetime import date

from sqlalchemy import Date, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.users.models import Base


class DailyUsage(Base):
    __tablename__ = "daily_usage"

    user_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    day: Mapped[date] = mapped_column(Date, primary_key=True)
    feature: Mapped[str] = mapped_column(String(32), primary_key=True)
    input_tokens: Mapped[int] = mapped_column(Integer, default=0)
    output_tokens: Mapped[int] = mapped_column(Integer, default=0)
