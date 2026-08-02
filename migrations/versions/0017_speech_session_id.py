"""speech turn session id

Revision ID: 0017_speech_session_id
Revises: 0016_speaking_topics
Create Date: 2026-08-01

Groups speech turns into conversations. A "session" = one topic run (changing the
topic starts a new session); the client generates the id. Nullable so existing
turns (and any client that doesn't send one) keep working — they just aren't
grouped. Used by the end-of-conversation vocab-review endpoint.
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "0017_speech_session_id"
down_revision = "0016_speaking_topics"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("speech_turns", sa.Column("session_id", sa.String(length=64), nullable=True))
    op.create_index("ix_speech_turns_session_id", "speech_turns", ["session_id"])


def downgrade() -> None:
    op.drop_index("ix_speech_turns_session_id", table_name="speech_turns")
    op.drop_column("speech_turns", "session_id")
