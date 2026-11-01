---
id: 1085
title: "derriere" is tagged pos adjective (1003 leftover)
severity: low
area: content
persona: edge-case-breaker
status: done
found: 2026-10-31
---

## Steps to reproduce
Env: B=http://127.0.0.1:9303; T=bearer from POST $B/auth/signup (invite qa063-b).
1. POST $B/vocab/personal/preview {"word":"derriere"}

## Expected
pos preposition (or adverb).

## Actual
{"fr":"derrière","en":"behind","pos":"adjective",...}. Conjunctions and pronoun now populate correctly (mais, parce que, ou, elle, ni), but lorsque -> adverb and il y a -> verb also remain odd.

## Notes
1003 noted derriere -> adjective explicitly; still reproduces. The Lexique pos override does not correct it (no override for non-noun model tags?).

## Triage
- Explanation: Offline: pos('derrière','adjective') -> 'adjective' while Lexique says preposition (635). lexicon.pos only overrides model pos when it is ''/'noun', so a model 'adjective' is never corrected. Deterministic gap in lexicon.pos.
- Against spec: 1003 intent: closed-class words tagged correctly. Unspecified in the plan beyond QA 1002 intent (fix accent typos, not corrupt correct words).
- Verdict: validated
- Rationale: Real but low (derrière shown as adjective). Fix: also override model adjective/verb when Lexique's dominant pos is preposition/conjunction. Other leftovers (lorsque, il y a) not analysed.

## Critic
- Challenge: Cosmetic, model-quality? Reproduced offline: pos('derrière','adjective') stays adjective though Lexique says preposition (635); live preview shows adjective. Deterministic gap since lexicon.pos only overrides ''/noun. A common word is mislabelled.
- Holds up? Yes, with a tight scope so as not to regress 1000: also override a model 'adjective' only when Lexique's dominant pos is preposition or conjunction (NOT adverb, since many true adjectives are adverbial). I scanned all course yaml entries tagged adjective: none has a Lexique preposition/conjunction pos, so no known regressions. Other leftovers (lorsque, il y a) are out of scope.
- Final verdict: validated

## Fix
Fix: app/content/lexicon.py — pos() overrides a model adjective when Lexique says preposition/conjunction (derrière). Tests: tests/test_enrich.py
