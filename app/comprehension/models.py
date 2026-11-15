"""Comprehension content schema (reading + listening MCQ sets).

A set is a passage (reading) or an audio clip (listening) with MCQ questions, each
carrying its own explanation (shown after grading). Listening sets are accent-
tagged (R6) and carry a no-replay flag for exam-style practice.

A TCF set (`exam: tcf`) follows the TCF reading paper instead of the TEF: short
documents on one `topic` (a notice, an email, an article), one question each, four
choices.
"""

from typing import Literal

from pydantic import BaseModel, ConfigDict, model_validator

_Strict = ConfigDict(extra="forbid")


class ComprehensionQuestion(BaseModel):
    model_config = _Strict
    id: str
    prompt: str
    options: list[str]
    answer: str
    explain: str = ""

    @model_validator(mode="after")
    def _answer_in_options(self) -> "ComprehensionQuestion":
        if self.answer not in self.options:
            raise ValueError(f"{self.id}: answer {self.answer!r} not in options")
        return self


class ComprehensionSet(BaseModel):
    model_config = _Strict
    id: str
    level: str
    skill: Literal["reading", "listening"]
    title: str
    time_limit_seconds: int | None = None  # timed sets (None = untimed)
    passage: str | None = None  # reading
    audio_ref: str | None = None  # listening — storage key
    script: str | None = None  # listening transcript: TTS source + post-grading review
    accent: str | None = None  # e.g. "qc", "fr" — accent-tagged library
    allow_replay: bool = True  # False = no-replay (exam mode)
    pass_threshold: float = 0.6
    exam: Literal["tef", "tcf"] = "tef"
    topic: str | None = None  # a TCF set's theme: logement, travail, …
    questions: list[ComprehensionQuestion]

    @model_validator(mode="after")
    def _skill_requirements(self) -> "ComprehensionSet":
        if not self.questions:
            raise ValueError(f"{self.id}: needs at least one question")
        if self.skill == "reading" and not self.passage:
            raise ValueError(f"{self.id}: reading set requires a passage")
        if self.skill == "listening" and not self.audio_ref:
            raise ValueError(f"{self.id}: listening set requires an audio_ref")
        if self.exam == "tcf" and not self.topic:
            raise ValueError(f"{self.id}: a TCF set needs a topic")
        if self.exam == "tcf" and any(len(q.options) != 4 for q in self.questions):
            raise ValueError(f"{self.id}: TCF questions have four choices")
        return self
