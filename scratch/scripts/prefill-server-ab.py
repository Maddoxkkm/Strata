#!/usr/bin/env python3
"""Prefill A/B through the live server: same real-text prompt, one chunk size per arm.

    python scratch/scripts/prefill-server-ab.py 4096 7500 16384

The CLI ladder (ab-group.py) replays a *token file*, and repeated synthetic tokens route to a narrow expert
set, which flatters the rate. What the user actually experiences is a real prompt through serve/server.py,
so this harness measures that: it rewrites the engine config's --prefill, restarts the server from the
launcher, sends one long real-text prompt, and reads the engine's own accounting line

    strata serve: prompt N tokens = R reused + M read in T ms (RATE tok/s)
"""
import json
import pathlib
import re
import subprocess
import sys
import time
import urllib.request

ROOT = pathlib.Path(r"D:\llm-dev\strata")
CFG = ROOT / "scratch" / "configs" / "strata-iq2_xs.json"
import os as _os
if _os.environ.get("PRE_CONFIG"):                      # e.g. a second model's config (see model-bench.sh)
    CFG = ROOT / _os.environ["PRE_CONFIG"]
LOG = ROOT / "scratch" / "configs" / "strata-iq2_xs.log"
SERVER_LOG = ROOT / "logs" / "server-prefill-ab.log"
READ = re.compile(r"strata serve: prompt (\d+) tokens = (\d+) reused \+ (\d+) read in (\d+) ms \(([\d.]+) tok/s\)")

UNIT = ("The maintenance window is scheduled for the third Tuesday of each quarter, after the nightly "
        "replication has finished and before the morning batch jobs begin. Operators should confirm the "
        "replica lag is under sixty seconds, then drain the queue and verify that the failover path "
        "answers within the documented budget. ")


def prompt_for(tokens: int) -> str:
    # UNIT measures ~55 tokens, not 18: ask the tokenizer-free way and overshoot deliberately rather than
    # undershoot (a shorter prompt reads at a worse rate and would flatter the small-chunk arms)
    return UNIT * max(1, tokens // 55)


def set_chunk(n: int) -> None:
    c = json.loads(CFG.read_text(encoding="utf-8-sig"))
    a = c["args"]
    a[a.index("--prefill") + 1] = str(n)
    CFG.write_text(json.dumps(c, indent=1), encoding="utf-8")


def restart() -> None:
    subprocess.run(["cmd", "/c", "stop-server.bat"], cwd=ROOT, capture_output=True, stdin=subprocess.DEVNULL)
    time.sleep(2)
    server_log = open(SERVER_LOG, "w", encoding="utf-8")
    subprocess.Popen(["cmd", "/c", "run-iq2_xs.bat"], cwd=ROOT, stdout=server_log,
                     stderr=subprocess.STDOUT, stdin=subprocess.DEVNULL)
    for _ in range(60):
        try:
            with urllib.request.urlopen("http://127.0.0.1:8080/health", timeout=4) as r:
                if b'"loaded": true' in r.read():
                    return
        except Exception:
            pass
        time.sleep(5)
    raise SystemExit("  server did not come up")


def measure(tokens: int) -> float:
    body = json.dumps({"model": "local", "messages": [{"role": "user", "content": prompt_for(tokens)}],
                       "max_tokens": 4}).encode()
    req = urllib.request.Request("http://127.0.0.1:8080/v1/chat/completions", data=body,
                                headers={"Content-Type": "application/json"})
    t0 = time.time()
    with urllib.request.urlopen(req, timeout=900) as r:
        r.read()
    wall = time.time() - t0
    lines = [m for m in READ.finditer(LOG.read_text(encoding="utf-8", errors="replace"))]
    if not lines:
        return 0.0
    last = lines[-1]
    print(f"    prompt {int(last.group(1)):,} tok  read in {int(last.group(4))/1000:.1f} s  "
          f"= {float(last.group(5)):,.1f} tok/s   (wall {wall:.1f} s, chunks in log above)")
    return float(last.group(5))


def main():
    sizes = [int(x) for x in sys.argv[1:]] or [4096, 7500, 16384]
    print(f"  real-text prefill through the server, prompt ~24K tokens")
    out = {}
    for n in sizes:
        print(f"\n  --- --prefill {n} ---")
        set_chunk(n)
        restart()
        import os as _os
        out[n] = measure(int(_os.environ.get("PRE_TOKENS", 24000)))
        # the engine prints how it sliced the prompt; surface it for the record
        tail = SERVER_LOG.read_text(encoding="utf-8", errors="replace")
        for m in re.findall(r"prefill [0-9]+ tokens in [0-9]+ chunks[^\n]*", tail)[-1:]:
            print(f"    {m[:120]}")
        b = re.findall(r"RAM budget [\d.]+ GiB", tail)
        if b:
            print(f"    {b[-1]}")
    print("\n  === summary (server-side, real text) ===")
    for n, v in sorted(out.items(), key=lambda kv: -kv[1]):
        print(f"    --prefill {n:<6} {v:8,.1f} tok/s")


if __name__ == "__main__":
    main()
