---
id: 252
title: Completing a full mock exam awards zero XP
severity: medium
area: exam
persona: exam-crammer
status: done
found: 2026-06-22
---

## Steps to reproduce
1. Sign up, complete a full mock exam (start, submit all 4 sections, finish).
2. Check GET /progress/me -- XP is unchanged.
3. Complete 3 more mock exams across A1 and A2 levels.
4. XP is still 0 from exams (only comprehension sets award XP).

## Expected
Completing a full mock exam should award XP (and/or count as an activity for streak purposes), since it is the most substantial learning activity in the app.

## Actual
POST /exam/{id}/finish does not call `record_activity`. Completing a mock exam has no effect on XP, streak, or progress tracking. A user who only uses mock exams (the exam-crammer persona) will appear inactive on the board despite heavy usage.

## Notes
The comprehension module awards 15 XP per first-pass set via `record_activity`. The exam module has no equivalent. The exam `finish` endpoint updates the attempt record but does not touch the progress system. This means the primary activity of the exam-crammer persona is invisible to the progress/board system.

## Triage
- Explanation: `app/exam/api.py` finish endpoint (line 183-208) updates the attempt status to "finished" and computes the CLB report, but never calls `record_activity` from `app/progress/service.py`. The comprehension module calls `record_activity(session, user.id, xp_award=15, level=...)` after completing a set, so comprehension activity counts toward XP and streak. Exam completion -- the most substantial activity in the app -- is entirely invisible to the progress system.
- Against spec: AC1.6 says "streak increments on daily activity; group board shows each member's level/streak." A mock exam is unambiguously a "daily activity." The spec does not enumerate which activities count, but excluding the largest one violates the spirit of the progress system.
- Verdict: validated
- Rationale: Users who primarily use mock exams (the exam-crammer persona) get zero XP and no streak credit, making them appear inactive on the group board despite being the most engaged users. This undermines the group motivation layer that the spec calls out as a core feature.

## Critic
- Challenge: The spec does not explicitly say exam completion should award XP. AC1.6 says "streak increments on daily activity" but does not enumerate which activities count. The exam module was added in Phase 5, while `record_activity` was designed in Phase 1 for the learning core. It is possible the design intentionally separates "learning activities" (lessons, comprehension, writing practice) from "assessment activities" (mock exams), treating exams as measurement rather than practice. The XP amount is also unspecified -- what should a mock exam award? Adding a `record_activity` call introduces a design decision (how much XP?) that has no spec basis.
- Holds up? Yes, with reservation. The XP amount is a design decision, but the streak omission is the stronger argument. AC1.6 says "streak increments on daily activity." Completing a full four-section mock exam is unambiguously a daily activity. A user who only uses mock exams (a valid usage pattern per the exam-crammer persona) would have a permanently zero streak and zero XP, making them invisible on the group board. The spec explicitly requires the board to show "each member's level/streak" as a motivation feature. A user who does the hardest activity in the app appearing as inactive breaks that contract. The XP amount can default to a reasonable value (the comprehension module uses 15). The PM is right.
- Final verdict: validated

Fix: Call record_activity with EXAM_XP=25 in finish endpoint after completing a mock exam (app/exam/api.py, tests/test_exam.py)
