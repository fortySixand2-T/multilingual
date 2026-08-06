---
id: 621
title: GET /srs/hardest with negative limit silently drops cards from the deck (not just "no items")
severity: medium
area: srs
persona: edge-case-breaker
status: done
found: 2026-08-05
---

## Steps to reproduce
1. Sign up / log in, get a Bearer token.
2. Seed and review 7 cards (mix of content + personal) so `/srs/hardest` (no limit)
   returns all 7, sorted hardest-first, e.g.:
   ```
   a_bientot     6.4
   a_demain      5.1
   uv:chat_noir  5.1
   au_revoir     5.1
   acheter       2.1
   annee         2.1
   addition      1.0
   ```
3. `GET /srs/hardest?limit=-1`
4. `GET /srs/hardest?limit=-2`

## Expected
A negative `limit` should either be rejected (422), clamped to the default/ignored
(returning the full ranked deck, same as no `limit` param), or otherwise return a
sane, fully-explainable result. It should never silently return a *subset* of the
correctly-ranked deck with no indication data was dropped — that's a correctness
bug, not just missing validation.

## Actual
`limit=-1` returns 6 of the 7 cards — `addition` (the single lowest-difficulty,
i.e. "least hard" card) is missing entirely, with no error, warning, or count field
to say the result was truncated:

```
$ curl -s "http://127.0.0.1:8091/srs/hardest?limit=-1" -H "Authorization: Bearer $TOKEN"
{"cards":[{"card_key":"a_bientot","difficulty":6.4,...},
          {"card_key":"a_demain","difficulty":5.1,...},
          {"card_key":"uv:chat_noir","difficulty":5.1,...},
          {"card_key":"au_revoir","difficulty":5.1,...},
          {"card_key":"acheter","difficulty":2.1,...},
          {"card_key":"annee","difficulty":2.1,...}]}
```
(6 cards, `addition` missing)

`limit=-2` drops 2 cards (`annee` and `addition`, i.e. the two lowest-ranked):

```
$ curl -s "http://127.0.0.1:8091/srs/hardest?limit=-2" -H "Authorization: Bearer $TOKEN"
{"cards":[... 5 cards, "acheter" is now the last one shown ...]}
```

For comparison, `GET /srs/hardest?limit=0` correctly returns `{"cards":[]}`, and
`limit=99999` correctly returns all 7 cards — so this is specifically a negative-N
slicing bug, not a general limit-handling gap.

## Notes
Root cause (read for context, not to be treated as authoritative repro): in
`app/srs/service.py::hardest_cards`, the ranked list is truncated with
`ranked[:limit]` (line ~93). Because `limit` is a plain Python slice bound,
`ranked[:-1]` means "all but the last item" (Python slice semantics), not
"no limit" or "empty". So a negative limit doesn't fail loudly or get ignored —
it silently truncates the *tail* of the ranked (i.e. easiest/lowest-difficulty)
cards, by an amount equal to `abs(limit)`.

This is distinct from issue 290 (rejected: negative/zero limit alone on
`/srs/queue` with no crash, purely a validation-strictness question). This is not
about the *absence* of a 422 — it's that the endpoint returns *wrong data*
(a truncated deck) for a request that isn't obviously invalid at the HTTP layer,
which could confuse a client that (reasonably) treats negative limit as "no cap"
or forwards a miscomputed limit (e.g. `total - already_shown` going negative near
the end of pagination) and silently gets an incomplete "hardest cards" list.

Severity: medium — no crash, but real data is silently omitted with no signal to
the caller, and the endpoint is specifically pitched as a ranking/decision surface
("hardest for you" deck) where a silently-shortened list is misleading.

