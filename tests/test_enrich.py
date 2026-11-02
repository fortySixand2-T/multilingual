"""Dictionary enrichment engine (app/content/enrich.py) — suffix rules, gender table,
the deterministic backstop's precedence, JSON parsing, and the async orchestration.

The LLM is faked (a canned JSON reply) so the test is deterministic and offline.
"""

from __future__ import annotations

import asyncio
import json

from app.ai.accounting import make_usage
from app.ai.interfaces import LLMResult
from app.content import enrich as E


class FakeRouter:
    """Returns a fixed JSON dictionary entry; records the profile it was asked for."""

    def __init__(self, payload: dict):
        self.payload = payload
        self.calls: list[dict] = []

    def run(self, profile, *, system, messages, **kw):
        self.calls.append({"profile": profile, "messages": messages})
        return LLMResult(
            text=json.dumps(self.payload),
            provider="ollama",
            model="llama3.1",
            usage=make_usage(input_tokens=12, output_tokens=8),
        )


# --- pure helpers -------------------------------------------------------------


def test_strip_leading_article():
    assert E.strip_leading_article("le vélo") == "vélo"
    assert E.strip_leading_article("une voiture") == "voiture"
    assert E.strip_leading_article("l'eau") == "eau"
    assert E.strip_leading_article("de la crème") == "crème"
    assert E.strip_leading_article("chat") == "chat"  # no article
    # phone keyboards type U+2019 (QA 1020)
    assert E.strip_leading_article("l\u2019eau") == "eau"
    assert E.strip_leading_article("L\u2019été") == "été"


def test_suffix_gender_high_confidence_endings():
    assert E.suffix_gender("information") == "f"  # -tion
    assert E.suffix_gender("qualité") == "f"  # -té
    assert E.suffix_gender("gouvernement") == "m"  # -ment
    assert E.suffix_gender("bureau") == "m"  # -eau
    assert E.suffix_gender("voyage") == "m"  # -age
    assert E.suffix_gender("chat") == ""  # no reliable ending


def test_suffix_gender_exceptions():
    # feminine -age / -eau words must NOT be called masculine by the rule
    assert E.suffix_gender("plage") == "f"
    assert E.suffix_gender("image") == "f"
    assert E.suffix_gender("eau") == "f"
    assert E.suffix_gender("peau") == "f"


def test_gender_table_loads_seed_and_looks_up():
    t = E.GenderTable.load()  # bundled seed table
    assert len(t) > 0
    assert t.get("ordinateur") == "m"
    assert t.get("voiture") == "f"
    assert t.get("enfant") == "mf"
    assert t.get("nonexistent-word") == ""


def test_gender_table_has_full_lexique_coverage():
    # The bundled table is the full Lexique383 extract, not just the seed set.
    t = E.GenderTable.load()
    assert len(t) > 40000
    # Animate m/f pairs share a Lexique lemma but must keep their own gender.
    assert t.get("chien") == "m" and t.get("chienne") == "f"
    assert t.get("acteur") == "m" and t.get("actrice") == "f"
    # Robust to Lexique's blank-headword quirk (genre only on the plural row).
    assert t.get("voiture") == "f" and t.get("main") == "f"
    # Curated overrides win: true epicene, and a noun blank throughout Lexique.
    assert t.get("élève") == "mf"
    assert t.get("livre") == "m"


def test_gender_table_loads_custom_file(tmp_path):
    p = tmp_path / "g.tsv"
    p.write_text("# comment\nfoo\tf\nbar\tm\nbad\tx\n\n", encoding="utf-8")
    t = E.GenderTable.load(p)
    assert t.get("foo") == "f" and t.get("bar") == "m"
    assert t.get("bad") == ""  # invalid gender ignored


# --- the precedence backstop --------------------------------------------------


def test_resolve_gender_table_beats_suffix_and_llm():
    # "silence" ends in -ence (suffix would say 'f') but is masculine; the table wins.
    t = E.GenderTable.load()
    assert t.get("silence") == "m"
    g, src = E.resolve_gender("silence", "noun", "f", table=t)
    assert (g, src) == ("m", "table")


def test_resolve_gender_suffix_beats_llm_when_not_in_table():
    t = E.GenderTable.load()
    # a made-up -tion word not in the table: suffix rule (f) must beat a wrong llm 'm'
    g, src = E.resolve_gender("blorgation", "noun", "m", table=t)
    assert (g, src) == ("f", "suffix")


def test_resolve_gender_falls_back_to_llm():
    g, src = E.resolve_gender("bidule", "noun", "m", table=None)
    assert (g, src) == ("m", "llm")


