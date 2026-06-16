"""Grading calibration (R3): check the grader against human-rated samples.

A calibration set is sample answers with an expected CLB band. We grade each and
measure how often the estimate lands within tolerance. The agreement math is a
pure function (unit-tested); the live grading CLI needs an LLM provider.
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import yaml

from app.assessment.models import WritingTask  # noqa: F401  (re-exported context)


@dataclass(frozen=True)
class CalibrationSample:
    task_id: str
    section: str
    task_prompt: str
    text: str
    expected_clb: int


@dataclass(frozen=True)
class AgreementReport:
    total: int
    within: int
    pairs: list[tuple[int, int]]  # (expected, actual)

    @property
    def ratio(self) -> float:
        return self.within / self.total if self.total else 0.0


def agreement(pairs: list[tuple[int, int]], tolerance: int = 1) -> AgreementReport:
    """Fraction of (expected, actual) CLB pairs within ±tolerance."""
    within = sum(1 for exp, act in pairs if abs(exp - act) <= tolerance)
    return AgreementReport(total=len(pairs), within=within, pairs=list(pairs))


def load_calibration(content_root: str | Path, level: str) -> list[CalibrationSample]:
    root = Path(content_root) / level / "writing" / "calibration"
    out: list[CalibrationSample] = []
    if not root.is_dir():
        return out
    for f in sorted(root.glob("*.yaml")):
        for row in yaml.safe_load(f.read_text(encoding="utf-8")) or []:
            out.append(
                CalibrationSample(
                    task_id=row["task_id"],
                    section=row["section"],
                    task_prompt=row["task_prompt"],
                    text=row["text"],
                    expected_clb=int(row["expected_clb"]),
                )
            )
    return out
