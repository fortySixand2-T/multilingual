# QA round 035 — plan

- date: 2026-07-04
- app under test: backend :8080 / SPA :8080
- scope: Grammar reference index (student-help slice 1) — new GET /content/grammar endpoint + Grammar.tsx screen

## Change surface (highest risk first)

One commit on feat/grammar-reference (`08bad80`), touching:
- `app/content/api.py` — new `GET /content/grammar?level=` route
- `web/src/screens/Grammar.tsx` — new screen (grouped by unit, client-side search, lesson links)
- `web/src/App.tsx` — new `/grammar` route + nav link
- `web/src/api.ts` — new `api.grammar()` method + `GrammarItem` type
- `tests/test_content_sync.py` — 2 new grammar tests

## Hypotheses (ranked)

| # | area | hypothesis | how to probe | persona |
|---|------|------------|--------------|---------|
| H1 | ordering | Items returned by /content/grammar may not strictly follow path order — the code iterates `unit.lessons` list but that list could have a different ordering than `ContentUnit.ordinal` ascending | Cross-check grammar item unit_id sequence against /content/path unit order for a1, b1, b2 | edge-case-breaker |
| H2 | completeness | Lessons without `grammar_point` might still appear (empty-string vs None handling); or lessons WITH a grammar_point might be omitted if the data key differs in content YAML | Count grammar items per level vs manually counted lessons-with-grammar; spot-check lesson detail | edge-case-breaker |
| H3 | auth | /content/grammar might not enforce auth (missing Depends, copy-paste gap) | Hit endpoint without token → expect 401 | edge-case-breaker |
| H4 | edge params | Unknown level → 404 confirmed; but what about missing `level` param (422?), empty string `level=` (potentially 200 or 500 instead of 404) | Probe level=, level=xx, omit level | edge-case-breaker |
| H5 | regression | New route mounted at /content/grammar could accidentally shadow or conflict with /content/lessons/{id} if routing is greedy | GET /content/lessons/grammar → should 404 (no such lesson), not match grammar route | edge-case-breaker |
| H6 | frontend search | Client-side search filtering: searching for a substring of grammar_point, unit_title, or lesson_title should narrow results; empty search should restore all items; level-switch should refetch | Manually test search + level switch behavior in running SPA | edge-case-breaker |
| H7 | pytest+ruff+web | New tests + lint + web build pass cleanly | Run the full suite | edge-case-breaker |

## Coverage gaps

- No issue history exists for /content/grammar (brand new endpoint — no prior round touched it).
- The Grammar.tsx screen is entirely new — no prior UI coverage.
- Cross-level ordering hasn't been validated (a2, b1, b2 each could have different ordinal gaps).

## Charters (per tester, with id blocks)

- `edge-case-breaker` (ids 443–452): chase H1, H2, H3, H4, H5, H6, H7. This is a small surface — one focused tester is sufficient. Verify ordering for ALL four levels (a1/a2/b1/b2). Spot-check at least 2 lesson_ids via /content/lessons/{id} and confirm grammar_point matches. Run pytest + ruff + web build/test.

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

## Outcomes

- H1 — REFUTED (area sound): ordering correct for all four levels; unit ordinals never decreased in any response.
- H2 — CONFIRMED (partial, issue 443): A1 returned 30 items instead of 36 — two units (a1.u11, a1.u12) were never synced to the live DB after being added to path.yaml. Spot-checks of lesson_ids passed; grammar_point strings matched. Also confirmed test gap (issue 445): no count assertion existed to catch this class of omission in CI.
- H3 — REFUTED (area sound): 401 returned without token.
- H4 — REFUTED (area sound): unknown level → 404, missing param → 422, empty string → 404. All correct.
- H5 — REFUTED (area sound): /content/lessons/grammar → 404 (not routed to grammar endpoint); /content/lessons/greetings-01 → 200.
- H6 — REFUTED (area sound): search filtering, empty search restore, and level-switch refetch all worked correctly in the running SPA.
- H7 — REFUTED (area sound): pytest 23/23 passed (incl. 2 new grammar tests + added count assertion), ruff clean, web build successful (685ms), npm test 19/19 passed.
