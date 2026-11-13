---
id: 1162
title: Bare adjective/noun homographs resolve to the noun reading (moyen, général, sourd, muet, ancien, calme, vide, bête, brave, double)
severity: medium
area: content
persona: exam-crammer
status: done
found: 2026-11-12
---

## Steps to reproduce
1. POST /vocab/personal/preview with bare moyen, général (fresh), then sourd, muet, ancien, calme, vide, bête, brave, double.

## Expected
The reading a learner almost always means: moyen/général/ancien/calme/vide/double adjectives (average, general, old/former, calm, empty), with an adjective gloss.

## Actual
Dictionary lists the noun first and Lexique has no usual pos, so the noun wins:
- moyen -> noun m "means"; général -> noun m "general"
- sourd -> noun m "deaf person"; muet -> noun m "mute"; ancien -> noun m "old person"; calme -> noun m "calmness, stillness, coolness (of a person)"
- vide -> noun m "space, vacuum, void"; double -> noun m "double, duplicate"; brave -> noun m "hero"; bête -> noun f "beast, animal" ("stupid" absent)
(moyen, général verified bare-first; the others were first looked up as "un X" in this session, so the cache may have come from the article form: re-test bare-first.) In contrast sec, sauvage, aveugle, sage, grave come out as adjectives.

## Notes
Cache means whoever looks up first decides; cannot be changed by the learner except by editing after the preview. Dictionary.entry picks Wiktionary's first pos when Lexique is silent.

## Triage
- Explanation: Reproduced from the TSV: moyen has noun first ('means') then adjective; bete noun-first. dictionary.entry() uses Lexique usual pos if present, else Wiktionary's first pos, so noun wins whenever Lexique is silent. Note ancien/calme etc. have adjective first in the TSV (ancien adjective listed first), so the reporter's noun results for those came from the cache seeded by 'un X' (1160 mechanism); re-test bare-first before assuming otherwise.
- Against spec: Unspecified.
- Verdict: validated
- Rationale: Real, medium: learners usually mean the adjective for moyen/general/bete/vide/double. FIX LOCATION: scripts/build_gloss_table.py (order pos by Lexique per-pos frequency instead of Wiktionary order) or dictionary.entry (prefer adjective over noun when both exist and Lexique has no usual pos). Dedupes the adjective half of 1160.

## Critic
- Challenge: Reporter's noun results for ancien/calme were partly cache pollution from 'un X' (1160), and a blanket adjective-preference would break genuine nouns (le sourd, un brave).
- Holds up? Yes, narrowly. moyen is noun-first ('means') with the adjective second in the TSV, bête too, so the bare lookup is wrong for them. Scope: order pos by Lexique per-pos frequency (or keep Lexique usual pos), not a blanket adjective-over-noun rule; re-test bare-first.
- Final verdict: validated

## Fix
- `scripts/build_gloss_table.py`: parts of speech are written most frequent first by Lexique per-pos frequency (vide, sourd, ... lead with the adjective), plus `ADJECTIVE_FIRST` for moyen and bête where Lexique counts the noun more often but a learner means the adjective.
