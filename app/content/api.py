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
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.auth import get_current_user
from app.content.tables import ContentLesson, ContentUnit, ContentVocab
from app.db.session import get_session
from app.progress.service import completed_lesson_ids
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
    level: str,
    tag: str | None = None,
    session: AsyncSession = Depends(get_session),
    user: User = Depends(get_current_user),
) -> dict:
    """A level's vocabulary as a browsable deck (id/fr/en/audio/pos/tags). Optional
    `tag` narrows to one theme. Free-study companion to the scheduled SRS review."""
    rows = (
        (
            await session.execute(
                select(ContentVocab).where(ContentVocab.level == level).order_by(ContentVocab.id)
            )
        )
        .scalars()
        .all()
    )
    if not rows:
        raise HTTPException(status.HTTP_404_NOT_FOUND, f"no vocab for level {level!r}")
    cards = [r.data for r in rows]
    if tag:
        cards = [c for c in cards if tag in (c.get("tags") or [])]
    return {"level": level, "cards": cards}
