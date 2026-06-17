"""exam blueprints + attempts

Revision ID: 0008_exam
Revises: 0007_speech
Create Date: 2026-06-16

Phase 5 exam simulation: synced blueprints + per-user attempts with the aggregate
CLB report.
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "0008_exam"
down_revision = "0007_speech"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "exam_blueprints",
        sa.Column("id", sa.String(length=64), primary_key=True),
        sa.Column("level", sa.String(length=16), nullable=False),
        sa.Column("data", sa.JSON(), nullable=False),
    )
    op.create_index("ix_exam_blueprints_level", "exam_blueprints", ["level"])

    op.create_table(
        "exam_attempts",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("blueprint_id", sa.String(length=64), nullable=False),
        sa.Column("level", sa.String(length=16), nullable=False),
        sa.Column("status", sa.String(length=16), nullable=False),
        sa.Column("sections", sa.JSON(), nullable=False),
        sa.Column("clb_report", sa.JSON(), nullable=True),
        sa.Column("started_at", sa.DateTime(), nullable=False),
        sa.Column("finished_at", sa.DateTime(), nullable=True),
    )
    op.create_index("ix_exam_attempts_user", "exam_attempts", ["user_id"])
    op.create_index("ix_exam_attempts_blueprint", "exam_attempts", ["blueprint_id"])


def downgrade() -> None:
    op.drop_index("ix_exam_attempts_blueprint", table_name="exam_attempts")
    op.drop_index("ix_exam_attempts_user", table_name="exam_attempts")
    op.drop_table("exam_attempts")
    op.drop_index("ix_exam_blueprints_level", table_name="exam_blueprints")
    op.drop_table("exam_blueprints")
