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
import re

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
    "{label:'plural', fr:'les <plural>'}, using the correct definite article "
    "(le/la/l') for the given gender.\n"
    "- verb (give the infinitive's conjugation, 1st person singular 'je' unless the "
    "verb is impersonal): four entries labelled 'présent', 'passé composé', 'futur', "
    "'imparfait', each with its subject pronoun (e.g. 'j'ai mangé').\n"
    "- adjective: two entries labelled 'masculine' and 'feminine', each the bare "
    "singular adjective with NO article, e.g. heureux / heureuse.\n"
    "Keep each `fr` to just the form (plus its article or subject pronoun where "
    "asked). No explanations."
)

# The small local model slips on agreement and elision ("un intéressante",
# "ce ébouriffant", "je aime"), so whatever a rule can decide is decided here
# rather than by the model: the adjective's masculine form and plurals, and l'/j'.
_DETERMINERS = ("le ", "la ", "les ", "l'", "un ", "une ", "des ", "ce ", "cet ", "cette ", "ces ")
_AL_PLURAL_S = {"banal", "bancal", "fatal", "final", "natal", "naval", "glacial", "idéal"}
# Invariable adjectives (mostly colors/borrowed words): never take a feminine -e or a
# plural -s, in any of the four slots (QA 851). "un pull marron", "une veste marron",
# "des yeux marron", "des vestes marron".
_INVARIABLE_ADJECTIVES = {"marron", "chic", "sympa", "super", "orange", "kaki", "turquoise"}


def _bare(fr: str) -> str:
    """Drop any determiner the model put in front of an adjective."""
    low = fr.lower()
    for d in _DETERMINERS:
        if low.startswith(d):
            return fr[len(d) :].strip()
    return fr


def _adjective_plural(w: str, *, feminine: bool) -> str:
    if w.endswith(("s", "x")):
        return w
    if not feminine and w.endswith("eau"):
        return w + "x"
    if not feminine and w.endswith("al") and w.lower() not in _AL_PLURAL_S:
        return w[:-2] + "aux"
    return w + "s"


def _adjective_forms(forms: list[dict], lemma: str) -> list[dict]:
    """The headword is the masculine singular; the model only supplies the feminine."""
    if lemma.lower() in _INVARIABLE_ADJECTIVES:
        return [
            {"label": "masculine", "fr": lemma},
            {"label": "feminine", "fr": lemma},
            {"label": "masculine plural", "fr": lemma},
            {"label": "feminine plural", "fr": lemma},
        ]
    by_label = {f["label"].lower(): _bare(f["fr"]) for f in forms}
    fem = by_label.get("feminine") or lemma
    masc = lemma
    if fem == lemma and by_label.get("masculine"):  # headword was given in the feminine
        masc = by_label["masculine"]
    return [
        {"label": "masculine", "fr": masc},
        {"label": "feminine", "fr": fem},
        {"label": "masculine plural", "fr": _adjective_plural(masc, feminine=False)},
        {"label": "feminine plural", "fr": _adjective_plural(fem, feminine=True)},
    ]


_ELIDABLE = re.compile(r"\b(je|me|te|se|le|la) (?=[aeiouyàâäéèêëîïôöûüœ])", re.IGNORECASE)
_ELIDABLE_H = re.compile(r"\b(je|me|te|se) (?=h)", re.IGNORECASE)
# Common verbs with h aspiré, which don't elide (je hais, je me hâte).
_H_ASPIRE_VERBS = ("haïr", "hacher", "hanter", "harceler", "hâter", "hausser", "heurter")
_SUBJECT = re.compile(r"(je |j'|tu |il |elle |on |nous |vous |ils |elles )", re.IGNORECASE)
# Impersonal verbs only ever take "il" as subject — never "je" (QA 850).
_IMPERSONAL_VERBS = ("pleuvoir", "neiger", "falloir", "geler", "s'agir", "grêler", "tonner")
# Reflexive verbs whose passé composé needs être + an agreeing reflexive clitic, not the
# model's frequent "j'ai <participe>" default (QA 853).
_PASSE_COMPOSE = "passé composé"
_ETRE_PRESENT = {
    "je": "suis",
    "j'": "suis",
    "tu": "es",
    "il": "est",
    "elle": "est",
    "on": "est",
    "nous": "sommes",
    "vous": "êtes",
    "ils": "sont",
    "elles": "sont",
}


def _elide(fr: str, *, before_h: bool = False) -> str:
    """'le arbre' -> "l'arbre", 'je aime' -> "j'aime". A noun's h is left to the model
    (l'homme but le héros); a verb's h elides unless the verb is h aspiré."""
    fr = _ELIDABLE.sub(lambda m: m.group(1)[0] + "'", fr)
    return _ELIDABLE_H.sub(lambda m: m.group(1)[0] + "'", fr) if before_h else fr


