---
id: 1082
title: "boeuf" keeps the unligatured headword and glosses as "cow, ox" (oeuf/oeil/coeurs are restored)
severity: low
area: content
persona: edge-case-breaker
status: done
found: 2026-10-31
---

## Steps to reproduce
Env: B=http://127.0.0.1:9303; T=bearer from POST $B/auth/signup (invite qa063-b).
1. POST $B/vocab/personal/preview {"word":"boeuf"}
2. Control: {"word":"oeil"}, {"word":"oeufs"}, {"word":"coeurs"}, {"word":"soeur"}.
3. POST $B/vocab/personal/from-word {"word":"boeuf"} then GET $B/vocab/personal.

## Expected
fr "bœuf" (ligature restored like œil, œufs, cœurs, sœur); en "beef, ox".

## Actual
Step 1: {"fr":"boeuf","en":"cow, ox","pos":"noun","gender":"m","ipa":"bœf"} - the IPA has œ, the headword does not. Controls: œil, œufs, cœurs, sœur all restored. Step 3 stores fr "boeuf", en "cow, ox" (a cow is "vache"; boeuf is beef/ox).

## Notes
Ligature restoration is table/model dependent; boeuf is not in the oe-ligature set. Gloss is model quality but is shown to learners.

## Triage
- Explanation: Lexique stores boeuf without a ligature and has no bœuf form, so respell cannot restore it; oeil/oeufs/coeurs work only because the model proposed œ. Gloss 'cow, ox' is the 7B. Both are model/data-table limits, not a regression of #133.
- Against spec: Unspecified. Not a respell/pos/clean_gloss defect.
- Verdict: deferred
- Rationale: Low; a small ligature word table (boeuf, voeu, noeud) could be a future content tweak.

## Critic
- Challenge: Is it a regression? No: respell cannot restore a ligature Lexique lacks, and 'cow, ox' is 7B. Low value, model/data limits.
- Holds up? Deferral confirmed.
- Final verdict: deferred

## Fix
lexicon.respell writes œ where French does (oe before u or il: bœuf, vœu, cœur, œil, chef-d'œuvre; coefficient and moelle keep oe). The prompt now asks for a list of senses; against the real 7B boeuf gives "cattle, beef" (was "cow, ox"). Test: test_respell_writes_the_oe_ligature.
