"""The one place Piper's raw eSpeak phonemes become the IPA a learner sees.

Used wherever IPA is produced or repaired — synthesis (`lookup.voice_with_ipa`), the
read-time heal, and `scripts/backfill_ipa.py` — so they can never disagree.

  1. Display-only overrides for the few common words eSpeak gets wrong (fils, oignon,
     cacahuète). The clip still says what eSpeak voices; only the written IPA is fixed.
     A plain dict keyed by lowercase headword, so a larger table can feed it later.
  2. Otherwise: drop stress marks (French has no lexical stress; eSpeak's final-syllable
     ˈ misleads beginners), collapse whitespace, and cap at the column width on a word
     boundary so a long phrase never ends mid-symbol.
"""

from __future__ import annotations

import re

IPA_MAX = 64  # vocab_lookup.ipa / user_vocab.ipa column width

IPA_OVERRIDES: dict[str, str] = {
    "fils": "fis",
    "oignon": "ɔɲɔ̃",
    "oignons": "ɔɲɔ̃",
    "cacahuète": "kakawɛt",
    "cacahuètes": "kakawɛt",
    # Accentless spellings already cached/stored before headword voicing (QA 891): eSpeak
    # reads "cacahuetes" as kakayət, and the old LLM IPA was English ("peanuts").
    "cacahuete": "kakawɛt",
    "cacahuetes": "kakawɛt",
}

_STRESS = re.compile("[ˈˌ]")


def normalize_ipa(raw: str, fr: str = "") -> str:
    """Learner-facing IPA for `fr` from Piper's `raw` phonemes ("" stays "")."""
    if not raw:
        return ""
    if override := IPA_OVERRIDES.get(fr.strip().lower()):
        return override
    ipa = " ".join(_STRESS.sub("", raw).split())
    if len(ipa) > IPA_MAX:
        head = ipa[: IPA_MAX + 1]  # keep one extra char: a space there means a clean cut
        ipa = head.rsplit(" ", 1)[0] if " " in head else ipa[:IPA_MAX]
    return ipa
