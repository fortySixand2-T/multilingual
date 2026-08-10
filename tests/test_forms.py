"""Pure-unit tests for app.content.forms: JSON parsing, the non-inflecting skip,
and the example-history merge. No DB, LLM faked."""

import asyncio
import json

from app.ai.accounting import make_usage
from app.ai.interfaces import LLMResult
from app.content import forms as F


def _run(coro):
    return asyncio.run(coro)


class FakeRouter:
    def __init__(self, payload):
        self.payload = payload
        self.calls = []

    def run(self, profile, *, system, messages, **kw):
        self.calls.append((profile, kw))
        self.last_prompt = messages[-1].content
        return LLMResult(
            text=json.dumps(self.payload),
            provider="ollama",
            model="llama3.1",
            usage=make_usage(input_tokens=10, output_tokens=8),
        )


# --- parsing ------------------------------------------------------------------


def test_parse_forms_tolerates_fences_and_junk():
    body = (
        '{"forms": [{"label": "singular", "fr": "le chat"}, {"bad": 1}, {"label": "", "fr": "x"}]}'
    )
    text = f"```json\n{body}\n```"
    assert F._parse_forms(text) == [{"label": "singular", "fr": "le chat"}]


def test_parse_forms_caps_at_four():
    raw = {"forms": [{"label": f"l{i}", "fr": f"f{i}"} for i in range(9)]}
    assert len(F._parse_forms(json.dumps(raw))) == 4


def test_parse_examples_keeps_fr_requires_it():
    text = '{"examples": [{"fr": "Il mange.", "en": "He eats."}, {"en": "no fr"}, {"fr": "Ok"}]}'
    assert F._parse_examples(text) == [
        {"fr": "Il mange.", "en": "He eats."},
        {"fr": "Ok", "en": ""},
    ]


def test_parse_bad_json_is_empty():
    assert F._parse_forms("not json") == []
    assert F._parse_examples("{oops") == []


# --- generate_forms: the non-inflecting skip ---------------------------------


def test_generate_forms_skips_non_inflecting_pos():
    router = FakeRouter({"forms": [{"label": "x", "fr": "y"}]})
    for pos in ("adverb", "preposition", "phrase", ""):
        out, llm = _run(F.generate_forms(router, "vite", pos, ""))
        assert out == [] and llm is None
    assert router.calls == []  # no LLM call for words that don't inflect


def test_generate_forms_calls_model_for_verb():
    router = FakeRouter({"forms": [{"label": "présent", "fr": "je mange"}]})
    out, llm = _run(F.generate_forms(router, "manger", "verb", ""))
    assert out == [{"label": "présent", "fr": "je mange"}]
    assert llm is not None
    assert router.calls[0][0] == "vocab_forms"


def test_generate_forms_passes_gender_for_noun():
    router = FakeRouter({"forms": []})
    _run(F.generate_forms(router, "le chat", "noun", "m"))
    # article stripped before the model sees it; gender forwarded in the prompt
    assert "chat" in router.last_prompt and "le chat" not in router.last_prompt
    assert "Gender: m" in router.last_prompt


# --- generate_examples: variety knobs ----------------------------------------


def test_generate_examples_uses_high_temperature_and_caps_count():
    router = FakeRouter({"examples": [{"fr": f"S{i}", "en": f"E{i}"} for i in range(5)]})
    out, llm = _run(F.generate_examples(router, "chat", "cat", count=2))
    assert len(out) == 2  # capped at the requested count
    assert router.calls[0][0] == "vocab_examples"
    assert router.calls[0][1]["temperature"] == 0.9  # variety over determinism


def test_generate_examples_empty_word_no_call():
    router = FakeRouter({"examples": []})
    out, llm = _run(F.generate_examples(router, "   ", "cat"))
    assert out == [] and llm is None and router.calls == []


# --- merge_examples: rolling history -----------------------------------------


def test_merge_prepends_dedupes_and_caps():
    history = [{"fr": "A", "en": "a"}, {"fr": "B", "en": "b"}]
    fresh = [{"fr": "C", "en": "c"}, {"fr": "a", "en": "dup-diff-case"}]
    merged = F.merge_examples(history, fresh)
    # fresh is prepended (newest first); the fresh "a" wins the case-insensitive dedupe
    # against the older "A", which is dropped; "B" stays.
    assert [e["fr"] for e in merged] == ["C", "a", "B"]


def test_merge_caps_at_max_history():
    history = [{"fr": f"H{i}", "en": ""} for i in range(F.MAX_EXAMPLE_HISTORY)]
    merged = F.merge_examples(history, [{"fr": "NEW", "en": ""}])
    assert len(merged) == F.MAX_EXAMPLE_HISTORY
    assert merged[0]["fr"] == "NEW"  # newest kept, oldest dropped
