"""speech turns

Revision ID: 0007_speech
Revises: 0006_usage_assessment
Create Date: 2026-06-16

Phase 4 speaking: stores transcript + examiner reply (and a key to the cached TTS
reply). Deliberately no raw-audio column — learner audio is discarded after
transcription (R10).
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "0007_speech"
down_revision = "0006_usage_assessment"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "speech_turns",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("mode", sa.String(length=16), nullable=False),
        sa.Column("transcript", sa.Text(), nullable=False),
        sa.Column("reply_text", sa.Text(), nullable=False),
        sa.Column("reply_audio_key", sa.String(length=128), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
    )
    op.create_index("ix_speech_turns_user", "speech_turns", ["user_id"])


def downgrade() -> None:
    op.drop_index("ix_speech_turns_user", table_name="speech_turns")
    op.drop_table("speech_turns")
