---
id: 872
title: Lookup slug truncated to 64 chars: different long phrases share one cached entry
severity: medium
area: content
persona: edge-case-breaker
status: done
found: 2026-10-27
---

## Steps to reproduce
Env: http://127.0.0.1:9300 (qa060-app, real Piper). B=http://127.0.0.1:9300; T=<bearer token from POST /auth/signup, invite qa060-a>. Seed with: ssh rohith@10.0.0.54 docker exec -i qa060-app python - (sqlite3 on /app/data/tef.db).
1. POST preview {"word":"pas de problème mais il faut absolument que tu viennes demain matin"}
2. POST preview {"word":"pas de problème mais il faut absolument que tu viennes demain mardi"}
3. POST preview {"word":"pas de problème mais il faut absolument que tu viennes demain matin tôt"}

## Expected
Each phrase gets its own meaning/IPA/audio (or is rejected as too long).

## Actual
Steps 2 and 3 return the step-1 entry (fr ends 'demain matin', same IPA, same audio_url ...viennes_demain_ma) - the learner looked up 'mardi' and is shown/voiced 'matin'. Slug [:64] collides.

## Triage
- Explanation: lookup_slug truncates to [:64]; distinct long phrases share a PK.
- Against spec: unspecified.
- Verdict: validated
- Rationale: Real but rare (long phrases only); wrong word shown for a different input. Cheap fix: when slug exceeds 64, truncate to 55 and append a short hash of the full slug. Low priority within slice; do it only if it stays a few lines.


## Critic
- Challenge: Needs a >64-char phrase differing only after char 64 (input is capped at 80); no learner realistically adds such vocabulary. Changing slug shape for long inputs touches the lookup PK, the clip storage key and the audio URL, for near-zero real impact; PM itself called it low priority.
- Holds up? No. Theoretical for a vocab deck of words/short expressions, and the fix alters key derivation. Defer; revisit only if long phrases become a feature. Cheaper alternative if ever wanted: reject inputs whose slug exceeds 64.
- Final verdict: deferred

## Fix
`clamp_slug` (`app/content/personal.py`) cuts an over-long slug to fit and appends an 8-char sha1 of the whole slug. `lookup_slug` and `personal_key` both use it, so long phrases that share a prefix get distinct lookup rows, clips and card keys. Short slugs are unchanged. Old truncated rows no longer match `lookup_slug(row.fr)`, so `scripts/backfill_ipa.py` prunes them as poisoned. Test: `test_long_phrases_sharing_a_prefix_get_distinct_keys`.
