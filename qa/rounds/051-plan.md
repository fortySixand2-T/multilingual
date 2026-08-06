# QA round 051 — plan

- date: 2026-08-05
- app under test: http://127.0.0.1:8091 (backend + built SPA, single origin)
- scope: Slice 2 — FSRS difficulty surfacing + the "Hardest for you" deck (branch feat/hardest-deck, commit 5e256e3)

## Change surface (highest risk first)
Commit 5e256e3 "feat(srs): difficulty surfacing + hardest for you deck":
- `app/srs/fsrs.py::difficulty(state)` — new pure function, null until first review.
- `app/srs/service.py::hardest_cards()` — new ranking query; sorts reviewed cards
  hardest-first in Python (difficulty lives inside opaque FSRS JSON, not a DB column).
- `app/srs/api.py`:
  - `GET /srs/hardest` — new endpoint, shared `_resolve_vocab` helper now used by
    both `/srs/queue` and `/srs/hardest` (refactor risk: could regress `/queue`'s
    existing vocab resolution).
  - `GET /srs/queue` — payload gains a `difficulty` field per card (regression risk
    on the pre-existing endpoint).
- `web/src/screens/Hardest.tsx` (new), `web/src/screens/Review.tsx` (tough-ones badge,
  `difficulty >= 7`), `web/src/screens/Path.tsx` (🔥 hub tile), `web/src/App.tsx` (route).
- Tests added: `tests/test_srs.py` (+48 lines), `tests/test_personal_vocab.py` (+29),
  `web/src/screens/Hardest.test.tsx` (new, 50 lines) — so basic paths likely already
  covered by unit tests; QA should target integration/UI/edge gaps unit tests don't reach.

## Hypotheses (ranked)
| # | area | hypothesis | how to probe | persona |
|---|------|------------|--------------|---------|
| H1 | srs/hardest ranking | Cards rank hardest-first by true FSRS difficulty after mixed again/hard/good/easy ratings; an unreviewed card is correctly absent | seed 4+ content cards, rate each a different rating, GET /srs/hardest, assert descending order and unreviewed card missing | edge-case-breaker |
| H2 | srs/hardest cross-bank | A hard personal (`uv:`) card and a hard content card both resolve correctly (personal carries `personal:true`+`audio_url`; content carries `audio`) with no field bleed between them | add one personal + one content card, rate both hard, inspect both entries' vocab shape | edge-case-breaker |
| H3 | auth scoping | friend-002 never sees friend-001's hardest cards | seed+review cards on both accounts, GET /srs/hardest as each, diff card_keys | returning-learner |
| H4 | edge cases | empty deck -> `{cards: []}`; `limit=0`/huge limit; a card rated to "easy" (difficulty ~1) still appears since it's reviewed; ties don't crash | fresh account hardest call; limit=0; limit=9999; rate a card to easy and confirm presence | edge-case-breaker |
| H5 | queue regression | `/srs/queue` still returns correct vocab (content+personal) post-refactor, plus new `difficulty`: null pre-review, numeric post-review | GET /srs/queue before/after reviewing a seeded card | returning-learner |
| H6 | UI rendering | /hardest reachable via 🔥 tile; band labels/colors (Tough/Tricky/Getting there) match thresholds (>=7 red, >=4 amber, else green); numeric difficulty shown; reveal-meaning toggles; audio button renders for both content and personal cards; empty-state copy on fresh account; no console errors | browse as a seeded+reviewed account and as a fresh account | qa-browser-tester (returning-learner-styled) |
| H7 | UI review badge | Review screen shows "🔥 one of your tough ones" only for difficulty>=7 cards, not lower | review a hard (rated "again" repeatedly) card and a fresh/easy card in the UI | qa-browser-tester |

| H8 | srs scheduling | Difficulty->frequency invariant: again/hard schedules a card due sooner than good/easy, for both content and personal cards; repeated "again" keeps a card surfacing (high difficulty + near-term due), consistent between /srs/hardest and /srs/queue | POST /srs/review with again vs easy on twin cards, compare returned `due` timestamps; repeat for a `uv:` personal card; cross-check hardest_cards vs due_cards agree | edge-case-breaker |
| H9 | deck integration loop | Full add-review-resurface loop: a personal card added via /vocab/personal appears in /srs/queue, can be reviewed, then appears in /srs/hardest once rated hard - the three deck views (My deck / Review queue / Hardest) stay consistent | POST /vocab/personal -> GET /srs/queue (confirm card present) -> POST /srs/review rating hard/again -> GET /srs/hardest (confirm it appears, ranked correctly) | edge-case-breaker |

## Coverage gaps
- No prior issue history at all for `/srs/hardest` (brand new endpoint) — full blind spot.
- `_resolve_vocab` shared-helper refactor has no prior issue history checking `/srs/queue`
  didn't regress from the refactor.
- Personal-card difficulty surfacing (band/color) in the UI is untested territory —
  prior personal-vocab issues (slice E) were about the add/list endpoints, not SRS review.

