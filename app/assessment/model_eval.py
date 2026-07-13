"""Offline shadow eval: compare candidate models on `writing_feedback`.

Actor-critic, offline mode. Each candidate model grades every writing calibration
sample; the critic reward is objective ground truth (CLB agreement within +/-1),
gated by validity (a candidate whose output can't be parsed as feedback scores a
miss on that item). Costs come from the provider usage. The pure policy math in
app.ai.evaluation turns quality + cost into a cost-penalized weight leaderboard and
a suggested ai_routing.yaml block — nothing is applied automatically.

Run offline (never touches live traffic):
    ./start.sh eval "anthropic/claude-opus-4-8,openrouter/z-ai/glm-4.6" b2

Reuses the existing calibration set, WritingGrader (its strict-JSON parse is the
validity gate) and the agreement metric — this file only adds the per-candidate
loop and the leaderboard.
"""

from __future__ import annotations

from pathlib import Path

from app.ai.errors import AllProvidersFailedError
from app.ai.evaluation import ModelStats, rank, suggested_routing
from app.ai.registry import build_default_registry
from app.ai.router import AIRouter, ProfileConfig
from app.assessment.calibration import load_calibration
from app.assessment.grader import GradingError, WritingGrader

_PROFILE = "writing_feedback"


def _grader_for(registry, target: str) -> WritingGrader:
    """A grader pinned to a single candidate target (no fallback) so the eval
    measures that exact model, not the routing chain."""
    router = AIRouter(registry, {_PROFILE: ProfileConfig("llm", target)})
    return WritingGrader(router)


def evaluate_model(registry, target: str, samples, *, tolerance: int = 1) -> ModelStats | None:
    """Grade every sample with one candidate. Returns None if the model can't run
    at all (e.g. provider not configured). Invalid/unparseable output counts as a
    miss (the validity gate), not an exclusion."""
    grader = _grader_for(registry, target)
    within = 0
    cost = 0.0
    plays = 0
    for s in samples:
        try:
            feedback, result = grader.grade_text(
                task_prompt=s.task_prompt, section=s.section, submission=s.text
            )
        except AllProvidersFailedError:
            if plays == 0:
                return None  # model unavailable — drop it from the leaderboard
            continue
        except GradingError:
            plays += 1  # validity gate: unparseable => a miss
            continue
        plays += 1
        cost += result.usage.cost_usd
        if abs(s.expected_clb - feedback.clb_estimate) <= tolerance:
            within += 1
    quality = within / plays if plays else 0.0
    return ModelStats(model=target, quality=quality, cost_usd=round(cost, 6), plays=plays)


def run_eval(
    candidates: list[str],
    content_root: str | Path,
    level: str,
    *,
    lam: float = 0.15,
    tolerance: int = 1,
):
    """Score each candidate on the level's writing calibration set and rank them."""
    from app.config.settings import get_settings

    registry = build_default_registry(get_settings())
    samples = load_calibration(content_root, level)
    if not samples:
        raise SystemExit(f"no writing calibration samples for level '{level}'")

    stats: list[ModelStats] = []
    for target in candidates:
        print(f"  evaluating {target} on {len(samples)} samples ...")
        s = evaluate_model(registry, target, samples, tolerance=tolerance)
        if s is None:
            print(f"    skipped (provider not configured / unavailable): {target}")
            continue
        stats.append(s)
    return rank(stats, lam=lam)


def _print_leaderboard(ranked, *, lam: float) -> None:
    print(f"\n  model{'':<28}quality  cost$    adv     weight")
    print("  " + "-" * 60)
    for r in ranked:
        print(
            f"  {r.model:<32}{r.quality:>6.2f}  {r.cost_usd:>7.4f}  "
            f"{r.advantage:>+5.2f}  {r.weight:>6.2f}"
        )
    primary, fallback = suggested_routing(ranked)
    print(
        f"\n  suggested routing (lam={lam}, quality-first): primary={primary}, fallback={fallback}"
    )
    print("  (a suggestion only — nothing was applied to ai_routing.yaml)")


if __name__ == "__main__":
    import sys

    if len(sys.argv) < 2:
        print(
            'usage: python -m app.assessment.model_eval "<target1,target2,...>" [level] [lam]\n'
            "  e.g. python -m app.assessment.model_eval "
            '"anthropic/claude-opus-4-8,openrouter/z-ai/glm-4.6" b2'
        )
        raise SystemExit(1)
    _candidates = [c.strip() for c in sys.argv[1].split(",") if c.strip()]
    _level = sys.argv[2] if len(sys.argv) > 2 else "a1"
    _lam = float(sys.argv[3]) if len(sys.argv) > 3 and sys.argv[3] else 0.15
    _ranked = run_eval(_candidates, "content", _level, lam=_lam)
    _print_leaderboard(_ranked, lam=_lam)
