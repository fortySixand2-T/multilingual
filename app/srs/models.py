"""SRS review-card table. One row per (user, vocab id)."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import JSON, DateTime, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.users.models import Base


class ReviewCard(Base):
    __tablename__ = "srs_cards"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(Integer, index=True)
    card_key: Mapped[str] = mapped_column(String(64))  # vocab id (immutable content id)
    due: Mapped[datetime] = mapped_column(DateTime, index=True)  # naive UTC, for queue queries
    state: Mapped[dict] = mapped_column(JSON)  # opaque FSRS card dict

    __table_args__ = (UniqueConstraint("user_id", "card_key", name="uq_srs_user_card"),)
