"""Personal vocab decks (Slice E): a learner's own cards, separate from the shared
content bank. The SRS engine is unchanged — a personal card rides the exact same FSRS
loop as a content card, because the review-queue `card_key` is an FK-free string.

The one rule that keeps the two banks apart: personal keys are namespaced `uv:<slug>`.
`resolve_queue_vocab` (used by /srs/queue) sends any `uv:`-prefixed key here and
everything else to `ContentVocab`, so the two id spaces can never collide.
"""

from __future__ import annotations

import re
import unicodedata

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.content.enrich import strip_leading_article
from app.content.tables import UserVocab

PERSONAL_PREFIX = "uv:"


class EmptyLemmaError(ValueError):
    """The word has no letters/digits to build a card key from (e.g. "  ", "!!!", "があ").
    Caught at the API edge and returned as a 422 rather than storing a blank card."""


def is_personal_key(card_key: str) -> bool:
    return card_key.startswith(PERSONAL_PREFIX)


def normalize_lemma(fr: str) -> str:
    """The stored `fr` for a personal card: trimmed, with a leading article dropped so a
    direct API add matches what the preview flow (which enriches to a bare lemma) yields.
    Raises EmptyLemmaError if nothing sluggable remains."""
    fr = strip_leading_article(fr.strip())
    if not slugify(fr):
        raise EmptyLemmaError(fr)
    return fr


def slugify(fr: str) -> str:
    """ASCII lowercase id from a French lemma (café -> cafe). Same convention as the
    content ids and scripts/import_anki, so a personal 'chat' and a global 'chat' share
    a slug — the `uv:` prefix is what keeps their card keys distinct."""
    ascii_ = "".join(c for c in unicodedata.normalize("NFD", fr) if unicodedata.category(c) != "Mn")
    return re.sub(r"[^a-z0-9]+", "_", ascii_.lower()).strip("_")


def personal_key(fr: str) -> str:
    # Clamp so `uv:<slug>` always fits the card_key String(64) column regardless of DB
    # backend (SQLite ignores the cap; Postgres would 500 on INSERT). fr is already
    # length-capped at the API, but keep the invariant here where the key is minted.
    slug = slugify(fr)[: 64 - len(PERSONAL_PREFIX)]
    return PERSONAL_PREFIX + slug


def card_payload(v: UserVocab) -> dict:
    """Queue/list shape for a personal card. `level: 'personal'` tags its origin;
    `audio_url` points at the lazy-TTS endpoint (no pre-built clip, so no `audio` key)."""
    return {
        "card_key": v.card_key,
        "fr": v.fr,
        "en": v.en,
        "gender": v.gender,
        "pos": v.pos,
        "ipa": v.ipa,
        "level": "personal",
        "personal": True,
        "source": v.source,
        "audio_url": f"/vocab/personal/audio/{v.card_key}",
    }


async def add_personal(
    session: AsyncSession,
    user_id: int,
    *,
    fr: str,
    en: str,
    gender: str = "",
    pos: str = "",
    ipa: str = "",
    source: str = "manual",
) -> tuple[UserVocab, bool]:
    """Insert a personal card (idempotent per user+slug). Returns (row, created).
    An existing card is returned untouched so re-adding a word never clobbers it or
    resets its review progress. Does NOT seed the SRS card — the caller does that so
    the commit boundary stays with the request handler.

    Raises EmptyLemmaError for input that slugifies to nothing (whitespace / punctuation
    / non-Latin only), so a blank "uv:" card can never be stored or seeded into review."""
    fr = normalize_lemma(fr)
    key = personal_key(fr)
    existing = await session.scalar(
        select(UserVocab).where(UserVocab.user_id == user_id, UserVocab.card_key == key)
    )
    if existing is not None:
        return existing, False
    row = UserVocab(
        user_id=user_id,
        card_key=key,
        fr=fr,
        en=en.strip(),
        gender=gender,
        pos=pos,
        ipa=ipa,
        source=source,
    )
    session.add(row)
    await session.flush()  # assign id without committing
    return row, True


async def list_personal(session: AsyncSession, user_id: int) -> list[UserVocab]:
    rows = await session.execute(
        select(UserVocab).where(UserVocab.user_id == user_id).order_by(UserVocab.created_at.desc())
    )
    return list(rows.scalars().all())


async def get_personal(session: AsyncSession, user_id: int, card_key: str) -> UserVocab | None:
    return await session.scalar(
        select(UserVocab).where(UserVocab.user_id == user_id, UserVocab.card_key == card_key)
    )


async def resolve_queue_vocab(
    session: AsyncSession, user_id: int, card_keys: list[str]
) -> dict[str, dict]:
    """Personal-card metadata for the review queue, keyed by card_key. Only looks up
    the `uv:`-prefixed keys; content keys are resolved by the caller against ContentVocab."""
    keys = [k for k in card_keys if is_personal_key(k)]
    if not keys:
        return {}
    rows = (
        (
            await session.execute(
                select(UserVocab).where(UserVocab.user_id == user_id, UserVocab.card_key.in_(keys))
            )
        )
        .scalars()
        .all()
    )
    return {v.card_key: card_payload(v) for v in rows}
