---
id: 342
title: Readiness endpoint aggregates CLB trends across different CEFR exam levels without separation
severity: medium
area: exam
persona: exam-crammer
status: deferred
found: 2026-07-22
---

## Steps to reproduce
1. Sign up as user `qa-crammer-2@qa.test`.
2. Complete a B1 mock exam (blueprint `b1-mock-1`) with section scores that yield CLB 6 for writing/speaking.
3. Complete a B2 mock exam (blueprint `b2-mock-3`) with section scores that yield CLB 8 for writing/speaking.
4. GET `/exam/readiness`

## Expected
The readiness response should either:
- Report trends separately per level (e.g., `per_skill.writing.trend_b1: [6]`, `per_skill.writing.trend_b2: [8]`), or
- At minimum, document in the response that the trend mixes attempts from different difficulty levels, or
- Accept a `?level=b2` filter to restrict the trend to a specific target level.

## Actual
The readiness endpoint mixes CLB scores from B1 and B2 exams into a single `trend` array per skill. For user `qa-crammer-2@qa.test`:
```json
{
  "per_skill": {
    "writing": {"best": 8, "recent": 8, "trend": [6, 8]},
    "speaking": {"best": 8, "recent": 8, "trend": [6, 8]}
  }
}
```
The trend `[6, 8]` shows writing "improving" from 6→8, but the 6 came from a B1 (easier) exam and the 8 from a B2 (harder) exam. These are not comparable CLB estimates — a CLB 6 on a B1 mock does not measure the same difficulty as a CLB 8 on a B2 mock. The "improvement" trend is meaningless cross-level.

## Notes
- `app/exam/api.py` `readiness()` (line 263-313) queries all `finished` ExamAttempt rows for the user with no level filter, then accumulates all per-skill CLB values into a flat series.
- A crammer preparing for TEF Canada at B2 would set their level to B2 and take B2 mocks. If they previously did a B1 warmup, the readiness view conflates the two, making the trend appear to show "growth" when it actually shows a level-switch artifact.
- The `overall` metric uses `min(best)` across all mixed-level best scores, which could also be inflated or deflated by the cross-level mixing.
- The `weakest_skill` calculated from mixed-level data may point to a skill that only looks weak because of an older lower-level attempt, not the user's actual current skill.

Severity: medium — the readiness dashboard is the primary tool for the exam-crammer persona to gauge their preparation. Cross-level CLB mixing produces misleading trends and overall scores that don't accurately reflect B2 readiness.

Found on live remote deployment: https://rohith-alienware-17-r4.tail592ffa.ts.net

## Triage
- Explanation: GET /exam/readiness aggregates CLB trends across all attempts regardless of CEFR level, so a B1→B2 switch looks like "improvement".
- Against spec: readiness has no `?level` filter or per-level breakdown. Real, but a presentation/feature enhancement.
- Verdict: deferred
- Rationale: needs a product decision on per-level readiness (endpoint shape + UI); out of scope for a fix-round.

## Critic
- Challenge: is the mixed trend misleading enough to be a bug?
- Holds up as deferred? Yes — meaningful enhancement (scope readiness by level), not broken behaviour.
- Final verdict: deferred
