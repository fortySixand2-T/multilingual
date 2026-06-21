---
id: 170
title: Concurrent section recording silently drops sections (JSON lost-update)
severity: medium
area: exam
persona: exam-crammer
status: done
found: 2026-06-20
---

## Steps to reproduce
1. Start a mock. Record all four sections concurrently (4 parallel
   `POST /exam/{id}/section`, one per skill).
2. `GET /exam/attempts/{id}`.

## Expected
All four sections persist.

## Actual
Only one (sometimes two) survive — e.g. `recorded: ['writing']` from a 4-way burst. The
others are silently lost. Found via round-009 H1.

## Notes
`record_section` did `sections = dict(attempt.sections); sections[skill] = …;
attempt.sections = sections` — a read-modify-write that rewrites the whole JSON blob. Each
concurrent request reads the same (empty) blob and the last writer clobbers the rest. The
user then can't finish (qa-004 requires all sections) or gets a wrong report.

## Triage
- Explanation: lost-update on the `exam_attempts.sections` JSON column — the whole object
  is overwritten rather than the one key patched.
- Against spec: an exam must not silently drop recorded results.
- Verdict: validated
- Rationale: real, silent **data loss** of the user's exam work — same concurrency class
  we fixed for lessons (qa-070) and comprehension (qa-100), here on a JSON blob.

## Critic
- Challenge: sections are normally recorded one at a time, so is the race realistic?
- Holds up? Yes. The trigger is narrower than a double-click, but the consequence is
  worse (lost graded results, not a 500), a flaky-network retry or two tabs hits it, and
  read-modify-write on a shared blob is a latent fragility. Consistent with the class we
  fix; the atomic patch is the right tool, no new schema.
- Final verdict: validated

Fix: patch the single skill key with an atomic SQLite `json_set` UPDATE instead of
overwriting the blob, so concurrent writes to different keys merge (`app/exam/api.py`;
test `test_concurrent_sections_all_persist`). Verified live: 4 concurrent sections → all
4 persist, zero 500s.
