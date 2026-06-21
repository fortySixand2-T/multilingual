---
id: 150
title: Starting a mock repeatedly spawns duplicate in-progress attempts
severity: low
area: exam
persona: exam-crammer
status: done
found: 2026-06-20
---

## Steps to reproduce
1. `POST /exam/start {"blueprint_id":"mock-1"}` three times without finishing.
2. `GET /exam/history`.

## Expected
At most one in-progress attempt per blueprint; "start" resumes the open one.

## Actual
Three distinct `in_progress` attempts for the same blueprint, all shown in history /
resume. Found via round-007 H4. Clutters the resume list built for qa-004 and is easy to
trigger by re-clicking "start".

## Triage
- Explanation: `start` always inserts a new `ExamAttempt`; nothing checks for an existing
  open one.
- Against spec: the qa-004 resume feature assumes you pick up where you left off — multiple
  open attempts of one blueprint undercut that.
- Verdict: validated (low)
- Rationale: self-inflicted clutter, no shared-state harm, but it muddies a feature we
  built and the fix is cheap.

## Critic
- Challenge: harmless practice clutter — worth touching the hot start path?
- Holds up? Yes, low. Resuming the open attempt is the behavior the resume feature implies,
  prevents orphan attempts, and is a handful of lines. A finished attempt still starts a
  fresh one, so nothing legitimate is blocked.
- Final verdict: validated (low)

Fix: `start` returns the existing `in_progress` attempt for the blueprint if one exists,
else creates a new one (`app/exam/api.py`; test
`test_start_resumes_in_progress_instead_of_duplicating`). Verified live: 3 starts → one
attempt id.
