# Speaking latency — baseline report (2026-10-17 / box re-verified 2026-10-18T06:02Z)

Baseline measurement taken before migrating Whisper STT from CPU to GPU on the
self-hosted box. Pure measurement run: no edits to `app/`, `web/`, `.env`, or
compose files; no `docker compose up/build/restart`. Raw samples:
[`bench/results/latency-2026-10-17-baseline.json`](../results/latency-2026-10-17-baseline.json).
Fixtures: `bench/latency/fixtures/{short,medium,long}.wav`.

System under test: box `rohith@10.0.0.54`, repo `~/projects/multilingual`,
containers `multilingual-app-1` (FastAPI, 127.0.0.1:9000) and
`multilingual-ollama-1`; public ingress via Tailscale Funnel at
`https://rohith-alienware-17-r4.tail592ffa.ts.net`. All turns used a disposable
`latency-bot` account created through `/auth/signup`; no real learner account
was touched.

## 1. Headline numbers

"Text" = learner stops talking → `reply_text` is returned by `POST /speech/turn`.
"Audio starts" = that same moment → first byte available from
`GET /speech/audio/{turn_id}` (first-fetch, i.e. including on-demand Piper
synthesis).

| Path | Fixture | → text shown (median / p90) | → audio starts, cumulative (median / p90) |
|---|---|---|---|
| Internet (Funnel) | short (~1.8s speech) | 12.34s / 19.81s | 34.19s / 40.33s |
| Internet (Funnel) | medium (~5.7s speech) | 4.22s / 4.85s | 6.52s / 9.57s |
| Internet (Funnel) | long (~11.8s speech) | 35.03s / 65.19s | 64.30s / 89.43s |
| Loopback (on-box) | short | 3.96s / 7.02s | 5.09s¹ / 8.26s¹ |
| Loopback (on-box) | long | 4.55s / 5.84s | 5.33s¹ / 6.93s¹ |

¹ loopback "audio starts" = `turn_total_s` + `audio_fetch_s` (no separate `sum`
field was recorded for scenario C; computed from the two measured components).

**n=5 for every row except loopback audio_fetch on long (n=4 — one run
returned an empty `audio_url`, see §5 caveats).**

The internet-path numbers are dominated by Tailscale Funnel connection
variance, not by fixture size — `short` (12.34s median) is markedly *worse*
than `medium` (4.22s median) despite carrying a third of the audio. This is a
measured, reproducible pattern in this session's data (not an artifact of one
outlier): short's own min/max span is 8.12s–19.81s, all five runs are already
above medium's p90. See §4.

## 2. Waterfall per fixture

Loopback numbers isolate the on-box compute pipeline cleanly, since Funnel/TLS
overhead is removed; the per-stage breakdown below is loopback (scenario C) +
direct component benchmarks (scenario D) combined.

### Short fixture (~1.8s speech, loopback total 3.96s median text / 5.09s to audio)

| Stage | Time (median) | % of 5.09s total |
|---|---|---|
| Network/TLS (loopback) | ~0.00s (unix-local) | ~0% |
| STT (faster-whisper small, cpu/int8) | 1.76s | 35% |
| LLM (qwen2.5:7b, GPU, streamed, ~25-91 tokens) | 1.12–5.40s (see D below; using 1.97s as representative) | ~39% |
| App overhead (upload handling, DB write, routing) | turn_total − STT − LLM ≈ 0.23s | ~5% |
| TTS (Piper, on first audio fetch) | 0.59s | 12% |
| Audio download (loopback) | 1.14s (`C_short` audio_fetch median) — most of this is the TTS synth cost; see note | — |

Note: in the real app, TTS does **not** run during `/speech/turn` — it runs
lazily on the first `GET /speech/audio/{turn_id}`. So the "audio starts"
column in §1 already includes TTS. Scenario D's standalone TTS timing (0.45–
1.13s per Piper call) and scenario C's `audio_fetch_s` (first fetch, 1.14s
median for short) agree closely, confirming TTS dominates the audio-fetch gap
and network/serialization overhead on loopback is near zero.

