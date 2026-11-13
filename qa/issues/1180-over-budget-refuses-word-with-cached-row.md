---
id: 1180
title: Over budget, typing the correctly accented spelling of an already cached model word returns over_budget instead of the cached row
severity: low
area: content
persona: edge-case-breaker
status: deferred
found: 2026-11-12
---

## Steps to reproduce
1. Scratch app with VOCAB_DAILY_TOKEN_BUDGET=1; user already over budget.
2. A model-only word exists in vocab_lookup without its accents (e.g. slug zebu, fr "zebu", en "zebu (humped ox)").
3. POST /vocab/personal/preview {"word":"zebu"} then {"word":"zébu"}.

## Expected
"zébu" returns the cached row (a DB read costs nothing) or the same answer as "zebu".

## Actual
- "zebu" -> 200 enrichment zebu / "zebu (humped ox)".
- "zébu" -> {"enrichment":null,"over_budget":true}. The learner who types the right spelling is told they are over budget while the less-correct spelling works. from-word behaves the same.

## Notes
cached_lookup treats the row as a miss because accent_count(typed) > accent_count(row.fr), then fresh_lookup runs with no router. Other budget checks passed: dictionary and course words work over budget and cost 0 tokens (daily_usage unchanged); model-only words (zzyx, xylophone, zébu, wapiti) give {"enrichment":null,"over_budget":true}; a user at 0 used gets one model call (319/28 billed) then is over; accentless ambiguous words (epice, derive, reserve) resolve with no billing.

## Triage
- Explanation: Confirmed from code: lookup.cached_lookup treats a row as a miss when accent_count(typed) > accent_count(row.fr); when over budget, _lookup passes router=None so fresh_lookup returns nothing and the endpoint answers over_budget even though a cached row exists.
- Against spec: Over-budget rule intends cached/dictionary reads be free (PR #139 notes).
- Verdict: validated
- Rationale: Low impact, narrow (model-only word, over budget, learner typing accents the cached row lacks) but a wrong 'over budget' message. FIX LOCATION: runtime lookup.py/personal_api._lookup: when over budget and a row exists, return it. Bundle with the 1175 cache rework.

## Critic
- Challenge: Narrow: over budget AND model-only word AND typed accents the cached row lacks; the message is wrong but harm is tiny.
- Holds up? Doesn't justify its own change. If the 1175 cache rework stops treating accent-count differences as misses, this disappears; re-test then.
- Final verdict: deferred
