"""Sync exam blueprints into the DB (delete-and-replace per level)."""
from __future__ import annotations

import asyncio
import sys
from pathlib import Path

from sqlalchemy import delete
from sqlalchemy.ext.asyncio import AsyncSession

from app.exam.loader import load_blueprints
from app.exam.tables import ExamBlueprintRow

DEFAULT_CONTENT_ROOT = "content"


async def sync_blueprints(session: AsyncSession, content_root: str | Path, level: str) -> int:
    bps = load_blueprints(content_root, level)
    await session.execute(delete(ExamBlueprintRow).where(ExamBlueprintRow.level == level))
    for bp in bps.values():
        session.add(ExamBlueprintRow(id=bp.id, level=level, data=bp.model_dump(mode="json")))
    await session.commit()
    return len(bps)


async def _main(level: str, content_root: str) -> None:
    from app.db.session import SessionLocal

    async with SessionLocal() as session:
        n = await sync_blueprints(session, content_root, level)
    print(f"synced level {level!r}: {n} exam blueprints")


if __name__ == "__main__":
    _level = sys.argv[1] if len(sys.argv) > 1 else "a1"
    _root = sys.argv[2] if len(sys.argv) > 2 else DEFAULT_CONTENT_ROOT
    asyncio.run(_main(_level, _root))