def _is_reflexive(lemma: str) -> bool:
    return lemma.startswith(("se ", "s'"))


def _reflexive_passe_compose(fr: str, lemma: str) -> str:
    """Rewrite a reflexive verb's passé composé to être + agreeing clitic + participle.
    The small model's frequent reply drops the clitic and defaults to avoir
    ("j'ai levé" instead of "je me suis levé") — 100% rule-decidable, so fixed here
    rather than trusted from the model."""
    m = re.match(r"(je|j'|tu|il|elle|on|nous|vous|ils|elles)\b\s*", fr, re.IGNORECASE)
    subject = m.group(1).lower() if m else "je"
    rest = fr[m.end() :] if m else fr
    # Strip a leading "ai"/"a"/"as"/"avons"/"avez"/"ont" (any avoir form the model used)
    # and any reflexive clitic already present, leaving just the past participle.
    rest = re.sub(r"^(?:ai|as|a|avons|avez|ont)\b\s*", "", rest, flags=re.IGNORECASE)
    rest = re.sub(r"^(?:me|m'|te|t'|se|s'|nous|vous)\b\s*", "", rest, flags=re.IGNORECASE)
    participle = rest.strip()
    clitic = {
        "je": "me",
        "j'": "me",
        "tu": "te",
        "il": "se",
        "elle": "se",
        "on": "se",
        "nous": "nous",
        "vous": "vous",
        "ils": "se",
        "elles": "se",
    }[subject]
    etre = _ETRE_PRESENT[subject]
    subject_word = "je" if subject == "j'" else subject
    out = f"{subject_word} {clitic} {etre} {participle}"
    return _elide(out)


def _verb_form(fr: str, lemma: str, label: str = "") -> str:
    is_impersonal = lemma.lower().startswith(_IMPERSONAL_VERBS)
    if not is_impersonal and _is_reflexive(lemma) and label.lower() == _PASSE_COMPOSE:
        fr = _reflexive_passe_compose(fr, lemma)
    elif not _SUBJECT.match(fr) and not _is_reflexive(lemma) and not is_impersonal:
        fr = "je " + fr  # the model often drops the pronoun: 'ai mangé'
    fr = _restore_complement(fr, lemma)
    return _elide(fr, before_h=not lemma.lower().startswith(_H_ASPIRE_VERBS))


def _restore_complement(fr: str, lemma: str) -> str:
    """A multi-word "avoir X" headword ("avoir faim", "avoir besoin de") is a fixed
    idiom whose complement the small model often drops, collapsing to bare "avoir"
    conjugations (QA 852). Re-append the complement when missing — but only check
    whether the reply already contains it (not a blind substring-absence check), so a
    reply that already has a *partial* complement ("j'ai besoin" for "avoir besoin de")
    isn't given a duplicated tail ("j'ai besoin besoin de").
    Scoped to "avoir X" idioms only — a reflexive lemma's second word is the verb
    itself ("se laver"), not a fixed complement, so it must not go through this path."""
    head, _, complement = lemma.partition(" ")
    if not complement or head.lower() != "avoir":
        return fr
    low = fr.lower().rstrip()
    comp_low = complement.lower()
    if low.endswith(comp_low) or comp_low in low:
        return fr
    # Guard against a partial-complement overlap: if the reply already ends with a
    # leading prefix of the complement's first word, don't append the whole thing.
    first_word = comp_low.split(" ", 1)[0]
    if low.endswith(first_word):
        return fr
    return f"{fr} {complement}"


def _noun_form(fr: str) -> str:
    head, _, rest = fr.partition(" ")
    definite = {"un": "le", "une": "la", "des": "les"}.get(head.lower())
    return _elide(f"{definite} {rest}" if definite and rest else fr)


def tidy_forms(forms: list[dict], fr: str, pos: str) -> list[dict]:
    """Rule-fix a forms list. Also applied on read, so forms stored before these rules
    existed are served corrected without rewriting the row."""
    lemma = strip_leading_article(fr)
    forms = [{"label": f["label"], "fr": f["fr"].replace("’", "'")} for f in forms]
    # Qwen occasionally lapses into Chinese mid-form ("j'吃"); Latin script ends < U+0250.
    forms = [f for f in forms if all(ord(c) < 0x250 for c in f["fr"])]
    if pos == "adjective":
        return _adjective_forms(forms, lemma) if forms else []
    if pos == "verb":
        return [{"label": f["label"], "fr": _verb_form(f["fr"], lemma, f["label"])} for f in forms]
    return [{"label": f["label"], "fr": _noun_form(f["fr"])} for f in forms]


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
            temperature=0.0,  # reference data: most-likely form, not variety
            max_tokens=max_tokens,
        )
    )
    return tidy_forms(_parse_forms(result.text), lemma, pos), result


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
