# QA round 047 — plan

- date: 2026-08-01
- app under test: backend :9010 (restarted mid-round — was serving stale
  pre-Slice-3a code, missing `/speech/session/{id}/vocab-review`; confirmed
  fixed after restart, `vocab_extract` now in `/health` profiles) / SPA
  (vite dev server) :5173, single-origin `/api` proxy to :9010.
- scope: Slice 3a — Speaking→vocab review loop, commit 62a1d2c on
  `feat/anki-vocab-decks` (merged to `main` locally, 1 commit ahead of origin).

## Change surface (highest risk first)

- `app/speech/api.py::session_vocab_review` (NEW) — `POST
  /speech/session/{session_id}/vocab-review`. Reads the session's persisted
  turns (scoped to `user.id` + `session_id`), runs one LLM extraction pass,
  resolves lemmas to `ContentVocab`, bills usage, returns candidates.
  **Notably: no daily-budget check before the LLM call** — contrast with
  `/speech/turn`, which calls `examiner.turn(..., daily_budget=...)` and
  short-circuits with `over_budget: true` before spending tokens. The docstring
  says this endpoint is "re-runnable for a past session_id" by design, with no
  mention of a cap.
- `app/speech/vocab_review.py` (NEW) — `_parse_words` (tolerant JSON/fence/
  bare-list parsing), `_norm`/`_deaccent` (article-stripping + accent fallback
  matching), `resolve_to_vocab` (dedup, in-deck exclusion, `limit=12` cap while
  `_MAX_WORDS=10` in the extraction prompt — the cap can never bind under
  normal LLM output, only if the model ignores the prompt's word limit).
- `app/speech/api.py::_recent_history` — now takes `session_id: str = ""`;
  empty string = old unscoped-by-session query (legacy/free-flow compat).
  `speech_turn` persists `session_id or None`.
- `app/speech/tables.py` / `migrations/0017` — nullable `session_id` on
  `speech_turns`, indexed. Already applied to `data/tef.db` (alembic head =
  0017, confirmed).
- `app/config/ai_routing.yaml` / `.ollama.yaml` — new `vocab_extract` profile,
  `format: json`. Local dev routes to ollama/llama3.1 (no format enforcement
  guarantee from every backend — `_parse_words`'s tolerance is the real safety
  net if the model doesn't emit clean JSON).
- `web/src/screens/Speaking.tsx` — `sessionId` state (`crypto.randomUUID()`),
  regenerated on `pickTopic` (covers both picking *and* "Change topic", since
  both route through the same handler with a new or null topic). `SessionReview`
  keyed by `sessionId`, gated on `hasTurns = sessionTurns > 0`. Optimistic add
  with rollback-on-failure per word (not per whole batch); "Add all" iterates
  the same per-word `add()`.
- `tests/test_speech.py` (+111 lines) already cover: JSON-parsing tolerance,
  article/case normalization, happy-path resolution (mixed known/unknown
  lemma), already-in-deck exclusion, empty/unknown session → no LLM call,
  session_id persisted + returned on `/speech/turn`. **Not covered by the new
  tests:** cross-session leakage (session A's turns showing in session B's
  review), budget/repeat-call behavior, multi-user isolation on
  `session_vocab_review`, `resolve_to_vocab` dedup when the *same* vocab id is
  reachable by two different surface forms in one extraction, and any frontend
  test for `SessionReview`/`pickTopic` (no `Speaking.test.tsx` exists).

## Hypotheses (ranked)

| # | area | hypothesis | how to probe | persona |
|---|------|------------|--------------|---------|
| H1 | billing/abuse | `session_vocab_review` never checks `speaking_daily_token_budget` before calling the LLM (unlike `/speech/turn`), and the docstring frames it as re-runnable — so a user who has already exhausted today's speaking budget (or wants to run up cost) can call this endpoint repeatedly for the same or different sessions with no cap, each call billing more tokens to the same ledger with nothing ever refusing. | Seed/produce a session with turns; call `POST /speech/session/{id}/vocab-review` many times in a row (or after driving `/speech/turn` past `over_budget: true`) and confirm it keeps returning 200 + keeps billing rather than degrading/capping. | edge-case-breaker |
| H2 | api/data isolation | Session scoping in the new endpoint and in `_recent_history` might leak across sessions or users if `session_id` collisions occur (e.g. two different users independently picking the same client-generated UUID — extremely unlikely but the query is `user_id == X AND session_id == Y`, so verify both predicates are actually applied, not just one). | Two users, same `session_id` string; turns for user A; call vocab-review as user B with that id — expect empty candidates, not user A's words. Also verify calling vocab-review for a `session_id` that belongs to a *different, real* session of the same user only returns that session's words (not bleeding in from another session of theirs). | edge-case-breaker |
| H3 | data/logic | `resolve_to_vocab`'s `already` exclusion and `exact`/`loose` dual-lookup: does re-running vocab-review immediately after adding a word (via `/srs/add`) correctly exclude it on the second run? Does a lemma that only matches via the accent-insensitive fallback (`loose`) get picked correctly when the exact-normalized map has no entry, and does the *dedup-by-`row.id`* correctly collapse two different surface words in one extraction that resolve to the same vocab id? | Seed a vocab row with an accented `fr` value; extraction returns the deaccented form; confirm it resolves. Add a word via `/srs/add`, then call vocab-review again for the same session — confirm it's no longer suggested. Craft an extraction result with two variants of the same word (e.g. "café" and "Café") and confirm only one candidate for that `card_key`. | edge-case-breaker |
| H4 | api/regression | `_recent_history`'s new `session_id` scoping doesn't regress `/speech/turn` for callers that omit `session_id` (old client, or a client that reuses the same call pattern as before) — history should still return the last 3 turns unscoped, and turns without a `session_id` should not appear scoped to any session incorrectly. | Post two turns with no `session_id` field at all; confirm history/context still works as before (no error, no session-not-found behavior) and the persisted rows have `session_id IS NULL`. | edge-case-breaker |
| H5 | ui/ux | `SessionReview`'s state machine: "Finish & review words" only appears once a turn has happened this session (`sessionTurns > 0`); switching topics (or hitting "Change topic") regenerates `sessionId` and unmounts/remounts `SessionReview` (via `key={sessionId}`) — does this silently discard an in-progress or completed-but-not-fully-added review with no warning, losing candidate words the learner hadn't gotten to yet? Is there any confusing double-render/flash when `hasTurns` flips from false→true mid-session? | Drive the Speaking screen (topic-picker-only, no live STT needed): pick a topic, note the UI has no way to browse a past session's review after switching topics away from it. Confirm whether "Change topic" while a completed-but-partially-added candidate list is showing wipes it without confirmation. This can be probed by inspecting component state/behavior in the browser even without STT — e.g. force `sessionTurns` via whatever dev affordance exists, or note as a design-level observation if STT-gating blocks reaching `hasTurns=true` in this environment. | absolute-beginner |
| H6 | ui/ux | Topic-picker interactions haven't regressed with `pickTopic` now doing extra work (new session id, clearing turns) on every pick, including re-clicking the *already selected* topic (not applicable via UI since picking hides itself behind the task card — "Change topic" is the only path back) — confirm "Change topic" → picker list still renders correctly for both levels with topics and levels with none (`topics.length === 0` hides the whole picker). | Navigate Speaking screen across at least two CEFR levels; verify topic picker renders/hides correctly, "Change topic" returns to the list, and no dangling empty state appears when a level has zero topics. | absolute-beginner |

## Coverage gaps

- No frontend test file exists for `Speaking.tsx` (`SessionReview`, `pickTopic`,
  `TopicPicker`) — this whole UI surface has zero automated regression coverage,
  same gap noted in round 045.
- No test exercises budget/rate-limiting on `session_vocab_review` (H1) — this
  is a real blind spot, not just an untested edge case; the endpoint has no
  such control at all in the diff.
- No test exercises cross-user or cross-session isolation for
  `session_vocab_review` (H2) beyond the single-session happy path.
- `docs/anki-vocab-plan.md` doesn't mention a budget/rate design for this
  endpoint either — worth flagging to the human as a possible scope gap rather
  than assuming it's deliberately deferred.

## Charters (per tester, with id blocks)

- `edge-case-breaker` via `qa-tester` (ids 580–589): chase H1, H2, H3, H4.
  Backend at `http://127.0.0.1:9010` (just restarted — confirm
  `/speech/session/{id}/vocab-review` is reachable before starting; if you get
  a 404 the server is stale, restart it with
  `nohup /tmp/tef312/bin/python -m uvicorn app.main:app --host 127.0.0.1 --port 9010 &`
  from `/Users/sirius/projects/multilingual`). Sign up via the invite-code flow
  (`INVITE_CODES` already set on the running server, same as prior rounds). STT
  is unconfigured so `/speech/turn` returns 503 — for H1/H2/H3/H4 you need
  persisted `SpeechTurn` rows with real `session_id`s and vocab already in
  `ContentVocab`, which you *cannot* create through `/speech/turn` here (503
  before persistence). Prefer HTTP+unit-hybrid: use the same dependency-
  override / fake-router / seed pattern as `tests/test_speech.py` (see
  `JsonRouter`, `_seed_vocab`, `_client(stt=FakeSTT(), ...)`) to write focused
  pytest cases against the live app module, OR seed rows directly into
  `data/tef.db` (a copy, not the shared dev DB, if you're going to leave state
  behind) and drive only `POST /speech/session/{id}/vocab-review` over HTTP
  with real auth tokens — that endpoint itself needs no STT. State your method
  per issue so the pm/critic can judge reproducibility.
- `absolute-beginner` via `qa-browser-tester` (ids 590–599): chase H5, H6. App
  at `http://127.0.0.1:5173` (SPA dev server; confirm it proxies `/api` to
  :9010 — it was already serving 200 before the backend restart, no action
  needed there). Sign up / log in, go to Speaking, work the topic picker across
  at least two levels. Do not attempt real mic/recording — `/speech/status`
  reports unavailable by design; note config-blocked paths (can't reach
  `sessionTurns > 0` without a working turn) rather than filing them as bugs.
  If `SessionReview`/the Finish button is genuinely unreachable without a live
  turn, say so plainly in your report as untested rather than guessing at
  behavior.

## Don't re-file (already settled)

- 540 (mic requested before availability check) — done; not touched by this
  slice, don't re-verify unless you notice a regression.
- Speaking/Writing/Drill 503 with no STT/TTS provider configured — expected,
  documented environment state, not a bug.
- 550/560/561 (topic id / instruction-hint issues from round 045) — out of
  scope for this round; don't re-probe topic-id ownership again here, this
  round's H2 is specifically about the *new* vocab-review endpoint's session
  scoping, not topic_id.
- 240 (writing word-count validation) — unrelated feature, don't conflate with
  this round's usage/budget hypothesis (H1) even though both are "missing a
  guard before an LLM call" in flavor — file H1 findings against
  `session_vocab_review` specifically.

<!-- After the round, the planner notes each hypothesis: confirmed (→ issue NNN) /
     refuted (area sound) / untested. -->

## Outcomes

- **H1 (no daily-budget check on `session_vocab_review`) — CONFIRMED.** Filed as
  issue 580, validated by both qa-pm and qa-critic (independent code read +
  test re-run), fixed by dev-fixer. `session_vocab_review` now checks
  `tokens_used_today(..., "speaking", ...)` against
  `settings.speaking_daily_token_budget` before calling the extraction LLM,
  returning `{"candidates": [], "over_budget": true}` once exhausted — mirrors
  the existing `SpeakingExaminer.turn` guard. Frontend (`SessionReview`) now
  shows a "come back tomorrow" message on `over_budget`. Permanent regression
  test added (`test_vocab_review_over_budget_skips_llm_and_stops_billing`).
  Backend suite: 244 passed, 1 skipped (up from 243). This was a real,
  in-scope, unbounded-cost/abuse gap in brand-new billing surface — the
  highest-value find of the round.
- **H2 (cross-user/cross-session isolation on the new endpoint) — REFUTED.**
  Verified via seeded pytest: both `user_id` and `session_id` predicates are
  genuinely enforced; a second user posting to the same `session_id` string
  gets empty candidates, never another user's derived words.
- **H3 (resolve_to_vocab logic: accent fallback, in-deck exclusion, dedup) —
  REFUTED (all three sub-cases).** Accent-insensitive fallback resolves
  correctly; a word added to the deck is correctly excluded on a re-run;
  casing/whitespace variants of one word correctly collapse to a single
  candidate. (Tester noted a latent global-uniqueness assumption in the
  `exact`/`loose` maps if two different `ContentVocab` rows ever share a
  normalized `fr` value across the whole catalog — not exercised by the real
  content bank today, not filed as a separate issue, worth a mental note only.)
- **H4 (session_id-less turns / `_recent_history` regression) — REFUTED.**
  Turns posted with no `session_id` persist `SpeechTurn.session_id = NULL`
  (not empty string, no error); old-style callers are unaffected.
- **H5 (state loss on topic change, no confirmation) — UNTESTED /
  not filed.** Browser tester confirmed "Change topic" silently clears the
  transcript panel, but the test account had no prior turns to lose, so actual
  data loss was never demonstrated. Flagged as a design-level observation, not
  a bug: `Speaking.tsx` seeds `turns` from all-time `/speech/history` on mount
  but `pickTopic` unconditionally wipes it with no confirmation and no way
  back — worth a human's attention if it recurs, not filed per the "only file
  demonstrated bugs" instruction.
- **H6 (topic picker regressions across levels) — REFUTED.** All four CEFR
  levels render their own topics correctly; task card, "Change topic", level
  switching, and controls-disabled-while-recording/busy all behaved correctly
  in the browser; no console errors. No level with zero topics existed to
  exercise the empty-picker path — untested, not a gap worth chasing further
  this round.

## Environment note for future rounds

The backend at :9010 was found running **stale pre-Slice-3a code** at round
start (no `--reload`, process started before this feature was written/merged)
— `/speech/session/{id}/vocab-review` 404'd and `vocab_extract` was missing
from `/health`'s profile list. Restarted it
(`/tmp/tef312/bin/python -m uvicorn app.main:app --host 127.0.0.1 --port 9010`)
before handing charters to testers. Future rounds should verify the running
server's `/health` profiles and `/openapi.json` paths actually include the
round's target surface before chartering testers against it — a stale server
would have silently produced false "endpoint doesn't exist" 404s instead of
real findings.

## Filed / fixed

- Issue 580 (high, area: speech) — validated → done.

## Residual risk

- H5's design-level UX gap (session state wiped with no confirmation on topic
  change) is real in the sense of the observed silent-clear behavior, but
  unconfirmed as a *loss* since the browser account had nothing to lose. Worth
  a human glance if a returning learner ever reports vanished words mid-review.
- The `exact`/`loose` normalized-lemma maps in `resolve_to_vocab` assume no two
  `ContentVocab` rows share a normalized `fr` across the whole catalog; true
  today, not enforced, not a bug yet.
