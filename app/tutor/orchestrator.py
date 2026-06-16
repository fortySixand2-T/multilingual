"""Level-gated tutor orchestration.

A1 mode produces scaffolded micro-drills only (model sentence → one small
manipulation), routed through the `drill_a1` AI profile. The level gate is
structural: at A1 the only operation is `drill`, the system prompt forbids open
conversation/free-form production, and there is no chat method to fall into.

Per-user daily token budgets are enforced *before* the LLM call — over budget
returns a graceful message and makes no provider call (AC1.5).

The router call is synchronous (adapters use blocking HTTP/LiteLLM); we run it in
a worker thread so the async event loop isn't blocked (plan §4.1 concurrency rule).
"""
from __future__ import annotations

import functools
from dataclasses import dataclass
from datetime import date
from pathlib import Path

import anyio
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.interfaces import Msg
from app.tutor.models import TutorDailyUsage

_PROMPT_DIR = Path(__file__).parent / "prompts"
_PROMPT_BY_LEVEL = {"a1": (_PROMPT_DIR / "a1_drill.md").read_text(encoding="utf-8")}
_PROFILE_BY_LEVEL = {"a1": "drill_a1"}

OVER_BUDGET_MESSAGE = (
    "You've hit today's practice limit — come back tomorrow to keep your streak going."
)


@dataclass(frozen=True)
class DrillResult:
    over_budget: bool
    text: str
    provider: str
    model: str
    profile: str
    tokens_used_today: int
    daily_budget: int


async def tokens_used_today(session: AsyncSession, user_id: int, day: date) -> int:
    row = await session.get(TutorDailyUsage, (user_id, day))
    return (row.input_tokens + row.output_tokens) if row else 0


async def _add_usage(
    session: AsyncSession, user_id: int, day: date, input_tokens: int, output_tokens: int
) -> None:
    row = await session.get(TutorDailyUsage, (user_id, day))
    if row is None:
        row = TutorDailyUsage(user_id=user_id, day=day, input_tokens=0, output_tokens=0)
        session.add(row)
        await session.flush()
    row.input_tokens += input_tokens
    row.output_tokens += output_tokens


class Tutor:
    def __init__(self, router, *, level: str = "a1") -> None:
        if level not in _PROFILE_BY_LEVEL:
            raise ValueError(f"unsupported tutor level {level!r}")
        self._router = router
        self._level = level
        self._profile = _PROFILE_BY_LEVEL[level]
        self._system_prompt = _PROMPT_BY_LEVEL[level]

    @property
    def system_prompt(self) -> str:
        return self._system_prompt

    @property
    def profile(self) -> str:
        return self._profile

    def build_messages(
        self, *, grammar_point: str, vocab: list[str], attempt: str | None = None
    ) -> tuple[str, list[Msg]]:
        lines = [
            f"Grammar point: {grammar_point or '(none specified)'}",
            f"Target vocabulary: {', '.join(vocab) if vocab else '(none)'}",
        ]
        if attempt:
            lines.append(
                "The learner's last attempt (give a short scaffolded correction, "
                f"not a conversation): {attempt!r}"
            )
        lines.append("Produce exactly ONE scaffolded micro-drill following the system rules.")
        return self._system_prompt, [Msg("user", "\n".join(lines))]

    async def drill(
        self,
        session: AsyncSession,
        user_id: int,
        *,
        grammar_point: str,
        vocab: list[str],
        attempt: str | None = None,
        daily_budget: int,
        today: date | None = None,
    ) -> DrillResult:
        today = today or date.today()
        used = await tokens_used_today(session, user_id, today)
        if used >= daily_budget:
            return DrillResult(
                over_budget=True,
                text=OVER_BUDGET_MESSAGE,
                provider="",
                model="",
                profile=self._profile,
                tokens_used_today=used,
                daily_budget=daily_budget,
            )

        system, messages = self.build_messages(
            grammar_point=grammar_point, vocab=vocab, attempt=attempt
        )
        result = await anyio.to_thread.run_sync(
            functools.partial(self._router.run, self._profile, system=system, messages=messages)
        )
        spent = result.usage.input_tokens + result.usage.output_tokens
        await _add_usage(
            session, user_id, today, result.usage.input_tokens, result.usage.output_tokens
        )
        return DrillResult(
            over_budget=False,
            text=result.text,
            provider=result.provider,
            model=result.model,
            profile=self._profile,
            tokens_used_today=used + spent,
            daily_budget=daily_budget,
        )
