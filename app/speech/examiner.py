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

# Appended to the system prompt to make the examiner open the conversation itself,
# before the learner has said anything. Paired with a neutral stage-direction cue
# (the model needs a user turn) so the reply is a spoken French greeting + question.
_OPENER_DIRECTIVE = (
    "\n\n## Start the conversation\n"
    "The learner has just begun this session and hasn't spoken yet. Open the "
    "conversation yourself: greet them warmly in simple French and ask your first "
    "question to get them talking. Keep it to one or two short sentences."
)
_OPENER_CUE = "[The learner just opened the session and is ready. Greet them and begin.]"

# Free-conversation openers (no topic picked) are the same every time, so they're
# canned rather than generated: no LLM call, nothing billed, and the synthesized
# audio is cached once per mode and shared across sessions. Topic openers still go
# through the LLM (examiner.opener) since they're framed around the picked task.
# Plain TTS-safe French prose: one greeting + one question, no markup/emoji.
_CANNED_OPENERS = {
    "conversation": (
        "Bonjour ! Je suis content de discuter avec vous aujourd'hui. "
        "De quoi avez-vous envie de parler ?"
    ),
    "examiner": (
        "Bonjour ! Nous allons faire un peu de conversation en français. "
        "Pour commencer, pouvez-vous vous présenter en quelques mots ?"
    ),
}


def canned_opener(mode: str) -> tuple[str, str]:
    """(canonical_mode, greeting) for a free-conversation opener. Unknown modes fall
    back to the examiner greeting. The canonical mode keys the shared audio cache so
    every session's canned opener reuses one synthesized clip."""
    canon = mode if mode in _CANNED_OPENERS else "examiner"
    return canon, _CANNED_OPENERS[canon]


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

    async def opener(
        self,
        session: AsyncSession,
        user_id: int,
        *,
        mode: str = "examiner",
        daily_budget: int,
        want_audio: bool = True,
        voice: str = "",
        system_extra: str = "",
        max_tokens: int = 1024,
        today: date | None = None,
    ) -> TurnResult:
        """The examiner's opening line — spoken before the learner says anything, so
        a session starts as a conversation instead of a cold prompt. No STT (there's
        no learner audio yet); billed against the same daily ledger as a spoken turn.
        Returns a TurnResult with an empty transcript (the opener has no utterance)."""
        today = today or date.today()
        used = await tokens_used_today(session, user_id, _FEATURE, today)
        if used >= daily_budget:
            return TurnResult(True, "", OVER_BUDGET_MESSAGE, None, "", "")

        system = self.system_prompt(mode) + system_extra + _OPENER_DIRECTIVE
        reply = await anyio.to_thread.run_sync(
            functools.partial(
                self._router.run,
                _PROFILE,
                system=system,
                messages=[Msg("user", _OPENER_CUE)],
                max_tokens=max_tokens,
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

        return TurnResult(False, "", reply.text, reply_audio, reply.provider, reply.model)
