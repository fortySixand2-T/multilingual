"""Assemble a BLIND evaluation packet from the captured model samples.

Reads bench/results/samples/*.json, assigns each model a stable anonymous label
(Model A, B, ...) via a seeded shuffle, and emits the outputs grouped by task so a
judge who knows nothing about the project — or which model is which — can score
them. The label->model key is written separately (NOT part of the packet) so the
judge stays blind; we de-anonymize after scoring.

    python bench/build_eval_packet.py
      -> writes  bench/results/eval_key.json   (label -> real model, for us)
      -> prints   the anonymized packet (feed to the judge agent)
"""

from __future__ import annotations

import glob
import json
import os
import random

HERE = os.path.dirname(os.path.abspath(__file__))
SAMPLES = os.path.join(HERE, "results", "samples")
KEY_OUT = os.path.join(HERE, "results", "eval_key.json")
SHUFFLE_SEED = 1337


def main() -> None:
    files = sorted(glob.glob(os.path.join(SAMPLES, "*.json")))
    runs = [json.load(open(f, encoding="utf-8")) for f in files]
    if not runs:
        raise SystemExit(f"no samples in {SAMPLES}")

    models = [r["model"] for r in runs]
    labels = [f"Model {chr(ord('A') + i)}" for i in range(len(models))]
    order = list(range(len(models)))
    random.Random(SHUFFLE_SEED).shuffle(order)
    label_of = {models[order[i]]: labels[i] for i in range(len(models))}
    json.dump({label_of[m]: m for m in models}, open(KEY_OUT, "w", encoding="utf-8"), indent=2)

    # Group outputs by task, models listed in label order (A, B, ...) so identity
    # can't be inferred from position.
    by_task: dict[str, dict[str, str]] = {}
    task_order: list[str] = []
    prompts: dict[str, str] = {}
    for r in runs:
        for s in r["samples"]:
            t = s["task"]
            if t not in by_task:
                by_task[t] = {}
                task_order.append(t)
                prompts[t] = s["prompt"]
            by_task[t][label_of[r["model"]]] = s["output"]

    header = f"# Blind evaluation packet ({len(models)} systems, {len(task_order)} tasks)\n"
    out = [header]
    for t in task_order:
        out.append(f"\n===== TASK: {t} =====")
        out.append(f"PROMPT: {prompts[t]}\n")
        for lab in labels:
            text = by_task[t].get(lab, "(no output)")
            out.append(f"--- {lab} ---\n{text}\n")
    print("\n".join(out))


if __name__ == "__main__":
    main()
