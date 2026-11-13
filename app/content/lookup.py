"""Durable, shared word lookups for My deck (the `vocab_lookup` table).

A lookup's result — meaning, gender, IPA and a pronunciation clip — is the same for
every learner, so it's computed once and kept: the first lookup of a word pays one Piper
run (audio + IPA) and, for a word the dictionary lacks, one LLM call (meaning/pos/gender);
every later lookup, by anyone and across restarts, is a single DB read. IPA comes from
Piper's own eSpeak phonemes, never the LLM, which often guessed English IPA ("vélo" ->
/ˈbiːsɪkl/, "horrible" -> /hɒrəbəl/). Without a TTS backend a word has no IPA until its clip is
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
from app.content import dictionary, lexicon
from app.content.enrich import GenderTable, enrich, gloss
from app.content.ipa import normalize_ipa
from app.content.lexicon import respell
from app.content.personal import clamp_slug, normalize_lemma, slugify
from app.content.tables import UserVocab, VocabLookup
from app.storage.interface import ObjectStorage

log = logging.getLogger(__name__)


_PIPES = re.compile(r"\s*\|\s*")
_LIGATURES = str.maketrans({"œ": "oe", "Œ": "oe", "æ": "ae", "Æ": "ae"})


def fold_slug(word: str) -> str:
    """Accent-free article-stripped ASCII slug (raises EmptyLemmaError): the key every
    spelling of a word shares. Ligatures spell out first (œil -> oeil) so they can't
    fold into another word (il)."""
    return clamp_slug(slugify(normalize_lemma(word).translate(_LIGATURES)), 64)


def is_word(text: str) -> bool:
    """True for a spelling the dictionary or Lexique knows."""
    return dictionary.entry(text) is not None or lexicon.known(text)


def _own_word(typed: str) -> bool:
    """True when `typed` is a word French spells just so, not a slip for an accented one
    (ou, du: yes; eleve for élève: no)."""
    low = typed.lower()
    return is_word(low) and respell(low) == low


def lookup_slug(word: str) -> str:
    """Cache key for a word: its fold slug, except an accented spelling that is a word
    of its own beside an accent-free one (où / ou, dû / du) gets a key of its own, so
    neither overwrites the other for every learner (QA 1175)."""
    slug = fold_slug(word)
    typed = normalize_lemma(word).lower()
    if accent_count(typed) and is_word(typed) and is_word(lexicon.fold(typed)):
        return clamp_slug(f"{slug}_{typed.encode().hex()}", 64)
    return slug


def accent_count(text: str) -> int:
    return sum(unicodedata.category(c) == "Mn" for c in unicodedata.normalize("NFD", text))


async def cached_lookup(session: AsyncSession, word: str) -> VocabLookup | None:
    """The shared row for `word`, unless it holds another spelling of it than the one
    typed: a worse-accented one (row "ete", typed "été": QA 890), or any other when the
    typed spelling is a word itself (row "où", typed "ou": QA 1175). Then it's a miss and
    the lookup re-runs."""
    row = await session.get(VocabLookup, lookup_slug(word))
    if row is None:
        return None
    typed = normalize_lemma(word)
    if accent_count(typed) > accent_count(row.fr) or (
        typed.lower() != row.fr.lower() and _own_word(typed)
    ):
        return None
    return row


async def stored_lookup(session: AsyncSession, fr: str) -> VocabLookup | None:
    """The shared row holding the headword `fr`, found under its own key or, when it was
    looked up accent-free ("cote" -> côté), under the fold slug."""
    for slug in (lookup_slug(fr), fold_slug(fr)):
        row = await session.get(VocabLookup, slug)
        if row is not None and row.fr == fr:
            return row
    return None


def _headword(typed: str, proposed: str) -> str:
    """The model's accented spelling of `typed`, only if it is the same word (same slug)
    with no accent lost; anything else falls back to what was typed (QA 891). When the
    learner typed no accents, the model's are checked against Lexique (QA 1002)."""
    if not accent_count(typed):
        proposed = respell(proposed or typed)
    if not proposed or len(proposed) > 128:
        return typed
    try:
        same = fold_slug(proposed) == fold_slug(typed)
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
    when the model gave no meaning, and nothing is cached so a retry can succeed. With
    no `router`, only a word the dictionary has gets a row."""
    result, llm = await enrich(router, word, table=table, headword=_headword)
    if result is None or not result.en:
        return None, llm
    slug = lookup_slug(word)
    fr = result.fr
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


async def heal_gloss(session: AsyncSession, row: VocabLookup) -> None:
    """Give a row cached before the dictionary its meaning (pêche: "fruit" -> "peach,
    fishing", QA 1101), and commit if it changed. Same part of speech only: a row
    looked up as "la personne" must not turn into the pronoun."""
    found = dictionary.entry(row.fr, pos=row.pos)
    en = gloss(row.fr, row.pos, found["en"]) if found else ""
    if en and en != row.en:
        row.en = en
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
