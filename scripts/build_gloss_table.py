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

    pip install wordfreq  # build-time only: English word frequencies
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

from wordfreq import zipf_frequency

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
    ("mon", "adjective"): ("m", "my"),
    ("traduire", "verb"): ("", "to translate"),
    ("réclamer", "verb"): ("", "to demand, to claim"),
    ("visser", "verb"): ("", "to screw (on, in)"),
    ("raisin", "noun"): ("m", "grape"),
    ("bouquin", "noun"): ("m", "book (informal)"),
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
    "figuratively",
    "literary",
    "reflexive",  # se plaindre "to complain" is its own headword, not plaindre's meaning
    # regional senses (file "traffic jam" is Belgian)
    *"Louisiana Quebec Canada Canadian Montreal Ontario Newfoundland New-England Belgium".split(),
    *"Switzerland Fribourg Luxembourg Africa Rwanda Morocco Congo Antilles Vietnam".split(),
    *"Lyon Alsace Lorraine Normandy Picardy Savoie".split(),
}
MAX_WORDS = 3  # per translation: longer is a definition ("good as opposed to evil")
MAX_SENSES = 2
MAX_PER_SENSE = 2
MAX_PIECES = 3
MIN_ZIPF = 3.0  # English word frequency an extra sense must reach (wordfreq's Zipf scale)
GENERIC = {"person", "someone", "one", "thing", "something", "man", "woman", "place", "act"}
_PAREN = re.compile(r"\s*\(([^()]*)\)")
_SPLIT = re.compile(r"\s*[,;]\s*")
_ARTICLE = re.compile(r"^(?:a|an|the) ", re.I)
_DESCRIPTION = re.compile(r"(?:a|an|the|used|that|which|who|where)\b", re.I)
_LABEL = re.compile(r"^\([^()]*\)\s*")  # "(climbing) to climb"
_DESCRIBES = re.compile(r"\s+(?:used|that|which|who|whose|where|placed|in which)\b.*")
# a bracket that isn't a short note, a binomial (Allium cepa) or a spelling note (color/colour)
_ASIDE = re.compile(r"[,;/]|\b(?:i\.e|e\.g|sense|see)\b|^[A-Z][a-z]+ [a-z]+$")


def _keep_paren(m: re.Match) -> str:
    inner = m.group(1)
    return m.group(0) if len(inner.split()) <= MAX_WORDS and not _ASIDE.search(inner) else ""


def _clean(piece: str) -> bool:
    """No list tail ("or privately hired", "usually pear-shaped"), label ("Audio: …") or
    broken bracket."""
    return (
        not re.match(r"(?:or|and|in particular|especially|specifically|usually|typically|often|chiefly|mainly)\b", piece, re.I)
        and not re.match(r"(?:synonym|alternative|variant) of\b", piece)
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
    gloss = gloss.split(": ")[0]  # "wise: prudent, cautious, and judicious" -> "wise"
    pieces = [_ARTICLE.sub("", _LABEL.sub("", p.strip("[] "))) for p in _SPLIT.split(gloss) if p]
    if describing and pieces and len(pieces[0].split()) > MAX_WORDS and _ARTICLE.match(gloss):
        cut = _DESCRIBES.sub("", pieces[0])  # a noun definition, cut where it describes
        if len(cut.split()) == 1 and cut not in GENERIC:  # "hammer", not a clipped phrase
            pieces[0] = cut
    short = [p for p in pieces if 0 < len(_PAREN.sub("", p).split()) <= MAX_WORDS and _clean(p)]
    # A long first piece is a definition whatever follows ("The most common adverb of
    # negation …, typically translating as not, don't, …"); a long later one makes the
    # rest its description ("water, a liquid that is transparent, colorless, …").
    if short[:1] != pieces[:1]:
        return []
    raw = _SPLIT.split(gloss)[1:]
    describes = [p for p in raw if len(p.split()) > MAX_WORDS and _DESCRIPTION.match(p)]
    return short[:1] if describes else short


def _gender(tags: set[str]) -> str:
    if {"masculine", "feminine"} <= tags:
        return "mf"
    return "m" if "masculine" in tags else "f" if "feminine" in tags else ""


def _same(piece: str) -> str:
    """What two translations share when they say the same thing: "to take off" and
    "take off", "law (legal code)" and "law (scientific principle)"."""
    return re.sub(r"^to ", "", _PAREN.sub("", piece).lower())


def _common(piece: str) -> bool:
    """An everyday English word, not a specialist's (fishing, not bulwark or wingtip):
    a word's extra senses are only worth a learner's attention in everyday English."""
    words = re.findall(r"[a-z]+", _PAREN.sub("", piece).lower())
    return not words or min(zipf_frequency(w, "en") for w in words) >= MIN_ZIPF


def _sentence(gloss: str) -> bool:
    """Written as a sentence ("Faith.", "Chaste, modest, …"), so its capital is no name's."""
    return gloss.endswith(".") or any(p[:1].islower() for p in _SPLIT.split(gloss)[1:])


def _normal(piece: str, word: str, pos: str, sentence: bool) -> str:
    """One house style: lower case unless a name ("German", "Thursday"), "to" on verbs."""
    if sentence and piece[1:2].islower():  # "Faith.", "Chaste, modest": sentence case
        piece = piece[0].lower() + piece[1:]
    infinitive = word.endswith(("er", "ir", "re"))  # not voilà, soit, issu
    if pos == "verb" and infinitive and not re.match(r"(?:to|can|may|must|will)\b", piece):
        piece = "to " + piece
    return piece


def gloss(entries: list[dict[int, list[str]]], word: str = "") -> str:
    """Up to MAX_PIECES translations across a word's same-pos entries: the first
    entry's first sense, then each homograph entry's first sense (pêche: "peach" then
    "fishing"), then the first entry's second sense, the extra ones only in everyday
    English (fraise: not "bulwark"). Senses are keyed by their place in Wiktionary, so a
    definition we couldn't use doesn't promote the rare sense behind it."""
    first, *others = entries
    senses = [first.get(0), *(e.get(0) for e in others), first.get(1)]  # [] for a definition
    out: list[str] = []
    used = 0
    for sense in filter(None, senses):
        if used == MAX_SENSES or (used and not _common(sense[0])):
            continue
        used += 1
        for piece in sense[:MAX_PER_SENSE]:
            french = bool(out) and _same(piece) == _same(word)  # carotte "carotte (tobacco roll)"
            if not french and all(_same(o) != _same(piece) for o in out):
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
            senses, tags = {}, set()
            for s in d.get("senses", []):
                stags = set(s.get("tags", []))
                tags |= stags
                if s.get("glosses") and not stags & SKIP_TAGS and "form_of" not in s:
                    i, text = len(senses), _header_child(s["glosses"])  # i: place among usable
                    found_t = translations(text, describing=i == 0)
                    senses[i] = [_normal(t, word, pos, _sentence(text)) for t in found_t]
            if any(senses.values()):
                found.setdefault((word, pos), []).append((_gender(tags), senses))
    rows = {}
    for (word, pos), entries in found.items():
        if text := gloss([senses for _, senses in entries], word):
            rows[word, pos] = (entries[0][0], text)
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
