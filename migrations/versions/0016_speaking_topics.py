"""speaking topics

Revision ID: 0016_speaking_topics
Revises: 0015_daily_xp
Create Date: 2026-08-01

Authored TEF Expression Orale topics the learner picks to frame a speaking
session. Synced per level (delete-and-replace), like writing_tasks.
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "0016_speaking_topics"
down_revision = "0015_daily_xp"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "speaking_topics",
        sa.Column("id", sa.String(length=64), primary_key=True),
        sa.Column("level", sa.String(length=16), nullable=False),
        sa.Column("section", sa.String(length=2), nullable=False),
        sa.Column("data", sa.JSON(), nullable=False),
    )
    op.create_index("ix_speaking_topics_level", "speaking_topics", ["level"])
    op.create_index("ix_speaking_topics_section", "speaking_topics", ["section"])


def downgrade() -> None:
    op.drop_index("ix_speaking_topics_section", table_name="speaking_topics")
    op.drop_index("ix_speaking_topics_level", table_name="speaking_topics")
    op.drop_table("speaking_topics")
