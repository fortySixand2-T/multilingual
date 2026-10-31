---
id: 893
title: Lookup gloss is a wrong sense or a definition, not a translation (education -> educate|training, éléphant -> large land mammal)
severity: medium
area: content
persona: edge-case-breaker
status: done
found: 2026-10-27
---

## Steps to reproduce
Env: B=http://127.0.0.1:9300; T=<bearer from POST /auth/signup, invite qa060-b>. P(w) = curl -s $B/vocab/personal/preview -H "authorization: Bearer $T" -H 'content-type: application/json' -d '{"word":"w"}'
1. P(education) -> en "educate|training".
2. P(elephant) -> en "large land mammal"; P(grandes) -> pos "" en "large"; P(apres) -> pos ""; P(francais) -> pos "" en "French"; P(garcon) -> "boy|male youth"; P(travaux) -> "works|labors"; P(a la maison) -> pos "preposition".

## Expected
Short learner gloss, correct sense ("education", "elephant", "tall/big (f. pl.)" or "(f. pl.)" note), pos populated, no pipe fragments (884 covers pipes generally).

## Actual
education glossed as a verb ("educate") with a noun pos; elephant given a dictionary definition; plural/feminine adjective forms lose the form info (grandes -> "large", no "f. pl." note) and pos is empty for grandes/apres/francais; "à" gets gender m. Not covered by 884, which is only the pipe separator.

## Notes
Same shared cache means one bad gloss reaches every learner.

## Triage
- Explanation: Gloss/pos come from the single 7B `vocab_enrich` LLM pass (`enrich.propose`); sense choice and definition-style glosses are model quality. Pipes are covered by 884. Empty `pos` occurs when the model returns a value outside `_POS_VALUES`. "à" gets gender m because `resolve_gender` only blocks the LLM gender when pos is non-empty, so empty pos lets a guessed gender through.
- Against spec: Gloss quality is not specified beyond "short gloss"; not part of the pronunciation/word complaint.
- Verdict: deferred
- Rationale: Real but model-quality and subjective; no deterministic fix without a better model/dictionary source (Lexique/next slice). Two cheap items may ride along with the 891 prompt edit if trivial, not as separate work: tighten the prompt ("a translation, not a definition; note form e.g. 'f. pl.' only if inflected") and ignore the LLM gender when pos is empty. Do not block the slice on this; re-file with a concrete failing word list after the headword fix lands (gloss for a corrected headword may improve on its own).


## Critic
- Challenge: The two cheap ride-alongs (prompt tightening, ignore LLM gender when pos empty) could be done now.
- Holds up? Deferral stands, and the ride-alongs are struck: model-quality tuning of the prompt is untestable without a real LLM and risks regressing 891's headword output; gender-when-pos-empty is a separate behaviour change to resolve_gender. Re-file with a concrete failing list after the headword fix.
- Final verdict: deferred

## Fix
Three changes in `app/content/enrich.py`. (1) The model's gender is used only when pos is `noun`, so "à" with an empty pos no longer gets m. (2) `_pos` maps pos variants (`adj`, `Adverb (time)`, `prep.`) onto the known values instead of dropping them to "". (3) The gloss rule asks for a learner translation, not a definition, with an (f. pl.) note for inflected forms. Tests cover (1) and (2). (3) is a prompt change and was NOT benched against the box's 7B model in this pass. Already-cached lookups keep their old gloss until re-looked-up.
