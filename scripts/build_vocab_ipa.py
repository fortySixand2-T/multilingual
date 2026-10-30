#!/usr/bin/env python3
"""Fill `ipa` (and `fem_ipa`) on every content-bank vocab card, checked two ways.

Sources, in order of trust:
  1. REVIEWED below: hand-checked answers for the cards where the sources disagreed.
  2. Single words: Lexique383's `phon` (a curated lexical database, CC BY-SA 4.0,
     http://www.lexique.org), mapped from its own code to IPA. Homographs pick the row
     matching the card's part of speech, then the most frequent lemma (fils: fis > fil).
  3. Phrases: Piper's own eSpeak phonemes (it knows liaison and elision; a word-by-word
     Lexique join does not), via the app's `normalize_ipa`.

Each card is also checked against the other source; the cards where they disagree
beyond accepted variation (o/ɔ, e/ɛ, a dropped schwa) are written to the report so a
person reviews them and records the answer in REVIEWED.

Piper's phonemes come from the box, one word per run (a multi-line run joins the words
into one sentence, with liaison across them):

    ssh rohith@10.0.0.54 "docker exec -i multilingual-app-1 sh -c 'while IFS= read -r w; do
      printf \\"%s\\t\\" \\"\\$w\\"; printf \\"%s\\n\\" \\"\\$w\\" | piper --model
      /app/voices/fr_FR-upmc-medium.onnx --output_file /dev/null --debug 2>&1 |
      grep -o \\"ids: .*\\" | sed \\"s/^ids: //\\"; done'" < forms.txt > piper.tsv

    python scripts/build_vocab_ipa.py imports/Lexique383.tsv piper.tsv --report r.tsv
    python scripts/build_vocab_ipa.py imports/Lexique383.tsv piper.tsv --write

`forms.txt` is every `fr` and `fem` in the bank, one per line (`--forms` prints it).
"""

from __future__ import annotations

import argparse
import csv
import re
import sys
from collections import defaultdict
from pathlib import Path

import yaml

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))  # run as a plain script

from app.content.ipa import normalize_ipa  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
LEVELS = ("a1", "a2", "b1", "b2")

# Lexique's phonetic code -> IPA (the rest of its letters already are IPA).
_LEXIQUE = str.maketrans(
    {
        "E": "ɛ",
        "°": "ə",
        "2": "ø",
        "9": "œ",
        "5": "ɛ̃",
        "1": "œ̃",
        "@": "ɑ̃",
        "§": "ɔ̃",
        "O": "ɔ",
        "S": "ʃ",
        "Z": "ʒ",
        "N": "ɲ",
        "R": "ʁ",
        "8": "ɥ",
        "G": "ŋ",
        "g": "ɡ",
    }
)
_CGRAM = {
    "noun": ("NOM",),
    "verb": ("VER", "AUX"),
    "adjective": ("ADJ",),
    "numeral": ("ADJ:num",),
    "adverb": ("ADV",),
    "interjection": ("ONO",),
}
_ELIDED = re.compile(r"^(qu|[cdjlmnst])['’]", re.IGNORECASE)
_CLITIC = {"qu": "k", "c": "s", "j": "ʒ"}  # the rest sound as spelled

# Hand-checked against Wiktionary where Lexique and Piper disagreed or Lexique has no
# entry and Piper is wrong (English reading, nj for ɲ, an initialism read as a word).
REVIEWED: dict[str, str] = {
    "sac à dos": "sak a do",
    "oublier de": "ublije də",
    "se renseigner": "sə ʁɑ̃sɛɲe",
    "témoigner de": "temwaɲe də",
    "obsolescence programmée": "ɔpsɔlɛsɑ̃s pʁɔɡʁame",
    "zoo": "zo",
    "soccer": "sɔkœʁ",
    "fiançailles": "fjɑ̃saj",
    "basketball": "baskɛtbol",
    "wifi": "wifi",
    "PIB": "peibe",
    "infonuagique": "ɛ̃fɔnɥaʒik",
    "dehors": "dəɔʁ",
    "bon appétit": "bɔ̃ napeti",
    "soins à domicile": "swɛ̃ a domisil",
}


def load_lexique(path: Path) -> dict[str, list[tuple[str, str, float]]]:
    """ortho -> [(ipa, cgram, lemma frequency)]."""
    rows: dict[str, list[tuple[str, str, float]]] = defaultdict(list)
    with path.open(encoding="utf-8") as f:
        for r in csv.DictReader(f, delimiter="\t"):
            freq = float(r["freqlemfilms2"] or 0) + float(r["freqlemlivres"] or 0)
            rows[r["ortho"]].append((r["phon"].translate(_LEXIQUE), r["cgram"], freq))
    return rows


def lexique_word(lex: dict, word: str, pos: str = "") -> str | None:
    word = word.lower()
    rows = lex.get(word) or lex.get(word.replace("œ", "oe").replace("æ", "ae"))  # coeur
    if not rows:
        return None
    wanted = [r for r in rows if r[1].startswith(_CGRAM.get(pos, ("",)))] or rows
    ipa = max(wanted, key=lambda r: r[2])[0]
    # Lexique writes the voiced -isme of speech (tuʁizm); dictionaries write /tuʁism/
    return ipa[:-2] + "sm" if word.endswith("isme") and ipa.endswith("zm") else ipa


