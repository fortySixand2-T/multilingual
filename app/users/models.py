from __future__ import annotations

from datetime import datetime

from sqlalchemy import Boolean, DateTime, Integer, String, func
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    email: Mapped[str] = mapped_column(String(255), unique=True)
    display_name: Mapped[str] = mapped_column(String(120), default="")
    password_hash: Mapped[str] = mapped_column(String(255))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class Invite(Base):
    """A shareable signup token. Reusable by default (``max_uses`` NULL = unlimited).

    A token is redeemable while ``active`` and not past ``expires_at`` (NULL = never)
    and under ``max_uses`` (NULL = unlimited). Env ``INVITE_CODES`` still work in
    parallel as always-valid, unlimited codes — this table just adds managed tokens.
    """

    __tablename__ = "invites"

    id: Mapped[int] = mapped_column(primary_key=True)
    token: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    label: Mapped[str] = mapped_column(String(120), default="")  # human note, e.g. "Reddit group"
    max_uses: Mapped[int | None] = mapped_column(Integer, nullable=True)  # NULL = unlimited
    uses: Mapped[int] = mapped_column(Integer, default=0)
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    active: Mapped[bool] = mapped_column(Boolean, default=True)  # kill switch (revoke)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
