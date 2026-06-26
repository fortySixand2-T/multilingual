---
id: 390
title: Concurrent exam finish requests multiply XP award
severity: high
area: exam
persona: edge-case-breaker
status: done
found: 2026-06-25
---

## Steps to reproduce
1. Sign up with invite code `friend-001`.
2. `POST /exam/start {"blueprint_id":"mock-2"}` -- note the attempt_id.
3. Record all four sections (reading, listening, writing, speaking).
4. Note the current XP via `GET /progress/me`.
5. Fire 10 concurrent `POST /exam/{attempt_id}/finish` requests in parallel.
6. Check XP via `GET /progress/me` again.

## Expected
XP increases by exactly 25 (EXAM_XP constant). The finish endpoint should be
idempotent even under concurrency -- only one request should award XP.

## Actual
XP increases by 250 (10 x 25). All 10 requests see `status == "in_progress"`,
bypass the idempotent early return, and each call `record_activity` with 25 XP.
The SQL-level `xp = xp + 25` is atomic per-statement, so all 10 increments
succeed independently.

Tested with: XP before = 75, XP after = 325, delta = 250.

## Notes
This is the same race pattern as issue 100 (comprehension XP double-award,
fixed), but in the exam finish path which was not similarly protected. The fix
for issue 100 used an atomic status transition guard (e.g., `UPDATE ... WHERE
status = 'in_progress'` with a row-count check) -- the same pattern should be
applied to `POST /exam/{attempt_id}/finish`. File: `app/exam/api.py`, lines
192-218.

## Triage
- Explanation: The finish endpoint (app/exam/api.py lines 192-218) reads the attempt status into a Python object (line 199) and checks it in application code. Under concurrency, N parallel requests all load the attempt while status is still "in_progress", all pass the idempotent guard, and each independently calls record_activity with xp_award=25. The ORM-level status="finished" write on line 214 is a last-writer-wins no-op for duplicates, but the XP increment in record_activity uses SQL "xp = xp + N" which is atomic per-statement, so all N increments succeed. This is the exact same race pattern as issue 100 (comprehension XP double-award), which was fixed with an atomic INSERT-with-rowcount guard but was not applied to the exam path.
- Against spec: The spec expects XP awards to be idempotent. Issue 100 established the precedent that concurrent finish/complete requests must not multiply XP. The exam path was missed when that fix was applied.
- Verdict: validated
- Rationale: Real concurrency bug with direct user-facing impact -- any learner whose client retries or sends overlapping finish requests gets multiplied XP (10x in the reproduction). Fix should use an atomic UPDATE ... WHERE status='in_progress' with rowcount==1 guard, same pattern as the comprehension fix.

## Critic
- Challenge: A normal browser client sends exactly one finish request. Truly concurrent requests require either a malicious user deliberately crafting parallel calls or a buggy client. For a language-learning app where XP is gamification rather than currency, inflated XP is low-stakes. Sequential retries would typically serialize (first commit lands before the second request reads status), so the realistic window is narrow. One could argue this is a theoretical/adversarial-only concern that does not justify added complexity.
- Holds up? yes
- Final verdict: validated
- Rationale: The adversarial argument does not survive scrutiny for three reasons. First, issue 100 established a project-level precedent that concurrent XP multiplication is a real bug worth fixing -- leaving the identical pattern unfixed in the exam path is an inconsistency, not a design choice. Second, the fix is minimal and well-understood (atomic UPDATE ... WHERE status='in_progress' with rowcount check, mirroring the comprehension INSERT-claim pattern at app/comprehension/api.py lines 150-166). It adds no meaningful complexity. Third, the vulnerability is objectively present in the code: the finish endpoint (app/exam/api.py lines 198-217) reads status into a Python object, checks it in application memory, then sets it via ORM attribute assignment with no atomic SQL guard -- a textbook TOCTOU race. Whether the timing window is "narrow" is irrelevant; correctness bugs do not need to be probable to warrant fixing when the fix is trivial.

Fix: Atomic UPDATE ... WHERE status='in_progress' with rowcount guard on exam finish; XP awarded only when rowcount==1 (app/exam/api.py, tests/test_exam.py)
