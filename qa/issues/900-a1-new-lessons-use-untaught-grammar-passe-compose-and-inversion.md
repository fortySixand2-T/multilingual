---
id: 900
title: "A1 time-words-02 and adverbs-02 use passé composé and inverted questions that no A1 lesson teaches"
severity: low
area: content
persona: edge-case-breaker
status: deferred
found: 2026-10-29
---

## Steps to reproduce
1. `a1/time-words-02.e5`: "« Tu as ___ mangé ? » (Have you already eaten?)" with explain
   "déjà … placed between avoir and the past participle". No A1 lesson teaches the passé composé
   (`grep -l "passé composé" content/a1/lessons/*.yaml` is empty; `a1` has no past-participle exercise).
2. `a1/adverbs-02.e6`: word_bank "Pourquoi es-tu dehors ?" (inversion). No other A1 lesson uses `-tu`/`-vous` inversion (`grep -rn -- "-tu " content/a1/lessons` finds only this one).

## Expected
A1 exercises stay inside A1 grammar, or the explain introduces the structure (a one-line gloss of "tu as mangé = you ate/have eaten").

## Actual
Unexplained structures at the end of the A1 path; a beginner cannot parse the sentence they are asked to complete/build.

## Notes
Low; vocabulary being tested is fine. Could use "Tu es déjà là ?" and "Pourquoi tu es dehors ?" to stay at level.


## Triage
- Explanation: A1 lessons use passé composé (tu as déjà mangé) and -tu inversion without teaching them; same family as existing 755 (lesson-vocab/grammar coherence).
- Against spec: 755 is the existing tracker; no A1 spec ban on exposure.
- Verdict: deferred
- Rationale: Real but a widespread pattern already tracked; address under 755 (cheap rewording: 'Tu es déjà là ?'). Not a standalone fix now.

## Critic
- Challenge: Real but same as 755.
- Holds up? PM deferral is right; folded into 755.
- Final verdict: deferred
