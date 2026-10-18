"""Exam blueprint schema — a timed four-section mock composed of existing content.

The mock references content that other modules own (comprehension sets, writing
tasks, speaking prompts); the exam module orchestrates timing and aggregates the
report. It does not re-implement grading.

Two formats, scored differently (see `app.exam.clb`):
  tef  — TEF Canada: one exam across all levels, reported as a per-skill CLB profile.
  delf — DELF: a separate exam per CEFR level, each section /25, pass = 50/100 with
         at least 5/25 in every section.
"""

from typing import Literal

from pydantic import BaseModel, ConfigDict, model_validator

_Strict = ConfigDict(extra="forbid")

Skill = Literal["reading", "listening", "writing", "speaking"]
ExamFormat = Literal["tef", "delf"]


class ExamSection(BaseModel):
    model_config = _Strict
    skill: Skill
    time_limit_seconds: int
    # reading / listening: one or more sets, taken in order as the section's exercises
    comprehension_set_ids: list[str] = []
    writing_task_ids: list[str] = []  # writing
    speaking_prompts: list[str] = []  # speaking

    @model_validator(mode="after")
    def _refs_match_skill(self) -> "ExamSection":
        if self.skill in ("reading", "listening") and not self.comprehension_set_ids:
            raise ValueError(f"{self.skill} section needs comprehension_set_ids")
        if self.skill == "writing" and not self.writing_task_ids:
            raise ValueError("writing section needs writing_task_ids")
        if self.skill == "speaking" and not self.speaking_prompts:
            raise ValueError("speaking section needs speaking_prompts")
        return self


class ExamBlueprint(BaseModel):
    model_config = _Strict
    id: str
    level: str
    title: str
    format: ExamFormat = "tef"
    sections: list[ExamSection]

    @model_validator(mode="after")
    def _has_sections(self) -> "ExamBlueprint":
        if not self.sections:
            raise ValueError(f"{self.id}: blueprint needs at least one section")
        return self
