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

## Triage
- Explanation: The ExamAttemptSummary TypeScript type in api.ts omitted the `level` field that the backend already returns. As a result, Exam.tsx could not display which level each in-progress or completed attempt belonged to. The fix adds `level: string` to ExamAttemptSummary and renders `a.level.toUpperCase()` in both the "Resume mock" title (in-progress section) and the score-history card header.
- Against spec: Yes -- with the level switcher enabling multi-level use, attempts from different levels were visually identical, which is a clear information gap.
- Verdict: validated
- Rationale: Users with attempts across multiple levels could not distinguish which attempt belonged to which level, risking resumption of the wrong exam or misattribution of CLB scores.

## Critic
- Challenge: Is this a real problem or theoretical? How many users would have in-progress exams across multiple levels simultaneously? Verified: ExamAttemptSummary in api.ts (line 232) now includes `level: string`. Exam.tsx line 140 shows `a.level.toUpperCase()` in the resume title, line 154 shows it in score history. The backend already returned the field -- this was just a frontend omission. Even if multi-level overlap is uncommon, the score history section persists indefinitely, and users reviewing their CLB scores across levels genuinely need to know which level each score belongs to. The fix is trivial (one type field + two template interpolations).
- Holds up? Yes -- low-severity but real information gap, minimal fix complexity.
- Final verdict: done
