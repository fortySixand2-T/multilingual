"""Render bench/results/*.json into a single markdown report.

    python3 bench/render_report.py [results_dir] [out.md]

Defaults: bench/results -> bench/reports/ollama-perf-<UTC date>.md. Stdlib only.
"""

from __future__ import annotations

import glob
import json
import os
import sys
from datetime import UTC, datetime

HERE = os.path.dirname(os.path.abspath(__file__))


def load(results_dir: str) -> list[dict]:
    out = []
    for p in sorted(glob.glob(os.path.join(results_dir, "*.json"))):
        try:
            out.append(json.load(open(p)))
        except (ValueError, OSError):
            pass
    # Fastest first.
    return sorted(out, key=lambda d: d.get("mean_gen_tok_per_s", 0), reverse=True)


def fit_str(fit: dict) -> str:
    if not fit.get("resident"):
        return "n/a"
    if fit.get("fully_on_gpu"):
        return f"✅ {fit['vram_gb']} GB (100% GPU)"
    pct = int(round(fit.get("gpu_fraction", 0) * 100))
    return f"⚠️ spill — {fit['vram_gb']}/{fit['size_gb']} GB on GPU ({pct}%)"


def verdict(d: dict) -> str:
    fit, rate = d.get("fit", {}), d.get("mean_gen_tok_per_s", 0)
    if fit.get("resident") and not fit.get("fully_on_gpu"):
        return "❌ Spills to CPU — too slow, don't use"
    if rate >= 30:
        return "✅ Fast — snappy for chat/drills"
    if rate >= 15:
        return "✅ Usable — fine for graded/async work"
    if rate >= 8:
        return "🟡 Sluggish — tolerable, not for live chat"
    return "❌ Too slow"


def render(models: list[dict]) -> str:
    now = datetime.now(UTC).strftime("%Y-%m-%d %H:%M UTC")
    L = []
    L.append("# Ollama model/quant benchmark — GTX 1070 (8 GB, CC 6.1)")
    L.append("")
    L.append(f"_Generated {now} · host: rohith@10.0.0.54 · driver 550.54.14 · ollama 0.6.8_")
    L.append("")
    L.append(
        "Measured with `bench/ollama_perf.py` inside the app container against "
        "`http://ollama:11434`, one model resident at a time. Rates are Ollama's native "
        "`eval_count / eval_duration` (exact tokens/sec), median of "
        f"{models[0].get('runs_per_profile', '?') if models else '?'} runs/profile after a warmup. "
        "TTFT is wall-clock to first streamed token."
    )
    L.append("")

    # Summary table
    L.append("## Summary")
    L.append("")
    L.append("| Model | VRAM fit | Cold load | Mean gen tok/s | Verdict |")
    L.append("|---|---|---|--:|---|")
    for d in models:
        L.append(
            f"| `{d['model']}` | {fit_str(d.get('fit', {}))} | "
            f"{d.get('cold_load_s', '?')}s | **{d.get('mean_gen_tok_per_s', '?')}** | "
            f"{verdict(d)} |"
        )
    L.append("")

    # Per-model detail
    L.append("## Per-profile detail")
    L.append("")
    for d in models:
        L.append(f"### `{d['model']}`")
        L.append("")
        L.append(f"- **Fit:** {fit_str(d.get('fit', {}))} · **Cold load:** {d.get('cold_load_s')}s")
        L.append("")
        L.append("| Profile | Gen tok/s | Prompt tok/s | Out tokens | TTFT (s) | Total (s) |")
        L.append("|---|--:|--:|--:|--:|--:|")
        for p in d.get("profiles", []):
            L.append(
                f"| {p['profile']} | {p['gen_tok_per_s']} | {p['prompt_tok_per_s']} | "
                f"{p['gen_tokens']} | {p['ttft_s']} | {p['total_s']} |"
            )
        L.append("")
    return "\n".join(L) + "\n"


if __name__ == "__main__":
    results_dir = sys.argv[1] if len(sys.argv) > 1 else os.path.join(HERE, "results")
    models = load(results_dir)
    if not models:
        print(f"no results in {results_dir}", file=sys.stderr)
        raise SystemExit(1)
    default_out = os.path.join(HERE, "reports", f"ollama-perf-{datetime.now(UTC):%Y-%m-%d}.md")
    out = sys.argv[2] if len(sys.argv) > 2 else default_out
    os.makedirs(os.path.dirname(out), exist_ok=True)
    with open(out, "w") as f:
        f.write(render(models))
    print(f"wrote {out} ({len(models)} models)")
