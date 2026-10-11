#!/usr/bin/env python3
"""Issue #1913's diagnostic on this box: where a decode window's time goes, per request.

    python scratch/scripts/decode-timing.py [requests]

Turns on STRATA_DECODE_TIMING=1 (one line per request, in the engine log), sends a few requests of different
lengths, then prints the breakdown and — the number #1913 is about — the host cost per expert entry. The
reporter there saw that number jump 3-5x mid-session and stay there while entries/window and GPU wait did not
move; if ours does the same, the pool's memory placement is the suspect. Restores the config afterwards.
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
LOG = ROOT / "scratch" / "configs" / "strata-iq2_xs.log"
NUM = re.compile(r"([-\d.]+)")

PROMPTS = [
    "What is 17*23? Just the number.",
    "Name three primary colours.",
    "Write a haiku about a graphics card.",
    "Explain in two sentences why a cache helps a database.",
    "What is the capital of Australia? Just the city.",
]


def set_timing(on: bool) -> None:
    c = json.loads(CFG.read_text(encoding="utf-8-sig"))
    if on:
        c["env"]["STRATA_DECODE_TIMING"] = "1"
    else:
        c["env"].pop("STRATA_DECODE_TIMING", None)
    CFG.write_text(json.dumps(c, indent=1), encoding="utf-8")


def restart() -> None:
    subprocess.run(["cmd", "/c", "stop-server.bat"], cwd=ROOT, capture_output=True, stdin=subprocess.DEVNULL)
    time.sleep(2)
    log = open(ROOT / "logs" / "server-dectiming.log", "w", encoding="utf-8")
    subprocess.Popen(["cmd", "/c", "run-iq2_xs.bat"], cwd=ROOT, stdout=log, stderr=subprocess.STDOUT,
                     stdin=subprocess.DEVNULL)
    for _ in range(60):
        try:
            with urllib.request.urlopen("http://127.0.0.1:8080/health", timeout=4) as r:
                if b'"loaded": true' in r.read():
                    return
        except Exception:
            pass
        time.sleep(5)
    raise SystemExit("  server did not come up")


def ask(q: str, n: int) -> None:
    body = json.dumps({"model": "local", "messages": [{"role": "user", "content": q}],
                       "max_tokens": 160}).encode()
    req = urllib.request.Request("http://127.0.0.1:8080/v1/chat/completions", data=body,
                                headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=900) as r:
        json.load(r)


def main():
    n = int(sys.argv[1]) if len(sys.argv) > 1 else 8
    set_timing(True)
    restart()
    before = len(LOG.read_text(encoding="utf-8", errors="replace").splitlines())
    for i in range(n):
        ask(PROMPTS[i % len(PROMPTS)] + (f"  (request {i + 1})" if i >= len(PROMPTS) else ""), 160)
    time.sleep(2)
    tail = LOG.read_text(encoding="utf-8", errors="replace").splitlines()[before:]
    lines = [l for l in tail if "decode" in l.lower() and re.search(r"\d+\.\d+", l)]
    print(f"  timing lines: {len(lines)}")
    for l in lines[:14]:
        print("   ", l[:150])
    print("\n  === host per entry (the #1913 number: ms_host / entries) ===")
    for l in lines[:14]:
        nums = dict(re.findall(r"(host|entries|pool|wait|pcie|hits|misses)\s*[=:]?\s*([-\d.]+)", l))
        try:
            h, e = float(nums["host"]), float(nums.get("entries", 0))
            if e:
                print(f"     host {h:8.2f} ms / entries {e:6.0f} = {h / e:6.2f} ms per entry")
        except (KeyError, ValueError, ZeroDivisionError):
            continue
    set_timing(False)
    restart()
    print("\n  timing flag removed, server restored")


if __name__ == "__main__":
    main()