## Charters (per tester, with id blocks)
- `qa-tester` (edge-case-breaker) - ids 650-659: chase H8, H9 (added mid-round at user request - scheduling is the point of the whole feature). Verify again/hard schedules sooner than good/easy for both content and `uv:` personal cards; verify repeated "again" keeps a card surfacing near-term while "easy" pushes it out, and that /srs/hardest and /srs/queue agree; walk the full personal-card add->queue->review->hardest loop end to end.
- `qa-tester` (edge-case-breaker) — ids 621–629: chase H1, H2, H4. Seed content +
  personal cards via `/srs/add` and `/vocab/personal`, rate them with varied ratings via
  `/srs/review`, hit `/srs/hardest` with default/0/negative/huge `limit`, and a fresh
  account with zero reviews. Also sanity-check `/srs/queue`'s new `difficulty` field
  (H5) since it's cheap to check alongside seeding.
- `qa-tester` (returning-learner) — ids 630–639: chase H3, H5. Use both invite codes
  (friend-001, friend-002) to build two accounts with distinct hardest decks and confirm
  no cross-account leakage; separately verify `/srs/queue` vocab resolution (content +
  personal) is intact post-refactor.
- `qa-browser-tester` (returning-learner) — ids 640–649: chase H6, H7. Sign up/login via
  UI (or reuse a seeded account if session/localStorage token can be set), reach /hardest
  via the 🔥 hub tile, verify band colors/labels/numeric difficulty/reveal/audio button
  for both a content and a personal hard card, check the empty-state copy on a fresh
  account, and confirm the Review screen's tough-ones badge appears only for
  difficulty >= 7. Watch the browser console for errors throughout.

## Don't re-file (already settled)
- Negative/zero `limit` on `/srs/*` endpoints returning more/fewer rows than expected
  without a 422 — settled **rejected** in issue 290 (srs-queue-negative-limit-bypasses-pagination):
  input-hardening on a trusted authenticated endpoint, not a real defect. Only file a
  new issue here if `limit` causes a crash/500, not just "unexpected but harmless" row counts.
- `level` query param silently ignored — rejected in issue 360, unrelated to this slice
  but same endpoint family; don't re-raise "unused param" style findings without a
  concrete behavioral bug.
- `/srs/add` accepting empty/nonexistent card_key, `/srs/queue` vocab missing level/audio
  key — all already fixed (issues 310, 311, 350, 400); don't re-file, but a browser/API
  tester noticing a *regression* of these (e.g. audio key silently disappears again with
  the `_resolve_vocab` refactor) should treat it as a fresh, real finding (link back to
  the old issue for context).

## Outcome
- H1 (ranking correctness) — refuted (sound): strictly descending order; unreviewed cards correctly absent.
- H2 (cross-bank correctness) — refuted (sound): personal (`personal:true`+`audio_url`) vs content (`audio`) shapes correct, no bleed.
- H3 (auth scoping) — refuted (sound): per-user isolation confirmed, including on a shared content card_key reviewed by two users independently; clean 401s on bad/missing auth.
- H4 (edge cases) — confirmed → issue 621 (negative `limit` silently truncates the ranked deck via Python slice semantics — distinct from the already-rejected issue 290). Other edge cases (empty deck, limit=0, huge limit, easy-but-reviewed card, ties) refuted/sound.
- H5 (queue regression) — confirmed → issue 622 (`/srs/queue` difficulty unrounded vs `/srs/hardest`'s rounded value). Vocab shape (content `audio`, personal `personal`/`audio_url`) confirmed intact post-refactor.
- H6 (UI rendering) — refuted (sound), except confirmed → issue 640 (tough badge emoji/text visually collapse + wrong casing).
- H7 (UI review badge) — refuted (sound): gating at difficulty >= 7 works correctly (only issue was the cosmetic 640 above).
- H8 (difficulty→frequency invariant, added mid-round) — refuted (sound): again/hard schedules sooner than good/easy for both content and personal cards; repeated again/easy diverge as expected; `/srs/hardest` and `/srs/queue` agree. Backend regression test added (tests/test_srs.py: test_again_persists_sooner_due_than_easy, test_personal_card_key_gets_identical_scheduling_to_content_key).
- H9 (deck integration loop, added mid-round) — refuted (sound): `/vocab/personal` auto-seeds a ReviewCard; add→queue→review→hardest loop consistent, card_key stable across all three views.

## Issues filed / gate results
- 621 (medium, srs) — validated by pm + critic → fixed (dev-fixer): `GET /srs/hardest` limit now `Query(30, ge=0)`, 422 on negative.
- 622 (low, srs) — validated by pm + critic → fixed: `/srs/queue` difficulty now rounded 1dp (None-safe), matching `/srs/hardest`.
- 640 (low, web) — validated by pm + critic → fixed: Review.tsx badge restructured (flex + separate spans) and copy lowercased.
- No `needs-info` or `deferred` issues this round.

## Housekeeping after fixes
- `/tmp/tef312/bin/python -m pytest -q` → 294 passed, 1 skipped
- `/tmp/tef312/bin/python -m ruff check app/ tests/` → clean
- `/tmp/tef312/bin/python -m ruff format --check app/ tests/` → clean
- `web/`: `VITE_API_BASE="" npm run build` → OK; `npm test` → 13 files / 42 tests passed
