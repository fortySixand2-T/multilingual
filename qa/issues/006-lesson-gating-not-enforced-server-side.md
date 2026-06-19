---
id: 006
title: Locked lessons can be completed via the API, bypassing unit gating
severity: medium
area: progress
persona: edge-case-breaker
status: done
found: 2026-06-17
---

## Steps to reproduce
1. Sign up a brand-new user. `GET /content/path?level=a1` shows
   `a1.u1: available`, `a1.u2: locked` (u2 unlocks only after u1 completes).
2. Without touching u1, `POST /progress/lessons/cafe-01/result {"score":9.0}`
   (cafe-01 lives in the locked u2).

## Expected
The result is refused (e.g. 403/409 "lesson is locked") because its unit's unlock
requirement isn't met — the same gating the path UI shows.

## Actual
`HTTP 200` → `{"passed":true,"first_time":true,"xp":10}`. A re-fetch of the path shows
`a1.u2: complete`. The lock is purely advisory in the UI; the result endpoint never
checks the unlock rule, so the whole curriculum can be skipped.

## Notes
`POST /progress/lessons/{id}/result` records any known lesson regardless of its unit's
`unlock` requirement. Gating is computed for display in `content/path` but not enforced
on write. A learner (or a tampering client) can skip ahead and pollute the group board.

## Triage
- Explanation: `POST /progress/lessons/{id}/result` (`app/progress/api.py:45`) records
  any known lesson after a pass-threshold check; it never consults the unit `unlock`
  rule. Gating is derived read-only by `compute_unit_status` / `_unlock_ok`
  (`app/content/api.py:35`,`:28`) purely to render `/content/path`.
- Against spec: the plan's Phase 1 is a "structured … level-gated" progression and the
  path schema deliberately models `unlock {type, requires}`. Enforcing it only on read
  makes the model decorative — enforcing on write matches the intent.
- Verdict: validated
- Rationale: any client can complete locked lessons, skip the curriculum, award itself
  XP, and inflate the shared board others see. Medium.

## Critic
- Challenge: This is a 5-friend trust group, and the UI never surfaces a locked lesson —
  it's only reachable by hand-crafting a request, so is it real?
- Holds up? Yes. Unlike an inert tamper it writes a real `LessonCompletion`, awards XP,
  and mutates the shared leaderboard everyone sees; sequencing is a core Phase-1 promise,
  not cosmetic. The fix reuses the existing `_unlock_ok`, so no new complexity.
- Final verdict: validated

Fix: `submit_result` now rejects a locked lesson with 409 via a new
`is_lesson_unlocked()` that reuses the read side's `compute_unit_status`, so write
gating can't drift from what the path renders (`app/content/api.py`,
`app/progress/api.py`; test `test_locked_lesson_result_is_rejected_server_side` in
`tests/test_progress.py`). Verified live: locked→409, available→200, unlock→200.
