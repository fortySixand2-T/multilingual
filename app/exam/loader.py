"""Load + validate exam blueprints (content/<level>/exam/*.yaml)."""

from __future__ import annotations

from pathlib import Path

from app.assessment.loader import load_tasks
from app.comprehension.loader import load_sets
from app.exam.models import ExamBlueprint
from app.loaders import load_keyed_yaml


class ExamError(Exception):
    pass


def load_blueprints(content_root: str | Path, level: str) -> dict[str, ExamBlueprint]:
    bps = load_keyed_yaml(
        Path(content_root) / level / "exam",
        ExamBlueprint,
        duplicate_error=lambda i, f: ExamError(f"duplicate exam blueprint id {i!r} ({f})"),
    )
    _check_references(bps, content_root, level)
    return bps


def _check_references(bps: dict[str, ExamBlueprint], content_root: str | Path, level: str) -> None:
    """A mock only references content other modules own. Resolve every reference
    against *this level's* content so a typo'd id (or a cross-level one) fails the
    load instead of 500ing at exam time."""
    sets = load_sets(content_root, level)
    task_ids = set(load_tasks(content_root, level))
    errors: list[str] = []

    for bp in bps.values():
        for sec in bp.sections:
            if sec.comprehension_set_id is not None:
                cs = sets.get(sec.comprehension_set_id)
                if cs is None:
                    errors.append(
                        f"{bp.id}: {sec.skill} section references comprehension set "
                        f"{sec.comprehension_set_id!r} not in level {level!r}"
                    )
                elif cs.skill != sec.skill:
                    errors.append(
                        f"{bp.id}: {sec.skill} section references {sec.comprehension_set_id!r}, "
                        f"which is a {cs.skill} set"
                    )
            for tid in sec.writing_task_ids:
                if tid not in task_ids:
                    errors.append(
                        f"{bp.id}: writing section references task {tid!r} not in level {level!r}"
                    )

    if errors:
        raise ExamError("exam blueprint reference errors:\n  - " + "\n  - ".join(errors))
