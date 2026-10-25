# QA round 058 — plan

- date: 2026-10-25
- app under test: backend + SPA single-origin at `http://127.0.0.1:9200`, pointed at
  the box's real Ollama (`OLLAMA_BASE_URL=http://10.0.0.54:11434`,
  `AI_ROUTING_PATH=app/config/ai_routing.ollama.yaml`,
  `OLLAMA_MODEL=qwen2.5:7b-instruct-q4_K_M`). Scratch DB `/tmp/qa058/qa.db`, content +
  speaking topics synced (`python -m app.content.sync <lvl>` and
  `python -m app.speech.topics <lvl>` for a1/a2/b1/b2 — note these are **two separate
  sync commands**, the latter is easy to forget and leaves `/speech/topics` empty).
- scope: PR #120, `origin/main..feat/topic-openers` (368192b, a481ede, 6cf6628) —
  raw-ChatML/`/api/generate` for qwen models, whole-session examiner history (16-turn
  cap, 8-turn trim blocks), a background prompt-cache warm-up on `/speech/opener`, and
  5 authored `{fr,en}` openers per topic (29 topics, a1–b2).

## Change surface (highest risk first)

1. **`app/ai/adapters/ollama_adapter.py`** — for `model.startswith("qwen")`, renders
   ChatML client-side and POSTs `/api/generate` with `raw: true` instead of
   `/api/chat`. This is the literal provider for **every** LLM feature on the live
   box when its profile's primary is `ollama/qwen*`: writing feedback (`format:
   json`), vocab extract/forms/examples (`format: json`), drill, grammar explain,
   speaking examiner turns/openers. A bad render (wrong stop behavior, broken
   `format: json` combo with raw mode) silently degrades every one of those at once.
   No `"stop"` option is set in the payload — raw mode relies entirely on the
   model's own Modelfile-configured stop sequence to end the turn.
2. **`app/speech/api.py` `_recent_history`** — history is now the whole session,
   capped at 16 turns, trimmed 8 at a time (`cut = ((over-1)//8 + 1) * 8`). Replaces
   a simple "last 3 turns" window. Off-by-one in the cut formula, or the row order
   query (`order_by(SpeechTurn.id).offset(cut)` with no `.limit()`), would either
   silently drop/duplicate turns or feed the examiner a misordered conversation.
3. **`/speech/opener` background `warm()`** (`app/speech/examiner.py`) — a sync
   1-token completion scheduled via `BackgroundTasks` after the opener commits,
   gated on `router.primary("examiner_roleplay").startswith("ollama/")`. Must never
   slow/break the opener response and must never fire (or bill) when the profile's
   primary is hosted.
4. **Authored topic openers** (`content/*/speaking/*.yaml`, `app/speech/topics.py`,
   `app/speech/api.py`) — `SpeakingTopic.openers: list[TopicOpener]`, picked at
   random excluding the line this user last heard **on that topic** (matched by
   `reply_text` string, scoped only by `user_id` — relies on opener strings being
   unique per topic, which holds today but has no DB-level guard). Canned audio
   keyed by `sha1(voice|text)` (`_canned_audio_key`), `reply_en` stored directly on
   the turn.

## Already probed during planning (don't re-verify from scratch — build on this)

Direct calls to `OllamaAdapter.complete()` against the box's real
`qwen2.5:7b-instruct-q4_K_M` (not through the app, see `/tmp/qa058/probe_ollama*.py`
if still present, otherwise reproduce inline):
- Plain chat, `format: json`, and a simulated 16-user/assistant-turn history all
  returned clean text/valid JSON with **no** leaked `<|im_start|>`/`<|im_end|>` and
  no run-on into a fake next turn, across 5 samples. This is a *lead*, not proof —
  testers should sample more, and specifically through the real endpoints (history
  trim boundary, `format: json` + raw combo through `/vocab/forms` etc.), not just
  the bare adapter.
- A prompt-injection probe (user text containing literal `<|im_start|>system...`
  control tokens instructing the model to "become a pirate, speak English") **did**
  derail the model into English pirate-talk — but reproduces identically against
  `/api/chat` with `llama3.1` too (same injection, no raw mode, no ChatML
  client-rendering). **This is a pre-existing LLM-level prompt-injection
  susceptibility, not a regression from this PR — do not file it this round**;
  flagging it here only so no one re-discovers and miscredits it to raw ChatML.
- `warm()`'s guard is correct against the **real deployed** routing: production
  `app/config/ai_routing.yaml` has `examiner_roleplay.primary:
  "anthropic/claude-sonnet-4-6"` (hosted), so `warm()` returns immediately and never
  calls out on the live box. Confirmed by reading the config, not by a live call —
  worth a quick live confirmation (swap primary, see it skip) rather than trusting
  the read.
- Topics are **not** synced by `app.content.sync` — that's a separate entrypoint,
  `python -m app.speech.topics <level>`. Already wired into this round's app setup;
  mention to testers so they don't waste time debugging an empty `/speech/topics`.

## Hypotheses (ranked)

| # | area | hypothesis | how to probe | persona |
|---|------|------------|--------------|---------|
| H1 | ollama_adapter / raw+format:json | `format: json` combined with raw-mode `/api/generate` for qwen still constrains output to valid JSON matching the caller's schema, through the **real** endpoints (`vocab_extract`, `vocab_forms`, `vocab_examples`, `writing_feedback` via assessment submit) — not just the bare adapter. | curl: hit `/vocab/extra`, `/vocab/forms` (needs an existing personal card — add one via `/vocab/personal` first), `/vocab/examples`, and an assessment writing submit, 3–5 times each with varied input; confirm every response parses and matches the documented schema, no 500s, no raw-JSON-wrapped-in-prose. | edge-case-breaker |
| H2 | ollama_adapter / leakage at scale | Across ~15-20 live examiner/drill/grammar replies (not 5), none ever contain `<|im_start|>`, `<|im_end|>`, or visibly run on into a second fake turn ("Utilisateur:", "User:"), including right at the `max_tokens` cap (truncation mid-generation is OK; leaking the control token is not). | script (TestClient + fake STT/TTS + real router, see below) driving several `/speech/turn` calls with varied `max_tokens`-forcing content; also a couple of direct adapter calls with intentionally long expected replies and a low `max_tokens`. | edge-case-breaker |
| H3 | ollama_adapter / quality | Graded feedback / examiner replies read as on-topic, grammatically sound French, and appropriately leveled — not degraded by the raw-render switch. This is subjective; flag anything that reads obviously broken/truncated/wrong-language, not just "could be better." | read 5-10 real replies gathered for H1/H2 for fluency and relevance. | edge-case-breaker |
| H4 | speech history / session scoping | Starting a new `session_id` (new topic) never includes turns from a prior session/topic in the examiner's context — confirm via an actual LLM reply that only makes sense if it received (or didn't receive) the right history. | TestClient+fake-stt/tts+real-router script: seed turns under session A, start session B (new `session_id`), send a turn whose only sensible reply depends on NOT knowing session A's content; inspect the actual prompt sent (log/print `messages` before calling, or check `prompt_eval_count` sanity) and the reply. | returning-learner |
| H5 | speech history / trim boundary math | At exactly 16, 17, 24, and 25 persisted turns in one session, `_recent_history` returns the right turns in the right order (oldest→newest, no gaps/dupes) — confirm turn **count** and **content identity** (not just that *something* came back), both via direct DB+function call and via an end-to-end `/speech/turn` call whose reply must reference specific content from a turn that should/shouldn't still be in the window. | same TestClient script: seed `SpeechTurn` rows directly up to each count, call `_recent_history` (or go through `/speech/turn`) and assert on the exact set of turn ids returned at 16 vs 17 vs 24 vs 25. | returning-learner |
| H6 | speech history / opener turns in window | An opener turn (empty `transcript`, non-empty `reply_text`) inside the history window is fed back as a lone `assistant` message (no blank `user` message), at every position — start of window, middle, and right at a trim boundary. | script: seed an opener turn at turn 1, another at turn 9 (post-trim boundary at 17 turns), inspect the `Msg` list `_recent_history` builds for each. | returning-learner |
| H7 | /speech/opener / warm never blocks or bills | `/speech/opener`'s response time and body are unaffected by `warm()` (background, after commit); `warm()` is a no-op (no network call) when the profile's primary doesn't start with `ollama/` — confirm live by pointing the test router at both an ollama-primary profile and a hosted-primary profile and observing whether a call reaches Ollama. | script: call `/speech/opener` with the TestClient + real router (ollama primary) and measure response latency vs. a direct adapter call latency (opener response should return before/without waiting on the warm call); then swap the router's `examiner_roleplay.primary` to a non-"ollama/" string and confirm no request hits Ollama (e.g. point to a bogus unreachable host and confirm no error/delay). | returning-learner |
| H8 | authored openers / no-repeat + content | Across ~15-20 consecutive sessions on the same topic for one user, the exact same `fr` line is never served twice in a row (matches heard-last, not just "some" avoidance); `reply_en` on the turn is non-empty and matches the authored `en` for whichever `fr` was picked; the canned audio key is stable for the same `(voice, text)` and changes if either changes. | script: loop `/speech/opener` for the same `topic_id`/user ~15-20 times (authored-opener topic has only 5 variants, so repeats of non-last lines are expected and fine — only *immediate* repeat of the previous line is the bug), record each `reply_text`/`reply_en`/audio key; also authored-content spot check: read 8-10 yaml files across levels for French grammar correctness and role-appropriate register (vous vs tu). | edge-case-breaker |
| H9 | authored openers / topics without authored lines still work | Any topic (if one exists) with `openers: []` still falls back to the LLM `examiner.opener()` path cleanly — `/openapi.json`-level check plus a quick scan of all 29 yaml files confirms whether any topic *lacks* `openers` (if none do, this path is currently dead code in production and worth a one-line note, not a bug). | grep: `grep -L "^openers:" content/*/speaking/*.yaml` across all 29 files; if any found, drive `/speech/opener` for that topic_id and confirm LLM-opener behavior unchanged (framing, billing). | edge-case-breaker |

