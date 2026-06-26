---
id: 394
title: Level-filtered endpoints silently accept empty-string level and return empty arrays
severity: low
area: content
persona: edge-case-breaker
status: rejected
found: 2026-06-25
---

## Steps to reproduce
1. Sign up and obtain a valid JWT token.
2. `GET /comprehension/sets?level=` -- returns `{"sets":[]}` with HTTP 200.
3. `GET /assessment/tasks?level=` -- returns `{"tasks":[]}` with HTTP 200.
4. `GET /exam/blueprints?level=` -- returns `{"blueprints":[]}` with HTTP 200.
5. `GET /content/path?level=` -- returns `{"detail":"no content for level ''"}` with HTTP 404.

## Expected
All level-filtered endpoints should reject an empty-string level consistently. Either all return 422 (invalid value for required parameter) or all return 404 (no content for that level). The behavior should be uniform across endpoints.

## Actual
`content/path` rejects the empty string with a clear 404 error, but `comprehension/sets`, `assessment/tasks`, and `exam/blueprints` silently return empty arrays with HTTP 200. The same inconsistency applies to any non-existent level like `b2` -- `content/path` returns 404 while the other three return 200 with empty arrays.

## Notes
Low severity because the frontend LevelProvider validates levels against the available set from `/content/levels` and clamps to the first available. However, if a frontend bug or manual API call passes an empty or invalid level, the inconsistent behavior across endpoints could cause confusion (some screens show "no content found" while others show an error). A shared validation layer or guard on the level parameter would make the API more predictable.

## Triage
- Explanation: `content/path` explicitly raises 404 when the query returns zero units (line 108 of content/api.py), because a learning path with no units is a meaningless response. The other three endpoints (comprehension/sets, assessment/tasks, exam/blueprints) use a standard query-filter pattern -- they query rows WHERE level=X and return whatever matches, which is an empty array when nothing matches. Both behaviors are correct for their semantics: a "path" is a singular resource that either exists or does not (404), while "sets", "tasks", and "blueprints" are collection endpoints where an empty result set is a valid response (200 + empty array).
- Against spec: unspecified -- the spec does not mandate a shared level validation layer or prescribe how empty/invalid levels should be handled across list endpoints.
- Verdict: rejected
- Rationale: Working as designed. Returning 200 with an empty array for "no items match this filter" is standard REST collection behavior. The content/path 404 is the intentional outlier because a path is a singular composite resource. The frontend already clamps levels via /content/levels, so no user-facing confusion arises. Adding a shared validation layer would be a nice-to-have but not a bug fix.

## Critic
- Challenge: Could the inconsistency between /content/path (404) and collection endpoints (200 + empty) cause real user-facing bugs? Verified: content/api.py line 108 explicitly raises 404 for empty path results, which is correct singular-resource semantics. Collection endpoints returning empty arrays for no-match is standard REST. The frontend LevelProvider clamps levels from /content/levels, so empty-string level is not reachable through normal UI. This is only reachable via direct API tampering. The "inconsistency" is actually correct design -- different resource types, different semantics.
- Holds up? Yes -- the PM's rejection is correct. No real user impact, correct REST semantics, adding validation would be unnecessary complexity.
- Final verdict: rejected
