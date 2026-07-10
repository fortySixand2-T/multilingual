---
id: 463
title: "Comprehension submit response missing xp and streak fields"
severity: medium
area: comprehension
persona: returning-learner
status: deferred
found: 2026-07-09
---

## Steps to reproduce
1. Sign up or log in as any user.
2. Submit answers to a comprehension set for the first time (first pass):
   ```
   POST /comprehension/sets/read-cafe-01/submit
   Authorization: Bearer <token>
   {"answers":{"read-cafe-01.q1":"Dans un café","read-cafe-01.q2":"Non"},"elapsed_seconds":30}
   ```
3. Observe the response body.

## Expected
The response should include the updated `xp` and `streak` fields so the user gets
immediate confirmation that their XP and streak were credited — consistent with the
lesson completion endpoint (`POST /progress/lessons/{id}/complete`) which returns:
```json
{"lesson_id":"...","passed":true,"first_pass":true,"streak":1,"xp":20}
```
The comprehension endpoint awards `COMPREHENSION_XP = 15` XP on a first pass
(via `record_activity`) but never surfaces the new totals to the caller.

## Actual
Response on a first-pass submission (HTTP 200):
```json
{
  "set_id":"read-cafe-01",
  "score":1.0,
  "correct":2,
  "total":2,
  "passed":true,
  "first_pass":true,
  "over_time":false,
  "results":[...]
}
```
No `xp` or `streak` fields. The user has no way to see that 15 XP was earned
without making a separate call to `/progress/me`. The UI streak counter and XP
total will appear stale until the next page load.

## Notes
- `app/comprehension/api.py` line 171 calls `record_activity(session, user.id, xp_award=15, level=row.level)` but discards the returned `prog` object without reading `prog.xp` or `prog.streak`.
- The lesson endpoint (`app/progress/api.py` lines 93-104) correctly refreshes `prog` and returns `{"streak": prog.streak, "xp": prog.xp}`.
- Fix would be to capture the `prog` return value, refresh it (as in the lesson path), and include `xp` and `streak` in the comprehension submit response.
- Returning learner persona specifically watches for XP/streak updating immediately and "notices if numbers look wrong or stale."

## Triage
- investigator: qa-pm
- Explanation: The submit handler in `app/comprehension/api.py` line 171 calls `await record_activity(session, user.id, xp_award=COMPREHENSION_XP, level=row.level)` but discards the returned `prog` object entirely. The `return` dict on lines 174-183 has no `xp` or `streak` keys. By contrast, the lesson completion path in `app/progress/api.py` lines 93-97 captures the `prog` return value, calls `await session.refresh(prog)` to get the post-increment value, then includes `prog.streak` and `prog.xp` in its response. The asymmetry is purely an omission in the comprehension submit handler — the data is available, it just is never read or returned.
- Against spec: The Phase 2 ACs in `TEF_Platform_Technical_Plan.md` list "timed MCQ sets, per-question explanations, accent-tagged audio library, replay-disable flag" for comprehension — the submit response shape is unspecified. No AC mandates that xp/streak appear in the comprehension submit response. However, AC1.6 requires "streak increments on daily activity; group board shows each member's level/streak," which implies the streaks and XP totals must be visible to the learner; the spec does not prescribe *when* or *through which endpoint* that visibility is delivered.
- Verdict: validated
- Rationale: The XP and streak are silently awarded and then invisible to the caller until a separate `/progress/me` fetch. This directly degrades the returning-learner persona experience: the UI streak counter and XP total appear stale immediately after completing a comprehension set, which is a real UX defect. The fix is a two-line capture-and-refresh identical to the pattern already used in the lesson completion path. The inconsistency between the two submit endpoints is also a maintenance risk — the lesson path sets a clear pattern that the comprehension path did not follow.

## Critic
- Challenge: The PM's "stale UI counter" harm depends on the frontend actually consuming `xp`/`streak` from the comprehension submit response — but it does not. `CompResult` in `/Users/sirius/projects/multilingual/web/src/api.ts` (lines 169-178) has no `xp` or `streak` fields. The `Results` component in `/Users/sirius/projects/multilingual/web/src/screens/ComprehensionSet.tsx` (line 133) displays a hardcoded `+15 XP` badge derived from `first_pass`, not a live total from the response. There is no `api.me()` call anywhere in ComprehensionSet.tsx and no topbar streak/XP counter in `App.tsx`. The "stale counter" symptom the PM describes does not currently exist in the UI because the UI was never wired to consume these fields. The backend omission is real, but the severity is lower than claimed: the only user-visible gap is that the XP total on the Group Board remains stale until the user navigates there — a normal latency for any aggregated display. The spec (Phase 2 ACs in `TEF_Platform_Technical_Plan.md`) does not mandate these fields in the comprehension submit response. No existing test asserts their absence, so adding them is safe — but the backend change alone would be inert: the frontend `CompResult` type and the `Results` component would also need updating before any user-visible change occurs. The PM validated a half-fix that leaves the UI side unaddressed. The issue as scoped is therefore incomplete rather than wrong.
- Holds up? Partially. The backend omission is confirmed and the fix is low-risk. However, the described user-visible harm ("UI streak counter and XP total appear stale") is not reproducible in the current UI because the frontend does not read those fields from this endpoint at all. The true gap is an end-to-end one spanning backend response shape, TypeScript type, and UI rendering — none of which is captured in this issue's scope. Validating only the backend half creates a dangling fix with no observable user benefit until the UI work is also done.
- Final verdict: deferred
