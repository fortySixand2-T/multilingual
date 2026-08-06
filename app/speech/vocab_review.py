"""End-of-conversation vocab review: mine a speaking session's transcript for
French words worth adding to the learner's review deck.

Two decoupled steps so each is testable in isolation:
  1. `extract_review_words` — one lightweight LLM pass over the session's turns
     returns candidate French lemmas (compute; runs the router in a worker thread).
  2. `resolve_to_vocab` — matches those lemmas against the content catalog and the
     learner's existing SRS cards, returning only *new, known* words to suggest.

`resolve_to_vocab` is the "cheap tier" (Slice 3a): lemmas that resolve to an existing
`ContentVocab` id, so every suggested card is a real, audio-backed vocab entry.
`resolve_new_words` is the "rich tier" (Slice 3c): the leftover lemmas — words the
learner used that aren't in the bank and aren't already personal cards — surfaced for
one-click enrich-and-add into their own deck (Slice D dictionary + Slice E user_vocab).
"""

from __future__ import annotations

import functools
import json
import unicodedata

import anyio
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.interfaces import LLMResult, Msg
from app.content.personal import personal_key
from app.content.tables import ContentVocab, UserVocab
from app.speech.tables import SpeechTurn
from app.srs.models import ReviewCard

_PROFILE = "vocab_extract"
_MAX_WORDS = 10  # keep the debrief short; a long list is decision fatigue

_EXTRACT_SYSTEM = (
    "You review a French learner's speaking-practice transcript and select a SHORT "
    "list of French vocabulary words worth adding to their review deck: words they "
    "used incorrectly, reached for and got wrong, or that the examiner introduced "
    "and that are useful everyday vocabulary. Use dictionary form (infinitive verbs, "
    "singular nouns WITHOUT article). Skip proper nouns, function words (articles, "
    "pronouns, prepositions), and trivial words a learner already knows. "
    f'Reply with STRICT JSON only, no prose: {{"words": ["mot", ...]}}, at most '
    f"{_MAX_WORDS} words."
)


def _transcript_blob(turns: list[SpeechTurn]) -> str:
    lines: list[str] = []
    for t in turns:
        if t.transcript:
            lines.append(f"[learner] {t.transcript}")
        if t.reply_text:
            lines.append(f"[examiner] {t.reply_text}")
    return "\n".join(lines)


def _parse_words(text: str) -> list[str]:
    """Pull the word list out of the model's JSON reply, tolerantly."""
    s = text.strip()
    if s.startswith("```"):  # strip ```json ... ``` fences some models add
        s = s.strip("`")
        s = s[4:] if s[:4].lower() == "json" else s
    try:
        data = json.loads(s)
    except (ValueError, TypeError):
        return []
    words = data.get("words") if isinstance(data, dict) else data
    if not isinstance(words, list):
        return []
    out: list[str] = []
    for w in words:
        if isinstance(w, str) and w.strip():
            out.append(w.strip())
    return out[:_MAX_WORDS]


async def extract_review_words(
    router, turns: list[SpeechTurn], *, max_tokens: int = 256
) -> tuple[list[str], LLMResult | None]:
    """Run the extraction pass. Returns (lemmas, llm_result) — the result is passed
    back so the caller can bill usage. Empty session → no call, no cost."""
    blob = _transcript_blob(turns)
    if not blob.strip():
        return [], None
    messages = [Msg("user", f"Transcript of the exchange:\n{blob}")]
    result = await anyio.to_thread.run_sync(
        functools.partial(
            router.run, _PROFILE, system=_EXTRACT_SYSTEM, messages=messages, max_tokens=max_tokens
        )
    )
    return _parse_words(result.text), result


def _norm(word: str) -> str:
    """Normalize for matching: lowercase, strip a leading article, trim punctuation."""
    w = word.strip().lower()
    for art in (
        "de la ",
        "de l'",
        "l'",
        "d'",
        "le ",
        "la ",
        "les ",
        "un ",
        "une ",
        "des ",
        "du ",
        "au ",
        "aux ",
    ):
        if w.startswith(art):
            w = w[len(art) :]
            break
    return w.strip(" .,;:!?\"'()")


def _deaccent(word: str) -> str:
    return "".join(c for c in unicodedata.normalize("NFD", word) if unicodedata.category(c) != "Mn")


async def resolve_to_vocab(
    session: AsyncSession, user_id: int, words: list[str], *, limit: int = 12
) -> list[dict]:
    """Match lemmas to existing vocab ids, dropping words the learner already has in
    review. Returns [{card_key, fr, en, level}], deduped, capped at `limit`."""
    if not words:
        return []

    rows = (await session.execute(select(ContentVocab))).scalars().all()
    # Two lookups: exact-normalized, and accent-insensitive as a fallback (the model
    # may drop accents). Exact wins when both match.
    exact: dict[str, ContentVocab] = {}
    loose: dict[str, ContentVocab] = {}
    for r in rows:
        fr = r.data.get("fr", "")
        if not fr:
            continue
        n = _norm(fr)
        exact.setdefault(n, r)
        loose.setdefault(_deaccent(n), r)

    already = set(
        (
            await session.execute(select(ReviewCard.card_key).where(ReviewCard.user_id == user_id))
        ).scalars()
    )

    picked: list[dict] = []
    seen: set[str] = set()
    for w in words:
        n = _norm(w)
        row = exact.get(n) or loose.get(_deaccent(n))
        if row is None or row.id in seen or row.id in already:
            continue
        seen.add(row.id)
        picked.append(
            {
                "card_key": row.id,
                "fr": row.data.get("fr"),
                "en": row.data.get("en"),
                "level": row.level,
            }
        )
        if len(picked) >= limit:
            break
    return picked


async def find_content_match(session: AsyncSession, word: str) -> ContentVocab | None:
    """Look up `word` against the shared content bank using the same normalized/
    deaccented matching `resolve_new_words` uses. Lets other entry points (e.g.
    POST /vocab/personal/from-word, called directly rather than via the Speaking
    debrief) reject a word that already has a real ContentVocab entry instead of
    silently minting a duplicate `uv:` personal card for it."""
    n = _deaccent(_norm(word))
    if not n:
        return None
    rows = (await session.execute(select(ContentVocab))).scalars().all()
    for r in rows:
        fr = r.data.get("fr", "")
        if fr and _deaccent(_norm(fr)) == n:
            return r
    return None


async def resolve_new_words(
    session: AsyncSession, user_id: int, words: list[str], *, limit: int = 6
) -> list[str]:
    """The "rich tier" (Slice 3c): extracted lemmas that DON'T map to a content card and
    aren't already in the learner's personal deck. These are the words worth enriching
    (Slice D) into a personal card (Slice E) — returned as bare lemmas for the client to
    add one-click via POST /vocab/personal/from-word. Deduped, capped at `limit`."""
    if not words:
        return []

    rows = (await session.execute(select(ContentVocab))).scalars().all()
    content = {_deaccent(_norm(r.data.get("fr", ""))) for r in rows if r.data.get("fr")}
    owned = set(
        (
            await session.execute(select(UserVocab.card_key).where(UserVocab.user_id == user_id))
        ).scalars()
    )

    out: list[str] = []
    seen: set[str] = set()
    for w in words:
        n = _norm(w)
        if not n or _deaccent(n) in content:
            continue  # empty, or the cheap tier already offers it as a content card
        key = personal_key(n)
        if key == "uv:" or key in owned or key in seen:
            continue  # degenerate slug, already owned, or a dup within this batch
        seen.add(key)
        out.append(n)
        if len(out) >= limit:
            break
    return out
