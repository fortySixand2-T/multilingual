# QA round 048 — plan

- date: 2026-08-01
- app under test: backend + SPA single-origin :9020 (branch `feat/anki-vocab-decks`,
  commit a141cc5; frontend built via `VITE_API_BASE="" npm run build`, served by
  `app/main.py`'s SPA mount)
- scope: Slice 3b — "resurface last conversation's review words" nudge on the
  Speaking screen (`GET /speech/last-session` + generalized `SessionReview` nudge)

## Change surface (highest risk first)
`git diff 2dcd3c6 a141cc5`:
- `app/speech/api.py` — new `GET /speech/last-session?exclude=<sid>`: most recent
  prior `session_id` for the current user (query on `SpeechTurn`, ordered by
  `id desc`, filters `session_id IS NOT NULL` and `!= exclude`). No LLM.
- `web/src/screens/Speaking.tsx` — `SessionReview` generalized from
  `{sessionId, hasTurns}` to `{sessionId, visible, label, blurb, dismissible}`.
  New `priorSession` state + `useEffect([sessionId])` fetching
  `speechLastSession(sessionId)`. Renders an opt-in, dismissible nudge above the
  transcript when `priorSession && priorSession !== sessionId`. End-of-conversation
  review is the same component now (`visible={sessionTurns>0}`, non-dismissible).
- `web/src/api.ts` — thin `speechLastSession` wrapper.
- Tests added on both sides (`test_speech.py`: latest/exclude/null;
  `Speaking.test.tsx`: mock only, no new behavioral assertions for the nudge).

Notably *not* covered by the diff's own tests: multi-user isolation on
`last-session` (only single-user scenarios), any live-browser check of the nudge
rendering/dismiss/self-clearing, and the interaction between the nudge and the 3a
budget gate (2dcd3c6).

## Hypotheses (ranked)
| # | area | hypothesis | how to probe | persona |
|---|------|------------|--------------|---------|
| H1 | speech (API) | `last-session` may leak across users — if the SQL only filters by `session_id`/`exclude` and not carefully by `user_id` in all paths, user A could see user B's session id | seed turns for two users interleaved (B's turn has a higher id than A's last), call `/speech/last-session` as A, assert it's still A's own prior session, never B's | qa-tester |
| H2 | speech (API) | legacy NULL `session_id` turns might still surface as "prior session" (`None` returned as a session id, or a crash) if a user's *only* turns predate the `session_id` column | seed a turn with `session_id=NULL` only, call `/speech/last-session`, expect `null`, not an error or the literal string "None" | qa-tester |
| H3 | speech (API) | `exclude=""` (empty string, the JS default) vs. omitted `exclude` should behave identically (no filtering) — a subtle off-by-string bug (`exclude=""` matching a session literally named `""`) is plausible | call with no query param, with `?exclude=`, and with `?exclude=<real-sid>`, compare | qa-tester |
| H4 | speech (API) | self-clearing design: after adding a prior session's words via `vocab-review`, calling `vocab-review` again on the *same* session should return `candidates: []` (not still list the now-already-added words) — this is the load-bearing assumption for "no reviewed flag" | seed a session with vocab-matchable turns, POST vocab-review (adds to `ReviewCard`), POST vocab-review again, assert second call's candidates are empty/excludes previously-added ones | qa-tester |
| H5 | web (UI) | the nudge might auto-fire the billed vocab-review call on mount instead of staying opt-in (regression of the "no auto-billing" contract) — the `useEffect` only fetches `last-session` (cheap), but worth confirming no code path also calls `vocab-review` before a click | load Speaking with a prior session present, watch network calls before any click; only `speechHistory`/`speechStatus`/`speakingTopics`/`speechLastSession` should fire, not `vocab-review` | qa-browser-tester |
| H6 | web (UI) | "Not now" dismiss and the `key={prior-<sid>}` remount logic: does dismissing the nudge stick for that session, and does switching topics (new `sessionId`) correctly *un-dismiss* by surfacing the new prior session? | dismiss the nudge, confirm it's gone; switch topics; confirm a fresh nudge for the newly-prior session appears (not still hidden) | qa-browser-tester |
| H7 | web (UI) | rendering regression: `label`/`blurb` are now plain JS string props instead of literal JSX text — confirm `✓ Finish & review words` and the nudge's own label render as plain text (no literal `&amp;`, no XSS-style escaping artifact, no missing checkmark) | visually inspect both the end-of-conversation button and the nudge button/text | qa-browser-tester |
| H8 | web (UI) | double-render/refetch loop from `useEffect([sessionId])` — since `sessionId` is stable via lazy `useState` and only changes on topic switch, a loop is unlikely, but verify no repeated/duplicate `speechLastSession` network calls fire on every keystroke/render while idle | watch network tab for ~10s idle on the Speaking screen, count `last-session` calls (expect exactly 1 per session) | qa-browser-tester |
| H9 | web (UI) | nudge + end-of-conversation review both visible at once (learner has an unreviewed prior session *and* has already spoken in the new session) — check they don't visually collide/overlap or confuse the learner about which "Finish" belongs to which conversation | start a new session, speak a turn (so end-of-conversation card shows) while a prior-session nudge is also showing; inspect layout | qa-browser-tester |
| H10 | speech (API) | budget gate interaction (3a fix, 2dcd3c6): if the user is already over budget, does clicking the *nudge* still correctly show the "reached today's limit" message and refuse to bill, same as the end-of-conversation path? | exhaust the daily budget, then call vocab-review against the prior session id (not the current one) — confirm `over_budget` still gates it | qa-tester |

## Coverage gaps
- No prior issue history at all for `/speech/last-session` or the generalized
  `SessionReview` — this is genuinely new surface.
- Multi-user isolation for any `session_id`-scoped speech query has not been
  explicitly tested before in this codebase (worth checking if the pattern
  generalizes — flag as a broader note if found, not just file for this endpoint).

## Environment / seeding note (for both testers)
- Live server: `http://127.0.0.1:9020`, branch `feat/anki-vocab-decks` @ a141cc5,
  DB at `./data/tef.db` (sqlite), invite codes `qa-001,qa-002` accepted for signup.
  `GET /speech/status` confirms STT is unavailable here (`{"available":false}`), so
  `/speech/turn` cannot be driven end-to-end through the real UI or curl.
- To get a real prior `session_id` into the DB for either stage to observe (via
  `GET /speech/last-session`, `GET /speech/history`, or the rendered nudge), insert
  directly into the `speech_turns` table for your test user's `user_id`
  (`id, user_id, session_id, mode, transcript, reply_text, reply_audio_key, created_at`
  — see `app/speech/tables.py`), or reuse the `FakeSTT`/dependency-override client
  pattern in `tests/test_speech.py` against a throwaway app instance pointed at the
  same `./data/tef.db` file. Sign up/log in first via the real auth endpoints to get
  a `user_id`, then seed turns for that id.
- qa-tester: seed via direct sqlite3 insert or a short ad hoc pytest/python snippet;
  whichever is fastest, note which you used in the issue's repro steps.
- qa-browser-tester: if you cannot seed directly (no DB/py tooling in your toolset),
  ask qa-tester's output/timing isn't guaranteed — instead seed yourself via the
  same sqlite3 CLI (`sqlite3 data/tef.db "INSERT INTO speech_turns (...) VALUES (...);"`)
  before starting the Chrome checks; Bash is available to you for this.

## Charters (per tester, with id blocks)
- `qa-tester` (ids 590–599): HTTP/curl against `http://127.0.0.1:9020`. Chase
  H1–H4 and H10 — user-scoping/exclude/null correctness on
  `GET /speech/last-session`, the self-clearing `resolve_to_vocab` assumption via
  repeated `vocab-review` calls, and the budget-gate interaction with a
  non-current session id. Use the fake-STT/seeded-`SpeechTurn`/`ContentVocab`
  pattern already in `tests/test_speech.py` if seeding via the running server's
  HTTP surface isn't sufficient (e.g. run ad hoc pytest snippets against a test
  DB, same as issue 580's approach) — but prefer live HTTP against :9020 first
  since `last-session` needs no STT/LLM and is fully exercisable that way with a
  real invite-code login (`INVITE_CODES=qa-001,qa-002` is set on the server).
- `qa-browser-tester` (ids 600–609): drive the real SPA at `http://127.0.0.1:9020`
  in Chrome as the `returning-learner` persona (a learner coming back to Speaking
  after an earlier abandoned conversation is exactly this feature's target user).
  Chase H5–H9 — nudge visibility/no-auto-billing, dismiss + topic-switch refresh,
  label/blurb text rendering, refetch-loop absence, and nudge/end-of-conversation
  co-visibility. Speech STT is likely unconfigured locally (`/speech/turn` may
  503) — note that as config-blocked rather than getting stuck; the nudge itself
  only needs `GET /speech/last-session` (no STT) so it should render regardless.
  To get a "prior session" to show, either post a turn via curl/qa-tester first
  (coordinate: qa-tester should seed one before or note in its issue if timing
  matters) or use the API test hooks — if turns truly can't be seeded from the
  browser stage alone, note H5–H9 as best-effort/partially-blocked rather than
  skipping the round.

## Don't re-file (already settled)
- Speaking screen requesting mic before checking availability — filed as 540,
  unrelated to this slice.
- TTS diction/sanitizer gaps (570–573) — unrelated to this slice, already
  triaged.
- Speech backend 503 with no STT/LLM provider configured — expected in this
  environment, not a bug; note as config-blocked instead of filing.
- Vocab-review missing budget check — already fixed (580 → 2dcd3c6); only
  re-probe the gate's *interaction* with the new nudge path (H10), don't re-file
  the base gate.

<!-- After the round, the planner notes each hypothesis: confirmed (→ issue NNN) /
     refuted (area sound) / untested. -->
