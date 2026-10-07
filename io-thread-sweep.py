#!/usr/bin/env python3
"""Sweep STRATA_IO_THREADS (the stager's issuing threads) and measure the effect on prefill.

    python io-thread-sweep.py 4 8 16 32

One engine run per value, same tokenized prompt, same config otherwise. Reports the engine's own prefill tok/s and
host staging ms, plus the peak disk read rate sampled during the run - if the peak rises with the thread count,
the read path was under-queued; if it stays ~0.9 GB/s, the limiter is inside the stager's wait/serialization.
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
VALUES = [int(a) for a in sys.argv[1:]] or [4, 8, 16, 32]


def run(threads):
    cfg = json.loads(CFG.read_text(encoding="utf-8-sig"))
    env = dict(os.environ)
    env.update({k: str(v) for k, v in (cfg.get("env") or {}).items()})
    env["STRATA_IO_THREADS"] = str(threads)
    libs = [str(p) for p in cfg.get("lib_dirs", [])]
    if libs:
        env["PATH"] = os.pathsep.join(libs + [env.get("PATH", "")])
    cmd = [cfg["exe"], *cfg["args"], "--tokens-file", TOKENS, "--stats"]
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

    th = threading.Thread(target=sample, daemon=True)
    th.start()
    p = subprocess.run(cmd, cwd=cfg.get("cwd") or str(ROOT), env=env, capture_output=True, text=True)
    stop.set()
    text = (p.stderr or "") + "\n" + (p.stdout or "")
    (ROOT / "logs" / f"io-threads-{threads}.log").write_text(text, encoding="utf-8", errors="replace")
    pre = re.search(r"prefill (\d+) tokens in (\d+) chunks, ([\d.]+) ms \(([\d.]+) tok/s\); experts streamed (\d+) "
                    r"\((\d+) by DMA, host ([\d.]+) ms\), resident (\d+)", text)
    pool = re.search(r"pool multi\s+.*?([\d.]+) GB/s over the rows phases", text)
    peak = max(reads) if reads else 0
    sustained = sorted(reads)[len(reads) // 2] if reads else 0
    if pre:
        _, toks, _, rate, streamed, dma, host_ms, resident = pre.groups()
        print(f"  IO_THREADS={threads:<3} prefill {rate} tok/s   host {float(host_ms)/1000:.1f} s   "
              f"streamed {streamed} ({dma} DMA)   disk peak {peak:.0f} MB/s, median {sustained:.0f} MB/s"
              + (f"   pool {pool.group(1)} GB/s" if pool else ""), flush=True)
    else:
        print(f"  IO_THREADS={threads:<3} no prefill line (exit {p.returncode})", flush=True)


print(f"sweeping STRATA_IO_THREADS {VALUES} (one engine run each)")
for v in VALUES:
    run(v)
