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


def entry(word: str, *, pos: str = "") -> dict | None:
    """{"fr", "en", "pos", "gender"}, shaped like the model's proposal, or None when
    the dictionary doesn't have the word (or not as `pos`). Without `pos`, the reading
    Lexique says the word usually has (pendant -> preposition), else Wiktionary's first."""
    by_pos = _entries().get(word.strip().lower())
    if not by_pos:
        return None
    if not pos:
        usual = lexicon.usual_pos(word)
        pos = usual if usual in by_pos else next(iter(by_pos))
    if pos not in by_pos:
        return None
    gender, gloss = by_pos[pos]
    return {"fr": word.strip(), "en": gloss, "pos": pos, "gender": gender}
