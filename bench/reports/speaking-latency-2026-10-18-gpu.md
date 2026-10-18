# Speaking latency: Whisper on GPU vs the CPU baseline (2026-10-18)

This run repeats the [2026-10-17 baseline](speaking-latency-2026-10-17-baseline.md)
after the box was rebuilt so faster-whisper runs on the GTX 1070 (`WHISPER_DEVICE=cuda`,
`WHISPER_COMPUTE_TYPE=int8`). It used the same fixtures
(`bench/latency/fixtures/{short,medium,long}.wav`), the same scratch scripts, the same
run counts and the same `latency-bot` account. It was measurement only: no container was
rebuilt, restarted or reconfigured, and every temp file on the box and in the container
was removed. Raw samples are in
[`bench/results/latency-2026-10-18-gpu.json`](../results/latency-2026-10-18-gpu.json).
The `before_after_summary` key in that file holds every number in the tables below.

Budget used: 33 spoken turns and 3 topic openers that called the LLM (the cap is about 40).

## 1. Headline

**Loopback is the fair comparison.** The baseline's internet runs for short and long were
hit by a degraded Funnel connection. Section 4.4 shows this with fetches of already-cached
audio that took 3 to 24 s. So only the loopback rows and the internet medium row isolate
what the GPU changed.

| Path | Fixture | → reply text, before → after (median / p90) | → audio starts, before → after (median / p90) |
|---|---|---|---|
| Loopback | short (~1.8 s speech) | 3.96 / 7.02 → **1.79 / 1.86** | 5.11 / 8.16 → **2.45 / 2.56** |
| Loopback | medium (~5.7 s) | not run → **2.45 / 3.22** | not run → **3.25 / 4.25** |
| Loopback | long (~11.8 s) | 4.55 / 5.83 → **3.57 / 4.41** | 5.64 / 6.93 → **4.59 / 5.56** |
| Internet | short | 12.34 / 19.81 → **2.46 / 4.04** ² | 34.19 / 40.33 → **3.70 / 6.06** ² |
| Internet | medium | 4.22 / 4.85 → **3.82 / 4.29** | 6.52 / 9.57 → **6.26 / 6.74** |
| Internet | long | 35.03 / 65.19 → **3.68 / 4.30** ² | 64.30 / 89.42 → **4.90 / 5.86** ² |

n=5 per cell, except the baseline's loopback long "audio" cell (n=4).
"Audio starts" is the reply text time plus the first `GET /speech/audio/{id}`, which
includes the lazy Piper synthesis. For the baseline, the loopback "audio" cells were
recomputed per run from the raw JSON (turn + fetch). The baseline report summed component
medians instead (5.09 / 5.33), so its figures differ slightly.
² Most of this drop comes from the baseline's degraded Funnel path, not from the GPU
(section 4.4).

## 2. Per-stage before/after (compute, measured inside the container)

Scenario D: the real adapters, run with `docker exec`, 5 runs per STT fixture and per TTS
text, and 6 LLM calls with streaming (2 prompts × 3). These stages don't depend on the
network path, so they apply to both loopback and internet.

| Stage | Before median / p90 | After median / p90 | Δ median |
|---|---|---|---|
| STT short (faster-whisper small) | 1.76 / 2.48 s (cpu int8) | **0.23 / 0.26 s** (cuda int8) | −1.53 s (7.8×) |
| STT medium | 1.69 / 2.31 s | **0.30 / 0.32 s** | −1.39 s (5.6×) |
| STT long | 3.97 / 4.25 s | **0.57 / 0.57 s** | −3.40 s (6.9×) |
| LLM TTFT (qwen2.5 7B q4_K_M) | 0.10 / 0.14 s | 0.08 / 0.08 s | ≈ unchanged |
| LLM total | 2.22 / 2.87 s (51.5 tok median) | 2.35 / 2.46 s (55 tok median) | ≈ unchanged (tracks reply length) |
| LLM throughput | 23.6 tok/s | 24.0 tok/s | unchanged: STT on the same GPU does not slow Ollama |
| TTS short reply (Piper) | 0.58 / 0.63 s | 0.40 / 0.43 s | −0.19 s ³ |
| TTS medium reply | 0.94 / 1.13 s | 0.73 / 0.77 s | −0.21 s ³ |

