"""Build app/content/data/fr_gloss.tsv.gz from kaikki.org's English Wiktionary
extract of French: a short English meaning for every common French word.

One line per (word, part of speech), in Wiktionary's order:
`<word>\t<pos>\t<gender>\t<gloss>`. A word is kept when Lexique sees it at least once
per million words (app/content/data/fr_forms.tsv.gz); a sense is kept when it is a
current, neutral meaning (no form-of, slang, archaic …) that reads as a translation
of three words or fewer ("peach", "to eat"), not a definition (a definition is cut
where it starts describing: "hammer used for pounding" -> "hammer"). A word's parts of
speech come most frequent first, by Lexique when imports/Lexique383.tsv is there. My
deck's lookup uses it instead of the local model, which got two-meaning words wrong
(pêche -> "fruit", QA 1101). Wiktionary is CC BY-SA 4.0 (see app/content/data/NOTICE.md);
extract from https://kaikki.org.

    curl -O https://kaikki.org/dictionary/French/kaikki.org-dictionary-French.jsonl.gz
    python -m scripts.build_gloss_table kaikki.org-dictionary-French.jsonl.gz
"""

from __future__ import annotations

import gzip
import json
import re
import sys
from collections import defaultdict
from pathlib import Path

from scripts.build_forms_table import POS as LEXIQUE_POS

DATA = Path(__file__).resolve().parent.parent / "app" / "content" / "data"
OUT = DATA / "fr_gloss.tsv.gz"
LEXIQUE = Path(__file__).resolve().parent.parent / "imports" / "Lexique383.tsv"
MIN_FREQ = 1.0  # per million words, as Lexique counts them
POS = {
    "noun": "noun",
    "verb": "verb",
    "adj": "adjective",
    "adv": "adverb",
    "prep": "preposition",
    "conj": "conjunction",
    "pron": "pronoun",
    "det": "adjective",  # son, leur: Lexique calls possessives adjectives too
}
# Rows the rules can't reach: the sense a learner needs is a long definition or sits
# under a rare one. Keep this to a handful of very common words.
OVERRIDES = {
    ("pas", "adverb"): ("", "not"),
    ("truc", "noun"): ("m", "thing, trick"),
    ("sinon", "conjunction"): ("", "otherwise, if not"),
    ("chez", "preposition"): ("", "at the home of, among"),
    ("selon", "preposition"): ("", "according to, depending on"),
    ("après", "preposition"): ("", "after"),
    ("leur", "pronoun"): ("", "their, (to) them"),
    ("celui", "pronoun"): ("m", "the one (m.)"),
    ("celle", "pronoun"): ("f", "the one (f.)"),
    ("sujet", "noun"): ("m", "subject, topic"),
    ("vase", "noun"): ("m", "vase"),
    ("plan", "noun"): ("m", "plan, map"),
    ("file", "noun"): ("f", "line, queue"),
    ("rang", "noun"): ("m", "rank, row"),
    ("pire", "adjective"): ("", "worse, worst"),
    ("bête", "adjective"): ("", "stupid, silly"),
}
# Words a learner almost always means as an adjective although Lexique counts the noun
# more often (une bête, un moyen).
ADJECTIVE_FIRST = {"bête", "moyen"}
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
GENERIC = {"person", "someone", "one", "thing", "something", "man", "woman", "place", "act"}
_PAREN = re.compile(r"\s*\(([^()]*)\)")
_SPLIT = re.compile(r"\s*[,;]\s*")
_ARTICLE = re.compile(r"^(?:a|an|the) ", re.I)
_DESCRIBES = re.compile(r"\s+(?:used|that|which|who|whose|where|placed|in which)\b.*")
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


def _header_child(glosses: list[str]) -> str:
    """The sense itself: under a header ("the plural pronoun of the first person:") it is
    the line below ("we")."""
    return glosses[-1] if len(glosses) > 1 and glosses[0].endswith(":") else glosses[0]


