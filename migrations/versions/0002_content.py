"""content: units, lessons, vocab tables

Revision ID: 0002_content
Revises: 0001_init
Create Date: 2026-06-15

Phase 1 content store (DB target of the file sync). Lessons/vocab keep their
authored shape in a JSON column so re-authoring doesn't require a migration.
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "0002_content"
down_revision = "0001_init"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "content_units",
        sa.Column("id", sa.String(length=64), primary_key=True),
        sa.Column("level", sa.String(length=16), nullable=False),
        sa.Column("ordinal", sa.Integer(), nullable=False),
        sa.Column("title", sa.String(length=200), nullable=False),
        sa.Column("icon", sa.String(length=64), nullable=False, server_default=""),
        sa.Column("lessons", sa.JSON(), nullable=False),
        sa.Column("unlock_type", sa.String(length=16), nullable=False),
        sa.Column("unlock_requires", sa.JSON(), nullable=False),
    )
    op.create_index("ix_content_units_level", "content_units", ["level"])

    op.create_table(
        "content_lessons",
        sa.Column("id", sa.String(length=64), primary_key=True),
        sa.Column("level", sa.String(length=16), nullable=False),
        sa.Column("title", sa.String(length=200), nullable=False),
        sa.Column("data", sa.JSON(), nullable=False),
    )
    op.create_index("ix_content_lessons_level", "content_lessons", ["level"])

    op.create_table(
        "content_vocab",
        sa.Column("id", sa.String(length=64), primary_key=True),
        sa.Column("level", sa.String(length=16), nullable=False),
        sa.Column("data", sa.JSON(), nullable=False),
    )
    op.create_index("ix_content_vocab_level", "content_vocab", ["level"])


def downgrade() -> None:
    op.drop_index("ix_content_vocab_level", table_name="content_vocab")
    op.drop_table("content_vocab")
    op.drop_index("ix_content_lessons_level", table_name="content_lessons")
    op.drop_table("content_lessons")
    op.drop_index("ix_content_units_level", table_name="content_units")
    op.drop_table("content_units")
