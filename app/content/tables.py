"""SQLAlchemy tables for synced content (the DB target of the file loader).

Shares the `Base` from `users.models` so Alembic's `target_metadata` picks these
up. Content is file-sourced and re-syncable, so lessons/vocab are stored as JSON
blobs keyed by their stable string id — schema churn in a lesson doesn't require
a migration. Crucially, learner state (progress, SRS) references these ids as
plain strings, *not* foreign keys, so a content re-sync never cascades into
learner data (plan §6).
"""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import JSON, DateTime, Integer, String, UniqueConstraint, func
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


class UserVocab(Base):
    """A learner's own vocab card (personal deck) — words they added themselves, e.g.
    from a Speaking conversation or the manual "add a word" flow. Distinct from the
    shared `ContentVocab` bank: private to one user and enriched on the fly (Slice D).

    `card_key` is the SRS card key, namespaced `uv:<slug>` so it can never collide with
    a global content id — the review queue routes any `uv:`-prefixed key here instead of
    to `ContentVocab`. Still no FK to anything: SRS/progress reference it by string.
    Pronunciation is synthesized lazily (`audio_key` caches the first play), mirroring
    the Speaking lazy-TTS path — no pre-built mp3."""

    __tablename__ = "user_vocab"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(Integer, index=True)
    card_key: Mapped[str] = mapped_column(String(64))  # "uv:<slug>"
    fr: Mapped[str] = mapped_column(String(128))
    en: Mapped[str] = mapped_column(String(255))
    gender: Mapped[str] = mapped_column(String(2), default="")
    pos: Mapped[str] = mapped_column(String(16), default="")
    ipa: Mapped[str] = mapped_column(String(64), default="")
    source: Mapped[str] = mapped_column(String(32), default="")  # "manual" | "speaking"
    audio_key: Mapped[str | None] = mapped_column(String(128), nullable=True)  # lazy-TTS cache
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    __table_args__ = (UniqueConstraint("user_id", "card_key", name="uq_uservocab_user_card"),)
