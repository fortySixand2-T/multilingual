#!/usr/bin/env python3
"""Build app/content/data/fr_gender.tsv from a Lexique383.tsv extract.

Lexique scatters the `genre` column across a lemma's inflected rows (the singular
headword is often blank while the plural carries m/f), so gender is resolved at
the LEMMA level, then written per surface form (ortho):

  * If a lemma family carries a single gender, every form of it gets that gender
    (robust to the blank-headword quirk: voiture -> f).
  * If a lemma family carries both genders — an animate m/f pair like chien+chienne
    sharing lemma `chien` — each surface form is split by its OWN rows' genders,
    and a blank masculine headword defaults to 'm' (chien -> m, chienne -> f).
    A form genuinely attested as both (un/une élève) stays 'mf'.

A curated override block is appended last so hand-checked cases win.
"""

from __future__ import annotations

import sys
from pathlib import Path

SRC = Path(sys.argv[1])
OUT = Path(sys.argv[2])

lemma_genders: dict[str, set[str]] = {}  # lemme -> {m,f}
ortho_own: dict[str, set[str]] = {}  # ortho -> genders on its own rows
ortho_lemmas: dict[str, set[str]] = {}  # ortho -> lemmas it appears under

with SRC.open(encoding="utf-8") as f:
    next(f)  # header
    for line in f:
        parts = line.rstrip("\n").split("\t")
        if len(parts) < 5:
            continue
        ortho, lemme, cgram, genre = parts[0], parts[2], parts[3], parts[4]
        if cgram != "NOM":
            continue
        ortho = ortho.strip().lower()
        lemme = lemme.strip().lower()
        if not ortho or not lemme:
            continue
        ortho_lemmas.setdefault(ortho, set()).add(lemme)
        ortho_own.setdefault(ortho, set())
        if genre in ("m", "f"):
            lemma_genders.setdefault(lemme, set()).add(genre)
            ortho_own[ortho].add(genre)


def resolve(ortho: str) -> str | None:
    family: set[str] = set()
    for lem in ortho_lemmas.get(ortho, ()):
        family |= lemma_genders.get(lem, set())
    if not family:
        return None  # no gender anywhere in the family
    if family == {"m"} or family == {"f"}:
        return next(iter(family))
    # mixed family -> split by this form's own rows
    own = ortho_own.get(ortho, set())
    if own == {"m", "f"}:
        return "mf"
    if own == {"m"}:
        return "m"
    if own == {"f"}:
        return "f"
    return "m"  # blank headword of an m/f pair -> masculine base form


table: dict[str, str] = {}
for ortho in ortho_lemmas:
    g = resolve(ortho)
    if g:
        table[ortho] = g

# Curated overrides — win over the bulk extract. Fix Lexique gaps (nouns whose
# genre is blank throughout, e.g. 'fin') and epicene nouns Lexique tags with a
# single gender but that take both articles in real usage.
OVERRIDES = {
    "fin": "f",
    "livre": "m",  # genre blank throughout Lexique; le livre (book) is dominant
    "enfant": "mf",
    "ami": "mf",
    "élève": "mf",
    "collègue": "mf",
    "camarade": "mf",
    "touriste": "mf",
    "artiste": "mf",
    "propriétaire": "mf",
    "adulte": "mf",
    "partenaire": "mf",
}
table.update(OVERRIDES)

header = (
    "# French noun gender table — the authoritative source for enrich.resolve_gender.\n"
    "# Format: <word><TAB><m|f|mf>. Word is lowercase, accents kept, no article.\n"
    "# Generated from Lexique383 (cgram==NOM): gender resolved per lemma family, then\n"
    "# written per surface form; mixed m/f families are split by form (chien=m,\n"
    "# chienne=f) while true epicenes stay 'mf'. A curated override block wins last.\n"
    "# Lexique is distributed under CC BY-SA 4.0 (http://www.lexique.org).\n"
    "# Regenerate: download Lexique383.tsv from lexique.org, then\n"
    "#   python scripts/build_gender_table.py Lexique383.tsv app/content/data/fr_gender.tsv\n"
)

lines = [f"{w}\t{g}" for w, g in sorted(table.items())]
OUT.write_text(header + "\n".join(lines) + "\n", encoding="utf-8")
n_mf = sum(1 for g in table.values() if g == "mf")
print(f"wrote {len(table)} entries ({n_mf} mf) to {OUT}")
