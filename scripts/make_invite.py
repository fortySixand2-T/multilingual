#!/usr/bin/env python3
"""Mint, list, and revoke managed signup invite links.

Tokens live in the `invites` table and are reusable by default (no --max-uses =
unlimited). Env INVITE_CODES keep working in parallel; this just adds tokens you
can share as a link, cap, expire, or revoke without a redeploy.

    python -m scripts.make_invite new --label "Study group"          # reusable link
    python -m scripts.make_invite new --label "One friend" --max-uses 1
    python -m scripts.make_invite new --label "Reddit" --expires-days 7
    python -m scripts.make_invite list
    python -m scripts.make_invite revoke <token>

The printed link uses PUBLIC_BASE_URL from settings/.env when set, else a bare
"/signup?invite=<token>" path you prefix with your host.
"""

from __future__ import annotations

import argparse
import asyncio
from datetime import UTC, datetime, timedelta

from sqlalchemy import select

from app.config.settings import get_settings
from app.db.session import SessionLocal
from app.users.invites import create_invite, is_redeemable
from app.users.models import Invite


def _link(token: str) -> str:
    base = get_settings().public_base_url.rstrip("/")
    return f"{base}/signup?invite={token}" if base else f"/signup?invite={token}"


def _fmt(invite: Invite) -> str:
    cap = "∞" if invite.max_uses is None else str(invite.max_uses)
    exp = invite.expires_at.date().isoformat() if invite.expires_at else "never"
    status = "active" if is_redeemable(invite) else "spent/revoked"
    label = invite.label or "-"
    return f"[{status:14}] {invite.token:24} uses {invite.uses}/{cap:3} exp {exp:10} {label}"


async def _new(args: argparse.Namespace) -> None:
    expires_at = None
    if args.expires_days:
        expires_at = datetime.now(UTC) + timedelta(days=args.expires_days)
    async with SessionLocal() as session:
        invite = await create_invite(
            session, label=args.label, max_uses=args.max_uses, expires_at=expires_at
        )
    print("Invite created — share this link:\n")
    print(f"  {_link(invite.token)}\n")
    print(_fmt(invite))


async def _list(_: argparse.Namespace) -> None:
    async with SessionLocal() as session:
        rows = (await session.execute(select(Invite).order_by(Invite.id))).scalars().all()
    if not rows:
        print("No invites yet. Create one:  python -m scripts.make_invite new --label ...")
        return
    for invite in rows:
        print(_fmt(invite))


async def _revoke(args: argparse.Namespace) -> None:
    async with SessionLocal() as session:
        result = await session.execute(select(Invite).where(Invite.token == args.token))
        invite = result.scalar_one_or_none()
        if invite is None:
            raise SystemExit(f"No invite with token {args.token!r}")
        invite.active = False
        await session.commit()
    print(f"Revoked {args.token}")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="cmd", required=True)

    p_new = sub.add_parser("new", help="mint a new (reusable) invite link")
    p_new.add_argument("--label", default="", help="human note, e.g. 'Study group'")
    p_new.add_argument(
        "--max-uses", type=int, default=None, help="cap redemptions (default: unlimited)"
    )
    p_new.add_argument("--expires-days", type=int, default=None, help="expire after N days")
    p_new.set_defaults(fn=_new)

    sub.add_parser("list", help="list all invites").set_defaults(fn=_list)

    p_rev = sub.add_parser("revoke", help="deactivate a token")
    p_rev.add_argument("token")
    p_rev.set_defaults(fn=_revoke)

    args = parser.parse_args()
    asyncio.run(args.fn(args))


if __name__ == "__main__":
    main()
