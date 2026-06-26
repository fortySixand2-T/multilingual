# QA round 026 — plan

- date: 2026-06-25
- app under test: backend :9000
- scope: B1 vertical slice (PR #21) — 6-unit learn path, 72 vocab cards, 18 lessons, 72 audio clips

## Change surface (highest risk first)

1. **18 lesson YAML files** — 90 exercises across 5 types (mcq, translate, listen_type, word_bank, match_pairs). Hand-authored French at B1 level: accents, conjugations, gender agreement, answer correctness.
2. **6 vocab deck YAMLs** — 72 cards; ids are FSRS primary keys and must be globally unique vs a1/a2.
3. **path.yaml** — 6-unit linear chain with `unlock: all_of` gating.
4. **72 TTS audio clips** — every listen_type exercise references one; file must exist.
5. **tests/test_all_levels.py** — relaxed per-skill validation for incomplete levels; new `COMPLETE_LEVELS` guard for a1/a2.

## Hypotheses (ranked)

| # | area | hypothesis | how to probe | persona |
|---|------|------------|--------------|---------|
| H1 | French correctness | Some translate/mcq answers have wrong accents, missing articles, or incorrect conjugation — hand-authored B1 grammar (subjonctif, futur simple, conditionnel, comparatives) is error-prone | Audit every exercise answer vs its prompt; check each vocab `fr` field for missing diacritics; verify conjugation forms claimed in grammar_point | edge-case-breaker |
| H2 | exercise integrity — word_bank | A word_bank `answer` token might not appear in `tokens` (multiset violation), or the sentence might be ungrammatical | For each word_bank exercise, verify `answer` is a subset of `tokens`; check the built sentence is correct French | edge-case-breaker |
| H3 | exercise integrity — mcq | An mcq `answer` might not be in `options`, or all distractors might be obviously wrong (no learning value) | Verify `answer in options` for every mcq; spot-check distractor plausibility | edge-case-breaker |
| H4 | listen_type audio_ref resolution | An `audio_ref` might reference a file that doesn't exist, or the `answer` field might not match the vocab `fr` form (accent mismatch) | Cross-reference every listen_type `audio_ref` against `content/b1/audio/`; compare `answer` to the vocab deck `fr` | edge-case-breaker |
| H5 | vocab coverage gaps | Some of the 12 vocab ids in a deck might not appear in any of that unit's 3 lessons' `new_vocab`, leaving cards that never get seeded | Union each unit's 3 lessons' new_vocab and diff vs its deck | edge-case-breaker |
| H6 | vocab id collision | A b1 vocab id might collide with an a1/a2 id, corrupting FSRS state | Already pre-checked (no collisions found); testers should verify programmatically | returning-learner |
| H7 | path gating chain | Completing u1's lessons should unlock u2 but not u3; the unlock chain should work end-to-end | Walk the path.yaml chain; hit the API for path status after lesson completion | returning-learner |
| H8 | content-sync + API | `content-sync b1` might fail; `/content/levels` might not list b1; `/content/vocab?level=b1` might be empty | Run sync, then query the endpoints | returning-learner |
| H9 | test relaxation regression | The COMPLETE_LEVELS guard might have been set too narrowly — if a future level is added to COMPLETE_LEVELS it should still enforce all skills | Review the test code; verify a1/a2 still have the full skill check | returning-learner |
| H10 | match_pairs well-formedness | A match_pairs exercise might have a French key that doesn't match the vocab `fr` form (accent mismatch between lesson and deck) | Compare every match_pairs French-side entry to the vocab deck `fr` field | edge-case-breaker |

## Coverage gaps

- B1 content-sync end-to-end has never been tested (new level).
- No prior QA on word_bank token/answer multiset validation for B1.
- B1 path gating with `all_of` (prior rounds tested a1/a2 `none` gating only).
- The `realiser` vocab entry is tagged `verb` (only verb in all B1 decks) — check it works in the noun-oriented pipeline.

## Charters (per tester, with id blocks)

- **edge-case-breaker** (ids 401-419): Chase H1, H2, H3, H4, H5, H10. Primary focus: audit every single exercise in all 18 lessons for French correctness (accents, conjugation, gender), exercise type integrity (word_bank subset, mcq answer-in-options, match_pairs form matching), and audio_ref resolution. This is a content audit -- go through every YAML file systematically.

- **returning-learner** (ids 420-429): Chase H6, H7, H8, H9. Focus: run content-sync for b1 and verify API endpoints respond correctly; walk the path gating chain; verify vocab global uniqueness programmatically; review the test relaxation for soundness; check that a1/a2 are unaffected.

## Don't re-file (already settled)

- 001 invalid email -- deferred
- 007 negative elapsed_seconds -- rejected
- 050 lesson score client-reported -- rejected
- 131 password no max length -- deferred
- 181 locked lesson content readable -- rejected
- 251 exam history ignores level filter -- rejected
- 330 vocab deck stale comment -- rejected
- 371 writing target vocab off-theme -- rejected
- 394 empty-string level accepted -- rejected
- B1 missing comprehension/writing/exam -- intentionally not content-complete (by design for this slice)
- Drill / Writing / Speaking 503 with no provider -- expected

## Outcome

| # | hypothesis | result | notes |
|---|------------|--------|-------|
| H1 | French correctness | refuted | All 90 exercises audited: accents, conjugations (subjonctif dormes/prennes, futur realiserai, conditionnel devrais, comparatives plus...que), gender agreement all correct |
| H2 | word_bank integrity | refuted | All 18 word_bank exercises: every answer token present in tokens list; built sentences grammatically correct |
| H3 | mcq integrity | refuted | All 18 mcq exercises: answer in options; distractors plausible |
| H4 | listen_type audio_ref | refuted | All 18 audio_refs resolve to existing files; answer matches vocab fr field |
| H5 | vocab coverage | refuted | All 6 units: union of 3 lessons' new_vocab = 12 deck ids (complete coverage) |
| H6 | vocab id collision | refuted | 492 total vocab ids across a1/a2/b1, zero collisions |
| H7 | path gating chain | refuted | u1 unlock:none, u2-u6 each requires predecessor; all lesson ids match files |
| H8 | content-sync + API | refuted | load_content returns 6 units, 18 lessons, 72 vocab; all 7 level tests pass |
| H9 | test relaxation | refuted | COMPLETE_LEVELS guards a1/a2 for all skills; relaxed test still validates vocab/lessons/path for b1 |
| H10 | match_pairs forms | refuted | All French-side entries match vocab deck fr field with correct diacritics |

**Verdict: clean round -- zero issues filed. B1 vertical slice content is sound.**
