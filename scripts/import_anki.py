#!/usr/bin/env python3
"""Import an AnkiWeb shared French deck (.apkg) into review-ready vocab YAML.

Slice 1 of the AnkiWeb plan (docs/anki-vocab-plan.md). An `.apkg` is a zip holding
a SQLite `collection.anki2`/`.anki21` (notes in `notes.flds`, fields joined by
\\x1f). We read the two front/back fields, clean them, keep single words / short
phrases, DROP anything that collides with the 780 existing vocab ids or lemmas,
heuristically fill gender/pos, and write `content/<level>/vocab/<tag>.yaml`.

LICENSING: the `.apkg` is treated as a **wordlist reference only** — a gitignored
build input under `imports/`. What we commit is our own schema + enrichment, which
must be **human-reviewed before sync** (this script never syncs). See the plan.

    python scripts/import_anki.py imports/french-travel.apkg --level a2 --tag voyage \\
        --deck "French Travel (AnkiWeb #123)" --source https://ankiweb.net/shared/info/123

Add --fr-field/--en-field to pick columns (default fr=0, en=1); --swap = fr is the
back. --keep-phrases keeps up to 4-word expressions (default: single words only).
"""

from __future__ import annotations

import argparse
import glob
import html
import re
import sqlite3
import sys
import tempfile
import unicodedata
import zipfile
from pathlib import Path

import yaml

CONTENT_ROOT = Path(__file__).resolve().parent.parent / "content"

# Leading article -> grammatical gender guess. Only true singular/plural articles:
# `les` gives no gender signal (leaves it unresolved for the human). Contractions and
# partitives (au/du/des/de) are deliberately excluded — they mostly head fixed phrases
# ("au revoir", "pomme de terre"), so stripping them would mangle the lemma. Elided
# l'/d' are handled separately in strip_article.
_ARTICLE_GENDER = {
    "le": "m",
    "un": "m",
    "la": "f",
    "une": "f",
    "les": "",
}
_SOUND_RE = re.compile(r"\[sound:[^\]]*\]")
_TAG_RE = re.compile(r"<[^>]+>")
_CLOZE_RE = re.compile(r"\{\{c\d+::")


class ImportError_(Exception):
    """Deck can't be read (unsupported format, no notes, etc.)."""


# --- reading the .apkg --------------------------------------------------------


def read_apkg_notes(apkg_path: Path) -> list[list[str]]:
    """Return each note's field list (split on the \\x1f separator)."""
    with zipfile.ZipFile(apkg_path) as z:
        names = set(z.namelist())
        # Prefer the newer collection if present; both keep notes in `notes.flds`.
        db_name = next((n for n in ("collection.anki21", "collection.anki2") if n in names), None)
        if db_name is None:
            # v3 exports ship zstd-compressed `collection.anki21b` — not plain SQLite.
            if "collection.anki21b" in names:
                raise ImportError_(
                    "this looks like a newer (v3/zstd) .apkg; re-export from Anki as a "
                    "'Legacy' .apkg (Export → uncheck 'Support older Anki versions' OFF)"
                )
            raise ImportError_("no collection.anki2/.anki21 inside the .apkg")
        with tempfile.TemporaryDirectory() as td:
            db_path = Path(td) / db_name
            db_path.write_bytes(z.read(db_name))
            con = sqlite3.connect(db_path)
            try:
                rows = con.execute("SELECT flds FROM notes").fetchall()
            finally:
                con.close()
    return [r[0].split("\x1f") for r in rows]


def clean_text(s: str) -> str:
    """Strip HTML, media/sound refs, and entities; collapse whitespace."""
    s = _SOUND_RE.sub(" ", s)
    s = _TAG_RE.sub(" ", s)
    s = html.unescape(s)
    s = s.replace("\xa0", " ")
    return " ".join(s.split()).strip()


# --- normalizing / enriching --------------------------------------------------


