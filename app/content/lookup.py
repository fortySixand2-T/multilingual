"""Durable, shared word lookups for My deck (the `vocab_lookup` table).

A lookup's result — meaning, gender, IPA and a pronunciation clip — is the same for
every learner, so it's computed once and kept: the first lookup of a word pays one LLM
call (meaning/pos/gender) plus one Piper run (audio + IPA); every later lookup, by
anyone and across restarts, is a single DB read. IPA comes from Piper's own eSpeak
phonemes, never the LLM, which often guessed English IPA ("vélo" -> /ˈbiːsɪkl/,
"horrible" -> /hɒrəbəl/). Without a TTS backend a word has no IPA until its clip is
first voiced (personal_api._serve_audio fills it in then).
"""

from __future__ import annotations

import logging
import re
import unicodedata

import anyio
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.interfaces import LLMResult
from app.ai.router import AIRouter
from app.content.enrich import GenderTable, enrich
from app.content.ipa import normalize_ipa
from app.content.personal import clamp_slug, normalize_lemma, slugify
from app.content.tables import UserVocab, VocabLookup
from app.storage.interface import ObjectStorage

log = logging.getLogger(__name__)


_PIPES = re.compile(r"\s*\|\s*")
_LIGATURES = str.maketrans({"œ": "oe", "Œ": "oe", "æ": "ae", "Æ": "ae"})


def lookup_slug(word: str) -> str:
    """Cache key for a word: article-stripped ASCII slug (raises EmptyLemmaError).
    Ligatures spell out first (œil -> oeil) so they can't fold into another word (il)."""
    return clamp_slug(slugify(normalize_lemma(word).translate(_LIGATURES)), 64)


def accent_count(text: str) -> int:
    return sum(unicodedata.category(c) == "Mn" for c in unicodedata.normalize("NFD", text))


async def cached_lookup(session: AsyncSession, word: str) -> VocabLookup | None:
    """The shared row for `word`, unless it holds a worse-accented spelling than the one
    typed (row "ete", typed "été"): then it's a miss and the lookup re-runs (QA 890)."""
    row = await session.get(VocabLookup, lookup_slug(word))
    if row is not None and accent_count(normalize_lemma(word)) > accent_count(row.fr):
        return None
    return row


def _headword(typed: str, proposed: str) -> str:
    """The model's accented spelling of `typed`, only if it is the same word (same slug)
    with no accent lost; anything else falls back to what was typed (QA 891)."""
    if not proposed or len(proposed) > 128:
        return typed
    try:
        same = lookup_slug(proposed) == lookup_slug(typed)
    except ValueError:  # EmptyLemmaError
        return typed
    proposed = normalize_lemma(proposed)
    return proposed if same and accent_count(proposed) >= accent_count(typed) else typed


async def fresh_lookup(
    session: AsyncSession,
    router: AIRouter,
    tts,
    storage: ObjectStorage,
    word: str,
    *,
    voice: str = "",
    table: GenderTable | None = None,
) -> tuple[VocabLookup | None, LLMResult | None]:
    """Enrich `word`, voice it, and store the result. Returns (row, llm) — row is None
    when the model gave no meaning, and nothing is cached so a retry can succeed."""
    result, llm = await enrich(router, word, table=table)
    if result is None or not result.en:
        return None, llm
    slug = lookup_slug(word)
    fr = _headword(result.fr, result.headword)
    row = VocabLookup(
        slug=slug,
        fr=fr,
        en=result.en,
        gender=result.gender,
        pos=result.pos,
        gender_source=result.gender_source,
        ipa="",  # explicit: a re-lookup (QA 890) must not keep the old spelling's IPA/clip
        audio_key=None,
    )
    if tts is not None:
        try:
            wav, ipa = await anyio.to_thread.run_sync(lambda: voice_with_ipa(tts, fr, voice))
            key = f"vocablookup/{slug}.wav"
            await anyio.to_thread.run_sync(lambda: storage.put(key, wav, "audio/wav"))
            row.audio_key = key
            row.ipa = ipa
        except Exception:
            log.warning("lookup audio failed for %r; served lazily instead", word, exc_info=True)
    row = await session.merge(row)  # merge: a concurrent lookup of the same word is fine
    await session.flush()
    return row, llm


def voice_with_ipa(tts, text: str, voice: str) -> tuple[bytes, str]:
    """WAV plus the learner-facing French IPA the TTS voiced ("" for a backend that
    can't report it)."""
    if hasattr(tts, "synthesize_ipa"):
        wav, ipa = tts.synthesize_ipa(text=text, voice=voice)
        return wav, normalize_ipa(ipa, text)
    return tts.synthesize(text=text, voice=voice, lang="fr"), ""


async def heal_ipa(session: AsyncSession, tts, row: VocabLookup | UserVocab, voice: str) -> None:
    """Re-derive `row.ipa` from the TTS and commit if it changed. For rows that have a
    clip but a stale or empty IPA (pre-#121 LLM guesses, a cold first run). Best effort:
    a TTS hiccup must never block serving the word."""
    if not hasattr(tts, "synthesize_ipa"):
        return
    try:
        _, ipa = await anyio.to_thread.run_sync(lambda: voice_with_ipa(tts, row.fr, voice))
    except Exception:
        log.warning("ipa heal failed for %r", row.fr, exc_info=True)
        return
    if ipa and ipa != row.ipa:
        row.ipa = ipa
        await session.commit()


def lookup_payload(row: VocabLookup) -> dict:
    return {
        "fr": row.fr,
        "en": _PIPES.sub(", ", row.en),  # the model's "a|b" alternatives, readable (QA 884)
        "pos": row.pos,
        "gender": row.gender,
        "ipa": row.ipa,
        "gender_source": row.gender_source,
        "audio_url": f"/vocab/personal/lookup-audio/{row.slug}",
    }
