"""Regression tests for the round-055 content QA fixes (issues 750-755).

Covers:
- 750: a garbled mcq option in health-b1-01.e5.
- 751: an over-accepting `accept` entry in food-04.e7.
- 752/753/754: new_vocab words that were never shown in any exercise
  (adjectives-01, medias-b2-01, verbs-01, verbs-02).
- 755: the systemic new_vocab/exercise-coverage gap, now guarded across
  *every* lesson at every level rather than just the round's new lessons.
  Every `new_vocab` id should be resolvable to a headword that
  shows up somewhere in the lesson's own exercises (allowing for inflected/
  agreement forms via a stem match), since new_vocab is exactly what seeds
  SRS review cards on first lesson pass (`app.progress.api.seed_cards`).
"""

from __future__ import annotations

from app.content.loader import load_content
from scripts.check_content import (
    CONTENT_ROOT,
    KNOWN_GAPS,
    missing_words,
)
from scripts.check_content import (
    norm as _norm,
)
from scripts.check_content import (
    shown_in_lesson as _shown_in_lesson,
)

# Lessons from the round-055 new-lesson arc (PRs #87-#90) that issue 755 swept.
# `vouloir` in a1/verbs-01 is a known, human-verified exception: it's shown via
# the conjugated form "veux" as the graded word_bank answer in e6, which a
# literal/stemmed headword match can't detect.
KNOWN_CONJUGATED_ONLY = {("a1", "verbs-01"): {"vouloir"}}

LEVELS = ("a1", "a2", "b1", "b2")


def _missing_words(level: str, lesson_id: str) -> list[str]:
    return missing_words(level, lesson_id, load_content(CONTENT_ROOT, level))


def test_health_b1_01_e5_mcq_options_are_well_formed():
    """Issue 750: the second mcq option was the garbled 'allée aller'."""
    bundle = load_content(CONTENT_ROOT, "b1")
    ex = next(e for e in bundle.lessons["health-b1-01"].exercises if e.id == "health-b1-01.e5")
    assert ex.options == ["allé", "allée", "vais"]
    assert all(" " not in o for o in ex.options), "each mcq option should be a single word/phrase"


def test_food_04_e7_accept_does_not_over_specify():
    """Issue 751: 'accept' shouldn't add unrequested meaning (red wine) to a
    prompt that only asked for 'a glass of wine'."""
    bundle = load_content(CONTENT_ROOT, "a1")
    ex = next(e for e in bundle.lessons["food-04"].exercises if e.id == "food-04.e7")
    accept = ex.accept or []
    assert "un verre de vin rouge" not in accept
    assert all("rouge" not in a for a in accept)


def test_anchor_lessons_have_no_unpracticed_new_vocab():
    """Issues 752/753/754: adjectives-01, medias-b2-01, verbs-01, verbs-02 each
    had several new_vocab words never shown in any exercise; closed by adding
    a match_pairs exercise covering the gap."""
    for level, lesson_id in [
        ("a1", "adjectives-01"),
        ("b2", "medias-b2-01"),
        ("a1", "verbs-01"),
        ("a1", "verbs-02"),
    ]:
        missing = _missing_words(level, lesson_id)
        assert missing == [], f"{level}/{lesson_id} still has unpracticed new_vocab: {missing}"


def _iter_lessons():
    for level in LEVELS:
        bundle = load_content(CONTENT_ROOT, level)
        for lesson_id, lesson in bundle.lessons.items():
            if lesson.new_vocab:
                yield level, lesson_id


def test_all_lessons_new_vocab_is_practiced_in_exercises():
    """Every lesson's `new_vocab` should be shown (verbatim or via an inflected
    stem) in at least one of that lesson's own exercises — `new_vocab` seeds SRS
    cards on first pass, so a gap means a learner is quizzed on a word they were
    never taught. Known legacy gaps are carved out via KNOWN_GAPS."""
    failures = {}
    for level, lesson_id in _iter_lessons():
        missing = set(_missing_words(level, lesson_id))
        allowed = KNOWN_GAPS.get((level, lesson_id), set())
        unexpected = missing - allowed
        if unexpected:
            failures[f"{level}/{lesson_id}"] = sorted(unexpected)
    assert not failures, f"new_vocab words never shown in exercises: {failures}"


def test_known_gaps_are_not_stale():
    """KNOWN_GAPS may only shrink. Once a legacy lesson is fixed, its entry has
    to be deleted, so the carve-out can never quietly outlive the defect."""
    stale = {}
    for (level, lesson_id), allowed in KNOWN_GAPS.items():
        missing = set(_missing_words(level, lesson_id))
        fixed = allowed - missing
        if fixed:
            stale[f"{level}/{lesson_id}"] = sorted(fixed)
    assert not stale, f"these words are now practiced -- remove them from KNOWN_GAPS: {stale}"


def test_shown_in_lesson_rejects_unrelated_prefix_matches():
    """The matcher used to accept any word sharing a 4-char prefix, so lessons
    counted as teaching a word they never showed: `serviette` passed on
    "serveur", `chaussette` on "chaussures", `patin` on "patinoire", and
    `transition` / `probation` / `electrique` on the English prompt and gloss
    text ("translate:", "probationary", "electric")."""
    for headword, blob in [
        ("serviette", "le serveur | waiter"),
        ("chaussette", "chaussures | shoes"),
        ("patin", "patinoire | skating rink"),
        ("transition", "translate: “the climate”"),
        ("probation", "probationary period"),
        ("electrique", "electric"),
        ("partir", "past participle"),
        ("jour", "aujourdhui"),
        ("entrainement", "entraineur | coach"),
        ("blesse", "blessure | injury"),
    ]:
        assert not _shown_in_lesson(_norm(headword), _norm(blob)), (
            f"{headword!r} should not count as shown by {blob!r}"
        )


def test_shown_in_lesson_still_accepts_real_inflections():
    """Tightening the matcher must not lose genuine agreement/conjugation
    forms, which is the whole reason it is not an equality check."""
    for headword, blob in [
        ("regarder", "je regarde la télé"),
        ("ajouter", "on ajoute du sel"),
        ("aider", "aidez-moi !"),
        ("brancher", "branchez, puis attendez"),
        ("compostage", "en compostant les restes"),
        ("ami", "mes amis | my friends"),
        ("arrivee", "il arrive demain"),
    ]:
        assert _shown_in_lesson(_norm(headword), _norm(blob)), (
            f"{headword!r} should count as shown by {blob!r}"
        )


def test_shown_in_lesson_requires_whole_multiword_phrase():
    """A multi-word headword is not taught by showing only its first word --
    `transport en commun` is not covered by "transport"."""
    assert not _shown_in_lesson(_norm("transport en commun"), _norm("transport | voirie"))
    assert _shown_in_lesson(
        _norm("transport en commun"), _norm("le transport en commun est frequent")
    )
    # word_bank answers are joined into a sentence so the phrase stays contiguous
    assert _shown_in_lesson(_norm("beau temps"), _norm("il fait beau temps aujourdhui"))
