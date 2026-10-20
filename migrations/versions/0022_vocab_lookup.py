"""vocab_lookup: shared durable cache of My-deck word lookups

Revision ID: 0022_vocab_lookup
Revises: 0021_speech_reply_en
Create Date: 2026-10-19

One row per word (keyed by ASCII slug), shared across users: meaning, gender, IPA and
the pronunciation clip's storage key. Repeat lookups skip the LLM and TTS entirely.

Also forgets personal cards' cached clips: they were voiced with upmc, which garbles
single words; they re-synthesize on next play with the clearer word voice (siwis).
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "0022_vocab_lookup"
down_revision = "0021_speech_reply_en"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "vocab_lookup",
        sa.Column("slug", sa.String(length=64), primary_key=True),
        sa.Column("fr", sa.String(length=128), nullable=False),
        sa.Column("en", sa.String(length=255), nullable=False),
        sa.Column("gender", sa.String(length=2), nullable=False, server_default=""),
        sa.Column("pos", sa.String(length=16), nullable=False, server_default=""),
        sa.Column("ipa", sa.String(length=64), nullable=False, server_default=""),
        sa.Column("gender_source", sa.String(length=16), nullable=False, server_default=""),
        sa.Column("audio_key", sa.String(length=128), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
    )
    op.execute("UPDATE user_vocab SET audio_key = NULL")


def downgrade() -> None:
    op.drop_table("vocab_lookup")
