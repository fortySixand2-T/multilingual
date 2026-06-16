"""Sync comprehension sets to the DB and audio files into object storage.

Sets: delete-and-replace per level (same discipline as content sync).
Audio: every file under content/<level>/audio/ is uploaded through the storage
interface under key `<level>/audio/<filename>` — which is what listening sets
reference as `audio_ref`. Real Québec clips are licensing-gated (R6); the example
ships a tiny placeholder so the pipeline runs end to end.
"""
from __future__ import annotations

import asyncio
import mimetypes
import sys
from pathlib import Path

from sqlalchemy import delete
from sqlalchemy.ext.asyncio import AsyncSession

from app.comprehension.loader import load_sets
from app.comprehension.models import ComprehensionSet
from app.comprehension.tables import ComprehensionSetRow
from app.storage.interface import ObjectStorage

DEFAULT_CONTENT_ROOT = "content"


async def sync_sets(session: AsyncSession, level: str, sets: dict[str, ComprehensionSet]) -> None:
    await session.execute(delete(ComprehensionSetRow).where(ComprehensionSetRow.level == level))
    for cs in sets.values():
        session.add(
            ComprehensionSetRow(
                id=cs.id,
                level=level,
                skill=cs.skill,
                accent=cs.accent,
                data=cs.model_dump(mode="json"),
            )
        )
    await session.commit()


def upload_audio(storage: ObjectStorage, content_root: str | Path, level: str) -> int:
    audio_dir = Path(content_root) / level / "audio"
    if not audio_dir.is_dir():
        return 0
    count = 0
    for f in sorted(audio_dir.iterdir()):
        if not f.is_file():
            continue
        key = f"{level}/audio/{f.name}"
        ctype = mimetypes.guess_type(f.name)[0] or "application/octet-stream"
        storage.put(key, f.read_bytes(), content_type=ctype)
        count += 1
    return count


async def sync_comprehension(
    session: AsyncSession, storage: ObjectStorage, content_root: str | Path, level: str
) -> tuple[int, int]:
    sets = load_sets(content_root, level)
    await sync_sets(session, level, sets)
    uploaded = upload_audio(storage, content_root, level)
    return len(sets), uploaded


async def _main(level: str, content_root: str) -> None:
    from app.config.settings import get_settings
    from app.db.session import SessionLocal
    from app.storage.factory import build_storage

    storage = build_storage(get_settings())
    async with SessionLocal() as session:
        n_sets, n_audio = await sync_comprehension(session, storage, content_root, level)
    print(f"synced level {level!r}: {n_sets} comprehension sets, {n_audio} audio files")


if __name__ == "__main__":
    _level = sys.argv[1] if len(sys.argv) > 1 else "a1"
    _root = sys.argv[2] if len(sys.argv) > 2 else DEFAULT_CONTENT_ROOT
    asyncio.run(_main(_level, _root))
