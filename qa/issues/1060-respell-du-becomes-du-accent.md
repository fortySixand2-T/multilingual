---
id: 1060
title: Typing accentless 'du' stores headword 'dû' (verb) with gloss 'of'
severity: high
area: content
persona: edge-case-breaker
status: done
found: 2026-10-31
---

## Steps to reproduce
Target http://127.0.0.1:9303 (signed up with qa063-a, bearer token).
1. POST /vocab/personal/preview body {"word":"du"}

## Expected
fr stays "du" (the article 'of the'); the learner meant the most common word.

## Actual
{"enrichment":{"fr":"dû","en":"of","pos":"verb","gender":"","ipa":"dy",...}} fr/en mismatch (dû is past participle of devoir), pos verb, and this wrong headword is cached/shared.

## Notes
H1 confirmed. lexicon.respell prefers the accented variant for du, even though the model's own headword was probably du. Respell should not override a headword that is itself a valid word more frequent than the accented one.

## Triage
- Explanation: Offline repro: lexicon._forms() has no entry for 'du' or 'des' (Lexique lacks them), so _respell_word sees an unknown typed spelling, finds best['du']='dû' (verb, freq 620) and treats it as a misspelling. lookup._headword then accepts it (same slug). Deterministic, in lexicon.respell.
- Against spec: Unspecified in the plan beyond QA 1002 intent (fix accent typos, not corrupt correct words). Respell exists for misspellings like chausseé, not for the top-10 articles.
- Verdict: validated
- Rationale: Real bug, primary for the du/des class (dup: 1061, 1100). A top-10 word is stored/cached wrong with gloss/headword mismatch. Fix: pin/skip respell for words absent from Lexique that are closed-class (du, des, ...) or when the model's own headword equals the typed spelling and a gloss disagrees with the accented variant.

## Critic
- Challenge: Respell is meant for misspellings; maybe the model/7B is at fault. Reproduced offline: lexicon.respell('du')='dû', respell('des')='dès' because Lexique has no entry for du/des (forms.get -> None), so the unknown-spelling branch fires regardless of what the model said. Also live preview of du/des returns dû/dès. Deterministic, top-10 words, cached and shared; learner impact real (wrong headword on a core word).
- Holds up? Yes. Fix must be minimal and not regress 1002: add a tiny keep-as-typed set for valid words missing from Lexique (du, des; au/aux already survive) checked in _respell_word before the unknown-spelling branch. chausseé/à côté de are untouched (a côté de relies on à being more frequent than a, and on cote being 55x rarer than côté; neither path involves the pin). Do NOT add a general 'typed word is a known form' rule; it would break cote->côté. Folded duplicates: 1061 (des) and 1100 (My deck UI path) - add des and du to the regression test; no separate work.
- Final verdict: validated

## Fix
Fix: app/content/lexicon.py — _KEEP_AS_TYPED (du, des) skipped in _respell_word; also covers 1061/1100. Tests: tests/test_enrich.py
