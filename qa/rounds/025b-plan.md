# QA round 025b — plan (continuation of 025)

- date: 2026-06-25
- app under test: backend :9000 / SPA :5173
- scope: PR #20 `level-switcher` — continuation round. Verify fixes for 391/392/393, then probe remaining risk surfaces not covered in round 025.

## Context
Round 025 filed three issues (391, 392, 393) and hit a session limit before PM/critic could run. The user self-triaged and fixed all three in commit f94e0a6. This round:
1. Verifies the three fixes hold (PM + critic gate on existing issue files).
2. Probes the risk areas round 025 did not reach.

## Change surface (highest risk first)
1. `web/src/level.tsx` — LevelProvider seeding logic: localStorage > me.level > first available; clamping when stored level not in available set; graceful fallback on fetch failure
2. `web/src/screens/Exam.tsx` — fixed: [level] effect now resets attempt/recorded/report/error (391 fix)
3. `web/src/screens/Drill.tsx` — fixed: shows "A1 only" note when off-level (392 fix)
4. `web/src/api.ts` — ExamAttemptSummary gained `level` field (393 fix)
5. `app/content/api.py` — `GET /content/levels`: returns distinct levels from ContentUnit, CEFR-sorted, auth-gated
6. All screens (Path, Comprehension, Writing, Exam) refactored to useLevel()

## Hypotheses (ranked)

| # | area | hypothesis | how to probe | persona |
|---|------|------------|--------------|---------|
| H1 | level.tsx | If /content/levels or /progress/me fails (network error, 401), the provider might crash instead of defaulting to a1 | Revoke token / kill endpoint mid-load; verify no crash, fallback to a1 | edge-case-breaker |
| H2 | level.tsx | If localStorage has a level no longer in the available set (e.g. "b2"), seeding might pick an invalid level instead of clamping to the first available | Set localStorage tef.level=b2 and reload; verify it clamps to a1 | edge-case-breaker |
| H3 | /content/levels | Endpoint might return duplicates if a level has multiple units, or wrong ordering, or allow unauthenticated access | Call unauthenticated; call with auth and inspect ordering + uniqueness | edge-case-breaker |
| H4 | screens | Switching to A2 might not actually change content on some screens — Path/Comprehension/Writing might still show A1 data (the API call passes level, but does the screen re-render?) | Switch to A2, verify each screen shows A2-specific items (units, comp sets, writing tasks) | returning-learner |
| H5 | deep links | Navigating directly to /lesson/<a2-lesson-id> or /comprehension/<a2-set> might fail or show wrong-level content if the context level is still a1 | Grab an A2 lesson ID and navigate directly while on a1 | edge-case-breaker |
| H6 | regression | A1 flows across all screens (Path, Comprehension, Writing, Exam, Drill, Vocab) might regress with the new LevelProvider wrapping | Run a1 happy path through Path + lesson + comprehension + vocab | returning-learner |
| H7 | vocab | Vocab decks span levels — the Decks screen should NOT be filtered by level context (it fetches all cards). Verify level switching doesn't affect displayed vocab. | Switch between a1/a2 while on vocab screen; verify cards from both levels always show | returning-learner |
| H8 | exam history | examHistory() has no level filter param — it returns all attempts across levels. Verify the level label (393 fix) correctly appears and distinguishes entries | Create attempts at both a1 and a2, view history | edge-case-breaker |

## Coverage gaps
- `GET /content/levels` — no prior issue history; new endpoint deserving validation
- Level provider seeding/clamping logic — never tested in prior rounds
- Deep-linked sub-routes across levels — untested
- Rapid level switching (race conditions in useEffect) — untested
- Vocab screen interaction with level context — untested

## Charters (per tester, with id blocks)

- `edge-case-breaker` (ids 394–399): Chase H1 (provider failure/fallback), H2 (stale localStorage clamping), H3 (/content/levels validation), H5 (deep links), H8 (exam history labels). Also verify fixes 391/392/393 hold by exercising the exact repro steps from those issues. **Do not re-file 391/392/393** — they are fixed.

- `returning-learner` (ids 400–409): Chase H4 (A2 content actually loads), H6 (A1 regression), H7 (vocab unaffected by level switch). Happy-path the level switcher: switch to A2, see A2 path/comp/writing, switch back to A1, verify everything still works. Check persistence across page reload.

## Don't re-file (already settled)
- 391 exam stale state on level switch — done (fixed)
- 392 drill hardcodes a1 — done (partial/by-design; "A1 only" note added)
- 393 exam history missing level label — done (fixed)
- 251 exam history ignores level filter — rejected
- 102 exam CLB estimate clamped — rejected
- 131 password no max length — rejected
- 181 locked lesson content readable — rejected
- 180 comprehension feedback reveals answers — deferred
- 221 comprehension pass threshold not shown — deferred
- 290 SRS queue negative limit — rejected
- 300 vocab known accepts string bool — rejected
- 320 e2e reuse server — rejected
- 330 vocab deck stale comment — rejected
- 370/371 writing tasks — rejected
- Drill / Writing / Speaking 503 with no LLM provider — expected (needs Ollama)
- Drill backend is a1-only (drill_a1 profile) — by design, full multi-level drill is a logged follow-up

<!-- After the round, the planner notes each hypothesis: confirmed / refuted / untested. -->
