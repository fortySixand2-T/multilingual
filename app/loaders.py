"""Shared content-loading helper.

Several modules load a directory of single-object YAML files keyed by `.id`
(comprehension sets, writing tasks, exam blueprints). One helper instead of a copy
per module. Each caller keeps its own error type via `duplicate_error`.
"""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path

import yaml


def load_keyed_yaml[T](
    directory: str | Path,
    model: type[T],
    *,
    duplicate_error: Callable[[str, str], Exception],
) -> dict[str, T]:
    """Load `directory`/*.yaml into `{obj.id: obj}`, validated by `model`.

    Returns an empty dict if the directory is absent (the section is optional).
    Raises `duplicate_error(id, filename)` on a repeated id.
    """
    items: dict[str, T] = {}
    d = Path(directory)
    if not d.is_dir():
        return items
    for f in sorted(d.glob("*.yaml")):
        obj = model.model_validate(yaml.safe_load(f.read_text(encoding="utf-8")))
        if obj.id in items:  # type: ignore[attr-defined]
            raise duplicate_error(obj.id, f.name)  # type: ignore[attr-defined]
        items[obj.id] = obj  # type: ignore[attr-defined]
    return items
