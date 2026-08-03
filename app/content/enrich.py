"""Dictionary enrichment: turn a bare French word into a review-ready vocab record.

Slice D of the vocab-decks plan (docs/anki-vocab-plan.md). Given a lemma like
"ordinateur", produce {en, pos, gender, ipa} so it can become a personal-deck card
(Slice E) or clean up a bulk import (scripts/import_anki.py). Two layers, decoupled
so each is testable on its own:

  1. `propose` — one cheap LLM pass (`vocab_enrich` profile, strict JSON) proposes
     en / pos / gender / ipa. Runs the router in a worker thread; empty word → no call.
  2. `resolve_gender` — a DETERMINISTIC backstop that overrides the model's gender
     guess. A local model gets French noun gender wrong often enough that we don't
     trust it when we have a better signal:
         table (Lexique-style word→gender lookup, authoritative)
           > high-confidence suffix rule (‑tion/‑té → f, ‑ment/‑eau → m, …)
             > the model's own guess
               > "" (unresolved — flagged for a human)

The gender table is the "source of truth" slot: `GenderTable.load` reads a TSV
(`word\tgender`), seeded here with common words (`app/content/data/fr_gender.tsv`).
Drop a full Lexique383 extract at that path to widen coverage with no code change.
"""

from __future__ import annotations

import functools
import json
from dataclasses import dataclass
from pathlib import Path

import anyio

from app.ai.interfaces import LLMResult, Msg

_PROFILE = "vocab_enrich"
_DATA_DIR = Path(__file__).resolve().parent / "data"
_DEFAULT_TABLE = _DATA_DIR / "fr_gender.tsv"

# Articles we strip off the front so the table/rules see a bare lemma. Mirrors
# import_anki.strip_article but returns no gender — gender is resolved separately here.
_ARTICLES = ("de la ", "de l'", "l'", "d'", "le ", "la ", "les ", "un ", "une ", "des ")

# --- deterministic gender by word ending --------------------------------------
# Only endings reliable enough to beat a local model's guess. Ordered longest-first
# so the most specific ending wins (‑ation before ‑tion is redundant, but ‑ité before
# ‑té matters). Exceptions below carve out the well-known counter-examples.
_FEM_SUFFIXES = (
    "tion", "sion", "aison", "ité", "té", "ette", "ance", "ence", "ude", "esse",
)
_MASC_SUFFIXES = (
    "ment", "isme", "eau", "phone", "scope", "age", "oir",
)
# The classic feminine `-age` / `-eau` nouns that break the masculine rule.
_AGE_FEM = {"cage", "image", "nage", "page", "plage", "rage"}
_EAU_FEM = {"eau", "peau"}


def strip_leading_article(word: str) -> str:
    """Bare lemma: drop a leading article if the model returned e.g. 'le vélo'."""
    w = word.strip()
    low = w.lower()
    for art in _ARTICLES:
        if low.startswith(art):
            return w[len(art):].strip()
    return w


def suffix_gender(word: str) -> str:
    """'m' / 'f' from a high-confidence noun ending, else '' (no signal)."""
    w = word.strip().lower()
    if not w:
        return ""
    if w.endswith("age"):
        return "f" if w in _AGE_FEM else "m"
    if w.endswith("eau"):
        return "f" if w in _EAU_FEM else "m"
    for suf in _FEM_SUFFIXES:
        if w.endswith(suf):
            return "f"
    for suf in _MASC_SUFFIXES:
        if w.endswith(suf):
            return "m"
    return ""


# --- the gender table (source of truth) ---------------------------------------


@dataclass
class GenderTable:
    """word (lowercased, accents kept) -> 'm' | 'f' | 'mf'. Authoritative over rules."""

    _by_word: dict[str, str]

    @classmethod
    def load(cls, path: Path | str | None = None) -> GenderTable:
        p = Path(path) if path is not None else _DEFAULT_TABLE
        by_word: dict[str, str] = {}
        if p.exists():
            for line in p.read_text(encoding="utf-8").splitlines():
                line = line.strip()
                if not line or line.startswith("#"):
                    continue
                word, _, gender = line.partition("\t")
                gender = gender.strip()
                if word and gender in ("m", "f", "mf"):
                    by_word[word.strip().lower()] = gender
        return cls(by_word)

    def get(self, word: str) -> str:
        return self._by_word.get(word.strip().lower(), "")

    def __len__(self) -> int:
        return len(self._by_word)


