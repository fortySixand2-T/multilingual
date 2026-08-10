# QA round 053 — plan

- date: 2026-08-09
- app under test: backend :9101 (SPA served single-origin from web/dist)
- scope: `feat/vocab-extra-content-decks` (95e4594) — extending word-forms +
  usage-examples from personal "My deck" cards to shared content-bank cards, via a
  consolidated per-user `vocab_extra` table and one generic endpoint set
  (`/vocab/extra`, `/vocab/forms`, `/vocab/examples`) that serves BOTH banks.

## Change surface (highest risk first)
Single commit `95e4594 feat(vocab): extend forms + usage examples to content-bank
decks` on top of the already-shipped, already-QA'd personal-card feature
(`a97822a`, PR #74, incl. fix for qa-660 empty-forms-caching). New/changed:
- `migrations/versions/0020_vocab_extra.py` — creates `vocab_extra`
  (user_id, card_key, forms, examples, updated_at; unique(user_id, card_key)),
  drops `user_vocab.forms`/`.examples` (added by 0019 three days ago, never deployed).
- `app/content/vocab_extra.py` (new) — `resolve_card_meta` routes `uv:`-prefixed
  keys to `user_vocab` (user-scoped query) and everything else to `content_vocab`
  (`session.get` by id); `get_extra`/`get_or_create_extra`.
- `app/content/vocab_extra_api.py` (new router, `/vocab/extra|forms|examples`,
  registered in `app/main.py`) — replaces the old personal-only
  `/vocab/personal/forms` and `/vocab/personal/examples` (now gone — confirmed via
  `/openapi.json` in preflight, they no longer appear).
- `app/content/personal.py::card_payload` no longer embeds forms/examples.
- `web/src/screens/WordDetail.tsx` now takes `{cardKey, pos}` (was a whole card
  object) and hydrates via `/vocab/extra` then `/vocab/forms` on expand; wired into
  `web/src/screens/Deck.tsx` (content bank, panel only rendered when flipped,
  `key={card.id}`) and `web/src/screens/MyDeck.tsx` (personal, unkeyed but each
  instance sits under a keyed list `<div key={c.card_key}>` parent, so per-card
  reset is structurally fine there too — verified by code read, not re-tested).

Existing coverage already found in `tests/test_vocab_extra.py` (8 tests) is
strong: content-card forms cache, unknown-card 404 for both bank shapes,
over-budget graceful degrade, qa-660 regression at the generic layer, examples
accumulate/dedup/history-on-read, personal card still works, and one
per-user-scoping test (`test_extra_is_scoped_per_user`, content-card only,
one direction: B reads after A writes). Backend 314/1 skipped, frontend 47
vitest + build clean, ruff clean, migration chain verified in preflight
(re-ran `alembic upgrade head` against the live dev DB in this round — 0019→0020
applied cleanly, `user_vocab.forms/examples` gone, `vocab_extra` present with the
right columns).

## Hypotheses (ranked)

| # | area | hypothesis | how to probe | persona |
|---|------|------------|--------------|---------|
| H1 | isolation | The one existing cross-user test only covers a **content** card key (A writes, B reads own `/vocab/extra` — gets nulls). Untested: a **personal `uv:` key** — if user B calls `/vocab/forms` or `/vocab/extra` with user A's literal `uv:<slug>` string (e.g. guessed/replayed from a shared support ticket, or two users who both add the same word and get the same slug), `resolve_card_meta`'s `UserVocab` query is scoped by `user_id`, so B should get 404/nulls, never A's data. | curl: A adds `manger` (`uv:manger`), generates forms/examples; B (fresh user) calls `/vocab/forms` and `/vocab/extra` with literal `card_key:"uv:manger"` — expect 404 (no card) since B never added it, and definitely never A's forms/examples. Then have B *also* add `manger` themselves (own `uv:manger`) and confirm B's row is independent (own empty state, not A's cached forms) even though the card_key string is byte-identical between the two users. | edge-case-breaker |
| H2 | endpoint removal | Old personal-only endpoints are fully gone, not just unlisted — confirm `POST /vocab/personal/forms` / `/vocab/personal/examples` 404 (route not found), and that `GET /vocab/personal` no longer echoes stale `forms`/`examples` keys in card payloads. | curl the two old paths directly; inspect a `GET /vocab/personal` card's JSON shape. | edge-case-breaker |
| H3 | concurrency | `get_or_create_extra` does select-then-insert with no unique-violation handling visible in the code; two near-simultaneous first-time `/vocab/forms` (or one `/forms` + one `/examples`) calls for the same (user, new card_key) could both miss the row and both try to `session.add()` a `VocabExtra`, risking an IntegrityError on the `uq_vocabextra_user_card` constraint on the second commit (500) instead of a clean second write. | curl: fire two concurrent `POST /vocab/forms` (or one forms + one examples) for a brand-new card_key for the same user; check both return 200, no 500, and exactly one `vocab_extra` row ends up persisted. | edge-case-breaker |
| H4 | budget/billing | Confirm no partial DB write or billing occurs when the model call itself fails (503, no ollama on this box) for BOTH `/vocab/forms` (inflecting pos) and `/vocab/examples` on a **content** card specifically (the personal-card version of this was already verified pre-this-slice; re-check it holds through the new shared code path) — no `vocab_extra` row created with a half-written state, no `daily_usage` bump. | curl a content noun/verb card's `/vocab/forms` and `/vocab/examples` with the real (ollama-less) AI router; expect a clean 503 (or whatever the router's failure surface is) and re-check `/vocab/extra` afterward shows no row / unchanged row. | edge-case-breaker |
| H5 | frontend/UX | Content-bank `Deck.tsx`: the "Forms & examples" panel only appears after flip, and moving to the next card resets the panel to collapsed/unfetched state rather than carrying over the previous card's forms/examples or `open` state (via `key={card.id}`). Also: on a real content card with a real invite-code login, does the button render for every pos, including ones with no gender (adjectives, invariant words)? | Browser: log in, open a content deck, flip a card, expand the panel (expect a clean 503-tolerant "No forms" or budget message, not a crash/blank/console error), advance to the next card, confirm the panel is collapsed again for the new card. | absolute-beginner |
| H6 | frontend/UX | `MyDeck.tsx` regression: the already-shipped personal-card panel still renders and behaves the same now that it's driven by the new generic endpoints (hydrate via `/vocab/extra`, not the old personal-specific route) — no visual regression, no stuck "Loading…", no console errors. | Browser: add a personal word, open its card, expand the panel, confirm graceful behavior under the ollama-less 503. | absolute-beginner |
| H7 | data shape | A content-bank card whose `data` JSON is missing a `pos` or `gender` key entirely (older/irregular rows) — `resolve_card_meta`'s `d.get("pos", "")` / `d.get("gender", "")` default to `""`; confirm this doesn't crash `/vocab/forms` (should just short-circuit to `{"forms": [], ...}` like any non-inflecting pos) and the frontend's `inflects(pos)` on an empty string doesn't render a broken panel. | curl: query `/content/vocab` for a real card, spot check whether any lack `pos`/`gender`; if none found in-bank, seed one via sqlite directly and hit `/vocab/forms`. | edge-case-breaker |

