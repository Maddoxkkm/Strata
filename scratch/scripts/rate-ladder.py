#!/usr/bin/env python3
"""Prefill rate vs prompt size, from every server/engine log we still have.

    python rate-ladder.py

Three sources are parsed, all of them the engine's own accounting:
  * `strata serve: prompt N tokens = ... read in T ms (R tok/s)`  - the per-request read
  * `[strata] reading the prompt: N of M tokens, T s so far`      - per-chunk progress
  * `[strata] done: X tokens in T s (R tok/s)`                    - the summary line
The point: prefill rate depends strongly on prompt size (per-chunk overhead amortises), so a
"1.3k then, <1k now" comparison is only meaningful at the same prompt length.
"""
import pathlib
import re
import sys

ROOT = pathlib.Path(r"D:\llm-dev\strata")
READ = re.compile(r"prompt (\d+) tokens = (\d+) reused \+ (\d+) read in (\d+) ms \(([\d.]+) tok/s\)")
PROG = re.compile(r"reading the prompt: ([\d,]+) of ([\d,]+) tokens, (\d+) s so far")
DONE = re.compile(r"done: (\d+) tokens in ([\d.]+) s \(([\d.]+) tok/s\)")
BUDGET = re.compile(r"RAM budget ([\d.]+) GiB")


def logs():
    files = [ROOT / "scratch/configs/strata-iq2_xs.log"] + sorted(ROOT.glob("logs/server-*.log"))
    return [f for f in files if f.exists()]


def main():
    rows = []          # (prompt_tokens, rate, source, kind)
    budgets = {}       # source -> budget GiB seen
    for f in logs():
        text = f.read_text(encoding="utf-8", errors="replace")
        for m in READ.finditer(text):
            prompt_t, reused, read, ms, rate = (int(m.group(1)), int(m.group(2)), int(m.group(3)),
                                                int(m.group(4)), float(m.group(5)))
            # a cache-served request (most of the prompt reused) is not a prefill measurement
            if reused > prompt_t // 10 or read < 512:
                continue
            rows.append((prompt_t, rate, f.name, "read"))
        for m in PROG.finditer(text):
            pass          # progress lines carry no reuse breakdown, so they cannot be told from a cache hit
        b = BUDGET.findall(text)
        if b:
            budgets[f.name] = b[-1]

    if not rows:
        print("  no records")
        return
    rows.sort(key=lambda r: -r[1])
    print("=== highest recorded prefills (real reads only) ===")
    for total, rate, src, kind in rows[:16]:
        print(f"  {rate:8.1f} tok/s   prompt {total:>7,} tok   {kind:<8} {src}")

    print("\n=== rate by prompt-size bucket (median of the top half, all logs) ===")
    buckets = [(0, 4096), (4096, 8192), (8192, 16384), (16384, 32768), (32768, 10**9)]
    for lo, hi in buckets:
        sel = sorted(r for t, r, _, _ in rows if lo <= t < hi)
        if not sel:
            continue
        mid = sel[len(sel) // 2]
        print(f"  {lo:>6}-{hi if hi < 10**9 else '∞':>7}: n={len(sel):<4} median {mid:8.1f} tok/s   "
              f"best {sel[-1]:8.1f}")

    print("\n=== budget recorded per log (the prefill lever) ===")
    for name, b in sorted(budgets.items()):
        print(f"  {b:>6} GiB  {name}")


if __name__ == "__main__":
    main()
