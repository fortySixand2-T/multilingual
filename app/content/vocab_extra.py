"""Per-user study extras (word forms + usage examples) for ANY vocab card.

The generation logic lives in `forms.py`; this module is the storage + card-resolution
layer that makes those work for both banks behind one set of endpoints:

  - `resolve_card_meta` turns a `card_key` into the fr/en/pos/gender the generators
    need, routing `uv:`-prefixed keys to the personal `user_vocab` table and everything
    else to the shared `content_vocab` catalog. Returns None for an unknown card.
  - `get_extra` / `_row` read-or-create the single `vocab_extra` row per (user, card).

Keeping the two banks behind one resolver is what lets `/vocab/forms` and
`/vocab/examples` serve a personal card and a content card with identical code.
"""

from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.content.personal import is_personal_key
from app.content.tables import ContentVocab, UserVocab, VocabExtra


@dataclass(frozen=True)
class CardMeta:
    """The fields the form/example generators need, resolved from either bank."""

    fr: str
    en: str
    pos: str
    gender: str


async def resolve_card_meta(session: AsyncSession, user_id: int, card_key: str) -> CardMeta | None:
    """fr/en/pos/gender for a card, or None if it exists in neither bank. Personal
    cards are scoped to the user; content cards are shared (id lookup)."""
    if is_personal_key(card_key):
        v = await session.scalar(
            select(UserVocab).where(UserVocab.user_id == user_id, UserVocab.card_key == card_key)
        )
        if v is None:
            return None
        return CardMeta(fr=v.fr, en=v.en, pos=v.pos, gender=v.gender)

    cv = await session.get(ContentVocab, card_key)
    if cv is None:
        return None
    d = cv.data or {}
    return CardMeta(
        fr=d.get("fr", ""),
        en=d.get("en", ""),
        pos=d.get("pos", ""),
        gender=d.get("gender", ""),
    )


async def get_extra(session: AsyncSession, user_id: int, card_key: str) -> VocabExtra | None:
    """The stored extras row for (user, card), or None if nothing's been generated yet."""
    return await session.scalar(
        select(VocabExtra).where(VocabExtra.user_id == user_id, VocabExtra.card_key == card_key)
    )


async def get_or_create_extra(session: AsyncSession, user_id: int, card_key: str) -> VocabExtra:
    """The extras row for (user, card), inserting an empty one (forms/examples = None)
    if it doesn't exist yet. Flushes so the row is usable in the same transaction;
    the caller owns the commit."""
    row = await get_extra(session, user_id, card_key)
    if row is None:
        row = VocabExtra(user_id=user_id, card_key=card_key)
        session.add(row)
        await session.flush()
    return row
