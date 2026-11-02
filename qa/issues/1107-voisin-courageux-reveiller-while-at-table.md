---
id: 1107
title: Listening b1-un-voisin-courageux: residents are at dinner yet Karim knocks 'pour réveiller les habitants' (and Q1 asks how he 'réveillé' them)
severity: medium
area: comprehension
persona: returning-learner
status: done
found: 2026-11-01
---

## Steps to reproduce
1. Sign in (invite qa064-a) at http://127.0.0.1:9304 and GET /comprehension/sets/listen-b1-un-voisin-courageux (source: content/b1/comprehension/listen-b1-un-voisin-courageux.yaml).
2. Read the passage/script and questions as a native French reviewer.

## Expected
A coherent story. Suggested script: « ... Karim ... a senti la fumée. Il est allé frapper à toutes les portes pour prévenir les habitants. » and Q1 « Comment Karim a-t-il prévenu les habitants ? » (update explain too and re-render audio).

## Actual
Script: « Hier soir, un incendie ... Beaucoup d'habitants venaient de se mettre à table et n'ont pas eu le temps de finir de manger. ... Il est allé frapper à toutes les portes pour réveiller les habitants. » People who just sat down to eat are not asleep. Q1 « Comment Karim a-t-il réveillé les habitants ? » repeats the contradiction. 'finir de manger' / 'se mettre à table' also look forced in to cover headwords.



## Triage
- Explanation: Script says residents had just sat down to eat, then Karim knocks 'pour réveiller les habitants'; Q1 repeats 'réveillé'.
- Against spec: Spec: natural, coherent graded text.
- Verdict: validated
- Rationale: Real coherence error: people at dinner are not asleep. Q1 and the explain quote carry it; audio needs re-render. Keep 'se mettre à table' and 'finir de' covered (gate=100). Suggested 'prévenir/alerter' fix is correct.

## Critic
- Challenge: Challenge: stylistic? No. Residents who 'venaient de se mettre à table' are awake, and Q1/explain say 'réveillé'. A learner hears an incoherent story and Q1 asks a false-premise question. Reproduced in YAML lines 11-14.
- Holds up? yes - genuine coherence error
- Final verdict: validated
- Note for dev-fixer: Fix script + Q1 + explain, and re-render the mp3 (same re-render as any change to this file). Keep 'se mettre à table', 'finir de' covered.

Fix: content/b1/comprehension/listen-b1-un-voisin-courageux.yaml — script/Q1/explain now 'prévenir'; mp3 regenerated (34 s vs 120 s limit).
