---
id: 321
title: POST /content/vocab/known accepts nonexistent card_key silently
severity: medium
area: content
persona: edge-case-breaker
status: done
found: 2026-07-22
---

## Steps to reproduce
1. Sign up and obtain a valid JWT token (invite code `friend-001`).
2. Send `POST /content/vocab/known` with a `card_key` that does not exist in the vocab table:
   ```
   curl -X POST https://<host>/content/vocab/known \
     -H "Authorization: Bearer <token>" \
     -H "Content-Type: application/json" \
     -d '{"card_key":"phantom-word-that-doesnt-exist-in-vocab-table","known":true}'
   ```
3. Observe the response.

## Expected
The endpoint should validate that the `card_key` exists in the vocab table and return a `404` error (matching the behaviour of `POST /srs/add`, which was fixed in issue 311 for the same reason).

## Actual
Returns HTTP 200:
```json
{"card_key":"phantom-word-that-doesnt-exist-in-vocab-table","known":true}
```
The phantom key is silently inserted into the `known_vocab` table with no vocab row to back it up. The ghost entry never surfaces in any vocab list (since `GET /content/vocab` joins to `ContentVocab`), so users get false confirmation that a word was marked known. Unlike `/srs/add` (which was fixed), `/content/vocab/known` has no existence check.

## Notes
- Confirmed live on the remote deployment 2026-07-22.
- `POST /srs/add` correctly rejects `{"card_key":"phantom-..."}` with `{"detail":"no vocab card 'phantom-...'"}` (fix from issue 311). That same guard was not applied to the parallel `vocab/known` endpoint.
- The inconsistency is confusing: two sibling "mark card as known" endpoints behave differently.
- Severity is medium rather than high because the ghost entry is inert — it does not pollute vocab lists or SRS queues — but it is a silent data integrity gap and a broken user-facing confirmation.

## Triage
- Explanation: POST /content/vocab/known inserted a KnownVocab row without checking the key exists — unlike srs/add (qa-311), which 404s on phantom keys.
- Against spec: inconsistent validation at the user-facing edge; phantom keys accumulate silently.
- Verdict: validated
- Rationale: same class as qa-311; one-line catalog check.

## Critic
- Challenge: is marking a phantom card "known" actually harmful?
- Holds up? Yes — silent acceptance is a data-integrity/consistency gap and cheap to close.
- Final verdict: validated

Fix: set_known validates card_key against ContentVocab, 404 on miss (app/content/api.py; tests/test_progress.py::test_vocab_known_rejects_phantom_card_key)
