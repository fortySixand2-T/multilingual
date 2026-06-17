"""srs + progress tables

Revision ID: 0003_srs_progress
Revises: 0002_content
Create Date: 2026-06-15

Phase 1 learner-state tables: SRS review cards and progress (per-user streak/XP +
lesson completions). Keyed by user_id/lesson_id/vocab-id strings, no FK into
content — content re-syncs never touch learner state.
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "0003_srs_progress"
down_revision = "0002_content"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "srs_cards",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("card_key", sa.String(length=64), nullable=False),
        sa.Column("due", sa.DateTime(), nullable=False),
        sa.Column("state", sa.JSON(), nullable=False),
        sa.UniqueConstraint("user_id", "card_key", name="uq_srs_user_card"),
    )
    op.create_index("ix_srs_cards_user_id", "srs_cards", ["user_id"])
    op.create_index("ix_srs_cards_due", "srs_cards", ["due"])

    op.create_table(
        "progress_user",
        sa.Column("user_id", sa.Integer(), primary_key=True),
        sa.Column("level", sa.String(length=16), nullable=False, server_default="a1"),
        sa.Column("xp", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("streak", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("last_active", sa.Date(), nullable=True),
    )

    op.create_table(
        "progress_lesson_completions",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("lesson_id", sa.String(length=64), nullable=False),
        sa.Column("level", sa.String(length=16), nullable=False),
        sa.Column("score", sa.Float(), nullable=False),
        sa.Column("completed_at", sa.DateTime(), nullable=False),
        sa.UniqueConstraint("user_id", "lesson_id", name="uq_completion_user_lesson"),
    )
    op.create_index("ix_completions_user_id", "progress_lesson_completions", ["user_id"])
    op.create_index("ix_completions_lesson_id", "progress_lesson_completions", ["lesson_id"])


def downgrade() -> None:
    op.drop_index("ix_completions_lesson_id", table_name="progress_lesson_completions")
    op.drop_index("ix_completions_user_id", table_name="progress_lesson_completions")
    op.drop_table("progress_lesson_completions")
    op.drop_table("progress_user")
    op.drop_index("ix_srs_cards_due", table_name="srs_cards")
    op.drop_index("ix_srs_cards_user_id", table_name="srs_cards")
    op.drop_table("srs_cards")
