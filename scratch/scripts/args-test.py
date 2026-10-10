#!/usr/bin/env python3
"""Run the engine CLI prefill with extra flags appended, and report the prefill split.

    python args-test.py --resident-budget-gib 18

Same config/prompt as every other measurement here (logs/prompt-ids.txt), so numbers compare directly with the
68%/-from-files, ~180 tok/s baseline. Prints the read-mode lines the engine emits, so a change is attributed.
"""
import json
import os
import pathlib
import re
import subprocess
import sys
import threading
import time

ROOT = pathlib.Path(r"D:\llm-dev\strata")
CFG = ROOT / "scratch/configs/strata-iq2_xs.json"
TOKENS = str(ROOT / "logs" / "prompt-ids.txt")
EXTRA = sys.argv[1:]

cfg = json.loads(CFG.read_text(encoding="utf-8-sig"))
if os.environ.get("STRATA_TEST_EXE"):        # run a locally built engine (build-hip-win/strata.exe) instead
    cfg["exe"] = os.environ["STRATA_TEST_EXE"]
env = dict(os.environ)
env.update({k: str(v) for k, v in (cfg.get("env") or {}).items()})
libs = [str(p) for p in cfg.get("lib_dirs", [])]
if libs:
    env["PATH"] = os.pathsep.join(libs + [env.get("PATH", "")])
cmd = [cfg["exe"], *cfg["args"], *EXTRA, "--tokens-file", TOKENS, "--stats"]
tag = "-".join(EXTRA).replace("--", "").replace("/", "") or "baseline"
reads = []
stop = threading.Event()


def sample():
    import psutil
    prev = psutil.disk_io_counters()
    t_prev = time.time()
    while not stop.is_set():
        time.sleep(0.5)
        cur = psutil.disk_io_counters()
        dt = time.time() - t_prev
        if dt > 0:
            reads.append((cur.read_bytes - prev.read_bytes) / dt / 2**20)
        prev, t_prev = cur, time.time()


threading.Thread(target=sample, daemon=True).start()
t0 = time.time()
p = subprocess.run(cmd, cwd=cfg.get("cwd") or str(ROOT), env=env, capture_output=True, text=True)
stop.set()
text = (p.stderr or "") + "\n" + (p.stdout or "")
(ROOT / "logs" / f"args-{tag}.log").write_text(text, encoding="utf-8", errors="replace")

print(f"--- extra flags: {' '.join(EXTRA) or '(none)'} | exit {p.returncode} after {time.time()-t0:.0f}s ---")
for line in text.splitlines():
    if re.search(r"experts via|unbuffered|file cache|buffer|budget|complement|resident-budget|memory", line, re.I):
        print("   mode:", line.strip()[:180])
for line in text.splitlines():                      # the engine's own decode / per-token lines
    if re.search(r"^\s*(decode|prefill|per token|verify window|pool multi|mtp)\s", line):
        print("   perf:", line.strip()[:170])
pre = re.search(r"prefill (\d+) tokens in (\d+) chunks, ([\d.]+) ms \(([\d.]+) tok/s\); experts streamed (\d+)"
                r" \((\d+) by DMA, host ([\d.]+) ms\), resident (\d+)", text)
if pre:
    _, toks, chunks, ms, rate, streamed, dma, host_ms, resident = (None, *pre.groups())
    tot = int(streamed) + int(resident)
    print(f"   prefill {rate} tok/s | host {float(host_ms)/1000:.1f} s | streamed {streamed} of {tot} "
          f"({100*int(streamed)/max(tot,1):.0f}% from files), resident {resident}")
    print(f"   disk peak {max(reads) if reads else 0:.0f} MB/s, median {sorted(reads)[len(reads)//2] if reads else 0:.0f} MB/s")
else:
    print("   no prefill line")
