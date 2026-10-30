---
id: 901
title: "time-words-01.e5 and verbs-a2-01.e6 word banks allow a second valid word order that is marked wrong"
severity: low
area: content
persona: edge-case-breaker
status: done
found: 2026-10-29
---

## Steps to reproduce
Client check is exact array equality with `answer` (`WordBank` in `web/src/screens/Lesson.tsx`).
1. `a1/time-words-01.e5` "I often work at night", tokens `[Je, travaille, souvent, la, nuit, toujours]`, answer `Je travaille souvent la nuit`.
   Build "Je travaille la nuit souvent" (valid French, adverb at the end).
2. `a2/verbs-a2-01.e6` "I left the office at six", tokens `[J'ai, quitté, le, bureau, à, six, heures, suis]`, answer `J'ai quitté le bureau à six heures`.
   Build "À six heures j'ai quitté le bureau" is not offered (case of tiles) but "J'ai quitté à six heures le bureau" is not valid, so only #1 is a clean case; #2 is note-only: capitalised first tile `J'ai` blocks the fronted-time-phrase order.

## Expected
Either token sets that leave only one natural order, or accepting alternates.

## Actual
"Je travaille la nuit souvent" -> "Not quite".

## Notes
Low severity; only time-words-01.e5 is a clean double-answer.


## Triage
- Explanation: word_bank check is exact array equality; token set for time-words-01.e5 permits two valid orders.
- Against spec: Unspecified.
- Verdict: validated
- Rationale: 'Je travaille la nuit souvent' is valid French marked wrong: fix by removing a token/adding the order. Second part (verbs-a2-01.e6) is not a bug and is rejected.

## Critic
- Challenge: Part 2 is not a bug.
- Holds up? Yes for time-words-01.e5 only (Je travaille la nuit souvent is valid); drop verbs-a2-01.e6 part.
- Final verdict: validated

## Fix
time-words-01.e5 now 'I work at night' with distractor 'jamais', leaving a single valid order (verbs-a2-01.e6 not a bug).
