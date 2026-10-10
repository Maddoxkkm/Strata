#!/usr/bin/env python3
"""Combine the prefill arm measurements into a decision table.

    .venv/Scripts/python.exe analyze-prefill.py

Reads prefill-arms.csv (written by prefill-bench.py), groups the fresh requests by (arm, prompt size),
and prints every sample plus the median per group. The arms differ in a couple of characters of their
prompt token counts (the filler lands where it lands), so sizes are bucketed: <10k and >=10k.
"""
import csv
import pathlib
import statistics
from collections import defaultdict

ROOT = pathlib.Path(r"D:\llm-dev\strata")


def bucket(tokens: int) -> str:
    return "~6k prompt" if tokens < 10000 else "~13k prompt"


rows = [r for r in csv.DictReader((ROOT / "prefill-arms.csv").open(encoding="utf-8"))
        if r["request"].startswith("fresh_")]
groups = defaultdict(list)
for r in rows:
    groups[(r["arm"], bucket(int(r["prompt_tokens"])))].append((int(r["prompt_tokens"]), float(r["prefill_tok_s"]),
                                                                 float(r["decode_tok_s"])))

arms, sizes = [], []
for a, s in groups:
    if a not in arms:
        arms.append(a)
    if s not in sizes:
        sizes.append(s)
arms.sort()
sizes.sort()

print(f"{len(rows)} fresh-prompt measurements\n")
for size in sizes:
    print(f"{size} — prefill tok/s (every sample, then median)")
    base = None
    for a in arms:
        v = groups.get((a, size))
        if not v:
            continue
        rates = [x[1] for x in v]
        med = statistics.median(rates)
        if base is None:
            base = med
        delta = f"{100 * (med / base - 1):+5.1f}%" if base else ""
        samples = ", ".join(f"{x:.0f}" for x in sorted(rates))
        dec = statistics.median([x[2] for x in v])
        print(f"  {a:<24} n={len(rates)}  [{samples:<22}] median {med:6.1f} t/s {delta:>7}   decode {dec:5.1f} t/s")
    print()

print("verdict: compare each arm's median against the baseline column; this box's run-to-run spread is ~25%,")
print("so only a consistent gap across BOTH prompt sizes is worth adopting.")
