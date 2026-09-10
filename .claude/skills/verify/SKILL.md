---
name: verify
description: Choose and run the right level of verification for a change — deterministic checks, an adversarial API probe, a UI pass, or the full QA loop. Use before merging or deploying, when asked to "QA this", "verify", "run a round", or to check whether a change is safe to ship.
---

# Verifying a change

**Pick the cheapest level that can actually find the bug in front of you.** The
full QA loop is five agent stages; most changes do not need it, and running it
where a deterministic check would do has actively caused harm here (see
*When the loop hurts*).

## Choose the level from the change surface

| changed | level | what runs | agents |
|---|---|---|---|
| `content/**` only | **0** | `check_content.py`, pytest, ruff | none |
| backend, API, schema, auth | **1** | level 0 + adversarial API probe | 1 |
| `web/**` | **2** | level 0 + e2e + UI persona pass | 1–2 |
| release, deploy, cross-cutting refactor | **3** | the full loop | 5+ |

When two apply, take the higher. Level 0 always runs — it is the floor, not an
alternative.

## Level 0 — deterministic (no agents)

```bash
python scripts/check_content.py      # content invariants; run BEFORE pytest
ruff check . && ruff format --check .
pytest -q
cd web && npm run build && npx playwright test   # if web/ changed
```

**This is the whole verification for content-only changes.** Every content rule
worth checking is already an assertion — id collisions, `new_vocab` coverage,
audio, tags, path reachability, the YAML traps. An agent cannot beat a
deterministic check on a deterministic property; it can only be slower and
occasionally wrong about it.

## Level 1 — adversarial API probe (1 agent)

> Use the `qa-tester` agent with persona `edge-case-breaker`.

**The single highest-yield stage in the whole loop.** It has produced 58% of all
issues ever filed here at the *lowest* false-positive rate (16% rejected, vs
30–33% for the UX personas). It probes what assertions miss: malformed payloads,
negative and out-of-range values, concurrent double-submits, server-side gating
that the client happens to enforce.

Run it whenever request handling, validation, scoring or state transitions
change. Triage its findings yourself — one agent's output does not need a
committee.

## Level 2 — UI pass

Run the Playwright specs first (`web/e2e/specs/`) — they are deterministic and
cover auth, exam, lesson, path, review, level-switch and the screens smoke test.
Only then:

> Use the `qa-browser-tester` agent with persona `absolute-beginner`.

for what specs cannot assert: whether a screen is *understandable*, whether a
button gives feedback before it is double-tapped, whether a dead end has an exit.
Expect a higher false-positive rate here — this is judgement, not contract.

Known flake: `web/e2e/specs/vocab-deck.spec.ts:30` on chromium. Re-run before
investigating.

## Level 3 — the full loop

> Use the `qa-planner` agent to run a QA round.

planner → testers → `qa-pm` → `qa-critic` → `dev-fixer`, coordinated only by the
`status:` field in `qa/issues/`. See `qa/README.md`.

**Reserve it for releases and cross-cutting change.** Its distinctive value is
the *plan* — mining the diff, past issues and untested endpoints into ranked
hypotheses — and the triage gate, which rejects about one raised issue in four.
That gate is what makes many-agent output safe to act on; it is also most of the
cost.

### Gate only what is worth gating

Severity predicts noise better than anything else in the backlog:

| severity | fixed | rejected | reject rate |
|---|---|---|---|
| medium | 50 | 4 | **6%** |
| high | 11 | 5 | 31% |
| low | 17 | 18 | **47%** |

Nearly half of `low` findings are not real. Send `high`/`medium` through
pm → critic; batch the `low` ones into a single review pass, or defer them.
Do not spend two agent stages adjudicating a cosmetic nit.

## When the loop hurts

Round 055 ran the full loop against the content arc. It found four real
answer-key defects — and its fix for the systemic issue **trimmed `new_vocab`
across 37 lessons, dropping 73 words and reversing the goal of the work**. It
also committed straight to `main` and skipped the CHANGELOG. All of it had to be
overridden by hand.

The lesson is not "agents are unreliable". It is that a domain with a
deterministic verifier should be checked by that verifier. `check_content.py`
now encodes those rules; a content round should be level 0.

**Escalate a level when:** the change crosses a trust boundary (auth, payments,
invites), touches money/score/state that users can't fix themselves, or you
cannot name the assertion that would catch a regression. **Drop a level when:**
the property is already asserted in CI.

## Reporting back

Say which level ran and why, what it found, and what it could not cover. A level
0 pass on a content change is a *complete* verification — say so plainly rather
than implying an agent round was skipped.
