---
id: 429
title: "culture-b2-02.e1 MCQ distractors make ungrammatical French with the fixed stem"
status: done
severity: medium
area: content
persona: exam-crammer
round: "032"
---

## Steps to reproduce
1. Read `/Users/sirius/projects/multilingual/content/b2/lessons/culture-b2-02.yaml`, exercise `culture-b2-02.e1`.
2. The prompt stem is: `« ___ au mécénat, le festival a pu avoir lieu. »`
3. The MCQ options are: `["Grâce", "À cause", "En raison"]`
4. Insert each distractor into the blank and read the full sentence.

## Expected
All three options should produce grammatically plausible French when inserted (even if semantically wrong), so the learner is choosing on meaning, not on surface grammar.
- "Grâce au mécénat…" — correct ✓
- A competing distractor such as "À cause du mécénat…" — grammatically valid (negative connotation) ✓
- A competing distractor such as "En raison du" — grammatically valid (neutral) ✓

## Actual
- "À cause au mécénat" — ungrammatical. The expression is "à cause **de**"; the contraction of "de + le" is "du", not "au" (which is "à + le").
- "En raison au mécénat" — ungrammatical. The expression is "en raison **de**"; same contraction issue.

Both distractors are immediately eliminable by grammar, not by meaning. A learner who does not know the semantic distinction (positive vs. negative cause) can still pick the correct answer simply because the other two are ungrammatical with the fixed "au" in the stem.

## Notes
Fix options:
- Change the stem to `« ___ du mécénat, le festival a pu avoir lieu. »` and options to `["Grâce", "À cause", "En raison"]` — but then "Grâce du" is wrong ("Grâce à" always contracts to "au"/"à la").
- Keep the stem as-is and replace the distractors with options that work with "à": e.g., `["Grâce", "Suite", "Face"]` giving "Suite au mécénat…" (valid) and "Face au mécénat…" (valid, though unusual).
- Simplest correct fix: keep "Grâce" as answer and replace the two broken distractors with `"Suite"` (suite à = following/due to, positive nuance) and `"Contrairement"` (contrairement à = contrary to, which changes the meaning). Both contract correctly with "au".

## Triage
- status: validated
- rationale: Confirmed in `content/b2/lessons/culture-b2-02.yaml` — the stem fixes "au" (à + le) so "À cause au" and "En raison au" are ungrammatical; both distractors are eliminable by surface grammar alone, making the question test grammar rather than semantics. Real content bug.
- fix_hint: Replace the two broken distractors with prepositions that contract correctly with "au": e.g., `["Grâce", "Suite", "Contrairement"]` — "Suite au mécénat" and "Contrairement au mécénat" are both grammatical with the fixed stem.

## Critic
- final_status: validated
- agree_with_pm: yes
- rationale: Independent verification confirms the analysis. "À cause de" and "En raison de" both require the preposition "de"; combining them with the stem's fixed "au" (= à + le) produces "À cause au mécénat" and "En raison au mécénat" — both ungrammatical in French. A B2 learner who has never encountered "grâce à / à cause de / en raison de" as a semantic triad can still pick "Grâce" simply by recognising that "grâce à" contracts to "grâce au" while the other two take "de" (not "à"). The exercise is intended to test the positive/negative cause distinction (grâce à = positive result; à cause de = negative/neutral), but the ungrammatical distractors reduce it to a surface agreement test. The fix note correctly identifies valid replacement distractors ("Suite", "Contrairement") that contract with "à" and therefore work grammatically with "au" in the stem.
- severity_check: appropriate

## Fix
- changed options in culture-b2-02.e1 from ["Grâce", "À cause", "En raison"] to ["Grâce", "Suite", "Contrairement"]
- both new distractors contract correctly with "au" and require semantic reasoning to eliminate
- pytest: all tests pass; ruff: clean
