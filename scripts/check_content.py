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

from app.comprehension.loader import load_sets
from app.content.loader import load_content
from app.speech.topics import load_topics

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

# One spelling per part of speech. `adj` vs `adjective` drifted in four entries
# before this was checked.
KNOWN_POS = {"noun", "verb", "adjective", "adverb", "numeral", "phrase", "interjection"}

# Floor, in percent, for how much of a level's vocab bank its comprehension
# passages actually use. A word the learner only ever meets on a deck tile and
# in a drill is recognised, never read in context. These are set to the achieved
# value rounded down to a multiple of 5, and `check_comprehension_covers_vocab`
# refuses to let a level sit 5+ points above its floor -- so coverage ratchets
# up and can never silently regress when the bank next grows.
MIN_COMPREHENSION_COVERAGE = {"a1": 95, "a2": 80, "b1": 90, "b2": 90}

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
        if w.pos not in KNOWN_POS:
            report(f"{level}/{vid}: pos {w.pos!r} is not one of {sorted(KNOWN_POS)}")
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


def check_speaking_covers_both_sections(level, bundle, report):
    """Every TEF candidate sits both Expression orale sections, so every level
    needs both: A = obtain information, B = argue a position. a1/a2 once had
    only A and b1/b2 only B, so half the exam was unpractisable at every level.
    """
    topics = load_topics(CONTENT_ROOT, level)
    for section, what in (("A", "obtain information"), ("B", "argue a position")):
        if not [t for t in topics.values() if t.section == section]:
            report(f"{level}: no Section {section} speaking topic ({what})")
    for t in topics.values():
        for pt in t.points:
            if not isinstance(pt, str):
                report(
                    f"{level}/{t.id}: a `points` entry parsed as {type(pt).__name__}, "
                    "not a string — an unquoted ' : ' makes YAML build a mapping"
                )


def check_path_covers_lessons(level, bundle, report):
    """A lesson missing from path.yaml is unreachable in the Learn tab."""
    in_path = {lid for unit in bundle.path.units for lid in unit.lessons}
    for lid in set(bundle.lessons) - in_path:
        report(f"{level}/{lid}: not referenced by any path unit — unreachable")


def comprehension_blob(level: str) -> str:
    """Everything a learner reads or hears in a level's comprehension sets."""
    parts: list[str] = []
    for s in load_sets(CONTENT_ROOT, level).values():
        parts.append(s.passage or s.script or "")
        for q in s.questions:
            parts += [q.prompt, *q.options, q.explain]
    return norm(" ".join(parts))


def _canon_quote(s: str) -> str:
    """Compare quoted text to passage text ignoring what a quote may legitimately
    change: typographic apostrophes, an editorial [insertion], whitespace, and the
    punctuation a quotation ends on."""
    s = s.replace("\u2019", "'").replace("\u2018", "'")
    s = re.sub(r"\[[^\]]*\]", "", s)
    return re.sub(r"\s+", " ", norm(s)).strip().strip(" .,;:!?")


def check_explain_quotes_are_real(level, bundle, report):
    """Guillemets in an `explain` promise a quotation from the passage. Eight had
    drifted into paraphrase -- a dropped « , lui, », a reworded clause -- which
    teaches the learner to look for words the text does not contain. An ellipsis
    (…) splits a quote into pieces that must each appear."""
    for cset in load_sets(CONTENT_ROOT, level).values():
        body = _canon_quote(cset.passage or cset.script or "")
        for q in cset.questions:
            for frag in re.findall(r"\u00ab\s*(.+?)\s*\u00bb", q.explain or ""):
                for piece in (_canon_quote(x) for x in frag.split("\u2026")):
                    if piece and piece not in body:
                        report(
                            f"{level}/{q.id}: explain quotes «{piece[:60]}» "
                            "but the passage does not say that"
                        )


def check_comprehension_covers_vocab(level, bundle, report):
    """Vocabulary the comprehension library never uses is vocabulary the learner
    only ever recognises. b2 once had the largest bank and the thinnest library:
    21% coverage, with five whole themes (100 words) never once in a passage.

    Headword matching undercounts verbs -- `craindre` in the text as *craint* is
    invisible here -- so the floor is deliberately a floor, not a target.
    """
    floor = MIN_COMPREHENSION_COVERAGE.get(level)
    if floor is None:
        return
    blob = comprehension_blob(level)
    words = list(bundle.vocab.values())
    hit = sum(1 for w in words if shown_in_lesson(norm(strip_article(w.fr)), blob))
    pct = 100 * hit // len(words)
    if pct < floor:
        report(
            f"{level}: comprehension uses {hit}/{len(words)} = {pct}% of the vocab bank, "
            f"below the {floor}% floor — add sets, or author them from the theme files"
        )
    elif pct >= floor + 5:
        report(
            f"{level}: comprehension coverage is now {pct}% — raise "
            f"MIN_COMPREHENSION_COVERAGE[{level!r}] to {pct // 5 * 5} to lock it in"
        )


RULES = [
    check_exercise_shapes,
    check_vocab_fields,
    check_audio_present,
    check_every_word_is_taught,
    check_new_vocab_is_practiced,
    check_known_gaps_not_stale,
    check_speaking_covers_both_sections,
    check_path_covers_lessons,
    check_comprehension_covers_vocab,
    check_explain_quotes_are_real,
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
