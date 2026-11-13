---
id: 1177
title: My deck: an accented typo (mâ) makes the model invent a word and overwrite the cached valid word (ma -> mâ, male)
severity: medium
area: content
persona: edge-case-breaker
status: rejected
found: 2026-11-12
---

## Steps to reproduce
1. POST /vocab/personal/preview {"word":"ma"} -> {"fr":"ma","en":"my","pos":"pronoun"}.
2. POST /vocab/personal/preview {"word":"mâ"} (a typo).
3. POST /vocab/personal/preview {"word":"ma"} as any user.

## Expected
A non-word is rejected ("Couldn't find a meaning") or at least cached separately; "ma" still means "my".

## Actual
Step 2 returns {"fr":"mâ","en":"male","pos":"noun","gender":"m","gender_source":"llm"} (model invention, billed) and replaces the shared row. Step 3 now returns {"fr":"mâ","en":"male","pos":"noun"} for every user, permanently (DB: vocab_lookup slug "ma" -> fr "mâ", en "male"). Also "é" is accepted as an adverb meaning "e" and takes slug "e", so a later "e" returns "é".

## Notes
Same root cause family as 1175 (accent-folded slug, higher accent count always wins). Because the cache is shared, one learner typo corrupts lookups for all.

## Triage
- Explanation: Duplicate of 1175: same accent-folded slug with 'higher accent count always wins' overwrite. The extra part is that a non-word (mâ) gets a model-invented 'male' and replaces the valid row for ma; the 1175 fix (never overwrite a valid dictionary word's row from a different spelling/model proposal) removes this too.
- Against spec: As 1175.
- Verdict: rejected
- Rationale: Duplicate; track under 1175 and add 'accented typo (mâ, é) must not overwrite or take another word's slug' to its acceptance checks.

## Critic
- Challenge: Duplicate: model proposing a different word for a typo.
- Holds up? Rejection holds; the 1175 fix (never overwrite a valid word's row from a different spelling) removes it. Add mâ/é to 1175 acceptance checks.
- Final verdict: rejected
