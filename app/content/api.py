"""Content delivery API: the path (with gating) and individual lessons.

Gating is *derived*, not stored: `compute_unit_status` is a pure function of the
units and the set of completed lesson ids. The per-user completed set will come
from the `progress` module (not built yet) — `_completed_lesson_ids` is the seam,
and currently returns empty, so the first unit is `available` and gated units are
`locked`. That's the real gating logic running against a real (empty) progress
state, not a stub of the response.
"""

from __future__ import annotations

import re
from collections.abc import Iterable

import anyio
from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.auth import get_current_user
from app.content.tables import ContentLesson, ContentUnit, ContentVocab, KnownVocab
from app.db.session import get_session
from app.progress.service import completed_lesson_ids
from app.srs.models import ReviewCard
from app.storage.interface import ObjectStorage
from app.users.models import User

router = APIRouter(prefix="/content", tags=["content"])

# Audio storage keys are content-controlled (`<level>/audio/<file>.mp3`). Validate the
# shape before hitting storage — LocalFileStorage joins the key onto a base path with no
# traversal guard, so an unchecked key could escape the asset dir.
_AUDIO_KEY = re.compile(r"^[a-z0-9]+/audio/[A-Za-z0-9._-]+\.mp3$")


def get_storage(request: Request) -> ObjectStorage:
    return request.app.state.storage


def _unlock_ok(unit: ContentUnit, complete_units: set[str], completed_lessons: set[str]) -> bool:
    if unit.unlock_type == "none":
        return True
    # all_of: every required unit/lesson id must be complete
    return all(req in complete_units or req in completed_lessons for req in unit.unlock_requires)


def compute_unit_status(
    units: Iterable[ContentUnit], completed_lessons: set[str]
) -> dict[str, str]:
    """Map unit id -> 'complete' | 'available' | 'locked'."""
    units = list(units)
    complete_units = {u.id for u in units if u.lessons and set(u.lessons) <= completed_lessons}
    out: dict[str, str] = {}
    for u in units:
        if u.id in complete_units:
            out[u.id] = "complete"
        elif _unlock_ok(u, complete_units, completed_lessons):
            out[u.id] = "available"
        else:
            out[u.id] = "locked"
    return out


async def is_lesson_unlocked(session: AsyncSession, user_id: int, lesson: ContentLesson) -> bool:
    """True unless the lesson sits in a unit the user hasn't unlocked yet.

    Reuses the same `compute_unit_status` gating the path renders, so the write side
    and the read side can never disagree. A lesson not owned by any unit is ungated.
    """
    units = (
        (await session.execute(select(ContentUnit).where(ContentUnit.level == lesson.level)))
        .scalars()
        .all()
    )
    owning = next((u for u in units if lesson.id in (u.lessons or [])), None)
    if owning is None:
        return True
    completed = await completed_lesson_ids(session, user_id)
    return compute_unit_status(units, completed)[owning.id] != "locked"


@router.get("/levels")
async def get_levels(
    session: AsyncSession = Depends(get_session),
    user: User = Depends(get_current_user),
) -> dict:
    """Levels that actually have a learning path, ordered low→high. Drives the UI
    level switcher so it only offers shipped levels (b1 appears once synced)."""
    rows = (await session.execute(select(ContentUnit.level).distinct())).scalars().all()
    order = {lvl: i for i, lvl in enumerate(["a1", "a2", "b1", "b2", "c1", "c2"])}
    levels = sorted(rows, key=lambda lvl: order.get(lvl, len(order)))
    return {"levels": levels}


@router.get("/path")
async def get_path(
    level: str,
    session: AsyncSession = Depends(get_session),
    user: User = Depends(get_current_user),
) -> dict:
    result = await session.execute(
        select(ContentUnit).where(ContentUnit.level == level).order_by(ContentUnit.ordinal)
    )
    units = result.scalars().all()
    if not units:
        raise HTTPException(status.HTTP_404_NOT_FOUND, f"no content for level {level!r}")

    completed = await completed_lesson_ids(session, user.id)
    status_by_unit = compute_unit_status(units, completed)
    return {
        "level": level,
        "units": [
            {
                "id": u.id,
                "title": u.title,
                "icon": u.icon,
                "lessons": u.lessons,
                "unlock": {"type": u.unlock_type, "requires": u.unlock_requires},
                "status": status_by_unit[u.id],
            }
            for u in units
        ],
    }


