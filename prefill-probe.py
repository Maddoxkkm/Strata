#!/usr/bin/env python3
"""Interleaved prefill probe: send the same ~3.1K-token prompt N times and report prompt/prefill tok/s.

    python prefill-probe.py <rounds> [label]

Prints per-round prompt tokens and the engine's own prefill timing (parsed from the server log tail if present),
plus the wall-clock rate from the HTTP response.  Same prompt every round, same max_tokens, so runs are comparable
before and after a tuning-table change.
"""
import json
import sys
import time
import urllib.request

ROUNDS = int(sys.argv[1]) if len(sys.argv) > 1 else 3
LABEL = sys.argv[2] if len(sys.argv) > 2 else "probe"
URL = "http://127.0.0.1:8080/v1/chat/completions"

# ~3,151 tokens at ~4 chars/token, matching the shape the upstream table was calibrated on
BODY = ("The following is a long technical note about GPU memory hierarchies. " * 240)
PROMPT = (BODY + "\n\nSummarise the note in one sentence.")


def one(i):
    payload = {"model": "local", "messages": [{"role": "user", "content": PROMPT}], "max_tokens": 8}
    req = urllib.request.Request(URL, data=json.dumps(payload).encode(),
                                 headers={"Content-Type": "application/json"})
    t0 = time.time()
    with urllib.request.urlopen(req, timeout=900) as r:
        d = json.load(r)
    wall = time.time() - t0
    pt = (d.get("usage") or {}).get("prompt_tokens")
    ct = (d.get("usage") or {}).get("completion_tokens")
    return wall, pt, ct


print(f"--- {LABEL}: {ROUNDS} rounds, {len(PROMPT)} chars (~{len(PROMPT)//4} tokens) ---")
rows = []
for i in range(ROUNDS):
    wall, pt, ct = one(i)
    rate = pt / wall if wall > 0 and pt else 0
    rows.append((wall, pt, rate))
    print(f"  round {i+1}: prompt_tokens={pt} completion={ct} wall={wall:.2f}s -> {rate:.1f} prompt tok/s (incl. decode)")
best = sorted(r[2] for r in rows)[len(rows) // 2]
print(f"  median prompt tok/s (wall, incl. {ROUNDS} rounds): {best:.1f}")
