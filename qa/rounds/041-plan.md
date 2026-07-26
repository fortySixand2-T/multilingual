# QA round 041 — plan

- date: 2026-07-25
- app under test: backend :9000 / SPA :5173
- scope: **the speech / speaking module, end-to-end, with real STT+TTS+LLM providers loaded.** Every prior round treated "Speaking 503" as expected and never exercised the loop. This round flips that: the goal is to actually run record → transcribe → examiner → TTS reply and find where it breaks.

## Precondition (this round cannot run in the default config)
The loop is disabled out of the box (`app/config/settings.py:42-45`: `stt_backend`/`tts_backend = "disabled"`). Before testing, on a box that can host the models (the GTX 1070 self-host):
- `STT_BACKEND=faster-whisper`, `WHISPER_MODEL=` a model the 1070 can hold — **`large-v3` is the default and likely OOMs 8 GB; start with `small` or `medium`**.
- `TTS_BACKEND=piper`, `PIPER_VOICE=` an actual `.onnx` voice path (default is `""` — see H8).
- An LLM provider wired for the `examiner_roleplay` profile (Ollama).
- Confirm `GET /speech/turn` deps resolve: `request.app.state.stt` / `.tts` are non-None (`app/speech/api.py:76-79`).

If models can't be loaded, **stop and report** — do not "pass" the round by confirming 503s.

## Change surface (highest risk first)
Not a diff-driven round — the module is old code that has simply never been exercised. Risk concentrates where the module meets the *outside world*:
- `app/speech/api.py` — `/turn` (multipart audio in), `/audio/{turn_id}`, `/history`.
- `app/speech/examiner.py` — STT → LLM → TTS orchestration, budget gate, R1/R2/R10 handling.
- `app/ai/adapters/faster_whisper_adapter.py`, `app/ai/adapters/piper_adapter.py` — first real use of both adapters.
- `web/src/screens/Speaking.tsx` — `MediaRecorder` capture, blob upload, playback, error states.

## Hypotheses (ranked)

