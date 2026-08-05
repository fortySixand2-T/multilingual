---
id: 611
title: Long `fr` produces a `uv:` card_key well past the declared 64-char DB column limit
severity: low
area: content
persona: edge-case-breaker
status: done
found: 2026-08-05
---

## Steps to reproduce
1. Sign up / log in, get a bearer token.
2. `POST /vocab/personal` with a 120-character `fr` (within the API's
   `max_length=128` validation on `AddBody.fr`), e.g.:
   `"anticonstitutionnellement anticonstitutionnellement anticonstitutionnellement anticonstitutionnellement anticonstitution"`
   and any `en`.
3. Inspect the returned `card_key`.
4. `GET /vocab/personal` and re-check the stored row's `card_key` length.

## Expected
The `user_vocab.card_key` column is declared `String(64)` (`"uv:" + slug`,
app/content/tables.py) and is meant to be a short SRS review key, consistent with
every content-bank key. The API layer should keep `fr` short enough that the derived
`uv:<slug>` key actually fits that column (e.g. clamp/validate slug length, or reject
inputs whose slug would overflow) — or the column should be widened to match what
`fr`'s own `max_length=128` actually allows.

## Actual
The card is accepted with HTTP 200 and a 123-character `card_key`:

```
uv:anticonstitutionnellement_anticonstitutionnellement_anticonstitutionnellement_anticonstitutionnellement_anticonstitution
```

(3-char prefix + 120-char slug = 123 chars, nearly double the declared 64-char column
limit.) On this instance the app runs on SQLite (`DATABASE_URL=sqlite+aiosqlite:...`
in both `.env.example` and `docker-compose.yml`), which does not enforce `VARCHAR`
length constraints, so the write silently succeeds with no truncation and no error —
it round-trips correctly on `GET /vocab/personal` and would presumably work through
`/srs/queue` too. No crash was observed. However, the column type declares an
intentional 64-char cap that the request-validation layer (`AddBody.fr`,
`max_length=128`) does not honor at all — the two limits are inconsistent by design,
and the only reason this doesn't currently corrupt data or 500 is that the target
database happens to be lenient. This is a real latent schema/API mismatch, not just
"loose input shape" (distinct from the previously-rejected input-looseness pattern):
any future migration to a length-enforcing database (Postgres, etc.) would turn every
personal-deck add with a moderately long word/phrase into a hard 500 on `INSERT`.

## Notes
- `app/content/tables.py`: `card_key: Mapped[str] = mapped_column(String(64))`
- `app/content/personal_api.py`: `AddBody.fr = Field(min_length=1, max_length=128)`
- `app/content/personal.py`: `slugify()`/`personal_key()` have no length clamp.
- Suggested fix direction: clamp the slug (e.g. `slug[:61]`) inside `personal_key()`
  so `uv:<slug>` always fits 64 chars, independent of what the DB backend tolerates.


## Resolution (2026-08-05, round 049)
Fixed in `app/content/personal.py`: `personal_key()` now clamps the slug so `uv:<slug>` always fits the `card_key` String(64) column (`slug[:64-len('uv:')]`), independent of DB backend. Regression test `test_card_key_never_exceeds_column_limit`.
