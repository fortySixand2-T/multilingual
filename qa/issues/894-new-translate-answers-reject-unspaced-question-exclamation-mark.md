---
id: 894
title: "8 new translate exercises reject the unspaced '?' / '!' form (e.g. 'Arrête!', 'Ça suffit!') that bare-keyboard learners type"
severity: medium
area: content
persona: edge-case-breaker
status: done
found: 2026-10-29
---

## Steps to reproduce
1. Read the `translate` exercises below (or `GET /content/lessons/<id>` with a token).
   The client check is `norm(val) === norm(a)` over `[answer, ...accept]` with
   `norm = trim + lowercase + collapse whitespace` (`web/src/screens/Lesson.tsx:7,213-219`).
   It does not strip or normalise punctuation.
2. In each exercise the answer ends in a spaced ` ?` / ` !` and `accept` has no
   unspaced variant. Type the answer the way an English-keyboard learner does (no space
   before the mark).

Affected (answer -> rejected input):
- `a1/people-01.e7` `quel est votre nom ?` -> "Quel est votre nom?"
- `a2/verbs-a2-01.e7` `arrête !` -> "Arrête!" (bare "arrête" is accepted, "arrête!" is not)
- `a2/verbs-a2-04.e7` `ne bouge pas !` -> "Ne bouge pas!"
- `a2/verbs-a2-05.e7` `pouvez-vous répéter, s'il vous plaît ?` -> "Pouvez-vous répéter, s'il vous plaît?" (also the comma form without "?" is rejected)
- `a2/reflexives-a2-01.e6` `on s'est amusés !` -> "On s'est amusés!"
- `a2/adjectives-a2-01.e8` `tu es sûr ?` -> "Tu es sûr?"
- `b1/ideas-b1-02.e8` `bonne chance !` -> "Bonne chance!"
- `b1/verbes-b1-04.e8` `ça suffit !` -> "Ça suffit!"

## Expected
A fully correct answer typed with the unspaced mark ("Arrête!") is marked correct.

## Actual
"Not quite — keep going." although the French is correct. A script over all lessons shows
these 8 are the ONLY translate answers in the whole course ending in ` ?`/` !`; all 8 fail
the unspaced form. Older lessons avoid terminal punctuation in `answer`, so this pattern is
new with this content.

## Notes
Fix in content: drop the terminal punctuation from `answer` (accept both), or add the
unspaced variant to every `accept`. Better: make `norm()` strip `[?!.]` and the space before it.


## Triage
- Explanation: Lesson.tsx norm() only trims/lowercases/collapses whitespace; no punctuation handling. Accept lists for these 8 end in spaced ' ?'/' !' with no unspaced variant (bare form accepted for some).
- Against spec: Unspecified; norm() rule in CLAUDE/Lesson.tsx.
- Verdict: validated
- Rationale: A correct answer typed the normal English-keyboard way is marked wrong: unfair marking on 8 exercises. Fix by making norm() strip terminal [?!.] and the preceding space (fixes all at once).

## Critic
- Challenge: Only 8 exercises; could just add accept variants.
- Holds up? Yes. norm() (Lesson.tsx:7) does no punctuation handling; verified. Correct answers marked wrong; single-place norm() fix is simpler than 8 edits.
- Final verdict: validated

## Fix
norm() in web/src/screens/Lesson.tsx now drops the space before ? ! : ; so 'Arrête!' matches 'arrête !' (test in Lesson.test.tsx).
