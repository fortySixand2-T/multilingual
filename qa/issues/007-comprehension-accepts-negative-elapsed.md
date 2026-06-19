---
id: 007
title: Comprehension submit accepts a negative elapsed_seconds
severity: low
area: comprehension
persona: edge-case-breaker
status: rejected
found: 2026-06-17
---

## Steps to reproduce
1. `GET /comprehension/sets/listen-greet-01`.
2. `POST /comprehension/sets/listen-greet-01/submit`
   with `{"answers":{},"elapsed_seconds":-99}`.

## Expected
422 — `elapsed_seconds` can't be negative (it's wall-clock time spent).

## Actual
`HTTP 200`, the submission is accepted with the negative time.

## Notes
The submit body doesn't constrain `elapsed_seconds` (`Field(ge=0)`). This was the
hypothesis left in issue 003's notes ("Same pattern likely applies to comprehension
elapsed_seconds"). Low severity — it only skews any timing display, not scoring or
gating. The CLB report does not currently use this value.

## Triage
- Explanation: `SubmitBody.elapsed_seconds` (`app/comprehension/api.py:37`) is an
  unconstrained `int | None`. It feeds an over-limit check (`> limit`, `:136`) and is
  stored (`:154`); it does not affect scoring, gating, or the CLB report.
- Against spec: comprehension is timed, but `elapsed_seconds` is a client-reported
  convenience value — the spec assigns it no scoring role.
- Verdict: validated (low)
- Rationale: input hygiene, and the sibling endpoint got exactly this in issue 003
  ("same pattern" noted there). The fix is a one-line `Field(ge=0)`.

## Critic
- Challenge: A negative elapsed has no reachable effect. The over-limit branch is
  `> limit`, so a negative simply reads as in-time — indistinguishable from a fast,
  honest submit; it never touches score, gating, or the board, and no screen surfaces
  the stored value. The SPA timer only ever sends `≥ 0` (`ComprehensionSet.tsx`), so
  this is reachable only by hand-crafting a request — self-inflicted.
- Holds up? No. Contrast issue 005, also self-inflicted but kept because it polluted the
  shared CLB board; 007 pollutes nothing a user sees. The 003 precedent doesn't carry —
  there the bad value faked passing/XP/gating; here it's inert. Adding a validator + a
  test for a value with no user-facing consequence is gold-plating against CLAUDE.md's
  "no unnecessary code, simplicity paramount."
- Final verdict: rejected — no change. (Revisit only if a "time spent" stat ever surfaces
  the stored value to users.)
