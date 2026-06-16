"""Load + validate writing tasks (content/<level>/writing/*.yaml)."""
from __future__ import annotations

from pathlib import Path

import yaml

from app.assessment.models import WritingTask


class WritingError(Exception):
    pass


def load_tasks(content_root: str | Path, level: str) -> dict[str, WritingTask]:
    root = Path(content_root) / level / "writing"
    tasks: dict[str, WritingTask] = {}
    if not root.is_dir():
        return tasks
    for f in sorted(root.glob("*.yaml")):
        task = WritingTask.model_validate(yaml.safe_load(f.read_text(encoding="utf-8")))
        if task.id in tasks:
            raise WritingError(f"duplicate writing task id {task.id!r} ({f.name})")
        tasks[task.id] = task
    return tasks
