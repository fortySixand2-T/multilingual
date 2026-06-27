---
id: 403
title: Exam section can be re-submitted to change score before finish
severity: medium
area: exam
persona: exam-crammer
status: rejected
found: 2026-06-26
---

## Steps to reproduce
1. Sign up / log in and obtain a bearer token.
2. POST /exam/start with blueprint_id "b1-mock-1".
3. POST /exam/{attempt_id}/section with `{"skill":"reading","correct":1,"total":3}` -- observe CLB 4.
4. POST /exam/{attempt_id}/section again with `{"skill":"reading","correct":3,"total":3}` -- observe CLB 9.
5. The second submission silently overwrites the first.

## Expected
Once a section result is recorded for an in-progress attempt, re-submitting the same skill should either be rejected (409 "section already recorded") or at least warned. In a real TEF exam, you cannot redo a section after submitting it.

## Actual
The API silently accepts the second submission and overwrites the previous score. A user can submit reading, see the CLB result, then re-submit with better answers to inflate their score. The final CLB report is then based on the gamed scores, making the "estimate" unreliable.

## Notes
The overwrite is technically an atomic json_set (good for concurrency), but the endpoint lacks a guard like `if body.skill in attempt.sections: raise 409`. This matters most for the exam-crammer persona who needs believable, non-gameable CLB estimates to gauge real readiness.

## Triage
- Explanation: sections are keyed by skill in the attempt JSON, so a repeat POST upserts in place (last-write-wins). This is the same mechanism reported in issue 030.
- Against spec: Phase 5 treats mock CLB as an estimate, not official. Section redo is part of the intended practice flow.
- Verdict: rejected
- Rationale: Duplicate of issue 030, which was already rejected through the full gate (PM + critic). The critic ruled that re-recording is a feature for practice, not a bug -- the only "harm" is inflating your own practice estimate, which corrupts no shared state.

## Critic
- Challenge: Could this be a genuinely new angle on issue 030 that the PM dismissed too quickly? The issue frames it as "score gaming" rather than "overwrite." However, the mechanism is identical (POST same skill twice, last write wins), the endpoint is the same, the impact is the same (self-inflicted CLB inflation on a practice estimate), and the critic ruling on issue 030 already addressed the gaming angle explicitly: "the only harm is inflating your own practice estimate; nothing shared is corrupted." The severity bump from low to medium is not justified by any new evidence.
- Holds up? Yes -- the PM's rejection is correct. This is a textbook duplicate. Issue 030 was rejected through the full gate with a clear rationale that directly addresses the "gaming" framing raised here. No new information or angle warrants reopening.
- Final verdict: rejected
