"""daily xp ledger: per-(user, day, source) XP for the daily-goal ring + caps

Revision ID: 0015_daily_xp
Revises: 0014_lesson_attempts
Create Date: 2026-07-27

Records XP earned per source per day. The daily-goal ring sums a day's rows;
repeatable activities (review/drill) claim their bonus once per day via the
unique (user, day, source) marker so they can't be farmed. Additive — no
backfill needed (a fresh day starts empty; lifetime xp stays on progress_user).
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "0015_daily_xp"
down_revision = "0014_lesson_attempts"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "progress_daily_xp",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("day", sa.Date(), nullable=False),
        sa.Column("source", sa.String(length=24), nullable=False),
        sa.Column("xp", sa.Integer(), nullable=False, server_default="0"),
        sa.UniqueConstraint("user_id", "day", "source", name="uq_daily_xp_user_day_source"),
    )
    op.create_index("ix_progress_daily_xp_user_id", "progress_daily_xp", ["user_id"])
    op.create_index("ix_progress_daily_xp_day", "progress_daily_xp", ["day"])


def downgrade() -> None:
    op.drop_index("ix_progress_daily_xp_day", table_name="progress_daily_xp")
    op.drop_index("ix_progress_daily_xp_user_id", table_name="progress_daily_xp")
    op.drop_table("progress_daily_xp")
