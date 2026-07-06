"""weak_spots: missed comprehension questions kept for targeted re-practice

Revision ID: 0012_weak_spots
Revises: 0011_vocab_known
Create Date: 2026-07-05

One row per (user, ref_id) — the missed question id. A wrong answer upserts and
bumps times_missed; a correct (re-)answer or a dismiss sets resolved=true. `kind`
is "comprehension" for now; the shape leaves room for lesson misses later.
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "0012_weak_spots"
down_revision = "0011_vocab_known"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "weak_spots",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("kind", sa.String(length=16), nullable=False),
        sa.Column("ref_id", sa.String(length=96), nullable=False),
        sa.Column("set_id", sa.String(length=64), nullable=False),
        sa.Column("times_missed", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("last_missed", sa.DateTime(), nullable=False),
        sa.Column("resolved", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.UniqueConstraint("user_id", "ref_id", name="uq_weak_spot_user_ref"),
    )
    op.create_index("ix_weak_spots_user_id", "weak_spots", ["user_id"])


def downgrade() -> None:
    op.drop_index("ix_weak_spots_user_id", table_name="weak_spots")
    op.drop_table("weak_spots")
