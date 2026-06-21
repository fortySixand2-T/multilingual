# QA round 008 — plan

- date: 2026-06-20
- app under test: backend :9000 / SPA :5173
- scope: resilience + integrity round — does the app **degrade cleanly** when the AI
  provider is down, is the exam state machine safe under **concurrency**, and did the
  round-5 atomic-XP change **regress** any caller?

## Change surface (highest risk first)
- Round 5 rewrote `record_activity` to use an atomic SQL XP increment. Any caller that
  reads `prog.xp` after commit (with `expire_on_commit=False`) without a refresh would get
  a broken value — regression risk worth auditing.
- AI-backed routes (tutor, assessment, speech) depend on a provider that isn't reachable
  here; their failure handling is untested end-to-end.

## Hypotheses (ranked)
| # | area | hypothesis | how to probe | persona |
|---|------|------------|--------------|---------|
| H1 | resilience | An AI-backed endpoint returns an ugly **500 / stack trace** (not a clean 503) when no provider is reachable | POST tutor/drill, assessment submit, speech turn | edge-case-breaker |
| H2 | exam | Concurrent `finish` of one attempt **500s or yields an inconsistent report** | record all sections, fire 5 parallel finishes | exam-crammer |
| H3 | progress | The round-5 atomic-XP change **regressed** an XP caller (broken value / 500) | audit every `record_activity` caller; exercise lesson + comprehension XP | edge-case-breaker |
| H4 | exam | The attempt state machine is leaky — a section can be **recorded after finish** | record a section on a finished attempt | edge-case-breaker |

## Coverage gaps
No issue history: AI-down degradation, exam finish under concurrency, regression of the
round-5 write-path change.

## Charters (per tester, with id blocks)
- `edge-case-breaker` (ids 160–169): chase H1, H3, H4.
- `exam-crammer` (ids 170–179): chase H2.

## Don't re-file (already settled)
- 007, 030, 071, 102, 131 — rejected. 001, 050 — deferred.
- 006, 010, 040, 070, 100, 101, 130, 150 — fixed.
- Drill / Writing / Speaking 503 with no provider — expected (H1 tests the *handling*).

## Outcome (after the round) — CLEAN ROUND, 0 bugs
- **H1 — refuted.** `tutor/drill` and `assessment/submit` both return a clean
  `503 "The AI service is temporarily unavailable…"`. (Speech needs a valid `audio`
  payload — a malformed body is a correct 422, not a crash.) Graceful degradation holds.
- **H2 — refuted.** 5 concurrent finishes → all 200, status `finished`, one coherent
  report (overall 7), zero 500s. `finish` is idempotent enough under concurrency.
- **H3 — refuted.** Only two callers (`progress`, `comprehension`); the progress path
  refreshes after commit, the comprehension path ignores the return. No regression.
- **H4 — refuted.** Recording a section on a finished attempt → `409`.

No issues filed — every hypothesis held. A round that finds nothing is a valid result:
it's evidence these areas are sound, recorded rather than dressed up as a fix.
