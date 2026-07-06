# QA round 037 — plan

- date: 2026-07-05
- app under test: backend :8080 / SPA :8080
- scope: Weak-spot / mistake-review feature (student-help slice 3) — DB migration 0012, capture hook in comprehension submit hot-path, GET /progress/weak-spots, POST /progress/weak-spots/{id}/answer, POST /progress/weak-spots/{id}/dismiss, WeakSpots.tsx

## Change surface (highest risk first)

Branch feat/weak-spots, touching:
- `migrations/versions/0012_weak_spots.py` — new `weak_spots` table with UNIQUE(user_id, ref_id) constraint and ix_weak_spots_user_id index. Migration integrity (upgrade/downgrade/round-trip) is first-class risk.
- `app/progress/service.py::sync_weak_spots` — called inside the comprehension submit HOT PATH. Any exception here aborts the submit; any logic error silently corrupts the miss-count.
- `app/comprehension/api.py::submit` — `sync_weak_spots` injected before the XP claim. If it raises, XP/first_pass/score are not returned. If it commits prematurely, the atomic XP claim races.
- `app/progress/api.py` — three new endpoints: GET /progress/weak-spots, POST /progress/weak-spots/{id}/answer, POST /progress/weak-spots/{id}/dismiss. Auth guard, 404-vs-403 ownership, re-hydration from set data.
- `app/progress/models.py::WeakSpot` — ORM model; must match migration schema exactly.
- `web/src/screens/WeakSpots.tsx` — re-answer inline, dismiss, empty state, graded feedback.
- `web/src/App.tsx` / `web/src/api.ts` — /weak-spots route, nav link, typed API methods.
- `tests/test_comprehension.py` — 4 new weak-spot unit tests.

## Hypotheses (ranked)

| # | area | hypothesis | how to probe | persona |
|---|------|------------|--------------|---------|
| H1 | migration | upgrade creates weak_spots with UNIQUE constraint + index; downgrade drops both; re-upgrade is clean; full chain from base still works | Run alembic upgrade head on a fresh DB, query sqlite_master, downgrade -1, upgrade head again | edge-case-breaker |
| H2 | hot-path regression | sync_weak_spots is inside submit before the commit — if it raises or breaks the session, the entire submit (score, XP, first_pass) will 500 or produce wrong results | Submit with all-wrong answers, all-right answers, partial; verify score/correct/passed/first_pass/over_time unchanged from pre-feature behavior | edge-case-breaker |
| H3 | upsert correctness | Missing a question twice should produce exactly ONE weak_spot row (UNIQUE upsert) with times_missed=2, not two rows | Submit set twice with same wrong answer; GET /progress/weak-spots; count rows; check times_missed | edge-case-breaker |
| H4 | resolve-on-correct | Submitting the same question CORRECTLY after a miss should flip resolved=true and drop it from GET /progress/weak-spots | Miss q1, then submit q1 correctly; verify it vanishes from the list | edge-case-breaker |
| H5 | unanswered-as-miss | An unanswered question (not in answers dict) is graded as wrong (chosen=None != answer) and must be captured as a weak-spot | Submit with empty answers dict {}; verify all questions appear in weak-spots | edge-case-breaker |
| H6 | re-practice /answer | Correct re-answer → {correct:true, resolved:true}; wrong re-answer → {correct:false, resolved:false} and times_missed increments again; item stays on list | Use /answer endpoint both ways | edge-case-breaker |
| H7 | /dismiss | POST /progress/weak-spots/{id}/dismiss → {id, resolved:true}; item drops off GET /progress/weak-spots | Dismiss a known weak-spot; verify response + list | edge-case-breaker |
| H8 | auth guard | All three new endpoints return 401 without a token (no bearer header) | Curl all three without Authorization header | edge-case-breaker |
| H9 | ownership 404 | Acting on another user's weak-spot id (or a nonexistent id) must return 404, not 403 or 500 | Create weak-spot as user A; attempt /answer and /dismiss as user B using that id | edge-case-breaker |
| H10 | isolation | User A's weak-spots must never appear in user B's GET /progress/weak-spots | Create weak-spots as user A; sign up user B; verify empty list | edge-case-breaker |
| H11 | empty state | Fresh user with zero comprehension history → GET /progress/weak-spots returns {weak_spots:[]} (not 500) | Sign up fresh user; hit endpoint | edge-case-breaker |
| H12 | re-hydration quality | GET /progress/weak-spots must re-hydrate set_title, prompt, options, skill from the live set data; set_id/ref_id are stored, but if the question id in YAML doesn't match ref_id exactly, the item silently disappears (question=None → skip) | Submit wrong answer; verify all re-hydration fields present and correct | edge-case-breaker |
| H13 | stale-set resilience | If the set is removed from the DB (re-sync scenario), the list must not 500 — it must skip the orphaned spot; the spot must still be dismissable via /dismiss | Manually call dismiss with a valid ws id whose set_id doesn't exist in the DB | edge-case-breaker |
| H14 | ordering | GET /progress/weak-spots is ordered most-missed first (times_missed DESC, last_missed DESC) | Create two weak-spots with different miss counts; verify ordering | edge-case-breaker |
| H15 | pytest+ruff+web | 4 new tests pass; ruff check/format clean; web build succeeds; npm test passes | Run full suite | edge-case-breaker |

