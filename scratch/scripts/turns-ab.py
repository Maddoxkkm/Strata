#!/usr/bin/env python3
"""The measurement #1838 actually needs: a growing conversation, per turn.

    python scratch/scripts/turns-ab.py <exe-a> <exe-b>

#1838 makes the resident RAM copy follow the conversation, so a single cold prompt cannot show it - the
effect is in the *later* turns of a session (fewer misses, fewer re-reads). This sends six requests whose
prompt grows by a fixed block each turn (so the conversation cache can reuse the prefix), one engine restart
per binary, and prints the engine's own accounting per turn: prompt / reused / read ms and rate / generated /
draft acceptance / expert-cache hit. Also answers issue #1906's question for this box (does reuse happen).
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
SERVE = re.compile(r"prompt (\d+) tokens = (\d+) reused \+ (\d+) read in (\d+) ms \(([\d.]+) tok/s\)"
                   r"(?:, (\d+) generated in (\d+) ms \(([\d.]+) tok/s\))?")
HIT = re.compile(r"expert cache ([\d.]+)% hit")

BLOCK = ("The maintenance window is scheduled for the third Tuesday of each quarter, after the nightly "
         "replication has finished and before the morning batch jobs begin. Operators confirm the replica lag "
         "is under sixty seconds, drain the queue, and verify the failover path answers within budget. ")


def set_exe(exe: str) -> None:
    c = json.loads(CFG.read_text(encoding="utf-8-sig"))
    c["exe"] = exe
    CFG.write_text(json.dumps(c, indent=1), encoding="utf-8")


def restart() -> None:
    subprocess.run(["cmd", "/c", "stop-server.bat"], cwd=ROOT, capture_output=True, stdin=subprocess.DEVNULL)
    time.sleep(2)
    log = open(ROOT / "logs" / "server-turns.log", "w", encoding="utf-8")
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


def turn(prompt: str) -> None:
    body = json.dumps({"model": "local", "messages": [{"role": "user", "content": prompt}],
                       "max_tokens": 64}).encode()
    req = urllib.request.Request("http://127.0.0.1:8080/v1/chat/completions", data=body,
                                headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=900) as r:
        json.load(r)


def run(exe: str, turns: int = 6) -> list[tuple]:
    set_exe(exe)
    restart()
    before = len(LOG.read_text(encoding="utf-8", errors="replace").splitlines())
    for i in range(1, turns + 1):
        turn((BLOCK * (i * 4)).strip() + f"\n\nSummarise the above in one word. (turn {i})")
    time.sleep(2)
    lines = LOG.read_text(encoding="utf-8", errors="replace").splitlines()[before:]
    out = []
    for l in lines:
        m = SERVE.search(l)
        if m:
            h = HIT.search(l)
            out.append((int(m.group(1)), int(m.group(2)), int(m.group(3)), int(m.group(4)), float(m.group(5)),
                        h.group(1) if h else "?"))
    return out


def main():
    exes = sys.argv[1:] or ["logs/binaries/strata-142-b.exe", "logs/binaries/strata-142-all.exe"]
    for exe in exes:
        rows = run(exe)
        print(f"\n  === {pathlib.Path(exe).name} ===")
        print(f"  {'turn':<5}{'prompt':>9}{'reused':>9}{'read':>8}{'ms':>8}{'tok/s':>9}{'hit%':>7}")
        for i, (p, r, rd, ms, rate, hit) in enumerate(rows[:8], 1):
            print(f"  {i:<5}{p:>9}{r:>9}{rd:>8}{ms:>8}{rate:>9.0f}{hit:>7}")
        if len(rows) > 1:
            first, last = rows[0], rows[-1]
            print(f"  first turn {first[4]:.0f} tok/s -> last turn {last[4]:.0f} tok/s; "
                  f"reuse {first[1]}/{first[0]} -> {last[1]}/{last[0]}")


if __name__ == "__main__":
    main()
