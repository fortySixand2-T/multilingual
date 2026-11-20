"""Present-tense tables for the verb decks (app/content/conjugation.py)."""

from __future__ import annotations

from pathlib import Path

import pytest

from app.content.conjugation import group, present
from app.content.loader import load_level_vocab

CONTENT = Path(__file__).resolve().parents[1] / "content"


def test_every_subject_pronoun_gets_its_form():
    assert present("aller") == [
        ("je", "vais"),
        ("tu", "vas"),
        ("il / elle / on", "va"),
        ("nous", "allons"),
        ("vous", "allez"),
        ("ils / elles", "vont"),
    ]


def test_je_elides_before_a_vowel_or_mute_h():
    assert present("acheter")[0] == ("j'", "achète")
    assert present("habiter")[0] == ("j'", "habite")
    assert present("haïr")[0] == ("je", "hais")  # h aspiré


def test_pronominal_verbs_and_phrases_keep_their_parts():
    assert present("se lever")[2] == ("il / elle / on", "se lève")
    assert present("s'asseoir")[0] == ("je", "m'assieds")  # the usual series, not assois
    assert present("se rendre compte")[3] == ("nous", "nous rendons compte")
    assert present("faire face à")[4] == ("vous", "faites face à")
    assert present("falloir") == [("il", "faut")]
    assert present("valoir mieux") == [("il", "vaut mieux")]


def test_one_spelling_series_per_table():
    assert [v for _, v in present("harceler")][:2] == ["harcèle", "harcèles"]


def test_regular_means_the_er_and_issons_patterns():
    for word in ("parler", "acheter", "manger", "se lever", "finir", "choisir"):
        assert group(word) == "regular", word
    for word in ("aller", "être", "partir", "prendre", "faire face à", "s'asseoir"):
        assert group(word) == "irregular", word
    assert group("zorglubber") == ""


@pytest.mark.parametrize("level", ["a1", "a2", "b1", "b2"])
def test_every_course_verb_has_a_table(level):
    verbs = [v.fr for v in load_level_vocab(CONTENT, level).values() if v.pos == "verb"]
    assert verbs and [v for v in verbs if not present(v)] == []
