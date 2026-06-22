---
id: 280
title: GET /exam/attempts/{id} omits finished_at for completed attempts
severity: medium
area: exam
persona: exam-crammer
status: done
found: 2026-06-22
---

## Steps to reproduce
1. Sign up a fresh user (POST /auth/signup with invite code friend-001).
2. Start an exam (POST /exam/start {"blueprint_id":"mock-1"}).
3. Record all 4 sections (reading, listening, writing, speaking).
4. Finish the exam (POST /exam/{id}/finish).
5. GET /exam/attempts/{id} and inspect the response keys.
6. GET /exam/history and inspect the response keys for the same attempt.

## Expected
The attempt detail endpoint should include `finished_at` for completed attempts, just like the history endpoint does. A user reviewing a specific past attempt needs to know when it was completed.

## Actual
GET /exam/attempts/28 returns keys: `attempt_id, blueprint_id, blueprint, status, started_at, recorded, remaining, clb_report` -- no `finished_at`.

GET /exam/history includes `finished_at: "2026-06-22T19:40:53.078260"` for the same attempt.

The two endpoints are inconsistent. The detail endpoint has `started_at` but not `finished_at`.

## Notes
The history endpoint serializes `finished_at` at line 245 of app/exam/api.py, but the get_attempt endpoint (lines 129-138) does not include it. One-line fix: add `"finished_at": attempt.finished_at.isoformat() if attempt.finished_at else None` to the returned dict.

## Triage
- Explanation: The `get_attempt` endpoint (app/exam/api.py lines 119-138) builds its response dict with `started_at` but never includes `finished_at`, even though the model stores it (set at line 214 in the `finish` endpoint). The `history` endpoint (line 245) does serialize `finished_at`. This is a simple omission in the detail endpoint's response construction.
- Against spec: The spec does not enumerate exact response fields, but the two endpoints describe the same resource (an exam attempt) and are inconsistent with each other. A completed attempt should expose its completion timestamp on its detail view -- this is basic data completeness, not a feature request.
- Verdict: validated
- Rationale: A learner (or future frontend) reviewing a specific past attempt via GET /exam/attempts/{id} cannot see when it was completed, even though the data exists in the database and is returned by the history list endpoint. Low-effort fix with clear user value.

## Critic
- Challenge: The get_attempt endpoint docstring says "Resume support" -- it was designed for resuming in-progress attempts, not for reviewing completed ones. For in-progress attempts, finished_at is always None, so omitting it is reasonable by design. The history endpoint is the intended way to review past attempts. The spec does not require finished_at on the detail endpoint. This could be treated as a feature request rather than a bug.
- Holds up? Yes -- the challenge is weak because get_attempt does not filter by status; it happily returns finished attempts including their clb_report (which is only meaningful post-completion). If the endpoint already serves finished attempts and already includes completion-specific data like clb_report, omitting finished_at while including started_at is an inconsistency within the endpoint itself, not just between endpoints. The docstring may say "resume support" but the implementation is a general-purpose detail view. One-line fix, no added complexity.
- Final verdict: validated

## Fix
Added `finished_at` to the `get_attempt` response dict in `app/exam/api.py` (line 135). Added test `test_get_attempt_includes_finished_at` in `tests/test_exam.py` verifying the field is None for in-progress attempts and a valid ISO timestamp for finished ones, consistent with the history endpoint.
