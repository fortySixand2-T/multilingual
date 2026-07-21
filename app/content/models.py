"""Content schema: the A1 lesson-path model (Pydantic).

Source of truth is version-controlled YAML (plan §6); these models validate it on
load. `extra="forbid"` everywhere so authoring typos fail loudly instead of
silently dropping fields.

Exercises are a discriminated union on `type` — the Duolingo-style interaction
set. Most types are deterministic (known answer, checked without an LLM →
cost ≈ 0, AC1.4); `translate` is the one that may route to the level-gated
`tutor` for tolerant checking.

IDs (unit/lesson/exercise/vocab) are an immutable contract: learner SRS cards and
progress reference content by these string ids, so renaming one orphans state.
The loader upserts by id; never reuse or rename a published id.
"""

from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

_Strict = ConfigDict(extra="forbid")


# --- exercises (discriminated union on `type`) ---------------------------------


class McqExercise(BaseModel):
    model_config = _Strict
    id: str
    type: Literal["mcq"]
    prompt: str
    options: list[str]
    answer: str
    explain: str = ""

    @model_validator(mode="after")
    def _answer_in_options(self) -> "McqExercise":
        if self.answer not in self.options:
            raise ValueError(f"{self.id}: answer {self.answer!r} not in options")
        return self


class WordBankExercise(BaseModel):
    """Tap tiles to build a sentence — the scaffolded A1 drill (AC1.3)."""

    model_config = _Strict
    id: str
    type: Literal["word_bank"]
    prompt: str
    tokens: list[str]  # the tile bank (includes distractors)
    answer: list[str]  # the correct ordered subset

    @model_validator(mode="after")
    def _answer_drawn_from_tokens(self) -> "WordBankExercise":
        bank = list(self.tokens)
        for tok in self.answer:
            if tok in bank:
                bank.remove(tok)  # multiset check: enough tiles for the answer
            else:
                raise ValueError(f"{self.id}: answer token {tok!r} not in tokens")
        return self


class ListenTypeExercise(BaseModel):
    """Type what you hear — audio_ref is a REAL Québec recording (R6), not TTS."""

    model_config = _Strict
    id: str
    type: Literal["listen_type"]
    audio_ref: str
    answer: str
    prompt: str = ""


class MatchPairsExercise(BaseModel):
    model_config = _Strict
    id: str
    type: Literal["match_pairs"]
    pairs: list[tuple[str, str]]


class TranslateExercise(BaseModel):
    """Short constrained translation. May route to the `tutor` drill_a1 profile
    for tolerant checking; `accept` lists known-good alternates for offline check."""

    model_config = _Strict
    id: str
    type: Literal["translate"]
    prompt: str
    answer: str
    accept: list[str] = []
    via_tutor: bool = True


Exercise = Annotated[
    McqExercise | WordBankExercise | ListenTypeExercise | MatchPairsExercise | TranslateExercise,
    Field(discriminator="type"),
]


# --- lessons, vocab, path ------------------------------------------------------


class Lesson(BaseModel):
    model_config = _Strict
    id: str
    title: str
    grammar_point: str = ""
    est_minutes: int = 5
    new_vocab: list[str] = []  # vocab ids seeded into SRS on completion
    pass_threshold: float = 8.0  # 0–10 scale
    exercises: list[Exercise]


class Vocab(BaseModel):
    model_config = _Strict
    id: str  # this IS the FSRS card key
    fr: str
    en: str
    audio: str = ""
    pos: str = ""
    tags: list[str] = []
    # Grammatical gender of the word, shown to learners as (m)/(fe):
    #   "m"  masculine    "f"  feminine    "mf" both forms exist (e.g. ami / amie)
    #   ""   not gendered (verbs, adverbs, phrases, numerals…)
    # `fem` is the feminine spelling and is REQUIRED for (and only for) "mf" words; its
    # pronunciation clip follows the convention `<level>/audio/<id>_f.mp3`.
    gender: Literal["", "m", "f", "mf"] = ""
    fem: str = ""

    @model_validator(mode="after")
    def _fem_matches_gender(self) -> "Vocab":
        if self.gender == "mf" and not self.fem.strip():
            raise ValueError(f"{self.id}: gender 'mf' requires a `fem` (feminine) form")
        if self.gender != "mf" and self.fem:
            raise ValueError(f"{self.id}: `fem` is only valid for gender 'mf'")
        return self


class UnlockRule(BaseModel):
    model_config = _Strict
    type: Literal["none", "all_of"]
    requires: list[str] = []  # unit or lesson ids


class Unit(BaseModel):
    model_config = _Strict
    id: str
    title: str
    icon: str = ""
    lessons: list[str]  # lesson ids, ordered
    unlock: UnlockRule


class Path(BaseModel):
    model_config = _Strict
    level: str
    title: str
    units: list[Unit]


class ContentBundle(BaseModel):
    """A whole level's content, loaded and cross-validated."""

    model_config = _Strict
    path: Path
    lessons: dict[str, Lesson]
    vocab: dict[str, Vocab]
