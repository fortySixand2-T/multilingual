"""Build app/content/data/fr_conj.tsv.gz from kaikki.org's English Wiktionary extract
of French: the present tense of every common verb.

One line per verb: `<infinitive>\t<je>\t<tu>\t<il>\t<nous>\t<vous>\t<ils>`, the bare
forms (a pronominal verb's me/te/se are the app's to add); a person a verb has no form
for is empty (falloir: only "faut"). A verb is kept when Lexique sees it at least once per
million words. Each form is checked against the ones Lexique tags for that person and
verb; a disagreement is printed for review, never written silently (Lexique tags the
odd homograph wrongly: "donnes" as nous). Wiktionary is CC BY-SA 4.0 (see
app/content/data/NOTICE.md); extract from https://kaikki.org.

    curl -O https://kaikki.org/dictionary/French/kaikki.org-dictionary-French.jsonl.gz
    python -m scripts.build_conj_table kaikki.org-dictionary-French.jsonl.gz
"""

from __future__ import annotations

import csv
import gzip
import json
import re
import sys
from collections import defaultdict
from pathlib import Path

DATA = Path(__file__).resolve().parent.parent / "app" / "content" / "data"
OUT = DATA / "fr_conj.tsv.gz"
LEXIQUE = Path(__file__).resolve().parent.parent / "imports" / "Lexique383.tsv"
MIN_FREQ = 1.0  # per million words, films and books together
PERSONS = (
    ("first-person", "singular"),
    ("second-person", "singular"),
    ("third-person", "singular"),
    ("first-person", "plural"),
    ("second-person", "plural"),
    ("third-person", "plural"),
)
LEXIQUE_PERSONS = ("1s", "2s", "3s", "1p", "2p", "3p")
_REFLEXIVE = re.compile(r"^(?:me |te |se |nous |vous |m'|t'|s')")


def lexique_verbs() -> tuple[set[str], dict[str, list[dict[str, float]]]]:
    """Common verb infinitives, and each verb's present forms by person as Lexique tags
    them, with their frequency."""
    common: set[str] = set()
    forms: dict[str, list[dict[str, float]]] = defaultdict(lambda: [{} for _ in LEXIQUE_PERSONS])
    with LEXIQUE.open(encoding="utf-8") as f:
        for r in csv.DictReader(f, delimiter="\t"):
            if r["cgram"] not in ("VER", "AUX"):
                continue
            freq = float(r["freqlemfilms2"] or 0) + float(r["freqlemlivres"] or 0)
            if freq >= MIN_FREQ:
                common.add(r["lemme"])
            for tag in r["infover"].split(";"):
                if tag.startswith("ind:pre:") and tag[8:] in LEXIQUE_PERSONS:
                    seen = forms[r["lemme"]][LEXIQUE_PERSONS.index(tag[8:])]
                    seen[r["ortho"]] = float(r["freqfilms2"] or 0) + float(r["freqlivres"] or 0)
    return common, forms


def conjugation(entry: dict, seen: list[dict[str, float]]) -> list[str] | None:
    """The six present forms of a Wiktionary verb entry, or None when it has none. Of
    the variant spellings Wiktionary lists in parallel (harcèle / harcelle, assieds /
    assois), the series Lexique sees most often is kept whole, so a table never mixes
    the two."""
    variants: list[list[str]] = [[] for _ in PERSONS]
    for f in entry.get("forms", []):
        tags = set(f.get("tags") or [])
        if {"indicative", "present"} <= tags and "multiword-construction" not in tags:
            for i, person in enumerate(PERSONS):
                form = _REFLEXIVE.sub("", f["form"])
                if set(person) <= tags and form[0] not in "-/" and form not in variants[i]:
                    variants[i].append(form)  # not "-" (none), a /pronunciation/ or a repeat
    if not any(variants):
        return None
    series = max(
        range(max(map(len, variants))),
        key=lambda k: sum(
            lex.get(vs[k], 0) if len(vs) > k else 0 for vs, lex in zip(variants, seen, strict=True)
        ),
    )
    return [vs[series] if len(vs) > series else (vs[0] if vs else "") for vs in variants]


def main(path: str) -> None:
    common, lexique = lexique_verbs()
    rows: dict[str, list[str]] = {}
    with gzip.open(path, "rt", encoding="utf-8") as f:
        for line in f:
            entry = json.loads(line)
            word = entry.get("word", "")
            if entry.get("pos") != "verb" or word not in common or word in rows:
                continue
            if (conj := conjugation(entry, lexique[word])) is not None:
                rows[word] = conj
    for word, present in sorted(rows.items()):
        for form, seen in zip(present, lexique[word], strict=True):
            if form and seen and form not in seen:
                print(f"check {word}: Wiktionary {form!r}, Lexique {sorted(seen)}")
    with gzip.open(OUT, "wt", encoding="utf-8", compresslevel=9) as out:
        for word, present in sorted(rows.items()):
            out.write("\t".join((word, *present)) + "\n")
    print(f"{len(rows)} verbs -> {OUT}")


if __name__ == "__main__":
    main(sys.argv[1])
