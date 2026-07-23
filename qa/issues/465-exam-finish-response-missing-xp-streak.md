---
id: 465
title: Exam finish response does not include xp or streak — 25 XP silently awarded
severity: low
area: exam
persona: absolute-beginner
status: done
found: 2026-07-22
---

## Steps to reproduce
1. Sign up as a new user with invite code `friend-001`.
2. Start a mock exam:
   ```
   POST /exam/start
   {"blueprint_id": "mock-1"}
   ```
   Note the `attempt_id` (e.g. 1).
3. Submit all 4 sections (reading, listening, writing, speaking).
4. Finish the exam:
   ```
   POST /exam/1/finish
   Authorization: Bearer <token>
   ```
5. Observe the response body.

## Expected
The finish response should include the updated `xp` and `streak` fields so the user
receives immediate confirmation that 25 XP was credited — consistent with:
- Lesson completion (`POST /progress/lessons/{id}/result`) which returns `xp` and `streak`
- Comprehension submit (fixed in issue 463) which now returns `xp` and `streak`

## Actual
Response from `POST /exam/1/finish` (HTTP 200):
```json
{
    "attempt_id": 1,
    "report": {
        "per_skill": {
            "reading": 8,
            "listening": 9,
            "writing": 7,
            "speaking": 6
        },
        "overall": 6,
        "target_met": false,
        "note": "Estimate only — not an official TEF result."
    }
}
```

No `xp` or `streak` fields. The exam finish handler awards `EXAM_XP = 25` via
`record_activity()` (`app/exam/api.py` line 223) but never reads back the updated
`prog` object or includes `xp`/`streak` in the response.

After finishing, `GET /progress/me` confirms XP did increase (by 25), but the user
has no in-context feedback that points accumulated from this action.

## Notes
- `EXAM_XP = 25` is the highest single-action XP award in the system (vs 10 per
  lesson, 15 per comprehension). Not surfacing it in the finish response makes the
  largest XP event completely invisible.
- Fix pattern mirrors the comprehension fix (issue 463): capture the return value of
  `record_activity()`, call `await session.refresh(prog)`, and add `"xp": prog.xp,
  "streak": prog.streak` to the finish response dict in `app/exam/api.py`.
- Severity is low because a workaround exists (`GET /progress/me` after finish) and
  the XP is correctly persisted; this is a presentation gap only.
- Found against live remote deployment:
  `https://rohith-alienware-17-r4.tail592ffa.ts.net`

## Triage
- Explanation: `finish()` awards EXAM_XP via record_activity but returned only `{attempt_id, report}`; the client couldn't show the new XP/streak without a separate /progress/me fetch.
- Against spec: inconsistent with comprehension submit (qa-463) and the lesson-result endpoint, which return live xp/streak.
- Verdict: validated
- Rationale: real inconsistency; low-risk fix mirroring the accepted qa-463 pattern.

## Critic
- Challenge: does the client already refetch, making this cosmetic?
- Holds up? Yes — qa-463 set the contract that submit/finish endpoints return live totals; parity is expected.
- Final verdict: validated

Fix: finish() returns live xp/streak (refresh on award, else read row); idempotent re-finish reports the same totals (app/exam/api.py; tests/test_exam.py::test_finish_awards_xp)
