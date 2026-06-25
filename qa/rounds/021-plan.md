# QA round 021 — plan

- date: 2026-06-24
- app under test: backend :9000
- scope: PR #13 `content/deepen-vocab` — +160 vocab cards across A1+A2, wired into review lessons, +160 TTS clips. No app code changes.

## Change surface (highest risk first)
Single commit `7a793e5` touching only `content/`:
1. **20 vocab YAML files** (10 A1 + 10 A2): each gained 8 new cards (+80 per level, +160 total). Schema: `{id, fr, en, pos, tags}`.
2. **20 lesson YAML files** (10 A1 `-03` reviews + 10 A2 `-03` reviews): `new_vocab` changed from `[]` (or short list) to include the 8 new ids per theme. `restaurant-02` also grew (food deck rides on it).
3. **160 new MP3 audio clips** under `content/a1/audio/` and `content/a2/audio/`.
4. **No `app/` or `web/` code changes** — risk is purely data integrity, reference correctness, and API surface reflecting the new content correctly.

## Hypotheses (ranked)

| # | area | hypothesis | how to probe | persona |
|---|------|------------|--------------|---------|
| H1 | vocab-id uniqueness | With +160 ids across 20 files and 2 levels, a duplicate id may have slipped in (within a file, across files in a level, or across A1+A2). Duplicate ids would break FSRS card keys. | Run `test_all_levels.py` uniqueness assertions; also script a raw YAML scan for dupes. | edge-case-breaker |
| H2 | lesson ref integrity | Each lesson's `new_vocab` list references ids that must exist in a vocab file for that level. A typo or id mismatch would cause `_check_references` to fail silently or the loader to skip the card. | Load both levels via the loader; call `GET /content/lessons/{id}` for each changed lesson and verify the new_vocab ids appear in vocab endpoint. | edge-case-breaker |
| H3 | SRS seeding | Completing a deepened review lesson (e.g. `cafe-03`) should seed the 8 new vocab ids into the user's SRS queue via `seed_cards`. If seeding is broken, users complete the lesson but never review the words. | Register user, complete a `-03` lesson via API, then `GET /srs/queue` and verify all 8 card_keys appear. Re-complete and verify no duplicates. | returning-learner |
| H4 | audio serving | The 160 new MP3 files must serve via `GET /content/audio/{key}` with 200 and valid content. Missing or misnamed files would break pronunciation playback. | Spot-check ~10 audio keys across both levels. Verify 200 + `audio/mpeg` content-type. Also test a bad key for 404/400. | edge-case-breaker |
| H5 | vocab API counts | `GET /content/vocab?level=a1` should now return 188 cards (was 108); a2 should return 180 (was 100). Each card should have a correct `audio` key. Tag filtering should still work. | Call the vocab endpoint with level filter and count; verify audio keys; filter by tag. | returning-learner |
| H6 | gating regression | Adding `new_vocab` to existing `-03` lessons must not change lesson ids, unit membership, or gating logic. Unit completion still requires all 3 lessons done. | Run `test_progress.py`; also manually check `GET /content/path` structure. | returning-learner |
| H7 | test suite green | All 127 pytest tests and 15 vitest tests must pass. The E2E suite reads A1 content but asserts subsets/regex, so growth should be safe. | `pytest -q` + `npx vitest run`. | edge-case-breaker |
| H8 | French accuracy | Spot-check ~10-15 new cards for correct fr/en pairing, accents (e.g. `glacon` id but `fr: "glacon"` vs proper `glaçon`), and level appropriateness. | Manual review of vocab YAML diffs. | returning-learner |

## Coverage gaps
- No prior issues have tested vocab loading at scale (only 300/310/311/330 touched vocab/SRS surface lightly).
- No prior issue tested lesson `new_vocab` wiring end-to-end through SRS seeding.
- Audio serving (`GET /content/audio/{key}`) has no issue history at all.

## Charters (per tester, with id blocks)

- **edge-case-breaker** (ids 340--349): chase H1, H2, H4, H7. Focus on data integrity: duplicate ids, broken references, missing audio files, and full test suite regression. Run the loader, the uniqueness checks, audio spot-checks, and `pytest -q`.

- **returning-learner** (ids 350--359): chase H3, H5, H6, H8. Focus on the user-facing behavior: complete a deepened lesson and verify SRS seeding, check vocab API counts and deck sizes, verify gating is unchanged, and spot-check French accuracy on ~10-15 new cards.

## Don't re-file (already settled)
- 001 invalid email -- deferred (product decision)
- 007 negative elapsed_seconds -- rejected
- 006 lesson gating not enforced server-side -- deferred
- 030 exam section re-record -- deferred
- 050 lesson score client-reported -- deferred
- 130/131 display-name/password no max length -- done
- 300 vocab known accepts string bool -- rejected
- 310/311 SRS add accepts empty/nonexistent card key -- rejected
- 330 vocab deck stale comment -- deferred
- Drill/Writing/Speaking 503 with no provider -- expected, don't file

<!-- After the round, the planner notes each hypothesis: confirmed / refuted / untested. -->
