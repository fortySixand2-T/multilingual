---
id: 898
title: "ideas-b1-01 mcq prompts have no English cue and a second grammatical option (e4 'Un amour…', e5 'dire une vérité')"
severity: low
area: content
persona: edge-case-breaker
status: done
found: 2026-10-29
---

## Steps to reproduce
1. `b1/ideas-b1-01.e4`: "« ___ amour est plus fort que tout. »", options `L'`, `Un`, `De l'`, answer `L'`.
   "Un amour est plus fort que tout" is grammatical (a particular love), and nothing in the prompt says it is a general statement.
2. `b1/ideas-b1-01.e5`: "« Il faut dire ___ vérité. »", options `la`, `une`, `de`, answer `la`.
   "Il faut dire une vérité" is grammatical ("one truth"). Compare e4/e6 in other lessons, which carry an English cue in parentheses.
3. Pick `Un` / `une`.

## Expected
Prompt includes a cue that makes only the definite article correct ("(love, in general)", "(to tell the truth)"), or the distractor is plainly ungrammatical.

## Actual
A learner who picks a grammatical option is told "Not quite" and the explain ("A general idea takes the definite article")
does not address why theirs fails.

## Notes
The lesson's grammar point is exactly the generic-vs-indefinite contrast, so the missing cue matters.


## Triage
- Explanation: mcq distractors Un/une are grammatical; prompts lack the cue other lessons carry.
- Against spec: Lesson's grammar point is generic-vs-indefinite; a cue is required to make the item single-answer.
- Verdict: validated
- Rationale: Learner who picks a grammatical option is marked wrong with an explain that does not address it. Add English cue (e.g. 'love, in general') to e4/e5.

## Critic
- Challenge: Learner who picks Un is merely taught the rule.
- Holds up? Yes: verified e4/e5 prompts (ideas-b1-01) have no cue and Un/une are grammatical; a cue is a one-line fix.
- Final verdict: validated

## Fix
Added English cues '(love, in general)' / '(to tell the truth)' to ideas-b1-01 e4/e5 prompts.