def strip_article(fr: str) -> tuple[str, str]:
    """(lemma_without_article, gender_guess). Existing cards store `fr` bare
    (café, not le café), so we split the article off and use it for gender."""
    parts = fr.split(" ", 1)
    if len(parts) == 2 and parts[0].lower() in _ARTICLE_GENDER:
        return parts[1].strip(), _ARTICLE_GENDER[parts[0].lower()]
    # `l'eau` — elided article glued to the word.
    low = fr.lower()
    if low.startswith("l'") or low.startswith("l’"):
        return fr[2:].strip(), ""
    return fr, ""


def slugify(fr: str) -> str:
    """ASCII, lowercase, alnum+underscore id from a French lemma (café -> cafe)."""
    ascii_ = "".join(c for c in unicodedata.normalize("NFD", fr) if unicodedata.category(c) != "Mn")
    slug = re.sub(r"[^a-z0-9]+", "_", ascii_.lower()).strip("_")
    return slug


def build_candidate(fr_raw: str, en_raw: str, tag: str, *, keep_phrases: bool) -> dict | None:
    """One cleaned note -> a Vocab-shaped dict, or None if it should be skipped."""
    fr, en = clean_text(fr_raw), clean_text(en_raw)
    if not fr or not en:
        return None
    if _CLOZE_RE.search(fr) or _CLOZE_RE.search(en):
        return None  # cloze notes aren't vocab pairs
    lemma, gender = strip_article(fr)
    if not lemma:
        return None
    words = lemma.split()
    if len(words) > (4 if keep_phrases else 1):
        return None  # sentence / long phrase — not a vocab card
    vid = slugify(lemma)
    if not vid:
        return None
    pos = "noun" if gender else ""  # an article implies a noun; otherwise leave blank
    return {
        "id": vid,
        "fr": lemma,
        "en": en,
        "gender": gender,
        "pos": pos,
        "tags": [tag],
        # bookkeeping (dropped before emit); flags rows a human must check
        "_review": _review_flags(lemma, en, gender, words),
    }


def _review_flags(lemma: str, en: str, gender: str, words: list[str]) -> list[str]:
    flags: list[str] = []
    if not gender:
        flags.append("gender?")  # noun gender unresolved (l'/les/no article)
    if len(words) > 1:
        flags.append("phrase")
    if len(en) > 40 or "," in en or ";" in en:
        flags.append("long-en")
    return flags


# --- dedup against the existing bank ------------------------------------------


def existing_vocab() -> tuple[set[str], set[str]]:
    """All vocab ids and normalized French lemmas already in content/*/vocab."""
    ids: set[str] = set()
    lemmas: set[str] = set()
    for f in glob.glob(str(CONTENT_ROOT / "*" / "vocab" / "*.yaml")):
        for v in yaml.safe_load(Path(f).read_text(encoding="utf-8")) or []:
            ids.add(v["id"])
            lemmas.add(v["fr"].strip().lower())
    return ids, lemmas


def dedup(cands: list[dict], ids: set[str], lemmas: set[str]) -> tuple[list[dict], int]:
    """Keep only genuinely new lemmas; also de-dup within the deck itself."""
    kept: list[dict] = []
    seen_ids = set(ids)
    seen_lemmas = set(lemmas)
    skipped = 0
    for c in cands:
        if c["id"] in seen_ids or c["fr"].lower() in seen_lemmas:
            skipped += 1
            continue
        seen_ids.add(c["id"])
        seen_lemmas.add(c["fr"].lower())
        kept.append(c)
    return kept, skipped


# --- emit ---------------------------------------------------------------------


class _FlowList(list):
    """A list that YAML dumps inline, so `tags: [voyage]` matches house style."""


def _flow_list(dumper, data):
    return dumper.represent_sequence("tag:yaml.org,2002:seq", data, flow_style=True)


yaml.add_representer(_FlowList, _flow_list)


