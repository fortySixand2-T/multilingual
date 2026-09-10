#!/usr/bin/env python3
"""Authoring validator for content/ — one place for every rule an expansion must hold.

Run it after authoring, before pytest::

    python scripts/check_content.py            # all levels
    python scripts/check_content.py b1 b2      # just these

Most of these rules exist because the rule was broken at least once. YAML is
forgiving in exactly the ways content authoring is fragile: `en: true` parses as
a boolean, `- [action, share, stock]` becomes a 3-item pair, a copy-pasted
exercise id silently shadows another lesson's. All of that loads as valid YAML
and only fails later — at Pydantic validation, in the app, or not at all.

`tests/test_content_invariants.py` runs these in CI, so the checker and the test
suite can never drift apart.
"""

from __future__ import annotations

import re
import sys
import unicodedata
from pathlib import Path

from app.content.loader import load_content

CONTENT_ROOT = Path(__file__).resolve().parents[1] / "content"

# Legacy lessons whose `new_vocab` is not yet fully practiced by their own
# exercises. Now EMPTY: every word at every level is taught by the lesson that
# seeds it. Keep the mechanism -- a future expansion that lands against a known
# gap can carve it out here, and `check_known_gaps_not_stale` guarantees the
# carve-out shrinks back to nothing.
KNOWN_GAPS: dict[tuple[str, str], set[str]] = {}

# `vouloir` in a1/verbs-01 is shown only as the conjugated word_bank answer
# "veux", which a headword match cannot see.
KNOWN_CONJUGATED_ONLY = {("a1", "verbs-01"): {"vouloir"}}

_ARTICLES = ("le ", "la ", "les ", "l'", "un ", "une ", "des ")


def norm(s: str) -> str:
    stripped = "".join(
        c for c in unicodedata.normalize("NFD", s) if unicodedata.category(c) != "Mn"
    )
    return stripped.lower()


def strip_article(fr: str) -> str:
    n = norm(fr)
    for a in _ARTICLES:
        if n.startswith(a):
            return n[len(a) :]
    return n


def exercise_blob(ex) -> str:
    """Every string in an exercise that a learner actually sees."""
    t = ex.type
    if t == "match_pairs":
        parts = [w for pair in ex.pairs for w in pair]
    elif t == "mcq":
        parts = [ex.prompt, *[str(o) for o in ex.options], str(ex.answer)]
        if ex.explain:
            parts.append(ex.explain)
    elif t == "word_bank":
        # the joined answer is the sentence the learner builds, so a multi-word
        # headword stays contiguous
        parts = [" ".join(ex.answer), *ex.tokens, ex.prompt]
    elif t == "translate":
        parts = [ex.answer, *(ex.accept or []), ex.prompt]
    elif t == "listen_type":
        parts = [ex.answer, ex.prompt]
    else:
        parts = []
    return " | ".join(parts)


def shown_in_lesson(headword_norm: str, blob_norm: str) -> bool:
    """True if the headword appears in the exercise text, allowing inflection but
    not unrelated words that merely share a prefix.

    A bare prefix match is far too loose: it let `serviette` pass on "serveur",
    `chaussette` on "chaussures", and `transition` on the English prompt word
    "translate:". So a multi-word headword must appear as a contiguous phrase,
    and a single word may drop at most 2 trailing characters to reach a stem
    while the word it matches may add at most 2.
    """
    words = headword_norm.split()
    if len(words) > 1:
        return re.search(r"\b" + r"\s+".join(re.escape(w) for w in words), blob_norm) is not None

    min_stem = min(len(headword_norm), 4)
    for trim in range(0, 3):
        stem = headword_norm[: len(headword_norm) - trim]
        if len(stem) < min_stem:
            break
        for m in re.finditer(r"\b" + re.escape(stem) + r"(\w*)", blob_norm):
            if len(m.group(1)) <= 2:
                return True
    return False


def missing_words(level: str, lesson_id: str, bundle) -> list[str]:
    lesson = bundle.lessons[lesson_id]
    blob = norm(" | ".join(exercise_blob(e) for e in lesson.exercises))
    skip = KNOWN_CONJUGATED_ONLY.get((level, lesson_id), set())
    return [
        vid
        for vid in lesson.new_vocab
        if vid not in skip and not shown_in_lesson(strip_article(bundle.vocab[vid].fr), blob)
    ]


# --- rules -------------------------------------------------------------------
# Each rule takes (level, bundle, report) and appends human-readable failures.


def check_exercise_shapes(level, bundle, report):
    """The YAML traps: bool tokens, 3-item pairs, answers not in options."""
    for lid, lesson in bundle.lessons.items():
        for ex in lesson.exercises:
            where = f"{level}/{lid}:{ex.id}"
            if ex.type == "match_pairs":
                for pair in ex.pairs:
                    if len(pair) != 2 or not all(isinstance(x, str) for x in pair):
                        report(f"{where}: malformed pair {pair!r} (unquoted comma or bool?)")
            elif ex.type == "mcq":
                if not all(isinstance(o, str) for o in ex.options):
                    report(f"{where}: non-string mcq option (unquoted yes/no/true?)")
                if ex.answer not in ex.options:
                    report(f"{where}: answer {ex.answer!r} not among options")
            elif ex.type == "word_bank":
                bank = list(ex.tokens)
                for tok in ex.answer:
                    if tok in bank:
                        bank.remove(tok)
                    else:
                        report(f"{where}: answer token {tok!r} not in tokens")
            elif ex.type == "listen_type":
                if not (CONTENT_ROOT / ex.audio_ref).is_file():
                    report(f"{where}: audio_ref {ex.audio_ref} does not exist")