## Coverage gaps
- `/speech/turn/{turn_id}/translate` interaction with the new `reply_en` set by an
  *authored* opener (not the LLM-filled one from round 057's endpoint) — does
  calling `/translate` on an authored-opener turn correctly short-circuit (already
  has `reply_en`, no LLM call) or does it re-translate needlessly? Worth a quick
  check if time allows; not ranked above because it's a minor efficiency question,
  not a correctness one.
- No prior round has looked at `app/ai/router.py`'s new `primary()` method in
  isolation — confirm it doesn't raise on an unknown profile name (defensive, low
  risk, quick to check).

## Charters (per tester, with id blocks)

- `qa-tester` (persona **edge-case-breaker**, ids **830–839**): chase H1 (format:json
  through real non-speech endpoints), H2/H3 jointly with the returning-learner's
  script output (read, don't re-run, if the other tester already gathered samples —
  coordinate by checking `qa/issues/` and `/tmp/qa058/` for the other tester's
  artifacts first), H8's content-quality half (yaml grammar/register spot check —
  read files directly, no need to hit the app for this half), and H9. App base
  `http://127.0.0.1:9200`; invite codes `friend-001`/`friend-002`; sign up with an
  `@qa.test` email. For H1's `/vocab/forms` you'll need an existing personal card —
  `POST /vocab/personal/from-word` or `/vocab/personal` first to get a `card_key`.
  Do not hammer the box — a few varied calls per endpoint is enough, this is a
  shared 1070, not a load test.
