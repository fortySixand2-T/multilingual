---
id: 1179
title: My deck dictionary gloss misses the main meaning: marteau = rapper, door knocker, malleus (no hammer); cuite = batch of ore
severity: low
area: content
persona: edge-case-breaker
status: rejected
found: 2026-11-12
---

## Steps to reproduce
1. POST /vocab/personal/preview {"word":"marteau"}; {"word":"cuite"}.

## Expected
marteau: "hammer". cuite: "(cooked/baked) / hangover, drunkenness".

## Actual
- marteau -> {"en":"rapper, door knocker, malleus","pos":"noun","gender":"m"}  (also what heal_gloss rewrites an old "tool" row to)
- cuite -> {"en":"batch of ore, viewed economically","pos":"noun","gender":"f"}
Also "bœuf" -> "cattle, beef", "regle" returns the course card "ruler" for règle.

## Notes
Data/gloss-table quality (data/fr_gloss.tsv.gz, first-sense heuristics); more in H1 from the other testers. Filed here because heal_gloss also forces these onto previously good cached rows.

## Triage
- Explanation: Duplicate of the gloss-table quality family (1145/1146): marteau/cuite are first-sense picks from the TSV (cuite: only noun 'batch of ore'); hammer is lost by the same filter/first-entry heuristics. The heal_gloss angle is by design (QA 1101 intends dictionary to replace model rows, same pos only) but depends on table quality.
- Against spec: Unspecified.
- Verdict: rejected
- Rationale: Duplicate; add marteau, cuite, boeuf ('cattle, beef') to the 1146 fix's regression list. The 'regle -> course card ruler' item is 1176. Fix in build_gloss_table.py; consider holding heal_gloss until the table is reviewed so it does not worsen good cached rows.

## Critic
- Challenge: marteau (no 'hammer') is a real wrong card.
- Holds up? Rejection holds only as a duplicate: the defect is real but is the 1146 root cause (long first sense dropped). Add marteau, cuite, bœuf to 1146's regression list; 'regle -> ruler' is 1176.
- Final verdict: rejected
