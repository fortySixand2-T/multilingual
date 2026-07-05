# QA round 036 — plan

- date: 2026-07-05
- app under test: backend :8080 / SPA :8080
- scope: Per-skill CLB readiness dashboard (student-help slice 2) — GET /exam/readiness + Readiness.tsx

## Change surface (highest risk first)

One commit on feat/readiness-dashboard (`4b37629`), touching:
- `app/exam/api.py` — new `GET /exam/readiness` route (aggregation logic: best/recent/trend per skill, weakest_skill, overall via aggregate_report)
- `web/src/screens/Readiness.tsx` — new screen (skill bars, weakest-skill focus nudge, trend text, empty state)
- `web/src/App.tsx` — new `/readiness` route + nav link
- `web/src/api.ts` — new `api.readiness()` + `Readiness` type
- `tests/test_exam.py` — 2 new readiness tests

## Hypotheses (ranked)

| # | area | hypothesis | how to probe | persona |
|---|------|------------|--------------|---------|
| H1 | aggregation | With ≥2 finished mocks at known CLBs, best/recent/trend might be wrong — e.g. best not being the true max, trend not in attempt-id order, or recent not being the last attempt's value. Most likely failure mode: off-by-one or ordering bug. | POST two mocks with known per-skill CLBs; verify best=max, recent=last, trend=chronological list | edge-case-breaker |
| H2 | regression case | recent < best (skill regressed between mocks) might not surface correctly — the code uses vals[-1] for recent which could be wrong if ordering is wrong | Drive attempt 1 CLB 8 → attempt 2 CLB 5 for a skill; confirm recent=5, best=8 | edge-case-breaker |
| H3 | target_met | target_met requires ALL skills' best ≥ 7; if ANY skill is < 7 it must be false. Easy to get wrong if aggregate_report logic is misapplied to the "best" dict | Drive a mock where all 4 skills best ≥ 7; confirm target_met true and weakest_skill still set to the min-best skill | edge-case-breaker |
| H4 | empty state | Fresh user (zero finished mocks) must return attempts=0, per_skill={}, overall=null, weakest_skill=null, target_clb=7. Also: an in-progress (unfinished) attempt must NOT count. | New signup + hit /exam/readiness; then start-but-don't-finish a mock and hit /exam/readiness again | edge-case-breaker |
| H5 | isolation | readiness only reflects the current user's attempts; user B sees empty readiness even if user A has finished mocks | Finish a mock as user A; log in as user B; verify /exam/readiness is empty for B | edge-case-breaker |
| H6 | auth | /exam/readiness might be missing auth guard (no token → 401) | Hit /exam/readiness without Authorization header | edge-case-breaker |
| H7 | regression | /exam/history, /exam/finish, and the full mock flow still work correctly after the new route was added | Run the standard mock flow end-to-end; check /exam/history returns correct data | edge-case-breaker |
| H8 | overall alignment | overall in readiness response must equal the weakest skill's best, consistent with aggregate_report's floor logic. If weakest_skill is speaking=6 and all others are ≥7, overall should be 6. | Cross-check overall == min(per_skill[s]["best"] for all s) | edge-case-breaker |
| H9 | pytest+ruff+web | New tests + lint + web build/npm test pass cleanly | Run full suite | edge-case-breaker |

## Coverage gaps

- No prior round has touched GET /exam/readiness (brand new endpoint, zero issue history).
- The Readiness.tsx screen is entirely new — no prior UI coverage.
- The "regression" scenario (recent < best) hasn't been tested in any prior round.
- The target_met=true path (all skills ≥ 7) hasn't been explicitly validated in previous rounds.

## Charters (per tester, with id blocks)

- `edge-case-breaker` (ids 447–456): Chase H1–H9. This is a small surface (one endpoint + one screen). Work through the hypotheses in order:
  1. Auth gate first (H6): `curl -s http://localhost:8080/exam/readiness` with no token.
  2. Empty state + in-progress non-count (H4): Sign up a fresh user (invite friend-001), hit /exam/readiness, start a mock, don't finish it, hit /exam/readiness again.
  3. Aggregation + regression case (H1, H2): As a fresh user, finish two mocks. Mock 1: reading=6, listening=7, writing=7, speaking=8. Mock 2: reading=8, listening=7, writing=7, speaking=5. Verify: reading best=8,recent=8,trend=[6,8]; speaking best=8,recent=5,trend=[8,5]; weakest_skill must be the skill with min best (speaking and reading are tied at 8, listening+writing at 7 — weakest is one of listening/writing); confirm overall=7 (floor of bests); target_met=false (7 < 7 fails — wait, 7 == 7 so target_met true if all ≥7). Adjust: use speaking=5 in mock 1, speaking=6 in mock 2 → best=6, weakest_skill=speaking, overall=6, target_met=false.
  4. target_met=true path (H3): Do a third mock or create a separate user where all 4 skills' bests ≥ 7.
  5. overall alignment check (H8): Cross-check overall == min(all best values).
  6. Isolation (H5): Sign up a second fresh user (invite friend-002), hit /exam/readiness — must be empty.
  7. Regression (H7): Verify /exam/history still lists all attempts for the first user; /exam/finish still produces the report.
  8. Pytest + ruff + web build (H9).
  - Blueprint: use "b2-mock-1" for mocks (it has 4 skills: reading/listening/writing/speaking). Reading/listening use correct/total; writing/speaking use clb_estimate.
  - CLB mapping reference: correct/10 → CLB: 6→6, 7→7, 8→8 (i.e. 6/10=0.6 → CLB 6, 7/10=0.7 → CLB 7, 8/10=0.8 → CLB 8).

## Don't re-file (already settled)

- 001 signup accepts invalid email — deferred
- 007 comprehension accepts negative elapsed — rejected
- 050 lesson score is client-reported — deferred
- 030 / 403 exam section rerecord overwrites — rejected
- 071 / 404 comprehension no-replay not enforced server-side — deferred
- 131 password no max length — deferred
- 181 locked lesson content readable — deferred
- 394 level-filtered endpoints accept empty string — deferred
- 418 mock exam stuck when LLM unavailable — deferred (503 expected)
- 428 lesson fail first_time — done (fixed in 777f223)
- Drill / Writing / Speaking 503 with no AI provider — expected
- Self-scored writing/speaking (user supplies clb_estimate) — by design (issue 418 rejected)

<!-- After the round, the planner notes each hypothesis: confirmed (→ issue NNN) /
     refuted (area sound) / untested. -->
