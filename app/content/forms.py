"""Word forms + usage examples for a vocab card (vocab forms slice).

Two model-backed lookups that expand a bare card (fr/en/pos/gender) into study
material, built to sit next to `enrich.py`:

  1. `generate_forms` — the word's *morphological forms*, shaped by part of speech
     (noun -> singular/plural; verb -> a few key conjugations; adjective -> m/f/pl).
     A word's forms are stable, so this runs on the cached `vocab_forms` profile and
     the caller persists the result once (`user_vocab.forms`).
  2. `generate_examples` — fresh example *sentences* that use the word. These are
     meant to vary every time the learner asks for more, so they run on the
     uncached `vocab_examples` profile at a higher temperature, and the caller passes
     the recently-shown sentences as `avoid` to nudge the model off repeats.

Both return plain dict/list payloads (JSON-serialisable) plus the raw `LLMResult`
so the API layer can bill the `vocab` daily budget exactly like enrichment does.
Empty/unknown input -> no LLM call, no cost.
"""

from __future__ import annotations

import functools
import json

import anyio

from app.ai.interfaces import LLMResult, Msg
from app.content.enrich import strip_leading_article

_FORMS_PROFILE = "vocab_forms"
_EXAMPLES_PROFILE = "vocab_examples"

# Parts of speech that actually inflect. Adverbs, prepositions, conjunctions and
# fixed phrases have no useful form table, so we skip the model call for them.
_INFLECTING_POS = {"noun", "verb", "adjective"}

MAX_EXAMPLE_HISTORY = 6  # how many past sentences a card keeps (newest first)


# --- forms --------------------------------------------------------------------

_FORMS_SYSTEM = (
    "You are a French grammar reference. Given a French headword and its part of "
    "speech, return its key inflected forms as STRICT JSON only, no prose:\n"
    '{"forms": [{"label": "...", "fr": "..."}]}\n'
    "Each `label` is a short English tag for the form; each `fr` is the French form.\n"
    "Follow the part of speech:\n"
    "- noun: two entries — {label:'singular', fr:'<article> <word>'} and "
    "{label:'plural', fr:'<article> <plural>'}, using the correct definite article "
    "(le/la/l'/les) for the given gender.\n"
    "- verb (give the infinitive's conjugation, 1st person singular 'je' unless the "
    "verb is impersonal): four entries labelled 'présent', 'passé composé', 'futur', "
    "'imparfait'.\n"
    "- adjective: four entries labelled 'masculine', 'feminine', 'masculine plural', "
    "'feminine plural'.\n"
    "Return between 2 and 4 entries. Keep each `fr` to just the form (plus its article "
    "or subject pronoun where asked). No explanations."
)


def _parse_forms(text: str) -> list[dict]:
    """Pull the `forms` list out of the model reply, tolerantly (fences, junk keys)."""
    data = _loads_lenient(text)
    if not isinstance(data, dict):
        return []
    raw = data.get("forms")
    if not isinstance(raw, list):
        return []
    out: list[dict] = []
    for item in raw:
        if not isinstance(item, dict):
            continue
        label = item.get("label")
        fr = item.get("fr")
        if isinstance(label, str) and isinstance(fr, str) and label.strip() and fr.strip():
            out.append({"label": label.strip(), "fr": fr.strip()})
    return out[:4]


async def generate_forms(
    router, fr: str, pos: str, gender: str, *, max_tokens: int = 160
) -> tuple[list[dict], LLMResult | None]:
    """Morphological forms for a word, as [{label, fr}]. Only nouns/verbs/adjectives
    inflect — anything else returns ([], None) with no LLM call. Runs the router in a
    worker thread (it's sync) exactly like enrich.propose."""
    lemma = strip_leading_article(fr)
    if not lemma or pos not in _INFLECTING_POS:
        return [], None
    prompt = f"Headword: {lemma}\nPart of speech: {pos}"
    if pos == "noun" and gender in ("m", "f", "mf"):
        prompt += f"\nGender: {gender}"
    result = await anyio.to_thread.run_sync(
        functools.partial(
            router.run,
            _FORMS_PROFILE,
            system=_FORMS_SYSTEM,
            messages=[Msg("user", prompt)],
            max_tokens=max_tokens,
        )
    )
    return _parse_forms(result.text), result