³ Piper still runs on the CPU (onnxruntime providers: `AzureExecutionProvider`,
`CPUExecutionProvider`; no CUDA provider). The small speed-up is probably less CPU
contention, not the migration (an inference).

### Same table by path (end-to-end, from the client)

| Metric | Loopback before → after | Internet before → after |
|---|---|---|
| Time to text, short | 3.96 / 7.02 → 1.79 / 1.86 | 12.34 / 19.81 → 2.46 / 4.04 ² |
| Time to text, medium | — → 2.45 / 3.22 | 4.22 / 4.85 → 3.82 / 4.29 |
| Time to text, long | 4.55 / 5.83 → 3.57 / 4.41 | 35.03 / 65.19 → 3.68 / 4.30 ² |
| First audio fetch (TTS + download), short | 1.14 / 1.24 → 0.66 / 0.69 | 20.52 / 26.23 → 1.35 / 2.02 ² |
| First audio fetch, medium | — → 0.83 / 1.15 | 2.11 / 5.42 → 1.98 / 2.92 |
| First audio fetch, long | 0.78 / 1.09 → 1.08 / 1.22 | 24.23 / 30.16 → 1.24 / 1.56 ² |
| Time to audio, short | 5.11 / 8.16 → 2.45 / 2.56 | 34.19 / 40.33 → 3.70 / 6.06 ² |
| Time to audio, medium | — → 3.25 / 4.25 | 6.52 / 9.57 → 6.26 / 6.74 |
| Time to audio, long | 5.64 / 6.93 → 4.59 / 5.56 | 64.30 / 89.42 → 4.90 / 5.86 ² |

## 3. Waterfall after the migration (loopback medians, time to audio)

The app does not log per-stage timing for a real turn, so the "LLM + app" share is the
turn total minus the STT time from scenario D. Medians don't add up exactly, so the
shares are approximate.

| Fixture | Total | STT | LLM + app overhead | TTS + fetch |
|---|---|---|---|---|
| short | 2.45 s | 0.23 s (9 %) | ~1.56 s (64 %) | 0.66 s (27 %) |
| medium | 3.25 s | 0.30 s (9 %) | ~2.15 s (66 %) | 0.83 s (26 %) |
| long | 4.59 s | 0.57 s (12 %) | ~3.00 s (65 %) | 1.08 s (24 %) |

STT went from the dominant stage for long utterances (74 % of loopback time to audio in
the baseline) to about 10 % of the total. **The examiner LLM now takes about two thirds of
every turn.**

On a clean connection, the internet path adds about 0.1 to 1.4 s on top of loopback for
time to text. The spread is wide because reply length is not controlled between runs.
For a 0.3 to 0.8 MB WAV reply, the audio download adds about 0.3 to 0.9 s more than
loopback (cached fetch over Funnel: 0.30 to 0.94 s).

## 4. Findings

1. **Measured: STT is 5.6 to 7.8 times faster on the GPU** (median 1.76 → 0.23,
   1.69 → 0.30 and 3.97 → 0.57 s), and its variance collapsed: long p90 − min went from
   0.78 s to 0.006 s. It also no longer grows much with audio length: going from 1.8 s
   to 11.8 s of speech now costs 0.34 s, against 2.2 s before.
2. **Measured: loopback time to audio fell by 52 % for short (5.11 → 2.45 s) and 19 %
   for long (5.64 → 4.59 s).** Long gains less than the 3.4 s STT saving because these
   runs' LLM replies were longer. Loopback long time to text minus STT is about 3.0 s now,
   against about 0.58 s in the baseline, whose long replies happened to be very short.
   Reply length is an uncontrolled confound in every end-to-end number.
3. **Measured: putting Whisper on the GPU did not slow the LLM.** Ollama runs at
   23.95 tok/s against 23.6 tok/s before, with TTFT of 75 to 176 ms, while Whisper sits
   resident on the same card.
