"""Build app/content/data/fr_forms.tsv.gz from a Lexique383.tsv extract.

One line per single-word spelling (ortho): `<form>\t<pos>\t<frequency>\t<note>`, where
frequency is films + books per million, pos is the part of speech that carries at
least two thirds of it ("" when no reading dominates: élève is a noun and a verb), and
note marks an inflected adjective form: "f.", "pl." or "f. pl." (grandes).
The lookup uses it to fix the model's accents and adjective/noun mix-ups
(app/content/lexicon.py). Lexique383 is CC BY-SA 4.0, http://www.lexique.org.

    python scripts/build_forms_table.py imports/Lexique383.tsv
"""

from __future__ import annotations

import csv
import gzip
import sys
from collections import defaultdict
from pathlib import Path

OUT = Path(__file__).resolve().parent.parent / "app" / "content" / "data" / "fr_forms.tsv.gz"
POS = {
    "NOM": "noun",
    "VER": "verb",
    "AUX": "verb",
    "ADJ": "adjective",
    "ADV": "adverb",
    "PRE": "preposition",
    "CON": "conjunction",
    "PRO": "pronoun",
}


def main(src: Path) -> None:
    freq: dict[str, dict[str, float]] = defaultdict(lambda: defaultdict(float))
    adj: dict[str, list[tuple[str, str]]] = defaultdict(list)  # form -> [(genre, nombre)]
    with src.open(encoding="utf-8") as f:
        for r in csv.DictReader(f, delimiter="\t"):
            form, pos = r["ortho"].strip().lower(), POS.get(r["cgram"].split(":")[0])
            if pos and form and " " not in form:
                freq[form][pos] += float(r["freqfilms2"] or 0) + float(r["freqlivres"] or 0)
                if r["cgram"] == "ADJ":
                    adj[form].append((r["genre"], r["nombre"]))
    lines = []
    for form, by_pos in sorted(freq.items()):
        total = sum(by_pos.values())
        top = max(by_pos, key=by_pos.get)
        dominant = top if total and by_pos[top] >= total * 2 / 3 else ""
        rows = adj.get(form, [])
        fem = bool(rows) and all(g == "f" for g, _ in rows)
        plural = bool(rows) and all(n == "p" for _, n in rows)
        note = " ".join(["f."] * fem + ["pl."] * plural)
        lines.append(f"{form}\t{dominant}\t{round(total, 2):g}\t{note}\n")
    with gzip.open(OUT, "wt", encoding="utf-8", compresslevel=9) as f:
        f.writelines(lines)
    print(f"{len(lines)} forms -> {OUT}", file=sys.stderr)


if __name__ == "__main__":
    main(Path(sys.argv[1]))
