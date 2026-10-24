# Speaking: examiner history, prompt cache and warm-up (2026-10-24)

Live box (GTX 1070, Ollama 0.6.8, `qwen2.5:7b-instruct-q4_K_M`, 100% GPU, keep-alive forever).
Simulated 20-turn session on `speak-b1-b-ecrans`, at the live reply cap (`examiner_max_tokens=220`),
temperature 0.3, with a fresh nonce in the system prompt per session so nothing is pre-cached.
Each result is the mean of 2 reps. Bench scripts were throwaway, run in `multilingual-app-1` against `http://ollama:11434`.

## What changed

1. **Whole-session history, trimmed in blocks.** The old history was a 3-turn sliding window. From turn 4 on, the
   prompt shifted every turn, so Ollama's prefix cache missed and it re-read the whole prompt
   (~0.42 s per turn). The new history is append-only up to 16 turns. Past 16, the oldest turns are dropped 8 at a time,
   so the cache breaks once per 8 turns instead of on every turn (`_HISTORY_MAX_TURNS`, `_HISTORY_TRIM_BLOCK`
   in `app/speech/api.py`). This was not a context-limit issue: 40 turns (4082 tokens) did not truncate.
2. **Warm-up at session open.** `/speech/opener` schedules `SpeakingExaminer.warm` as a background task.
   It is a 1-token call over turn 1's exact prefix (system + topic framing + opener), sent while the learner
   listens to the opener. It runs for local (`ollama/`) models only, since a hosted provider would bill for it.
3. **Raw ChatML for Qwen.** Ollama's `/api/chat` re-tokenizes every suffix of the message list on
   every request to fit the context window. That time sits in `total_duration` but outside prompt eval and decode,
   and it grows with history:

   | turn | `/api/chat` overhead | `/api/generate` raw overhead |
   |---|---|---|
   | 1  | 0.013 s | 0.001 s |
   | 8  | 0.252 s | 0.001 s |
   | 16 | 0.823 s | 0.001 s |

   Without this fix, change 1 was a wash: mean total went from 2.40 s to 2.46 s, because the cache win was eaten by
   this overhead. `OllamaAdapter` now renders ChatML itself for `qwen*` models and calls `/api/generate` with
   `raw: true`. Other models still go through `/api/chat`.

## Result

| | today: window=3, `/api/chat`, no warm-up | new: raw + warm-up + whole session |
|---|---|---|
| turn 1 prefill | 1.196 s | **0.101 s** |
| turn 1 total | 3.35 s | **2.27 s** |
| turns 2–8 mean prefill | 0.337 s | **0.115 s** |
| turns 5–8 mean prefill | 0.419 s | **0.118 s** |
| turns 1–20 mean prefill | 0.438 s | **0.193 s** |
| turns 1–20 mean total | 2.43 s | **2.04 s** (−16%) |
| mean reply / decode | 42.0 tok @ 22.1 tok/s | 41.0 tok @ 22.4 tok/s |
| examiner remembers | last 3 turns | whole session (≤16) |

Reply length and decode speed are unchanged, so the gain is all on the prompt side.

**Cost of trimming.** Turn 17 re-reads the shortened prompt cold: 1.40 s prefill, 3.00 s total. That happens once every
8 turns past 16, about 0.16 s per turn amortized. That is still well under the 3-turn window's ~0.32 s per turn of cache misses.

An earlier run at a 60-token cap showed longer replies with full history (49.8 vs 38.7 tokens). That was an artifact
of the truncated replies in context: at the live 220 cap, lengths match.

## Per-turn prefill (mean of 2 reps)

```
turn  today (hist, prefill, total)   new (hist, prefill, total)
  1      1  1.196  3.35                 1  0.101  2.27
  4      3  0.471  2.27                 4  0.112  1.61
  8      3  0.424  2.50                 8  0.128  1.97
 12      3  0.445  2.13                12  0.140  2.10
 16      3  0.439  2.37                16  0.146  2.40
 17      3  0.425  2.34                 9  1.396  3.00   <- block trim
 20      3  0.452  2.71                12  0.152  1.77
```