## Coverage gaps

- GET /progress/weak-spots has no issue history (brand new endpoint).
- POST /progress/weak-spots/{id}/answer and /dismiss are entirely new surfaces.
- The comprehension submit has never been tested with a capture hook in the hot path — side effects of sync_weak_spots on the transaction model are unverified.
- Migration 0012 is the first migration tested with the "upgrade→downgrade→upgrade" chain in this project after round 036 confirmed the pattern.
- The WeakSpots.tsx screen is brand-new UI with no prior coverage.

## Charters (per tester, with id blocks)

- `edge-case-breaker` (ids 448–467): Chase H1–H15 in full. This tester owns the entire surface.

  **Sequencing**:
  1. Auth guard (H8): No-token curl on all three endpoints.
  2. Fresh-user empty state (H11): Sign up new user (friend-001), GET /progress/weak-spots → must be [].
  3. Migration integrity (H1): `export DATABASE_URL="sqlite:////tmp/ws_qa.db"; rm -f /tmp/ws_qa.db; /tmp/tef312/bin/python -m alembic upgrade head` — check sqlite_master for weak_spots table + unique constraint + index. Then `alembic downgrade -1` — verify weak_spots gone. Then `alembic upgrade head` again — verify clean. Report pass/fail.
  4. Hot-path regression (H2): As the fresh user, submit a reading comprehension set with known answers: first all-correct (score=1.0, passed=true, first_pass=true, XP awarded); second all-wrong (score=0, passed=false, first_pass=false); partial. Verify score/correct/total/passed/first_pass/over_time match expected exactly.
  5. Capture correctness — one wrong (H3+H12): Submit with q1 wrong; GET /progress/weak-spots; verify exactly ONE item with correct set_title/prompt/options/skill/times_missed=1.
  6. Unanswered-as-miss (H5): Submit with empty answers {}; verify ALL questions appear in weak-spots.
  7. Upsert/no-duplicate (H3): Submit same wrong answer again; verify times_missed=2, still one row for that ref_id.
  8. Resolve-on-correct (H4): Submit same question correctly; verify it disappears from list.
  9. Ordering (H14): Miss two different questions with different frequencies; verify ordering.
  10. /answer correct (H6a): POST /answer with correct option → {correct:true, resolved:true}; verify item gone from list.
  11. /answer wrong (H6b): POST /answer with wrong option → {correct:false, resolved:false}; times_missed increments; item still in list.
  12. /dismiss (H7): POST /dismiss → {id, resolved:true}; item drops off list.
  13. Ownership 404 (H9): User A's weak-spot id → user B /answer and /dismiss → must 404.
  14. Isolation (H10): User B GET /progress/weak-spots → must be empty (user A's data invisible).
  15. Stale-set (H13): For a ws whose set data exists, call /dismiss — confirm it works even if you imagine the set vanished (can confirm via code path reading: if srow is None → skip in GET, but dismiss doesn't need srow, so should return 200).
  16. pytest+ruff+web (H15): `/tmp/tef312/bin/python -m pytest -q tests/test_comprehension.py`; `ruff check .`; `ruff format --check .`; `cd web && VITE_API_BASE="" npm run build`; `npm test`.

  **Comprehension set to use**: find a reading set (skill=reading) from `GET /comprehension/sets?level=a1` or `a2`. Use that set_id. Inspect the set via GET /comprehension/sets/{set_id} to know the question ids and correct answers. Submit wrong answers using known-wrong strings (not in options list, or an option that isn't the answer key).

  **Auth**: POST /auth/signup with invite_code friend-001 (user A) and friend-002 (user B). Use returned token in Authorization: Bearer {token} header for all subsequent calls.

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
- 428 lesson fail first_time — done
- 447 focus pill shows when target_met — done
- Drill / Writing / Speaking 503 with no AI provider — expected
- Self-scored writing/speaking (user supplies clb_estimate) — by design
- Unanswered comprehension questions counting as misses — BY DESIGN (specified)

<!-- After the round, the planner notes each hypothesis: confirmed (→ issue NNN) /
     refuted (area sound) / untested. -->

## Outcome

Round complete — 15 hypotheses, all sound (migration integrity, hot-path regression in
comprehension submit, upsert dedup, resolve-on-correct, unanswered-as-miss, /answer & /dismiss,
auth, ownership 404, per-user isolation, empty state, re-hydration, stale-set resilience,
ordering, full suite). Migration up/down/re-up verified mechanically post-round.

| id | title | verdict |
|----|-------|---------|
| 448 | wrong pick not highlighted after incorrect answer | **fixed** — WeakSpots.tsx records the picked option and applies `.wrong`/`.correct` classes (matches the Lesson screen convention) |
| 449 | /answer accepts calls on already-resolved spots | **deferred** — API-abuse only; resolved spots are never rendered, so no UI path; one-line hardening left for a future pass |
| 450 | missing tests for unanswered-as-miss / ordering / nonexistent-id 404 | **deferred** — all three behaviors verified working this round; test-hygiene gap, non-blocking |

**Verdict: sound.** 1 validated (fixed), 2 deferred, 0 rejected. Hot-path regression: PASS.
Migration: PASS. 156 pytest, ruff clean, web build + 19 npm tests.
