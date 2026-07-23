"""invites: managed, reusable signup tokens

Revision ID: 0013_invites
Revises: 0012_weak_spots
Create Date: 2026-07-22

A shareable signup token, complementing the static env INVITE_CODES. Reusable by
default (max_uses NULL = unlimited); optionally capped (max_uses), time-boxed
(expires_at) or revoked (active=false). Redemption bumps `uses`.
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "0013_invites"
down_revision = "0012_weak_spots"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "invites",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("token", sa.String(length=64), nullable=False),
        sa.Column("label", sa.String(length=120), nullable=False, server_default=""),
        sa.Column("max_uses", sa.Integer(), nullable=True),
        sa.Column("uses", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.UniqueConstraint("token", name="uq_invites_token"),
    )
    op.create_index("ix_invites_token", "invites", ["token"])


def downgrade() -> None:
    op.drop_index("ix_invites_token", table_name="invites")
    op.drop_table("invites")
