"""Load + validate writing tasks (content/<level>/writing/*.yaml)."""

from __future__ import annotations

from pathlib import Path

from app.assessment.models import WritingTask
from app.content.loader import load_level_vocab
from app.loaders import load_keyed_yaml


class WritingError(Exception):
    pass


def load_tasks(content_root: str | Path, level: str) -> dict[str, WritingTask]:
    tasks = load_keyed_yaml(
        Path(content_root) / level / "writing",
        WritingTask,
        duplicate_error=lambda i, f: WritingError(f"duplicate writing task id {i!r} ({f})"),
    )
    _check_target_vocab(tasks, content_root, level)
    return tasks


def _check_target_vocab(
    tasks: dict[str, WritingTask], content_root: str | Path, level: str
) -> None:
    """Every `target_vocab` id must be a real word *in this level* — this is where
    the within-level constraint is enforced: a word from another level isn't in
    this level's vocab, so it fails here."""
    vocab_ids = set(load_level_vocab(content_root, level))
    errors = [
        f"writing task {t.id!r}: target_vocab references {vid!r}, not a vocab id in level {level!r}"
        for t in tasks.values()
        for vid in t.target_vocab
        if vid not in vocab_ids
    ]
    if errors:
        raise WritingError("writing target_vocab errors:\n  - " + "\n  - ".join(errors))
