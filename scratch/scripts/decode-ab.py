#!/usr/bin/env python3
"""Decode A/B for --kv modes, measured from the engine's own per-request line.

    python decode-ab.py k8v4 int8

For each mode: rewrite the config's --kv, restart the server, warm up, then send N requests of max_tokens=256 and
read the engine's "strata serve: prompt ... generated M tokens in Z ms (W tok/s)" line - W is the decode rate the
engine measured for that request, not wall clock.  Prints every sample and the median per mode.
"""
import json
import pathlib
import re
import subprocess
import sys
import time
import urllib.request

ROOT = pathlib.Path(r"D:\llm-dev\strata")
CFG = ROOT / "scratch/configs/strata-iq2_xs.json"
import os as _os
if _os.environ.get("AB_CONFIG"):                       # e.g. a second model's config (see model-bench.sh)
    CFG = ROOT / _os.environ["AB_CONFIG"]
LOG = ROOT / "scratch/configs/strata-iq2_xs.log"
URL = "http://127.0.0.1:8080/v1/chat/completions"
ROUNDS = 3
PROMPT = ("Write a short paragraph about GPU memory hierarchies and expert streaming, "
          "then a second paragraph about why bandwidth usually binds before compute. Keep it under 150 words.")


def set_kv(mode, exe=None):
    c = json.loads(CFG.read_text(encoding="utf-8-sig"))
    a = c["args"]
    a[a.index("--kv") + 1] = mode
    if exe:
        c["exe"] = exe
    CFG.write_text(json.dumps(c, indent=1), encoding="utf-8")


def restart():
    subprocess.run(["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-File",
                    str(ROOT / "stop-strata.ps1")], cwd=str(ROOT), capture_output=True, text=True)
    subprocess.Popen(["cmd", "/c", "run-iq2_xs.bat"], cwd=str(ROOT),
                     stdout=open(ROOT / "logs" / "server-decode-ab.log", "ab"),
                     stderr=subprocess.STDOUT)
    for _ in range(60):
        try:
            with urllib.request.urlopen("http://127.0.0.1:8080/health", timeout=5) as r:
                if '"loaded": true' in r.read().decode():
                    return True
        except Exception:
            pass
        time.sleep(5)
    return False


def one(i, n=256):
    body = json.dumps({"model": "local", "messages": [{"role": "user", "content": PROMPT}],
                       "max_tokens": n}).encode()
    req = urllib.request.Request(URL, data=body, headers={"Content-Type": "application/json"})
    mark = LOG.stat().st_size if LOG.exists() else 0
    t0 = time.time()
    with urllib.request.urlopen(req, timeout=900) as r:
        json.load(r)
    wall = time.time() - t0
    chunk = LOG.read_bytes()[mark:].decode("utf-8", errors="replace")
    hits = re.findall(r"prompt \d+ tokens = .*?generated (\d+) in (\d+) ms \(([\d.]+) tok/s\)", chunk)
    if hits:
        gen, ms, rate = hits[-1]
        return float(rate), int(gen), wall
    return None, None, wall


def main():
    modes = sys.argv[1:] or ["k8v4", "int8"]
    out = {}
    for mode in modes:
        set_kv(mode)
        if not restart():
            print(f"{mode}: server did not come up")
            continue
        one(-1, 32)   # warm-up, discarded
        rates = []
        print(f"--- --kv {mode} ---", flush=True)
        for i in range(ROUNDS):
            rate, gen, wall = one(i)
            if rate is None:
                print(f"  round {i+1}: no engine line (wall {wall:.1f}s)")
                continue
            rates.append(rate)
            print(f"  round {i+1}: {gen} tokens at {rate:.1f} tok/s ({wall:.1f}s wall)", flush=True)
        if rates:
            out[mode] = sorted(rates)[len(rates) // 2]
            print(f"  median decode: {out[mode]:.1f} tok/s", flush=True)
    print("\nsummary:", {k: round(v, 1) for k, v in out.items()})


if __name__ == "__main__":
    main()
