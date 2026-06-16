"""Speech turns. Stores the transcript + examiner reply only — never the raw
learner audio (R10: voice data discarded post-transcription by default)."""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.users.models import Base


class SpeechTurn(Base):
    __tablename__ = "speech_turns"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(Integer, index=True)
    mode: Mapped[str] = mapped_column(String(16))
    transcript: Mapped[str] = mapped_column(Text)            # what the learner said
    reply_text: Mapped[str] = mapped_column(Text)            # examiner reply
    reply_audio_key: Mapped[str | None] = mapped_column(String(128), nullable=True)  # TTS in storage
    created_at: Mapped[datetime] = mapped_column(DateTime)
    # NOTE: deliberately no column for the uploaded audio — R10.
