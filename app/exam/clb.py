"""CLB band mapping + aggregation. Output is an *estimate*, never an official score (R3, Phase 5 stop)."""
from __future__ import annotations

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
