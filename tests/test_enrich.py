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


def test_resolve_gender_unresolved():
    assert E.resolve_gender("xyzzy", "noun", "", table=None) == ("", "")


# --- JSON parsing -------------------------------------------------------------


def test_parse_enrichment_tolerates_fences_and_bad_pos():
    text = '```json\n{"en": "computer", "pos": "Noun", "gender": "m", "ipa": "/ɔʁdinatœʁ/"}\n```'
    d = E._parse_enrichment(text)
    assert d == {"en": "computer", "pos": "noun", "gender": "m", "ipa": "ɔʁdinatœʁ"}


def test_parse_enrichment_drops_junk():
    d = E._parse_enrichment('{"en": "x", "pos": "gibberish", "gender": "z", "ipa": 5}')
    assert d == {"en": "x", "pos": "", "gender": "", "ipa": ""}
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
    assert result.ipa == "silɑ̃s"
    assert router.calls[0]["profile"] == "vocab_enrich"
    assert llm is not None  # usage returned for billing


def test_enrich_empty_word_makes_no_call():
    router = FakeRouter({"en": "x", "pos": "noun", "gender": "m", "ipa": ""})
    result, llm = _run(E.enrich(router, "   "))
    assert result is None and llm is None
    assert router.calls == []  # no cost for empty input
