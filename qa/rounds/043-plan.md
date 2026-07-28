# QA round 043 — plan

- date: 2026-07-27
- app under test: backend + built SPA, single-origin at `127.0.0.1:9000` (main,
  `54bff7d`) for local work; self-host box (`ssh rohith@10.0.0.54`, docker
  `multilingual-app-1`, `127.0.0.1:9000` on the box) for the real speech loop.
- scope: **post-merge hardening over everything that landed this session** —
  weighted toward (a) the speech stack standing up for the first time
  (`feat/speech-stack-deploy` + the H9 input-hardening follow-up, #53/#56) and
  (b) the nav redesign (#52 + its round-042 follow-ups). Round 041's speech plan
  was written but **never executed** (confirmed: no filed issue touches
  speech/whisper/piper/stt/tts) — the speaking loop has genuinely never been
  QA'd until this round.

## Change surface (highest risk first)
1. `app/speech/api.py`, `app/speech/examiner.py`, `app/ai/adapters/faster_whisper_adapter.py`,
   `app/ai/errors.py` — new H9 input hardening (empty→400, oversized→413,
   undecodable→422 `TranscriptionError`, silence→422 no-bill, `vad_filter=True`).
   Well covered by **fakes** in `tests/test_speech.py` and by **direct adapter**
   calls in `tests/test_speech_integration.py` (gated, box-only) — but neither
   exercises the *real* HTTP endpoint against the *real* whisper/piper stack
   together. That seam (api.py's exception→status mapping wired to the actual
   `FasterWhisperAdapter`, on the actual box) has zero coverage. Highest-risk gap.
2. Docker image / compose wiring for STT+TTS (`docker-compose.yml`, box env:
   `STT_BACKEND=faster-whisper`, `WHISPER_MODEL=small`, `TTS_BACKEND=piper`,
   `PIPER_VOICE=/app/voices/fr_FR-siwis-medium.onnx`) — first time this config
   has ever been exercised end-to-end; a mis-wired `app.state.stt/.tts` would
   show as an unexpected 503 even though the box is "configured."
3. `web/src/App.tsx`, `web/src/screens/Path.tsx`, `web/src/styles.css` (nav
   redesign) — already round-042-tested (H1–H5); two issues filed (470 rejected,
   490 validated+fixed, both `done`/closed). This round re-checks reachability
   is still intact after the 490 fix landed (regression, not a fresh hypothesis
   hunt) and covers what 042 explicitly didn't: the Speaking screen's *local*
   503 experience (mic UX only reachable through the same slimmed nav).
4. `1971333 fix(web): responsive nav for phones` — landed **after** round 042
   closed; the mobile-nav CSS was touched again post-fix. No issue history at
   all on this specific commit — worth a fast confirm it didn't reopen H3.

## Hypotheses (ranked)

| # | area | hypothesis | how to probe | persona |
|---|------|------------|--------------|---------|
| H1 | speech/HTTP+real-model | The real HTTP path (multipart upload → `api.py` → real `FasterWhisperAdapter`/`PiperAdapter` → real Ollama examiner) behaves per the H9 contract end-to-end: `empty.bin`→400, oversized (>10MB)→413, `not-audio.bin`→422, `silence.wav`→422 with **no** `SpeechTurn` row persisted. Unit tests fake the STT; this is the first check with the real model wired through the real endpoint. | On the box, via ssh+curl against `127.0.0.1:9000/speech/turn` with a disposable test account + the committed `qa/fixtures/speech/*` fixtures, confirm each status code and (for silence) that `/speech/history` doesn't grow. | edge-case-breaker |
| H2 | speech/happy path | A real spoken turn works end-to-end: French audio in → non-empty, faithful transcript out (R1, not "corrected" — `graded-a1-fr.wav` is known-clean per the fixtures README) → non-empty examiner `reply_text` → a fetchable `reply_audio_url` (real Piper WAV, `RIFF` header). First-ever real exercise of this path. | One `/speech/turn` POST with `graded-a1-fr.wav` on the box; assert transcript content, `reply_text` non-empty, `GET reply_audio_url` returns 200 `audio/wav` with nonzero frames. | edge-case-breaker |
| H3 | speech/IDOR | `/speech/audio/{turn_id}` and `/speech/history` are per-user even against the real deployed DB (round-041 planned this, never ran; unit-tested with fakes in `test_speech.py` only for history, not cross-user audio access with a real turn). | Two disposable accounts on the box; account A creates a turn (reuse H2's), account B requests A's `turn_id` audio → expect 404; B's `/speech/history` must not include A's turn. | edge-case-breaker |
| H4 | speech/integration suite | The gated real-adapter suite (`tests/test_speech_integration.py`) still passes against the *current* deployed image/models — it was last known-run pre-#56; the H9 hardening changed `faster_whisper_adapter.py` (added `vad_filter=True`) and this suite has an explicit silence-transcript assertion that could regress. | `docker cp` `tests/` + `qa/fixtures/` into `multilingual-app-1` (recreated since last copy — confirmed missing), run `RUN_SPEECH_INTEGRATION=1 pytest tests/test_speech_integration.py -q` inside the container, then delete the copied dirs. | edge-case-breaker |
| H5 | speech/local contract | With `STT_BACKEND=disabled` (the local default, confirmed live: `POST /speech/turn` → `401` unauth / would be `503` once past auth), the endpoint fails cleanly and predictably — this is the shape most learners hit in dev/CI and needs its own confirmation independent of the box. | Locally: hit `/speech/turn` unauthenticated (expect 401, not 500), then authenticated with `stt=None` (expect 503 "speech is not configured"), and `/speech/audio/{id}` / `/speech/history` for a nonexistent id/empty history (expect clean 404 / empty list, no 500). | edge-case-breaker |
| H6 | nav/regression | The 8 hub-card destinations (Vocab, Grammar, Drill, Read & Listen, Write, Speak, Weak spots, Readiness) are still all reachable and console-clean after the 490 heading fix and the later `1971333` phone-nav change — a quick regression sweep, not a fresh hunt (round 042 already did the deep pass). | Click through all 8 cards from Path; confirm the new "Practice & tools" `<h2>` renders visibly (490's fix); confirm the 4-item topbar (Learn/Review/Mock/Group) still highlights correctly. | returning-learner |
| H7 | nav/mobile regression | `1971333 fix(web): responsive nav for phones` landed after round 042 closed with no dedicated issue — re-check 375px/320px viewports (round 042's H3 territory) for new overflow/clipping introduced by this later fix, and specifically look at the Speaking screen's local "not configured" messaging at narrow widths (never viewport-tested before, since Speaking was previously always 503). | Resize to 375×812 and 320×568 on Path, one hub destination, and `/speaking` (503 copy state); screenshot; look for overflow, clipped text, or a broken layout the 490/1971333 fixes might have introduced. | edge-case-breaker |
| H8 | web/speech UX (local) | The Speaking screen's local "not available" state (STT disabled) is legible and doesn't look broken — a learner navigating there via the new hub card shouldn't hit a dead/blank screen or console error just because speech is off in this environment. | From Path, click the "Speak" hub card → `/speaking`; confirm a clear message (not a blank pane or unhandled error), no console errors, and that mic-permission UI doesn't appear misleadingly if the backend already reports unavailable. | absolute-beginner |

## Coverage gaps
- `/speech/turn`, `/speech/audio/{id}`, `/speech/history` have **zero** issue
  history and (per H1–H4) have never been exercised end-to-end with real
  models — the single biggest blind spot this round targets.
- Round 041's H2 (level gating on speech `mode`), H7 (scope/pronunciation
  honesty), H10 (multi-turn history continuity across mode switches), H11
  (latency/concurrency under real models) remain **entirely untested** — out of
  scope for this round too (see Don't re-file / Explicitly untested below):
  budget-exhaustion and concurrency probes are expensive/risky to run against a
  shared production box and are deliberately excluded here; flag for a future
  round if the box gets a dedicated test slot.
- No prior issue ever touched the Speaking screen's UI at all (local 503 state
  included) — `web/src/screens/Speaking.tsx` is otherwise only covered by round
  041's unexecuted plan.

## Charters (per tester, with id blocks)
- **`qa-tester` as `edge-case-breaker` — box speech HTTP charter** (ids
  500–509): H1, H2, H3, H4. Runs against the **production self-host box**
  (`ssh rohith@10.0.0.54`) — read-mostly, minimal footprint:
  - Use `ssh rohith@10.0.0.54 "docker exec multilingual-app-1 ..."` and
    `ssh rohith@10.0.0.54 "curl -s http://127.0.0.1:9000/..."` (the box only
    binds `9000` to its own loopback — must run curl *inside* the ssh session
    or via `docker exec`, not from this machine directly).
  - Create **exactly one or two** disposable test accounts via `/auth/signup`
    (existing invite codes are visible in the container env — use one, e.g.
    `friend-002` — do not reuse the operator's real account). Delete/ignore
    after — no cleanup mechanism exists, so keep it to the minimum accounts
    needed for H3's two-user check.
  - `docker cp` **both** `tests/test_speech_integration.py` (and the rest of
    `tests/` it imports from, if any) and `qa/fixtures/speech/` into
    `multilingual-app-1:/app/` before running H4's suite; **`docker exec` the
    cleanup afterward** (`rm -rf` the copied paths) — the prod image doesn't
    ship these and shouldn't gain them permanently.
  - Budget note: `SPEAKING_DAILY_TOKEN_BUDGET=60000` on the box — H1/H2/H3
    together are a handful of turns and won't come close; don't add extra
    speaking calls beyond what H1–H3 need.
  - **Do not** touch `multilingual-ollama-1` directly, restart any container,
    or run anything beyond the commands above. This is a shared production
    box that also runs unrelated trading containers.
- **`qa-tester` as `edge-case-breaker` — local speech contract charter** (ids
  510–519): H5. Runs against local `127.0.0.1:9000` (STT/TTS disabled here by
  design — confirmed live: unauth → 401). Pure curl, no box access.
- **`qa-browser-tester` as `returning-learner`** (ids 520–529): H6. Local
  `127.0.0.1:9000` (already serving the current build) or spin its own per the
  standard runbook — regression sweep only, light touch.
- **`qa-browser-tester` as `edge-case-breaker`** (ids 530–539): H7. Viewport
  regression at 375px/320px, including the never-before-tested `/speaking`
  503 state at narrow width.
- **`qa-browser-tester` as `absolute-beginner`** (ids 540–549): H8. First-look
  at the local Speaking screen's unavailable state via the hub card.

## Don't re-file (already settled)
- 470 (tool-grid `.active` highlight unreachable) — **rejected** by critic:
  provably behavior-invariant dead code, no learner-facing gap. Don't re-file.
- 490 (home hub grid missing visible heading) — **done**, fixed with a visible
  `<h2 className="section-label">Practice &amp; tools</h2>`. This round's H6
  should *confirm* the fix renders, not re-litigate whether it was needed.
- 466 (invalid/expired token → broken shell instead of redirect to login) —
  **done**, pre-existing and unrelated to this session's changes; don't re-file
  if seen again incidentally, but do flag if the *speech* auth path (401 on
  `/speech/turn`) somehow triggers the same broken-shell symptom (new surface).
- `NavLink` string-className losing the `active` class — refuted by source
  read in round 042; don't re-hunt this specific mechanism.
- Pronunciation/accent scoring absent — by design (R2, round 041 pre-check);
  only file if the app *claims* to score it.
- `lang="fr"` hard-coded on speech — deliberate; only file if it crashes on
  non-French input (H1/H9 territory), not as a feature request.
- Drill/Writing 503 with no LLM provider — expected local limitation, not in
  scope.

## Explicitly untested this round (say so in the report, don't guess)
- Speech budget exhaustion (round 041 H3), level gating on `mode` (H2), scope
  honesty under real examiner prompts (H7), multi-turn history continuity
  (H10), latency/concurrency (H11), and the full in-browser mic→record→
  playback loop (H12, round 041) against the real box — all deliberately
  excluded as too expensive/risky for a shared production box in one round.
  Note each as **untested** (not refuted) in the final report.

<!-- After the round, the planner notes each hypothesis: confirmed (→ issue NNN) /
     refuted (area sound) / untested. -->
