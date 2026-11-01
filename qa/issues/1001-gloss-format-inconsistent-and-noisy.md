---
id: 1001
title: Gloss suffixes are inconsistent and noisy: "(f pl)", "(adj)", "(m)", "(Brit. English: ...)", "while during"
severity: low
area: content
persona: edge-case-breaker
status: done
found: 2026-10-31
---

## Steps to reproduce
Env: B=http://127.0.0.1:9302; T=bearer from POST /auth/signup (invite qa062-a). P(w) = POST $B/vocab/personal/preview -H "authorization: Bearer $T" -d {"word":"w"} (fresh, uncached words, real 7B).
Run P on the words below.

## Expected
Short translation; inflection note only as "(f. pl.)" and only on inflected forms; no grammar labels on base words; no meta commentary.

## Actual
| word | en |
|---|---|
| grandes | large (f pl) |
| longues | long (f pl) |
| sportives | active (f pl) |
| actifs | active (adj) |
| francais | French (m) |
| trottoir | pavement (m) |
| vendeuse | saleswoman (f.) |
| mangeaient | were eating (formal plural past) |
| rez-de-chaussee | ground floor (Brit. English: ground floor) |
| pendant | while during |
| travaux / oeufs / journaux | works (pl.) / eggs (pl.) / newspapers (pl.) |
| parlent | speak (they) |
| chez | at the |

## Notes
Three different spellings of the form note ("f pl", "f. pl.", "pl."), gender tags on base nouns/adjectives, a self-referential Brit. English note, and "chez" glossed "at the" (should be "at the home of / at"). "while during" is two senses jammed together without a separator.

## Triage
- Explanation: Gloss text is stored verbatim from the model (_parse_enrichment en). The prompt only suggests '(f. pl.)'; the 7B improvises '(f pl)', '(adj)', '(m)', '(Brit. English: ...)'. Fully model-driven.
- Against spec: unspecified beyond 893 prompt rule (brackets only for f./pl. forms).
- Verdict: validated
- Rationale: validated (narrow)

## Critic
- Challenge: Entirely 7B improvisation of gloss suffixes ('(f pl)', '(adj)', 'Brit. English'); severity low, cosmetic, and the only remedy is another unbenched prompt rewrite (or regex scrubbing of free text, which risks mangling legitimate glosses). Prompt already asks for '(f. pl.)'. 'chez' = 'at the' and 'while during' are sense quality, not format bugs.
- Holds up? No. Not deterministic, not small, not benchable. Fixer: no change.
- Final verdict: deferred

## Fix
enrich.clean_gloss: inflection notes canonicalised to (f.), (pl.), (f. pl.) and kept on adjectives only; grammar labels ((m), (adj)…) and regional asides (Brit./US/English) dropped; a dangling trailing article removed (chez -> at). Prompt asks for comma-separated senses and no other notes. Sense quality ("while during") remains model-driven. Test: test_clean_gloss_makes_notes_consistent.
