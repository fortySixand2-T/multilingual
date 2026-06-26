# QA round 025 — plan

- date: 2025-06-25
- app under test: backend :9000 / SPA :5173
- scope: PR #20 `level-switcher` — UI level switcher (LevelProvider/LevelSwitcher) + /content/levels endpoint + screen refactors to consume level from context

## Change surface (highest risk first)
1. `web/src/level.tsx` (new) — LevelProvider context, seeding logic (localStorage > me.level > first available), clamping, LevelSwitcher dropdown
2. `web/src/screens/{Path,Comprehension,Writing,Exam}.tsx` — refactored from hardcoded "a1" to useLevel(); each adds useEffect cleanup on level change
3. `app/content/api.py` — new `GET /content/levels` endpoint
4. `web/src/api.ts` — `api.levels()`
5. `web/src/App.tsx` — LevelProvider wrapping, switcher in topbar
6. `web/e2e/global-setup.ts` — seeds a1 + a2 content

## Hypotheses (ranked)

| # | area | hypothesis | how to probe | persona |
|---|------|------------|--------------|---------|
| H1 | Exam stale state | Exam.tsx does NOT clear `attempt`, `recorded`, `report`, or `error` when level changes (unlike Path/Comprehension/Writing which reset state). Switching levels mid-attempt or after finishing could show stale data from old level. | Switch level on Exam page mid-attempt and after viewing results; verify stale state doesn't persist | edge-case-breaker |
| H2 | Level seeding/fallback | If /content/levels or /progress/me fails, the provider should degrade to "a1" not crash. If localStorage has a level not in available list, it should clamp. | Call with expired token; clear localStorage and reload; set localStorage to "b2" (not available) and reload | edge-case-breaker |
| H3 | A2 content switching | Switching to A2 should show A2-specific path/comprehension/writing content, not A1. Content should actually change. | Switch to A2, verify path shows A2 units, comprehension shows A2 sets, writing shows A2 tasks | returning-learner |
| H4 | /content/levels correctness | Endpoint should return only levels with content, ordered a1<a2, no duplicates, require auth | Call unauthenticated; verify ordering; check no duplicates; add b1 content and verify it appears | edge-case-breaker |
| H5 | Switcher visibility | Switcher should be hidden when only 1 level has content; appear when >=2 | Check with only a1 content seeded vs a1+a2 | returning-learner |
| H6 | Drill isolation | Drill screen does NOT consume level context (intentional). Verify it still works on a1 and isn't broken by the LevelProvider wrapper. | Navigate to drill, start a session, confirm it works | returning-learner |
| H7 | Deep-linked routes | Navigating directly to /lesson/<a2-id>, /comprehension/<a2-set-id>, /writing/<a2-task-id> should work regardless of selected level | Access A2 lesson/set/task IDs directly via URL | edge-case-breaker |
| H8 | Persistence across reload | Selected level should survive page reload (localStorage), and switching should update localStorage immediately | Switch to A2, reload page, verify A2 still selected | returning-learner |

## Coverage gaps
- `GET /content/levels` — brand new endpoint, no prior issue history
- Level switcher UI — brand new component, no prior testing
- Cross-level state transitions — never tested before (was hardcoded a1)
- Vocab decks — span levels, should be unaffected by level context (Decks screen doesn't use useLevel)

## Charters (per tester, with id blocks)

- `edge-case-breaker` (ids 391-399): Chase H1 (Exam stale state on level switch), H2 (seeding/fallback edge cases), H4 (/content/levels auth + ordering + edge cases), H7 (deep-linked routes across levels). Focus on breaking the level-switching boundary conditions and the new endpoint.

- `returning-learner` (ids 400-409): Chase H3 (A2 content actually loads on switch), H5 (switcher visibility), H6 (Drill still works), H8 (persistence across reload). Focus on the happy-path switching experience and regression on existing flows.

## Don't re-file (already settled)
- 102 exam CLB estimate clamped — rejected
- 131 password no max length — rejected
- 181 locked lesson content readable — rejected
- 180 comprehension feedback reveals answers — deferred (product decision)
- 221 comprehension pass threshold not shown — deferred
- 251 exam history ignores level filter — rejected
- 290 SRS queue negative limit — rejected
- 300 vocab known accepts string bool — rejected
- 320 e2e reuse server bypasses db isolation — rejected
- 330 vocab deck stale comment — rejected
- 370 new writing tasks not synced — rejected
- 371 writing target vocab off-theme — rejected
- Drill / Writing / Speaking 503 with no LLM provider — expected (needs Ollama)

<!-- After the round, the planner notes each hypothesis: confirmed / refuted / untested. -->
