---
id: 753
title: "medias-b2-01 (B2) seeds SRS cards for 5/20 new_vocab words never shown in any exercise"
severity: medium
area: content
persona: edge-case-breaker
status: done
found: 2026-09-08
---

## Steps to reproduce
1. Read `content/b2/lessons/medias-b2-01.yaml` (or `GET /content/lessons/medias-b2-01`
   authed) — `new_vocab` (20 ids): `[deontologie, ligne_editoriale, redaction,
   la_une, editorial, chronique, enquete, verification_faits, sensationnalisme,
   traitement_mediatique, couverture_presse, pluralisme, independance, abonne,
   audimat, viralite, clivage, bulle_informationnelle, recoupement, credibilite]`.
2. Cross-check against the lesson's 8 exercises (3 `match_pairs` + `mcq` +
   `word_bank` + `translate` + `listen_type`).
3. `chronique` (a regular column), `traitement_mediatique` (media coverage/
   framing), `couverture_presse` (press coverage), `independance` (editorial
   independence), and `abonne` (subscriber) never appear in any pair, prompt,
   option, token, answer, or accept string across all 8 exercises.

## Expected
Same as issue 752/the psychologie-b2-01 / justice-b2-01 findings already noted
in the round plan: every word in `new_vocab` should be shown to the learner at
least once by the lesson's own exercises before it's seeded as an SRS card.

## Actual
5/20 (25%) of `medias-b2-01`'s new_vocab is completely unpracticed — tied with
`psychologie-b2-01` for the worst gap rate found in this sweep (not counting
the two lessons the round plan already flagged, which aren't being re-filed
here).

## Notes
- See issue 755 for the aggregate numbers across all 51 lessons.
- Affected: `content/b2/lessons/medias-b2-01.yaml`.

## Triage
- Explanation: Confirmed by direct read of `content/b2/lessons/medias-b2-01.yaml`
  — `chronique`, `traitement_mediatique`, `couverture_presse`, `independance`,
  `abonne` genuinely never appear in any of e1-e8. Same seeding mechanism as
  issue 752 (`app/progress/api.py`'s `seed_cards(... data.get("new_vocab", []))`
  on first lesson pass) — same root cause, different lesson.
- Against spec: unspecified explicitly; same pedagogical-intent reasoning as 752.
- Verdict: validated
- Rationale: At B2, abstract/rare vocabulary already strains a learner's working
  memory; being SRS-quizzed on words like "indépendance (éditoriale)" or "abonné"
  that were never shown once is a worse experience than at A1 since the learner
  has no contextual scaffolding to fall back on. One concrete instance of the
  systemic pattern in issue 755; recommend resolving alongside 755's fix rather
  than as an isolated patch.

## Critic
- Challenge: Same "SRS-card-is-itself-the-first-exposure" argument as 752
  applies here, arguably even more so at B2 — an advanced learner is expected
  to infer/retain abstract vocabulary from a translation card without needing
  a dedicated exercise slot. Also: is 5/20 really "tied for worst" worth
  calling out as a separate ticket rather than folding silently into 755's
  aggregate?
- Holds up? Same conclusion as 752 — the coverage-claim mismatch is real and
  independently verified (`chronique`, `traitement_mediatique`,
  `couverture_presse`, `independance`, `abonne` confirmed absent from all 8
  exercises in `content/b2/lessons/medias-b2-01.yaml`), and the fix is cheap
  either way (trim new_vocab or add coverage). The B2-inference argument cuts
  both ways: a learner unfamiliar with "indépendance éditoriale" as a
  collocation has *less* scaffolding to guess correctly from a bare
  translation card, not more, so the SRS-teaches-cold-words defense is weaker
  here than at A1, not stronger. Keeping this as a validated, file-specific
  anchor for 755's systemic fix is reasonable; no basis to reject or defer as
  a mere duplicate since it will be resolved by the same fix, not extra work.
- Final verdict: validated

## Fix
`content/b2/lessons/medias-b2-01.yaml`: added exercise `medias-b2-01.e9`
(a 5-pair `match_pairs`: chronique/column, traitement médiatique/media
coverage, couverture de presse/press coverage, indépendance/independence,
abonné/subscriber), so all 20 `new_vocab` words are now shown at least once.
Regression test: `tests/test_vocab_coverage.py::test_anchor_lessons_have_no_unpracticed_new_vocab`.
Content re-synced (`app.content.sync b2`); backend suite green.
