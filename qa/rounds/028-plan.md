# QA round 028 — plan

- date: 2026-06-26
- app under test: backend :9000 / SPA :5173
- scope: PR #23 (b1-mock-golive) — B1 mock blueprints + go-live wiring

## Change surface (highest risk first)
What changed since the last round (from git diff origin/main...HEAD):
- 3 new B1 mock exam blueprints: `content/b1/exam/mock-{1,2,3}.yaml`
  - each a four-section timed mock (reading / listening / writing / speaking)
  - speaking sections contain brand-new free French text (6 prompts total)
- `tests/test_all_levels.py` — b1 promoted into `COMPLETE_LEVELS`
- `web/e2e/global-setup.ts` — e2e seed now syncs b1 alongside a1/a2

## Hypotheses (ranked)

| # | area | hypothesis | how to probe | persona |
|---|------|------------|--------------|---------|
| H1 | speaking prompts | The 6 new French speaking prompts may contain grammar errors, missing/wrong accents, register issues, or B2+ vocabulary that's inappropriate for B1 | Linguistically review each prompt for correctness, accent marks, register, CEFR B1-appropriateness | exam-crammer |
| H2 | mock composition | A blueprint's `comprehension_set_id` or `writing_task_id` may not resolve at runtime (dangling reference, wrong level, skill mismatch) | Start each B1 mock via the API; check that GET /exam/blueprints returns all 3 with correct structure; start one and verify sections load | exam-crammer |
| H3 | go-live wiring | With b1 seeded, GET /content/levels should return a1, a2, b1 in order; the level switcher should expose B1; content endpoints should serve B1 data | Hit /content/levels, /content/path?level=b1, /content/vocab?level=b1, /comprehension/sets?level=b1, /assessment/tasks?level=b1, /exam/blueprints?level=b1 | exam-crammer |
| H4 | mock-3 writing pairing | mock-3 reuses write-b1-remote-request (same as mock-2) + write-b1-social-media (same as mock-1). Both Section A+B pairing is valid, but test whether this creates any issue with the exam engine (e.g., duplicate task_id across mocks) | Start mock-3, verify writing section loads correctly despite shared task IDs | edge-case-breaker |
| H5 | regression a1/a2 | Adding b1 to the seed/sync loop might break a1/a2 exam flows or content endpoints | Run a1 mock start, check a1/a2 blueprints still load, check /content/levels still has a1+a2 | edge-case-breaker |
| H6 | exam flow end-to-end | A B1 mock can be started, all 4 sections submitted, finished, and produces a CLB report | Full mock lifecycle: start -> section (reading) -> section (listening) -> section (writing) -> section (speaking) -> finish -> check CLB report | exam-crammer |
| H7 | edge cases on B1 exam | Starting a B1 mock with invalid/missing section data, finishing without all sections, double-finishing, etc. | Attempt pathological flows: finish before sections, submit section for wrong skill, double-start | edge-case-breaker |

## Coverage gaps
- B1 speaking prompts have never been tested (brand new free text)
- B1 mock exam end-to-end flow (new blueprints, first time synced)
- Level switcher with 3 levels (previously only a1+a2)

## Charters (per tester, with id blocks)

- `exam-crammer` (ids 403-412): chase H1, H2, H3, H6
  - French language review of all 6 speaking prompts (H1 is top priority)
  - Verify all 3 B1 blueprints load and reference valid content (H2)
  - Test go-live wiring: /content/levels returns b1, level switcher works (H3)
  - Run a full B1 mock lifecycle end-to-end (H6)

- `edge-case-breaker` (ids 413-422): chase H4, H5, H7
  - Test mock-3 with shared writing task IDs across mocks (H4)
  - Regression: a1/a2 blueprints and content still work (H5)
  - Pathological exam flows: double-finish, missing sections, wrong skill (H7)

## Don't re-file (already settled)
- 001 signup accepts invalid email — deferred (product decision)
- 007 comprehension accepts negative elapsed — rejected (no impact)
- 050 lesson score is client-reported — deferred
- 030 exam section rerecord overwrites — rejected
- 071 comprehension no-replay not enforced — deferred
- 131 password no max length — deferred
- 102 exam CLB estimate clamped — rejected
- 181 locked lesson content readable — deferred
- 180 comprehension feedback reveals answers — deferred
- 221 comprehension pass threshold not shown — deferred
- 251 exam history ignores level filter — deferred
- 290 SRS queue negative limit — deferred
- 320 e2e reuse server — deferred
- 300 vocab known accepts string bool — rejected
- 330 vocab deck stale comment — rejected
- 370 new writing tasks not synced — rejected (by-design)
- 371 writing target vocab off-theme — rejected
- 394 level-filtered endpoints accept empty string — deferred
- 400 SRS queue vocab missing level field — done
- 401 match pairs en truncated — rejected
- 402 word bank global warming missing climatique — rejected
- Drill / Writing / Speaking 503 with no provider — expected (no Ollama profiles loaded)
- "B1 is shallow / only 6 units" — NOT a bug, vertical slice by design

## Outcome table

| # | hypothesis | result | issue | gate outcome |
|---|------------|--------|-------|--------------|
| H1 | French speaking prompts have errors | REFUTED — all 6 prompts correct (grammar, accents, register, B1-appropriate) | none | n/a |
| H2 | Blueprint references don't resolve | REFUTED — all 3 mocks load, all comprehension/writing refs resolve | none | n/a |
| H3 | Go-live wiring broken | REFUTED — /content/levels returns [a1,a2,b1], all B1 endpoints serve data | none | n/a |
| H4 | Shared writing task IDs cause conflicts | REFUTED — no conflict, sections stored per-attempt | none | n/a |
| H5 | a1/a2 regression | REFUTED — a1/a2 content, blueprints, and full mock flows all work | none | n/a |
| H6 | B1 mock can't run end-to-end | REFUTED — full lifecycle works: start, 4 sections, finish, CLB report | none | n/a |
| H7 | Pathological flows crash | REFUTED — all return clean 4xx (409/422/404/401) | none | n/a |

## Issues filed and gate results

| id | title | PM verdict | critic verdict | final |
|----|-------|-----------|----------------|-------|
| 403 | Exam section overwrite allows score gaming | rejected (dup of 030) | rejected | rejected |
| 404 | B1 listening sets all allow replay | validated | deferred (allow_replay client-only, no enforcer exists) | deferred |
| 405 | Mock-3 writing tasks all duplicated | validated (low) | rejected (rearranging is churn, real fix needs new tasks) | rejected |

**Round verdict: CLEAN.** Zero validated issues. All 7 hypotheses refuted -- the B1 go-live surface is sound.
