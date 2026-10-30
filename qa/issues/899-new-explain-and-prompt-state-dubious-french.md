---
id: 899
title: "adjectives-a2-01.e5 explain says 'mieux goes with verbs' (contradicted by 'ça va mieux'); adverbs-a2-02.e4 models 'Je préfère plutôt'"
severity: low
area: content
persona: edge-case-breaker
status: done
found: 2026-10-29
---

## Steps to reproduce
1. `a2/adjectives-a2-01.e5`: "« Ce gâteau est ___ que l'autre. »", answer `meilleur`, explain:
   "meilleur is the comparative of the adjective bon (mieux goes with verbs)". This is an over-simplification: "être mieux" / "c'est mieux" / "ce gâteau est mieux" are common predicative uses
   (the course itself teaches "ça va mieux" in `a1/adverbs-01.e7`). The option `mieux` is not clearly wrong here.
   Suggest explain: "With a noun being compared for quality use meilleur(e); mieux is the adverb of bien (il chante mieux)." and/or make the prompt attributive ("un ___ gâteau").
2. `a2/adverbs-a2-02.e4`: "« Je préfère ___ le thé. » (I'd rather have tea)", answer `plutôt`.
   "Je préfère plutôt le thé" is redundant/unnatural French (préférer already means "rather"). Natural: "Je prends plutôt le thé" or "Je préférerais le thé".

## Expected
Explanations state accurate rules; model sentences are natural.

## Actual
As above. Learners are taught a rule contradicted elsewhere in the course and an unidiomatic sentence.


## Triage
- Explanation: Authored explain over-simplifies mieux/meilleur; 'Je préfère plutôt' is redundant.
- Against spec: Spec requires accurate rules; course elsewhere teaches 'ça va mieux'.
- Verdict: validated
- Rationale: Teaches a rule contradicted elsewhere and an unidiomatic model sentence. Reword explain; change sentence to 'Je prends plutôt le thé'.

## Critic
- Challenge: Over-simplified explain is acceptable at this level.
- Holds up? Yes, cheap and accuracy matters; 'Je préfère plutôt' is genuinely redundant. Reword explain and sentence.
- Final verdict: validated

## Fix
Reworded adjectives-a2-01.e5 explain (meilleur qualifies a noun; mieux is the adverb of bien); adverbs-a2-02.e4 now 'Je prends ___ le thé'.
