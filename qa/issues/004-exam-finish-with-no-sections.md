---
id: 004
title: A mock exam can be "finished" with zero sections, giving a meaningless CLB report
severity: medium
area: exam
persona: exam-crammer
status: open
found: 2026-06-16
---

## Steps to reproduce
1. `POST /exam/start {"blueprint_id":"mock-1"}` → get `attempt_id`.
2. Immediately `POST /exam/{attempt_id}/finish` (record no sections).

## Expected
Either block finishing an exam with no recorded sections (409 / "record at least
one section"), or clearly mark the result incomplete — not present it as a result.

## Actual
`HTTP 200` with `report: {per_skill: {}, overall: null, target_met: false, note: …}`
and the attempt is marked `finished`. It shows up in history as a finished mock
with a null overall — looks like a real (failed) result.

## Notes
`finish` aggregates whatever's in `sections` with no completeness check. Consider
requiring all blueprint sections (or ≥1) before finishing, and/or a
`complete: false` flag in the report when sections are missing.