# --- examples -----------------------------------------------------------------

_EXAMPLES_SYSTEM = (
    "You are a French tutor writing example sentences for a learner (CEFR A2–B1). "
    "Given a French word and its English gloss, return short natural example "
    "sentences that USE the word, as STRICT JSON only, no prose:\n"
    '{"examples": [{"fr": "...", "en": "..."}]}\n'
    "Each `fr` is one French sentence (8–14 words, everyday register) that clearly "
    "uses the given word; each `en` is a faithful English translation. Vary the "
    "sentences you produce — different subjects, tenses and situations. If the user "
    "lists sentences to avoid, do NOT repeat or lightly reword them."
)


def _parse_examples(text: str) -> list[dict]:
    """Pull the `examples` list out of the model reply, tolerantly."""
    data = _loads_lenient(text)
    if not isinstance(data, dict):
        return []
    raw = data.get("examples")
    if not isinstance(raw, list):
        return []
    out: list[dict] = []
    for item in raw:
        if not isinstance(item, dict):
            continue
        fr = item.get("fr")
        en = item.get("en")
        if isinstance(fr, str) and fr.strip():
            out.append({"fr": fr.strip(), "en": en.strip() if isinstance(en, str) else ""})
    return out


async def generate_examples(
    router,
    fr: str,
    en: str,
    *,
    avoid: list[str] | None = None,
    count: int = 2,
    max_tokens: int = 220,
) -> tuple[list[dict], LLMResult | None]:
    """Fresh example sentences using the word, as [{fr, en}]. Uncached and at a higher
    temperature so repeated presses give new sentences; `avoid` (recently-shown French
    sentences) is fed to the model to push it off repeats. Empty word -> ([], None)."""
    lemma = strip_leading_article(fr)
    if not lemma:
        return [], None
    n = max(1, min(count, 3))
    prompt = f"Word: {lemma}"
    if en.strip():
        prompt += f"\nMeaning: {en.strip()}"
    prompt += f"\nWrite {n} new example sentence{'s' if n > 1 else ''}."
    if avoid:
        joined = "\n".join(f"- {s}" for s in avoid[:MAX_EXAMPLE_HISTORY] if s.strip())
        if joined:
            prompt += f"\nAvoid these already-seen sentences:\n{joined}"
    result = await anyio.to_thread.run_sync(
        functools.partial(
            router.run,
            _EXAMPLES_PROFILE,
            system=_EXAMPLES_SYSTEM,
            messages=[Msg("user", prompt)],
            temperature=0.9,  # variety over determinism — new sentences each press
            max_tokens=max_tokens,
        )
    )
    return _parse_examples(result.text)[:n], result


def merge_examples(history: list[dict] | None, fresh: list[dict]) -> list[dict]:
    """Prepend freshly-generated sentences to the card's history (newest first),
    dropping duplicates by French text and capping at MAX_EXAMPLE_HISTORY."""
    out: list[dict] = []
    seen: set[str] = set()
    for item in [*fresh, *(history or [])]:
        fr = (item.get("fr") or "").strip()
        if not fr or fr.lower() in seen:
            continue
        seen.add(fr.lower())
        out.append({"fr": fr, "en": (item.get("en") or "").strip()})
        if len(out) >= MAX_EXAMPLE_HISTORY:
            break
    return out


# --- shared -------------------------------------------------------------------


def _loads_lenient(text: str):
    """json.loads tolerant of ```json fences and surrounding junk (shared with enrich)."""
    s = text.strip()
    if s.startswith("```"):
        s = s.strip("`")
        s = s[4:] if s[:4].lower() == "json" else s
    try:
        return json.loads(s)
    except (ValueError, TypeError):
        return None