def resolve_gender(
    word: str, pos: str, llm_gender: str, *, table: GenderTable | None = None
) -> tuple[str, str]:
    """(gender, source). Gender only applies to nouns; anything the model tagged as a
    non-noun gets ''. Order: table > suffix rule > model guess > unresolved."""
    if pos and pos != "noun":
        return "", ""
    if table is not None and (g := table.get(word)):
        return g, "table"
    if g := suffix_gender(word):
        return g, "suffix"
    if llm_gender in ("m", "f", "mf"):
        return llm_gender, "llm"
    return "", ""


# --- the LLM proposal ---------------------------------------------------------

_ENRICH_SYSTEM = (
    "You are a French-English lexicographer. For the given French word, return a "
    "concise dictionary entry as STRICT JSON only, no prose:\n"
    '{"en": "...", "pos": "noun|verb|adjective|adverb|preposition|phrase", '
    '"gender": "m|f|mf|", "ipa": "..."}\n'
    "Rules: `en` is a short gloss (a few words, no article). `pos` is the part of "
    "speech. `gender` is the grammatical gender for NOUNS only (m, f, or mf when both "
    "a masculine and feminine form exist like ami/amie); use \"\" for anything that is "
    "not a noun. `ipa` is the IPA pronunciation without slashes. If unsure of gender, "
    'use "".'
)

_POS_VALUES = {"noun", "verb", "adjective", "adverb", "preposition", "phrase"}


def _parse_enrichment(text: str) -> dict:
    """Pull the JSON entry out of the model reply, tolerantly (fences, junk keys)."""
    s = text.strip()
    if s.startswith("```"):
        s = s.strip("`")
        s = s[4:] if s[:4].lower() == "json" else s
    try:
        data = json.loads(s)
    except (ValueError, TypeError):
        return {}
    if not isinstance(data, dict):
        return {}
    en = data.get("en")
    pos = data.get("pos")
    gender = data.get("gender")
    ipa = data.get("ipa")
    pos = pos.strip().lower() if isinstance(pos, str) else ""
    gender = gender.strip() if isinstance(gender, str) else ""
    return {
        "en": en.strip() if isinstance(en, str) else "",
        "pos": pos if pos in _POS_VALUES else "",
        "gender": gender if gender in ("m", "f", "mf") else "",
        "ipa": ipa.strip().strip("/[]") if isinstance(ipa, str) else "",
    }


@dataclass(frozen=True)
class Enrichment:
    fr: str  # bare lemma (article stripped)
    en: str
    pos: str
    gender: str  # "" | m | f | mf
    ipa: str
    gender_source: str  # "table" | "suffix" | "llm" | ""  (provenance / confidence)


async def propose(router, word: str, *, max_tokens: int = 128) -> tuple[dict, LLMResult | None]:
    """One LLM pass. Returns (parsed_entry, llm_result) so the caller can bill usage.
    Empty word → no call, no cost."""
    lemma = strip_leading_article(word)
    if not lemma:
        return {}, None
    messages = [Msg("user", f"French word: {lemma}")]
    result = await anyio.to_thread.run_sync(
        functools.partial(
            router.run, _PROFILE, system=_ENRICH_SYSTEM, messages=messages, max_tokens=max_tokens
        )
    )
    return _parse_enrichment(result.text), result


async def enrich(
    router, word: str, *, table: GenderTable | None = None, max_tokens: int = 128
) -> tuple[Enrichment | None, LLMResult | None]:
    """Full enrichment for a bare French word: LLM gloss/pos/ipa + deterministic
    gender backstop. Returns (Enrichment, llm_result); (None, None) for empty input."""
    lemma = strip_leading_article(word)
    if not lemma:
        return None, None
    entry, result = await propose(router, lemma, max_tokens=max_tokens)
    gender, source = resolve_gender(
        lemma, entry.get("pos", ""), entry.get("gender", ""), table=table
    )
    return (
        Enrichment(
            fr=lemma,
            en=entry.get("en", ""),
            pos=entry.get("pos", ""),
            gender=gender,
            ipa=entry.get("ipa", ""),
            gender_source=source,
        ),
        result,
    )
