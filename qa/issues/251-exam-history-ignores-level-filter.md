---
id: 251
title: GET /exam/history silently ignores level query param
severity: low
area: exam
persona: exam-crammer
status: rejected
found: 2026-06-22
---

## Steps to reproduce
1. Complete exams at both A1 and A2 levels.
2. GET /exam/history?level=a2 -- returns all 5 attempts (A1 and A2 mixed).
3. GET /exam/history?level=a1 -- same 5 attempts.
4. GET /exam/history (no level) -- same 5 attempts.

## Expected
Either the `level` query param should filter results to only that level's attempts, or the endpoint should reject the unknown param so the client knows filtering is not supported.

## Actual
The `level` query param is silently ignored. All attempts are returned regardless of the value. A client building a "show only A2 history" view would display wrong results.

## Notes
The blueprints endpoint requires `level` as a mandatory param. Consistency would suggest history should also support it. The `level` field is already present on each attempt record, so filtering is trivial to add. Low severity because the client can filter locally, but the silent acceptance of a no-op param is misleading.

## Triage
- Explanation: `app/exam/api.py` line 211-240 -- the `history` endpoint signature has no `level` parameter, so FastAPI simply ignores unknown query params. This is standard FastAPI/HTTP behavior: unrecognized query parameters are not rejected. The endpoint returns all attempts for the user, with the `level` field included in each record so the client can filter locally.
- Against spec: The spec (Phase 5) says "score history" with no mention of server-side filtering by level. The `/exam/blueprints` endpoint requires `level` because it is a content-discovery endpoint, not because all exam endpoints must accept `level`. There is no spec requirement for filtered history.
- Verdict: rejected
- Rationale: This is a feature request, not a bug. The endpoint works as designed -- it returns all history with level data included. Silent acceptance of unknown query params is standard HTTP/FastAPI behavior, not a defect. The client can filter locally with the data provided.

## Critic
- Challenge: Could the PM be wrong to reject this? If the endpoint silently accepts `?level=a2` and returns unfiltered data, a client developer could reasonably assume filtering is working and ship a broken "A2 only" view without realizing it. Silent acceptance of a semantically meaningful parameter name could be a usability trap for API consumers.
- Holds up? No, the rejection holds. The spec says "score history" with no mention of filtering. FastAPI's standard behavior of ignoring unknown query params is well-documented and expected by any developer familiar with the framework. The level field is included in each response record, so the client has the data to filter locally. Adding server-side filtering would be a feature enhancement, not a bug fix. The PM correctly identified this as a feature request.
- Final verdict: rejected
