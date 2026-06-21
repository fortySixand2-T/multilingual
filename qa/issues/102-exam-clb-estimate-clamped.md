---
id: 102
title: Exam clb_estimate accepts out-of-range values (silently clamped)
severity: low
area: exam
persona: edge-case-breaker
status: rejected
found: 2026-06-19
---

## Steps to reproduce
1. Start a mock, `POST /exam/{id}/section` with `{"skill":"writing","clb_estimate":999}`.

## Expected (per the report)
422 — `clb_estimate` should be a CLB band (1–12).

## Actual
`HTTP 200` → `{"skill":"writing","clb":12}`. The value is clamped by
`max(1, min(12, clb_estimate))`. Found via round-006 H4.

## Triage
- Explanation: `record_section` clamps the self-reported writing/speaking estimate into
  [1, 12] rather than rejecting out-of-range input.
- Against spec: writing/speaking are *self-estimated* bands in this practice tool; clamping
  to the valid range is coherent, not nonsensical.
- Verdict: borderline — could add `Field(ge=1, le=12)` for tidiness.

## Critic
- Challenge: unlike qa-005 (correct>total — a *contradictory* input that fabricated a top
  score), 999→12 is an out-of-range value clamped to the boundary, a normal defensive
  pattern. It's self-inflicted, only affects your own self-estimated section, and
  `overall = min` means one clamped-high skill rarely changes the result. The board shows
  xp/streak, not CLB — no shared-state harm.
- Holds up? Yes — no real victim; clamping is acceptable. Adding a validator here is
  tidiness, not a fix, and we don't churn the hot path for that.
- Final verdict: rejected — clamping is acceptable defensive behavior. No change.
