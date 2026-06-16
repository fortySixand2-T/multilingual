"""Sync file-based content into the DB (the write half of AC1.1).

Delete-and-replace per level: a re-sync wipes that level's content rows and
re-inserts from the authored files, so removed lessons/vocab actually disappear.
Safe because learner state references content by string id, not FK (see
`tables.py`) — wiping content rows never touches progress or SRS.

Run it:  ./start.sh content-sync a1     (or  python -m app.content.sync a1)
"""
from __future__ import annotations

import asyncio
import sys
from pathlib import Path as FsPath

from sqlalchemy import delete
from sqlalchemy.ext.asyncio import AsyncSession

from app.content.loader import load_content
from app.content.models import ContentBundle
from app.content.tables import ContentLesson, ContentUnit, ContentVocab

DEFAULT_CONTENT_ROOT = "content"


async def sync_bundle(session: AsyncSession, bundle: ContentBundle) -> None:
    level = bundle.path.level
    for table in (ContentUnit, ContentLesson, ContentVocab):
        await session.execute(delete(table).where(table.level == level))

    for ordinal, unit in enumerate(bundle.path.units):
        session.add(
            ContentUnit(
                id=unit.id,
                level=level,
                ordinal=ordinal,
                title=unit.title,
                icon=unit.icon,
                lessons=list(unit.lessons),
                unlock_type=unit.unlock.type,
                unlock_requires=list(unit.unlock.requires),
            )
        )
    for lesson in bundle.lessons.values():
        session.add(
            ContentLesson(
                id=lesson.id,
                level=level,
                title=lesson.title,
                data=lesson.model_dump(mode="json"),
            )
        )
    for v in bundle.vocab.values():
        session.add(ContentVocab(id=v.id, level=level, data=v.model_dump(mode="json")))

    await session.commit()


async def sync_content(
    session: AsyncSession, content_root: str | FsPath, level: str
) -> ContentBundle:
    bundle = load_content(content_root, level)
    await sync_bundle(session, bundle)
    return bundle


async def _main(level: str, content_root: str) -> None:
    from app.db.session import SessionLocal

    async with SessionLocal() as session:
        bundle = await sync_content(session, content_root, level)
    print(
        f"synced level {level!r}: "
        f"{len(bundle.path.units)} units, {len(bundle.lessons)} lessons, "
        f"{len(bundle.vocab)} vocab"
    )


if __name__ == "__main__":
    _level = sys.argv[1] if len(sys.argv) > 1 else "a1"
    _root = sys.argv[2] if len(sys.argv) > 2 else DEFAULT_CONTENT_ROOT
    asyncio.run(_main(_level, _root))
