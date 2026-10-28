"""Content-bank IPA builder (scripts/build_vocab_ipa.py) — Lexique mapping, homograph
choice, phrase cross-check, and the source each card's IPA is taken from."""

from __future__ import annotations

from scripts import build_vocab_ipa as bv

LEX = {
    "fils": [("fil", "NOM", 5.0), ("fis", "NOM", 90.0)],
    "est": [("ɛ", "AUX", 900.0), ("ɛst", "NOM", 20.0)],
    "paquet": [("pakɛ", "NOM", 30.0)],
    "coeur": [("kœʁ", "NOM", 200.0)],
    "ami": [("ami", "NOM", 80.0)],
    "tourisme": [("tuʁizm", "NOM", 40.0)],
    "un": [("œ̃", "ART:ind", 999.0)],
}


def test_lexique_code_maps_to_ipa():
    assert "S2R@§".translate(bv._LEXIQUE) == "ʃøʁɑ̃ɔ̃"


def test_homograph_picks_part_of_speech_then_frequency():
    assert bv.lexique_word(LEX, "fils", "noun") == "fis"
    assert bv.lexique_word(LEX, "est", "noun") == "ɛst"  # the compass point, not the verb
    assert bv.lexique_word(LEX, "est") == "ɛ"
    assert bv.lexique_word(LEX, "cœur") == "kœʁ"  # Lexique spells the ligature out
    assert bv.lexique_word(LEX, "inconnu") is None


def test_isme_is_written_the_dictionary_way():
    assert bv.lexique_word(LEX, "tourisme") == "tuʁism"


def test_phrase_join_attaches_elided_clitic():
    assert bv.lexique_phrase(LEX, "l'ami") == "lami"
    assert bv.lexique_phrase(LEX, "un ami") == "œ̃ ami"
    assert bv.lexique_phrase(LEX, "un inconnu") is None


def test_loose_ignores_accepted_variation():
    assert bv._loose("pakɛ") == bv._loose("pakˈeː")
    assert bv._loose("ʃəval") == bv._loose("ʃval")
    assert bv._loose("fis") != bv._loose("fil")


def test_resolve_prefers_lexique_for_words_and_piper_for_liaison():
    piper = {"fils": "fˈil", "un ami": "œ̃nami", "l'ami": "lami"}
    assert bv.resolve(LEX, piper, "fils", "noun")[:2] == ("fis", "lexique")
    assert bv.resolve(LEX, piper, "un ami", "phrase")[:2] == ("œ̃nami", "piper")
    assert bv.resolve(LEX, piper, "l'ami", "phrase")[:2] == ("lami", "lexique")


def test_reviewed_answer_wins(monkeypatch):
    monkeypatch.setitem(bv.REVIEWED, "fils", "fis")
    assert bv.resolve(LEX, {}, "fils", "noun")[:2] == ("fis", "reviewed")
