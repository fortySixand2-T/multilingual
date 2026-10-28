---
id: 870
title: POST /vocab/personal stores any client-sent ipa instead of the Piper IPA from the lookup row
severity: medium
area: content
persona: edge-case-breaker
status: done
found: 2026-10-27
---

## Steps to reproduce
Env: http://127.0.0.1:9300 (qa060-app, real Piper). B=http://127.0.0.1:9300; T=<bearer token from POST /auth/signup, invite qa060-a>. Seed with: ssh rohith@10.0.0.54 docker exec -i qa060-app python - (sqlite3 on /app/data/tef.db).
1. POST $B/vocab/personal/preview {"word":"horrible"} -> ipa "oʁˈibl".
2. POST $B/vocab/personal {"fr":"horrible","en":"terrible","pos":"adjective","gender":"","ipa":"WRONG"}
3. GET $B/vocab/personal ; GET $B/srs/queue.

## Expected
Card IPA comes from the Piper-derived vocab_lookup row (or is ignored/validated); arbitrary strings are not stored.

## Actual
201-style success, card ipa "WRONG" persisted, shown in deck and SRS queue vocab payload. add() copies audio_key from the lookup row but not ipa; any string up to 64 chars is accepted (also non-IPA text / markup).

## Notes
Violates the 'IPA only from Piper' intent of #121 for any client (and a stale SPA preview).

## Triage
- Explanation: add() in personal_api.py persists body.ipa (max_length 64) and copies only audio_key from the lookup row.
- Against spec: Rule from PO/#121: IPA must come only from Piper; nonsense IPA must never be shown.
- Verdict: validated
- Rationale: Any client or stale SPA can store non-Piper IPA on a card. Fix: ignore client ipa; take ipa from the lookup row (same slug), else empty. Small change, closes a second route for the user's bug.


## Critic
- Challenge: Self-inflicted: only a tampering client sends ipa other than the one the SPA got from preview.
- Holds up? Holds, but cheap and it removes a second route to stale IPA (old cached SPA bundle sends stale preview.ipa after the heal). Fix must look the lookup row up with lookup_slug(fr) -- note add() currently uses slugify(row.fr)[:64], which diverges from lookup_slug once 871 changes it (and skips normalize_lemma); use the one function in both places. If no lookup row: ipa empty. Keep the AddBody field accepted (ignored) so old clients do not 422.
- Final verdict: validated

## Fix
`POST /vocab/personal` ignores the client `ipa` (field still accepted) and, for a newly created card, takes the IPA of the `lookup_slug(fr)` lookup row, else empty; the same `lookup_slug` now also finds the clip.
- Files: `app/content/personal_api.py`
- Tests: `tests/test_personal_vocab.py::test_add_card_ignores_client_ipa_and_takes_the_lookups`
