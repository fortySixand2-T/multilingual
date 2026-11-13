"""The Wiktionary meaning table (app/content/dictionary.py) and the rules that build it
(scripts/build_gloss_table.py)."""

from __future__ import annotations

from app.content import dictionary
from app.content import enrich as E
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


def test_a_long_leading_definition_is_cut_where_it_describes():
    """QA 1146: marteau was "rapper, door knocker": its first sense is a definition."""
    assert translations("a hammer used for pounding", describing=True) == ["hammer"]
    assert translations("a hammer used for pounding") == []  # only a noun's leading sense
    assert translations("a person who runs errands", describing=True) == []  # too generic


def test_a_sense_under_a_header_is_the_line_below_it():
    """QA 1144: nous is "the plural personal pronoun …:" then "we"."""
    from scripts.build_gloss_table import _header_child

    assert _header_child(["the plural personal pronoun in the first person:", "we"]) == "we"
    assert _header_child(["a hammer", "a tool"]) == "a hammer"


def test_everyday_meanings_lead_for_common_words():
    """QA 1144 / 1146 / 1162: the table gives the meaning and part of speech a learner
    means for the most frequent words."""
    for word, pos, en in (
        ("nous", "pronoun", "we, us"),
        ("son", "adjective", "his, her"),
        ("leur", "pronoun", "their"),
        ("pas", "adverb", "not"),
        ("chez", "preposition", "at the home of"),
        ("sinon", "conjunction", "otherwise"),
        ("sujet", "noun", "subject"),
        ("plan", "noun", "plan"),
        ("truc", "noun", "thing"),
        ("marteau", "noun", "hammer"),
        ("file", "noun", "line"),
        ("moyen", "adjective", "middle"),
        ("bête", "adjective", "stupid"),
        ("vide", "adjective", "empty"),
    ):
        got = dictionary.entry(word)
        assert (got["pos"], got["en"].split(", ")[0]) == (pos, en.split(", ")[0]), word
        assert got["en"].startswith(en), word


def test_known_good_rows_do_not_regress():
    for word, en in (
        ("pendant", "during, throughout"),
        ("bien", "well"),
        ("car", "as, since"),
        ("désolé", "desolate"),
        ("falloir", "to need"),
    ):
        assert dictionary.entry(word)["en"].startswith(en), word


def test_gender_follows_the_common_sense():
    """QA 1163: le vase (not the silt, f) and la physique."""
    table = E.GenderTable.load()
    assert (table.get("vase"), table.get("physique")) == ("m", "f")


async def _enrich(word):
    return (await E.enrich(None, word))[0]


def test_pos_stays_the_dictionarys_when_the_gloss_is_for_it():
    """QA 1161: pas was an adverb glossed "step, pace, strait" (the noun's meaning)."""
    import asyncio

    pas = asyncio.run(_enrich("pas"))
    assert (pas.pos, pas.en) == ("adverb", "not")
    assert asyncio.run(_enrich("le pas")).pos == "noun"
    assert asyncio.run(_enrich("son")).pos == "adjective"
