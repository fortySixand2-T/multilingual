---
id: 1065
title: Lookup 'pas' glossed 'step, pace' gets pos adverb, gender dropped (also 'le pas')
severity: medium
area: content
persona: edge-case-breaker
status: done
found: 2026-10-31
---

## Steps to reproduce
Target http://127.0.0.1:9303 (signed up with qa063-a, bearer token).
1. POST /vocab/personal/preview body {"word":"pas"}
2. Repeat with {"word":"le pas"}

## Expected
pos noun, gender m for 'step, pace' (the learner typed 'le pas' explicitly in step 2).

## Actual
Both return {"fr":"pas","en":"step, pace","pos":"adverb","gender":""}. Explicit article 'le' is ignored by the pos override.

## Notes
H4 confirmed. Same cause as 1064; an article in the input is a strong noun signal and should block the flip.

## Triage
- Explanation: Duplicate of 1064: pos('pas','noun') -> 'adverb'. Extra point: strip_leading_article discards 'le' in enrich(), so the explicit article never reaches pos(); plumb 'had article' through to block the flip.
- Against spec: Unspecified in the plan beyond QA 1002 intent (fix accent typos, not corrupt correct words).
- Verdict: validated
- Rationale: Duplicate of 1064; the article-signal is a concrete fix hint.

## Critic
- Challenge: pas really is mostly an adverb; flipping is by design. Agreed for bare 'pas'. But live: 'le pas' also returns adverb, pos adverb, no gender, even though the learner typed an article, the one unambiguous noun signal. strip_leading_article in enrich() discards it before lexicon.pos runs.
- Holds up? Yes, narrowed: validated ONLY as 'a typed leading article (le/la/l'/un/une/les...) keeps the model noun and skips the Lexique flip'. Does not regress 1000: those cases are typed bare (grandes, petites), and the flip still applies there. Do not change bare-word behaviour. Folds 1064 ('le son' -> noun m) and 1066 ('la mure' -> noun f); add those as test cases. Caveat: preview of 'le pas'/'le son'/'la mure' currently all stay flipped (verified live, though cached).
- Final verdict: validated

## Fix
Fix: app/content/lexicon.py + enrich.py — a typed leading article (le pas, le son, la mure) keeps pos noun via lexicon.pos(article=True); also covers 1064/1066; bare words unchanged. Tests: tests/test_enrich.py
