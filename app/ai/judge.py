"""Pairwise LLM-as-judge critic for subjective profiles (drills, grammar, examiner).

Where there's no gold label, quality is measured by an LLM judge comparing two
actors' outputs head-to-head. The judge is itself a routing profile
(`pairwise_judge`, pinned to a strong model), so the critic is vendor-swappable
like everything else. Each pair is judged in **both orders** and the verdict kept
only if the two orderings agree — otherwise it's a tie. That cancels the judge's
position bias (the well-known tendency to favour whichever output came first).

`run_pairwise_eval` is generic over the profile under test: the caller supplies
`generate(target, item) -> (text, LLMResult)` (how an actor produces output) and
`describe(item) -> str` (the task text the judge sees). Aggregation + ranking reuse
`app.ai.evaluation`. See docs/model-eval.md.
"""

from __future__ import annotations

import itertools
import json
import re
from collections.abc import Callable
from pathlib import Path

from app.ai.evaluation import ModelStats, RankedModel, pairwise_win_rates, rank
from app.ai.interfaces import LLMResult, Msg

_PROMPT = (Path(__file__).parent / "prompts" / "pairwise_judge.md").read_text(encoding="utf-8")
_PROFILE = "pairwise_judge"


def parse_winner(text: str) -> str:
    """Extract 'A' | 'B' | 'tie' from the judge's JSON reply (tolerant of prose)."""
    start, end = text.find("{"), text.rfind("}")
    if start != -1 and end > start:
        try:
            w = str(json.loads(text[start : end + 1]).get("winner", "")).strip().lower()
            if w in ("a", "b", "tie"):
                return "tie" if w == "tie" else w.upper()
        except json.JSONDecodeError:
            pass
    m = re.search(r"\b(tie|a|b)\b", text.lower())  # fallback: first standalone token
    if m:
        return "tie" if m.group(1) == "tie" else m.group(1).upper()
    return "tie"  # unparseable verdict -> no clear winner


class PairwiseJudge:
    def __init__(self, router, *, profile: str = _PROFILE) -> None:
        self._router = router
        self._profile = profile

    def _judge_once(self, task: str, first: str, second: str) -> str:
        """Return 'first' | 'second' | 'tie' — which argument the judge preferred."""
        user = f"TASK:\n{task}\n\nOUTPUT A:\n{first}\n\nOUTPUT B:\n{second}"
        result = self._router.run(self._profile, system=_PROMPT, messages=[Msg("user", user)])
        w = parse_winner(result.text)
        return {"A": "first", "B": "second", "tie": "tie"}[w]

    def compare(self, *, task: str, output_a: str, output_b: str) -> str:
        """Return 'a' | 'b' | 'tie'. Judged in both orders; a disagreement between
        the orderings (a position-bias signal) is scored a tie."""
        r1 = self._judge_once(task, output_a, output_b)  # first=a, second=b
        r2 = self._judge_once(task, output_b, output_a)  # first=b, second=a
        v1 = {"first": "a", "second": "b", "tie": "tie"}[r1]
        v2 = {"first": "b", "second": "a", "tie": "tie"}[r2]
        return v1 if v1 == v2 else "tie"


def run_pairwise_eval[T](
    candidates: list[str],
    items: list[T],
    *,
    generate: Callable[[str, T], tuple[str, LLMResult]],
    describe: Callable[[T], str],
    judge: PairwiseJudge,
    lam: float = 0.15,
) -> list[RankedModel]:
    """Round-robin pairwise eval of `candidates` over `items`, ranked by win rate
    with the same cost-penalized policy as the ground-truth eval.

    `generate(target, item)` produces an actor's output (+ usage for cost);
    `describe(item)` is the task text shown to the judge.
    """
    outputs: dict[str, dict[int, str]] = {c: {} for c in candidates}
    cost: dict[str, float] = dict.fromkeys(candidates, 0.0)
    for i, item in enumerate(items):
        for c in candidates:
            text, result = generate(c, item)
            outputs[c][i] = text
            cost[c] += result.usage.cost_usd

    outcomes: list[tuple[str, str, str]] = []
    for i, item in enumerate(items):
        task = describe(item)
        for a, b in itertools.combinations(candidates, 2):
            verdict = judge.compare(task=task, output_a=outputs[a][i], output_b=outputs[b][i])
            winner = {"a": a, "b": b, "tie": "tie"}[verdict]
            outcomes.append((a, b, winner))

    quality = pairwise_win_rates(outcomes)
    stats = [
        ModelStats(
            model=c, quality=quality.get(c, 0.0), cost_usd=round(cost[c], 6), plays=len(items)
        )
        for c in candidates
    ]
    return rank(stats, lam=lam)
