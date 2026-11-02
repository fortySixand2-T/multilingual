"""French word forms from Lexique383 (`data/fr_forms.tsv.gz`, built by
scripts/build_forms_table.py): each spelling's usual part of speech and frequency.

The lookup uses it to correct the local model where it is reliably wrong:
  - `respell` puts accents where French puts them (coté -> côté, chausseé -> chaussée)
    and writes the œ ligature (boeuf -> bœuf),
  - `pos` stops an inflected adjective or a preposition being called a noun (grandes,
    pendant), which would otherwise get a gender stamped on it (QA 1000),
  - `form_note` says which inflected form an adjective is (grandes -> "f. pl.").
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
# French writes œ before u and il (bœuf, cœur, vœu, œil); Lexique spells it out.
_OE = re.compile(r"(o)e(?=u|il)", re.I)
# A spelling at least this many times rarer than its accent variant is a misspelling.
_RARER = 20
# What a "noun" from the model may really be. Never a verb or pronoun: été (summer) and
# personne (person) are mostly verb / pronoun in running text, yet a learner means the noun.
_NOT_NOUNS = {"adjective", "adverb", "preposition", "conjunction"}
# Lexique's reading wins over any model pos but a verb or pronoun (derrière was an
# "adjective", chez an "adverb"): these words are closed classes with no other use.
_FUNCTION_WORDS = {"preposition", "conjunction"}
# Correct words Lexique lacks, so respell would take them for a misspelling of dû / dès.
_KEEP_AS_TYPED = {"du", "des"}


def _key(word: str) -> str:
    """Accent-free, ligature-free spelling: the key accent variants share."""
    s = unicodedata.normalize("NFD", word.lower().translate(_LIGATURES))
    return "".join(c for c in s if unicodedata.category(c) != "Mn")


@functools.cache
def _forms() -> tuple[dict[str, tuple[str, float, str]], dict[str, str]]:
    """({form: (pos, frequency, adjective form note)}, {key: most frequent form with
    that key})."""
    forms: dict[str, tuple[str, float, str]] = {}
    best: dict[str, str] = {}
    if _PATH.exists():
        with gzip.open(_PATH, "rt", encoding="utf-8") as f:
            for line in f:
                form, pos, freq, note = line.rstrip("\n").split("\t")
                forms[form] = (pos, float(freq), note)
                k = _key(form)
                if k not in best or forms[best[k]][1] < forms[form][1]:
                    best[k] = form
    return forms, best


def _respell_word(word: str) -> str:
    forms, best = _forms()
    low = word.lower()
    if low in _KEEP_AS_TYPED:
        return word
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
    rez-de-chaussée), and oe is written œ where French does (boeuf -> bœuf, QA 1082).
    Same letters otherwise, so the lookup slug never changes."""
    text = "".join(
        part if i % 2 else _respell_word(part) for i, part in enumerate(_TOKENS.split(text))
    )
    return _OE.sub(lambda m: "Œ" if m.group(1) == "O" else "œ", text)


def _entry(word: str) -> tuple[str, float, str]:
    return _forms()[0].get(word.strip().lower().translate(_LIGATURES), ("", 0.0, ""))


def form_note(word: str) -> str:
    """ "f.", "pl." or "f. pl." for an inflected adjective form (grandes), else ""."""
    return _entry(word)[2]


def pos(word: str, model_pos: str, *, article: bool = False) -> str:
    """The model's part of speech, unless it called a word a noun that French almost
    always uses as something else (grandes -> adjective, pendant -> preposition), or a
    preposition or conjunction it called anything else (derrière, chez). A typed article
    (le pas) says noun."""
    usual = _entry(word)[0]
    if article and model_pos in ("", "noun"):
        return "noun"
    if (model_pos in ("", "noun") and usual in _NOT_NOUNS) or (
        usual in _FUNCTION_WORDS and model_pos not in ("verb", "pronoun")
    ):
        return usual
    return model_pos or usual
