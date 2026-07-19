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

# The controlled set of grammatical families a lesson's `grammar_point` can belong to.
# It's the guiding axis for the grammar reference (grouping/filtering by structure, not
# by theme). Authoring must pick one of these exact labels — an off-list value fails the
# load, so the taxonomy can't silently drift as content grows.
GRAMMAR_CATEGORIES: tuple[str, ...] = (
    "Verb conjugation & tenses",
    "Subjunctive",
    "Pronouns",
    "Articles & determiners",
    "Adjectives & comparison",
    "Logical connectors",
    "Sentence structures",
    "Expressions & communication",
)


class Lesson(BaseModel):
    model_config = _Strict
    id: str
    title: str
    grammar_point: str = ""
    grammar_category: str = ""  # one of GRAMMAR_CATEGORIES (guides the grammar reference)
    est_minutes: int = 5
    new_vocab: list[str] = []  # vocab ids seeded into SRS on completion
    pass_threshold: float = 8.0  # 0–10 scale
    exercises: list[Exercise]

    @model_validator(mode="after")
    def _known_grammar_category(self) -> "Lesson":
        if self.grammar_category and self.grammar_category not in GRAMMAR_CATEGORIES:
            raise ValueError(
                f"{self.id}: grammar_category {self.grammar_category!r} not one of "
                f"{GRAMMAR_CATEGORIES}"
            )
        return self


class Vocab(BaseModel):
    model_config = _Strict
    id: str  # this IS the FSRS card key
    fr: str
    en: str
    audio: str = ""
    pos: str = ""
    tags: list[str] = []


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
