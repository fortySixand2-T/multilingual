---
id: 754
title: "verbs-01 / verbs-02 (A1) never practice several of their own new_vocab verbs (dire, vouloir, devoir, mettre, passer, connaître, sentir, tenir)"
severity: medium
area: content
persona: edge-case-breaker
status: done
found: 2026-09-08
---

## Steps to reproduce
1. Read `content/a1/lessons/verbs-01.yaml` — `new_vocab`: `[etre, avoir, aller,
   faire, parler, manger, boire, venir, prendre, voir, dire, vouloir, devoir,
   mettre, ouvrir, fermer, ecouter, regarder, lire, ecrire]` (20 words).
2. Cross-check the 8 exercises: e1-e3 `match_pairs` cover
   être/avoir/aller/faire/parler/manger/boire/venir/prendre/voir/ouvrir/fermer/
   écouter/lire/écrire (15 words). e4 mcq drills être. e5 mcq drills boire.
   e6 word_bank drills vouloir/lire (as a distractor form). e7 translate drills
   regarder (conjugated "regarde"). e8 listen_type drills écrire.
3. `dire`, `vouloir` (the infinitive itself is only a distractor token, never
   the graded answer), `devoir`, and `mettre` are never shown in any form,
   conjugated or otherwise, anywhere in the lesson.
4. Same pattern in `content/a1/lessons/verbs-02.yaml` (new_vocab 20 verbs):
   `passer`, `connaître`, `sentir`, and `tenir` never appear in any exercise
   (match_pairs, mcq, word_bank, translate, or listen_type), infinitive or
   conjugated.

## Expected
Every `new_vocab` word for a lesson should be shown to the learner by that
lesson's exercises before it's seeded as an SRS card — see issue 752 for the
same expectation.

## Actual
`verbs-01` never shows 4/20 of its new_vocab (`dire`, `vouloir`, `devoir`,
`mettre`) and `verbs-02` never shows 4/20 (`passer`, `connaître`, `sentir`,
`tenir`) — both are basic, high-frequency A1 verbs that a beginner would
reasonably expect the "everyday verbs" lessons to actually cover, given they're
explicitly listed as what the lesson teaches.

## Notes
- Grouped verbs-01 and verbs-02 into one issue since they're the same lesson
  pair on the same grammar point with the identical failure pattern.
- See issue 755 for the aggregate numbers across all 51 lessons.
- Affected: `content/a1/lessons/verbs-01.yaml`, `content/a1/lessons/verbs-02.yaml`.

## Triage
- Explanation: Direct read of `content/a1/lessons/verbs-01.yaml` confirms `dire`,
  `devoir`, `mettre` never appear anywhere. However, `vouloir` is **not** a clean
  miss as claimed: e6's word_bank has `tokens: [Je, veux, lire, lis]` /
  `answer: [Je, veux, lire]` — "veux" (present-tense vouloir) is part of the
  *graded correct answer*, not a distractor as step 3 of this issue asserts (the
  actual distractor there is "lis", a wrong form of lire). By the same
  agreement-form-counts-as-shown standard issue 752 applies to "grande"/"vieille",
  "veux" should count as vouloir being shown. So verbs-01's real gap is 3/20
  (dire, devoir, mettre), not 4/20. `content/a1/lessons/verbs-02.yaml` is
  confirmed clean on the claimed 4/20: `passer`, `connaître`, `sentir`, `tenir`
  genuinely never appear in any form. Same seeding mechanism as 752/753.
- Against spec: unspecified explicitly; same pedagogical-intent reasoning as 752.
- Verdict: validated
- Rationale: Real gap confirmed (3/20 in verbs-01, 4/20 in verbs-02) even after
  correcting the vouloir miscount — `dire` and `devoir` in particular are
  top-frequency A1 verbs a "everyday verbs" lesson should cover. Validated as an
  instance of the systemic pattern in 755, but flagging the vouloir inaccuracy so
  the dev-fixer doesn't waste an edit re-adding a word that's already covered.
  Recommend resolving alongside 755's fix.

## Critic
- Challenge: The PM already corrected the original report's own miscount
  (vouloir is actually shown via "veux" in e6, contradicting the reporter's
  step 3), which suggests the reporter's methodology (grep for the exact
  headword string) is error-prone and the remaining "gaps" might also be
  underestimating conjugated-form coverage that a careful re-check would find.
- Holds up? Spot-checked independently: the PM's correction is right (verbs-01
  e6 word_bank answer includes "veux"), and after applying that same
  agreement/conjugation-counts-as-shown standard to the remaining claimed
  words, `dire`, `devoir`, `mettre` (verbs-01) and `passer`, `connaître`,
  `sentir`, `tenir` (verbs-02) genuinely do not appear in any conjugated or
  infinitive form anywhere in either lesson — grepped all inflected forms
  (dis/dit/disons/disent, dois/doit/devons/doivent, mets/met/mettons/mettent,
  passe/passes/passons, connais/connaît/connaissons, sens/sent/sentons,
  tiens/tient/tenons) against both YAML files with no hits beyond the
  new_vocab id itself. The methodology concern is fair but doesn't change the
  outcome once actually re-verified with the more generous standard. Keep
  validated, grouped as one ticket (reasonable since it's the same lesson pair
  and pattern), to be closed alongside 755's systemic fix.
- Final verdict: validated

## Fix
`content/a1/lessons/verbs-01.yaml`: added exercise `verbs-01.e9`
(`match_pairs`: dire/to say, devoir/to have to, mettre/to put) — `vouloir`
was left untouched (already shown via the conjugated "veux" in e6, per the
PM's correction). `content/a1/lessons/verbs-02.yaml`: added exercise
`verbs-02.e9` (`match_pairs`: passer/to pass, connaître/to know (someone),
sentir/to feel, tenir/to hold). All `new_vocab` words in both lessons are now
shown at least once. Regression test:
`tests/test_vocab_coverage.py::test_anchor_lessons_have_no_unpracticed_new_vocab`.
Content re-synced (`app.content.sync a1`); backend suite green.
