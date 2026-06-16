"""Exam tables: synced blueprints + per-user attempts (with the CLB report)."""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import JSON, DateTime, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.users.models import Base


class ExamBlueprintRow(Base):
    __tablename__ = "exam_blueprints"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    level: Mapped[str] = mapped_column(String(16), index=True)
    data: Mapped[dict] = mapped_column(JSON)


class ExamAttempt(Base):
    __tablename__ = "exam_attempts"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(Integer, index=True)
    blueprint_id: Mapped[str] = mapped_column(String(64), index=True)
    level: Mapped[str] = mapped_column(String(16))
    status: Mapped[str] = mapped_column(String(16))         # in_progress | finished
    sections: Mapped[dict] = mapped_column(JSON)            # skill -> {clb, detail}
    clb_report: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    started_at: Mapped[datetime] = mapped_column(DateTime)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