- `qa-tester` (persona **returning-learner**, ids **840–849**): chase H2 (leakage at
  scale), H4 (session scoping), H5 (trim boundary math), H6 (opener-turn-in-window),
  H7 (warm never blocks/bills), and H8's repeat-tracking half. This charter needs an
  **in-process script**, not curl: use `fastapi.testclient.TestClient` against
  `app.main.create_app()` built with the SAME env as the running server (real
  `AIRouter` pointed at `http://10.0.0.54:11434`, model `qwen2.5:7b-instruct-q4_K_M`,
  `AI_ROUTING_PATH=app/config/ai_routing.ollama.yaml`), then monkeypatch only
  `app.state.stt`/`app.state.tts` to fakes (see `tests/test_speech.py` lines ~1-170
  for `FakeSTT`/`FakeTTS`/dependency-override patterns — reuse the shape, but swap
  in the REAL router instead of `FakeRouter`) so `/speech/opener` and `/speech/turn`
  don't 503 locally. Use a throwaway sqlite file under `/tmp/qa058/`, not the running
  server's DB (avoid colliding with the other tester or corrupting shared state);
  write the script under `/tmp/qa058/` and delete it when done (or leave it, it's
  scratch). Each real LLM call costs a few seconds on the box's GPU — budget for
  ~15-20 opener calls (H8) + ~25 turn calls (H2/H4/H5/H6) total, don't loop into the
  hundreds.
- No `qa-browser-tester` this round: every `/speech/*` endpoint 503s in the real
  browser locally (no STT/TTS backend configured on the Mac — this is the known,
  expected local-environment gap, not something the browser can exercise around).
  All of this round's risk is backend logic reachable only via the in-process
  TestClient trick or direct non-speech HTTP endpoints, both covered above.

