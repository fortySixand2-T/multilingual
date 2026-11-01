---
id: 1003
title: Conjunctions and pronouns (mais, parce que, puisque, lorsque, ou, elle) get empty pos
severity: low
area: content
persona: edge-case-breaker
status: done
found: 2026-10-31
---

## Steps to reproduce
Env: B=http://127.0.0.1:9302; T=bearer from POST /auth/signup (invite qa062-a). P(w) = POST $B/vocab/personal/preview -H "authorization: Bearer $T" -d {"word":"w"} (fresh, uncached words, real 7B).
P(mais), P(parce que), P(puisque), P(lorsque), P(ou), P(elle).

## Expected
A populated pos (e.g. conjunction) like other word classes; 893 asked for pos to be populated.

## Actual
pos "" for all six (en: but, because, since, as, when, or, she). ni is tagged "adverb"; il y a is tagged "verb"; derrière is tagged "adjective" (should be preposition/adverb).

## Notes
_POS_VALUES in app/content/enrich.py has no conjunction/pronoun value, so the model's "conjunction" is dropped to "" by _pos; the prompt also lists only six pos values, forcing misfits (ni -> adverb, derriere -> adjective).

## Triage
- Explanation: _POS_VALUES in enrich.py is {noun,verb,adjective,adverb,preposition,phrase}; the prompt lists the same six. A 'conjunction' or 'pronoun' reply matches no 3-letter prefix in _pos and becomes ''. Confirmed in code.
- Against spec: 893: pos populated.
- Verdict: validated
- Rationale: validated

## Critic
- Challenge: Only the six-value pos set is real code; 'conjunction'/'pronoun' replies are dropped by _pos to '' (confirmed in enrich.py:166-173) and the prompt enum has no such value. But it is low severity and an empty pos is a graceful state (UI shows no mark; resolve_gender treats '' fine). Mislabels like ni->adverb, derriere->adjective, il y a->verb are 7B quality.
- Holds up? Partly. Survives only as a minimal change. Fixer scope: add 'conjunction' and 'pronoun' to _POS_VALUES and to the pos enum string in _ENRICH_SYSTEM (adding two enum words only; do not reword the prompt otherwise); check the 3-letter prefix map stays unambiguous (con, pro vs pre/phr; fine) and that no downstream pos allowlist (schema/tests/frontend types) rejects the new values. Do NOT attempt to fix ni/derriere/il y a mislabels; that part is deferred model quality.
- Final verdict: validated

## Fix
Added conjunction and pronoun to _POS_VALUES and the pos enum in _ENRICH_SYSTEM (app/content/enrich.py); no other prompt change. ni/derriere/il y a mislabels left deferred per critic. Test: tests/test_enrich.py::test_pos_variants_map_onto_the_known_values.
