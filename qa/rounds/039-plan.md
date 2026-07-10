# QA round 039 — plan

- date: 2026-07-09
- app under test: backend :8080 / SPA :8080
- scope: Hardening slice closing deferred issues 449/450/452 + light regression sweep
  of the four merged student-help features (grammar index, readiness, comprehension,
  drill tutor all-levels)

## Change surface (highest risk first)

Branch fix/deferred-qa-449-450-452, one commit on top of main, touching:

- `app/progress/api.py` — `answer_weak_spot` now raises HTTP 404 when `w.resolved`
  is True (the 449 guard). This is the primary change: highest risk because (a) it
  changes a previously-permissive path into a rejection, and (b) the guard sits in the
  same `_owned_weak_spot` helper used by /dismiss — any logic error here could break
  the normal open-spot flow (answer correct → resolve, answer wrong → increment count,
  dismiss → resolve) for active weak spots.
- `tests/test_comprehension.py` — four new tests: unanswered-questions-as-misses,
  most-missed-first ordering, nonexistent-id 404, resolved-spot answer → 404 (450+449
  coverage). Risk: user-id collisions with existing tests (new tests use 7101–7104) and
  incorrect test assumptions (e.g. relying on ordering of a fresh DB vs cumulative
  state).
- `tests/test_tutor_levelgate.py` — `_setup()` now loads all four levels (a1/a2/b1/b2);
  `test_drill_endpoint_derives_level_from_lesson` extended to assert a2 + b2 profiles
  (452 fix). Risk: a2/b2 content YAML must exist and load cleanly; cuisine-a2-01 and
  sciences-b2-01 must be in the DB before the test.

## Hypotheses (ranked)

| # | area | hypothesis | how to probe | persona |
|---|------|------------|--------------|---------|
| H1 | weak-spot 449 guard | POST /answer on a resolved spot must return 404 (not 200); times_missed must NOT change | Dismiss a spot, then POST /answer → assert 404; fetch DB count before/after via GET weak-spots (resolved included) | edge-case-breaker |
| H2 | weak-spot normal flow — not broken | The 449 guard must NOT break open-spot normal flow: answer correct → 200 + resolved:true; answer wrong → 200 + times_missed+1; dismiss → 200 + resolved:true | Run the normal happy path on a fresh open spot | edge-case-breaker |
| H3 | resolved-spot dismiss idempotency | POST /dismiss on an already-resolved spot should succeed (or at least not 500); 449 guard must not affect dismiss | Dismiss a spot twice, check second call status | edge-case-breaker |
| H4 | new tests — unanswered-as-misses | test_weak_spot_unanswered_questions_are_captured passes: empty answers dict → ALL questions captured as weak spots | Confirmed via pytest -q | edge-case-breaker |
| H5 | new tests — ordering | test_weak_spots_ordered_most_missed_first passes: two spots, most-missed returns first | Confirmed via pytest -q AND live HTTP ordering assertion | edge-case-breaker |
| H6 | new tests — nonexistent-id 404 | test_weak_spot_nonexistent_id_404 passes: /answer + /dismiss on id=999999 both return 404 | pytest -q + live curl | edge-case-breaker |
| H7 | 452 — a2/b2 HTTP level-derivation | test_drill_endpoint_derives_level_from_lesson now covers all four levels; cuisine-a2-01 routes drill_a2, sciences-b2-01 routes drill_b2 | pytest -q; also live HTTP: POST /tutor/drill for a2 and b2 lessons → 503 (not 400/500) | edge-case-breaker |
| H8 | regression — comprehension submit grades normally | A normal comprehension submit (all correct) still awards XP and returns graded responses; no 500 | POST /comprehension/sets/read-cafe-01/submit with correct answers | returning-learner |
| H9 | regression — grammar index | GET /content/grammar?level=a1 still returns grammar points | returning-learner |
| H10 | regression — readiness endpoint | GET /exam/readiness still returns skill breakdown | returning-learner |
| H11 | full suite | pytest -q (162 tests), ruff check, ruff format --check, web build, npm test all pass | run full suite | edge-case-breaker |

## Coverage gaps

- The /dismiss endpoint has no explicit test for the idempotent-on-already-resolved
  case (H3) — worth a quick live probe even if not previously filed.
- The four student-help features (grammar, readiness, comprehension, tutor) have no
  cross-feature state test: grammar fetched while a weak-spot drill is in progress.
  This is a blind spot but low priority given independent DB models.

## Charters (per tester, with id blocks)

