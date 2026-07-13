# Actor-critic model comparison

How we compare candidate LLMs (Anthropic, GLM/DeepSeek via OpenRouter, local Ollama)
against each other and let measured performance — not a hand-guess — decide routing.

## The idea

Choosing a model for a task is picking one action from a discrete set, so this is a
**bandit with a learned critic**, dressed in actor-critic vocabulary:

| Term | Here |
|---|---|
| **Actor** | a candidate `provider/model` for a profile (an "arm"), e.g. `openrouter/z-ai/glm-4.6` |
| **Critic** | scores an actor's output → reward in `[0, 1]` |
| **Advantage** | `reward − mean(reward over actors on the same item)` — the actor-critic baseline; makes the comparison *relative* and cuts variance |
| **Policy** | cost-penalized **exponential weights** over cumulative advantage → each model's routing weight |

The one knob:

```
utility = advantage − lam · normalized_cost
weight ∝ exp(eta · utility)          # softmax; sums to 1
```

- `lam` (cost sensitivity). **Small → quality-first**, cost only breaks near-ties —
  our default (`0.15`), so graded work stays on strong models. Large → aggressively
  prefer the cheap model unless it's clearly worse.
- `eta` (softmax temperature). Higher → sharper preference for the top actor.

## The critic — three layered signals

1. **Validity gate (disqualifier, not a score).** Before any quality judgement:
   does the output parse and conform? For `writing_feedback` the grader's strict-JSON
   + Pydantic parse *is* the gate — unparseable output scores a **miss** on that item,
   however fluent it read. This keeps a cheap model from ever shipping malformed graded
   output to a learner.
2. **Ground truth where it exists.** `writing_feedback` reuses the human-rated
   **calibration set**: reward = CLB agreement within ±1 band. Objective, no judge.
3. **LLM-as-judge for subjective tasks** (drills, grammar, examiner). **Pairwise**
   ("is A or B the better B2 drill for this prompt?") beats absolute scoring. The
   judge is just another routing profile (`pairwise_judge`) pinned to a strong model,
   so the critic is itself vendor-swappable. Each pair is judged in **both orders**
   and the verdict kept only if the orderings agree — cancelling the judge's position
   bias. Per-model quality is the win rate across comparisons.

## Operating mode: offline shadow (built)

Runs entirely **offline** — never routes a live learner to an unproven model:

```
./start.sh eval "anthropic/claude-opus-4-8,openrouter/z-ai/glm-4.6" b2
```

Each candidate grades every calibration sample → quality (agreement) + cost (provider
usage) → `app.ai.evaluation.rank` → leaderboard + a **suggested** `ai_routing.yaml`
block. Nothing is applied automatically; you read the board and edit routing by hand.

```
model                             quality  cost$    adv    weight
------------------------------------------------------------
anthropic/claude-sonnet-4-6        0.88    0.0300  +0.05    0.37
anthropic/claude-opus-4-8          0.92    0.1500  +0.09    0.35
openrouter/z-ai/glm-4.6            0.81    0.0060  -0.02    0.24
deepseek/deepseek-chat             0.74    0.0030  -0.11    0.04

suggested routing (lam=0.15, quality-first): primary=…, fallback=…
```

## Code map

| Piece | File |
|---|---|
| Pure weighting math (advantages, cost-penalized rank, pairwise win rates, suggestion) | `app/ai/evaluation.py` |
| Ground-truth eval runner for `writing_feedback` (reuses calibration + grader) | `app/assessment/model_eval.py` |
| Pairwise LLM-judge critic (order-swapped) + generic round-robin runner | `app/ai/judge.py` + `app/ai/prompts/pairwise_judge.md` |
| Pairwise eval runner for drills (items from lesson YAML, no DB) | `app/tutor/drill_eval.py` |
| Routing policy seam: `StaticPolicy` (default) + `BanditPolicy` + JSON persistence | `app/ai/policy.py` |
| CLI | `./start.sh eval "t1,t2" [level] [lam] [--save]` · `./start.sh drill-eval "t1,t2" [level] [lam] [limit] [--save]` |
| Tests | `tests/test_model_eval.py` · `tests/test_judge.py` · `tests/test_policy.py` |

## Learned routing (BanditPolicy)

The router asks a **policy** to order a profile's candidate targets:

- **`StaticPolicy`** (default) returns `[primary, fallback]` — today's behavior exactly.
- **`BanditPolicy`** reorders by weights learned in an offline eval, read from a small
  JSON store (`data/model_weights.json`, git-ignored). A profile with no learned weights
  falls through to the static order, and the YAML fallback is always kept as a safety net
  — so enabling the bandit **never regresses an un-evaluated profile**.

Loop: run an eval with `--save` → it writes the ranked order for that profile into the
store → the app loads it at startup (`load_bandit_policy`) and routes by learned weight.
Persistence is a JSON file, not a DB table, because the router is synchronous and the
store is tiny (same config-file ethos as `ai_routing.yaml`).

## Not built yet (follow-up slices)

- **Online ε-exploration** on drill profiles only (small ε live fan-out; never on graded writing).
- **Judge eval for grammar / examiner** (reuse `run_pairwise_eval` with a per-profile
  `generate`/`describe`; drills are wired, these two are the same shape).
