# QA round 011 — plan

- date: 2026-06-21
- app under test: backend :9000 / SPA :5173
- scope: maintainability + integrity — do the **migrations round-trip**, is **content
  sync idempotent**, and does the **speech** path degrade cleanly (the round-8 H1 case I
  hit with the wrong body shape)?

## Change surface (highest risk first)
- Migration 0009 was added mid-project; nobody has exercised the full downgrade path.
- Content/comprehension/exam sync run on every deploy — re-running must not duplicate.

## Hypotheses (ranked)
| # | area | hypothesis | how to probe | persona |
|---|------|------------|--------------|---------|
| H1 | migrations | A downgrade is broken — `upgrade head → downgrade base → upgrade head` fails | run it on a throwaway DB | edge-case-breaker |
| H2 | content | Re-running sync **duplicates** rows or errors | sync a1 twice on a fresh DB, compare counts | edge-case-breaker |
| H3 | speech | `speech/turn` 500s / leaks instead of a clean 503 when STT is unconfigured | POST a proper multipart turn | edge-case-breaker |

## Coverage gaps
No issue history: migration reversibility, sync idempotency, speech degradation.

## Charters (per tester, with id blocks)
- `edge-case-breaker` (ids 190–199): chase H1–H3.

## Don't re-file (already settled)
- 007, 030, 071, 102, 131, 181 — rejected. 001, 050, 180 — deferred.
- 006, 010, 040, 070, 100, 101, 130, 150, 170 — fixed.
- Drill / Writing / Speaking 503 with no provider — expected (H3 tests the handling).

## Outcome (after the round) — CLEAN ROUND, 0 bugs
- **H1 — refuted.** `upgrade head → downgrade base → upgrade head` succeeds, ending at
  `0009_comprehension_pass (head)`. Every downgrade is reversible.
- **H2 — refuted.** Two a1 syncs → identical counts (2 units, 2 lessons). Idempotent.
- **H3 — refuted.** `speech/turn` (multipart) → `503 "speech is not configured"`. Clean
  degradation, completing the round-8 resilience picture (tutor + assessment + speech).

No issues filed — maintainability and degradation surfaces are sound.