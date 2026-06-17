"""Load + validate exam blueprints (content/<level>/exam/*.yaml)."""

from __future__ import annotations

from pathlib import Path

from app.exam.models import ExamBlueprint
from app.loaders import load_keyed_yaml


class ExamError(Exception):
    pass


def load_blueprints(content_root: str | Path, level: str) -> dict[str, ExamBlueprint]:
    return load_keyed_yaml(
        Path(content_root) / level / "exam",
        ExamBlueprint,
        duplicate_error=lambda i, f: ExamError(f"duplicate exam blueprint id {i!r} ({f})"),
    )
