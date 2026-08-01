"""Speaking loop: transcribe → examiner role-play → (optional) TTS reply.

Honors the speech risks:
- R1: the raw transcript is returned to the caller (shown to the learner).
- R2: the prompt judges content/range/coherence/fluency only — never pronunciation
  (the model sees text, not audio).
- R10: raw audio is never persisted; only the transcript + reply are stored.

Blocking STT/TTS/LLM calls run in a worker thread (plan §4.1). Daily budget via the
shared usage ledger.
"""

from __future__ import annotations

import functools
from dataclasses import dataclass
from datetime import date
from pathlib import Path

import anyio
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.interfaces import Msg
from app.usage.service import add_usage, tokens_used_today

_PROMPT_DIR = Path(__file__).parent / "prompts"
_PROMPTS = {
    "examiner": (_PROMPT_DIR / "examiner.md").read_text(encoding="utf-8"),
    "conversation": (_PROMPT_DIR / "conversation.md").read_text(encoding="utf-8"),
}
_PROFILE = "examiner_roleplay"
_FEATURE = "speaking"

OVER_BUDGET_MESSAGE = "You've reached today's speaking-practice limit. Try again tomorrow."


class SpeechNotConfigured(Exception):
    """No STT provider is configured (speech is disabled)."""


@dataclass(frozen=True)
class TurnResult:
    over_budget: bool
    transcript: str
    reply_text: str
    reply_audio: bytes | None
    provider: str
    model: str
    no_speech: bool = False


class SpeakingExaminer:
    def __init__(self, stt, tts, ai_router) -> None:
        self._stt = stt
        self._tts = tts
        self._router = ai_router

    def system_prompt(self, mode: str) -> str:
        return _PROMPTS.get(mode, _PROMPTS["examiner"])

    async def turn(
        self,
        session: AsyncSession,
        user_id: int,
        *,
        audio: bytes,
        mode: str = "examiner",
        history: list[Msg] | None = None,
        daily_budget: int,
        want_audio: bool = True,
        voice: str = "",
        system_extra: str = "",
        max_tokens: int = 1024,
        today: date | None = None,
    ) -> TurnResult:
        if self._stt is None:
            raise SpeechNotConfigured("no STT provider configured")
        today = today or date.today()
        used = await tokens_used_today(session, user_id, _FEATURE, today)
        if used >= daily_budget:
            return TurnResult(True, "", OVER_BUDGET_MESSAGE, None, "", "")

        transcript = await anyio.to_thread.run_sync(
            functools.partial(self._stt.transcribe, audio=audio, lang="fr")
        )
        # R10: `audio` is used only here; it is never stored.

        # Silence (or audio that decoded to nothing) must not spend an LLM turn or
        # get billed — bail before the router runs. (H9)
        if not transcript.text.strip():
            return TurnResult(False, "", "", None, "", "", no_speech=True)

        system = self.system_prompt(mode) + system_extra
        messages = list(history or []) + [Msg("user", transcript.text)]
        reply = await anyio.to_thread.run_sync(
            functools.partial(
                self._router.run, _PROFILE, system=system, messages=messages, max_tokens=max_tokens
            )
        )
        await add_usage(
            session, user_id, _FEATURE, reply.usage.input_tokens, reply.usage.output_tokens, today
        )

        reply_audio = None
        if want_audio and self._tts is not None:
            reply_audio = await anyio.to_thread.run_sync(
                functools.partial(self._tts.synthesize, text=reply.text, voice=voice, lang="fr")
            )

        return TurnResult(
            False, transcript.text, reply.text, reply_audio, reply.provider, reply.model
        )
