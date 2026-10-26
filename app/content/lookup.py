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

import anyio
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.interfaces import LLMResult
from app.ai.router import AIRouter
from app.content.enrich import GenderTable, enrich
from app.content.personal import normalize_lemma, slugify
from app.content.tables import VocabLookup
from app.storage.interface import ObjectStorage

log = logging.getLogger(__name__)


def lookup_slug(word: str) -> str:
    """Cache key for a word: article-stripped ASCII slug (raises EmptyLemmaError)."""
    return slugify(normalize_lemma(word))[:64]


async def cached_lookup(session: AsyncSession, word: str) -> VocabLookup | None:
    return await session.get(VocabLookup, lookup_slug(word))


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
    row = VocabLookup(
        slug=slug,
        fr=result.fr,
        en=result.en,
        gender=result.gender,
        pos=result.pos,
        gender_source=result.gender_source,
    )
    if tts is not None:
        try:
            wav, ipa = await anyio.to_thread.run_sync(lambda: voice_with_ipa(tts, result.fr, voice))
            key = f"vocablookup/{slug}.wav"
            await anyio.to_thread.run_sync(lambda: storage.put(key, wav, "audio/wav"))
            row.audio_key = key
            row.ipa = ipa[:64]
        except Exception:
            log.warning("lookup audio failed for %r; served lazily instead", word, exc_info=True)
    row = await session.merge(row)  # merge: a concurrent lookup of the same word is fine
    await session.flush()
    return row, llm


def voice_with_ipa(tts, text: str, voice: str) -> tuple[bytes, str]:
    """WAV plus the French IPA the TTS voiced ("" for a backend that can't report it)."""
    if hasattr(tts, "synthesize_ipa"):
        return tts.synthesize_ipa(text=text, voice=voice)
    return tts.synthesize(text=text, voice=voice, lang="fr"), ""


def lookup_payload(row: VocabLookup) -> dict:
    return {
        "fr": row.fr,
        "en": row.en,
        "pos": row.pos,
        "gender": row.gender,
        "ipa": row.ipa,
        "gender_source": row.gender_source,
        "audio_url": f"/vocab/personal/lookup-audio/{row.slug}",
    }
