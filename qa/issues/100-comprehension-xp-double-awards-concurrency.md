---
id: 100
title: Comprehension XP double-awards under concurrent submits
severity: medium
area: progress
persona: edge-case-breaker
status: done
found: 2026-06-19
---

## Steps to reproduce
1. Sign up. Fire several identical correct `POST /comprehension/sets/{id}/submit`
   requests in parallel.

## Expected
The set's XP (COMPREHENSION_XP = 15) is awarded once, no matter how many land together.

## Actual
5 parallel passes → `xp = 75` (5 × 15). Each request runs `prior_pass` (a SELECT), all
miss it before any commits, and all award XP. Found via round-006 H1. Unlike lessons
(qa-070), there's no unique constraint to stop it — so it silently inflates XP rather
than 500ing, and XP shows on the shared board.

## Triage
- Explanation: the award was a racy check-then-act (`prior_pass` SELECT → award). With no
  unique key on a "passed this set" fact, concurrent first-passes all award.
- Against spec: same shared-board XP integrity concern as qa-070/010.
- Verdict: validated
- Rationale: reachable by a double-click; corrupts shared-board XP (data, not just a 500).

## Critic
- Challenge: self-inflicted, practice board — worth a schema change?
- Holds up? Yes. It's the same class we fixed for lessons; leaving one XP path racy is
  inconsistent, and the corruption is silent (worse than the 070 crash). The marker table
  is tiny and mirrors the established pattern — proportionate.
- Final verdict: validated

Fix: new `comprehension_passes(user_id, set_id)` table with a unique key (migration
0009). An in-time pass claims it via `on_conflict_do_nothing`; `rowcount == 1` is the one
first-pass that awards XP — atomic, so concurrency can't double-pay. Replaced the
`prior_pass` SELECT (`app/comprehension/{tables,api}.py`, `migrations/versions/0009_*`;
test `test_concurrent_passes_award_xp_once`). Verified live: 5 parallel passes → xp 15.
