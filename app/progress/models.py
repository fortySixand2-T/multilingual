"""Progress tables + streak logic.

Learner state keyed by `user_id` / `lesson_id` strings — no FK into content, so a
content re-sync never touches progress (plan §6). `LessonCompletion` is also what
the content path reads to compute gating.
"""

from __future__ import annotations

from datetime import date, datetime, timedelta

from sqlalchemy import Boolean, Date, DateTime, Float, Integer, String, UniqueConstraint
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
    # A row now exists once a lesson is attempted, not only when passed. `passed`
    # is the mastery star; `waived` is the escape hatch (unlocks the next unit but
    # stays flagged for review); `attempts` counts failed tries and gates the hatch.
    passed: Mapped[bool] = mapped_column(Boolean, default=True)
    waived: Mapped[bool] = mapped_column(Boolean, default=False)
    attempts: Mapped[int] = mapped_column(Integer, default=0)

    __table_args__ = (UniqueConstraint("user_id", "lesson_id", name="uq_completion_user_lesson"),)


class WeakSpot(Base):
    """A question a learner got wrong, kept for targeted re-practice. One row per
    (user, ref_id); `resolved` flips true once they answer it correctly (or dismiss
    it). `kind` is "comprehension" for now — the shape allows lesson misses later."""

    __tablename__ = "weak_spots"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(Integer, index=True)
    kind: Mapped[str] = mapped_column(String(16))  # "comprehension"
    ref_id: Mapped[str] = mapped_column(String(96))  # the missed question id (set-prefixed)
    set_id: Mapped[str] = mapped_column(String(64))  # owning comprehension set, for re-hydration
    times_missed: Mapped[int] = mapped_column(Integer, default=1)
    last_missed: Mapped[datetime] = mapped_column(DateTime)
    resolved: Mapped[bool] = mapped_column(Boolean, default=False)

    __table_args__ = (UniqueConstraint("user_id", "ref_id", name="uq_weak_spot_user_ref"),)


class DailyXp(Base):
    """XP earned per (user, day, source). Two jobs: it's the source of truth for
    "XP earned today" (the daily-goal ring sums a day's rows), and the once-per-day
    cap for repeatable activities — review/drill claim their bonus only once per day
    via the unique (user, day, source) marker, so they can't be farmed. Per-unit
    sources (lesson/comprehension/exam) accumulate into the day's row instead."""

    __tablename__ = "progress_daily_xp"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(Integer, index=True)
    day: Mapped[date] = mapped_column(Date, index=True)
    source: Mapped[str] = mapped_column(String(24))  # lesson|comprehension|exam|review|drill
    xp: Mapped[int] = mapped_column(Integer, default=0)

    __table_args__ = (
        UniqueConstraint("user_id", "day", "source", name="uq_daily_xp_user_day_source"),
    )


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
