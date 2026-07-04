---
id: 418
title: Mock exam permanently stuck in_progress when LLM unavailable — writing/speaking sections cannot be recorded
severity: blocker
area: exam
persona: exam-crammer
status: rejected
found: 2026-07-03
---

## Steps to reproduce
1. POST /exam/start with body `{"blueprint_id": "b2-mock-1"}` — note attempt_id returned (e.g. 75).
2. Record reading and listening sections normally:
   - POST /exam/75/section `{"skill": "reading", "correct": 5, "total": 5, "clb_estimate": 9}`
   - POST /exam/75/section `{"skill": "listening", "correct": 4, "total": 4, "clb_estimate": 9}`
3. Attempt to submit writing task first (as a real user would):
   - POST /assessment/tasks/write-b2-open-letter/submit with ~150-word text
   - Receive: `{"detail": "The AI service is temporarily unavailable. Please try again shortly."}`
   (No clb_estimate is produced because the LLM provider is down.)
4. Try to record the writing section with null clb_estimate:
   - POST /exam/75/section `{"skill": "writing", "correct": null, "total": null, "clb_estimate": null}`
   - Receive: `{"detail": "need clb_estimate"}`
5. Try to finish the exam without recording writing/speaking:
   - POST /exam/75/finish
   - Receive: `{"detail": "finish all sections first — missing: writing, speaking"}`

## Expected
When the AI grading service is unavailable (the documented known-limitation 503 scenario), the mock exam should still be completable. Either:
- The `/exam/{attempt_id}/section` endpoint should accept `clb_estimate: null` and treat ungraded sections as pending, OR
- `/exam/{attempt_id}/finish` should allow finishing with pending (ungraded) sections and omit those skills from the CLB report, OR
- There should be a bypass mechanism that records a writing/speaking section as "submitted — awaiting grade" so the exam attempt does not remain permanently stuck.

## Actual
With no LLM provider active (the normal state of the dev/QA environment):
- POST /exam/75/section with `clb_estimate: null` returns HTTP 422 `{"detail": "need clb_estimate"}`.
- POST /exam/75/finish returns HTTP 400 `{"detail": "finish all sections first — missing: writing, speaking"}`.
- The exam attempt is permanently stuck in `status: in_progress` with no path to completion.

## Notes
- This affects every user of every mock exam that includes writing or speaking sections, which is all B1 and B2 mocks.
- The app's own "known limitation" doc says a clean 503 from writing/speaking grading is expected, implying the rest of the exam flow should still work.
- Confirmed on attempt_id 75 (b2-mock-1) during round 031 QA session 2026-07-03.
- The `/exam/{attempt_id}/section` OpenAPI schema marks `clb_estimate` as `anyOf: [{type: integer}, {type: null}]` — so null is schema-valid, but the handler explicitly rejects it with a 422-like detail message.
