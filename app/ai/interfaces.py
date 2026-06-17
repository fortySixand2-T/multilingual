"""Vendor-free capability interfaces. Domain code depends only on these.

No provider SDK is ever imported here or anywhere outside app/ai/adapters/.
STT/TTS protocols are defined now (Phase 0) but get adapters in Phase 4.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol, runtime_checkable


@dataclass(frozen=True)
class Msg:
    role: str  # "user" | "assistant"
    content: str


@dataclass(frozen=True)
class Usage:
    input_tokens: int = 0
    output_tokens: int = 0
    cost_usd: float = 0.0


@dataclass(frozen=True)
class LLMResult:
    text: str
    provider: str
    model: str
    usage: Usage


@runtime_checkable
class LLMProvider(Protocol):
    name: str

    def complete(
        self,
        *,
        system: str,
        messages: list[Msg],
        model: str,
        temperature: float = 0.3,
        max_tokens: int = 1024,
    ) -> LLMResult: ...


@dataclass(frozen=True)
class Transcript:
    text: str
    provider: str


@runtime_checkable
class STTProvider(Protocol):
    name: str

    def transcribe(self, *, audio: bytes, lang: str = "fr") -> Transcript: ...


@runtime_checkable
class TTSProvider(Protocol):
    name: str

    def synthesize(self, *, text: str, voice: str, lang: str = "fr") -> bytes: ...