def lexique_phrase(lex: dict, text: str) -> str | None:
    """Word-by-word Lexique join (no liaison) — only a cross-check for phrases."""
    out = []
    for token in text.split():
        clitic = ""
        if m := _ELIDED.match(token):
            clitic = _CLITIC.get(m.group(1).lower(), m.group(1).lower())
            token = token[m.end() :]
        parts = [token] if lex.get(token.lower()) else token.split("-")
        ipas = [lexique_word(lex, p.strip(",.!?")) for p in parts]
        if None in ipas:
            return None
        out.append(clitic + "".join(ipas))
    return " ".join(out)


def _loose(ipa: str) -> str:
    """Comparison key that ignores accepted variation: spacing/liaison marks, o/ɔ, e/ɛ,
    optional schwas (ə/ø/œ), y/ɥ (eSpeak writes y for ɥ), and eSpeak's g vs IPA ɡ."""
    ipa = re.sub(r"[\s‿\-.ˈˌː]", "", ipa).replace("g", "ɡ")
    ipa = ipa.translate(str.maketrans({"ɔ": "o", "ɛ": "e", "œ": "ə", "ø": "ə", "ɥ": "y"}))
    return ipa.replace("ə", "")


def piper_ipa(raw: str, fr: str) -> str:
    return normalize_ipa(raw.replace("-", "").rstrip("."), fr)


def resolve(lex: dict, piper: dict[str, str], fr: str, pos: str) -> tuple[str, str, str, str]:
    """(chosen ipa, source, lexique, piper) for one spelling."""
    p = piper_ipa(piper.get(fr, ""), fr)
    phrase = " " in fr.strip() or bool(_ELIDED.match(fr))
    lx = lexique_phrase(lex, fr) if phrase else lexique_word(lex, fr, pos)
    if fr in REVIEWED:
        return REVIEWED[fr], "reviewed", lx or "", p
    if lx and (not phrase or _loose(lx) == _loose(p)):
        return lx, "lexique", lx, p  # a phrase keeps Piper only when liaison changes it
    return p, "piper", lx or "", p


def bank() -> list[tuple[str, Path, dict]]:
    return [
        (level, f, card)
        for level in LEVELS
        for f in sorted((ROOT / "content" / level / "vocab").glob("*.yaml"))
        for card in yaml.safe_load(f.read_text(encoding="utf-8")) or []
    ]


def build(lex: dict, piper: dict[str, str]) -> tuple[dict[tuple[str, str], str], list[list[str]]]:
    """({(card id, field): ipa}, report rows for disagreements and gaps)."""
    chosen: dict[tuple[str, str], str] = {}
    report = []
    for level, _, card in bank():
        for field, fr in (("ipa", card["fr"]), ("fem_ipa", card.get("fem", ""))):
            if not fr:
                continue
            ipa, source, lx, p = resolve(lex, piper, fr, card.get("pos", ""))
            chosen[(card["id"], field)] = ipa
            if source == "reviewed":
                continue
            if not ipa:
                why = "no ipa"
            elif not lx:
                why = "not in lexique"
            elif _loose(lx) != _loose(p):
                why = "disagree"
            else:
                continue
            report.append([why, level, card["id"], fr, card.get("pos", ""), ipa, lx, p])
    return chosen, report


def write(chosen: dict[tuple[str, str], str]) -> int:
    """Insert or replace `ipa:` after each card's `fr:` line (`fem_ipa:` after `fem:`),
    keeping every file's own layout. Returns the number of files changed."""
    changed = 0
    for f in sorted({f for _, f, _ in bank()}):
        lines = [
            ln
            for ln in f.read_text(encoding="utf-8").splitlines()
            if not re.match(r"\s+(fem_)?ipa:", ln)
        ]
        out, card_id = [], None
        for ln in lines:
            out.append(ln)
            if m := re.match(r"- id:\s*(\S+)", ln):
                card_id = m.group(1)
            elif m := re.match(r"(\s+)(fr|fem):", ln):
                field = "ipa" if m.group(2) == "fr" else "fem_ipa"
                if ipa := chosen.get((card_id, field)):
                    out.append(f"{m.group(1)}{field}: {ipa}")
        text = "\n".join(out) + "\n"
        if text != f.read_text(encoding="utf-8"):
            f.write_text(text, encoding="utf-8")
            changed += 1
    return changed


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("lexique", nargs="?", type=Path)
    ap.add_argument("piper", nargs="?", type=Path, help="fr<TAB>raw phonemes per line")
    ap.add_argument("--forms", action="store_true", help="print every fr/fem spelling")
    ap.add_argument("--report", type=Path, help="write disagreements/gaps as TSV")
    ap.add_argument("--write", action="store_true", help="write ipa into the YAML")
    args = ap.parse_args()
    if args.forms:
        seen = dict.fromkeys(w for _, _, c in bank() for w in (c["fr"], c.get("fem", "")) if w)
        print("\n".join(seen))
        return
    if not (args.lexique and args.piper):
        ap.error("lexique and piper paths are required")
    piper = {}
    for ln in args.piper.read_text(encoding="utf-8").splitlines():
        fr, _, raw = ln.partition("\t")
        piper[fr] = raw.strip()
    chosen, report = build(load_lexique(args.lexique), piper)
    if args.report:
        with args.report.open("w", encoding="utf-8") as f:
            w = csv.writer(f, delimiter="\t")
            w.writerow(["why", "level", "id", "fr", "pos", "chosen", "lexique", "piper"])
            w.writerows(report)
    counts: dict[str, int] = defaultdict(int)
    for row in report:
        counts[row[0]] += 1
    print(f"{len(chosen)} spellings; to review: {dict(counts)}", file=sys.stderr)
    if args.write:
        print(f"wrote {write(chosen)} files", file=sys.stderr)


if __name__ == "__main__":
    main()
