"""user vocab (personal decks)

Revision ID: 0018_user_vocab
Revises: 0017_speech_session_id
Create Date: 2026-08-04

Per-user personal vocab cards (Slice E). Distinct from the shared content bank; the
SRS card_key is namespaced `uv:<slug>` so the review queue routes it here instead of
to content_vocab. No FKs — SRS/progress reference cards by string id, as everywhere.
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "0018_user_vocab"
down_revision = "0017_speech_session_id"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "user_vocab",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("card_key", sa.String(length=64), nullable=False),
        sa.Column("fr", sa.String(length=128), nullable=False),
        sa.Column("en", sa.String(length=255), nullable=False),
        sa.Column("gender", sa.String(length=2), nullable=False, server_default=""),
        sa.Column("pos", sa.String(length=16), nullable=False, server_default=""),
        sa.Column("ipa", sa.String(length=64), nullable=False, server_default=""),
        sa.Column("source", sa.String(length=32), nullable=False, server_default=""),
        sa.Column("audio_key", sa.String(length=128), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint("user_id", "card_key", name="uq_uservocab_user_card"),
    )
    op.create_index("ix_user_vocab_user_id", "user_vocab", ["user_id"])


def downgrade() -> None:
    op.drop_index("ix_user_vocab_user_id", table_name="user_vocab")
    op.drop_table("user_vocab")
