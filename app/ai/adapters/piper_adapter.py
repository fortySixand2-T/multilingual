"""TTS via Piper (local, subprocess). Vendor confined to adapters/.

Piper synthesizes WAV to stdout. Blocking; callers run it in a worker thread.
Output is cacheable by (text, voice) — see plan §6.
"""

from __future__ import annotations

import subprocess


def _one_line(text: str) -> str:
    """Piper synthesizes one WAV per input *line* and concatenates them to stdout —
    a malformed stream that audio players stop reading after the first WAV. LLM
    examiner replies span multiple lines, so a multi-sentence reply would cut off at
    the first line break. Collapse all whitespace to a single line so Piper emits
    one WAV; sentence punctuation (`.`, `?`, `!`) still gives natural pauses within it."""
    return " ".join(text.split())


class PiperAdapter:
    name = "piper"

    def __init__(self, *, voice_model: str, piper_bin: str = "piper") -> None:
        self._voice = voice_model
        self._bin = piper_bin

    def synthesize(self, *, text: str, voice: str = "", lang: str = "fr") -> bytes:
        model = voice or self._voice
        proc = subprocess.run(
            [self._bin, "--model", model, "--output_file", "-"],
            input=_one_line(text).encode("utf-8"),
            capture_output=True,
            check=True,
        )
        return proc.stdout  # WAV bytes (one file — see _one_line)
