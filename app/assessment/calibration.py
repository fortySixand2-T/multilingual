"""Grading calibration (R3): check the grader against human-rated samples.

A calibration set is sample answers with an expected CLB band. We grade each and
measure how often the estimate lands within tolerance. The agreement math is a
pure function (unit-tested); the live grading CLI needs an LLM provider.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import yaml


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


def run_calibration(content_root: str | Path, level: str, tolerance: int = 1) -> AgreementReport:
    """Grade each calibration sample with the live grader and report agreement.

    Needs an LLM provider configured (it actually calls the model). Run via
    ``python -m app.assessment.calibration [level]``.
    """
    from app.ai.registry import build_default_registry
    from app.ai.router import AIRouter
    from app.assessment.grader import WritingGrader
    from app.config.settings import get_settings

    settings = get_settings()
    router = AIRouter.from_yaml(
        build_default_registry(settings),
        settings.ai_routing_path,
        ollama_model=settings.ollama_model,
    )
    grader = WritingGrader(router)

    pairs: list[tuple[int, int]] = []
    for s in load_calibration(content_root, level):
        feedback, _ = grader.grade_text(
            task_prompt=s.task_prompt, section=s.section, submission=s.text
        )
        pairs.append((s.expected_clb, feedback.clb_estimate))
        print(f"  {s.task_id}: expected CLB {s.expected_clb}, got {feedback.clb_estimate}")
    return agreement(pairs, tolerance)


if __name__ == "__main__":
    import sys

    _level = sys.argv[1] if len(sys.argv) > 1 else "a1"
    report = run_calibration("content", _level)
    print(f"agreement within +/-1: {report.within}/{report.total} ({report.ratio:.0%})")
