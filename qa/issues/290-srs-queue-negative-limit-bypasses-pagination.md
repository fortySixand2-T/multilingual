---
id: 290
title: SRS queue accepts negative limit, bypassing pagination
severity: low
area: srs
persona: returning-learner
status: rejected
found: 2026-06-22
---

## Steps to reproduce
1. Sign up and complete a few lessons to seed SRS cards.
2. GET /srs/queue?limit=-1 with a valid Bearer token.

## Expected
The endpoint should reject negative limit values with a 422 validation error, or clamp to a minimum of 1. The `limit` parameter exists to paginate the queue (default 20).

## Actual
`limit=-1` returns all due cards (HTTP 200), effectively bypassing pagination. SQLite interprets `LIMIT -1` as "no limit." Similarly, `limit=0` returns an empty array.

```
GET /srs/queue?limit=-1 -> 200, returns all 11 due cards
GET /srs/queue?limit=0  -> 200, returns {"due": []}
GET /srs/queue           -> 200, returns up to 20 (the default)
```

## Notes
The `limit` parameter is passed from the API layer directly to SQLAlchemy `.limit()` without validation. Adding `ge=1` (or `ge=0`) to the query parameter definition in `app/srs/api.py` would fix this. Severity is low because the practical impact is minimal -- the user just gets more cards than intended -- but it is a validation gap that could behave differently across database backends (e.g., Postgres may error on negative LIMIT).

## Triage
- Explanation: The `get_queue` endpoint (app/srs/api.py line 29) declares `limit: int = 20` as a plain query parameter with no constraints. This value flows unchanged to `due_cards` in app/srs/service.py line 70, which passes it to SQLAlchemy's `.limit()`. SQLite interprets `LIMIT -1` as "no limit," so negative values bypass pagination entirely. `limit=0` returns an empty list.
- Against spec: The spec (Phase 2, SRS queue) does not specify pagination constraints explicitly, but accepting negative values is a validation gap that produces backend-dependent behavior (SQLite silently accepts it; Postgres would error). This is a real, if minor, input validation defect.
- Verdict: validated
- Rationale: While severity is low and there is no frontend yet, this is a genuine validation hole: negative limit silently disables pagination on SQLite and would cause a 500 on Postgres. Adding `ge=1` to the query parameter is a one-line fix that prevents surprising cross-database behavior. Worth fixing in the next batch alongside other low-effort items.

## Critic
- Challenge: No real user will ever send limit=-1. There is no frontend, and when one exists it will use the default or a sensible value. This is a penetration-testing-style finding on a self-hosted learning app with authenticated endpoints only -- the caller is already a trusted, logged-in user. The "cross-database portability" argument is speculative: the project runs on SQLite today, and a Postgres migration would involve its own validation pass. The spec says nothing about pagination constraints. The actual impact is zero: a user who sends limit=-1 gets... their own due cards, which they are entitled to see. There is no data leak, no crash, no corruption. This is input-hardening, not a bug fix. Adding validation constraints to every integer parameter is feature-creep disguised as bug-fixing.
- Holds up? No -- the PM's validation does not survive the challenge. The behavior produces no harm to any real user. Returning all due cards to the card owner is not a security issue. The Postgres argument is hypothetical. The fix is trivial, yes, but "easy to fix" is not the same as "needs fixing." This is a hardening request, not a defect.
- Final verdict: rejected
