# QA round 016 — plan

- date: 2026-06-23
- app under test: backend :9000 / SPA :5174
- scope: vocab-deck feature (PR #7) — GET /content/vocab, POST /content/vocab/known, GET /content/audio for vocab clips, plus regression on existing flows

## Change surface (highest risk first)
PR #7 (`feat/vocab-deck`) adds:
1. `GET /content/vocab` — returns vocab cards with optional `level`/`tag` filters and per-user `known` flag
2. `POST /content/vocab/known` — mark/reset known status (idempotent, unique constraint)
3. `GET /content/audio/{key}` — serves TTS clips for vocab cards (207 clips for a1+a2)
4. Migration `0011_vocab_known` — new table with user+card unique constraint
5. Frontend vocab tab with flashcard study flow

## Hypotheses (ranked)

| # | area | hypothesis | how to probe | persona |
|---|------|------------|--------------|---------|
| H1 | known-marks | Marking the same card known twice may cause a 500 (unique constraint violation not caught) | POST known=true for same card_key twice rapidly | edge-case-breaker |
| H2 | known-marks | One user's known marks leak to another user's GET /content/vocab response | Sign up two users, mark cards with user A, check user B sees known:false | edge-case-breaker |
| H3 | vocab-endpoint | Omitting `level` param should return all levels with `level` field on each card and `known` per card | GET /content/vocab with no params, verify structure | absolute-beginner |
| H4 | vocab-endpoint | Unknown `level` returns 404 but unknown `tag` returns 200 with empty list | GET /content/vocab?level=c2 vs ?tag=nonexistent | edge-case-breaker |
| H5 | vocab-endpoint | GET /content/vocab without auth token returns 401 | Call without Authorization header | edge-case-breaker |
| H6 | audio | Vocab audio keys with underscores (se_lever, salle_de_bain, a_bientot) serve 200 audio/mpeg | GET /content/audio/{key} for underscore-containing ids | absolute-beginner |
| H7 | audio | Path traversal in /content/audio still blocked (../etc/passwd, %2e%2e) | Attempt traversal payloads | edge-case-breaker |
| H8 | known-validation | Missing card_key or known field returns 422, not 500 | POST with partial/malformed bodies | edge-case-breaker |
| H9 | known-marks | Resetting a card that was never marked known is a no-op (no error) | POST known=false for an unmarked card | edge-case-breaker |
| H10 | known-marks | Marking a non-existent card_key is accepted gracefully | POST known=true for card_key="DOESNOTEXIST" | edge-case-breaker |
| H11 | regression | Existing pytest suite (124+ tests) still passes on this branch | Run pytest | edge-case-breaker |
| H12 | regression | Lesson gating, exam flows, SRS queue still functional | Quick smoke of /content/path, /exam/start, /srs/queue | absolute-beginner |

## Coverage gaps
- The vocab endpoints are entirely new — zero issue history. This round's primary target.
- The `/content/audio/{key}` route was added for vocab but also serves lesson audio; collision between vocab and lesson audio keys is a risk.
- Known-marks concurrency: two users marking the same card simultaneously is untested.

## Charters (per tester, with id blocks)

- `edge-case-breaker` (ids 300-319): Chase H1, H2, H4, H5, H7, H8, H9, H10, H11.
  Focus: known-mark idempotency and constraint handling, input validation edge cases,
  cross-user isolation, audio traversal guard, pytest regression. Create TWO users to
  test isolation. Hammer the unique constraint with duplicate marks.

- `absolute-beginner` (ids 320-339): Chase H3, H6, H12.
  Focus: happy-path vocab browsing (all levels, single level, tag filter), audio
  playback for vocab cards (especially underscore ids), basic regression smoke of
  lesson path and SRS queue. One fresh user doing the "just browse vocab" flow.

## Don't re-file (already settled)
- 001 invalid email — deferred
- 002 no password minimum — deferred
- 007 negative elapsed_seconds — rejected
- 071 no-replay not enforced — rejected/deferred
- 131 password no max length — deferred
- Drill / Writing / Speaking 503 with no provider — expected (no LLM configured)
- All issues up to 290 are from prior rounds — don't duplicate them

<!-- After the round, the planner notes each hypothesis: confirmed / refuted / untested -->
