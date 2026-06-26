---
id: 391
title: Exam screen does not clear attempt/report state when level changes
severity: medium
area: exam
persona: edge-case-breaker
status: done
resolution: fixed — Exam.tsx [level] effect now resets attempt/recorded/report/error before reloading lists
found: 2026-06-25
---

## Steps to reproduce
1. Sign up / log in, navigate to the Mock exam screen.
2. Start an A1 mock exam (e.g. "TEF Canada mock -- A1 practice"). The screen shows the four-section attempt view with A1 content (comprehension set `read-cafe-01`, etc.).
3. While the attempt is in progress (sections not yet recorded or partially recorded), switch the level selector from A1 to A2.
4. Observe that the screen still shows the A1 attempt with A1 sections and A1 title. The level selector says A2, but the attempt view has not changed.

Alternatively:
1. Complete all four sections of an A1 mock and click "Finish & see CLB report".
2. The report card is displayed.
3. Switch level to A2. The A1 report remains on screen. The "Done" button is the only way out; there is no indication the user is now on A2.

## Expected
When the level changes, the Exam screen should reset `attempt`, `recorded`, `report`, and `error` state (as Comprehension and Writing screens do), returning the user to the blueprint list for the newly selected level.

## Actual
The `useEffect` on `[level]` in `Exam.tsx` only calls `loadLists()` (lines 22-26) to reload blueprints and history, but does not clear `attempt`, `recorded`, `report`, or `error`. The user stays trapped in the previous level's attempt or report view.

- If mid-attempt: the A1 exam sections persist while blueprints reload for A2 in the background (invisible because the attempt view is rendered instead).
- If viewing report: the A1 CLB report stays on screen. Pressing "Done" returns to the list, which now correctly shows A2 blueprints.
- If an error was showing: the stale error message persists.

## Notes
Compare with `Writing.tsx` lines 17-20 which resets `tasks` and `error` on level change, and `Comprehension.tsx` line 14 which resets `error`. The Exam screen is the only skill screen that omits this cleanup. The fix would be adding `setAttempt(null); setRecorded({}); setReport(null); setError("");` at the top of the `useEffect` body.

## Triage
- Explanation: The useEffect on [level] in Exam.tsx only called loadLists() without resetting attempt/recorded/report/error state. When the user switched levels, the previous level's in-progress attempt or finished report remained visible while blueprints silently reloaded in the background. The fix adds setAttempt(null), setRecorded({}), setReport(null), setError("") at the top of the [level] effect, matching the pattern used by Writing.tsx and Comprehension.tsx.
- Against spec: Yes -- every skill screen should reset its view state on level change; the Exam screen was the sole exception, inconsistent with the rest of the app.
- Verdict: validated
- Rationale: A user switching levels would see stale A1 exam content under an A2 heading, creating confusion and potential data-integrity issues if they continued interacting with the wrong-level attempt.

## Critic
- Challenge: Could this be considered cosmetic or unlikely? The level switcher is a dropdown -- would a user really switch levels mid-exam? Verified the fix in Exam.tsx lines 26-35: the useEffect on [level] now resets attempt/recorded/report/error before calling loadLists(). This matches the pattern in Writing.tsx and Comprehension.tsx. Without the fix, the stale attempt view was genuinely reachable by any user who switches levels, and the old attempt remained fully interactive (a user could record sections from the wrong level's exam). That is a real functional bug, not cosmetic.
- Holds up? Yes -- the fix is minimal (four setState calls), consistent with sibling screens, and addresses a real user-facing issue.
- Final verdict: done
