---
id: 050
title: Lesson grading is client-reported — a fabricated perfect score passes
severity: medium
area: progress
persona: edge-case-breaker
status: deferred
found: 2026-06-19
---

## Steps to reproduce
1. `POST /progress/lessons/greetings-01/result {"score": 10}` without answering anything.

## Expected (per the report)
The server checks the submitted answers, so a fabricated score can't pass.

## Actual
`passed: true`, XP awarded. The lesson result endpoint trusts a client-computed `score`;
no answers are sent or verified server-side. Found via round-004 H5.

## Notes
Lesson exercises ship their `answer` to the client (the SPA self-grades MCQs offline).

## Triage
- Explanation: by design — lessons are graded client-side for offline capability; the
  result endpoint records the reported `score`. There is no server-side answer check.
- Against spec: the architecture intentionally puts MCQ grading on the client. Closing
  this means re-architecting to submit answers and grade server-side for every lesson.
- Verdict: validated (low/medium) — shared-board XP is gameable.

## Critic
- Challenge: this is the deliberate design (and the same is true of exam sections, which
  are also self-reported). For a 5-friend trust group, the only victim of a fabricated
  score is the cheater's own progress. Re-architecting grading is disproportionate to the
  threat model and cuts against "keep it simple."
- Holds up? The concern is real (XP is shared) but the *fix* isn't worth it now — unlike
  qa-006 (gating, enforceable in one cheap check) this needs server-side grading across
  the curriculum. Distinguish on feasibility, not just shared-state.
- Final verdict: deferred — accept the client-trust tradeoff for the trust group; revisit
  if the group grows or stakes rise (then submit answers + grade server-side). No change now.
