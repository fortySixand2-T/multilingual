"""lesson attempts + waive: escape hatch for the learning path

Revision ID: 0014_lesson_attempts
Revises: 0013_invites
Create Date: 2026-07-25

Progression no longer hard-blocks on mastery. A per-lesson row can now exist
before the lesson is passed: `attempts` counts failed tries, and after enough of
them the learner may `waived`=true a lesson to unlock the next unit while it stays
flagged for review. Gating counts passed-OR-waived; the star still means passed.
Existing rows are passes, so they backfill passed=true / waived=false / attempts=0.
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "0014_lesson_attempts"
down_revision = "0013_invites"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "progress_lesson_completions",
        sa.Column("passed", sa.Boolean(), nullable=False, server_default=sa.true()),
    )
    op.add_column(
        "progress_lesson_completions",
        sa.Column("waived", sa.Boolean(), nullable=False, server_default=sa.false()),
    )
    op.add_column(
        "progress_lesson_completions",
        sa.Column("attempts", sa.Integer(), nullable=False, server_default="0"),
    )


def downgrade() -> None:
    op.drop_column("progress_lesson_completions", "attempts")
    op.drop_column("progress_lesson_completions", "waived")
    op.drop_column("progress_lesson_completions", "passed")
