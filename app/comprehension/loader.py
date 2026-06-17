"""Load + validate comprehension sets from files (content/<level>/comprehension/*.yaml)."""

from __future__ import annotations

from pathlib import Path

from app.comprehension.models import ComprehensionSet
from app.loaders import load_keyed_yaml


class ComprehensionError(Exception):
    pass


def load_sets(content_root: str | Path, level: str) -> dict[str, ComprehensionSet]:
    return load_keyed_yaml(
        Path(content_root) / level / "comprehension",
        ComprehensionSet,
        duplicate_error=lambda i, f: ComprehensionError(
            f"duplicate comprehension set id {i!r} ({f})"
        ),
    )