@router.get("/grammar")
async def get_grammar(
    level: str,
    session: AsyncSession = Depends(get_session),
    user: User = Depends(get_current_user),
) -> dict:
    """Every grammar point taught across a level's lessons, in path order (unit →
    lesson) — a browsable reference/review companion to the lessons themselves.
    Lessons without a `grammar_point` are omitted."""
    units = (
        (
            await session.execute(
                select(ContentUnit).where(ContentUnit.level == level).order_by(ContentUnit.ordinal)
            )
        )
        .scalars()
        .all()
    )
    if not units:
        raise HTTPException(status.HTTP_404_NOT_FOUND, f"no content for level {level!r}")

    lessons = (
        (await session.execute(select(ContentLesson).where(ContentLesson.level == level)))
        .scalars()
        .all()
    )
    by_id = {les.id: les for les in lessons}

    items = []
    for unit in units:
        for lid in unit.lessons:
            lesson = by_id.get(lid)
            if lesson is None:
                continue
            grammar_point = (lesson.data.get("grammar_point") or "").strip()
            if not grammar_point:
                continue
            items.append(
                {
                    "unit_id": unit.id,
                    "unit_title": unit.title,
                    "lesson_id": lid,
                    "lesson_title": lesson.title,
                    "grammar_point": grammar_point,
                    # grammatical family (one of GRAMMAR_CATEGORIES); the reference groups
                    # and filters by this. Older content without the field reads as "".
                    "grammar_category": (lesson.data.get("grammar_category") or "").strip(),
                }
            )
    return {"level": level, "items": items}


@router.get("/lessons/{lesson_id}")
async def get_lesson(
    lesson_id: str,
    session: AsyncSession = Depends(get_session),
    user: User = Depends(get_current_user),
) -> dict:
    lesson = await session.get(ContentLesson, lesson_id)
    if lesson is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, f"lesson {lesson_id!r} not found")
    return lesson.data


@router.get("/audio/{key:path}")
async def get_audio(
    key: str,
    storage: ObjectStorage = Depends(get_storage),
    user: User = Depends(get_current_user),
) -> Response:
    """Serve an audio asset (vocab `audio` / lesson `listen_type` `audio_ref`) by its
    storage key. Mirrors the comprehension audio route; auth-gated and shape-checked."""
    if not _AUDIO_KEY.match(key):
        raise HTTPException(status.HTTP_404_NOT_FOUND, "no such audio asset")
    try:
        # storage is sync (local-FS / boto3) — keep it off the event loop
        data = await anyio.to_thread.run_sync(lambda: storage.get(key))
    except Exception:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "audio asset not found") from None
    return Response(content=data, media_type="audio/mpeg")


@router.get("/vocab")
async def get_vocab(
    level: str | None = None,
    tag: str | None = None,
    session: AsyncSession = Depends(get_session),
    user: User = Depends(get_current_user),
) -> dict:
    """Vocabulary as browsable decks (id/fr/en/audio/pos/tags, each tagged with its
    `level`). Omit `level` to get every level at once; `tag` narrows to one theme.
    Free-study companion to the scheduled SRS review."""
    query = select(ContentVocab).order_by(ContentVocab.level, ContentVocab.id)
    if level:
        query = query.where(ContentVocab.level == level)
    rows = (await session.execute(query)).scalars().all()
    if level and not rows:
        raise HTTPException(status.HTTP_404_NOT_FOUND, f"no vocab for level {level!r}")
    known = set(
        (await session.execute(select(KnownVocab.card_key).where(KnownVocab.user_id == user.id)))
        .scalars()
        .all()
    )
    in_review = set(
        (await session.execute(select(ReviewCard.card_key).where(ReviewCard.user_id == user.id)))
        .scalars()
        .all()
    )
    cards = []
    for r in rows:
        card = {**r.data, "level": r.level}
        # every word has a pronunciation clip, keyed by convention `<level>/audio/<id>.mp3`
        # (matches scripts/gen_audio.py); served by the /content/audio route.
        if not card.get("audio"):
            card["audio"] = f"{r.level}/audio/{card['id']}.mp3"
        card["known"] = card["id"] in known
        card["in_review"] = card["id"] in in_review
        cards.append(card)
    if tag:
        cards = [c for c in cards if tag in (c.get("tags") or [])]
    return {"cards": cards}


class KnownBody(BaseModel):
    card_key: str
    known: bool


@router.post("/vocab/known")
async def set_known(
    body: KnownBody,
    session: AsyncSession = Depends(get_session),
    user: User = Depends(get_current_user),
) -> dict:
    """Mark a vocab card known (insert) or reset it (delete). Idempotent."""
    existing = (
        await session.execute(
            select(KnownVocab).where(
                KnownVocab.user_id == user.id, KnownVocab.card_key == body.card_key
            )
        )
    ).scalar_one_or_none()
    if body.known and existing is None:
        session.add(KnownVocab(user_id=user.id, card_key=body.card_key))
    elif not body.known and existing is not None:
        await session.delete(existing)
    await session.commit()
    return {"card_key": body.card_key, "known": body.known}
