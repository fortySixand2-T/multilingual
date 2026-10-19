"""Load + validate exam blueprints.

Per-level mocks live in content/<level>/exam/*.yaml: DELF mocks (`format: delf`) and
the older TEF-style level practice mocks (default format).
The TEF Canada exam is not per level — it spans A1→B2 difficulty in one sitting — so
its mocks live in content/tef/exam/ and may reference content from every level.
"""

from __future__ import annotations

from pathlib import Path

from app.assessment.loader import load_tasks
from app.comprehension.loader import load_sets
from app.exam.models import ExamBlueprint
from app.loaders import load_keyed_yaml

TEF_LEVEL = "tef"


class ExamError(Exception):
    pass


def content_levels(content_root: str | Path) -> list[str]:
    """The CEFR levels with authored content (same rule as the content checker)."""
    return sorted(p.parent.name for p in Path(content_root).glob("*/path.yaml"))


def load_blueprints(content_root: str | Path, level: str) -> dict[str, ExamBlueprint]:
    bps = load_keyed_yaml(
        Path(content_root) / level / "exam",
        ExamBlueprint,
        duplicate_error=lambda i, f: ExamError(f"duplicate exam blueprint id {i!r} ({f})"),
    )
    for bp in bps.values():
        if level == TEF_LEVEL and bp.format != "tef":
            raise ExamError(f"{bp.id}: DELF mocks are per level — move it to <level>/exam")
    _check_references(bps, content_root, level)
    return bps


def _check_references(bps: dict[str, ExamBlueprint], content_root: str | Path, level: str) -> None:
    """A mock only references content other modules own. Resolve every reference
    against *this level's* content (every level's, for TEF) so a typo'd id (or a
    cross-level one in a per-level mock) fails the load instead of 500ing at exam time."""
    levels = content_levels(content_root) if level == TEF_LEVEL else [level]
    sets = {k: v for lvl in levels for k, v in load_sets(content_root, lvl).items()}
    task_ids = {t for lvl in levels for t in load_tasks(content_root, lvl)}
    errors: list[str] = []

    for bp in bps.values():
        for sec in bp.sections:
            for sid in sec.comprehension_set_ids:
                cs = sets.get(sid)
                if cs is None:
                    errors.append(
                        f"{bp.id}: {sec.skill} section references comprehension set "
                        f"{sid!r} not in level {level!r}"
                    )
                elif cs.skill != sec.skill:
                    errors.append(
                        f"{bp.id}: {sec.skill} section references {sid!r}, "
                        f"which is a {cs.skill} set"
                    )
            for tid in sec.writing_task_ids:
                if tid not in task_ids:
                    errors.append(
                        f"{bp.id}: writing section references task {tid!r} not in level {level!r}"
                    )

    if errors:
        raise ExamError("exam blueprint reference errors:\n  - " + "\n  - ".join(errors))
