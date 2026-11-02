---
id: 1108
title: Listening b1-un-voisin-courageux: 'il ne faut jamais choisir de rester dans un bâtiment en feu' is unnatural and Q3 paraphrase drops the word
severity: low
area: comprehension
persona: returning-learner
status: rejected
found: 2026-11-01
---

## Steps to reproduce
1. Sign in (invite qa064-a) at http://127.0.0.1:9304 and GET /comprehension/sets/listen-b1-un-voisin-courageux (source: content/b1/comprehension/listen-b1-un-voisin-courageux.yaml).
2. Read the passage/script and questions as a native French reviewer.

## Expected
« Les pompiers rappellent qu'il ne faut jamais rester dans un bâtiment en feu : on risque de respirer une fumée toxique. »

## Actual
« il ne faut jamais choisir de rester dans un bâtiment en feu : c'est risquer de respirer une fumée toxique. » Nobody 'chooses' to stay in the warning; headword 'choisir de' forced. Q3's answer (« Il ne faut jamais rester dans un bâtiment en feu ») then differs from the audio the learner heard, while its explain quotes the 'choisir de' form.



## Triage
- Explanation: 'il ne faut jamais choisir de rester' forces headword 'choisir de'; Q3 option (without 'choisir de') differs from the heard sentence.
- Against spec: Unspecified.
- Verdict: validated
- Rationale: 'choisir de rester dans un bâtiment en feu' in a safety warning is odd; the option paraphrase is fine but the audio sentence is unnatural. Low severity; requires audio re-render and keeping 'choisir de' covered elsewhere or reworded naturally (e.g. 'ne faut jamais choisir de rester chez soi quand...').

## Critic
- Challenge: 'ne faut jamais choisir de rester dans un bâtiment en feu' is grammatical and understandable (one can choose to stay, e.g. to protect belongings, as the old lady nearly did); the Q3 option is a legitimate paraphrase of a heard sentence. Not an error, only mild stiffness. The only 'choisir de' occurrence is this sentence, so a rewrite risks the 100% coverage gate for no learner benefit.
- Holds up? no - preference, and the fix adds gate/audio risk
- Final verdict: rejected
- Note: PM's own rationale conceded it is 'odd' not wrong; evidence balanced so no change. If dev-fixer re-renders this audio for 1107 anyway, leave this sentence untouched.
