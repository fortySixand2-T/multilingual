"""Load + validate writing tasks (content/<level>/writing/*.yaml)."""
from __future__ import annotations

from pathlib import Path

from app.assessment.models import WritingTask
from app.loaders import load_keyed_yaml


class WritingError(Exception):
    pass


def load_tasks(content_root: str | Path, level: str) -> dict[str, WritingTask]:
    return load_keyed_yaml(
        Path(content_root) / level / "writing",
        WritingTask,
        duplicate_error=lambda i, f: WritingError(f"duplicate writing task id {i!r} ({f})"),
    )
