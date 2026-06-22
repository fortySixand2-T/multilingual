---
id: 221
title: Comprehension pass threshold hidden from user
severity: medium
area: comprehension
persona: exam-crammer
status: deferred
found: 2026-06-21
---

## Steps to reproduce
1. GET `/comprehension/sets/read-cafe-01` -- note the response has no `pass_threshold` field.
2. POST `/comprehension/sets/read-cafe-01/submit` with answers getting 1/2 correct.
3. Response says `"passed": true` (threshold is 0.6, score 0.5 rounds... actually 0.5 < 0.6 so it would say false).
4. User has no way to know what score is required to pass.

## Expected
Either the set delivery (`GET /comprehension/sets/{id}`) or the submit response should include the `pass_threshold` so the user knows the target score. For example: `"pass_threshold": 0.6` in the set response, or `"pass_threshold": 0.6` alongside `"passed": true/false` in the submit response.

## Actual
The `_client_view` function in `app/comprehension/api.py` strips the pass threshold from the delivered set. The submit response returns `passed` as a boolean but not the threshold that determined it. Different sets have different thresholds (reading: 0.6, listening: 0.5) which makes this more confusing -- a user might pass one set at 50% but fail another at the same score.

## Notes
An exam-crammer needs to know the bar to aim for. Without it, the `passed` field is opaque. The threshold isn't sensitive information (it's not an answer key). Severity is medium because users can still see pass/fail, but the missing context makes timed practice less useful for self-assessment.

## Triage
- Explanation: The `_client_view` function in `app/comprehension/api.py` deliberately builds a stripped-down view of the set data for delivery, omitting answers, explanations, and the pass_threshold. The submit response returns `passed` (bool), `score`, `correct`, and `total` but not the threshold itself. This is a design choice -- the delivery view is intentionally minimal to prevent cheating in timed sets.
- Against spec: The Phase 2 spec says "timed MCQ sets, per-question explanations" but does not mention exposing the pass threshold to clients. The threshold varies by skill (reading 0.6, listening 0.5) which is a content-level setting, not an API contract.
- Verdict: deferred
- Rationale: This is a UX improvement request, not a bug. The user already sees pass/fail, score, correct count, and total -- enough to self-assess. The threshold is not secret, but exposing it is an enhancement. The submit response already gives the user their numeric score and pass/fail status. Deferring because it is not broken, just could be more informative, and the spec does not require it.

## Critic
- Challenge: The PM deferred this as a UX enhancement. But could a real user be confused by different pass thresholds across skills (reading 0.6 vs listening 0.5)? A user who scores 55% might pass listening but fail reading with no explanation. That said, the submit response already returns `passed` (bool), `score`, `correct`, and `total` -- the user sees exactly whether they passed and what they scored. The threshold is an implementation detail; the pass/fail verdict is the user-facing output. The spec does not require exposing it.
- Holds up? Yes, the deferral holds. The user gets pass/fail plus their numeric score. Knowing the threshold is informative but not essential -- the system already tells you the answer (did you pass or not). This is a genuine enhancement, not a defect.
- Final verdict: deferred
- Rationale: The user receives pass/fail status, score, correct count, and total. The missing threshold is additional context, not a broken feature. The spec does not require it. Deferral is appropriate.