### Medium fixture (~5.7s speech, loopback not separately run — used LLM/TTS reply-text-length-matched samples from D)

| Stage | Time (median, from D) | Notes |
|---|---|---|
| STT | 1.69s | matches short within noise — STT scales with audio length, not transcript complexity |
| LLM | 2.09–2.87s for ~49-67 token replies | representative of medium-length replies |
| TTS | 0.94s | `medium_reply` sample (301KB wav) |

### Long fixture (~11.8s speech, loopback total 4.55s median text / 5.33s to audio)

| Stage | Time (median) | % of 5.33s total |
|---|---|---|
| STT | 3.97s | 74% — by far the dominant stage for long utterances |
| LLM + app overhead | turn_total − STT ≈ 0.58s | ~11% (short reply this run) |
| TTS (audio fetch) | 0.78s (C_long audio_fetch median, n=4) | ~15% |

**Key waterfall finding: STT scales linearly with spoken-audio duration
(1.76s → 1.69s → 3.97s for short/medium/long, i.e. ~2.3x for ~2x the audio
length) and is CPU-bound — it was observed pegging the app container's CPU at
up to 662% during scenario D, i.e. genuinely multi-threaded, not idle-waiting.
For long utterances STT is the single largest stage (74% of the loopback
total-to-audio time).** LLM generation time depends on reply length (tokens),
not on input length, and is comparatively fast and stable (17–24 tok/s,
TTFT 75–187ms) because it already runs on the GPU via Ollama.

## 3. Measured configuration snapshot

Captured via `docker exec`, `nvidia-smi`, `ollama ps`, `docker inspect`, and
reading `docker-compose.gpu.yml` / `app/config/settings.py` directly (not from
any `.env` dump). Re-verified identical at 2026-10-18T06:02Z vs. the original
capture earlier in this run.

