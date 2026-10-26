---
id: 866
title: Writing grader silently drops genuine lexical/word-choice errors (no citable vocabulary reference)
severity: medium
area: writing
persona: edge-case-breaker
status: done
found: 2026-10-25
---

## Steps to reproduce
1. Sign up (`@qa.test` + invite `friend-001`), get a bearer token.
2. `GET /assessment/tasks?level=a2` (etc.) to find real `task_id`s.
3. `POST /assessment/tasks/<task_id>/submit` with hand-written French mixing one real
   grammar error and one real, unambiguous lexical/word-choice error (wrong word for a
   real concept, not a translation-ambiguity). Repeat across levels.

   a2 (`write-a2-doctor`), submitted text (64 words):
   > "Bonjour, je ne me sens pas bien depuis deux jours. **Les symptômes a commencé**
   > lundi matin, avec de la fièvre et un peu de toux. J'ai aussi mal aux dents donc je
   > voudrais un rendez-vous avec **le docteur de mes dents** cette semaine, si possible
   > le matin. Je travaille les après-midis et je ne peux pas venir plus tard. Merci de
   > votre réponse rapide."

   Full response `corrections` array:
   ```json
   [
     {
       "excerpt": "Les symptômes a commencé lundi matin",
       "correction": "Les symptômes ont commencé lundi matin",
       "explanation": "Use 'ont' for passé composé.",
       "reference": "temps-passe"
     },
     {
       "excerpt": "avec de la fièvre et un peu de toux",
       "correction": "avec de la fièvre et une toux",
       "explanation": "Toux is feminine, so use 'une'.",
       "reference": "accord-genre-nombre"
     }
   ]
   ```

   b1 (`write-b1-environment`), submitted text (206 words), relevant excerpt:
   > "...Il faut que tout le monde **assiste à ce problème** dès maintenant..."
   (should be e.g. "s'attaque à ce problème" / "prenne ce problème en compte" — "assister
   à" means to attend/witness, not to address — a genuine lexical mistake, not a
   translation-ambiguity call). `corrections` returned only the unrelated grammar fix
   ("doit" -> "doivent"); nothing on "assiste à ce problème".

   b2 (`write-b2-health-letter`), submitted text (155 words), relevant excerpt:
   > "...**Nous manquons de monnaie** pour embaucher plus de personnel..."
   (should be "argent" — "monnaie" means change/currency, not money in this sense).
   `corrections` returned only an (arguably spurious, see issue 867) "infirmiers" ->
   "infirmières" fix; nothing on "monnaie".

## Expected
A learner who makes a real, recognizable lexical/word-choice error (wrong word for a
concept, false-friend usage, wrong register) should get a correction for it, the same
way a grammar slip does — or at minimum the `vocabulary` criterion's `comment` should
call the specific mistake out.

