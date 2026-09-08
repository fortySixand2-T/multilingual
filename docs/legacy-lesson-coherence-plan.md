# Plan — close the legacy lesson↔vocab coherence gap

## The defect

`new_vocab` is what seeds SRS review cards when a learner first passes a lesson
(`app.progress.api.seed_cards`). A word listed there but never shown by that lesson's
own exercises produces a review card for something the learner was never taught.

QA round 055 found and fixed this across the 51 lessons added in PRs #87–#90. The
same defect exists in the **pre-existing lessons**, at a higher rate, and predates
that work.

## Size (measured 2026-09-08, at `9cb697a`)

| level | lessons with gaps | words unshown | of new_vocab |
|---|---|---|---|
| a1 | 15 | 84 | 200 |
| a2 | 18 | 92 | 206 |
| b1 | 10 | 48 | 180 |
| b2 | 12 | 12 | 180 |
| **total** | **55** | **236** | **766** |

B2 is nearly clean (12 lessons × 1 word each). The weight is in a1/a2.

## Root cause — it is not the same as the one we just fixed

Ours was a fixed 8-exercise template against variable-length `new_vocab`.

This one is structural: **33 of the 55 are `-03` "review" lessons**. Their exercises
correctly recycle vocabulary from `-01`/`-02` — that is what a review lesson should
do — but the `-03` slot was also used to park each deck's *leftover* words in
`new_vocab`. So the lesson introduces 8 genuinely new words and practises none of
them.

`a1/cafe-03` is the archetype: exercises drill *addition, café, thé, eau, bière, vin*
(all from cafe-01/02), while `new_vocab` lists *chocolat_chaud, limonade, tasse,
pourboire, croissant, terrasse, glaçon, citron* — none of which appear anywhere in the
lesson. Eight of eight unshown.

The remaining 22 are ordinary partial gaps (1–4 words each).

## Decision to make first

The `-03` lessons pose a design question that the fix depends on:

**Option A — teach the leftovers in `-03`.** Add exercises so `-03` both reviews the
unit *and* introduces its remaining words. Cheapest, preserves 100% coverage, but
makes "review" lessons no longer purely review.

**Option B — redistribute.** Move the leftover words to `-01`/`-02` (with exercises)
and let `-03` stay a pure review lesson, its `new_vocab` trimmed to what it actually
revisits. Pedagogically cleaner, but touches three files per unit and rebalances
lesson length.

**Recommendation: A.** It matches the remedy already applied to the 51 new lessons,
keeps the diff per lesson small and reviewable, and preserves the
1732/1732-taught property. B is a content redesign wearing a bug fix's clothes — worth
doing deliberately later, if at all.

## Approach (assuming A)

Hybrid, mirroring what worked in PR #91:

1. **Baseline guarantee (scripted).** For each of the 55 lessons, append
   `match_pairs` exercises covering exactly its unshown words, 5 pairs max per
   exercise, drawn from the vocab bank so `fr`/`en` always match the deck. ~50 new
   exercises for 236 words. This alone closes the defect.
2. **Hand-upgrade the worst 33.** For the `-03` review lessons (8/8 unshown), a bare
   match_pairs block is thin for eight new words. Add one `mcq` or `translate` per
   lesson that uses the new words in context, so they are *used*, not just matched.
3. **Extend the regression test.** `tests/test_vocab_coverage.py` currently guards
   only the 51 new lessons via an explicit `TARGET_LESSONS` list. Replace that list
   with "every lesson at every level", so the property can never regress again — for
   old or new content. **Land this test first, failing**, so the fix is verifiably
   driven by it.

## Delivery

Per level, matching the established rhythm — 4 PRs, each verified and merged on green:

| PR | scope | words |
|---|---|---|
| 1 | b2 (12 lessons) + the generalized failing test | 12 |
| 2 | b1 (10 lessons) | 48 |
| 3 | a1 (15 lessons) | 84 |
| 4 | a2 (18 lessons) | 92 |

Starting with b2 is deliberate: it is the smallest slice, so it proves the test change
and the exercise-generation approach on 12 words before committing to 200+.

## Verification per PR

Same gates as the vocab arc:

- `pytest -q` (incl. the generalized coverage test), `ruff check`, `ruff format --check`
- `listen_type` refs resolve; no duplicate exercise ids; no malformed `match_pairs`
  (the 3-item-pair trap — see the authoring notes)
- coverage assertion stays at 1732/1732 taught
- content sync clean for the level

## Risks

- **Answer-key risk is low here**: `match_pairs` entries are generated from the vocab
  bank, so they cannot disagree with it. The hand-written mcq/translate additions in
  step 2 carry the usual risk and should be QA-sampled.
- **SRS impact is nil**: `new_vocab` is unchanged. These lessons already seed these
  words; the fix only makes the lesson actually show them.
- **Lesson length grows** for the 33 review lessons (5 exercises → 7–8). `est_minutes`
  should be bumped from 5 to 7 where that happens.
