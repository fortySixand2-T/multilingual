"""comprehension pass marker

Revision ID: 0009_comprehension_pass
Revises: 0008_exam
Create Date: 2026-06-20

One row per (user, set) first in-time pass. The unique key makes the comprehension XP
award atomic so concurrent submits can't double-pay (qa-100).
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "0009_comprehension_pass"
down_revision = "0008_exam"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "comprehension_passes",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("set_id", sa.String(length=64), nullable=False),
        sa.Column("awarded_at", sa.DateTime(), nullable=False),
        sa.UniqueConstraint("user_id", "set_id", name="uq_comprehension_pass"),
    )
    op.create_index("ix_comprehension_passes_user", "comprehension_passes", ["user_id"])
    op.create_index("ix_comprehension_passes_set", "comprehension_passes", ["set_id"])


def downgrade() -> None:
    op.drop_index("ix_comprehension_passes_set", table_name="comprehension_passes")
    op.drop_index("ix_comprehension_passes_user", table_name="comprehension_passes")
    op.drop_table("comprehension_passes")
