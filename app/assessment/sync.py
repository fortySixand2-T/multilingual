"""Sync writing tasks into the DB (delete-and-replace per level)."""

from __future__ import annotations

import asyncio
import sys
from pathlib import Path

from sqlalchemy import delete
from sqlalchemy.ext.asyncio import AsyncSession

from app.assessment.loader import load_tasks
from app.assessment.tables import WritingTaskRow

DEFAULT_CONTENT_ROOT = "content"


async def sync_tasks(session: AsyncSession, content_root: str | Path, level: str) -> int:
    tasks = load_tasks(content_root, level)
    await session.execute(delete(WritingTaskRow).where(WritingTaskRow.level == level))
    for t in tasks.values():
        session.add(
            WritingTaskRow(id=t.id, level=level, section=t.section, data=t.model_dump(mode="json"))
        )
    await session.commit()
    return len(tasks)


async def _main(level: str, content_root: str) -> None:
    from app.db.session import SessionLocal

    async with SessionLocal() as session:
        n = await sync_tasks(session, content_root, level)
    print(f"synced level {level!r}: {n} writing tasks")


if __name__ == "__main__":
    _level = sys.argv[1] if len(sys.argv) > 1 else "a1"
    _root = sys.argv[2] if len(sys.argv) > 2 else DEFAULT_CONTENT_ROOT
    asyncio.run(_main(_level, _root))
