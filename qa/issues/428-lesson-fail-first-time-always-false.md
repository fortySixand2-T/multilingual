---
id: 428
title: Failed lesson result always returns first_time=false even on genuine first attempt
severity: medium
area: progress
persona: edge-case-breaker
status: deferred
found: 2026-07-03
---

## Steps to reproduce
1. Sign up as a fresh user (or use any user who has NOT previously passed a given lesson).
2. Submit a failing score for that lesson:
   `POST /progress/lessons/societe-b2-01/result` with body `{"score": 3.0}`
   (pass_threshold defaults to 8.0, so score 3.0 is a fail)
3. Read the response field `"first_time"`.

## Expected
`"first_time"` should be `true` — this is the user's first-ever attempt at this lesson (no completion row exists). The field should reflect whether the user has previously *attempted* or *completed* the lesson, not be hardcoded.

Alternatively, if `first_time` is defined as "first pass" (i.e. whether we awarded first-pass XP), the field name should be `first_pass` or the API documentation should clearly say "first_time is only meaningful when passed=true".

## Actual
```json
{
  "lesson_id": "societe-b2-01",
  "passed": false,
  "first_time": false,
  "streak": 1,
  "xp": 75
}
```
`first_time` is unconditionally hardcoded to `false` in the failure branch of `app/progress/api.py` (line 63), regardless of whether the user has ever seen this lesson.

## Notes
- Root cause: the early-return on failure in `app/progress/api.py` line 58–67 returns `"first_time": False` without querying the `progress_lesson_completions` table at all.
- A UI that relies on `first_time` to decide whether to show a "first attempt" message or track new-lesson milestones will behave incorrectly for failed first attempts.
- The field is only meaningful when `passed=true` as currently implemented, but the response structure implies it is meaningful in both cases.
- Severity: medium — incorrect data returned to clients; no data loss or security issue.
