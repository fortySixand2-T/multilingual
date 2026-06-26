---
id: 402
title: word_bank prompt says "global warming" but answer omits "climatique"
severity: medium
area: content
persona: edge-case-breaker
status: done
found: 2026-06-25
---

## Steps to reproduce
1. Open lesson `environnement-b1-01`, exercise e4 (`environnement-b1-01.e4`).
2. Read the prompt: "Build: 'global warming is faster'".
3. Look at the answer tokens: `[le, rechauffement, est, plus, rapide]`.

## Expected
The French answer should translate back to "global warming is faster". The standard French term for "global warming" is "le rechauffement climatique", so the answer should be "le rechauffement climatique est plus rapide" and the tokens should include "climatique".

## Actual
The answer builds to "le rechauffement est plus rapide" which means "the warming is faster" -- the word "climatique" is missing. The English prompt promises "global warming" but the French answer only says "warming" without the qualifier.

## Notes
Either add "climatique" to the tokens and answer, or change the English prompt to just "warming is faster". The current mismatch teaches an incorrect translation of "global warming".
File: `content/b1/lessons/environnement-b1-01.yaml`, exercise e4.

## Triage
- Explanation: Exercise e4 in environnement-b1-01.yaml prompts "Build: 'global warming is faster'" but the answer tokens produce "le rechauffement est plus rapide" which means "the warming is faster". The standard French for "global warming" is "le rechauffement climatique" -- the word "climatique" is absent from both the tokens list and the answer. The vocab deck itself defines rechauffement as "warming (climate)" (parenthetical qualifier, not "global warming"), which is internally consistent with the answer but contradicts the English prompt.
- Against spec: The spec requires content correctness (AC1.1 content authored as YAML). A word_bank exercise whose English prompt does not match its French answer is a factual content error.
- Verdict: validated
- Rationale: A learner completing this exercise would be taught that "global warming" translates to "le rechauffement" without "climatique", which is incorrect. The simplest fix is to change the prompt from "global warming is faster" to "warming is faster" (aligning with the vocab deck's own definition). Alternatively, add "climatique" to both tokens and answer. Either way, the current mismatch is a real content error that teaches an incorrect translation.

## Critic
- Challenge: Could "le rechauffement" be understood as "global warming" in context, making the prompt acceptable without "climatique"? In everyday French, "le rechauffement" is sometimes used as shorthand for "le rechauffement climatique", much like English speakers say "warming" to mean "global warming". The lesson title is "Climate change" and the exercise sits alongside climate-related vocab (environnement, pollution, climat), so contextual disambiguation is arguably sufficient. Also, the vocab deck itself defines rechauffement as "warming (climate)" with a parenthetical qualifier, suggesting it already carries the climate connotation implicitly.
- Holds up? Yes, the PM's validation survives. While contextual shorthand exists in casual French, this is a language-learning platform teaching B1 students who need precise translations. The prompt explicitly says "global warming" -- not "warming" -- and the correct French for that specific term is "le rechauffement climatique". The deck's own parenthetical "(climate)" is a usage hint, not part of the translation, and the deck does NOT define it as "global warming". Worse, the token list includes "climat" (the noun) as a distractor, but "climatique" (the adjective needed for grammatical correctness) is absent -- so even an alert learner who suspects something is off cannot construct the right answer. This teaches an incorrect equivalence: "global warming" = "le rechauffement". The fix is trivial (change prompt to "warming is faster") and the harm is real (incorrect translation reinforced through active recall).
- Final verdict: validated

## Fix
Changed exercise e4 prompt from "global warming is faster" to "warming is faster" in `content/b1/lessons/environnement-b1-01.yaml`, aligning the English prompt with the French answer `[le, rechauffement, est, plus, rapide]` and the vocab deck definition of `rechauffement` as "warming (climate)".
