"""Mock scoring: TEF → CLB bands, DELF → points /25 per section.

Output is an estimate, never an official score (R3).
"""

from __future__ import annotations

import math

# comprehension score fraction -> CLB band (approximate; calibrate against real data later)
_BANDS: list[tuple[float, int]] = [
    (0.90, 9),
    (0.80, 8),
    (0.70, 7),
    (0.55, 6),
    (0.40, 5),
    (0.25, 4),
    (0.00, 3),
]


def clb_from_fraction(fraction: float) -> int:
    frac = max(0.0, min(1.0, fraction))
    for threshold, band in _BANDS:
        if frac >= threshold:
            return band
    return 3


def aggregate_report(per_skill: dict[str, int]) -> dict:
    """Build the CLB report from per-skill bands. Overall = the floor across skills
    (a profile is only as strong as its weakest skill, like CLB reporting)."""
    bands = [b for b in per_skill.values() if b is not None]
    overall = min(bands) if bands else None
    return {
        "per_skill": per_skill,
        "overall": overall,
        "target_met": overall is not None and overall >= 7,  # CLB 7 goal
        "note": "Estimate only — not an official TEF result.",
    }


# DELF: every section is marked /25; the diploma needs 50/100 overall AND at least
# 5/25 in each section (a single very weak skill fails the whole exam).
DELF_SECTION_MAX = 25
DELF_PASS_TOTAL = 50
DELF_SECTION_MIN = 5


def half_point(points: float) -> float:
    """Round to the nearest half point, halves up (the grids' granularity; round() is banker's)."""
    return math.floor(points * 2 + 0.5) / 2


def delf_points(fraction: float) -> float:
    """Comprehension score fraction -> DELF points /25."""
    return half_point(max(0.0, min(1.0, fraction)) * DELF_SECTION_MAX)


def delf_report(per_skill: dict[str, float]) -> dict:
    total = sum(per_skill.values())
    return {
        "format": "delf",
        "per_skill": per_skill,
        "total": total,
        "max": DELF_SECTION_MAX * len(per_skill),
        "passed": total >= DELF_PASS_TOTAL
        and all(v >= DELF_SECTION_MIN for v in per_skill.values()),
        "note": "Estimate only — not an official DELF result.",
    }