def translations(gloss: str, *, describing: bool = False) -> list[str]:
    """The short translations in one Wiktionary gloss: "a computer, a computing
    device." -> ["computer", "computing device"]; "great (i.e. important, …)" ->
    ["great"]; a definition gives [], unless `describing`: a noun's leading sense is cut
    where it starts describing ("a hammer used for pounding" -> ["hammer"])."""
    gloss = _PAREN.sub(_keep_paren, gloss).split(". ")[0].strip().rstrip(".")  # "freedom. 1688"
    pieces = [_ARTICLE.sub("", p.strip("[]")) for p in _SPLIT.split(gloss) if p]
    if describing and pieces and len(pieces[0].split()) > MAX_WORDS and _ARTICLE.match(gloss):
        cut = _DESCRIBES.sub("", pieces[0])  # a noun definition, cut where it describes
        if len(cut.split()) == 1 and cut not in GENERIC:  # "hammer", not a clipped phrase
            pieces[0] = cut
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
            seen = [i for i, o in enumerate(out) if _same(o) == _same(piece)]
            if not seen:
                out.append(piece)
    return ", ".join(out[:MAX_PIECES])


def _lexique_freq() -> dict[tuple[str, str], float]:
    """{(form, pos): films + books per million} from Lexique, {} when it isn't there."""
    freq: dict[tuple[str, str], float] = defaultdict(float)
    if LEXIQUE.exists():
        with LEXIQUE.open(encoding="utf-8") as f:
            header = f.readline().rstrip("\n").split("\t")
            for row in f:
                r = dict(zip(header, row.rstrip("\n").split("\t"), strict=False))
                if pos := LEXIQUE_POS.get(r["cgram"].split(":")[0]):
                    form = r["ortho"].strip().lower()
                    freq[form, pos] += float(r["freqfilms2"] or 0) + float(r["freqlivres"] or 0)
    return freq


def main(src: Path) -> None:
    common = set()
    with gzip.open(DATA / "fr_forms.tsv.gz", "rt", encoding="utf-8") as f:
        for line in f:
            form, _, freq, _ = line.rstrip("\n").split("\t")
            if float(freq) >= MIN_FREQ:
                common.add(form)
    # (word, pos) -> [(gender, senses)] per Wiktionary entry
    found: dict[tuple[str, str], list[tuple[str, list]]] = {}
    with gzip.open(src, "rt", encoding="utf-8") as f:
        for line in f:
            d = json.loads(line)
            word, pos = d.get("word", ""), POS.get(d.get("pos", ""))
            if not pos or d.get("lang_code") != "fr" or word not in common:
                continue
            senses, tags = [], set()
            for i, s in enumerate(d.get("senses", [])):
                stags = set(s.get("tags", []))
                tags |= stags
                if s.get("glosses") and not stags & SKIP_TAGS and "form_of" not in s:
                    if found_t := translations(_header_child(s["glosses"]), describing=i == 0):
                        senses.append(found_t)
            if senses:
                found.setdefault((word, pos), []).append((_gender(tags), senses))
    rows = {}
    for (word, pos), entries in found.items():
        rows[word, pos] = (entries[0][0], gloss([senses for _, senses in entries]))
    rows |= OVERRIDES
    freq = _lexique_freq()
    first = {word: i for i, word in enumerate(dict.fromkeys(w for w, _ in rows))}
    ordered = sorted(
        rows,
        key=lambda k: (
            first[k[0]],
            not (k[0] in ADJECTIVE_FIRST and k[1] == "adjective"),
            -freq[k],
        ),
    )
    lines = [f"{w}\t{p}\t{rows[w, p][0]}\t{rows[w, p][1]}\n" for w, p in ordered]
    with gzip.open(OUT, "wt", encoding="utf-8", compresslevel=9) as f:
        f.writelines(lines)
    print(f"{len(lines)} entries, {len(first)} words -> {OUT}", file=sys.stderr)


if __name__ == "__main__":
    main(Path(sys.argv[1]))
