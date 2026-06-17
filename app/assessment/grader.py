"""Writing grader: routes through the `writing_feedback` profile, parses the
strict-JSON result, validates it, and enforces a daily budget.

Robustness for R3: low temperature + few-shot-anchored prompt (in the prompt
file) keep scores stable; strict parse + Pydantic validation reject a malformed
grade instead of silently trusting it.
"""

from __future__ import annotations

import functools
import json
import re
from dataclasses import dataclass
from datetime import date
from pathlib import Path

import anyio
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.interfaces import Msg
from app.assessment.models import WritingFeedback
from app.usage.service import add_usage, tokens_used_today

_PROMPT = (Path(__file__).parent / "prompts" / "writing_grader.md").read_text(encoding="utf-8")
_PROFILE = "writing_feedback"
_FEATURE = "writing_feedback"

OVER_BUDGET_MESSAGE = "You've reached today's writing-feedback limit. Try again tomorrow."


class GradingError(Exception):
    """The model's response could not be parsed/validated as feedback."""


@dataclass(frozen=True)
class GradeResult:
    over_budget: bool
    feedback: WritingFeedback | None
    provider: str
    model: str
    tokens_used_today: int
    daily_budget: int
    word_count: int


def extract_json(text: str) -> dict:
    """Pull a JSON object out of the model's reply (tolerates code fences/prose)."""
    fenced = re.search(r"```(?:json)?\s*(\{.*\})\s*```", text, re.S)
    blob = fenced.group(1) if fenced else None
    if blob is None:
        start, end = text.find("{"), text.rfind("}")
        if start == -1 or end == -1 or end < start:
            raise GradingError("no JSON object found in model response")
        blob = text[start : end + 1]
    try:
        return json.loads(blob)
    except json.JSONDecodeError as e:
        raise GradingError(f"invalid JSON from model: {e}") from e


def parse_feedback(text: str) -> WritingFeedback:
    return WritingFeedback.model_validate(extract_json(text))


class WritingGrader:
    def __init__(self, router) -> None:
        self._router = router
        self._system = _PROMPT

    def build_messages(
        self, *, task_prompt: str, section: str, submission: str
    ) -> tuple[str, list[Msg]]:
        user = (
            f"Section: {section}\n"
            f"Task: {task_prompt}\n\n"
            f'Learner\'s submission:\n"""\n{submission}\n"""\n\n'
            "Grade it and return only the JSON object."
        )
        return self._system, [Msg("user", user)]

    async def grade(
        self,
        session: AsyncSession,
        user_id: int,
        *,
        task_prompt: str,
        section: str,
        submission: str,
        daily_budget: int,
        today: date | None = None,
    ) -> GradeResult:
        today = today or date.today()
        word_count = len(submission.split())
        used = await tokens_used_today(session, user_id, _FEATURE, today)
        if used >= daily_budget:
            return GradeResult(True, None, "", "", used, daily_budget, word_count)

        system, messages = self.build_messages(
            task_prompt=task_prompt, section=section, submission=submission
        )
        result = await anyio.to_thread.run_sync(
            functools.partial(
                self._router.run,
                _PROFILE,
                system=system,
                messages=messages,
                temperature=0.1,
                max_tokens=1500,
            )
        )
        spent = result.usage.input_tokens + result.usage.output_tokens
        await add_usage(
            session, user_id, _FEATURE, result.usage.input_tokens, result.usage.output_tokens, today
        )
        feedback = parse_feedback(result.text)  # raises GradingError on bad output
        return GradeResult(
            False, feedback, result.provider, result.model, used + spent, daily_budget, word_count
        )
