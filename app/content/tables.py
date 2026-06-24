"""SQLAlchemy tables for synced content (the DB target of the file loader).

Shares the `Base` from `users.models` so Alembic's `target_metadata` picks these
up. Content is file-sourced and re-syncable, so lessons/vocab are stored as JSON
blobs keyed by their stable string id — schema churn in a lesson doesn't require
a migration. Crucially, learner state (progress, SRS) references these ids as
plain strings, *not* foreign keys, so a content re-sync never cascades into
learner data (plan §6).
"""

from __future__ import annotations

from sqlalchemy import JSON, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.users.models import Base


class ContentUnit(Base):
    __tablename__ = "content_units"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    level: Mapped[str] = mapped_column(String(16), index=True)
    ordinal: Mapped[int] = mapped_column(Integer)
    title: Mapped[str] = mapped_column(String(200))
    icon: Mapped[str] = mapped_column(String(64), default="")
    lessons: Mapped[list] = mapped_column(JSON)  # ordered list[str] of lesson ids
    unlock_type: Mapped[str] = mapped_column(String(16))
    unlock_requires: Mapped[list] = mapped_column(JSON)  # list[str] of unit/lesson ids


class ContentLesson(Base):
    __tablename__ = "content_lessons"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    level: Mapped[str] = mapped_column(String(16), index=True)
    title: Mapped[str] = mapped_column(String(200))
    data: Mapped[dict] = mapped_column(JSON)  # full Lesson dump (incl. exercises)


class ContentVocab(Base):
    __tablename__ = "content_vocab"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    level: Mapped[str] = mapped_column(String(16), index=True)
    data: Mapped[dict] = mapped_column(JSON)  # full Vocab dump


class KnownVocab(Base):
    """A learner's self-marked 'known' vocabulary (free-study deck state). One row per
    (user, vocab id); marking known inserts, resetting deletes. References the vocab id
    as a plain string, not an FK — a content re-sync never touches it."""

    __tablename__ = "vocab_known"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(Integer, index=True)
    card_key: Mapped[str] = mapped_column(String(64))

    __table_args__ = (UniqueConstraint("user_id", "card_key", name="uq_known_user_card"),)
