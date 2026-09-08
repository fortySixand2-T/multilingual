---
id: 755
title: "new_vocab/exercise-coverage gap is systemic across the 51 new lessons, not isolated (43/51 lessons affected, ~12% of words never shown)"
severity: high
area: content
persona: edge-case-breaker
status: done
found: 2026-09-08
---

## Steps to reproduce
1. For all 51 new lessons (11 A1, 11 A2, 13 B1, 16 B2 — the full list from
   CHANGELOG 2026-09-08), diff each lesson's `new_vocab` id list against the
   headword(s) actually shown in that lesson's exercises: `match_pairs` pairs,
   `mcq` prompt/options/answer, `word_bank` tokens, `translate` answer/accept,
   `listen_type` answer (resolving each `new_vocab` id to its `fr` headword via
   `content/{level}/vocab/*.yaml`, stripping leading articles for matching).
2. Result across all 966 `new_vocab` entries in the 51 lessons:
   **117/966 (12.1%) never appear in any exercise**, spread across **43 of the
   51 lessons** (only `food-04`, `animals-01`, `school-01`, `adjectives-02`,
   `health-b1-01`, `actualite-b2-04`, `actualite-b2-05`, and `health-b1-02`
   (1 borderline word) are fully clean).
3. Worst offenders (excluding the two lessons already flagged in the round
   plan, `psychologie-b2-01` and `justice-b2-01`, which aren't re-filed here):
   `adjectives-01` 5/20 (issue 752), `medias-b2-01` 5/20 (issue 753),
   `verbs-01` 4/20 + `verbs-02` 4/20 (issue 754), `entreprise-b2-01` 4/20,
   `relationships-b1-01` 4/20, `communication-a2-01` 4/20.
4. Full per-lesson breakdown (level/lesson: missing/total):
   ```
   a1/house-01: 1/20        a1/places-01: 2/20       a1/jobs-01: 3/20
   a1/countries-01: 2/20    a1/verbs-01: 4/20*        a1/verbs-02: 4/20*
   a1/adjectives-01: 5/20
   a2/money-a2-01: 2/20     a2/nature-a2-01: 2/20     a2/studies-a2-01: 3/20
   a2/sports-a2-01: 3/20    a2/celebrations-a2-01: 3/20
   a2/communication-a2-01: 4/20   a2/people-a2-01: 3/20
   a2/emergencies-a2-01: 3/20     a2/travail-a2-04: 1/17
   a2/sante-a2-04: 1/17     a2/transport-a2-04: 2/17
   b1/immigration-b1-04: 3/20     b1/travail-b1-04: 3/20
   b1/logement-b1-04: 2/18  b1/argent-b1-04: 1/18     b1/rights-b1-01: 1/20
   b1/relationships-b1-01: 4/20   b1/tourism-b1-01: 2/20
   b1/food-b1-01: 3/20      b1/mobility-b1-01: 3/20   b1/arts-b1-01: 3/20
   b1/technology-b1-01: 3/20      b1/health-b1-02: 1/17
   b2/justice-b2-01: 3/20 (already known)
   b2/technologie-b2-01: 3/20     b2/education-b2-01: 3/20
   b2/medias-b2-01: 5/20    b2/migration-b2-01: 3/20
   b2/entreprise-b2-01: 4/20      b2/psychologie-b2-01: 4/20 (already known)
   b2/histoire-b2-01: 3/20  b2/travail-b2-04: 1/17    b2/sante-b2-04: 2/17
   b2/societe-b2-04: 2/17   b2/environnement-b2-04: 2/17
   b2/economie-b2-04: 2/17  b2/politique-b2-04: 1/17
   ```
   (`*` = counted conservatively; verbs-01/verbs-02 have 1 extra borderline
   word each that's practiced only in a conjugated, not infinitive, form.)

## Expected
`new_vocab` (which drives SRS card seeding on lesson completion, up to 20 cards
at once) should be a reasonably faithful list of words the lesson actually
taught — a learner shouldn't get quizzed via spaced repetition on a word they
were never shown once.

## Actual
This is not a two-lesson edge case (as the round plan's pre-existing finding on
`psychologie-b2-01`/`justice-b2-01` might suggest) — it's the default outcome
of how these 51 lessons were authored. 84% of them (43/51) have at least one
`new_vocab` word absent from every exercise, and the overall miss rate is ~12%
of all new vocabulary taught in this arc.

## Notes
- Likely root cause (structural, not per-lesson typos): each lesson has 20
  (or 14-18) `new_vocab` ids but a fixed exercise shape of 3 `match_pairs`
  (5 pairs each = 15 word slots) + 1 mcq + 1 word_bank + 1 translate + 1
  listen_type (4 more single-word slots, but these frequently reuse or
  agreement-inflect a word already shown in match_pairs rather than reaching
  for the ~5 words match_pairs didn't cover). With 20 words and effectively
  15-19 usable slots per lesson, some gap is close to structurally
  unavoidable given the current authoring template — worth deciding whether to
  fix per-lesson (swap distractors/reuse for new words) or systemically
  (increase match_pairs slots, or trim `new_vocab` to what's actually
  practiced).
- This issue is the quantified H3 finding requested by the round 055 plan; see
  issues 752/753/754 for the worst individual-lesson offenders filed as
  separate concrete repros.
- Not filing per-lesson issues for every one of the 43 affected lessons (would
  be excessive); recommend the dev-fixer treat this as one systemic ticket
  covering the pattern, with 752/753/754 as the most severe concrete examples.

## Triage
- Explanation: Spot-checked 4 of the cited lessons directly against the YAML
  (`adjectives-01`, `medias-b2-01`, `verbs-01`, `verbs-02`) and all matched the
  claimed miss lists exactly except one word (`vouloir` in verbs-01 is actually
  shown via the conjugated form "veux" as the graded answer in e6 — see the
  correction filed on issue 754; this doesn't materially change the aggregate
  conclusion, just shaves ~1 word off the 117/966 total). The root-cause
  hypothesis holds up on inspection: every one of the 51 lessons follows the
  same fixed template (3×5-pair match_pairs + mcq + word_bank + translate +
  listen_type = ~15-19 word "slots" for a 14-20 word `new_vocab` list), and the
  last 4 exercise types frequently re-use or agreement-inflect a word already
  covered by match_pairs rather than reaching for new_vocab's remainder. This is
  confirmed as a structural authoring-template issue, not per-lesson typos.
  `new_vocab` is the exact and only input to SRS card seeding
  (`app/progress/api.py`: `seed_cards(session, user.id,
  data.get("new_vocab", []))` on first lesson pass), so every gap here becomes a
  real SRS card the learner has never seen taught.
- Against spec: unspecified explicitly — no AC requires 1:1 coverage between
  `new_vocab` and exercise content — but it directly undercuts the stated
  purpose of the new_vocab→SRS pipeline (teach, then reinforce via spaced
  repetition) documented in `app/progress/api.py`'s own module docstring.
- Verdict: validated
- Rationale: High severity is justified — this isn't a two-lesson edge case but
  the default outcome of the current 51-lesson authoring template (43/51
  lessons, ~12% of all new vocabulary in this content arc), and it directly
  degrades the core promise of the SRS loop for essentially every learner who
  completes any of these new lessons. Recommend the dev-fixer treat this as the
  primary ticket (with 752/753/754 as concrete anchors already spot-verified)
  and fix at the template/generation level — e.g. widen match_pairs slot count,
  or programmatically trim `new_vocab` to what's demonstrably practiced — rather
  than hand-patching 43 files as one-offs.

## Critic
- Challenge: There is no spec, AC, or documented contract requiring
  `new_vocab` to be 1:1 with exercise content, and the framing that this
  "degrades the core promise of the SRS loop for essentially every learner"
  overstates the mechanism — `Review.tsx` shows the French word, audio, and
  (on reveal) the English translation before any rating is requested, so an
  SRS card is itself a valid first-teaching exposure, not a blind pop quiz.
  Given that, is a ~12% new_vocab/exercise mismatch actually "high" severity,
  or is this a curriculum-polish nice-to-have being inflated by an aggregate
  percentage that sounds worse than the per-learner impact (a handful of extra
  words per lesson learned via flashcard-first instead of exercise-first)?
- Holds up? The severity framing is somewhat overstated for the reason above,
  but the underlying finding is real, systemic, and independently
  reproducible — spot-checked 4 of the cited lessons directly against YAML
  (adjectives-01, medias-b2-01, verbs-01, verbs-02) and all matched the
  claimed gaps (with the one already-acknowledged vouloir correction). The
  root-cause hypothesis (fixed 3×5 match_pairs + 4 single-word slots
  structurally undersized for 14-20 word new_vocab lists) is well-argued and
  plausible. Regardless of whether SRS-first-exposure softens the "harm," the
  factual claim — new_vocab lists include words the lesson's own exercises
  never touch, at scale, across 43/51 lessons — is correct and worth fixing at
  the template/generation level as recommended, since a lesson claiming to
  teach 20 words while only exercising 15-19 is a real curation defect
  independent of how forgiving SRS review is. Recommend the fix owner also
  reconsider whether "high" severity is warranted vs "medium" given the
  SRS-card-teaches-too counterargument, but that's a severity/triage nuance,
  not grounds to reject the underlying finding.
- Final verdict: validated

## Fix
Resolved with a mix of both options offered, chosen per-lesson by tractability:

1. **Content fix (option a)** for the 4 verified anchor lessons (752, 753,
   754): added a `match_pairs` exercise to each covering exactly its missing
   words — `content/a1/lessons/adjectives-01.yaml`,
   `content/b2/lessons/medias-b2-01.yaml`, `content/a1/lessons/verbs-01.yaml`,
   `content/a1/lessons/verbs-02.yaml`.
2. **Structural fix (option b)** for the remaining lessons in the affected
   set: wrote a coverage checker (accent-normalized headword match, with a
   stem/prefix fallback so agreement and conjugated forms like
   "grande"/"veux" still count as "shown") and used it to trim `new_vocab`
   down to only the words each lesson's own exercises actually practice, for
   37 lessons across a1/a2/b1/b2 (adding up to ~90 trimmed ids) — e.g.
   `content/a1/lessons/house-01.yaml` (dropped `toilettes`),
   `content/a2/lessons/communication-a2-01.yaml` (dropped `signature`,
   `conversation`, `discuter`), `content/b2/lessons/psychologie-b2-01.yaml`
   (dropped `psychologue`, `emotion`, `perception`, `adaptation`), and 34
   others — full list is reproducible via the coverage checker embedded in
   `tests/test_vocab_coverage.py`. This directly means these words no longer
   seed untaught SRS cards; the words themselves remain fully authored in the
   level's vocab deck (`content/{level}/vocab/*.yaml`) and reachable via
   Browse/My Deck, just not force-seeded by lesson completion.
3. One known false positive from the coverage heuristic was preserved rather
   than wrongly trimmed: `vouloir` in `a1/verbs-01` — it's genuinely shown via
   the conjugated "veux" (per issue 754's correction), which a literal/stem
   match can't detect; hardcoded as a documented exception in the test.

Not changed: the underlying authoring *template* (3×5-pair match_pairs + 4
single-word slots) that produced this gap in the first place — this fix
closes the gap in the existing 51-lesson corpus but doesn't prevent a future
lesson authored the same way (20-word new_vocab, same template) from
reintroducing it. `tests/test_vocab_coverage.py::test_round_055_lessons_new_vocab_is_practiced_in_exercises`
guards regression for the specific 44 lessons covered here, but is not yet a
generic corpus-wide gate for lessons authored after this round — flagging as
a follow-up recommendation (e.g. widen the match_pairs template capacity, or
add a corpus-wide new_vocab/exercise-coverage CI check) rather than in-scope
for this fix.

Verified via `/tmp/tef312/bin/python -m app.content.sync {a1,a2,b1,b2}` (all
levels load and sync cleanly) and the new regression tests; backend suite
(330 passed, 1 skipped) and `ruff check` both green.
