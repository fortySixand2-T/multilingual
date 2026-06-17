"""Progress tables + streak logic.

Learner state keyed by `user_id` / `lesson_id` strings — no FK into content, so a
content re-sync never touches progress (plan §6). `LessonCompletion` is also what
the content path reads to compute gating.
"""

from __future__ import annotations

from datetime import date, datetime, timedelta

from sqlalchemy import Date, DateTime, Float, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.users.models import Base


class UserProgress(Base):
    __tablename__ = "progress_user"

    user_id: Mapped[int] = mapped_column(primary_key=True)
    level: Mapped[str] = mapped_column(String(16), default="a1")
    xp: Mapped[int] = mapped_column(Integer, default=0)
    streak: Mapped[int] = mapped_column(Integer, default=0)
    last_active: Mapped[date | None] = mapped_column(Date, nullable=True)


class LessonCompletion(Base):
    __tablename__ = "progress_lesson_completions"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(Integer, index=True)
    lesson_id: Mapped[str] = mapped_column(String(64), index=True)
    level: Mapped[str] = mapped_column(String(16))
    score: Mapped[float] = mapped_column(Float)
    completed_at: Mapped[datetime] = mapped_column(DateTime)

    __table_args__ = (UniqueConstraint("user_id", "lesson_id", name="uq_completion_user_lesson"),)


def compute_streak(prev_streak: int, last_active: date | None, today: date) -> int:
    """Daily-activity streak: +1 on a consecutive day, unchanged on the same day,
    reset to 1 after any gap."""
    if last_active is None:
        return 1
    if last_active == today:
        return prev_streak  # already counted today
    if last_active == today - timedelta(days=1):
        return prev_streak + 1
    return 1  # missed a day → reset
