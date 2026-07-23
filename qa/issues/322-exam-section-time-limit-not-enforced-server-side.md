---
id: 322
title: Exam section time limits exist in blueprint but are never enforced server-side
severity: medium
area: exam
persona: edge-case-breaker
status: deferred
found: 2026-07-22
---

## Steps to reproduce
1. Sign up and obtain a valid JWT token.
2. Start a mock exam: `POST /exam/start` with `{"blueprint_id":"mock-1"}`.
3. Note the blueprint response includes `time_limit_seconds` per section (e.g. `"time_limit_seconds":3600` for reading, `900` for speaking).
4. Wait far beyond the time limit (or just ignore it), then submit the section:
   ```
   curl -X POST https://<host>/exam/<attempt_id>/section \
     -H "Authorization: Bearer <token>" \
     -H "Content-Type: application/json" \
     -d '{"skill":"reading","correct":10,"total":10}'
   ```
5. Observe HTTP 200 and normal CLB score — no time-over penalty applied.

## Expected
Either:
- The server accepts an `elapsed_seconds` field in the section body and marks sections submitted over the time limit (parallel to comprehension's `over_time` flag and XP gate), **or**
- The server compares the section submission timestamp against `started_at + sum-of-prior-time-limits` and rejects/flags overruns.

## Actual
The `SectionResultBody` model has no `elapsed_seconds` field. The exam section endpoint completely ignores time limits — a user who takes 10 hours per section gets the same result as one who finishes in the allotted time. The `time_limit_seconds` values in the blueprint are display-only metadata.

## Notes
- Confirmed live on the remote deployment 2026-07-22.
- The comprehension endpoint (`POST /comprehension/sets/{set_id}/submit`) does track `elapsed_seconds` and sets `over_time=true` (blocking XP) when exceeded. The exam section endpoint has no equivalent.
- For a practice platform the impact is self-inflicted and low-stakes, but the blueprint prominently advertises time limits that are purely cosmetic. Users who "pass" under pressure may find real TEF exam time limits surprising.
- Severity is medium: exam integrity is a stated feature (TEF Canada prep), and the time pressure is a key differentiator between a mock exam and a regular lesson.

## Triage
- Explanation: SectionResultBody carries no elapsed_seconds and `time_limit_seconds` is display-only; section submit never checks elapsed time.
- Against spec: consistent with the app's client-trust timing model (comprehension uses a client-reported elapsed_seconds; exam sections collect none). Server-side enforcement needs a client change to report elapsed per section.
- Verdict: deferred
- Rationale: real gap but an enhancement requiring full-stack work + a product decision (hard cutoff vs. an over_time flag like comprehension); out of scope for this hardening round.

## Critic
- Challenge: is unenforced timing a correctness bug?
- Holds up as deferred? Yes — practice exam, no score-integrity impact; enhancement, not a defect.
- Final verdict: deferred
