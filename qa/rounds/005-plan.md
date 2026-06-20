# QA round 005 — plan

- date: 2026-06-19
- app under test: backend :9000 / SPA :5173
- scope: exercise the exam **CLB report math** at its extremes, probe **report integrity**
  (sections outside the blueprint), test a **concurrency** race on XP, and check whether
  the "no-replay" listening promise is enforced server-side.

## Change surface (highest risk first)
- Round 4 touched comprehension XP gating — low regression risk (covered).
- Untested logic now: exam CLB aggregation (`aggregate_report`, `overall = min(bands)`),
  the section→blueprint relationship, and write-path atomicity (XP).

## Hypotheses (ranked)
| # | area | hypothesis | how to probe | persona |
|---|------|------------|--------------|---------|
| H1 | exam | CLB aggregation breaks at extremes — all-perfect doesn't yield target_met, or all-zero yields null/crash instead of a floor band | full mock all-correct, then a fresh mock all-zero → inspect report | exam-crammer |
| H2 | exam | A valid skill **not required by the blueprint** can be recorded and pollutes the report / drags `overall` | record an extra section for a skill the blueprint doesn't list → finish, inspect report | edge-case-breaker |
| H3 | comprehension | `allow_replay: false` is **not enforced server-side** — the audio/set can be re-fetched any number of times | GET `/comprehension/audio/{id}` twice for a no-replay set | edge-case-breaker |
| H4 | progress | **Concurrency**: two simultaneous lesson-result POSTs both pass the `_already_completed` check and **double-award XP** | fire two identical result POSTs in parallel, check xp | edge-case-breaker |
| H5 | progress | Streak/XP wrong across same-day lessons — second lesson bumps streak past 1 or mis-adds XP | complete two different lessons same day → xp += 10 each, streak stays 1 | returning-learner |

## Coverage gaps
No issue history: `aggregate_report` extremes, section-vs-blueprint validation, write-path
atomicity, server-side replay enforcement. H1/H2/H4 cover the highest-value gaps.

## Charters (per tester, with id blocks)
- `edge-case-breaker` (ids 070–079): chase H2, H3, H4.
- `exam-crammer` (ids 080–089): chase H1.
- `returning-learner` (ids 090–099): chase H5.

## Don't re-file (already settled)
- 007 negative elapsed — rejected; 001 email — deferred; 030 section redo — rejected;
  050 client-graded lessons — deferred.
- 006 gating, 010 board PII, 040 over-time XP — fixed.
- Drill / Writing / Speaking 503 with no provider — expected.

## Outcome (after the round)
- **H1 — refuted.** CLB aggregation is sound: all-perfect → per-skill 9/9/12/12,
  overall 9, target_met; all-zero → 3/3/1/1, overall 1, not met. No nulls/crashes.
- **H2 — refuted (moot).** `skill` is a typed enum and mock-1 requires all four skills,
  so there's no valid skill outside the blueprint to inject.
- **H3 — confirmed → issue 071 (rejected).** No-replay isn't server-enforced, but the
  gate ruled it client-enforced by design (no advantage, no shared-state harm).
- **H4 — confirmed → issue 070 (validated → fixed).** Concurrent duplicate completions
  500'd on the unique constraint (XP integrity held). Fixed with atomic insert-or-ignore.
- **H5 — refuted.** Two same-day lessons → xp 20, streak 1. Correct.

Net: 5 hypotheses → 2 confirmed, 3 refuted; 1 fixed (070, a real concurrency bug), 1
rejected (071). The 070 fix also hardened `UserProgress` creation and XP against races.
