---
id: 393
title: Exam in-progress and history entries show no level label, indistinguishable across levels
severity: low
area: web
persona: edge-case-breaker
status: done
resolution: fixed — ExamAttemptSummary gains level; resume + score-history entries now show the level
found: 2026-06-25
---

## Steps to reproduce
1. Sign up / log in.
2. Start a mock exam on A1 (e.g. "TEF Canada mock -- A1 practice").
3. Without finishing, switch level to A2 and start a mock there too.
4. Return to the Exam list view. The "In progress" section shows two entries:
   - "Resume mock -- started [date] -- pick up where you left off"
   - "Resume mock -- started [date] -- pick up where you left off"
5. There is no indication which attempt belongs to which level.

Similarly, after finishing exams on both levels, the "Score history" section shows CLB results with no level label.

## Expected
Each in-progress and history entry should display the level (e.g. "A1" or "A2") so the user can tell them apart when they have attempts across multiple levels.

## Actual
The `ExamAttemptSummary` TypeScript type (api.ts line 229) omits the `level` field even though the API returns it. The Exam.tsx template at lines 131-132 only shows "Resume mock" with the start timestamp -- no level. Score history entries (lines 143-149) also lack a level label. With the level switcher now enabling multi-level use, in-progress and completed attempts from different levels are visually identical.

## Notes
The backend `GET /exam/history` response does include `level` per attempt. The fix requires adding `level: string` to `ExamAttemptSummary` and rendering it in both the "In progress" and "Score history" sections. Distinct from rejected issue 251 (API-side filtering) -- this is about UI labeling of already-returned data.
