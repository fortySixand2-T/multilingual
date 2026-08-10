"""vocab_extra: per-user forms + examples for any card

Revision ID: 0020_vocab_extra
Revises: 0019_vocab_forms_examples
Create Date: 2026-08-09

Consolidate the on-demand study extras (word forms + usage examples) into one
per-user table keyed by (user_id, card_key), so the SAME feature serves both the
shared content bank (card_key = content vocab id) and personal decks (card_key =
`uv:<slug>`). Replaces the card-specific columns added on user_vocab in 0019 —
those shipped days earlier and were never deployed, so there is no data to carry.
FK-free, as everywhere in learner state.
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "0020_vocab_extra"
down_revision = "0019_vocab_forms_examples"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "vocab_extra",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("card_key", sa.String(length=64), nullable=False),
        sa.Column("forms", sa.JSON(), nullable=True),
        sa.Column("examples", sa.JSON(), nullable=True),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint("user_id", "card_key", name="uq_vocabextra_user_card"),
    )
    op.create_index("ix_vocab_extra_user_id", "vocab_extra", ["user_id"])
    # Drop the short-lived per-card columns from 0019 (superseded by vocab_extra).
    op.drop_column("user_vocab", "examples")
    op.drop_column("user_vocab", "forms")


def downgrade() -> None:
    op.add_column("user_vocab", sa.Column("forms", sa.JSON(), nullable=True))
    op.add_column("user_vocab", sa.Column("examples", sa.JSON(), nullable=True))
    op.drop_index("ix_vocab_extra_user_id", table_name="vocab_extra")
    op.drop_table("vocab_extra")
