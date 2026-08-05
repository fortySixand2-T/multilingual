# QA round 049 — plan

- date: 2026-08-05
- app under test: backend + built SPA, single-origin, `http://127.0.0.1:8091`
- scope: Slice E — personal vocab decks ("build your own deck"), branch
  `feat/personal-decks` (afc4bac, not yet PR'd). Not merged to main; DB migrated
  to head (0018_user_vocab).

## Change surface (highest risk first)

- `app/content/personal.py` — new module: `slugify` (NFD-strip accents, non-alnum
  → `_`), `personal_key` = `uv:<slug>`, `add_personal` (idempotent per
  user+card_key, does not overwrite on re-add), `resolve_queue_vocab` (routes
  `uv:`-prefixed queue keys here). **`slugify`/`add_personal` do not call
  `strip_leading_article` or any lemma normalization** — that only happens in
  `app/content/enrich.py::enrich()`, which the UI always goes through via
  `/vocab/personal/preview` before calling `/vocab/personal`. A client that
  calls `POST /vocab/personal` directly (skipping preview) bypasses this
  normalization entirely.
- `app/content/tables.py::UserVocab` — `card_key: String(64)`, `fr: String(128)`.
  `AddBody.fr` allows up to 128 chars; `slugify` roughly preserves length (strips
  accents/diacritics only, doesn't shorten). A long `fr` can produce a slug whose
  `uv:<slug>` exceeds 64 chars — column-length mismatch, behavior depends on DB
  backend (silent truncation vs error).
- `app/content/personal_api.py`:
  - `POST /vocab/personal/preview` — budget-gated on `tokens_used_today(...,
    "vocab", ...)` vs `settings.vocab_daily_token_budget` (default 20000);
    returns `{"enrichment": null, "over_budget": true}` before calling the LLM
    once exhausted. Empty word after `strip_leading_article` → 422.
  - `POST /vocab/personal` (add) — **no budget check, no LLM call** (per spec);
    takes `fr`/`en`/`gender`/`pos`/`ipa`/`source` verbatim from the client body,
    `AddBody.fr` only enforces `min_length=1` (a single whitespace char passes),
    then `add_personal` does `fr.strip()` — so `" "` → `""` → slug `""` → card
    key literally `"uv:"`. Distinct whitespace-only inputs collapse to the same
    degenerate key (idempotency swallows the "duplicate").
  - `GET /vocab/personal/audio/{card_key}` — 404 if `card.audio_key` missing and
    `app.state.tts is None`; falls through to re-synth on any exception reading
    a stale cached key. TTS may be unconfigured on this instance (expected 404,
    not 500 — confirm it stays a clean 404).
  - `GET /srs/queue` → `resolve_queue_vocab` filters to `uv:`-prefixed keys only;
    content keys resolved separately. The two-bank boundary is enforced purely
    by string prefix — worth directly probing for collision.
- `web/src/screens/MyDeck.tsx` — new `/my-deck` screen: word input → "Look up"
  (`/preview`) → preview card → "Add to my deck" (`/vocab/personal`, always uses
  `preview.fr/en/gender/pos/ipa`, never the raw typed word) → list refresh +
  input clear. `over_budget` status shows fixed copy. Cards list uses
  `AudioButton` with `audio_url`. Nav entry from `Path.tsx`/`App.tsx` (⭐).

## Hypotheses (ranked)

| # | area | hypothesis | how to probe | persona |
|---|------|------------|--------------|---------|
| H1 | data/id-boundary | A personal word whose slug equals an existing content id (e.g. "chat", "café") coexists in `/srs/queue` alongside the content card, and each resolves to its own correct metadata (no shadowing either direction). | Add "chat" and "café" to a fresh user's personal deck (already content ids); pull `/srs/queue`, confirm both a content-bank `chat`/`café` key AND a `uv:chat`/`uv:cafe` key appear, each with correct `fr/en/level/personal` fields, and reviewing one doesn't touch the other's SRS state. | edge-case-breaker |
| H2 | data integrity | Idempotent re-add: adding the same word twice returns `added:false` the second time and does not overwrite gloss/pos/gender/ipa even if the second POST body has different values (simulating a stale/edited preview). Weird inputs — "le chat" (leading article) vs "chat" bypassing preview, accented "café", apostrophe "l'eau", empty string, whitespace-only, very long (120+ char) `fr`, HTML/script tag in `fr`/`en` — are stored sanely and the unique constraint (`user_id`,`card_key`) holds without 500s. | `curl` `POST /vocab/personal` directly (skip preview) with each crafted body; re-POST identical body to check `added:false` + unchanged fields; re-POST same word with different `en` to check original is preserved; check card_key length/shape in the response for the long-word case. | edge-case-breaker |
| H3 | srs integration | A freshly added personal card is immediately due and appears in `/srs/queue`; `POST /srs/review` against its `uv:` card_key succeeds (not 404) and advances its due date so it drops out of an immediate re-query of the queue. | Add a word, confirm it's in `/srs/queue`, POST a review rating for its `card_key`, re-fetch queue and confirm the card's due state moved (or it's no longer surfaced as due "now"). | edge-case-breaker |
| H4 | budget gate | `/vocab/personal/preview` stops calling the LLM and returns `{"enrichment": null, "over_budget": true}` once the day's "vocab" token usage ≥ `vocab_daily_token_budget`; `/vocab/personal` (add) still succeeds when over budget (it never calls the LLM, so it must be budget-independent). | Drive usage over the (default 20000, confirm actual configured value) "vocab" budget via repeated `/preview` calls (or inspect/seed `usage` table directly if that's faster), confirm the over-budget response shape, then confirm `POST /vocab/personal` still works normally while over budget. | edge-case-breaker |
| H5 | auth scoping | friend-002's `/vocab/personal` (GET) is empty / does not include cards friend-001 added; friend-002 cannot review or fetch audio for friend-001's `uv:` card_key. | Sign up both invite codes as separate users, add cards as friend-001, then as friend-002 check `GET /vocab/personal` is empty and `GET /vocab/personal/audio/<friend-001's card_key>` / `POST /srs/review` against that key 404s (not leaking friend-001's data). | edge-case-breaker |
| H6 | ui/ux flow | `/my-deck` happy path (look up → preview shows meaning/gender/IPA → add → appears in list, input clears) works; empty-deck state renders the empty-state copy; over-budget state shows "Daily word-lookup limit reached."; the ⭐ nav link from the home hub reaches `/my-deck`; a card's 🔊 button is present and its click doesn't crash the screen if TTS is unconfigured (404 handled gracefully by `AudioButton`, not a stuck spinner / console error storm). | Drive the browser: reach `/my-deck` via the ⭐ nav link, look up a real word, add it, confirm list + input-clear, reload to confirm persistence, try an empty-deck fresh account, try clicking 🔊 and check network/console for a graceful failure. | absolute-beginner |
| H7 | ui/ux edge | Typing a nonsense/non-French string ("asdfasdf", or a string that makes the LLM return an empty/garbage gloss) into "Look up" still renders a coherent preview card (no blank crash) or a sensible error, and rapid double-clicking "Look up"/"Add to my deck" doesn't file duplicate cards or leave the UI in a stuck "…/Adding…" state. | In the browser, look up garbage input and observe the preview card; double-click Add quickly and check the resulting list for duplicates. | edge-case-breaker (or absolute-beginner if time allows, lower priority) |

## Coverage gaps

- No prior QA issue history for `/vocab/personal*` — entirely new surface, zero
  prior passes. Related past patterns worth knowing (don't re-file as-is):
  - qa-290 (`/srs/queue` negative limit bypasses pagination) — **rejected**.
    Lenient pagination limits are an accepted pattern in this codebase; don't
    file the same class of finding against `/vocab/personal` list endpoints
    unless it actually 500s or leaks cross-user data.
  - qa-300 / qa-321 (`/vocab/known`, `/srs/add` accept malformed/nonexistent
    card keys leniently) — qa-321/qa-311/qa-310 were fixed (`done`), qa-300 was
    **rejected**. The precedent: strict-typing complaints on lenient string
    inputs are usually rejected unless they cause a crash or data corruption;
    focus H2 probes on cases that actually break something (500, silent data
    loss, cross-record collision), not "the API accepted an unusual string."
  - qa-580 (speech vocab-review had no budget check) — **done**, fixed. Confirms
    budget-gate bugs in this codebase are real and get fixed — H4 is a
    reasonable target, not a stretch.
  - qa-550 (speaking topic-id collision across levels) — **deferred**. Shows the
    project has an existing appetite for two-namespace collision bugs; H1 is the
    vocab-deck analog and worth taking seriously.
- No unit/integration test file located yet for `app/content/personal.py`'s
  `slugify` edge cases (long words, empty string, punctuation-only) — testers
  should check `tests/` for existing coverage before filing, but this looks like
  a gap.
- Frontend `MyDeck.test.tsx` exists — testers should skim it before filing UI
  issues to avoid duplicating already-covered assertions, but it's unlikely to
  cover the double-click/garbage-lookup UX cases in H7.

## Charters (per tester, with id blocks)

- `edge-case-breaker` via `qa-tester` (ids 610–629): chase H1, H2, H3, H4, H5,
  and H7's non-UI half (duplicate-add-under-race is hard over curl; focus H7 in
  the browser instead — treat H7 as browser-only). Backend at
  `http://127.0.0.1:8091`. Sign up two users with invite codes `friend-001` and
  `friend-002` (`POST /auth/signup`, `POST /auth/login`), keep both bearer
  tokens. Read `app/config/settings.py` for the actual configured
  `vocab_daily_token_budget` on this instance before trying to exhaust it (may
  be overridden in `.env`/env vars vs. the 20000 default in code). If exhausting
  the budget via real LLM calls is too slow/expensive, note that as a
  coverage gap rather than skipping H4 silently — check if there's a faster way
  (e.g. a test-only usage-seeding endpoint) but do not fabricate a bypass that
  isn't part of the real app surface.
- `absolute-beginner` via `qa-browser-tester` (ids 630–639): chase H6 and H7.
  App at `http://127.0.0.1:8091` (single-origin, built SPA — use this origin
  directly, not a dev server). Sign up / log in with invite code `friend-002`
  if not already used by the curl tester (avoid cross-tester state collisions;
  coordinate by using a fresh invite-derived account or a distinct
  email/username). Navigate via the ⭐ nav link, not by typing `/my-deck`
  directly, to also verify the nav entry itself is reachable.

## Don't re-file (already settled)

- qa-290, qa-300 (lenient input acceptance without a crash) — rejected pattern,
  see Coverage gaps above.
- Any TTS-unconfigured 404 on `/vocab/personal/audio/{card_key}` — expected
  degradation per the task brief, not a bug. Only flag if it 500s instead of
  404s, or if the frontend `AudioButton` mishandles the 404 (stuck spinner,
  console error storm, crash) — that part of H6 IS in scope.
- Generic "strict validation would be nicer" findings on `AddBody` fields
  (e.g. `gender` accepting values other than m/f/mf, `source` accepting
  arbitrary strings) — out of scope unless it causes a rendering bug or data
  integrity issue downstream (e.g. genderTag() rendering blank vs actually
  crashing).

## Execution notes

- Preflight: `GET /health` on :8091 → 200 confirmed before this plan was
  written. Next free issue id block starts at 610 (last filed issue on disk:
  602).
- Sequence: qa-tester + qa-browser-tester in parallel (disjoint id blocks) →
  qa-pm triage on all `status: open` → qa-critic on everything with a
  `## Triage` block → dev-fixer on `status: validated` only.

## Outcome (2026-08-05)

The qa-planner orchestrator died twice on API/connection errors mid-run; the round was
finished by hand against the live instance. Two issues found, both confirmed real,
in-scope, and **fixed** on `feat/personal-decks`:

- **#610 (medium) — degenerate `uv:` key.** Whitespace/punctuation/non-Latin `fr`
  slugified to empty → a shared blank card seeded into review. Fixed: `normalize_lemma`
  + `EmptyLemmaError` → 422; leading article also stripped on direct add.
- **#611 (low) — `card_key` overflow.** Long `fr` (≤128) minted a `uv:<slug>` past the
  String(64) column (latent 500 on Postgres). Fixed: `personal_key` clamps the slug.

Everything else passed: two-bank id boundary, idempotency, SRS integration (queue +
review on a `uv:` key), per-user auth scoping, and the preview budget gate (short-circuits
before the LLM). `/preview` happy path not exercisable locally (no LLM → clean 503, no
billing); covered by the faked-router unit test. Post-fix verification: backend 281
passed, ruff check + format clean, FE build + 39 tests green.
