"""Managed signup invites: token generation + redemption.

Framework-free (takes an ``AsyncSession``), like ``app.users.auth``. The FastAPI
signup surface in ``app.api.auth`` calls :func:`find_redeemable` during signup; the
``scripts/make_invite.py`` CLI calls :func:`create_invite` to mint and save tokens.
"""

from __future__ import annotations

import secrets
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.users.models import Invite


def generate_token() -> str:
    """A short, URL-safe, hard-to-guess token (~16 chars, ~96 bits)."""
    return secrets.token_urlsafe(12)


def _as_utc(dt: datetime) -> datetime:
    # SQLite hands back naive datetimes; treat those as the UTC we stored.
    return dt if dt.tzinfo else dt.replace(tzinfo=UTC)


def is_redeemable(invite: Invite, *, now: datetime | None = None) -> bool:
    now = now or datetime.now(UTC)
    if not invite.active:
        return False
    if invite.expires_at is not None and _as_utc(invite.expires_at) <= now:
        return False
    if invite.max_uses is not None and invite.uses >= invite.max_uses:
        return False
    return True


async def find_redeemable(session: AsyncSession, token: str) -> Invite | None:
    """Return the invite for ``token`` iff it can still be used, else None.

    Returns the session-attached row so the caller can bump ``uses`` and commit it
    atomically with the new user (see ``app.api.auth.signup``).
    """
    token = token.strip()
    if not token:
        return None
    result = await session.execute(select(Invite).where(Invite.token == token))
    invite = result.scalar_one_or_none()
    if invite is None or not is_redeemable(invite):
        return None
    return invite


async def create_invite(
    session: AsyncSession,
    *,
    label: str = "",
    max_uses: int | None = None,
    expires_at: datetime | None = None,
) -> Invite:
    """Mint and persist a new reusable invite token."""
    invite = Invite(
        token=generate_token(),
        label=label,
        max_uses=max_uses,
        expires_at=expires_at,
    )
    session.add(invite)
    await session.commit()
    await session.refresh(invite)
    return invite
