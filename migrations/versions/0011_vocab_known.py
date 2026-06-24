"""vocab_known: learner-marked known vocabulary (free-study deck state)

Revision ID: 0011_vocab_known
Revises: 0010_truncate_display_names
Create Date: 2026-06-22

One row per (user, vocab id). Marking a deck card "known" inserts; resetting
("still learning") deletes. card_key is the content vocab id as a plain string.
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "0011_vocab_known"
down_revision = "0010_truncate_display_names"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "vocab_known",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("card_key", sa.String(length=64), nullable=False),
        sa.UniqueConstraint("user_id", "card_key", name="uq_known_user_card"),
    )
    op.create_index("ix_vocab_known_user_id", "vocab_known", ["user_id"])


def downgrade() -> None:
    op.drop_index("ix_vocab_known_user_id", table_name="vocab_known")
    op.drop_table("vocab_known")