def test_resolve_gender_none_for_non_nouns():
    # verbs/adjectives/adverbs have no grammatical gender, even if they end -tion-ish
    assert E.resolve_gender("manger", "verb", "m") == ("", "")
    assert E.resolve_gender("rapidement", "adverb", "f") == ("", "")


def test_phrase_has_no_gender():
    # QA 1050: "...ce soir" must not pick up the -oir masculine suffix
    phrase = "je voudrais réserver une table pour quatre personnes ce soir"
    assert E.resolve_gender(phrase, "", "m", table=E.GenderTable.load()) == ("", "")
    assert E.resolve_gender(phrase, "noun", "m") == ("", "")


def test_llm_gender_needs_a_noun():
    # QA 893: "à" came back with no pos and a guessed gender m; only a noun has one.
    assert E.resolve_gender("à", "", "m", table=None) == ("", "")


def test_pos_variants_map_onto_the_known_values():
    assert E._pos("adj") == "adjective"
    assert E._pos("Adverb (time)") == "adverb"
    assert E._pos("prep.") == "preposition"
    assert E._pos("conjunction") == "conjunction" and E._pos("Pronoun") == "pronoun"  # QA 1003
    assert E._pos("") == "" and E._pos("interjection") == ""


def test_resolve_gender_unresolved():
    assert E.resolve_gender("xyzzy", "noun", "", table=None) == ("", "")


# --- JSON parsing -------------------------------------------------------------


def test_parse_enrichment_tolerates_fences_and_bad_pos():
    text = '```json\n{"en": "computer", "pos": "Noun", "gender": "m", "ipa": "/ɔʁdinatœʁ/"}\n```'
    d = E._parse_enrichment(text)
    assert d == {"fr": "", "en": "computer", "pos": "noun", "gender": "m"}  # IPA comes from Piper


def test_parse_enrichment_drops_junk():
    d = E._parse_enrichment('{"en": "x", "pos": "gibberish", "gender": "z", "ipa": 5}')
    assert d == {"fr": "", "en": "x", "pos": "", "gender": ""}
    assert E._parse_enrichment("not json") == {}


# --- async orchestration ------------------------------------------------------


def _run(coro):
    return asyncio.run(coro)


def test_enrich_overrides_model_gender_with_table():
    # model wrongly says feminine; table says silence is masculine -> table wins
    router = FakeRouter({"en": "silence", "pos": "noun", "gender": "f", "ipa": "silɑ̃s"})
    t = E.GenderTable.load()
    result, llm = _run(E.enrich(router, "le silence", table=t))
    assert result.fr == "silence"  # article stripped
    assert result.en == "silence"
    assert result.pos == "noun"
    assert (result.gender, result.gender_source) == ("m", "table")
    assert router.calls[0]["profile"] == "vocab_enrich"
    assert llm is not None  # usage returned for billing


def test_enrich_empty_word_makes_no_call():
    router = FakeRouter({"en": "x", "pos": "noun", "gender": "m", "ipa": ""})
    result, llm = _run(E.enrich(router, "   "))
    assert result is None and llm is None
    assert router.calls == []  # no cost for empty input


def test_inflected_adjective_and_preposition_are_not_nouns():
    """QA 1000: the model calls grandes / pendant nouns; Lexique knows better, and a
    non-noun gets no gender from the table."""
    t = E.GenderTable.load()
    cases = (("grandes", "adjective"), ("petits", "adjective"), ("pendant", "preposition"))
    for word, pos in cases:
        router = FakeRouter({"en": "x", "pos": "noun", "gender": "f"})
        result, _ = _run(E.enrich(router, word, table=t))
        assert (result.pos, result.gender) == (pos, ""), word
    # été / personne stay nouns: a learner means summer / person
    for word in ("été", "personne"):
        result, _ = _run(E.enrich(FakeRouter({"en": "x", "pos": "noun"}), word, table=t))
        assert result.pos == "noun" and result.gender, word


def test_typed_article_keeps_the_noun_and_bare_words_still_flip():
    """QA 1065 (+1064/1066): le pas / le son / la mure stay nouns; bare grandes still flips."""
    t = E.GenderTable.load()
    for word, gender in (("le pas", "m"), ("le son", "m"), ("la mure", "f")):
        router = FakeRouter({"en": "x", "pos": "noun", "gender": gender})
        result, _ = _run(E.enrich(router, word, table=t))
        assert (result.pos, result.gender) == ("noun", gender), word
    result, _ = _run(E.enrich(FakeRouter({"en": "x", "pos": "noun"}), "pas", table=t))
    assert result.pos == "adverb"


