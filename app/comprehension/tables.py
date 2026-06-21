"""Comprehension tables: synced sets + per-user attempts."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import JSON, DateTime, Float, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.users.models import Base


class ComprehensionSetRow(Base):
    __tablename__ = "comprehension_sets"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    level: Mapped[str] = mapped_column(String(16), index=True)
    skill: Mapped[str] = mapped_column(String(16), index=True)
    accent: Mapped[str | None] = mapped_column(String(16), nullable=True)
    data: Mapped[dict] = mapped_column(JSON)  # full set incl. answers + explanations


class ComprehensionAttempt(Base):
    __tablename__ = "comprehension_attempts"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(Integer, index=True)
    set_id: Mapped[str] = mapped_column(String(64), index=True)
    score: Mapped[float] = mapped_column(Float)
    elapsed_seconds: Mapped[int | None] = mapped_column(Integer, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime)


class ComprehensionPass(Base):
    """One row per (user, set) the *first* time they pass in time — the unique key makes
    the XP award atomic, so concurrent submits can't double-pay (qa-100)."""

    __tablename__ = "comprehension_passes"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(Integer, index=True)
    set_id: Mapped[str] = mapped_column(String(64), index=True)
    awarded_at: Mapped[datetime] = mapped_column(DateTime)

    __table_args__ = (UniqueConstraint("user_id", "set_id", name="uq_comprehension_pass"),)
