"""shared usage + writing assessment

Revision ID: 0006_usage_assessment
Revises: 0005_comprehension
Create Date: 2026-06-15

Replaces the tutor-specific usage table with a shared per-feature daily ledger,
and adds Phase 3 writing tasks + submissions.
"""
from __future__ import annotations

import sqlalchemy as sa

from alembic import op

revision = "0006_usage_assessment"
down_revision = "0005_comprehension"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.drop_table("tutor_daily_usage")

    op.create_table(
        "daily_usage",
        sa.Column("user_id", sa.Integer(), primary_key=True),
        sa.Column("day", sa.Date(), primary_key=True),
        sa.Column("feature", sa.String(length=32), primary_key=True),
        sa.Column("input_tokens", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("output_tokens", sa.Integer(), nullable=False, server_default="0"),
    )

    op.create_table(
        "writing_tasks",
        sa.Column("id", sa.String(length=64), primary_key=True),
        sa.Column("level", sa.String(length=16), nullable=False),
        sa.Column("section", sa.String(length=2), nullable=False),
        sa.Column("data", sa.JSON(), nullable=False),
    )
    op.create_index("ix_writing_tasks_level", "writing_tasks", ["level"])
    op.create_index("ix_writing_tasks_section", "writing_tasks", ["section"])

    op.create_table(
        "writing_submissions",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("task_id", sa.String(length=64), nullable=False),
        sa.Column("text", sa.Text(), nullable=False),
        sa.Column("clb_estimate", sa.Integer(), nullable=True),
        sa.Column("feedback", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
    )
    op.create_index("ix_writing_subs_user", "writing_submissions", ["user_id"])
    op.create_index("ix_writing_subs_task", "writing_submissions", ["task_id"])


def downgrade() -> None:
    op.drop_index("ix_writing_subs_task", table_name="writing_submissions")
    op.drop_index("ix_writing_subs_user", table_name="writing_submissions")
    op.drop_table("writing_submissions")
    op.drop_index("ix_writing_tasks_section", table_name="writing_tasks")
    op.drop_index("ix_writing_tasks_level", table_name="writing_tasks")
    op.drop_table("writing_tasks")
    op.drop_table("daily_usage")

    op.create_table(
        "tutor_daily_usage",
        sa.Column("user_id", sa.Integer(), primary_key=True),
        sa.Column("day", sa.Date(), primary_key=True),
        sa.Column("input_tokens", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("output_tokens", sa.Integer(), nullable=False, server_default="0"),
    )
