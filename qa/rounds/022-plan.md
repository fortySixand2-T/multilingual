# QA round 022 — plan

- date: 2025-06-25
- app under test: backend :9000 / SPA :5173
- scope: PR #17 content/a2-new-themes — two new A2 units (Technology + Town & services), 26 vocab cards, 6 lessons, 26 audio clips, no app code changes

## Change surface (highest risk first)
Single commit `8c94aa0` adds content only — no `app/` or `web/src/` code changes.
1. **content/a2/vocab/tech.yaml** (13 cards) + **content/a2/vocab/ville.yaml** (13 cards)
2. **content/a2/lessons/tech-a2-{01,02,03}.yaml** + **ville-a2-{01,02,03}.yaml** (6 lessons, 30 exercises)
3. **content/a2/path.yaml** — appended `a2.u11` (Technology) + `a2.u12` (Town & services), gated sequentially after `a2.u10`
4. **content/a2/audio/*.mp3** — 26 new TTS clips

## Hypotheses (ranked)

| # | area | hypothesis | how to probe | persona |
|---|------|------------|--------------|---------|
| H1 | vocab id uniqueness | One of the 26 new ids might collide with an existing A1 or A2 id, since short common words like "ecole", "marche", "parc" exist | Run `test_all_levels.py`; grep all vocab files for dup ids | edge-case-breaker |
| H2 | lesson new_vocab refs | A `new_vocab` entry in a lesson might reference a vocab id that doesn't exist in the vocab files (typo, missing underscore) | Load content with `_check_references`; manually cross-check new_vocab lists against vocab file ids | edge-case-breaker |
| H3 | exercise correctness | mcq `answer` not in `options`; word_bank `answer` tokens not subset of `tokens`; match_pairs malformed | Parse all 6 lesson YAMLs and verify constraints programmatically | edge-case-breaker |
| H4 | unit gating | a2.u11 should be locked until a2.u10 is done; a2.u12 locked until a2.u11 is done; completing all 3 lessons in a unit unlocks the next | Sync content, complete lessons via API, verify gating at each step | returning-learner |
| H5 | SRS seeding from new lessons | Completing tech-a2-01 should seed its 5 new_vocab cards into SRS queue with correct card_keys and audio keys | Complete a new lesson via API, then GET /srs/queue and verify | returning-learner |
| H6 | audio serving | All 26 new clips should serve as valid MP3 via GET /content/audio/a2/audio/{id}.mp3 after content-sync | Sync a2, then curl each audio endpoint; check 200 + Content-Type | edge-case-breaker |
| H7 | vocab API + decks | GET /content/vocab?level=a2 should return 206 cards total; new cards should appear with correct audio keys and group into "tech" and "services" tag decks | Query vocab API after sync, check counts and filtering | returning-learner |
| H8 | regression - test suite | pytest (128 tests) should pass; vitest (15) should pass; E2E should pass (known flake in vocab-deck is pre-existing, not this PR) | Run full test suites | edge-case-breaker |
| H9 | French accuracy | Spot-check ~10 cards for wrong fr/en pairing, missing accents in `fr` field, or non-A2 vocabulary | Manual review of vocab YAML | returning-learner |
| H10 | word_bank answer token mismatch | word_bank exercises use accented tokens in `answer` (e.g. "telecharger" vs "telecharger") but `tokens` list might differ in accent usage — the `answer` tokens must be exact substrings of `tokens` | Parse each word_bank exercise and compare | edge-case-breaker |

## Coverage gaps
- New tag decks (`tech`, `services`) have never been tested via the vocab API filtering — no prior issues cover tag-based grouping.
- Audio serving for PR content was only recently fixed (issues 340, 350) — the fix path for new content on this branch needs re-verification.
- No prior round has tested the gating chain beyond u10.

## Charters (per tester, with id blocks)

- `edge-case-breaker` (ids 360-369): chase H1, H2, H3, H6, H8, H10.
  Focus: structural integrity of all 6 lessons and 26 vocab cards. Run the full test suite (pytest + vitest). Verify audio serving for all 26 clips after sync. Check for id collisions across A1+A2. Validate exercise constraints (mcq answer in options, word_bank answer subset of tokens, match_pairs well-formed).

- `returning-learner` (ids 370-379): chase H4, H5, H7, H9.
  Focus: progression flow through the two new units. Sign up a fresh user (invite `friend-001`), advance through A2 to unlock u11, complete tech-a2-01, verify SRS seeding with audio keys. Check vocab API returns 206 cards with new tech/services decks. Spot-check ~10 French translations for accuracy.

## Don't re-file (already settled)
- 001 signup accepts invalid email — deferred (product decision)
- 007 comprehension accepts negative elapsed — rejected
- 030 exam section re-record overwrites — rejected (by design)
- 050 lesson score is client-reported — deferred
- 071 comprehension no-replay not enforced — rejected
- 102 exam clb_estimate clamped — rejected
- 131 password no max length — rejected
- 180 comprehension feedback reveals answers — deferred
- 181 locked lesson content readable — rejected (by design)
- 221 comprehension pass threshold not shown — deferred
- 251 exam history ignores level filter — rejected
- 290 srs queue negative limit — rejected
- 300 vocab known accepts string bool — rejected
- 320 e2e reuse server — rejected (test infra)
- 330 vocab-deck stale comment — rejected (nit)
- 340 a2 audio not synced — done (fixed in round 010)
- 350 srs queue vocab missing audio key — done (fixed in round 010)
- Known E2E flake in `vocab-deck > add to review` — pre-existing, not caused by this PR

## Results

| # | hypothesis | result | issue |
|---|------------|--------|-------|
| H1 | vocab id uniqueness (collision with A1/A2) | REFUTED — all 26 ids globally unique, test_all_levels.py 11/11 pass | -- |
| H2 | lesson new_vocab refs broken | REFUTED — loader runs clean, all refs resolve | -- |
| H3 | exercise correctness (mcq/word_bank/match_pairs) | REFUTED — all 30 exercises structurally valid | -- |
| H4 | unit gating (u11/u12 chain) | REFUTED — gating works: u10 done unlocks u11, u11 done unlocks u12 | -- |
| H5 | SRS seeding from new lessons | REFUTED — tech-a2-01 seeds 5 cards with audio keys into /srs/queue | -- |
| H6 | audio serving (26 clips) | REFUTED — all 26 clips serve 200 with audio/mpeg after sync | -- |
| H7 | vocab API + decks (206 count, tech/services tags) | REFUTED — 206 cards returned, new tags present, audio keys populated | -- |
| H8 | regression test suite | REFUTED — pytest 128/128 pass, vitest 15/15 pass | -- |
| H9 | French accuracy | REFUTED — all 26 cards correct fr/en, proper accents, A2-appropriate | -- |
| H10 | word_bank token mismatch | REFUTED — all 6 word_bank answers are exact subsets of their tokens | -- |
