"""Writing assessment schema.

`WritingTask` is authored content (the two TEF Expression écrite task types).
`WritingFeedback` is the strict-JSON grading contract the LLM must return — per-
criterion scores, inline corrections that cite a grammar reference (R4), and a CLB
estimate (clamped to a valid band). Parsing is lenient on extra keys but strict on
structure, so a malformed grade is caught rather than silently trusted (R3).
"""

from typing import Literal

from pydantic import BaseModel, ConfigDict, field_validator


class WritingTask(BaseModel):
    model_config = ConfigDict(extra="forbid")
    id: str
    level: str
    section: Literal["A", "B"]  # TEF tâche 1 (short response) / tâche 2 (argumentative)
    title: str
    prompt: str
    min_words: int
    max_words: int | None = None


class InlineCorrection(BaseModel):
    model_config = ConfigDict(extra="ignore")
    excerpt: str
    correction: str
    explanation: str
    reference: str = ""  # cited grammar reference (R4)


class CriterionScore(BaseModel):
    model_config = ConfigDict(extra="ignore")
    name: str
    score: int  # 0–10
    comment: str = ""


class WritingFeedback(BaseModel):
    model_config = ConfigDict(extra="ignore")
    clb_estimate: int  # 1–12
    criteria: list[CriterionScore]
    corrections: list[InlineCorrection]
    overall: str

    @field_validator("clb_estimate")
    @classmethod
    def _clamp_clb(cls, v: int) -> int:
        return max(1, min(12, v))
