---
id: 752
title: "adjectives-01 (A1) seeds SRS cards for 5 basic adjectives never shown in any exercise (beau, bon, mauvais, long, court)"
severity: medium
area: content
persona: edge-case-breaker
status: done
found: 2026-09-08
---

## Steps to reproduce
1. Read `content/a1/lessons/adjectives-01.yaml` (or `GET /content/lessons/adjectives-01`
   authed) — `new_vocab` lists 20 ids:
   `[grand, petit, nouveau, vieux, jeune, beau, joli, bon, mauvais, facile,
   difficile, long, court, fort, faible, rapide, lent, propre, sale, plein]`.
2. Grep every exercise's `match_pairs` pairs / `mcq` prompt+options+answer /
   `word_bank` tokens / `translate` answer+accept / `listen_type` answer for each
   of those 20 French headwords.
3. `grand, petit, nouveau, vieux, jeune` → e1. `facile, difficile, rapide, lent,
   plein` → e2. `propre, sale, fort, faible, joli` → e3. `grande`(agreement of
   grand) → e4. `propre` → e5. `petit` → e6. `vieille`(agreement of vieux) → e7.
   `difficile` → e8 (listen_type).
4. `beau, bon, mauvais, long, court` never appear anywhere in the 8 exercises.

## Expected
Completing this lesson seeds SRS review cards for all 20 `new_vocab` ids (per
the app's own seeding logic). A learner should have been shown/practiced a word
at least once before it starts appearing as an SRS review card — otherwise the
first time they ever see "bon"/"mauvais"/"long"/"court" is in a spaced-repetition
quiz with no prior exposure in the lesson that supposedly taught it.

## Actual
5/20 (25%) of this lesson's `new_vocab` — including four very high-frequency,
basic adjectives (`bon`, `mauvais`, `long`, `court`) that a beginner would
expect an "adjectives" lesson to actually cover — are silently seeded to SRS
without ever being shown in `adjectives-01`'s 8 exercises.

## Notes
- This is the same failure class already confirmed in `psychologie-b2-01` and
  `justice-b2-01` (round 055 plan, don't re-file those two) — this extends the
  finding to A1 content and to plain everyday words, not just abstract B2
  vocabulary, showing the pattern isn't limited to advanced/rare terms.
- Root-cause hypothesis: each new lesson has 3 `match_pairs` exercises (5 pairs
  each = 15 word slots) + 1 mcq + 1 word_bank + 1 translate + 1 listen_type,
  but the latter four often re-use/agree-form words already shown in the
  match_pairs rather than covering the ~5 words match_pairs didn't reach, so a
  lesson with 20 `new_vocab` structurally tends to leave several words
  completely unpracticed.
- See issue 755 for the full quantified sweep across all 51 new lessons (43/51
  lessons affected, 117/966 `new_vocab` entries never shown, ~12%).
- Affected: `content/a1/lessons/adjectives-01.yaml`.

## Triage
- Explanation: Confirmed by direct read of `content/a1/lessons/adjectives-01.yaml`
  — `beau`, `bon`, `mauvais`, `long`, `court` genuinely never appear (as headword,
  inflection, or agreement form) across e1-e8. `new_vocab` is exactly what
  `POST /progress/lessons/{id}/result` passes to `seed_cards()` on first pass
  (`app/progress/api.py` line 143: `await seed_cards(session, user.id,
  data.get("new_vocab", []))`), so these 5 words are seeded as SRS review cards
  with zero prior exposure in the lesson.
- Against spec: unspecified explicitly (no AC says "new_vocab must equal words
  shown in exercises"), but it's the clear pedagogical intent behind the
  new_vocab→SRS pipeline (`app/progress/api.py` module docstring: "seeds the
  lesson's new_vocab into the SRS review queue") — SRS is meant to reinforce
  what was taught, not introduce cold material via a quiz.
- Verdict: validated
- Rationale: A beginner would hit "bon"/"mauvais" (extremely high-frequency
  adjectives) for the first time as an SRS flashcard with no lesson context —
  worse for absolute beginners than for advanced learners who can infer from
  context. Real, in-scope content-authoring bug. This is one concrete instance of
  the systemic pattern quantified in issue 755 (43/51 lessons, ~12% of new_vocab);
  recommend the dev-fixer resolve it as part of 755's systemic fix rather than as
  an isolated patch, since the same authoring-template root cause applies here.

## Critic
- Challenge: There is no spec requiring 1:1 coverage between `new_vocab` and
  exercise content, and the SRS review card itself is not a "cold, contextless
  quiz" — `Review.tsx` shows the French word with audio, and on reveal shows
  the English translation before asking for a difficulty rating. That is
  exactly how many spaced-repetition decks (e.g. Anki) bootstrap brand-new
  vocabulary: the first "review" of a card IS the first teaching exposure.
  Framing this as SRS "testing" a word the learner was "never shown" overstates
  the harm — the card itself teaches it on first encounter.
- Holds up? Partially, but the core defect survives the challenge. Even
  granting that an SRS card can be a valid first-exposure mechanism, this
  lesson's `new_vocab` list is presented (via lesson metadata / the app's own
  seeding logic) as "words this lesson taught," and 5/20 of them received zero
  reinforcement, context, pronunciation practice, or usage example anywhere in
  the interactive exercises the lesson actually contains — verified directly
  against `content/a1/lessons/adjectives-01.yaml`, confirming `beau`, `bon`,
  `mauvais`, `long`, `court` are absent from all 8 exercises. Whether the fix
  is "trim new_vocab to what's practiced" or "add coverage," there's a real,
  reproducible mismatch worth correcting. This is a genuine but modest content
  gap, not a false alarm — validated stands, but I'd push back on any framing
  that treats SRS-first-exposure itself as the bug; the bug is the
  claimed-vs-actual coverage mismatch, which is real and independent of that.
  On overlap with 755: this remains a useful concrete anchor (verified,
  file-specific, testable) rather than a redundant duplicate — a systemic fix
  to 755 can and should close this ticket in the same commit rather than a
  separate patch; no need to defer or reject it as duplicate work.
- Final verdict: validated

## Fix
`content/a1/lessons/adjectives-01.yaml`: added exercise `adjectives-01.e9`
(a 5-pair `match_pairs`: beau/beautiful, bon/good, mauvais/bad, long/long,
court/short), so all 20 `new_vocab` words are now shown at least once.
Regression test: `tests/test_vocab_coverage.py::test_anchor_lessons_have_no_unpracticed_new_vocab`
(and the broader `test_round_055_lessons_new_vocab_is_practiced_in_exercises`
covering all 44 lessons from issue 755's sweep). Content re-synced
(`app.content.sync a1`); backend + frontend suites green.
