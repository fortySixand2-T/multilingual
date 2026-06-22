---
id: 220
title: Exam history response omits level field
severity: low
area: exam
persona: exam-crammer
status: done
found: 2026-06-21
---

## Steps to reproduce
1. Sign up and authenticate.
2. POST `/exam/start` with `{"blueprint_id":"mock-2"}` -- start an exam (level a1).
3. Complete all four sections and POST `/{attempt_id}/finish`.
4. GET `/exam/history`.

## Expected
Each attempt object in the `attempts` array should include a `level` field (e.g. `"level": "a1"`) so the user can distinguish attempts across different CEFR levels and filter/sort accordingly.

## Actual
The attempt objects contain `attempt_id`, `blueprint_id`, `status`, `clb_report`, `started_at`, `finished_at` -- but no `level` field. The `ExamAttempt` table stores `level` (line 27 of `app/exam/tables.py`), but the history serialization in `app/exam/api.py` lines 228-238 does not emit it.

Response example:
```json
{
  "attempt_id": 16,
  "blueprint_id": "mock-2",
  "status": "finished",
  "clb_report": {...},
  "started_at": "2026-06-22T03:25:45.555492",
  "finished_at": "2026-06-22T03:26:10.015128"
}
```

## Notes
A user cramming for the exam wants to compare scores across levels or confirm which level each attempt was for. The `blueprint_id` encodes no level info (e.g. `mock-1` and `mock-2` are both a1 but that's not obvious). One-line fix: add `"level": a.level` to the history dict comprehension.

## Triage
- Explanation: The `GET /exam/history` endpoint at `app/exam/api.py` lines 228-238 builds the response dict from ExamAttempt fields but omits the `level` column. The ExamAttempt table (line 27 of `app/exam/tables.py`) stores `level` as a String(16), so the data is available but simply not serialized.
- Against spec: Phase 5 spec says the exam module provides "score history" and "per-skill CLB band output." While the spec does not enumerate exact response fields, the level is necessary context for meaningful history -- a user cannot distinguish A1 vs B1 attempts without it.
- Verdict: validated
- Rationale: Low-effort fix (one line), clear user impact -- an exam-crammer reviewing history cannot tell which CEFR level each attempt targeted. The blueprint_id is opaque and does not encode level.

## Critic
- Challenge: The level field is a nice-to-have, not a bug. The data IS returned -- blueprint_id identifies the exam, and a client could map blueprint_id to level via the blueprint metadata. The spec says "score history" without enumerating fields. Currently only A1 blueprints exist, so there is nothing to distinguish. This is a feature request for future multi-level support, not a defect in the current system.
- Holds up? No. The challenge does not hold. The level column exists on ExamAttempt (it is stored per-attempt), the serialization omits it for no reason, and there is no public API to resolve blueprint_id to level. Even with only A1 today, the field is already populated and costs nothing to emit. Omitting available, useful context from a history endpoint is a serialization bug, not a feature request.
- Final verdict: validated
- Rationale: The data exists, is meaningful, and is simply not serialized. One-line fix, zero risk. The user cannot determine the level of an attempt from the current response without external knowledge.

Fix: Added `"level": a.level` to exam history dict in `app/exam/api.py`.
