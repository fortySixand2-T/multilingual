"""Dictionary enrichment: turn a bare French word into a review-ready vocab record.

Slice D of the vocab-decks plan (docs/anki-vocab-plan.md). Given a lemma like
"ordinateur", produce {en, pos, gender} so it can become a personal-deck card
(Slice E) or clean up a bulk import (scripts/import_anki.py). Two layers, decoupled
so each is testable on its own:

  1. `propose` — one cheap LLM pass (`vocab_enrich` profile, strict JSON) proposes
     en / pos / gender. Runs the router in a worker thread; empty word → no call.
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
import re
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

import anyio

from app.ai.interfaces import LLMResult, Msg
from app.content import lexicon

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
    "tion",
    "sion",
    "aison",
    "ité",
    "té",
    "ette",
    "ance",
    "ence",
    "ude",
    "esse",
)
_MASC_SUFFIXES = (
    "ment",
    "isme",
    "eau",
    "phone",
    "scope",
    "age",
    "oir",
)
# The classic feminine `-age` / `-eau` nouns that break the masculine rule.
_AGE_FEM = {"cage", "image", "nage", "page", "plage", "rage"}
_EAU_FEM = {"eau", "peau"}


def strip_leading_article(word: str) -> str:
    """Bare lemma: drop a leading article if the model returned e.g. 'le vélo'."""
    w = word.strip().replace("\u2019", "'").replace("\u2018", "'")  # phone keyboards (QA 1020)
    low = w.lower()
    for art in _ARTICLES:
        if low.startswith(art):
            return w[len(art) :].strip()
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
        w = word.strip().lower()
        return self._by_word.get(w) or self._by_word.get(w.replace("œ", "oe"), "")

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
    if " " in word.strip():  # a phrase has no gender; "...ce soir" must not hit -oir (QA 1050)
        return "", ""
    if g := suffix_gender(word):
        return g, "suffix"
    if pos == "noun" and llm_gender in ("m", "f", "mf"):  # a guess on "à" is not (QA 893)
        return llm_gender, "llm"
    return "", ""


# --- the LLM proposal ---------------------------------------------------------

_ENRICH_SYSTEM = (
    "You are a French-English lexicographer. For the given French word, return a "
    "concise dictionary entry as STRICT JSON only, no prose:\n"
    '{"fr": "...", "en": ["..."], "pos": "noun|verb|adjective|adverb|preposition|'
    'conjunction|pronoun|phrase", '
    '"gender": "m|f|mf|"}\n'
    "Rules: `fr` is the word exactly as given but with its correct French accents and "
    "spelling (eleve -> élève, cacahuetes -> cacahuètes); never a different word or form. "
    "`en` lists what the exact form given means in English, most common sense first: "
    'one sense, or two when French commonly uses both (avocat -> ["lawyer", '
    '"avocado"]; livre -> ["book", "pound"]). Each is one to three words, no article, '
    'no notes, never a definition (baleine -> ["whale"], not large sea mammal). A plural '
    'noun with a meaning of its own gets that meaning (lunettes -> ["glasses"]; affaires '
    '-> ["belongings", "business"]). Leave out any sense you are unsure of. `pos` is the '
    "part of speech. `gender` is the grammatical gender for NOUNS only (m, f, or mf when both "
    'a masculine and feminine form exist like ami/amie); use "" for anything that is '
    "not a noun. If unsure of gender, "
    'use "".'
)

_POS_VALUES = {
    "noun",
    "verb",
    "adjective",
    "adverb",
    "preposition",
    "conjunction",
    "pronoun",
    "phrase",
}


def _pos(raw: str) -> str:
    """The model's part of speech mapped onto _POS_VALUES by its first three letters,
    so "adj", "Adverb (time)" or "prep." aren't dropped to "" (QA 893)."""
    head = raw.strip().lower()[:3]
    return next((v for v in sorted(_POS_VALUES) if head and v.startswith(head)), "")


