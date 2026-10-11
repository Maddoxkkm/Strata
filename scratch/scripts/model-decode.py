#!/usr/bin/env python3
"""Decode rate for whichever model a config points at, read from the engine's own per-request line.

    python scratch/scripts/model-decode.py <label> [config] [rounds]

decode-ab.py sends too early (it gets 503s and reports "no engine line"), so this follows the readiness
pattern that works in model-answers.py: wait for /health to report loaded, settle, then send requests and read
"strata serve: ... generated M tokens in Z ms (W tok/s)" for each. Prints every sample plus the median.
"""
import json
import pathlib
import re
import statistics
import subprocess
import sys
import time
import urllib.request

ROOT = pathlib.Path(r"D:\llm-dev\strata")
CFG = pathlib.Path(sys.argv[2]) if len(sys.argv) > 2 else ROOT / "scratch" / "configs" / "strata-iq2_xs.json"
ROUNDS = int(sys.argv[3]) if len(sys.argv) > 3 else 3
ENGINE_LOG = ROOT / "scratch" / "configs" / "strata-iq2_xs.log"
GEN = re.compile(r"generated (\d+) tokens in (\d+) ms \(([\d.]+) tok/s\)")

PROMPT = ("Write a short paragraph explaining why a database uses a write-ahead log, then list three "
          "practical consequences of that design for application developers.")


def up() -> bool:
    try:
        with urllib.request.urlopen("http://127.0.0.1:8080/health", timeout=5) as r:
            return b'"loaded": true' in r.read()
    except Exception:
        return False


def main():
    label = sys.argv[1] if len(sys.argv) > 1 else "model"
    subprocess.run(["cmd", "/c", "stop-server.bat"], cwd=ROOT, capture_output=True, stdin=subprocess.DEVNULL)
    time.sleep(2)
    log = open(ROOT / "logs" / f"server-decode-{label}.log", "w", encoding="utf-8")
    subprocess.Popen(["cmd", "/c", "run-iq2_xs.bat"], cwd=ROOT, stdout=log, stderr=subprocess.STDOUT,
                     stdin=subprocess.DEVNULL)
    for _ in range(90):
        if up():
            break
        time.sleep(5)
    else:
        raise SystemExit("  server never reported loaded")
    time.sleep(10)

    samples = []
    print(f"  === {label} decode (max_tokens=256, engine's own timing) ===")
    for r in range(ROUNDS):
        before = len(ENGINE_LOG.read_text(encoding="utf-8", errors="replace").splitlines())
        body = json.dumps({"model": "local", "messages": [{"role": "user", "content": PROMPT}],
                           "max_tokens": 256, "reasoning_budget_tokens": 0}).encode()
        req = urllib.request.Request("http://127.0.0.1:8080/v1/chat/completions", data=body,
                                    headers={"Content-Type": "application/json"})
        t0 = time.time()
        try:
            with urllib.request.urlopen(req, timeout=900) as resp:
                got = json.load(resp)
            wall = time.time() - t0
            n = got.get("usage", {}).get("completion_tokens")
            print(f"    round {r+1}: wall {wall:5.1f}s, completion_tokens={n}")
        except Exception as e:
            print(f"    round {r+1}: request failed: {e}")
        time.sleep(1)
        for l in ENGINE_LOG.read_text(encoding="utf-8", errors="replace").splitlines()[before:]:
            m = GEN.search(l)
            if m:
                samples.append(float(m.group(3)))
                print(f"      engine: {m.group(1)} tokens in {m.group(2)} ms = {m.group(3)} tok/s")
    if samples:
        print(f"  {label} decode median: {statistics.median(samples):.1f} tok/s "
              f"(samples {[round(s,1) for s in samples]})")
    else:
        print(f"  {label}: no engine decode line captured")
    subprocess.run(["cmd", "/c", "stop-server.bat"], cwd=ROOT, capture_output=True, stdin=subprocess.DEVNULL)


if __name__ == "__main__":
    main()