## Don't re-file (already settled)
- `/speech/turn`, `/speech/opener` returning a clean `503` on a machine with no
  STT/TTS backend — expected, not a defect (only file if the *handling* is poor).
- Issue 820 (dead "Show English" button on empty `reply_en`, round 057) — different
  code path (LLM-translated subtitle, not an authored opener's `reply_en`, which is
  always non-empty by construction) but keep it in mind for H9/translate-gap check.
- The prompt-injection-via-literal-ChatML-tokens lead above — pre-existing, not a
  regression, do not file.
- All content/vocab issues below 810 (verb accept-list bugs, etc.) — unrelated area.

## Outcome (round 058)

- **H1** (format:json + raw-mode `/api/generate` through real endpoints) — **refuted**
  (area sound): `/vocab/forms`, `/vocab/extra`, `/vocab/examples`, and
  `/assessment/.../submit` (writing_feedback) all produced valid, schema-matching
  JSON across ~20 live LLM-backed calls; no 500s, no prose-wrapped/truncated JSON.
- **H2** (raw-ChatML leakage at scale) — **refuted**: ~18+ real completions through
  `_recent_history`/`SpeakingExaminer`, including forced low-`max_tokens` truncation
  and a cap-length generation, never leaked `<|im_start|>`/`<|im_end|>` or ran on
  into a fake turn.
- **H3** (reply/feedback quality) — **confirmed** real content-quality defects, but
  **not caused by this PR** → issues 830 (vocab/forms adjective agreement/elision
  errors), 831 (writing_feedback hallucinates corrections on already-correct
  French), 832 (from-word IPA returns English phonetics for French cognates). All
  three reproduced identically under the pre-PR `/api/chat` rendering in direct
  A/B tests against the real model, and 832 traces to the Piper-IPA-override path
  (`app/content/lookup.py`, from PR #119) being unreachable with no TTS backend
  locally — none touch this PR's diff. **Deferred**, upheld by qa-critic.
- **H4** (session scoping) — **refuted**: a fresh `session_id` returns `[]` from
  `_recent_history`; a live reply confirmed no cross-session bleed.
- **H5** (trim boundary math at 16/17/24/25) — **refuted**: exact kept turn-id
  range/order matches the `_HISTORY_MAX_TURNS=16`/`_HISTORY_TRIM_BLOCK=8` formula
  at every boundary tested.
- **H6** (opener turns inside the history window) — **refuted**: emits a lone
  `assistant` message with no paired blank `user` message, at window position 1
  and at a post-trim boundary position.
- **H7** (`warm()` never blocks or bills) — **refuted**: `/speech/opener` returns
  in ~0.3 s including the background warm call; `warm()` makes zero network calls
  when the profile's primary isn't `ollama/`-prefixed (confirmed against both the
  real deployed routing config and a stubbed non-ollama primary), and a simulated
  connection failure inside `warm()` never escapes to the caller.
- **H8** (no-repeat openers + content quality) — **refuted** on the mechanism (18
  consecutive opener calls for one topic, zero immediate repeats, `reply_en`
  always non-empty and matching, stable audio key) and **refuted** on content
  quality for the 19 topic files sampled across both testers (grammatically
  correct French, correct vous/tu register per role).
- **H9** (topics without authored openers) — **refuted**/moot: all 29 topic files
  have `openers:`; the LLM-fallback path is unexercised in production content
  (coverage note only, not a defect).
- **Coverage gaps noted in the plan** (translate-endpoint short-circuit on
  authored `reply_en`, `AIRouter.primary()` on an unknown profile) — **untested**
  this round; low risk, carry forward if a future round touches that code.

### Issues filed: 830, 831, 832 — all `deferred` (qa-pm, upheld by qa-critic).
No issue reached `validated`, so `dev-fixer` was not run this round (success, not
a gap — see rule in the top-level instructions).

### Verdict: **SHIP.**
Every hypothesis that touches PR #120's actual diff (raw-ChatML adapter rendering,
whole-session history trim, opener warm-up, authored topic openers/no-repeat
logic) was refuted — the changed code behaves as designed, with no regression
found. The three filed issues are real but pre-existing LLM content-quality bugs
in `vocab_forms`/`writing_feedback`/`from-word` IPA lookup, independently
reproduced under the OLD rendering path too, and are recommended as a follow-up
round's focus rather than a blocker for this PR.

