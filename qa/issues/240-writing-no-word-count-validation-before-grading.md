---
id: 240
title: Writing submit does not validate min/max word count before LLM grading
severity: medium
area: content
persona: edge-case-breaker
status: done
found: 2026-06-22
---

## Steps to reproduce
1. Sign up and authenticate.
2. `GET /assessment/tasks?level=a1` -- note write-a-invite has min_words=40, max_words=100.
3. `POST /assessment/tasks/write-a-invite/submit {"text":"Oui merci."}` (2 words, well under 40-word minimum).
4. Observe the response.
5. Also try with 150 words (above 100-word maximum).

## Expected
The server should reject submissions that violate the task's stated word count
constraints (min_words / max_words) with a 422 before reaching the LLM grading
step. This avoids wasting AI budget on submissions that are clearly invalid.

## Actual
- A 2-word submission is forwarded to the LLM for grading (returns 503 because the
  LLM is offline, but the code path reaches the grader before any word count check).
- An empty string is correctly rejected (422 "submission is empty"), but a non-empty
  string below min_words passes through.
- max_words is never validated server-side at all; it is only exposed in the task
  listing for the client to display.
- The `meets_min_words` flag is computed *after* grading, only as a response field.

## Notes
`app/assessment/api.py` line 83 checks `body.text.strip()` for empty but has no
check against `min_words` or `max_words` from the task data before calling
`grader.grade()`. With an operational LLM, every too-short or too-long submission
would consume tokens for a result that is knowably non-conforming. Severity is
medium because it wastes limited daily AI budget and the fix is a few lines of
validation before the grader call.

## Triage
- Explanation: `app/assessment/api.py` submit endpoint (line 83-84) only checks for empty string. The task's `min_words` and `max_words` from `row.data` are never consulted before calling `grader.grade()`. The `meets_min_words` flag is computed post-grading (line 124) as a response field only. With an operational LLM provider, every under/over-length submission burns tokens needlessly.
- Against spec: The spec (Phase 3 ACs) does not explicitly mandate server-side word count rejection, but the task schema exposes `min_words`/`max_words` as constraints, and the platform's cost goal (single-digit USD/month, AC1.5 daily budget enforcement) makes it unreasonable to spend AI budget on knowably invalid submissions.
- Verdict: validated
- Rationale: Real bug with concrete user impact -- wastes limited daily AI token budget on submissions that are provably out of bounds. The fix is a few lines of validation before the grader call. A user who exhausts their daily budget on junk submissions loses their chance to get real feedback.

## Critic
- Challenge: The spec (Phase 3) does not mandate server-side word count rejection. AC1.5's daily budget enforcement already works -- `over_budget` is checked at line 99 and returns a graceful response. The budget system is the designed throttle against waste. A user who sends junk burns their own allocation, which is self-inflicted. The min_words/max_words fields exist in the task schema as client-facing guidance, not necessarily as server-enforced gates. Adding server-side validation adds complexity for an edge case the budget cap already handles.
- Holds up? Yes, partially. The budget cap prevents runaway cost (AC1.5 is satisfied), so the system is not "broken." However, the task schema defines concrete constraints (min_words=40) that the server advertises but never enforces. A 2-word submission sent to an LLM is a knowable waste of budget -- the server has all the information needed to reject it before the grader call. More importantly, a user who burns their daily budget on obviously invalid submissions loses their chance at real feedback, which is a real UX harm. The fix is trivially simple (a few lines of comparison before the grader call) and does not add meaningful complexity. The PM's reasoning holds.
- Final verdict: validated

Fix: Validate word count against min_words/max_words before calling LLM grader, return 422 if out of bounds (app/assessment/api.py, tests/test_assessment.py)
