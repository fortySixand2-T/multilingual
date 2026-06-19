# QA loop — testers → triage gate → dev fixer

Multiple **tester agents** use the running app as different user personas and log every
problem in `qa/issues/`. Before anything is fixed, a **triage gate** decides whether
each raised issue is *actually* an issue — a **qa-pm** investigates and explains it,
and a **qa-critic** adversarially challenges that call. Only issues that clear the gate
(`validated`) reach the **dev-fixer**, which fixes them (reproduce → fix with a test →
mark done → commit). This keeps false positives from turning into churn.

```
                 ┌──────────────────────── qa-planner (orchestrates) ────────────────────────┐
tester → open ─▶ qa-pm (explain + judge) ─▶ qa-critic (challenge) ─▶ validated ─▶ dev-fixer ─▶ done
                                                                  └▶ rejected / deferred / needs-info  (no change)
```

A **qa-planner** plans *and* drives the round (it first writes a risk-based test plan,
then runs the pipeline against it); the four worker agents stay independent.

## Independence contract

The agents never call each other and share **no state except the `qa/issues/` backlog**.
Each is a pure stage keyed on issue **status**, so any one can run standalone:

| Agent | Reads | Writes |
|---|---|---|
| `qa-tester` | the running app | new issues `status: open` |
| `qa-pm` | `open` | `## Triage` + `validated`/`rejected`/`deferred`/`needs-info` |
| `qa-critic` | issues with a `## Triage` block | `## Critic` + the final status |
| `dev-fixer` | `status: validated` | the fix + `done` |
| `qa-planner` | CHANGELOG/git, issues, spec, API surface | the round plan in `qa/rounds/`; sequences the others. No issues/verdicts/code |

Because coordination is the status field, the workers stay independent — you can run the
stages by hand in order and get the same result.

## Run a round — orchestrated

> "Use the qa-planner agent to run a QA round."

It first **writes a plan** (`qa/rounds/<NNN>-plan.md`, from `qa/rounds/TEMPLATE.md`):
mines what changed since the last round, past issues, the spec ACs, and untested
endpoints into a ranked list of **hypotheses** ("if X, then Y might break") and a
**charter per persona**. Then it fans out the testers against those hypotheses (with
disjoint issue-id blocks so parallel runs don't collide), runs the gate (pm → critic),
hands only `validated` issues to the dev-fixer, and reports each hypothesis as
confirmed / refuted / untested — escalating any `needs-info` to you.

## Run a round — by hand

1. **Start the app** (both servers):
   ```bash
   ./start.sh serve            # backend :9000  (in one terminal)
   cd web && npm run dev       # SPA :5173      (in another)
   ```
   Seed content first if needed: `./start.sh migrate && ./start.sh content-sync a1`
   (also `comprehension-sync`, `writing-sync`, `exam-sync`).

2. **Spawn testers** — one per persona. In Claude Code:
   > "Use the qa-tester agent with persona `absolute-beginner`."
   Run several (in parallel) across `qa/personas/`. Each files issues into `qa/issues/`.

3. **Triage** — before fixing, gate the new issues:
   > "Use the qa-pm agent to triage the open issues, then the qa-critic to review them."

   The pm marks each `validated` / `rejected` / `deferred` / `needs-info` with an
   explanation; the critic confirms or overturns. Only `validated` survives to step 4.

4. **Fix** — when the backlog has `validated` items:
   > "Use the dev-fixer agent to work the QA backlog."

## Issue backlog

- One file per problem: `qa/issues/NNN-slug.md` (copy `qa/issues/TEMPLATE.md`).
- Status flows: `open` → `triage` → `validated` | `rejected` | `deferred` |
  `needs-info`; a `validated` issue then goes `in-progress` → `done` (or
  `cannot-reproduce`). The pm/critic append `## Triage` and `## Critic` blocks.
- Severity: `blocker` (can't proceed) > `high` (broken/ wrong) > `medium` (confusing/
  rough) > `low` (polish). Triage high-severity first.

## Scope note

Drill, Writing grading, and Speaking need an LLM/STT/TTS provider configured. With
none set, a clean `503` there is expected — testers only file it if the *handling*
is poor, not for the missing provider itself.
