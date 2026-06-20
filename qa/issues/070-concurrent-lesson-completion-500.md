---
id: 070
title: Concurrent duplicate lesson completion returns an unhandled 500
severity: medium
area: progress
persona: edge-case-breaker
status: done
found: 2026-06-19
---

## Steps to reproduce
1. Sign up. Fire several identical `POST /progress/lessons/greetings-01/result`
   requests in parallel (a double-click or network retry does this).

## Expected
Idempotent: one completion counts, the rest return the already-completed result. No 500.

## Actual
One request returns 200; the others return **`500 Internal Server Error`** with a
SQLAlchemy `IntegrityError: UNIQUE constraint failed: progress_lesson_completions
.user_id, lesson_id` stack trace. Found via round-005 H4.

## Notes
The unique constraint *did* prevent double XP (final xp stayed 10) — the bug is the
unhandled crash, not data loss. A try/except recovery failed because the autoflush
failure poisons the session (rollback returns the insert to *pending*, the recovery read
re-flushes it, looping the same error).

## Triage
- Explanation: `submit_result` did check-then-insert (`_already_completed` then
  `session.add`), which isn't atomic. Under concurrency both pass the check, the second
  insert violates `uq_completion_user_lesson`, and the autoflush error is unhandled.
- Against spec: robustness — a double-click/retry must not 500.
- Verdict: validated
- Rationale: reachable by an ordinary double-click; a 500 + stack trace is a real UX/log
  problem even though XP integrity held. Medium.

## Critic
- Challenge: needs concurrency, and the data is already safe — is it worth touching the
  hot write path?
- Holds up? Yes. Double-click is normal; the fix removes a whole class of races (and the
  same pattern bit `UserProgress` creation for brand-new users). The atomic primitive is
  *simpler* than the check-then-insert it replaces — no new complexity.
- Final verdict: validated

Fix: atomic **insert-or-ignore** (`sqlite_insert(...).on_conflict_do_nothing`) decides
first-completion by `rowcount`; `get_or_create_progress` does the same for the progress
row; XP uses an atomic SQL increment so a concurrent activity can't clobber the award
(`app/progress/api.py`, `app/progress/service.py`; test
`test_concurrent_completions_count_once_no_500`). Verified live: 8 parallel completions on
a brand-new user → all 200, final xp 10, zero IntegrityErrors.
