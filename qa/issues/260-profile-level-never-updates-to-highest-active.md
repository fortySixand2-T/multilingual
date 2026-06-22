---
id: 260
title: Profile level stuck at first-activity level, never updates when user advances
severity: medium
area: progress
persona: returning-learner
status: done
found: 2026-06-22
---

## Steps to reproduce
1. Sign up a fresh user (invite code `friend-001`).
2. Complete greetings-01 (A1 lesson) with score 9.0 -- this creates the UserProgress row with `level="a1"`.
3. Complete all three A2 unit 1 lessons (routine-a2-01, routine-a2-02, routine-a2-03) with score 9.0.
4. GET /progress/me -- observe the `level` field.
5. GET /progress/board -- observe the user's `level` in the member list.

## Expected
The user's level should reflect their most recently active level (or highest level with progress). After completing A2 lessons, the profile and board should show `"level": "a2"`.

## Actual
The `level` field is permanently stuck at `"a1"` (the level of the first lesson ever completed). `GET /progress/me` returns `{"level": "a1", ...}` and the board shows the user as A1, even though they completed an entire A2 unit.

The root cause is in `get_or_create_progress()` in `app/progress/service.py`: the `level` parameter is only used when creating a new row. Once the row exists, `level` is never updated, even when `record_activity` is called with `level="a2"`.

## Notes
- A user who starts directly with A2 (never touches A1) correctly shows `"level": "a2"`.
- For the returning-learner persona, this means the group board labels them as A1 even after weeks of A2 study, which is misleading and discouraging.
- Severity is medium because the data is cosmetically wrong but does not block functionality (gating, XP, SRS all work correctly across levels).

## Triage
- Explanation: `app/progress/service.py` `get_or_create_progress()` (line 26-39) only uses the `level` parameter when creating a new `UserProgress` row. Once the row exists, the level is never updated. `record_activity()` (line 42-60) passes `level` to `get_or_create_progress` but that has no effect on an existing row -- it updates streak, last_active, and xp, but never touches `prog.level`. So the level is frozen at whatever value was passed during the user's very first activity.
- Against spec: AC1.6 says "group board shows each member's level." The board showing a stale level (A1 for a user actively studying A2) is misleading. The spec does not detail level-advancement logic, but showing the wrong level is clearly not intended.
- Verdict: validated
- Rationale: Users who progress from A1 to A2 are permanently shown as A1 on their profile and the group board. This is misleading and discouraging for the returning-learner persona. The fix is to update `prog.level` in `record_activity` when the incoming level is higher than the stored one.

## Critic
- Challenge: The spec does not define level-advancement logic. The `level` field on UserProgress could be interpreted as "starting level" or "registration level" rather than "current active level." A user might do one A2 lesson while primarily studying A1 -- auto-promoting them to A2 on the board could be equally misleading. The spec says "group board shows each member's level" but does not say that level must change dynamically. Maybe the user should explicitly set their level in a profile setting, and the current behavior (frozen at first activity) is a placeholder for that.
- Holds up? Yes. The challenge about interpretation is theoretical. In practice, the code passes the level of the current activity to `record_activity` (e.g., `level="a2"` when completing an A2 lesson), which strongly implies intent to track the user's active level. The `get_or_create_progress` function accepts a `level` parameter on every call, which makes no sense if the level is meant to be static after creation. The behavior where a user completes an entire A2 unit and is still labeled A1 on the board is clearly a bug in the write path -- the level parameter is passed but silently ignored on existing rows. The fix (update `prog.level` when the incoming level is higher) is a single line with no added complexity. The PM is correct.
- Final verdict: validated

Fix: In record_activity, promote prog.level when incoming level is higher per CEFR ordering (app/progress/service.py, tests/test_progress.py)
