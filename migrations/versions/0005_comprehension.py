"""comprehension sets + attempts

Revision ID: 0005_comprehension
Revises: 0004_tutor
Create Date: 2026-06-15

Phase 2 comprehension: synced reading/listening sets (JSON blob) and per-user
attempts.
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "0005_comprehension"
down_revision = "0004_tutor"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "comprehension_sets",
        sa.Column("id", sa.String(length=64), primary_key=True),
        sa.Column("level", sa.String(length=16), nullable=False),
        sa.Column("skill", sa.String(length=16), nullable=False),
        sa.Column("accent", sa.String(length=16), nullable=True),
        sa.Column("data", sa.JSON(), nullable=False),
    )
    op.create_index("ix_comp_sets_level", "comprehension_sets", ["level"])
    op.create_index("ix_comp_sets_skill", "comprehension_sets", ["skill"])

    op.create_table(
        "comprehension_attempts",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("set_id", sa.String(length=64), nullable=False),
        sa.Column("score", sa.Float(), nullable=False),
        sa.Column("elapsed_seconds", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
    )
    op.create_index("ix_comp_attempts_user", "comprehension_attempts", ["user_id"])
    op.create_index("ix_comp_attempts_set", "comprehension_attempts", ["set_id"])


def downgrade() -> None:
    op.drop_index("ix_comp_attempts_set", table_name="comprehension_attempts")
    op.drop_index("ix_comp_attempts_user", table_name="comprehension_attempts")
    op.drop_table("comprehension_attempts")
    op.drop_index("ix_comp_sets_skill", table_name="comprehension_sets")
    op.drop_index("ix_comp_sets_level", table_name="comprehension_sets")
    op.drop_table("comprehension_sets")