## Coverage gaps
- `/vocab/extra`, `/vocab/forms`, `/vocab/examples` have decent backend unit-test
  coverage already (see above) — this round is about the gaps in that coverage
  (cross-user `uv:` isolation, concurrency, endpoint-removal regression, missing
  pos/gender fields) plus the UI layer, which has **zero** browser-driven coverage
  of the new content-bank wiring (`Deck.tsx` + `WordDetail.tsx`) yet — it's brand
  new in this commit.
- No existing issue history at all for `vocab_extra`/`vocab_extra_api` — first
  round touching this code.

## Charters (per tester, with id blocks)
- `qa-tester` (curl, persona edge-case-breaker, ids **700–709**): chase H1
  (cross-user `uv:` key isolation, both directions), H2 (old endpoints truly
  gone + payload shape), H3 (concurrent first-write race on `vocab_extra`), H4
  (no partial state / no billing on a real provider failure for a content
  card), H7 (missing pos/gender in content data doesn't crash resolution).
  App base URL: `http://127.0.0.1:9101`. Invite codes `friend-001`/`friend-002`
  available for two independent test users (needed for H1 and H4-vs-H1
  isolation). No ollama running — expect and treat a clean 503/graceful
  degrade as correct for any hypothesis that requires an actual model call
  (H3, H4); focus assertions on state/billing/status-code correctness, not
  content of generated forms.
- `qa-browser-tester` (persona absolute-beginner, ids **710–719**): chase H5
  (content Deck.tsx flip-gated panel + per-card reset) and H6 (MyDeck.tsx
  personal-card panel regression). App base URL: `http://127.0.0.1:9101` (SPA
  already built and served single-origin by the running backend — no need to
  run a separate dev server). No ollama running on this box, so any "generate
  forms/examples" action will fail server-side (503) — that is expected;
  file an issue only if the UI handles it badly (crash, blank panel, stuck
  spinner forever, misleading "budget exhausted" message for a provider
  failure, console error), not for the absence of real generated content.

## Don't re-file (already settled)
- qa-660 (empty-forms cache falsy-check) — already fixed, and the generic layer
  has its own regression test (`test_forms_empty_result_cached_for_non_inflecting_pos`)
  confirmed present and passing.
- 610/611 (personal card_key degenerate/overlong) — already fixed in
  `personal_key()`, upstream of this slice; not touched by this change.
- Drill / Writing / Speaking 503 with no provider — expected, out of scope.
- `/vocab/forms` and `/vocab/examples` generation returning empty/no real content
  due to no ollama on this box — expected environment limitation, not a bug;
  only file if the *handling* of that failure is wrong (crash, wrong status,
  partial write, bad UX), never for "the forms are empty/missing" itself.

<!-- After the round, the planner notes each hypothesis: confirmed (→ issue NNN) /
     refuted (area sound) / untested. -->
