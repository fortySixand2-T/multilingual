---
id: 1123
title: B2 comprehension questions are all verbatim string-matching, no inference (level fit)
severity: low
area: comprehension
persona: exam-crammer
status: deferred
found: 2026-11-01
---

## Steps to reproduce
1. Compare each correct option and its explain with the passage in read-b2-semaine-de-quatre-jours, read-b2-centre-ville-sans-voitures, listen-b2-telephones-a-l-ecole.

## Expected
B2 items test inference, paraphrase or attitude (the TEF B2 range).

## Actual
All 11 questions are answered by locating a phrase and picking the option that copies it (every `explain` quote is the option text, e.g. telephones q3 option = "Apprendre aux jeunes à utiliser le numérique avec esprit critique", script = same words). The 34 s listening with 150 s limit and 3 verbatim items is closer to A2/B1 in task demand, which makes the CLB estimate over-confident for exam-crammer users.

## Notes
Paraphrase the correct options (e.g. 'Former les jeunes à un usage réfléchi du numérique') and add at least one inference/author-stance question per set.


## Triage
- Explanation: Authoring pattern: every explain quotes the option's own words; true across the corpus, not a bug in these sets.
- Against spec: TEF B2 expects inference; no per-set spec requirement.
- Verdict: deferred
- Rationale: Real level-fit weakness for TEF B2 but a broad authoring-policy change (paraphrased options, inference items) affecting all sets, and rewriting 11 items alone would not fix it. Track as a content-quality backlog item; fold paraphrasing into the 1120 option edits where free.

## Critic
- Challenge: Broad authoring-policy item, true corpus-wide, not a defect of these sets; rewriting 11 items alone would not fix it.
- Holds up? yes
- Final verdict: deferred
- Note: Backlog.