def to_yaml(records: list[dict], *, deck: str, source: str, level: str, tag: str) -> str:
    header = (
        f"# Imported from AnkiWeb deck: {deck or '(unnamed)'}\n"
        f"# Source: {source or '(none given)'}\n"
        f"# Imported by scripts/import_anki.py — REVIEW BEFORE SYNC.\n"
        f"# Check gender/pos, fix translations, drop anything off-register for {level}.\n"
        f"# Deck licence is the uploader's; treat this as a wordlist reference, not a copy.\n\n"
    )
    clean = []
    for r in records:
        rec = {"id": r["id"], "fr": r["fr"], "en": r["en"]}
        # Omit empty gender/pos to match the authored files (they don't write `gender: ''`).
        if r["gender"]:
            rec["gender"] = r["gender"]
        if r["pos"]:
            rec["pos"] = r["pos"]
        rec["tags"] = _FlowList(r["tags"])
        clean.append(rec)
    # Dump each record on its own with a blank line between (house style).
    blocks = [yaml.dump([rec], allow_unicode=True, sort_keys=False, width=200) for rec in clean]
    return header + "\n".join(b.rstrip() + "\n" for b in blocks)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Import an AnkiWeb .apkg into vocab YAML.")
    ap.add_argument("apkg", type=Path, help="path to the .apkg file")
    ap.add_argument("--level", required=True, help="CEFR level dir, e.g. a2")
    ap.add_argument("--tag", required=True, help="deck tag (becomes the themed deck), e.g. voyage")
    ap.add_argument("--deck", default="", help="deck name (provenance header)")
    ap.add_argument("--source", default="", help="deck URL (provenance header)")
    ap.add_argument("--fr-field", type=int, default=0, help="note field index for French")
    ap.add_argument("--en-field", type=int, default=1, help="note field index for English")
    ap.add_argument("--swap", action="store_true", help="French is the back field (fr=1, en=0)")
    ap.add_argument("--keep-phrases", action="store_true", help="keep up to 4-word expressions")
    ap.add_argument("--limit", type=int, default=0, help="cap number of new cards (0 = all)")
    ap.add_argument(
        "--out",
        type=Path,
        default=None,
        help="output path (default content/<lvl>/vocab/<tag>.yaml)",
    )
    ap.add_argument("--dry-run", action="store_true", help="print report only, don't write")
    args = ap.parse_args(argv)

    fr_i, en_i = (args.en_field, args.fr_field) if args.swap else (args.fr_field, args.en_field)

    try:
        notes = read_apkg_notes(args.apkg)
    except (ImportError_, FileNotFoundError, zipfile.BadZipFile) as e:
        print(f"error: {e}", file=sys.stderr)
        return 2

    cands: list[dict] = []
    for flds in notes:
        if len(flds) <= max(fr_i, en_i):
            continue
        c = build_candidate(flds[fr_i], flds[en_i], args.tag, keep_phrases=args.keep_phrases)
        if c is not None:
            cands.append(c)

    ids, lemmas = existing_vocab()
    kept, skipped = dedup(cands, ids, lemmas)
    if args.limit > 0:
        kept = kept[: args.limit]

    print(
        f"{len(notes)} notes -> {len(cands)} candidates -> {len(kept)} new "
        f"({skipped} already in the bank).",
        file=sys.stderr,
    )
    needs = [k for k in kept if k["_review"]]
    if needs:
        print(f"\n{len(needs)} row(s) need review before sync:", file=sys.stderr)
        for k in needs:
            print(
                f"  {k['id']:<22} {k['fr']:<20} -> {k['en']:<28} [{', '.join(k['_review'])}]",
                file=sys.stderr,
            )

    if not kept:
        print("nothing new to import.", file=sys.stderr)
        return 0

    out = args.out or (CONTENT_ROOT / args.level / "vocab" / f"{args.tag}.yaml")
    text = to_yaml(kept, deck=args.deck, source=args.source, level=args.level, tag=args.tag)
    if args.dry_run:
        print(text)
        return 0
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(text, encoding="utf-8")
    print(f"\nwrote {len(kept)} cards -> {out}", file=sys.stderr)
    print(
        f"NEXT: review {out}, then "
        f"`/tmp/tef312/bin/python -m app.content.sync {args.level}` "
        f"and `python scripts/gen_audio.py {args.level}`.",
        file=sys.stderr,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
