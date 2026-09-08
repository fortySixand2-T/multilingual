"""Regression tests for the round-055 content QA fixes (issues 750-755).

Covers:
- 750: a garbled mcq option in health-b1-01.e5.
- 751: an over-accepting `accept` entry in food-04.e7.
- 752/753/754: new_vocab words that were never shown in any exercise
  (adjectives-01, medias-b2-01, verbs-01, verbs-02).
- 755: the systemic new_vocab/exercise-coverage gap across the round's new
  lessons — every `new_vocab` id should be resolvable to a headword that
  shows up somewhere in the lesson's own exercises (allowing for inflected/
  agreement forms via a stem match), since new_vocab is exactly what seeds
  SRS review cards on first lesson pass (`app.progress.api.seed_cards`).
"""

from __future__ import annotations

import re
import unicodedata
from pathlib import Path

from app.content.loader import load_content
from app.content.models import Exercise

CONTENT_ROOT = Path(__file__).resolve().parents[1] / "content"

# Lessons from the round-055 new-lesson arc (PRs #87-#90) that issue 755 swept.
# `vouloir` in a1/verbs-01 is a known, human-verified exception: it's shown via
# the conjugated form "veux" as the graded word_bank answer in e6, which a
# literal/stemmed headword match can't detect.
KNOWN_CONJUGATED_ONLY = {("a1", "verbs-01"): {"vouloir"}}

TARGET_LESSONS = [
    ("a1", "house-01"), ("a1", "places-01"), ("a1", "jobs-01"),
    ("a1", "countries-01"), ("a1", "verbs-01"), ("a1", "verbs-02"),
    ("a1", "adjectives-01"),
    ("a2", "money-a2-01"), ("a2", "nature-a2-01"), ("a2", "studies-a2-01"),
    ("a2", "sports-a2-01"), ("a2", "communication-a2-01"),
    ("a2", "people-a2-01"), ("a2", "emergencies-a2-01"),
    ("a2", "travail-a2-04"), ("a2", "sante-a2-04"), ("a2", "transport-a2-04"),
    ("b1", "immigration-b1-04"), ("b1", "travail-b1-04"),
    ("b1", "logement-b1-04"), ("b1", "argent-b1-04"), ("b1", "rights-b1-01"),
    ("b1", "relationships-b1-01"), ("b1", "tourism-b1-01"),
    ("b1", "food-b1-01"), ("b1", "mobility-b1-01"), ("b1", "arts-b1-01"),
    ("b1", "technology-b1-01"),
    ("b2", "justice-b2-01"), ("b2", "technologie-b2-01"),
    ("b2", "education-b2-01"), ("b2", "medias-b2-01"),
    ("b2", "migration-b2-01"), ("b2", "entreprise-b2-01"),
    ("b2", "psychologie-b2-01"), ("b2", "histoire-b2-01"),
    ("b2", "sante-b2-04"), ("b2", "societe-b2-04"),
    ("b2", "environnement-b2-04"), ("b2", "economie-b2-04"),
]

_ARTICLES = ("le ", "la ", "les ", "l'", "un ", "une ", "des ")


def _norm(s: str) -> str:
    stripped = "".join(
        c for c in unicodedata.normalize("NFD", s) if unicodedata.category(c) != "Mn"
    )
    return stripped.lower()


def _strip_article(fr: str) -> str:
    n = _norm(fr)
    for a in _ARTICLES:
        if n.startswith(a):
            return n[len(a):]
    return n


def _exercise_blob(ex: Exercise) -> str:
    t = ex.type
    if t == "match_pairs":
        parts = [w for pair in ex.pairs for w in pair]
    elif t == "mcq":
        parts = [ex.prompt, *[str(o) for o in ex.options], str(ex.answer)]
        if ex.explain:
            parts.append(ex.explain)
    elif t == "word_bank":
        parts = [*ex.tokens, *ex.answer, ex.prompt]
    elif t == "translate":
        parts = [ex.answer, *(ex.accept or []), ex.prompt]
    elif t == "listen_type":
        parts = [ex.answer, ex.prompt]
    else:
        parts = []
    return " | ".join(parts)


def _shown_in_lesson(headword_norm: str, blob_norm: str) -> bool:
    """True if the headword (or a plausible inflected/agreement stem of it)
    appears in the lesson's exercise text."""
    if headword_norm in blob_norm:
        return True
    for cut in range(0, max(len(headword_norm) - 3, 0)):
        stem = headword_norm[: len(headword_norm) - cut]
        if len(stem) < 4:
            break
        if re.search(r"\b" + re.escape(stem), blob_norm):
            return True
    return False


def _missing_words(level: str, lesson_id: str) -> list[str]:
    bundle = load_content(CONTENT_ROOT, level)
    lesson = bundle.lessons[lesson_id]
    blob_norm = _norm(" | ".join(_exercise_blob(e) for e in lesson.exercises))
    exceptions = KNOWN_CONJUGATED_ONLY.get((level, lesson_id), set())
    missing = []
    for vid in lesson.new_vocab:
        if vid in exceptions:
            continue
        headword = _strip_article(bundle.vocab[vid].fr)
        if not _shown_in_lesson(headword, blob_norm):
            missing.append(vid)
    return missing


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


def test_round_055_lessons_new_vocab_is_practiced_in_exercises():
    """Issue 755: across the round's new lessons, every new_vocab id should be
    shown (verbatim or via an inflected/agreement stem) in at least one of the
    lesson's own exercises — new_vocab seeds SRS cards on first pass, so a gap
    here means a learner is quizzed on a word they were never shown."""
    failures = {}
    for level, lesson_id in TARGET_LESSONS:
        missing = _missing_words(level, lesson_id)
        if missing:
            failures[f"{level}/{lesson_id}"] = missing
    assert not failures, f"new_vocab words never shown in exercises: {failures}"
