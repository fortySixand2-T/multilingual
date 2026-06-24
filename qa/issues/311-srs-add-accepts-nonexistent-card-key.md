---
id: 311
title: POST /srs/add accepts arbitrary non-existent card_key with no existence check
severity: high
area: srs
persona: edge-case-breaker
status: done
found: 2026-06-23
---

## Steps to reproduce
1. Sign up and obtain a bearer token.
2. POST /srs/add with body `{"card_key":"zzz_fake_not_real"}` and Authorization header.
3. Observe 200 response `{"card_key":"zzz_fake_not_real","added":true}`.
4. GET /srs/queue and observe an entry with `card_key: "zzz_fake_not_real"` and `vocab: null`.

## Expected
The endpoint should validate card_key against the known vocabulary catalog and return 404 or 422 if the key does not correspond to any existing vocab card. Only real vocabulary items should be addable to SRS.

## Actual
Any arbitrary string is accepted and persisted. The SRS queue then contains phantom entries with `vocab: null` that have no corresponding vocabulary data. These entries cannot be studied (no French word, no English translation, no audio) and pollute the review queue.

## Notes
There is no FK constraint or application-level existence check. A user (or buggy client) could fill their SRS queue with garbage entries. This also means the SRS queue endpoint must handle `vocab: null` gracefully on the frontend, which is an additional surface for rendering errors.

## Triage
- Explanation: The `POST /srs/add` endpoint passes the user-supplied `card_key` directly to `seed_cards()` in `app/srs/service.py`, which creates a `ReviewCard` row without checking whether the key exists in `content_vocab`. The lack of a FK constraint from `srs_cards.card_key` to `content_vocab.id` is intentional (the SRS module is decoupled from content so that lesson-completion seeding works independently). However, the `/srs/add` endpoint is a user-facing action where the caller explicitly requests to add a card -- unlike the internal `seed_cards` path from lesson completion, which only ever passes known vocab keys. The endpoint should validate the key against `content_vocab` before creating the row.
- Against spec: The spec does not explicitly require existence checking on `/srs/add`, but the SRS queue (AC1.2) is meant to present reviewable vocabulary cards. Phantom entries with `vocab: null` break that contract -- a card with no word/translation/audio cannot be reviewed.
- Verdict: validated
- Rationale: Any arbitrary string accepted by `/srs/add` creates a phantom card in the review queue that has no vocabulary data and cannot be studied. While the SRS-content decoupling is by design at the DB level, the user-facing endpoint should still validate input against the content catalog. User impact: a buggy client or curious user can fill their queue with un-reviewable garbage entries. Fix: add a `content_vocab` existence check in the `/srs/add` handler before calling `seed_cards`.

## Fix
The `/srs/add` handler now checks the key against `content_vocab` and returns 404 (`no vocab card ...`) if it doesn't exist, before seeding. The srs↔content DB decoupling (no FK) is preserved — internal lesson-completion seeding via `seed_cards` is unchanged; only the user-facing endpoint validates. Regression: `tests/test_content_sync.py::test_srs_add_rejects_nonexistent_card_key`.
