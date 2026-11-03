"""Build app/content/data/fr_gloss.tsv.gz from kaikki.org's English Wiktionary
extract of French: a short English meaning for every common French word.

One line per (word, part of speech), in Wiktionary's order:
`<word>\t<pos>\t<gender>\t<gloss>`. A word is kept when Lexique sees it at least once
per million words (app/content/data/fr_forms.tsv.gz); a sense is kept when it is a
current, neutral meaning (no form-of, slang, archaic …) that reads as a translation
of three words or fewer ("peach", "to eat"), not a definition. My deck's lookup uses
it instead of the local model, which got two-meaning words wrong (pêche -> "fruit",
QA 1101). Wiktionary is CC BY-SA 4.0; extract from https://kaikki.org.

    curl -O https://kaikki.org/dictionary/French/kaikki.org-dictionary-French.jsonl.gz
    python scripts/build_gloss_table.py kaikki.org-dictionary-French.jsonl.gz
"""

from __future__ import annotations

import gzip
import json
import re
import sys
from pathlib import Path

DATA = Path(__file__).resolve().parent.parent / "app" / "content" / "data"
OUT = DATA / "fr_gloss.tsv.gz"
MIN_FREQ = 1.0  # per million words, as Lexique counts them
POS = {
    "noun": "noun",
    "verb": "verb",
    "adj": "adjective",
    "adv": "adverb",
    "prep": "preposition",
    "conj": "conjunction",
    "pron": "pronoun",
}
SKIP_TAGS = {
    "form-of",
    "alt-of",
    "abbreviation",
    "misspelling",
    "archaic",
    "obsolete",
    "dated",
    "rare",
    "historical",
    "slang",
    "vulgar",
    "derogatory",
    "offensive",
    "colloquial",
    "informal",
    "humorous",
    "euphemistic",
    "Louisiana",
}
MAX_WORDS = 3  # per translation: longer is a definition ("good as opposed to evil")
MAX_SENSES = 2
MAX_PER_SENSE = 2
MAX_PIECES = 3
_PAREN = re.compile(r"\s*\(([^()]*)\)")
_SPLIT = re.compile(r"\s*[,;]\s*")
_ARTICLE = re.compile(r"^(?:a|an|the) ", re.I)
_ASIDE = re.compile(r"[,;]|\b(?:i\.e|e\.g|sense|see)\b")  # a bracket that isn't a short note


def _keep_paren(m: re.Match) -> str:
    inner = m.group(1)
    return m.group(0) if len(inner.split()) <= MAX_WORDS and not _ASIDE.search(inner) else ""


def _clean(piece: str) -> bool:
    """No list tail ("or privately hired"), label ("Audio: …") or broken bracket."""
    return (
        not re.match(r"(?:or|and) ", piece)
        and not re.search(r"[:“”\[\]]", piece)
        and piece.count("(") == piece.count(")")
    )


def translations(gloss: str) -> list[str]:
    """The short translations in one Wiktionary gloss: "a computer, a computing
    device." -> ["computer", "computing device"]; "great (i.e. important, …)" ->
    ["great"]; a definition gives []."""
    gloss = _PAREN.sub(_keep_paren, gloss).split(". ")[0].strip().rstrip(".")  # "freedom. 1688"
    pieces = [_ARTICLE.sub("", p.strip("[]")) for p in _SPLIT.split(gloss) if p]
    short = [p for p in pieces if 0 < len(_PAREN.sub("", p).split()) <= MAX_WORDS and _clean(p)]
    # A long first piece is a definition whatever follows ("The most common adverb of
    # negation …, typically translating as not, don't, …").
    return short if short[:1] == pieces[:1] else []


def _gender(tags: set[str]) -> str:
    if {"masculine", "feminine"} <= tags:
        return "mf"
    return "m" if "masculine" in tags else "f" if "feminine" in tags else ""


def _same(piece: str) -> str:
    """What two translations share when they say the same thing: "to take off" and
    "take off", "law (legal code)" and "law (scientific principle)"."""
    return re.sub(r"^to ", "", _PAREN.sub("", piece).lower())


def gloss(entries: list[list[list[str]]]) -> str:
    """Up to MAX_PIECES translations across a word's same-pos entries, taking each
    entry's first sense before any second one (pêche: "peach" then "fishing")."""
    ranks = range(max(map(len, entries)))
    senses = [e[rank] for rank in ranks for e in entries if rank < len(e)]
    out: list[str] = []
    for sense in senses[:MAX_SENSES]:
        for piece in sense[:MAX_PER_SENSE]:
            if _same(piece) not in map(_same, out):
                out.append(piece)
    return ", ".join(out[:MAX_PIECES])


def main(src: Path) -> None:
    common = set()
    with gzip.open(DATA / "fr_forms.tsv.gz", "rt", encoding="utf-8") as f:
        for line in f:
            form, _, freq, _ = line.rstrip("\n").split("\t")
            if float(freq) >= MIN_FREQ:
                common.add(form)
    # (word, pos) -> ([senses per entry], gender of the first entry)
    found: dict[tuple[str, str], tuple[list, str]] = {}
    with gzip.open(src, "rt", encoding="utf-8") as f:
        for line in f:
            d = json.loads(line)
            word, pos = d.get("word", ""), POS.get(d.get("pos", ""))
            if not pos or d.get("lang_code") != "fr" or word not in common:
                continue
            senses, tags = [], set()
            for s in d.get("senses", []):
                stags = set(s.get("tags", []))
                tags |= stags
                if s.get("glosses") and not stags & SKIP_TAGS and "form_of" not in s:
                    if found_t := translations(s["glosses"][0]):
                        senses.append(found_t)
            if senses:
                entries, gender = found.setdefault((word, pos), ([], _gender(tags)))
                entries.append(senses)
    lines = [f"{w}\t{p}\t{g}\t{gloss(e)}\n" for (w, p), (e, g) in found.items()]
    with gzip.open(OUT, "wt", encoding="utf-8", compresslevel=9) as f:
        f.writelines(lines)
    print(f"{len(lines)} entries, {len({w for w, _ in found})} words -> {OUT}", file=sys.stderr)


if __name__ == "__main__":
    main(Path(sys.argv[1]))
