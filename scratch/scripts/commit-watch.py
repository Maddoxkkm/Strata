#!/usr/bin/env python3
"""Commit-charge watch: what a long prompt does to the Windows commit limit while the engine is loaded.

    python commit-watch.py [tokens] [max_new]

Samples \\Memory\\Committed Bytes and \\Memory\\Commit Limit once a second through a request, so the headroom
(the thing that kills the engine with 0xC0000409 when it runs out) is visible per second.  See issues #1607
(the admission checks read only ullAvailPhys) and #1630 (a 8192-token prompt chunk spikes commit ~70 GB on a
7900 XTX).
"""
import json
import subprocess
import sys
import threading
import time
import urllib.request

URL = "http://127.0.0.1:8080/v1/chat/completions"
UNIT = ("The expert cache holds the layer-expert matrices the router is likely to pick, so a token is computed on "
        "the GPU instead of being streamed; the hit rate matters more than raw bandwidth. ")
TOKENS = int(sys.argv[1]) if len(sys.argv) > 1 else 12000
MAX_NEW = int(sys.argv[2]) if len(sys.argv) > 2 else 8


class Sampler(threading.Thread):
    def __init__(self):
        super().__init__(daemon=True)
        self.samples = []
        self._stop = threading.Event()

    def run(self):
        cmd = ["powershell", "-NoProfile", "-Command",
               "Get-Counter '\\Memory\\Committed Bytes','\\Memory\\Commit Limit' -SampleInterval 1 -MaxSamples 90 | "
               "ForEach-Object { $_.CounterSamples | ForEach-Object { $_.CookedValue } }"]
        p = subprocess.Popen(cmd, stdout=subprocess.PIPE, text=True)
        self._proc = p
        vals = []
        while not self._stop.is_set():
            line = (p.stdout.readline() if p.stdout else "")
            if not line:
                break
            try:
                vals.append(float(line.strip()))
            except ValueError:
                continue
            if len(vals) % 2 == 0 and len(vals) >= 2:
                self.samples.append((vals[-2], vals[-1]))
        try:
            p.kill()          # never leave the counter's process behind: the caller waits on the tree
        except Exception:
            pass

    def stop(self):
        self._stop.set()


def main():
    text = "User: explain the expert cache.\nAssistant: " + UNIT * max(1, TOKENS // 25)
    print(f"  prompt ~{len(text)//4} chars (~{TOKENS} tokens), max_tokens={MAX_NEW}")
    s = Sampler()
    s.start()
    time.sleep(2)
    t0 = time.time()
    body = json.dumps({"model": "local", "messages": [{"role": "user", "content": text + f"\n[{t0}]"}],
                       "max_tokens": MAX_NEW}).encode()
    req = urllib.request.Request(URL, data=body, headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=1800) as r:
            d = json.load(r)
        usage = d.get("usage") or {}
        print(f"  request done in {time.time()-t0:.1f}s, prompt_tokens={usage.get('prompt_tokens')}")
    except Exception as e:
        print(f"  REQUEST FAILED after {time.time()-t0:.1f}s: {type(e).__name__}: {e}")
    time.sleep(3)
    s.stop()
    if not s.samples:
        print("  no samples")
        return
    peak_used = max(u for u, _ in s.samples)
    limit = s.samples[-1][1]
    first = s.samples[0][0]
    print(f"  committed: start {first/2**30:.1f} GiB -> peak {peak_used/2**30:.1f} GiB of {limit/2**30:.1f} GiB "
          f"({100*peak_used/limit:.1f}% used, {((limit-peak_used)/2**30):.1f} GiB headroom at peak)")


if __name__ == "__main__":
    main()
