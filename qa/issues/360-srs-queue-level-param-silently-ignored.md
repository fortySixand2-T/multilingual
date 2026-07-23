---
id: 360
title: SRS queue ignores the ?level query parameter and always returns all cards
severity: medium
area: srs
persona: returning-learner
status: rejected
found: 2026-07-23
---

## Steps to reproduce
1. Sign up, complete A1 lessons so vocab cards are seeded into the SRS queue.
2. `GET /srs/queue?level=a2` — user has zero A2 cards.
3. Compare with `GET /srs/queue` (no level filter).

## Expected
`GET /srs/queue?level=a2` should return only cards whose `vocab.level == "a2"`.
With no A2 cards seeded, the response should be `{"due": []}`.
The `?level` parameter should be honoured so the review screen can be scoped to the
level the user is currently studying (same as `/content/vocab?level=a1`).

## Actual
All three calls return identical results — 20 cards, all A1:

```
GET /srs/queue               → due: 20 (all A1)
GET /srs/queue?level=a1      → due: 20 (all A1)
GET /srs/queue?level=a2      → due: 20 (all A1, should be 0)
GET /srs/queue?level=GARBAGE → due: 20 (all A1)
```

The route signature is `get_queue(limit: int = 20, ...)` — no `level` parameter is
declared, so FastAPI silently accepts and discards it. The underlying `due_cards()`
service also has no level filter.

## Notes
- Found on live remote deployment (Tailscale funnel, ollama backend).
- The `vocab.level` field IS present in each card response (fixed in issue 400), so the
  frontend could work around this by client-side filtering — but callers passing
  `?level=a1` receive a misleading implicit contract that the filter is applied.
- A returning learner who has progressed to A2 and adds `?level=a2` to scope their
  daily review to the new level will unknowingly get their entire backlog (A1 + A2)
  returned, making the review feel uncontrolled.
- Fix: add `level: str | None = None` to `get_queue`, pass it to `due_cards`, and
  add a `JOIN` or `IN` sub-select to filter `ReviewCard.card_key` by
  `ContentVocab.level == level` when the parameter is provided.

## Triage
- Explanation: GET /srs/queue declares no `level` param, so FastAPI silently ignores `?level=a2` and returns all due cards.
- Against spec: spaced repetition is deliberately cross-level — the queue surfaces what is DUE regardless of level; scoping to one level would skip due cards and defeat SRS. An ignored unknown query param is standard FastAPI behaviour (same as qa-251, rejected).
- Verdict: rejected
- Rationale: by design; matches the qa-251 precedent.

## Critic
- Challenge: should review be level-scopeable at all?
- Holds up? Yes for now — global due-review is intentional; per-level review decks would be a future feature, not a bug.
- Final verdict: rejected
