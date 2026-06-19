# QA round NNN — plan

- date: YYYY-MM-DD
- app under test: backend :9000 / SPA :5173
- scope: <one line — what this round is mainly chasing>

## Change surface (highest risk first)
What changed since the last round (from CHANGELOG / git) — recently touched code is
where bugs most likely hide.
- …

## Hypotheses (ranked)
The ideas. "If X, then Y might break, because Z." Rank by likelihood × impact.

| # | area | hypothesis | how to probe | persona |
|---|------|------------|--------------|---------|
| H1 | progress | … | … | edge-case-breaker |
| H2 | exam | … | … | exam-crammer |

## Coverage gaps
Endpoints / flows with no issue history yet — blind spots worth a look.
- …

## Charters (per tester, with id blocks)
- `<persona>` (ids NN0–NN9): chase H1, H3 …

## Don't re-file (already settled)
Rejected/deferred issues and known limitations — testers should skip these.
- 007 negative elapsed_seconds — rejected (no impact)
- 001 invalid email — deferred (product decision)
- Drill / Writing / Speaking 503 with no provider — expected

<!-- After the round, the planner notes each hypothesis: confirmed (→ issue NNN) /
     refuted (area sound) / untested. -->
