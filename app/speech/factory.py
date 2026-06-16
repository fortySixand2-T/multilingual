"""Config-driven STT/TTS provider selection (mirrors ai/cache/storage factories).

Default is "disabled" so the app runs without the heavy local models; speech
endpoints then return a clear 503. On a self-host box, set STT_BACKEND=faster-whisper
and TTS_BACKEND=piper. Vendor adapters are imported lazily.
"""
from __future__ import annotations

_OFF = {"disabled", "none", ""}


def build_stt(settings):
    backend = (settings.stt_backend or "disabled").lower()
    if backend in _OFF:
        return None
    if backend == "faster-whisper":
        from app.ai.adapters.faster_whisper_adapter import FasterWhisperAdapter

        return FasterWhisperAdapter(model=settings.whisper_model)
    raise ValueError(f"unknown stt backend '{backend}' (have: faster-whisper, disabled)")


def build_tts(settings):
    backend = (settings.tts_backend or "disabled").lower()
    if backend in _OFF:
        return None
    if backend == "piper":
        from app.ai.adapters.piper_adapter import PiperAdapter

        return PiperAdapter(voice_model=settings.piper_voice)
    raise ValueError(f"unknown tts backend '{backend}' (have: piper, disabled)")
