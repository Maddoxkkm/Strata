#!/usr/bin/env python3
"""Server-side short-prompt A/B for STRATA_PREFILL_CPU_SHARE, from the engine's own read times.

    python short-ab.py            # arms: off, auto   (3 measured requests each, after a warm-up)

Restarts the live server per arm, sends the same short chat prompts, and reads the engine's
"prompt N tokens = 0 reused + N read in X ms (Y tok/s)" line - X is the engine's own prompt-processing
time, so it isolates the knob from HTTP and client overhead.
"""
import json
import pathlib
import re
import subprocess
import sys
import time
import urllib.request

ROOT = pathlib.Path(r"D:\llm-dev\strata")
CFG = ROOT / "strata-iq2_xs.json"
LOG = ROOT / "strata-iq2_xs.log"
URL = "http://127.0.0.1:8080/v1/chat/completions"
N = 3


def set_knob(value):
    c = json.loads(CFG.read_text(encoding="utf-8-sig"))
    env = c.setdefault("env", {})
    if value is None:
        env.pop("STRATA_PREFILL_CPU_SHARE", None)
    else:
        env["STRATA_PREFILL_CPU_SHARE"] = value
    CFG.write_text(json.dumps(c, indent=1), encoding="utf-8")


def kill_all():
    out = subprocess.run(["netstat", "-ano"], capture_output=True, text=True).stdout
    pids = {l.split()[-1] for l in out.splitlines() if ":8080" in l and "LISTENING" in l}
    for p in pids:
        subprocess.run(["cmd", "/c", f"taskkill /F /PID {p}"], capture_output=True)
    tl = subprocess.run(["tasklist"], capture_output=True, text=True).stdout
    for l in tl.splitlines():
        if l.lower().startswith("strata"):
            subprocess.run(["cmd", "/c", f"taskkill /F /PID {l.split()[1]}"], capture_output=True)


def restart():
    kill_all()
    time.sleep(3)
    subprocess.Popen(["cmd", "/c", "run-iq2_xs.bat"], cwd=str(ROOT),
                     stdout=open(ROOT / "logs" / "server-short-ab.log", "ab"),
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


def ask(i, n=64):
    body = json.dumps({"model": "local", "messages": [{"role": "user",
                       "content": f"Prompt {i}: why does an expert cache hit rate matter more than raw disk bandwidth? One sentence."}],
                       "max_tokens": n}).encode()
    req = urllib.request.Request(URL, data=body, headers={"Content-Type": "application/json"})
    mark = LOG.stat().st_size if LOG.exists() else 0
    with urllib.request.urlopen(req, timeout=600) as r:
        json.load(r)
    for _ in range(10):   # the engine writes its summary just after the HTTP response
        time.sleep(1)
        chunk = LOG.read_bytes()[mark:].decode("utf-8", errors="replace")
        m = re.search(r"prompt (\d+) tokens = 0 reused \+ \d+ read in (\d+) ms \(([\d.]+) tok/s\)", chunk)
        if m:
            return int(m.group(1)), int(m.group(2)), float(m.group(3))
    return None


def main():
    if len(sys.argv) > 1:
        arms = [(a, None if a.lower() in ("off", "none", "") else a) for a in sys.argv[1:]]
    else:
        arms = [("off", None), ("auto", "auto")]
    for name, value in arms:
        set_knob(value)
        if not restart():
            print(f"{name}: server did not come up", flush=True)
            continue
        ask(-1, 32)   # warm-up
        times = []
        print(f"--- STRATA_PREFILL_CPU_SHARE={name} ---", flush=True)
        for i in range(N):
            r = ask(i)
            if not r:
                print("  no engine line")
                continue
            tok, ms, rate = r
            times.append(ms)
            print(f"  {tok} tokens read in {ms} ms ({rate:.1f} tok/s)", flush=True)
        if times:
            med = sorted(times)[len(times) // 2]
            print(f"  median read: {med} ms for ~72 tokens ({72 / med * 1000:.1f} tok/s)", flush=True)


if __name__ == "__main__":
    main()
