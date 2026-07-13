"""Pairwise LLM-judge critic: aggregation, verdict parsing, position-bias handling,
and the round-robin runner (all offline via a scripted fake router)."""

from app.ai.accounting import make_usage
from app.ai.evaluation import pairwise_win_rates
from app.ai.interfaces import LLMResult
from app.ai.judge import PairwiseJudge, parse_winner, run_pairwise_eval


def test_win_rates_from_outcomes():
    # a beats b, a ties c, b loses to c.
    outcomes = [("a", "b", "a"), ("a", "c", "tie"), ("b", "c", "c")]
    wr = pairwise_win_rates(outcomes)
    assert wr["a"] == (1.0 + 0.5) / 2  # win + tie over 2 games
    assert wr["b"] == (0.0 + 0.0) / 2  # loss + loss
    assert wr["c"] == (0.5 + 1.0) / 2  # tie + win


def test_parse_winner_variants():
    assert parse_winner('{"winner": "A"}') == "A"
    assert parse_winner('here you go: {"winner":"b"}') == "B"
    assert parse_winner('{"winner": "tie"}') == "tie"
    assert parse_winner("garbage no json") == "tie"  # unparseable -> tie


class ScriptedRouter:
    """Returns a fixed 'winner' verdict for every judge call."""

    def __init__(self, verdict: str) -> None:
        self._verdict = verdict

    def run(self, profile, *, system, messages, **kw):
        return LLMResult(
            text=f'{{"winner": "{self._verdict}"}}', provider="fake", model="j", usage=make_usage()
        )


def test_compare_agrees_across_orderings():
    # Judge always says the FIRST-shown output wins => order-dependent => tie.
    judge = PairwiseJudge(ScriptedRouter("A"))
    assert judge.compare(task="t", output_a="x", output_b="y") == "tie"


def test_compare_stable_winner():
    # Judge always says "tie" both orders => tie (stable, not position-driven).
    judge = PairwiseJudge(ScriptedRouter("tie"))
    assert judge.compare(task="t", output_a="x", output_b="y") == "tie"


class BiasFreeJudge:
    """Deterministic judge: whichever output string is lexicographically larger wins,
    independent of position — so orderings agree and produce a real winner."""

    def compare(self, *, task, output_a, output_b):
        if output_a == output_b:
            return "tie"
        return "a" if output_a > output_b else "b"


def test_run_pairwise_eval_ranks_by_win_rate():
    candidates = ["m_hi", "m_mid", "m_lo"]
    # Each model emits a constant, distinct output; larger string = "better".
    outputs = {"m_hi": "ccc", "m_mid": "bbb", "m_lo": "aaa"}

    def generate(target, item):
        text = outputs[target]
        result = LLMResult(text=text, provider=target, model="m", usage=make_usage(cost_usd=0.0))
        return text, result

    ranked = run_pairwise_eval(
        candidates,
        items=[0, 1],  # two items; outputs constant so winner is consistent
        generate=generate,
        describe=lambda i: f"item {i}",
        judge=BiasFreeJudge(),
        lam=0.15,
    )
    assert [r.model for r in ranked] == ["m_hi", "m_mid", "m_lo"]
    assert ranked[0].quality == 1.0  # m_hi wins every comparison
    assert ranked[-1].quality == 0.0  # m_lo loses every comparison