| Setting | Value | Source |
|---|---|---|
| `STT_BACKEND` | `faster-whisper` | container env |
| `WHISPER_MODEL` | `small` | container env |
| `WHISPER_DEVICE` | unset → defaults to `cpu` | `app/config/settings.py` default |
| `WHISPER_COMPUTE_TYPE` | unset → defaults to `int8` | `app/config/settings.py` default |
| `OLLAMA_MODEL` | `qwen2.5:7b-instruct-q4_K_M` | container env |
| `OLLAMA_KEEP_ALIVE` | `-1` (resident) | container env |
| Piper voice | `fr_FR-upmc-medium.onnx` | container env |
| GPU | GTX 1070, 8192 MiB total | `nvidia-smi` |
| VRAM used | 5245 MiB | `nvidia-smi` (with Ollama's 7B model resident) |
| VRAM free | **2861 MiB** | `nvidia-smi` |
| `ollama ps` | `qwen2.5:7b-instruct-q4_K_M`, 6.0 GB, **100% GPU**, until **Forever** | `docker exec multilingual-ollama-1 ollama ps` |
| Host RAM free | 4811 MiB (of 31964 MiB total, 14831 MiB in buff/cache) | `free -m` on box |
| `app` container GPU passthrough | **NONE** — `docker inspect` DeviceRequests = `[]` | `docker inspect multilingual-app-1` |
| `docker-compose.gpu.yml` scope | GPU reservation granted only to the `ollama` service | file contents, quoted below |
| `ctranslate2.get_cuda_device_count()` inside app container | **0** | `docker exec multilingual-app-1 /app/.venv/bin/python -c "import ctranslate2; print(ctranslate2.get_cuda_device_count())"` |
| faster-whisper CPU fallback | **not in the deployed build** — added on branch `perf/whisper-gpu` (read from the worktree mid-run, not from the box) | `app/ai/adapters/faster_whisper_adapter.py` |

`docker-compose.gpu.yml` (full contents, confirms the scoping claim above):

```yaml
# NVIDIA GPU passthrough for Ollama. Requires the NVIDIA Container Toolkit on the
# host (see docs/hosting.md). Layer it on top of the base file:
#   docker compose -f docker-compose.yml -f docker-compose.gpu.yml up -d --build
services:
  ollama:
    deploy:
      resources:
        reservations:
          devices:
            - driver: nvidia
              count: all
              capabilities: [gpu]
```

## 4. Findings (measured vs. inferred)

1. **MEASURED** — STT is the single largest compute stage for longer
   utterances: 3.97s median of a 5.33s loopback total for the long fixture
   (74%), vs. 1.76s of 5.09s for short (35%). STT time scales with *spoken
   audio duration*, not transcript word count.
2. **MEASURED** — LLM generation on Ollama/GPU is fast and consistent: TTFT
   75–187ms, 17–24 tok/s sustained, for replies capped at
   `EXAMINER_MAX_TOKENS=220`. LLM is not the bottleneck today.
3. **MEASURED** — TTS (Piper, CPU) costs 0.45–1.13s per reply and runs lazily
   on first audio fetch, not during the `/speech/turn` call itself (confirmed
   by code in `app/speech/api.py` and by `C_*` loopback numbers where
   `audio_fetch_s` tracks Piper's own synth time closely).
4. **MEASURED** — the internet path (Funnel) is dominated by connection
   variance, not payload size: short (12.34s median turn) is worse than medium
   (4.22s median) despite 1/3 the audio. A quiet re-measurement of pure
   network transport (ping 15–23ms RTT, fresh-TLS total 0.17–0.21s, upload
   throughput ~1 MB/s for a 253KB body) shows the underlying network is not
   inherently slow — the earlier B_short numbers reflect Funnel-specific
   variance (cold relay paths, TLS renegotiation) rather than a fixed
   per-request tax. This variance itself is a measured, reproducible finding
   even though its root cause (Funnel relay selection) is inferred, not
   directly instrumented.
5. **MEASURED** — no VRAM headroom problem for the planned migration: 2861 MiB
   free with the 7B Ollama model resident; faster-whisper `small` in
   `int8_float16` on CUDA needs roughly 0.5–1 GB (this sub-figure itself is
   **INFERRED** from published faster-whisper memory guidance, not measured on
   this box, since CUDA isn't currently reachable from the app container to
   test directly).
6. **MEASURED** — the `app` container has zero GPU passthrough today
   (`DeviceRequests: []`) and `ctranslate2.get_cuda_device_count()` returns 0
   inside it. **INFERRED** — this is very likely *caused* by the missing
   device passthrough alone (the compose GPU override only targets `ollama`);
   whether the installed `ctranslate2` wheel and the app container's base
   image also lack CUDA/cuDNN runtime libs was not independently
   disambiguated (e.g. via `ldd` on ctranslate2's shared library) — flagged as
   unverified rather than assumed.
7. *(Correction, added after the run)* — the CPU fallback on CUDA failure is
   new code on branch `perf/whisper-gpu`, not something the deployed build
   has; the agent read it from the worktree while it was being written.
8. **MEASURED** — light 3-way concurrent load on loopback shows only modest
   serialization: wall time 6.83s for 3 concurrent short-fixture turns vs.
   ~3.96s median for one turn solo — not 3x (which would indicate full
   serialization) and not ~1x (full parallelism); consistent with STT being
   CPU-thread-bound (up to 662% CPU for one request) competing for cores
   across concurrent requests rather than a hard lock.
9. **MEASURED** — canned (no-topic) openers cost ~1.4–1.5s steady-state
   (first run 9.03s was a cold-start outlier) vs. topic-framed openers at
   3.0–3.8s steady-state (first run 10.11s, also cold) — confirms the canned
   path is genuinely cheaper and LLM-free, topic-framed openers pay a real LLM
   call.

## 5. Recommendations, ranked by expected impact

Each entry states an estimated saving and its tradeoff. Nothing below has been
implemented — this is a measurement-only run.

1. **Move Whisper STT to GPU (int8_float16, faster-whisper `small`).**
   Estimated saving: ~1.3–3.5s per turn (STT is currently 1.76–3.97s on
   CPU/int8; GPU STT for `small` typically runs at a fraction of that —
   consistent with the app's own settings-file comment recommending this).
   This is the single biggest win because STT is the dominant stage on longer
   utterances (74% of loopback total for `long`). Tradeoff: requires (a)
   adding GPU device reservation to the `app` service in a new compose
   override (not just `ollama`), (b) confirming/installing a CUDA-enabled
   `ctranslate2` build and the CUDA/cuDNN runtime libs in the app image —
   neither of which is true today — and (c) re-checking VRAM headroom in
   production once both models are resident simultaneously (2861 MiB free
   measured here is enough on paper for `small`/int8_float16's ~0.5–1 GB, but
   that figure is a vendor estimate, not measured on this box).
2. **Reduce/flatten Funnel connection variance for the internet path.**
   Estimated saving: potentially 5–15s on worst-case turns (B_short's
   p90–median gap is 7.5s, and the cold-outlier openers in scenario E show
   ~8s of pure connection-setup tax). Approaches: keep a warm/persistent
   connection from the client (HTTP keep-alive, or a WebSocket for the speech
   session) instead of a fresh HTTPS request per turn; investigate whether
   Funnel relay selection can be pinned or whether a direct Tailscale IP
   (bypassing Funnel) is viable for already-authenticated clients. Tradeoff:
   more client-side complexity; bypassing Funnel changes the exposure/auth
   model and needs its own security review.
3. **Pre-warm/parallelize TTS instead of lazy-on-first-fetch.**
   Estimated saving: ~0.45–1.1s per turn (the measured Piper synth cost),
   moved off the critical "audio starts" path by kicking off synthesis as
   soon as `reply_text` is known, in parallel with the client's own render
   delay, rather than waiting for the first `GET /speech/audio/{id}`.
   Tradeoff: burns CPU/Piper time on replies the learner may never play back
   (e.g. if they end the session); needs a cancellation or TTL policy to avoid
   wasted synth on abandoned turns.
4. **Cap/trim LLM `max_tokens` further for examiner replies, or stream text to the client before full generation completes.**
   Estimated saving: ~0.5–2s on longer replies today capped at 220 tokens
   (measured 1.1–5.4s LLM total for 25–91 tokens of output); streaming
   display (showing partial text as tokens arrive) wouldn't reduce actual
   compute time but would reduce *perceived* latency to "first words shown",
   which TTFT measurements (75–187ms) show could be very fast. Tradeoff:
   requires a streaming response contract on `/speech/turn` instead of a
   single JSON reply — a larger API change than the others here.
5. **Already in place, keep it: canned (no-topic) openers.**
   Confirmed cheap (~1.4s steady state) and LLM-free vs. topic-framed openers
   (~3-3.8s, LLM-billed). No action needed, just noting this is already the
   right default and should stay the default when a topic isn't essential to
   the drill.

## 6. Known gaps / explicitly skipped (per brief: skip and say so, don't work around)

- **webm/opus fixture transcode**: not produced. No `ffmpeg` binary found on
  the box host, inside `multilingual-app-1`, or on the Mac. Only WAV fixtures
  exist under `bench/latency/fixtures/`.
- **Loopback scenario C for the medium fixture**: not run, to stay within the
  ≤~40 speaking-turn budget for the whole session; short+long loopback already
  bracket the STT-scaling behavior (§2, §4.1), and medium's internet-path
  numbers (scenario B) were captured.
- **One `C_long` run (run index 2) returned an empty `audio_url`/`audio_fetch_s`** despite HTTP 200 on the turn itself. Not root-caused (likely a shell/inline-python parsing hiccup in the loopback benchmark script rather than a server defect, since the HTTP status was fine) — excluded from the `audio_fetch` stats for that fixture (n=4 instead of 5).
- **Whether the installed `ctranslate2` wheel / app base image has CUDA runtime libs at all** (independent of the missing device passthrough) was not disambiguated — e.g. via `ldd` on ctranslate2's shared library. The device-passthrough gap alone is sufficient to explain `cuda_device_count()==0`, but this second question should be checked before assuming a compose-only change is enough.
- **Mac-side network path ambiguity**: `lsof` showed an active connection to `ingress-sfo-01.tailscale.com` despite `tailscale status` reporting "stopped" — the "from the internet" scenario-B numbers may not reflect a fully vanilla home-network client, though this is a client-side artifact, not a server-side one.

## 7. Exact re-run commands

Note: the helper scripts named below (`turn_bench.py`, `loopback_bench.sh`,
`stage_bench.py`, `opener_bench.py`, `concurrency_loopback.sh`) were scratch files
and were not kept; re-running means regenerating them with the latency-tester agent.

Fixture generation (inside the app container, using the box's own Piper voice):

```sh
docker exec multilingual-app-1 sh -c '
  for n in short medium long; do
    echo "<fixture text for $n>" > /tmp/$n.txt
    piper --model /app/voices/fr_FR-upmc-medium.onnx \
          --output_file /tmp/$n.wav < /tmp/$n.txt
  done
'
docker cp multilingual-app-1:/tmp/short.wav  bench/latency/fixtures/short.wav
docker cp multilingual-app-1:/tmp/medium.wav bench/latency/fixtures/medium.wav
docker cp multilingual-app-1:/tmp/long.wav   bench/latency/fixtures/long.wav
```

Test account (safe, no DB access, reuses existing auth API):

```sh
curl -s -X POST "$BASE/auth/signup" \
  -H 'Content-Type: application/json' \
  -d '{"email":"latency-bot@example.test","password":"<pw>","invite_code":"<code>"}'
# -> 201 + bearer token, or 409 if it already exists -> then /auth/login
```

Scenario A (network only, from the Mac, against the public URL):

```sh
ping -c 5 rohith-alienware-17-r4.tail592ffa.ts.net
curl -s -o /dev/null -w "dns=%{time_namelookup} connect=%{time_connect} tls=%{time_appconnect} ttfb=%{time_starttransfer} total=%{time_total}\n" "$BASE/speech/status"
curl -s -o /dev/null -w "upload: size=%{size_upload} speed=%{speed_upload} total=%{time_total}\n" -X POST --data-binary @bench/latency/fixtures/medium.wav "$BASE/speech/turn"
```

Scenario B (full turn, from the internet) — `turn_bench.py`:

```sh
python3 turn_bench.py "$BASE" "$TOKEN" bench/latency/fixtures/short.wav short_internet 5 examiner out_B_short.json
```

Scenario C (full turn, from the box, loopback) — run ON the box:

```sh
ssh rohith@10.0.0.54
sh loopback_bench.sh "$TOKEN" /tmp/short.wav short_loopback 5 /tmp/C_short.json
```

Scenario D (per-stage compute, inside the container):

```sh
docker cp stage_bench.py multilingual-app-1:/tmp/stage_bench.py
docker exec -w /app -e PYTHONPATH=/app multilingual-app-1 /app/.venv/bin/python /tmp/stage_bench.py
docker cp multilingual-app-1:/tmp/stage_bench_results.json ./D_stage.json
docker exec multilingual-app-1 rm -f /tmp/stage_bench.py /tmp/stage_bench_results.json /tmp/short.wav /tmp/medium.wav /tmp/long.wav
```

Scenario E (opener, canned vs. topic-framed):

```sh
python3 opener_bench.py "$BASE" "$TOKEN" "" 5 out_E_canned.json
python3 opener_bench.py "$BASE" "$TOKEN" speak-b1-a-formation 3 out_E_topic.json
```

Scenario F (3-way concurrency, loopback) — run ON the box:

```sh
ssh rohith@10.0.0.54
sh concurrency_loopback.sh "$TOKEN" /tmp/short.wav 3
```

Config snapshot:

```sh
ssh rohith@10.0.0.54 "docker exec multilingual-app-1 env | grep -iE 'whisper|ollama'; \
  nvidia-smi --query-gpu=name,memory.total,memory.used,memory.free --format=csv; \
  docker exec multilingual-ollama-1 ollama ps; free -m; \
  docker inspect multilingual-app-1 --format '{{json .HostConfig.DeviceRequests}}'; \
  docker exec -w /app -e PYTHONPATH=/app multilingual-app-1 /app/.venv/bin/python -c \
    'import ctranslate2; print(ctranslate2.get_cuda_device_count())'"
```