## Actual
Across 3 separate submissions at a2/b1/b2, each containing one unambiguous lexical
error embedded in text the grader otherwise read carefully (it correctly caught and
cited the grammar errors in the *same* submissions), the lexical error was: (a) never
present in `corrections`, and (b) never mentioned in the `vocabulary` criterion's
`comment` either (e.g. a2's vocabulary comment is "Uses some in-level words but misses
'médecin' and 'ordonnance'" — no mention that "docteur de mes dents" is wrong). The
learner gets zero signal that a real mistake was made.

## Notes
Root cause (code-read, `app/assessment/grader.py`): `_is_genuine()` keeps a correction
only if `c.reference in GRAMMAR_REFERENCES` — the 8-key curated set `{accord-sujet-verbe,
accord-genre-nombre, temps-passe, prepositions, pronoms, ordre-des-mots, orthographe,
elision}`. There is no vocabulary/lexical-choice key in that list, even though
`vocabulary` is one of the four scored criteria. So even if the underlying model
internally flags a lexical mistake, there is no reference key it could legally cite
that would survive the filter — the fix for issue 831 (over-triggering on invented
grammar "corrections") traded false positives for a structural false-negative on an
entire error category. This is the H5 hypothesis from `qa/rounds/059-plan.md`,
confirmed with 3 of 4 probed lexical-error submissions showing the gap cleanly (the 4th,
a1, also missed its grammar error entirely so is less clean evidence and not included
above). Related to (but distinct from) the mis-citation issue filed as 867.

## Triage
- Explanation: confirmed at both the prompt and code layer, both touched by 686cebd's
  831 fix. `app/assessment/prompts/writing_grader.md`'s "Inline corrections" section
  (edited by this PR to add the "only genuine errors" paragraph) instructs the model a
  correction's `reference` must be "a grammar point from this curated [8-key] list... Do
  not invent grammar rules or references outside this list" — vocabulary/word-choice is
  never one of the eight keys, despite `vocabulary` being one of the four scored
  criteria one paragraph above. `_is_genuine()` in `grader.py` then enforces the same
  list as a hard filter (`c.reference in GRAMMAR_REFERENCES`). So a genuine lexical
  error has no legal reference to cite even in principle — not just a case where the
  model picks the wrong key (that's issue 867) — the category is structurally excluded
  by both the instruction and the filter. Live testing confirmed the predicted effect:
  3 of 4 submissions with a clear, unambiguous lexical slip got zero correction and zero
  mention in the `vocabulary` comment.
- Against spec: the prompt's own scoring rubric treats `vocabulary` ("range and accuracy
  of word choice") as a first-class scored criterion, but the curated reference list
  added by this same PR has no corresponding key — an internal inconsistency introduced
  by 831's fix, not a pre-existing design choice (before 686cebd, `_is_genuine` didn't
  exist and any correction the model returned, lexical or grammatical, survived).
- Verdict: validated
- Rationale: this is a structural false-negative introduced by this PR's new curated-
  reference filter (traded 831's over-triggering false positives for an entire missing
  error category), not merely "confirming a disclosed residual" — 831's own Fix section
  only disclosed the mis-citation risk (867's class), never flagged that an entire error
  category (lexical/word-choice) would be unable to pass at all. Real learner-trust
  impact: a learner gets no signal whatsoever on a genuine mistake. In scope for a
  moderate fix: add a `vocabulaire`/lexical-choice key to `GRAMMAR_REFERENCES` and the
  prompt's curated list (and to the writing-grader tests that assert the two lists stay
  in sync, per 831's own test note).

## Critic
- Challenge: is "no vocabulary key" really a regression, or was it always the
  design — the prompt's own rubric separates `vocabulary` as a *scored* criterion
  from the curated grammar-reference list, which could be read as "inline
  corrections were only ever meant for grammar, lexical issues show up in the
  vocabulary score/comment instead." If that's true, 866 is asking for new scope,
  not catching something this PR broke.
- Holds up? No — the regression framing is correct, not the "always the design"
  reading. `git show 686cebd -- app/assessment/grader.py` proves `GRAMMAR_REFERENCES`
  and `_is_genuine()` are *both new in this PR* — there was no runtime filter on
  `reference` before 686cebd. `git show 686cebd -- app/assessment/prompts/
  writing_grader.md` shows the curated key list already existed pre-PR as advisory
  text to the model (7 of the 8 keys, missing only the new `elision` key this PR
  added) — but as advisory text only: pre-PR, nothing in `parse_feedback` checked
  `c.reference` at all, so any correction the model returned, grammar or lexical,
  survived into the response regardless of what (or whether) it cited. So the
  "vocabulary is scored, not citable" framing is not evidence of original intent —
  it's just as true before this PR as after; what changed is that this PR added a
  hard runtime gate keyed on a list that was never extended to cover the one scored
  criterion with no corresponding reference key. A lexical correction that would
  have passed through untouched last week is unconditionally dropped this week.
  That is a structural false-negative this PR introduced, confirmed independently
  via `git show`, not a pre-existing design choice being newly noticed.
- Final verdict: validated

## Fix
Added a `choix-lexical` key to `GRAMMAR_REFERENCES` in `app/assessment/grader.py` and
to the curated list in `app/assessment/prompts/writing_grader.md` (kept in sync per
`test_grammar_references_match_the_prompt`), so a genuine lexical/word-choice error
(false friend, wrong word for the concept) has a legal reference to cite and survives
`_is_genuine`'s filter instead of being structurally excluded.
- Files: `app/assessment/grader.py`, `app/assessment/prompts/writing_grader.md`
- Tests: `tests/test_assessment.py::test_genuine_lexical_correction_survives_the_filter`
  (existing `test_grammar_references_match_the_prompt` now also covers the new key)
