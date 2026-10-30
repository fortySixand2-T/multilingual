---
id: 951
title: New path units reuse unrelated icons (keyword-matched), duplicating neighbours' icons
severity: low
area: content
persona: absolute-beginner
status: deferred
found: 2026-10-29
---

## Steps to reproduce
1. Log in, Learn tab, level A1 then switch the Level selector to A2 and B1; scroll to the new units at the end of each path.

## Expected
Each unit has a distinct, meaningful icon; no book-glyph fallback.

## Actual
No book fallback (good), but icons look arbitrary or repeat existing ones:
- A1 "Describing things" = palette, same as "Colours" (a1.u21 icon `palette`); A1 "Little words" = lightbulb.
- A2 "Where, and what you notice" = wave/hello glyph; "Sure, fair, the same" = smiley; "Take, bring, let go" = shopping bag (same as "Giving and taking"); "Reflexive verbs" = two-people glyph; "Since, so, like" = clock; "Things you do" and "Comings and goings" both lightning.
- B1 "Small nouns, big expressions" = numbers glyph; "It seems, it's worth it" and "However, therefore" both scales; "Finding, saving, knocking" = target.
Icons for A2/B1 verb/adverb units suggest unrelated topics (hello, shopping, numbers) to a beginner skimming the path.

## Notes
Cosmetic. Icon keys come from path.yaml; pick generic glyphs for abstract word-class units.


## Triage
- Explanation: Icon keys chosen in path.yaml by keyword; limited glyph set.
- Against spec: Design choice; no book fallback occurs.
- Verdict: deferred
- Rationale: Cosmetic/product choice. Revisit when the icon set is expanded.

## Critic
- Challenge: Cosmetic design choice.
- Holds up? PM deferral right.
- Final verdict: deferred
