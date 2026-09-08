---
id: 750
title: mcq option "allée aller" is a garbled, non-French string in health-b1-01.e5
severity: medium
area: content
persona: edge-case-breaker
status: done
found: 2026-09-08
---

## Steps to reproduce
1. Sign up (invite `friend-001`), `GET /content/lessons/health-b1-01` (or read
   `content/b1/lessons/health-b1-01.yaml` directly).
2. Look at exercise `health-b1-01.e5`:
   ```yaml
   - id: health-b1-01.e5
     type: mcq
     prompt: "« Je suis ___ chez le médecin hier. »"
     options: ["allé", "allée aller", "vais"]
     answer: "allé"
     explain: "aller takes être in the passé composé: je suis allé(e)."
   ```

## Expected
All three mcq options should be well-formed, single French words/phrases that are
each individually plausible fills for the blank (that's the whole point of a
distractor set) — e.g. `["allé", "allée", "vais"]`.

## Actual
The second option is `"allée aller"` — two words concatenated with no connector,
not a real French form. It reads as a copy/paste or authoring error (most likely
`allée` and `aller` were meant to be two separate distractor candidates and got
merged into one option instead of being two of the three slots). Confirmed both
in the raw YAML and via `GET /content/lessons/health-b1-01` (same garbled string
is served verbatim to the client), so a real learner would see this nonsensical
option in the UI.

## Notes
- Found via H1 (answer-key sweep of the 51 new lessons, round 055 plan) while
  spot-checking `content/b1/lessons/health-b1-01.yaml`.
- Doesn't change the graded answer (still `"allé"`), so it's not a "wrong key"
  bug, but it's a broken/confusing option a beginner-to-intermediate learner
  would stumble on and can't be reasoned about like the other two options.
- Affected: `content/b1/lessons/health-b1-01.yaml` exercise `health-b1-01.e5`.

## Triage
- Explanation: Confirmed verbatim in `content/b1/lessons/health-b1-01.yaml` line 46:
  `options: ["allé", "allée aller", "vais"]`. This is served as-is by
  `GET /content/lessons/health-b1-01` (content API passes through YAML fields
  unmodified) and rendered as-is by the MCQ exercise component — no code
  normalizes or splits option strings. It's a content authoring/copy-paste error,
  not a rendering or grading bug (the graded `answer` is still correct).
- Against spec: unspecified explicitly, but the content-authoring intent (each MCQ
  option should be a single well-formed, plausible distractor) is self-evident from
  every other exercise in the corpus and from the `explain` field referencing
  "allé(e)" as the only two real forms in play — "allée aller" is neither.
- Verdict: validated
- Rationale: A real learner doing this exercise sees a nonsensical, obviously-broken
  option among three choices, which is confusing/unprofessional even though it
  doesn't change the correct answer. Cheap, low-risk content fix: replace with
  `"allée"` (the intended distractor, per the explain text pattern) as two separate
  slots aren't needed — a 3-option MCQ. One-line YAML edit.

## Critic
- Challenge: The graded answer is unaffected (still `"allé"`), so this is
  arguably cosmetic — a learner who can't parse "allée aller" simply rules it
  out as nonsense and picks between the two real words, with zero risk of
  landing on a wrong answer by mistake. Is a one-off typo in a single MCQ
  option worth a ticket, or just noise?
- Holds up? Yes. Verified directly in the YAML and confirmed the content API
  serves it verbatim with no normalization layer, so every learner who reaches
  this exercise sees a garbled, unprofessional string mid-lesson — a real (if
  minor) content-quality defect, not hypothetical. The fix is a true one-line
  content edit with no code risk and no change to grading behavior, so there's
  no "fix is worse than the bug" concern. Severity=medium and the proposed
  trivial fix both check out.
- Final verdict: validated

## Fix
`content/b1/lessons/health-b1-01.yaml` exercise `health-b1-01.e5`: replaced the
garbled `"allée aller"` mcq option with the intended single distractor
`"allée"` — options are now `["allé", "allée", "vais"]`, all well-formed,
individually plausible fills for the blank. Graded `answer` unchanged.
Regression test: `tests/test_vocab_coverage.py::test_health_b1_01_e5_mcq_options_are_well_formed`
(asserts the exact options list and that every mcq option is a single
word/phrase). Content re-synced (`app.content.sync b1`); backend suite green.
