---
id: 310
title: POST /srs/add accepts empty-string card_key creating orphan SRS entry
severity: medium
area: srs
persona: edge-case-breaker
status: done
found: 2026-06-23
---

## Steps to reproduce
1. Sign up and obtain a bearer token.
2. POST /srs/add with body `{"card_key":""}` and Authorization header.
3. Observe 200 response `{"card_key":"","added":true}`.
4. GET /srs/queue and observe an entry with `card_key: ""` and `vocab: null`.

## Expected
An empty-string card_key should be rejected with 422 (validation error), the same way a null or missing card_key is rejected. An empty string is not a valid vocabulary identifier.

## Actual
The endpoint returns 200 with `added: true`. The empty-string card is persisted in the SRS table and appears in GET /srs/queue as `{"card_key":"","due":"...","vocab":null}`. The user sees a ghost card with no vocabulary data.

## Notes
The card_key field validates null and missing inputs but does not enforce a minimum length of 1 (or validate against the known vocab catalog). This pollutes the user's SRS queue with unactionable entries.

## Triage
- Explanation: The `AddBody` Pydantic model in `app/srs/api.py` defines `card_key: str` with no `min_length` constraint. Pydantic allows empty strings by default. The `seed_cards` service in `app/srs/service.py` creates a `ReviewCard` row for any string value without validation, so `card_key=""` is persisted to `srs_cards`. When `GET /srs/queue` joins against `content_vocab`, the empty key matches nothing, producing `vocab: null` in the response.
- Against spec: The spec (AC1.2) requires FSRS to schedule reviews correctly, which implicitly assumes cards correspond to real vocabulary. No spec explicitly addresses empty-string validation, but an empty string is self-evidently not a valid vocabulary identifier. This is a missing input constraint.
- Verdict: validated
- Rationale: An empty card_key creates an unactionable ghost entry in the user's SRS queue (no word, no translation, no audio). The fix is trivial -- add `min_length=1` to the Pydantic field. User impact: learners see a blank, un-reviewable card polluting their review queue.

## Fix
`AddBody.card_key` now uses `Field(min_length=1)`, so an empty string is rejected with 422 — the same as null/missing. (A non-existent key is separately handled by the existence check added for #311.) Regression: `tests/test_content_sync.py::test_srs_add_rejects_empty_card_key`.
