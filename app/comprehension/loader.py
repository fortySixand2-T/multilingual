"""Load + validate comprehension sets from files (content/<level>/comprehension/*.yaml)."""
from __future__ import annotations

from pathlib import Path

import yaml

from app.comprehension.models import ComprehensionSet


class ComprehensionError(Exception):
    pass


def load_sets(content_root: str | Path, level: str) -> dict[str, ComprehensionSet]:
    root = Path(content_root) / level / "comprehension"
    sets: dict[str, ComprehensionSet] = {}
    if not root.is_dir():
        return sets  # comprehension is optional per level
    for f in sorted(root.glob("*.yaml")):
        cs = ComprehensionSet.model_validate(yaml.safe_load(f.read_text(encoding="utf-8")))
        if cs.id in sets:
            raise ComprehensionError(f"duplicate comprehension set id {cs.id!r} ({f.name})")
        sets[cs.id] = cs
    return sets
