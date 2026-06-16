"""tutor daily usage table

Revision ID: 0004_tutor
Revises: 0003_srs_progress
Create Date: 2026-06-15

Per-user/day tutor token usage for daily-budget enforcement (AC1.5).
"""
from __future__ import annotations

import sqlalchemy as sa

from alembic import op

revision = "0004_tutor"
down_revision = "0003_srs_progress"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "tutor_daily_usage",
        sa.Column("user_id", sa.Integer(), primary_key=True),
        sa.Column("day", sa.Date(), primary_key=True),
        sa.Column("input_tokens", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("output_tokens", sa.Integer(), nullable=False, server_default="0"),
    )


def downgrade() -> None:
    op.drop_table("tutor_daily_usage")
