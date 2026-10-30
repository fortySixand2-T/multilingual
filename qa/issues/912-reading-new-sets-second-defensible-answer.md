---
id: 912
title: New reading questions with a second defensible option or unclear prompt
severity: low
area: content
persona: exam-crammer
status: done
found: 2026-10-29
---

## Steps to reproduce
Fetch the sets and answer with the distractor named below, `POST /comprehension/sets/<id>/submit`.

## Expected
Exactly one option is supported by the passage; prompts are complete questions.

## Actual
- read-a2-le-mariage-de-lea q4 "Que va faire le petit frère ?": key "Jouer du piano" but distractor "Serrer la main des mariés" is also true for him ("tout le monde va embrasser les mariés et leur serrer la main"). Marking it wrong is unfair.
- read-a1-mon-samedi q2 "Comment va la mère aujourd'hui ?": key "Elle va mieux"; distractor "Elle est toujours malade" is also supported ("Elle est malade depuis longtemps, mais ... elle va mieux" - she is better, not cured).
- read-a1-mon-samedi q3: prompt "La piscine, c'est…" is a sentence fragment, not a question; unclear for an A1 learner what is asked ("la première fois" vs "jamais").
- read-a2-un-message-de-sophie q3: distractor "Suivre la grande rue" is also an instruction in the message.

## Notes
Quotes in all explain strings were checked: each appears verbatim in its passage and supports the key. Answer keys all correct; API scoring (all right = 1.0 pass, all wrong = 0, blank = 0, partial correct) behaves correctly and does not leak answers.


## Triage
- Explanation: Distractors written without checking against the passage; q3 prompt is a fragment.
- Against spec: Unspecified; each question must have one supported answer.
- Verdict: validated
- Rationale: le-mariage-de-lea q4 and mon-samedi q2 have a second true option: unfair marking. Reword options/prompt; un-message-de-sophie q3 and fragment prompt are folded in.

## Critic
- Challenge: Distractors arguable.
- Holds up? Yes for le-mariage-de-lea q4 and mon-samedi q2 (second true option, unfair marking); fragment prompt and sophie q3 folded in.
- Final verdict: validated

## Fix
mariage-de-lea q4 and mon-samedi q2 distractors no longer true; mon-samedi q3 is now a full question; sophie q3 distractor replaced.
