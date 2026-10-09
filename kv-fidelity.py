#!/usr/bin/env python3
"""Short-answer fidelity check for a running Strata server (used to compare --kv int8 against --kv k8v4).

    .venv/Scripts/python.exe kv-fidelity.py <label>

Five prompts whose answer is known exactly, plus one light reasoning prompt. Everything that is not the requested
string counts as a miss, and the first 60 characters of each reply are printed so a "thinking out loud" reply is
visible rather than hidden behind a pass/fail. Fresh salt per run so nothing is served from a cache.
"""
import json
import sys
import time
import urllib.request

LABEL = sys.argv[1] if len(sys.argv) > 1 else "run"
URL = "http://127.0.0.1:8080/v1/chat/completions"
CASES = [
    ("Reply with exactly: alpha", "alpha"),
    ("Reply with exactly: 391", "391"),
    ("Reply with exactly: k8v4 live", "k8v4 live"),
    ("What is 17*23? Reply with the number only.", "391"),
    ("Name the capital of France. Reply with the name only.", "Paris"),
]


def ask(text, expect, max_tokens=96, timeout=600):
    body = {"model": "strata", "messages": [{"role": "user", "content": text}],
            "max_tokens": max_tokens, "reasoning_effort": "none", "temperature": 0}
    req = urllib.request.Request(URL, data=json.dumps(body).encode(),
                                 headers={"Content-Type": "application/json"})
    t0 = time.time()
    with urllib.request.urlopen(req, timeout=timeout) as r:
        d = json.load(r)
    got = (d["choices"][0]["message"].get("content") or "").strip()
    return got, expect in got, time.time() - t0, d["timings"]


def main():
    hits = 0
    print(f"kv-fidelity [{LABEL}]")
    for text, expect in CASES:
        got, ok, wall, t = ask(text, expect)
        hits += ok
        print(f"  {'OK  ' if ok else 'MISS'} expected {expect!r:<12} got {got[:60]!r}"
              f"  [{t['predicted_per_second']:.0f} t/s, {wall:.1f}s]")
    print(f"  -> {hits}/{len(CASES)} exact")


if __name__ == "__main__":
    main()
