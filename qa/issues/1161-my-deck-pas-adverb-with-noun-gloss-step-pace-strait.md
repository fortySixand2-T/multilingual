---
id: 1161
title: pas is shown as an adverb but glossed with the noun meaning "step, pace, strait"
severity: medium
area: content
persona: exam-crammer
status: done
found: 2026-11-12
---

## Steps to reproduce
1. POST /vocab/personal/preview {"word":"pas"} (fresh DB), or POST /vocab/personal/from-word {"word":"pas"}.

## Expected
pas = adverb/negation particle "not" (the learner's main use), or noun m "step" with pos noun.

## Actual
{"fr":"pas","en":"step, pace, strait","pos":"adverb","gender":"","gender_source":""}
fr_gloss.tsv.gz only has pas as noun m "step, pace, strait"; lexicon.pos overrides pos to the usual adverb but the noun gloss is kept. The saved card (from-word) is identical: pos adverb, en "step, pace, strait". The word means "not" nowhere on the card. Possibly the same mismatch for other words whose usual pos is not in the dictionary entry (not enumerated).

## Notes
enrich.enrich: pos is rewritten after the gloss was chosen for a different pos. 'strait' is also an odd gloss for pas (pas de Calais sense).

## Triage
- Explanation: Reproduced on scratch: pas -> adverb 'step, pace, strait'. TSV has pas only as noun; dictionary.entry() falls back to the first pos, then enrich.enrich calls lexicon.pos() which rewrites noun -> Lexique's usual adverb, leaving a noun gloss under an adverb pos. Same mechanism gives son -> adjective 'sound, bran'.
- Against spec: enrich docstring intends pos and gloss to agree; no explicit spec.
- Verdict: validated
- Rationale: Real, medium: pos and meaning contradict on the card. This is the RUNTIME half of 1146's family. FIX LOCATION: runtime (enrich.py/dictionary.entry): when usual pos is not among the entry's pos values, keep the dictionary's pos (or use a small override for pas = 'not') rather than overriding pos on a gloss for another pos.

## Critic
- Challenge: Edge: only pas/son-type words whose usual pos is absent from the dictionary entry.
- Holds up? Yes. Reproduced in the TSV: pas exists only as 'noun m step, pace, strait' while runtime rewrites pos to adverb, so the card says adverb + noun gloss. Pas is among the most common words; a contradictory card is a real defect. Fix at runtime: do not rewrite pos to one the gloss does not cover (keep the dictionary pos), no new data required.
- Final verdict: validated

## Fix
- `app/content/enrich.py`: a dictionary entry keeps its own part of speech; Lexique's correction now applies only to the model's guess. pas is an adverb glossed "not"; son an adjective glossed "his, her".
