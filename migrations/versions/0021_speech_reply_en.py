"""english subtitle for a speech turn

Revision ID: 0021_speech_reply_en
Revises: 0020_vocab_extra
Create Date: 2026-09-12

Caches the English translation of an examiner reply. Subtitles are on demand —
the learner presses "English" on a turn — so this is filled lazily and only for
the turns actually asked about. Nullable: existing turns have none, and a turn
never asked about never gets one. Storing it means the same line is translated
(and billed) once, not on every toggle.
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "0021_speech_reply_en"
down_revision = "0020_vocab_extra"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("speech_turns", sa.Column("reply_en", sa.Text(), nullable=True))


def downgrade() -> None:
    op.drop_column("speech_turns", "reply_en")
