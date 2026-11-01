"""French word forms from Lexique383 (`data/fr_forms.tsv.gz`, built by
scripts/build_forms_table.py): each spelling's usual part of speech and frequency.

The lookup uses it to correct the local model where it is reliably wrong:
  - `respell` puts accents where French puts them (coté -> côté, chausseé -> chaussée),
  - `pos` stops an inflected adjective or a preposition being called a noun (grandes,
    pendant), which would otherwise get a gender stamped on it (QA 1000).
"""

from __future__ import annotations

import functools
import gzip
import re
import unicodedata
from pathlib import Path

_PATH = Path(__file__).resolve().parent / "data" / "fr_forms.tsv.gz"
_TOKENS = re.compile(r"([\s'’-]+)")
_LIGATURES = str.maketrans({"œ": "oe", "æ": "ae"})
# A spelling at least this many times rarer than its accent variant is a misspelling.
_RARER = 20
# What a "noun" from the model may really be. Never a verb or pronoun: été (summer) and
# personne (person) are mostly verb / pronoun in running text, yet a learner means the noun.
_NOT_NOUNS = {"adjective", "adverb", "preposition", "conjunction"}


def _key(word: str) -> str:
    """Accent-free, ligature-free spelling: the key accent variants share."""
    s = unicodedata.normalize("NFD", word.lower().translate(_LIGATURES))
    return "".join(c for c in s if unicodedata.category(c) != "Mn")


@functools.cache
def _forms() -> tuple[dict[str, tuple[str, float]], dict[str, str]]:
    """({form: (pos, frequency)}, {key: most frequent form with that key})."""
    forms: dict[str, tuple[str, float]] = {}
    best: dict[str, str] = {}
    if _PATH.exists():
        with gzip.open(_PATH, "rt", encoding="utf-8") as f:
            for line in f:
                form, pos, freq = line.rstrip("\n").split("\t")
                forms[form] = (pos, float(freq))
                k = _key(form)
                if k not in best or forms[best[k]][1] < forms[form][1]:
                    best[k] = form
    return forms, best


def _respell_word(word: str) -> str:
    forms, best = _forms()
    low = word.lower()
    top = best.get(_key(low))
    if not top or top == low.translate(_LIGATURES):  # Lexique spells cœur "coeur"
        return word
    known = forms.get(low)
    if known and known[1] * _RARER > forms[top][1]:
        return word
    return top[0].upper() + top[1:] if word[:1].isupper() else top


def respell(text: str) -> str:
    """`text` with each word's accents as French usually writes them: an unknown or far
    rarer spelling gives way to its common accent variant (rez-de-chausseé ->
    rez-de-chaussée). Same letters otherwise, so the lookup slug never changes."""
    return "".join(
        part if i % 2 else _respell_word(part) for i, part in enumerate(_TOKENS.split(text))
    )


def pos(word: str, model_pos: str) -> str:
    """The model's part of speech, unless it called a word a noun that French almost
    always uses as something else (grandes -> adjective, pendant -> preposition)."""
    usual = _forms()[0].get(word.strip().lower(), ("", 0.0))[0]
    if model_pos in ("", "noun") and usual in _NOT_NOUNS:
        return usual
    return model_pos or usual