4. **Measured: the baseline's internet numbers for short and long were network
   artefacts.** Fetching already-cached audio involves no compute, yet in the baseline it
   took 2.9 to 15.4 s (short) and 10.7 to 24.4 s (long). Today it takes 0.30 to 0.81 s.
   The no-LLM canned opener also went from 1.45 to 0.10 s warm, and STT has nothing to do
   with that path. **So the 30 to 60 s internet improvement for short and long is mostly
   Funnel recovering, not the GPU.** Medium is the one clean internet comparison:
   4.22 → 3.82 s to text, even though today's medium replies were longer (median 251
   against 200 characters).
5. **Measured: light concurrency.** With 3 short turns at once on loopback, the wall time
   was 3.40 s against 6.83 s in the baseline. Individual turns took 2.42, 2.46 and 3.33 s
   against a 1.79 s median when run alone. Requests still partly serialize, most likely
   at Ollama, which serves one model and one GPU (an inference). CPU contention between
   Whisper threads no longer plays a part.
6. **Measured: VRAM.** At idle, 5633 of 8192 MiB is used (Ollama 5232 MiB, app Whisper
   388 MiB), leaving 2473 MiB free. During the stage bench, which loaded a second probe
   Whisper model, the peak was 6149 MiB at 94 % utilisation. There is room for one more
   small model, but not for a second 7B.
7. **Measured: topic openers are faster** (3.76 → 2.02 s median; the cold first call went
   from 10.11 to 2.49 s). Most of the cold-start gain is probably the network recovery in
   finding 4 (an inference), since this path does not run STT.
8. **Anomaly (scripting, not the server): 5 of 15 loopback turns came back with an empty
   `audio_url`** (short #3; long #0, #1, #3, #4). The baseline had one such run. All five
   turns returned HTTP 200. Afterwards I fetched `/speech/audio/{131,138,139,141,142}`
   and all five returned 200 with WAV data. Those first fetches, which include the Piper
   synthesis, were folded into the stats and flagged with `audio_fetch_recovered_later`.
   Inferred cause: on the box `/bin/sh` is `dash`, and the scratch `loopback_bench.sh`
   pipes the body through `echo`. Dash's `echo` expands `\n` escapes inside the JSON
   string, so the Python parser rejects the body. A future run should use
   `printf '%s'` or Python for loopback.

## 5. What's left: the next-biggest stage is the examiner LLM

After the migration, the LLM accounts for about 1.6 to 3.0 s, roughly 65 % of loopback
time to audio. Generation is stable at about 24 tok/s, so its cost is simply reply length:
**about 0.42 s per 10 output tokens**. TTS plus fetch is next at about 25 % (0.66 to
1.08 s), and STT is now about 10 %.

Ranked options. None of them was implemented.

1. **Stream LLM tokens and synthesize TTS per sentence.** TTFT is 0.08 s. Showing text as
   it streams, and starting Piper on the first sentence (about 15 tokens ≈ 0.6 s, then
   about 0.2 s of synthesis), would bring "audio starts" from 2.5 to 4.6 s down to about
   1.2 to 1.5 s after STT, saving roughly 1.5 to 3 s. Cost: `/speech/turn` needs a
   streaming contract (SSE or WebSocket), and the client must queue audio chunks. This is
   the largest API change on the list.
2. **Shorter examiner replies.** Tighten the prompt toward 1 or 2 sentences, or lower
   `EXAMINER_MAX_TOKENS` from 220 to about 80. Today's replies are 24 to 70 tokens (1.0 to
   3.0 s), so capping them at about 35 tokens saves about 0.5 to 1.5 s on longer turns.
   Cost: a less rich examiner, and replies cut off mid-sentence if the cap does the work
   instead of the prompt.
3. **Kick off TTS eagerly when the reply text is ready** instead of waiting for the first
   `GET`. This takes the 0.4 to 0.7 s synthesis off the critical path whenever the client
   needs a moment to render the text. Cost: wasted CPU on replies nobody plays.
