"""The Wiktionary meaning table (app/content/dictionary.py) and the rules that build it
(scripts/build_gloss_table.py)."""

from __future__ import annotations

from app.content import dictionary
from scripts.build_gloss_table import gloss, translations


def test_two_meaning_words_get_both():
    """QA 1101: the model said pêche was "fruit"."""
    assert dictionary.entry("pêche")["en"].startswith("peach, fishing")
    assert dictionary.entry("livre")["en"].startswith("book, pound")


def test_usual_part_of_speech_is_picked_unless_asked():
    assert dictionary.entry("pendant")["pos"] == "preposition"
    assert dictionary.entry("pendant", pos="noun")["pos"] == "noun"
    assert dictionary.entry("pendant", pos="conjunction") is None
    assert dictionary.entry("Été")["en"] == "summer"  # the verb reading is only a form


def test_unknown_word_is_not_in_the_dictionary():
    assert dictionary.entry("zorglub") is None


def test_translations_keep_short_meanings_and_drop_definitions():
    assert translations("a computer, a computing device.") == ["computer", "computing device"]
    assert translations("great (i.e. important, outstanding)") == ["great"]
    assert translations("liberty, freedom. 1688") == ["liberty", "freedom"]
    assert translations("good as opposed to evil") == []
    assert translations("The most common adverb of negation, typically not, don't") == []
    assert translations("coach, or privately hired") == ["coach"]


def test_gloss_takes_each_entrys_first_sense_first_without_repeats():
    peach = [["peach"], ["form", "energy"]]
    fishing = [["fishing", "angling"]]
    assert gloss([peach, fishing]) == "peach, fishing, angling"
    assert gloss([[["to remove", "take off"], ["to take off"]]]) == "to remove, take off"
    assert gloss([[["law (legal code)"], ["law (scientific principle)"]]]) == "law (legal code)"


def test_accentless_word_is_ambiguous_only_between_dictionary_words():
    assert dictionary.ambiguous("peche")  # pêche, péché
    assert not dictionary.ambiguous("pêche")  # typed as a word
    assert not dictionary.ambiguous("maison")
