"""STT via faster-whisper (local). Vendor lib imported lazily, confined to adapters/.

Self-host path (plan §4.1): runs on CPU/GPU on the same box. The model is loaded
once at construction; transcription is a blocking call, so callers run it in a
worker thread.
"""
from __future__ import annotations

import io

from app.ai.interfaces import Transcript


class FasterWhisperAdapter:
    name = "faster-whisper"

    def __init__(self, *, model: str = "large-v3", device: str = "cpu", compute_type: str = "int8") -> None:
        from faster_whisper import WhisperModel  # lazy: heavy dep only when used

        self._model = WhisperModel(model, device=device, compute_type=compute_type)

    def transcribe(self, *, audio: bytes, lang: str = "fr") -> Transcript:
        # R1: lower the model's tendency to "fix" learner errors — no internal
        # language-model rescoring beyond default; we surface the raw transcript.
        segments, _info = self._model.transcribe(io.BytesIO(audio), language=lang)
        text = " ".join(seg.text for seg in segments).strip()
        return Transcript(text=text, provider=self.name)
