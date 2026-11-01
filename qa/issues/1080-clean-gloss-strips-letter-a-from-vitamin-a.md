---
id: 1080
title: Gloss cleaning strips the trailing letter A from "vitamin A" (vitamine A -> "vitamin")
severity: medium
area: content
persona: edge-case-breaker
status: done
found: 2026-10-31
---

## Steps to reproduce
Env: B=http://127.0.0.1:9303; T=bearer from POST $B/auth/signup (invite qa063-b).
1. POST $B/vocab/personal/preview {"word":"vitamine A"}
2. Control: {"word":"vitamine C"} and {"word":"vitamine B12"}.
3. POST $B/vocab/personal/from-word {"word":"vitamine A"} then GET $B/vocab/personal.

## Expected
en "vitamin A" (as vitamine C gives "vitamin C").

## Actual
Step 1: {"enrichment":{"fr":"vitamine A","en":"vitamin","pos":"noun","gender":"","ipa":"vitamin a",...}}. Step 2: en "vitamin C" / "vitamin B12" intact. Step 3: the saved card is stored with en "vitamin" (the wrong gloss is persisted and shared via the lookup cache). Same for "vitamine A." (trailing dot).

## Notes
app/content/enrich.py _TRAILING_ARTICLE = \s+(?:the|a|an)$ with re.I strips a legitimate final letter "A" (also "Plan A", "vitamin A", "Type A"). Only strip lowercase a/the/an or only when the gloss has more than the dangling article; case-sensitive match would fix it. Also IPA is "vitamin a" (Latin text, not IPA) for these.

## Triage
- Explanation: Offline: clean_gloss('vitamin A','noun') -> 'vitamin'. _TRAILING_ARTICLE=\s+(?:the|a|an)$ with re.I strips a legitimate capital A (Plan A too). Deterministic, enrich.py:229.
- Against spec: Round-063 hypothesis H5 predicted this. Unspecified in the plan beyond QA 1002 intent (fix accent typos, not corrupt correct words).
- Verdict: validated
- Rationale: Real: wrong gloss persisted and shared via lookup cache. Fix: drop re.I for the 'a' (strip lowercase only), keep capitals.

## Critic
- Challenge: Rare gloss. But reproduced offline: clean_gloss('vitamin A')='vitamin', 'Plan A'->'Plan', 'Type A'->'Type', and live preview of 'vitamine A' gives en 'vitamin'; the wrong gloss is stored and shared via the lookup cache. The regex's re.I is what hurts: a stripped dangling lowercase article is the intended case ('to eat a'), a capital letter A is content.
- Holds up? Yes; one-token fix (drop re.I from _TRAILING_ARTICLE, keep lowercase a/the/an), no regress on 1001. Leave the 'vitamin a' IPA aside.
- Final verdict: validated

## Fix
Fix: app/content/enrich.py — _TRAILING_ARTICLE is now case-sensitive so vitamin A / Plan A keep the capital. Tests: tests/test_enrich.py
