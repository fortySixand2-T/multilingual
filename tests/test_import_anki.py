"""AnkiWeb .apkg importer (scripts/import_anki.py) — parsing, enrichment, dedup, emit.

Uses a synthetic .apkg (a minimal SQLite `notes` table zipped up) so the test is
deterministic and needs no real deck download.
"""

from __future__ import annotations

import sqlite3
import zipfile
from pathlib import Path

import yaml

from app.content.models import Vocab
from scripts import import_anki as ia

_SEP = "\x1f"


def _make_apkg(
    path: Path, notes: list[tuple[str, str]], *, db_name: str = "collection.anki2"
) -> Path:
    """Write a minimal .apkg: a SQLite with a `notes(flds)` table, zipped."""
    db = path.with_suffix(".sqlite")
    con = sqlite3.connect(db)
    con.execute("CREATE TABLE notes (id INTEGER PRIMARY KEY, flds TEXT)")
    con.executemany("INSERT INTO notes (flds) VALUES (?)", [(_SEP.join(pair),) for pair in notes])
    con.commit()
    con.close()
    with zipfile.ZipFile(path, "w") as z:
        z.write(db, arcname=db_name)
    db.unlink()
    return path


def test_read_apkg_notes_splits_fields(tmp_path):
    apkg = _make_apkg(tmp_path / "d.apkg", [("le café", "coffee"), ("la voiture", "car")])
    notes = ia.read_apkg_notes(apkg)
    assert notes == [["le café", "coffee"], ["la voiture", "car"]]


def test_read_apkg_v3_gives_clear_error(tmp_path):
    apkg = tmp_path / "v3.apkg"
    with zipfile.ZipFile(apkg, "w") as z:
        z.writestr("collection.anki21b", b"\x28\xb5\x2f\xfd not-sqlite")
    try:
        ia.read_apkg_notes(apkg)
        raise AssertionError("expected ImportError_ for a v3 apkg")
    except ia.ImportError_ as e:
        assert "v3" in str(e).lower() or "legacy" in str(e).lower()


def test_clean_text_strips_html_and_media():
    assert ia.clean_text("le <b>café</b> [sound:c.mp3]&nbsp;noir") == "le café noir"


def test_strip_article_gender_and_elision():
    assert ia.strip_article("le café") == ("café", "m")
    assert ia.strip_article("la voiture") == ("voiture", "f")
    assert ia.strip_article("l'avion") == ("avion", "")  # elided -> gender unresolved
    assert ia.strip_article("chat") == ("chat", "")  # no article


def test_build_candidate_enriches_and_filters():
    c = ia.build_candidate("le vélo", "bike", "voyage", keep_phrases=False)
    assert c["id"] == "velo" and c["fr"] == "vélo" and c["gender"] == "m" and c["pos"] == "noun"
    assert c["tags"] == ["voyage"]

    # gender unresolved -> flagged for review
    a = ia.build_candidate("l'avion", "plane", "voyage", keep_phrases=False)
    assert a["gender"] == "" and "gender?" in a["_review"]

    # a whole sentence is not a vocab card
    assert (
        ia.build_candidate("Je voudrais un café", "I'd like a coffee", "x", keep_phrases=False)
        is None
    )
    # cloze note dropped
    assert ia.build_candidate("le {{c1::chat}}", "the cat", "x", keep_phrases=False) is None
    # empty side dropped
    assert ia.build_candidate("", "nothing", "x", keep_phrases=False) is None


def test_keep_phrases_allows_short_expressions():
    # No leading article, so it stays multi-word: dropped by default, kept with the flag.
    assert ia.build_candidate("carte postale", "postcard", "x", keep_phrases=False) is None
    c = ia.build_candidate("carte postale", "postcard", "x", keep_phrases=True)
    assert c and c["id"] == "carte_postale" and "phrase" in c["_review"]


def test_contraction_not_treated_as_article():
    # "au"/"du" are contractions, not articles — must NOT be stripped (would mangle
    # fixed expressions like "au revoir" into "revoir").
    c = ia.build_candidate("au revoir", "goodbye", "x", keep_phrases=True)
    assert c["fr"] == "au revoir" and c["id"] == "au_revoir"


def test_dedup_drops_existing_ids_and_lemmas():
    cands = [
        ia.build_candidate("le zzblorp", "nonsense-word", "t", keep_phrases=False),
        ia.build_candidate("le café", "coffee", "t", keep_phrases=False),  # id/lemma clash
        ia.build_candidate("le zzblorp", "dup within deck", "t", keep_phrases=False),  # in-deck dup
    ]
    kept, skipped = ia.dedup(cands, {"cafe"}, {"café"})
    assert [k["id"] for k in kept] == ["zzblorp"]
    assert skipped == 2


def test_to_yaml_matches_house_style_and_loads():
    rec = {
        "id": "velo",
        "fr": "vélo",
        "en": "bike",
        "gender": "m",
        "pos": "noun",
        "tags": ["voyage"],
    }
    text = ia.to_yaml([rec], deck="Test Deck", source="http://x", level="a2", tag="voyage")
    assert "tags: [voyage]" in text  # flow style, like the authored files
    assert "REVIEW BEFORE SYNC" in text
    loaded = yaml.safe_load(text)
    assert loaded[0]["id"] == "velo"
    Vocab(**loaded[0])  # emitted row is a valid Vocab


def test_main_end_to_end_writes_valid_reviewable_yaml(tmp_path, capsys):
    # café is really in the bank -> must be deduped out; the nonsense words are new.
    apkg = _make_apkg(
        tmp_path / "deck.apkg",
        [
            ("le café", "coffee"),  # existing -> dropped
            ("le zzblorp", "widget"),  # new
            ("la florgette", "gadget"),  # new, feminine
            ("Ceci est une phrase longue", "a long sentence"),  # sentence -> dropped
        ],
    )
    out = tmp_path / "voyage.yaml"
    rc = ia.main(["--level", "a2", "--tag", "voyage", "--out", str(out), str(apkg), "--deck", "T"])
    assert rc == 0
    rows = yaml.safe_load(out.read_text())
    ids = {r["id"] for r in rows}
    assert ids == {"zzblorp", "florgette"}  # café deduped, sentence dropped
    assert all(r["tags"] == ["voyage"] for r in rows)
    for r in rows:
        Vocab(**r)  # every emitted row validates
    assert {r["id"]: r["gender"] for r in rows} == {"zzblorp": "m", "florgette": "f"}
