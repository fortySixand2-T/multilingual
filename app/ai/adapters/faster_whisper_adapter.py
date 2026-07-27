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

    def __init__(
        self, *, model: str = "large-v3", device: str = "cpu", compute_type: str = "int8"
    ) -> None:
        from faster_whisper import WhisperModel  # lazy: heavy dep only when used

        self._model = WhisperModel(model, device=device, compute_type=compute_type)

    def transcribe(self, *, audio: bytes, lang: str = "fr") -> Transcript:
        from app.ai.errors import TranscriptionError

        # R1: lower the model's tendency to "fix" learner errors — no internal
        # language-model rescoring beyond default; we surface the raw transcript.
        try:
            # vad_filter: strip non-speech before decoding. Without it, Whisper
            # hallucinates phantom text on silence (e.g. "Sous-titres réalisés par
            # la communauté d'Amara.org"), which would bill a blank turn (H9).
            segments, _info = self._model.transcribe(
                io.BytesIO(audio), language=lang, vad_filter=True
            )
            # segments is a generator; decoding happens as it's consumed, so a
            # corrupt/non-audio upload raises here, not on the call above.
            text = " ".join(seg.text for seg in segments).strip()
        except Exception as e:  # noqa: BLE001 — any decode/inference failure is a bad upload
            raise TranscriptionError("could not decode the supplied audio") from e
        return Transcript(text=text, provider=self.name)
