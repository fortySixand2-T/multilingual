---
id: 1101
title: My deck lookup of "peche" gives pêche (fe) with gloss "pear, fishing" (peach missing)
severity: low
area: web
persona: absolute-beginner
status: deferred
found: 2026-10-31
---

## Steps to reproduce
1. /my-deck, type `peche`, Enter, wait for lookup.
2. Look at the result card and, after "Add to my deck", the saved card.

## Expected
Headword pêche, gloss "peach, fishing" (or "fishing, peach"). Ideally the learner sees the ambiguity.

## Actual
Headword "pêche (fe)", IPA /pɛʃ/, meaning prefilled "pear, fishing". "pear" (poire) is wrong; peach, the most common sense of pêche, is absent. The saved card keeps "pear, fishing".

## Notes
Likely 7B gloss quality rather than respell (respell chose pêche correctly), but the lookup then shows a confident wrong card. Also cosmetic: the feminine badge reads "(fe)" while the plan/other screens use f; intentional per VocabWord.tsx, noted only.

## Triage
- Explanation: "pêche" is not in the course content (no yaml/py hit), so the lookup falls through to the LLM-generated gloss (app/content/enrich.py path). Respell picked the correct headword; the wrong "pear" sense is 7B model gloss quality. The "(fe)" badge is the intentional MARK constant in web/src/VocabWord.tsx (`f: "(fe)"`), not a defect.
- Against spec: unspecified for per-word gloss accuracy; "(fe)" is documented in the VocabWord.tsx header comment.
- Verdict: deferred
- Rationale: Real but low severity, and it is model-quality noise with no deterministic code fix. Possible later mitigations: multi-sense prompt or a curated override for common homographs, or letting the learner edit the prefilled meaning (already possible before saving). "(fe)" part rejected as intentional. Not sent to qa-critic as a validated/rejected verdict.

## Critic
- Challenge: Maybe 'pear' is a prompt problem worth fixing. The respell chose pêche correctly; 'pear, fishing' is 7B gloss quality and the learner can edit the Meaning before saving. '(fe)' is the intentional VocabWord badge, confirmed by PM.
- Holds up? Deferral confirmed.
- Final verdict: deferred