def test_lexique_pos_fixes_adjective_prepositions():
    """QA 1085: derrière is a preposition; a true adjective stays one."""
    from app.content import lexicon

    assert lexicon.pos("derrière", "adjective") == "preposition"
    assert lexicon.pos("grand", "adjective") == "adjective"


def test_respell_keeps_du_des_and_still_fixes_accents():
    """QA 1060 (+1061/1100): du / des are not misspellings of dû / dès; 1002 still holds."""
    from app.content.lexicon import respell

    assert (respell("du"), respell("des"), respell("Du")) == ("du", "des", "Du")
    assert respell("cote") == "côté" and respell("chausseé") == "chaussée"


def test_gender_resolves_on_the_kept_headword():
    """QA 1004: typed "elephant", kept "éléphant" -> the table's m, not unresolved."""
    router = FakeRouter({"fr": "éléphant", "en": "elephant", "pos": "noun"})
    result, _ = _run(
        E.enrich(router, "elephant", table=E.GenderTable.load(), headword=lambda t, p: p)
    )
    assert (result.fr, result.gender, result.gender_source) == ("éléphant", "m", "table")


def test_model_gender_words_are_normalised():
    assert E._parse_enrichment('{"en": "x", "gender": "Masculine"}')["gender"] == "m"
    assert E._parse_enrichment('{"en": "x", "gender": "f."}')["gender"] == "f"


def test_clean_gloss_makes_notes_consistent():
    """QA 1001: the model's inflection notes, grammar labels, regional asides and
    dangling articles go; the adjective form note comes from Lexique."""
    cases = [
        ("large (f pl)", "", "large"),
        ("small (feminine plural)", "f. pl.", "small (f. pl.)"),
        ("active (adj)", "", "active"),
        ("French (adj/noun)", "", "French"),
        ("pavement (m)", "", "pavement"),
        ("eggs (pl.)", "", "eggs"),
        ("ground floor (Brit. English: ground floor)", "", "ground floor"),
        ("at the", "", "at"),
        ("vitamin A", "", "vitamin A"),  # QA 1080: a capital A is content
        ("Plan A", "", "Plan A"),
        ("speak (they)", "", "speak (they)"),  # other notes are left alone
    ]
    for en, note, want in cases:
        assert E.clean_gloss(en, note) == want, en


def test_clean_gloss_separates_and_dedupes_senses():
    """QA 1084: senses run together or split by | come out comma-separated, once each."""
    assert E.clean_gloss("book|pound") == "book, pound"
    assert E.clean_gloss("holidays,vacation") == "holidays, vacation"
    assert E.clean_gloss("speak (they), speak") == "speak (they)"


def test_senses_list_is_joined():
    """The prompt asks for `en` as a list of senses (QA 1083/1084)."""
    entry = E._parse_enrichment('{"en": ["news", "tidings"], "pos": "noun"}')
    assert entry["en"] == "news, tidings"


def test_adjective_form_note_comes_from_lexique():
    """QA 1001: grandes gets (f. pl.) whatever the model wrote; a noun gets none."""
    t = E.GenderTable.load()
    for word, en, want in (
        ("grandes", "large (f)", "large (f. pl.)"),
        ("rouges", "red", "red (pl.)"),
    ):
        result, _ = _run(E.enrich(FakeRouter({"en": en, "pos": "adjective"}), word, table=t))
        assert result.en == want, word
    result, _ = _run(
        E.enrich(FakeRouter({"en": "news (pl.)", "pos": "noun"}), "nouvelles", table=t)
    )
    assert (result.pos, result.en, result.gender) == ("noun", "news", "f")


def test_lexique_prepositions_win_over_other_model_pos():
    """chez came back as an adverb; Lexique says preposition."""
    from app.content import lexicon

    assert lexicon.pos("chez", "adverb") == "preposition"
    assert lexicon.pos("devant", "verb") == "verb"  # a verb reading is never overruled


def test_respell_writes_the_oe_ligature():
    """QA 1082: boeuf -> bœuf like œil, cœur; coefficient / moelle keep their oe."""
    from app.content.lexicon import respell

    got = [respell(w) for w in ("boeuf", "voeu", "coeur", "Oeuvre", "chef-d'oeuvre")]
    assert got == ["bœuf", "vœu", "cœur", "Œuvre", "chef-d'œuvre"]
    assert (respell("coefficient"), respell("moelle")) == ("coefficient", "moelle")
