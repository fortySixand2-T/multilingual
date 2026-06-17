"""Assessment tables: synced writing tasks + graded submissions."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import JSON, DateTime, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.users.models import Base


class WritingTaskRow(Base):
    __tablename__ = "writing_tasks"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    level: Mapped[str] = mapped_column(String(16), index=True)
    section: Mapped[str] = mapped_column(String(2), index=True)
    data: Mapped[dict] = mapped_column(JSON)


class WritingSubmission(Base):
    __tablename__ = "writing_submissions"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(Integer, index=True)
    task_id: Mapped[str] = mapped_column(String(64), index=True)
    text: Mapped[str] = mapped_column(Text)
    clb_estimate: Mapped[int | None] = mapped_column(Integer, nullable=True)
    feedback: Mapped[dict] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(DateTime)