_GENDER_WORDS = {"masculine": "m", "feminine": "f", "masculin": "m", "féminin": "f"}


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
    fr = data.get("fr")
    en = data.get("en")
    pos = data.get("pos")
    gender = data.get("gender")
    gender = gender.strip().lower().rstrip(".") if isinstance(gender, str) else ""
    gender = _GENDER_WORDS.get(gender, gender)
    if isinstance(en, list):  # the prompt asks for a list of senses
        en = ", ".join(s.strip() for s in en if isinstance(s, str))
    return {
        "fr": fr.strip() if isinstance(fr, str) else "",
        "en": en.strip() if isinstance(en, str) else "",
        "pos": _pos(pos) if isinstance(pos, str) else "",
        "gender": gender if gender in ("m", "f", "mf") else "",
    }


# Bracketed notes the model adds to a gloss: inflection notes (the adjective's comes
# from Lexique instead), grammar labels and regional asides all go (QA 1001).
_BRACKET = re.compile(r"\s*\(([^()]*)\)")
_FORM_NOTE = re.compile(r"(?:(?:fem(?:inine)?|masc(?:uline)?|plural|pl|[fm])\.?\s*)+", re.I)
_LABELS = r"(?:m|f|mf|n|v|adj|adv|prep|conj|noun|verb|adjective|adverb|preposition|pronoun)\.?"
_LABEL = re.compile(rf"{_LABELS}(?:\s*[/,&]\s*{_LABELS})*", re.I)
_REGIONAL = re.compile(r"\b(?:English|Brit|British|UK|US|American)\b", re.I)
_TRAILING_ARTICLE = re.compile(r"\s+(?:the|a|an)$")  # case-sensitive: "vitamin A" keeps its A
_SENSES = re.compile(r"\s*[|,;]\s*")


def clean_gloss(en: str, note: str = "") -> str:
    """The model's gloss made consistent: senses split on | , or ; and joined with ", ",
    each once ("speak, speak"); "pavement (m)", "active (adj)", "large (f pl)", "ground
    floor (Brit. English: …)" lose the note; "at the" loses its dangling article.
    `note` is the adjective form note to show ("f. pl." -> "large (f. pl.)")."""

    def keep(m: re.Match) -> str:
        inner = m.group(1).strip()
        drop = _FORM_NOTE.fullmatch(inner) or _LABEL.fullmatch(inner) or _REGIONAL.search(inner)
        return "" if drop else m.group(0)

    senses: dict[str, str] = {}
    for sense in _SENSES.split(_BRACKET.sub(keep, en)):
        sense = _TRAILING_ARTICLE.sub("", " ".join(sense.split()))
        if sense:
            senses.setdefault(_BRACKET.sub("", sense).lower(), sense)
    gloss = ", ".join(senses.values())
    return f"{gloss} ({note})" if gloss and note else gloss


@dataclass(frozen=True)
class Enrichment:
    fr: str  # headword: article stripped, accents checked by the caller's `headword`
    en: str
    pos: str
    gender: str  # "" | m | f | mf
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
    router,
    word: str,
    *,
    table: GenderTable | None = None,
    headword: Callable[[str, str], str] | None = None,
    max_tokens: int = 128,
) -> tuple[Enrichment | None, LLMResult | None]:
    """Full enrichment for a bare French word: LLM gloss/pos + deterministic
    gender backstop. `headword(typed, proposed)` picks the spelling to keep (default:
    as typed); pos and gender are settled on that spelling, so "elephant" typed and
    "éléphant" kept finds éléphant's gender (QA 1004). Returns (Enrichment,
    llm_result); (None, None) for empty input."""
    lemma = strip_leading_article(word)
    if not lemma:
        return None, None
    entry, result = await propose(router, lemma, max_tokens=max_tokens)
    fr = headword(lemma, entry.get("fr", "")) if headword else lemma
    pos = lexicon.pos(fr, entry.get("pos", ""), article=lemma != word.strip())
    gender, source = resolve_gender(fr, pos, entry.get("gender", ""), table=table)
    return (
        Enrichment(
            fr=fr,
            en=clean_gloss(
                entry.get("en", ""), lexicon.form_note(fr) if pos == "adjective" else ""
            ),
            pos=pos,
            gender=gender,
            gender_source=source,
        ),
        result,
    )
