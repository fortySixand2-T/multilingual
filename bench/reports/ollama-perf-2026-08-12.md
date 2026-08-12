# Ollama model/quant benchmark — GTX 1070 (8 GB, CC 6.1)

_Generated 2026-08-12 16:31 UTC · host: rohith@10.0.0.54 · driver 550.54.14 · ollama 0.6.8_

Measured with `bench/ollama_perf.py` inside the app container against `http://ollama:11434`, one model resident at a time. Rates are Ollama's native `eval_count / eval_duration` (exact tokens/sec), median of 3 runs/profile after a warmup. TTFT is wall-clock to first streamed token.

## Summary

| Model | VRAM fit | Cold load | Mean gen tok/s | Verdict |
|---|---|---|--:|---|
| `qwen2.5:3b-instruct-q4_K_M` | ✅ 3.08 GB (100% GPU) | 1.873s | **43.2** | ✅ Fast — snappy for chat/drills |
| `qwen2.5:7b-instruct-q4_K_M` | ✅ 5.99 GB (100% GPU) | 4.144s | **26.13** | ✅ Usable — fine for graded/async work |
| `llama3.1:latest` | ✅ 6.93 GB (100% GPU) | 6.172s | **25.53** | ✅ Usable — fine for graded/async work |
| `qwen2.5:7b-instruct-q5_K_M` | ✅ 6.7 GB (100% GPU) | 4.866s | **25.25** | ✅ Usable — fine for graded/async work |
| `qwen2.5:7b-instruct-q6_K` | ✅ 7.46 GB (100% GPU) | 5.359s | **20.9** | ✅ Usable — fine for graded/async work |
| `qwen2.5:14b-instruct-q3_K_M` | ⚠️ spill — 8.32/9.4 GB on GPU (88%) | 6.867s | **8.85** | ❌ Spills to CPU — too slow, don't use |

## Per-profile detail

### `qwen2.5:3b-instruct-q4_K_M`

- **Fit:** ✅ 3.08 GB (100% GPU) · **Cold load:** 1.873s

| Profile | Gen tok/s | Prompt tok/s | Out tokens | TTFT (s) | Total (s) |
|---|--:|--:|--:|--:|--:|
| drill_a2 | 43.75 | 8024.88 | 22 | 0.06 | 0.544 |
| grammar_explain | 41.991 | 6273.411 | 400 | 0.055 | 9.56 |
| writing_feedback | 43.203 | 8805.45 | 122 | 0.056 | 2.855 |
| examiner_roleplay | 43.415 | 6253.2 | 50 | 0.068 | 1.194 |
| vocab_enrich | 43.623 | 6869.816 | 29 | 0.058 | 0.699 |

### `qwen2.5:7b-instruct-q4_K_M`

- **Fit:** ✅ 5.99 GB (100% GPU) · **Cold load:** 4.144s

| Profile | Gen tok/s | Prompt tok/s | Out tokens | TTFT (s) | Total (s) |
|---|--:|--:|--:|--:|--:|
| drill_a2 | 26.689 | 8524.102 | 30 | 0.072 | 1.171 |
| grammar_explain | 25.717 | 6928.49 | 400 | 0.076 | 15.587 |
| writing_feedback | 26.282 | 9887.491 | 68 | 0.087 | 2.629 |
| examiner_roleplay | 26.404 | 7143.586 | 66 | 0.071 | 2.532 |
| vocab_enrich | 25.552 | 6121.35 | 29 | 0.096 | 1.173 |

### `llama3.1:latest`

- **Fit:** ✅ 6.93 GB (100% GPU) · **Cold load:** 6.172s

| Profile | Gen tok/s | Prompt tok/s | Out tokens | TTFT (s) | Total (s) |
|---|--:|--:|--:|--:|--:|
| drill_a2 | 25.736 | 20085.682 | 88 | 0.072 | 3.446 |
| grammar_explain | 24.884 | 10031.481 | 317 | 0.069 | 12.766 |
| writing_feedback | 25.537 | 22075.442 | 75 | 0.066 | 2.965 |
| examiner_roleplay | 25.604 | 16370.858 | 118 | 0.067 | 4.639 |
| vocab_enrich | 25.881 | 17191.62 | 34 | 0.065 | 1.344 |

### `qwen2.5:7b-instruct-q5_K_M`

- **Fit:** ✅ 6.7 GB (100% GPU) · **Cold load:** 4.866s

| Profile | Gen tok/s | Prompt tok/s | Out tokens | TTFT (s) | Total (s) |
|---|--:|--:|--:|--:|--:|
| drill_a2 | 25.69 | 8861.472 | 30 | 0.072 | 1.211 |
| grammar_explain | 24.499 | 4705.746 | 400 | 0.074 | 16.364 |
| writing_feedback | 25.212 | 9969.358 | 80 | 0.074 | 3.226 |
| examiner_roleplay | 25.34 | 7141.502 | 53 | 0.071 | 2.125 |
| vocab_enrich | 25.498 | 7483.871 | 35 | 0.071 | 1.406 |

### `qwen2.5:7b-instruct-q6_K`

- **Fit:** ✅ 7.46 GB (100% GPU) · **Cold load:** 5.359s

| Profile | Gen tok/s | Prompt tok/s | Out tokens | TTFT (s) | Total (s) |
|---|--:|--:|--:|--:|--:|
| drill_a2 | 21.154 | 7730.317 | 35 | 0.08 | 1.697 |
| grammar_explain | 20.372 | 6855.928 | 400 | 0.087 | 19.654 |
| writing_feedback | 20.815 | 9993.347 | 77 | 0.084 | 3.72 |
| examiner_roleplay | 20.98 | 7081.372 | 51 | 0.081 | 2.464 |
| vocab_enrich | 21.156 | 5272.795 | 34 | 0.082 | 1.656 |

### `qwen2.5:14b-instruct-q3_K_M`

- **Fit:** ⚠️ spill — 8.32/9.4 GB on GPU (88%) · **Cold load:** 6.867s

| Profile | Gen tok/s | Prompt tok/s | Out tokens | TTFT (s) | Total (s) |
|---|--:|--:|--:|--:|--:|
| drill_a2 | 8.978 | 534.461 | 49 | 0.151 | 5.603 |
| grammar_explain | 8.531 | 395.263 | 400 | 0.143 | 47.028 |
| writing_feedback | 8.816 | 592.46 | 54 | 0.157 | 6.272 |
| examiner_roleplay | 8.872 | 423.496 | 49 | 0.144 | 5.669 |
| vocab_enrich | 9.051 | 467.034 | 35 | 0.147 | 3.993 |