| # | area | hypothesis | how to probe | persona |
|---|------|------------|--------------|---------|
| H1 | audio format | **The browser sends `audio/webm` (Opus); Whisper may not decode it.** `Speaking.tsx:52` uploads `new Blob(chunks, {type: mr.mimeType \|\| "audio/webm"})`; `examiner.py:80` calls `stt.transcribe(audio=bytes, lang="fr")`. If faster-whisper needs WAV/PCM or a working ffmpeg on PATH, real mic input fails while a WAV fixture "works" — a false green. | POST `/speech/turn` with (a) a real Chrome `.webm` capture and (b) a `.wav` of the same speech; compare. Then do the full mic flow in-browser. | edge-case-breaker |
| H2 | level gating | **The plan promises "level-gated (drills → conversation → examiner)" but the API enforces no gate.** `mode` is a free `Form` field (`api.py:69`) and the UI offers both modes to everyone (`Speaking.tsx:71-73`) regardless of CEFR level. An A1 user can invoke full examiner mode. | As an A1 account, POST `mode=examiner`; confirm it runs. Decide: is the plan's gating a real AC that's missing, or was it descoped? | absolute-beginner |
| H3 | budget (R7) | **Daily token budget behavior at/over the edge.** Gate is `used >= daily_budget` checked *before* the turn (`examiner.py:76-78`), default 60000. A single turn can overshoot; the *next* is blocked with `over_budget` and no `SpeechTurn` saved (`api.py:99-100`). | Drive usage near 60000, confirm the next turn returns `{over_budget:true}`, no row added, LLM/TTS not charged again. Confirm isolation: user B unaffected; other features' budgets untouched. | exam-crammer |
| H4 | privacy (R10) | **Raw audio must never be persisted.** Claim: only transcript + reply stored; reply audio saved as `speech/{id}.wav`, raw upload discarded (`api.py:81`, `examiner.py:83`). | After several turns: grep storage + DB for the uploaded bytes; confirm only synthesized reply audio exists, `SpeechTurn` has no audio column for input, and nothing is written to disk/tmp for the raw upload. | edge-case-breaker |
| H5 | audio auth (IDOR) | **`/speech/audio/{turn_id}` and `/history` must be per-user.** `api.py:140` returns 404 when `turn.user_id != user.id`. | As user B, request user A's `turn_id` audio → expect 404 (not the file, not 403-leak). Confirm `/history` only returns caller's turns. Try unauth'd and non-existent ids. | edge-case-breaker |
| H6 | STT honesty (R1) | **Learner must see the real transcript, errors and all** — Whisper tends to "auto-correct" beginner French into fluent French, hiding mistakes. | Feed deliberately broken/mispronounced French audio; check the returned `transcript` reflects what was *said*, not an idealized version; confirm the UI shows it (`Speaking.tsx` renders `transcript`). Judge severity of any over-correction. | absolute-beginner |
| H7 | scope (R2) | **No pronunciation/accent claims.** Model sees text only (`examiner.py:86`). | Ask (in French) "how was my accent/pronunciation?"; confirm the examiner doesn't fabricate phoneme/accent scores and stays on content/range/coherence/fluency. Review `prompts/examiner.md` + `conversation.md` for over-promising. | exam-crammer |
| H8 | TTS config gap | **`tts_backend=piper` with `piper_voice=""` (the default) likely errors at synth.** `factory.py:31` builds `PiperAdapter(voice_model="")`; `examiner.py:96` synthesizes after the LLM has already run + been charged → a 500 that still burned tokens, or a turn saved with no audio. | Enable TTS with an empty/invalid voice path; observe failure mode. Is it a clear startup error, or a late per-turn 500 after cost? | edge-case-breaker |
| H9 | bad input | **Garbage / empty / wrong-type uploads.** 0-byte file, non-audio bytes, huge file, English speech (lang is hard-coded `"fr"`, `examiner.py:81`), silence. | POST each; expect graceful 4xx or empty-transcript handling, not a 500 or a hung worker. Confirm an empty transcript doesn't send a blank turn to the LLM and bill for it. | edge-case-breaker |
| H10 | history continuity | **Last 3 turns are replayed as context (`api.py:40`, `_recent_history`), mixing modes.** Switching examiner↔conversation mid-session feeds prior-mode turns into the new prompt. | Alternate modes across turns; check the examiner reply stays coherent and history/audio playback in the UI matches the turn it belongs to. | returning-learner |
| H11 | latency (R9) | **Round-trip feel + concurrency.** `large-v3` on a 1070, plus LLM, plus Piper, serialized through the threadpool (`anyio.to_thread`). | Time a cold turn and a warm turn; fire 2–3 concurrent turns; watch for OOM, event-loop starvation, or timeouts. Note p50/p95. | exam-crammer |
| H12 | mic UX | **Browser capture + permission + playback states.** `Speaking.tsx:46` `getUserMedia`, `:52` blob upload, `:34-36` 503 copy, `:28` over-budget copy, reply `<audio>` playback. | In-browser: deny mic → clear error; record/stop; play the examiner's TTS reply; verify Safari/iOS `audio/mp4` mimeType path (feeds H1). | absolute-beginner |

## Coverage gaps
- `/speech/turn`, `/speech/audio/{id}`, `/speech/history` have **zero** issue history — the loop has never run under test.
- The `faster_whisper_adapter` and `piper_adapter` have never been exercised against real bytes in a QA round.
- `Speaking.tsx` (mic capture/playback) is part of the acknowledged SPA test gap (`qa/FRONTEND_TEST_GAP.md`).

## Charters (per tester, with id blocks)
Split by transport, because half of this is browser-only:
- **`qa-tester` — HTTP loop** (ids 410–419): H2, H3, H4, H5, H8, H9. Hit `/speech/turn` directly with prepared fixture audio (a `.wav` and a real Chrome `.webm` of the same French utterance — commit these under `qa/fixtures/speech/`). curl-drivable; no mic.
- **`qa-browser-tester` — real mic UI** (ids 420–429): H1, H6, H12, and the UI half of H10. Drive `Speaking.tsx` through Claude-in-Chrome: grant mic, record French, stop, read transcript + play reply.
- **`exam-crammer` charter** (ids 430–439): H7 (scope honesty), H11 (latency/concurrency), examiner-mode realism.
- **`returning-learner` charter** (ids 440–449): H10 (multi-turn history continuity + playback correctness).

## Don't re-file (already settled)
- **Speaking 503 with no provider — expected** *in the default config only.* For THIS round, a 503 once models are supposedly enabled is a **real bug** (mis-wired `app.state.stt/tts`), not the known limitation.
- Pronunciation/accent scoring absent — **by design** (R2). Don't file "add pronunciation scoring"; only file if the app *claims* to do it.
- `lang="fr"` hard-coded — known/deliberate (French-only product); file only if it causes a crash on non-French input (that's H9), not as a feature request.

<!-- After the round, the planner notes each hypothesis: confirmed (→ issue NNN) /
     refuted (area sound) / untested (models couldn't be loaded — say so explicitly). -->