4. **Send compressed audio (Opus or MP3) instead of WAV.** Replies are 0.35 to 0.83 MB of
   WAV. Over Funnel that costs 0.3 to 0.9 s to download, while Opus at about 24 kbps would
   be about 30 KB, saving about 0.3 to 0.8 s on the internet path. Cost: an encode step,
   which needs ffmpeg or an encoder library in the image (neither is present today).
5. **A smaller LLM, such as qwen2.5:3b**, which the 2026-08-12 bench measured at 43 tok/s against about 24 here (about 1.8×).
   It roughly halves the largest stage, at the price of noticeably weaker French examiner
   quality (see `bench/reports/QUALITY-2026-08-12.md`).

## 6. Config snapshot

Taken from `docker exec multilingual-app-1 env`, `nvidia-smi`, `ollama ps`, `free -m` and
`docker inspect`, before and after the run. The values did not change.

| Setting | Value |
|---|---|
| Deployed commit | `07e4d09` (branch `perf/whisper-gpu`) |
| `STT_BACKEND` / `WHISPER_MODEL` | `faster-whisper` / `small` |
| `WHISPER_DEVICE` / `WHISPER_COMPUTE_TYPE` | **`cuda` / `int8`** (adapter reports `device=cuda`; no CPU-fallback warning in the logs) |
| ctranslate2 | 4.8.1, `get_cuda_device_count() == 1` |
| app container `DeviceRequests` | `[{Driver: nvidia, Count: -1, Capabilities: [[gpu]]}]` |
| `OLLAMA_MODEL` | `qwen2.5:7b-instruct-q4_K_M`, 6.0 GB, 100 % GPU, keep-alive forever |
| `EXAMINER_MAX_TOKENS` | unset → 220 |
| Piper voice | `/app/voices/fr_FR-upmc-medium.onnx` (CPU onnxruntime 1.28.0) |
| GPU | GTX 1070, 8192 MiB; used 5633 MiB idle (Ollama 5232 + Whisper 388), 2473 MiB free |
| Host RAM | 31964 MiB total, 18082 MiB available |
| App container CPUs | 8 |

## 7. How to re-run

The scratch scripts from the baseline run were reused unchanged, except that the stage
bench now reads the device from the environment. They live in the job scratch directory,
not in the repo:

```sh
# A: network only (Mac → Funnel)
ping -c 5 rohith-alienware-17-r4.tail592ffa.ts.net
curl -s -o /dev/null -w '%{time_appconnect} %{time_total}\n' "$BASE/speech/status"   # ×3 fresh
curl -s -o /dev/null -o /dev/null -o /dev/null -w '%{time_total}\n' "$BASE/speech/status" "$BASE/speech/status" "$BASE/speech/status"  # reused
# B: full turn over the internet, 5× per fixture
python3 turn_bench.py "$BASE" "$TOKEN" bench/latency/fixtures/short.wav short_internet 5 examiner B_short.json
# C: loopback, on the box (fix the dash `echo` issue first: use printf '%s' "$BODY")
sh loopback_bench.sh "$TOKEN" ~/latency_bench_tmp/short.wav short_loopback 5 ~/latency_bench_tmp/C_short.json
# D: per-stage compute inside the container (STT device/compute type from the container env)
docker cp stage_bench_gpu.py multilingual-app-1:/tmp/ && docker cp short.wav multilingual-app-1:/tmp/   # + medium, long
docker exec -w /app -e PYTHONPATH=/app multilingual-app-1 /app/.venv/bin/python /tmp/stage_bench_gpu.py
docker exec multilingual-app-1 rm -f /tmp/stage_bench_gpu.py /tmp/stage_bench_results.json /tmp/*.wav
# E: openers
python3 opener_bench.py "$BASE" "$TOKEN" "" 5 E_canned.json
python3 opener_bench.py "$BASE" "$TOKEN" speak-b1-a-formation 3 E_topic.json
# F: 3 concurrent turns, loopback, on the box
sh concurrency_loopback.sh "$TOKEN" ~/latency_bench_tmp/short.wav F_wall.txt
```
