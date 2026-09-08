---
id: 751
title: "translate accept list adds unrequested detail: 'a glass of wine' only accepts 'un verre de vin rouge'"
severity: low
area: content
persona: edge-case-breaker
status: done
found: 2026-09-08
---

## Steps to reproduce
1. Read `content/a1/lessons/food-04.yaml` exercise `food-04.e7` (or
   `GET /content/lessons/food-04` while authed):
   ```yaml
   - id: food-04.e7
     type: translate
     prompt: "Translate: “a glass of wine”"
     answer: "un verre de vin"
     accept: ["un verre de vin rouge"]
   ```

## Expected
The `accept` list should contain plausible paraphrases/variants of the exact
`answer` ("un verre de vin") — capitalization, punctuation, minor spelling
variants — not a phrase that adds unrequested meaning. "Un verre de vin rouge"
means "a glass of **red** wine", which is a different (more specific)
translation than the English prompt asked for.

## Actual
The only accepted alternate is a mistranslation that adds "red" — likely a
copy/paste leftover from another exercise. A learner who typed a *reasonable*
paraphrase of the correct answer (e.g. "Un verre de vin", capitalized, or "un
verre de vin s'il vous plaît") gets no extra leniency from this list, while
"un verre de vin rouge" (arguably the wrong answer to this exact prompt) would
be accepted.

## Notes
- Found via H1 (answer-key sweep, round 055 plan) — this is the "accept list
  too broad/mismatched" failure class called out in the plan.
- Low severity because the primary `answer` string is still correct and most
  grading paths presumably do case/whitespace-insensitive matching against
  `answer` first — but the `accept` entry itself is wrong content that should
  be fixed or removed.
- Affected: `content/a1/lessons/food-04.yaml` exercise `food-04.e7`.

## Triage
- Explanation: Confirmed verbatim in `content/a1/lessons/food-04.yaml` line 58:
  `answer: "un verre de vin"` / `accept: ["un verre de vin rouge"]`. The Translate
  grading path (`web/src/screens/Lesson.tsx` line 213-219, `Translate` component)
  builds its accept set as `[ex.answer, ...ex.accept]` and does a normalized
  exact-string match (`norm(a) === norm(val)`), so "un verre de vin rouge" would
  in fact be marked correct for a prompt asking to translate "a glass of wine" —
  it's not dead data, it actively over-accepts.
- Against spec: unspecified explicitly, but the evident authoring intent of
  `accept` (seen consistently elsewhere in the corpus, e.g. capitalization
  variants like "Elle regarde") is paraphrase/formatting leniency for the *same*
  meaning, not a different, more specific translation.
- Verdict: validated
- Rationale: Low user impact (a wrong-but-accepted answer is a false negative for
  rigor, not a false rejection of a correct one — the persona most likely to hit
  it would be typing the *exact* right answer and passing anyway), but it's
  incorrect content that silently teaches a learner "vin" == "vin rouge" is fine
  when checked, and is presumably a copy/paste leftover as the reporter suspects.
  Cheap one-line content fix: drop the `accept` entry (or replace with a genuine
  paraphrase/capitalization variant).

## Critic
- Challenge: This is a pure over-acceptance bug — it never rejects a correct
  answer, only wrongly accepts one specific incorrect phrase. No real learner
  types "un verre de vin rouge" while attempting to translate "a glass of
  wine" and expects credit for it; the population that could even hit this
  false-positive is vanishingly small (someone who happens to type exactly the
  wrong phrase). Is this worth a fix over leaving trivially-wrong low-traffic
  `accept` data alone?
- Holds up? Marginally, yes. Confirmed in the YAML and confirmed
  `web/src/screens/Lesson.tsx`'s Translate grading actually builds its accept
  set from `[answer, ...accept]` and does exact-match, so the over-acceptance
  is live, not dead data. Impact is genuinely low (as the original report and
  PM both say) but the fix is a one-line deletion with zero risk to any other
  behavior — there's no real argument for leaving objectively wrong content in
  the corpus when correcting it costs nothing. Severity=low is appropriately
  calibrated; validated is still the right call given the fix is nearly free.
- Final verdict: validated

## Fix
`content/a1/lessons/food-04.yaml` exercise `food-04.e7`: removed the
mismatched `accept: ["un verre de vin rouge"]` entry (it added unrequested
meaning — "red" — to a prompt asking only for "a glass of wine"). Most other
`translate` exercises in the corpus carry no `accept` at all (the grading path
already matches `answer` case/whitespace-insensitively), so no replacement
alternate was needed here. Regression test:
`tests/test_vocab_coverage.py::test_food_04_e7_accept_does_not_over_specify`.
Content re-synced (`app.content.sync a1`); backend suite green.
