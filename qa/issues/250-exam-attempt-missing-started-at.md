---
id: 250
title: Exam attempt response omits started_at — client cannot enforce section timers on resume
severity: medium
area: exam
persona: exam-crammer
status: done
found: 2026-06-22
---

## Steps to reproduce
1. Sign up, POST /exam/start with `{"blueprint_id":"a2-mock-1"}`.
2. Note the response: `{"attempt_id": N, "blueprint": {...}}` -- no `started_at`.
3. GET /exam/attempts/N -- response includes `attempt_id`, `blueprint_id`, `blueprint`, `status`, `recorded`, `remaining`, `clb_report` -- no `started_at`.
4. Refresh the page or resume the attempt later. The client has no server-provided timestamp to compute elapsed time for section timers.

## Expected
Both POST /exam/start and GET /exam/attempts/{id} should return `started_at` (and per-section time limits from the blueprint) so the client can enforce timed conditions, especially on resume.

## Actual
`started_at` is stored in the database (it appears in GET /exam/history for finished attempts) but is not returned by the start or attempt-detail endpoints. A client that tracks the timer locally loses it on page refresh or reconnect.

## Notes
The persona cares deeply about realistic timed practice. The blueprint includes `time_limit_seconds` per section, but without a server-provided start timestamp the client cannot reliably enforce those limits across sessions. The field already exists on the model -- it just needs to be included in the response.

## Triage
- Explanation: `app/exam/api.py` -- the `start` endpoint (line 94/109) returns only `attempt_id` and `blueprint` but not `started_at`. The `get_attempt` endpoint (lines 122-130) returns attempt_id, blueprint_id, blueprint, status, recorded, remaining, clb_report -- also no `started_at`. However, the `history` endpoint (line 236) does include `started_at`. The field exists on the `ExamAttempt` model and is populated at creation time (line 103), but the two endpoints a client uses during an active exam omit it.
- Against spec: Phase 5 spec says "Full timed four-section mock" and "timing matches exam." Without `started_at` in the start/resume responses, the client cannot enforce timing across page refreshes or reconnects, which undermines the "timed" requirement.
- Verdict: validated
- Rationale: The spec explicitly requires timed mocks. A client that loses its local timer state (page refresh, reconnect) has no way to recover the correct elapsed time. The field is already stored -- it just needs to be included in two response dicts.

## Critic
- Challenge: The spec says "timing matches exam" but does not prescribe that the server must provide `started_at` to the client. A client could store its own start timestamp locally (localStorage, sessionStorage) and manage timers entirely client-side. Many exam platforms handle timing this way. The server already stores `started_at` for record-keeping; the fact that it does not expose it in two endpoints could be a deliberate choice to keep response payloads minimal. Also, the frontend does not exist yet -- this is an API-only app right now. The "missing" field is arguably a premature optimization for a client that has not been built.
- Holds up? Yes. The challenge is weak on the resume case specifically. The resume path (line 94, returning an existing in-progress attempt) is the critical scenario: a user who refreshes the page or switches devices loses local state entirely. The server is the only source of truth for when the attempt started, and the spec requires timing to "match exam." A client cannot enforce timed conditions on resume without a server-provided timestamp. The field already exists on the model and is populated -- including it in the response dict is a one-line change per endpoint, adding zero complexity. The PM's reasoning is sound.
- Final verdict: validated

Fix: Include started_at (ISO string) in start, resume, and get_attempt responses (app/exam/api.py, tests/test_exam.py)
