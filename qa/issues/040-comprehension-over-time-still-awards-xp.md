---
id: 040
title: Over-time comprehension submission still passes and awards XP
severity: medium
area: comprehension
persona: exam-crammer
status: done
found: 2026-06-19
---

## Steps to reproduce
1. `GET /comprehension/sets/listen-greet-01` (time_limit_seconds: 90).
2. Submit all-correct with `elapsed_seconds: 999`.

## Expected
An over-time run shouldn't earn progression — timed listening that ran past the limit
wouldn't count under exam conditions.

## Actual
`passed: true`, `over_time: true`, **`first_pass: true`** → XP awarded. The `over_time`
flag was computed and returned but never affected pass/XP. Found via round-004 H2.

## Notes
XP feeds the shared leaderboard, so ignoring the timer inflates board standing.

## Triage
- Explanation: `submit` computes `over_time` (`app/comprehension/api.py:135`) but
  `first_pass` (which gates the XP award) ignored it — `passed and not prior_pass`.
- Against spec: Phase 5 wants timing to match exam conditions; an already-computed flag
  that nothing acts on is a half-built rule.
- Verdict: validated
- Rationale: real, reachable, and it inflates **shared-board XP** (cf. 005/010 — shared
  state is the line we fix on). Medium.

## Critic
- Challenge: the SPA runs the countdown and the flag is for display — isn't enforcement
  the UI's job? And it's practice, CLB is an estimate.
- Holds up? Yes, validated. The UI can be bypassed (raw submit), XP is shared state, and
  making the existing flag mean something is a one-line change — not new complexity. Keep
  `passed`/`score` honest for feedback; just don't pay XP for an over-time run.
- Final verdict: validated

Fix: `first_pass = passed and not prior_pass and not over_time` — over-time runs still
show their score but earn no XP (`app/comprehension/api.py`; test
`test_over_time_pass_earns_no_xp`). Verified live: over-time → xp 0; in-time → xp 15.
