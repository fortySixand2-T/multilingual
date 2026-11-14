"""Short English meanings of ~16,000 common French words, from Wiktionary
(`data/fr_gloss.tsv.gz`, built by scripts/build_gloss_table.py).

My deck's lookup asks here before the local model: a covered word gets a
dictionary meaning with no model call, so two-meaning words come out right
(pêche -> "peach, fishing", where the model said "fruit", QA 1101) and cost nothing
from the daily lookup budget. Wiktionary is CC BY-SA 4.0.
"""

from __future__ import annotations

import functools
import gzip
from pathlib import Path

from app.content import lexicon

_PATH = Path(__file__).resolve().parent / "data" / "fr_gloss.tsv.gz"


@functools.cache
def _entries() -> dict[str, dict[str, tuple[str, str]]]:
    """{word: {pos: (gender, gloss)}}, each word's parts of speech in Wiktionary's order."""
    entries: dict[str, dict[str, tuple[str, str]]] = {}
    if _PATH.exists():
        with gzip.open(_PATH, "rt", encoding="utf-8") as f:
            for line in f:
                word, pos, gender, gloss = line.rstrip("\n").split("\t")
                entries.setdefault(word, {})[pos] = (gender, gloss)
    return entries


@functools.cache
def _spellings() -> dict[str, list[str]]:
    """{accent-free key: the dictionary words spelled that way bar accents}."""
    spellings: dict[str, list[str]] = {}
    for word in _entries():
        spellings.setdefault(lexicon.fold(word), []).append(word)
    return spellings


def has_genders(word: str) -> bool:
    """True for a noun whose gender changes its meaning (tour, livre, poêle)."""
    return "noun:m" in _entries().get(word.strip().lower(), {})


def ambiguous(typed: str) -> bool:
    """True when `typed` is no word itself but its accents could make several ("peche":
    pêche, péché), so the spelling must be chosen before the meaning."""
    word = typed.strip().lower()
    return word not in _entries() and len(_spellings().get(lexicon.fold(word), ())) > 1


def alternatives(typed: str, chosen: str) -> list[dict]:
    """The other words `typed` could be with accents when it was typed with none
    ("peche" looked up as pêche: péché "sin"), as [{"fr", "en"}], so the learner sees
    them and can pick one (QA 1181). [] for a word typed with accents: that's a choice."""
    word = typed.strip().lower()
    if lexicon.fold(word) != word:
        return []
    others = (entry(w) for w in _spellings().get(word, ()) if w != chosen.strip().lower())
    return [{"fr": e["fr"], "en": e["en"]} for e in others if e][:3]


def entry(word: str, *, pos: str = "", gender: str = "") -> dict | None:
    """{"fr", "en", "pos", "gender"}, shaped like the model's proposal, or None when
    the dictionary doesn't have the word (or not as `pos`). Without `pos`, the reading
    Lexique says the word usually has (pendant -> preposition), else Wiktionary's first.
    A noun's `gender` (from a typed article) picks the meaning that goes with it when
    gender changes it: la tour "tower", le tour "turn" (QA 1160)."""
    by_pos = _entries().get(word.strip().lower())
    if not by_pos:
        return None
    if pos == "noun" and f"noun:{gender}" in by_pos:
        g, en = by_pos[f"noun:{gender}"]
        return {"fr": word.strip(), "en": en, "pos": "noun", "gender": g}
    if not pos:
        usual = lexicon.usual_pos(word)
        pos = usual if usual in by_pos else next(iter(by_pos))
    if pos not in by_pos:
        return None
    gender, gloss = by_pos[pos]
    return {"fr": word.strip(), "en": gloss, "pos": pos, "gender": gender}
