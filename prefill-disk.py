#!/usr/bin/env python3
"""Run the engine CLI prefill twice on the same token file while sampling disk read throughput.

    python prefill-disk.py

Run 1 follows a fresh engine start (expert pages likely cold); run 2 repeats immediately, so the OS page cache
should hold whatever the first run read.  Disk read MB/s is sampled once a second from psutil, so the prefill
window can be matched against the engine's own "experts streamed ... host X ms" line.  Prints both runs' summary
lines and the sampled disk rate.
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
CFG = ROOT / "strata-iq2_xs.json"
TOKENS = str(ROOT / "logs" / "prompt-ids.txt")


def run_engine(tag):
    cfg = json.loads(CFG.read_text(encoding="utf-8-sig"))
    env = dict(os.environ)
    env.update({k: str(v) for k, v in (cfg.get("env") or {}).items()})
    libs = [str(p) for p in cfg.get("lib_dirs", [])]
    if libs:
        env["PATH"] = os.pathsep.join(libs + [env.get("PATH", "")])
    cmd = [cfg["exe"], *cfg["args"], "--tokens-file", TOKENS, "--stats"]
    samples = []
    stop = threading.Event()

    def sampler():
        try:
            import psutil
        except ImportError:
            return
        prev = psutil.disk_io_counters()
        t0 = time.time()
        while not stop.is_set():
            time.sleep(1.0)
            cur = psutil.disk_io_counters()
            dt = time.time() - t0
            if dt <= 0:
                continue
            samples.append(((cur.read_bytes - prev.read_bytes) / dt / 2**20,
                            (cur.write_bytes - prev.write_bytes) / dt / 2**20))
            prev, t0 = cur, time.time()

    th = threading.Thread(target=sampler, daemon=True)
    th.start()
    t0 = time.time()
    p = subprocess.run(cmd, cwd=cfg.get("cwd") or str(ROOT), env=env, capture_output=True, text=True)
    stop.set()
    text = (p.stderr or "") + "\n" + (p.stdout or "")
    (ROOT / "logs" / f"prefill-disk-{tag}.log").write_text(text, encoding="utf-8", errors="replace")
    print(f"\n=== {tag}: exit {p.returncode} after {time.time() - t0:.0f}s ===", flush=True)
    for line in text.splitlines():
        if re.search(r"prefill \d|experts streamed|expert tiers|prompt copies|prefill +4089|per token", line):
            print("  |", line.strip()[:190])
    if samples:
        reads = [s[0] for s in samples]
        top = sorted(reads, reverse=True)[:8]
        print(f"  disk reads: peak {max(reads):.0f} MB/s, top-8 {[round(x) for x in top]}, "
              f"mean-over-run {sum(reads)/len(reads):.0f} MB/s ({len(samples)} samples)")


run_engine("run1")
run_engine("run2-warm")
