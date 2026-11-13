---
id: 1145
title: My deck preview: glosses add rare/wrong extra senses next to the right one (traduire 'to summon', fraise 'bulwark, palisade', saumon 'wingtip')
severity: medium
area: content
persona: returning-learner
status: deferred
found: 2026-11-12
---

## Steps to reproduce
1. Sign up with invite code qa065-a, then for each word below call `POST /vocab/personal/preview {"word": "<w>"}` (Bearer token).
2. Read `enrichment.en` / `pos` / `gender` as a learner adding the word to My deck.

## Expected
A learner-facing gloss lists the everyday meaning(s). Rare or technical extra senses should be dropped or the second piece should be a real common meaning.

## Actual
- `traduire` -> "to translate, to summon"
- `réclamer` -> "to protest, to object" (real meaning: to demand / claim; wrong first sense)
- `visser` -> "to screw in, to screw on, to serve"
- `fraise` -> "strawberry, bulwark, palisade"; `poire` -> "pear, bulb, usually pear-shaped" (fragment)
- `saumon` -> "salmon (fish), wingtip (of an aircraft)"; `mouche` -> "fly (insect), bullseye"; `rat` -> "rat, scrooge"
- `raisin` -> "grape, size of paper"; `haricot` -> "bean, green bean, kidney dish"; `collège` -> "academy, junior high school"
- `bouquin` -> "old, worn-out book, buck" (should be "book (informal)"; "buck" is nonsense)
- `rang` -> "knitting course" (should be "rank, row"); `file` -> "traffic jam" (should be "line, queue")
- `foule` -> "crowd, oppression, vexation"; `bouteille` -> "bottle, alcohol"; `autobus` -> "bus (Québec)" (standard French, not Québec-only); `texte` -> "text (piece of writing), original"; `morceau` -> "piece, slice, work"
- `plaindre` -> "to pity, to complain" (complain is se plaindre)

## Notes
Root cause: gloss() takes the first sense of each same-pos entry (homograph entries) up to MAX_SENSES=2, MAX_PIECES=3, so the second entry's first sense (often a technical/etymologically unrelated word) is appended regardless of relevance. Suggest: only add a second sense from another etymology entry when the word is frequent in that sense, or cap to the first entry unless it is a known homograph (pêche).

## Triage
- Explanation: Reproduced from the TSV logic: build_gloss_table.gloss() takes the first sense of EACH same-pos Wiktionary entry (homograph/etymology entries) up to MAX_SENSES=2, so an unrelated second entry's first sense is appended (fraise 'bulwark', saumon 'wingtip').
- Against spec: Unspecified.
- Verdict: validated
- Rationale: Real but medium: the main meaning is usually still present and the learner can edit before adding; extra noise and some fragments ('usually pear-shaped'). FIX LOCATION: scripts/build_gloss_table.py (second sense only from a different entry when that entry is common; drop fragments; filter register labels like Quebec). Some listed items (rang, file, reclamer) are really main-meaning-lost cases, same root as 1146.

## Critic
- Challenge: Main meaning is present in most listed cases (strawberry, salmon, rat, bean); the extra sense is noise the learner can edit away. Any fix is a heuristic on which homograph entry is 'common' that needs data we do not have, with real risk of dropping legitimate second senses (pêche). Items where the main meaning is lost (rang, file, réclamer, bouquin) are really 1146.
- Holds up? Partly. Cosmetic/noise rather than a wrong card; the genuinely wrong cases belong to 1146. Not worth a heuristic now.
- Final verdict: deferred