- `edge-case-breaker` (ids 453–462): Primary tester. Chase H1–H7 and H11.
  Sequence:
  1. Auth: POST /auth/signup with friend-001; store token.
  2. H1+H2 (449 guard + normal flow):
     - Submit read-cafe-01 with wrong answers → create open spot.
     - GET /progress/weak-spots → note id and times_missed.
     - POST /answer on open spot with wrong choice → expect 200, times_missed+1.
     - POST /dismiss on that spot → expect 200, resolved:true.
     - POST /answer on now-resolved spot → expect 404 (guard).
     - Confirm times_missed did NOT change after the 404 call (GET via second user
       query or note before/after).
  3. H3 (dismiss idempotency): POST /dismiss again on the resolved spot → should not 500.
  4. H6 (nonexistent-id): POST /progress/weak-spots/999999/answer and /dismiss → expect 404 each.
  5. H7 (a2/b2 tutor live): POST /tutor/drill {lesson_id:"cuisine-a2-01"} → 503;
     POST /tutor/drill {lesson_id:"sciences-b2-01"} → 503; neither 400 nor 500.
  6. H4+H5 (ordering): confirm live HTTP — POST two submit payloads that make q1
     miss twice and q2 miss once; GET weak-spots; assert q1 first.
  7. H11 (full suite): pytest -q; ruff check .; ruff format --check .; web build; npm test.

- `returning-learner` (ids 463–469): Regression sweep. Chase H8, H9, H10.
  Sequence:
  1. Auth: fresh signup with friend-002.
  2. H8: POST /comprehension/sets/read-cafe-01/submit with correct answers;
     verify 200, scores graded, XP returned.
  3. H9: GET /content/grammar?level=a1 → expect 200 with grammar_points list.
  4. H10: GET /exam/readiness → expect 200 with skill breakdown.
  5. Flag anything unexpected (wrong status codes, empty responses, 500s).

## Don't re-file (already settled)

- 001 signup accepts invalid email — deferred
- 007 comprehension accepts negative elapsed — rejected
- 050 lesson score is client-reported — deferred
- 071 comprehension no-replay not enforced server-side — deferred
- 131 password no max length — deferred
- 181 locked lesson content readable — deferred
- 394 level-filtered endpoints accept empty string — deferred
- 418 mock exam stuck when LLM unavailable — deferred (503 expected)
- 451 api/tutor/api.py docstring still says "A1 drill" — rejected
- Drill / Writing / Speaking 503 with no AI provider — EXPECTED (healthy outcome)
- Unanswered comprehension questions counting as misses — by design

## Outcome

Round complete — 11 hypotheses, 10 refuted outright, 1 surfaced a real backend gap
that was deferred. Zero validated issues. Dev-fixer not run.

### Hypothesis results

| # | verdict | notes |
|---|---------|-------|
| H1 | refuted | POST /answer on resolved spot → 404 "weak spot already resolved". Guard fires correctly. times_missed confirmed unchanged. |
| H2 | refuted | Normal open-spot flow intact: wrong answer → 200 + times_missed+1; correct answer → 200 + resolved:true; dismiss → 200 + resolved:true. |
| H3 | refuted | Second POST /dismiss on already-resolved spot → 200 (idempotent). No 500. |
| H4 | refuted | test_weak_spot_unanswered_questions_are_captured passes: empty {"answers":{}} → all questions captured as weak spots. |
| H5 | refuted | test_weak_spots_ordered_most_missed_first passes; live HTTP confirmed q1 (times_missed=2) before q2 (times_missed=1). |
| H6 | refuted | POST /progress/weak-spots/999999/answer → 404; POST /999999/dismiss → 404. |
| H7 | refuted | cuisine-a2-01 → 503; sciences-b2-01 → 503. Both clean, not 400/500. All four levels assert drill profile correctly in pytest. |
| H8 | refuted | Comprehension submit grades correctly; score/pass/first_pass/results all present. No 500. |
| H9 | refuted | GET /content/grammar?level=a1 → 200 with 36 grammar points across 12 units. B1 new themes present. |
| H10 | refuted | GET /exam/readiness → 200 with structurally correct response for a fresh user. |
| H11 | refuted | 162 pytest passed (0 failures); ruff check clean (112 files); ruff format clean; web build 724ms; npm test 19/19. |

### Issues filed

| id | title | final verdict |
|----|-------|---------------|
| 463 | Comprehension submit response missing xp and streak fields | deferred — backend omission confirmed, but `CompResult` TS type has no xp/streak fields and the UI renders a hardcoded "+15 XP" string from first_pass; fixing only the backend returns fields the frontend ignores; full-stack scope needed before this is actionable |

### Suite results

| check | result |
|-------|--------|
| pytest -q | 162 passed, 0 failed, 5 warnings |
| ruff check . | all checks passed |
| ruff format --check . | 112 files already formatted |
| web build (tsc + vite) | success (724ms) |
| npm test | 19/19 passed |

**Verdict: sound. 0 validated, 0 rejected, 1 deferred. Branch is ready for PR.**

The three target deferred issues (449, 450, 452) are confirmed closed by this branch:
- 449 guard fires correctly (404 on resolved spot); normal flow unaffected.
- 450 new tests all pass (unanswered-as-misses, ordering, nonexistent-id 404, resolved-spot 404).
- 452 a2/b2 HTTP level-derivation now covered at all four levels in pytest.
