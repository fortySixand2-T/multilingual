---
id: 005
title: Exam section accepts correct > total and silently reports CLB 9
severity: low
area: exam
persona: edge-case-breaker
status: open
found: 2026-06-16
---

## Steps to reproduce
1. Start a mock, then `POST /exam/{id}/section` with
   `{"skill":"reading","correct":50,"total":10}`.

## Expected
422 (correct cannot exceed total), or at least a fraction clamped sensibly.

## Actual
`HTTP 200` → `{"skill":"reading","clb":9}`. `correct/total = 5.0`, clamped to 1.0
by `clb_from_fraction`, yielding the top band — a nonsense input produces a
perfect score.

## Notes
Validate `0 <= correct <= total` (and `total > 0`) in the section endpoint /
`SectionResultBody`. Low severity (self-inflicted), but it pollutes the CLB report.