def check_vocab_fields(level, bundle, report):
    """`en: true` for the gloss of *vrai* parses as a boolean, not a string."""
    for vid, w in bundle.vocab.items():
        for field in ("fr", "en"):
            if not isinstance(getattr(w, field), str) or not getattr(w, field).strip():
                report(f"{level}/{vid}: {field} is not a non-empty string")
        if not getattr(w, "tags", None):
            report(f"{level}/{vid}: no tags — it will not appear under any deck")
        if getattr(w, "gender", None) == "mf" and not getattr(w, "fem", None):
            report(f"{level}/{vid}: gender 'mf' needs a distinct `fem` spelling")


def check_audio_present(level, bundle, report):
    """Audio is a build artifact (scripts/gen_audio.py); a gap is silent in the UI."""
    for vid, w in bundle.vocab.items():
        if not (CONTENT_ROOT / level / "audio" / f"{vid}.mp3").is_file():
            report(f"{level}/{vid}: no audio — run scripts/gen_audio.py")
        if getattr(w, "gender", None) == "mf":
            if not (CONTENT_ROOT / level / "audio" / f"{vid}_f.mp3").is_file():
                report(f"{level}/{vid}: no feminine audio ({vid}_f.mp3)")


def check_every_word_is_taught(level, bundle, report):
    """A word no lesson seeds can only ever be found by browsing its deck."""
    seeded = {v for lesson in bundle.lessons.values() for v in lesson.new_vocab}
    for vid in bundle.vocab:
        if vid not in seeded:
            report(f"{level}/{vid}: in the bank but no lesson introduces it")


def check_new_vocab_is_practiced(level, bundle, report):
    """new_vocab seeds SRS cards, so a word listed but never shown is a card for
    something the learner was never taught."""
    for lid in bundle.lessons:
        unexpected = set(missing_words(level, lid, bundle)) - KNOWN_GAPS.get((level, lid), set())
        if unexpected:
            report(f"{level}/{lid}: new_vocab never shown in its exercises: {sorted(unexpected)}")


def check_known_gaps_not_stale(level, bundle, report):
    """The carve-out may only shrink: once fixed, an entry must be deleted."""
    for (lvl, lid), allowed in KNOWN_GAPS.items():
        if lvl != level:
            continue
        fixed = allowed - set(missing_words(level, lid, bundle))
        if fixed:
            report(f"{level}/{lid}: now practiced, remove from KNOWN_GAPS: {sorted(fixed)}")


def check_path_covers_lessons(level, bundle, report):
    """A lesson missing from path.yaml is unreachable in the Learn tab."""
    in_path = {lid for unit in bundle.path.units for lid in unit.lessons}
    for lid in set(bundle.lessons) - in_path:
        report(f"{level}/{lid}: not referenced by any path unit — unreachable")


RULES = [
    check_exercise_shapes,
    check_vocab_fields,
    check_audio_present,
    check_every_word_is_taught,
    check_new_vocab_is_practiced,
    check_known_gaps_not_stale,
    check_path_covers_lessons,
]


# Pydantic reports these as a type mismatch deep in a nested model, which points
# at the symptom rather than the cause. Name the usual cause instead.
_LOAD_HINTS = (
    ("at most 2 items", "a flow-list pair has an unquoted comma: [action, share, stock]"),
    ("valid string", "a bare YAML boolean token: `en: true`, [vrai, true], on/off/yes/no"),
)


def _load(level: str) -> tuple[object | None, list[str]]:
    """Load a level, turning a validation error into a readable failure."""
    try:
        return load_content(CONTENT_ROOT, level), []
    except Exception as exc:  # noqa: BLE001 - any load failure is a content failure
        text = str(exc)
        hints = [h for needle, h in _LOAD_HINTS if needle in text]
        msg = f"{level}: content does not load — {text.splitlines()[0]}"
        return None, [msg, *(f"{level}: likely cause — {h}" for h in hints)]


def check_level(level: str) -> list[str]:
    bundle, failures = _load(level)
    if bundle is None:
        return failures
    for rule in RULES:
        rule(level, bundle, failures.append)
    return failures


def check_global(levels: list[str]) -> list[str]:
    """Rules that only mean anything across levels: ids that are DB keys."""
    failures: list[str] = []
    seen_vocab: dict[str, str] = {}
    seen_ex: dict[str, str] = {}
    for level in levels:
        bundle, errors = _load(level)
        if bundle is None:
            failures.extend(errors)
            continue
        for vid in bundle.vocab:
            if vid in seen_vocab:
                failures.append(
                    f"vocab id {vid!r} in both {seen_vocab[vid]} and {level} "
                    f"— ids are DB primary keys and FSRS card keys"
                )
            seen_vocab[vid] = level
        for lid, lesson in bundle.lessons.items():
            for ex in lesson.exercises:
                if ex.id in seen_ex:
                    failures.append(
                        f"exercise id {ex.id!r} in both {seen_ex[ex.id]} "
                        f"and {level}/{lid} — copy-paste slip?"
                    )
                seen_ex[ex.id] = f"{level}/{lid}"
    return failures


def main(argv: list[str]) -> int:
    levels = argv[1:] or sorted(p.parent.name for p in CONTENT_ROOT.glob("*/path.yaml"))
    total = 0
    for level in levels:
        failures = check_level(level)
        total += len(failures)
        print(f"{level}: {'OK' if not failures else f'{len(failures)} problem(s)'}")
        for f in failures:
            print(f"  - {f}")
    cross = check_global(levels)
    total += len(cross)
    print(f"cross-level: {'OK' if not cross else f'{len(cross)} problem(s)'}")
    for f in cross:
        print(f"  - {f}")
    print("\ncontent OK" if not total else f"\n{total} problem(s) found")
    return 1 if total else 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