## Triage
- Explanation: Reproduced exactly as reported. Seeded 7 cards (6 content + 1
  personal, `uv:chat_noir`), rated each to build a hardest-first ranking of
  `a_bientot(8.8) > a_demain(6.4) = au_revoir(6.4) = uv:chat_noir(6.4) > acheter(5.1)
  = annee(5.1) > addition(1.0)`. `GET /srs/hardest?limit=-1` returned 6 cards
  (dropped `addition`, the single lowest-ranked); `limit=-2` returned 5 (also
  dropped `annee`). Root cause confirmed in `app/srs/service.py::hardest_cards`
  line 93: `ranked[:limit]` — Python slice semantics mean a negative `limit` slices
  off `abs(limit)` items from the *tail* of the already-sorted list, which for this
  endpoint is specifically the easiest/lowest-difficulty cards, not "no cap" and not
  an empty result. `GET /srs/queue` (issue 290's endpoint) is unaffected by this
  root cause because it delegates `limit` straight to SQL `.limit()`, where SQLite
  treats negative as "no limit" — a completely different (and, per 290, accepted)
  behavior. `/srs/hardest` instead does the truncation in Python `list[:limit]`,
  which has different (and actively wrong) semantics for negative values.
- Against spec: unspecified — the plan doesn't define `/srs/hardest`'s limit
  validation, but the docstring/endpoint intent ("ranked...capped at limit") implies
  a monotonic cap, not content-dependent silent removal from the tail.
- Verdict: validated
- Rationale: This is not the same class of issue as 290 (missing 422 on a
  harmless "give me everything" negative limit). Here a plausible client bug
  (e.g. computing `limit = page_size - already_shown` and going negative near the
  end of pagination, or naively treating negative as "unlimited") causes the
  hardest-words deck to silently and specifically hide the *least* concerning
  cards while keeping the most concerning ones — the opposite of an obviously
  wrong result, so it's likely to go unnoticed by both the user and QA. Low-effort
  fix: clamp `limit = max(limit, 0)` (or reject negative with 422) before slicing
  in `hardest_cards`.

## Critic
- Challenge: Confirmed `web/src/api.ts:437` is the *only* caller of `/srs/hardest`
  and it hardcodes `limit=30` — no frontend code ever computes or forwards a
  negative limit. Triggering this requires hand-crafting a query string
  (`?limit=-1`), which is exactly the "only reachable by tampering / impossible
  client input" pattern this role is supposed to kill. No real learner using the
  shipped UI can hit this. Is a bug only reachable via direct curl/API tampering
  worth a code change, or is "don't send garbage limits" the client's problem?
- Holds up? Yes, validated survives. The self-inflicted framing applies to
  *today's* frontend, but `/srs/hardest` is a general-purpose API endpoint (not a
  private RPC), and the PM's own point stands independently of who calls it
  today: this isn't a missing-validation nitpick like 290, it's `ranked[:limit]`
  producing *wrong, silently-truncated* output for a value that isn't an obviously
  malformed request at the HTTP layer (unlike a non-numeric limit, which FastAPI
  would already 422 on). A one-line `max(limit, 0)` clamp is strictly simpler than
  today's accidental Python-slice behavior, not added complexity — it doesn't
  trade off against CLAUDE.md's simplicity bias, it removes a footgun. Low
  severity is already reflected in the PM's own "medium" rating and low-effort fix;
  nothing here inflates it further.
- Final verdict: validated

## Fix
Validated the `limit` query param at the API layer instead of the service layer, matching
the codebase convention of constraining values with `ge=`/`le=` (see
`app/progress/api.py`'s `Field(ge=0, le=10)`). `GET /srs/hardest`'s `limit` is now
`Query(30, ge=0)` in `app/srs/api.py::get_hardest`, so a negative limit is rejected with
a 422 instead of being handed to `ranked[:limit]` in `app/srs/service.py::hardest_cards`,
where Python's negative-slice semantics silently dropped items from the tail of the
ranked deck. Added `tests/test_personal_vocab.py::test_hardest_endpoint_rejects_negative_limit`.
Files: `app/srs/api.py`, `tests/test_personal_vocab.py`.
