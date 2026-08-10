"""user_vocab forms + examples

Revision ID: 0019_vocab_forms_examples
Revises: 0018_user_vocab
Create Date: 2026-08-09

On-demand study extras for a personal vocab card (vocab forms slice): `forms` caches
the word's morphological forms (generated once, stable), `examples` holds a small
rolling history of generated usage sentences. Both JSON, nullable — a card without
them just hasn't been expanded yet. No FKs (as everywhere in learner state).
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "0019_vocab_forms_examples"
down_revision = "0018_user_vocab"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("user_vocab", sa.Column("forms", sa.JSON(), nullable=True))
    op.add_column("user_vocab", sa.Column("examples", sa.JSON(), nullable=True))


def downgrade() -> None:
    op.drop_column("user_vocab", "examples")
    op.drop_column("user_vocab", "forms")
