#!/usr/bin/env python3
"""Run one engine prefill per env setting and compare.  Reusable A/B for the read path.

    python env-ab.py "STRATA_UNBUFFERED_LOAD=0" "STRATA_UNBUFFERED_LOAD=1"

Each argument is VAR=value (or bare VAR to unset).  Reports the engine's own prefill tok/s, host staging ms and
streamed/DMA counts, the peak/median disk read rate sampled during the run, and any line the engine prints about
how it chose the read mode - so a change can be attributed rather than guessed.
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
SETTINGS = sys.argv[1:] or ["STRATA_UNBUFFERED_LOAD=0", "STRATA_UNBUFFERED_LOAD=1"]


def run(setting):
    cfg = json.loads(CFG.read_text(encoding="utf-8-sig"))
    env = dict(os.environ)
    env.update({k: str(v) for k, v in (cfg.get("env") or {}).items()})
    key, _, val = setting.partition("=")
    if val:
        env[key] = val
    else:
        env.pop(key, None)
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

    threading.Thread(target=sample, daemon=True).start()
    t0 = time.time()
    p = subprocess.run(cmd, cwd=cfg.get("cwd") or str(ROOT), env=env, capture_output=True, text=True)
    stop.set()
    text = (p.stderr or "") + "\n" + (p.stdout or "")
    tag = setting.replace("=", "-").replace("\\", "").replace("/", "")
    (ROOT / "logs" / f"env-ab-{tag}.log").write_text(text, encoding="utf-8", errors="replace")
    pre = re.search(r"prefill (\d+) tokens in (\d+) chunks, ([\d.]+) ms \(([\d.]+) tok/s\); experts streamed (\d+)"
                    r" \((\d+) by DMA, host ([\d.]+) ms\), resident (\d+)", text)
    print(f"\n--- {setting} (run {time.time()-t0:.0f}s) ---", flush=True)
    for line in text.splitlines():
        if re.search(r"experts via|unbuffered|file cache|read_ahead|O_DIRECT|no-buffer|experts of the|the file tier",
                     line, re.I):
            print("   mode:", line.strip()[:170])
    if pre:
        _, toks, chunks, ms, rate, streamed, dma, host_ms, resident = (None, *pre.groups())
        med = sorted(reads)[len(reads) // 2] if reads else 0
        print(f"   prefill {rate} tok/s | host {float(host_ms)/1000:.1f} s | streamed {streamed} ({dma} DMA), "
              f"resident {resident}")
        print(f"   disk peak {max(reads) if reads else 0:.0f} MB/s, median {med:.0f} MB/s")
    else:
        print(f"   no prefill line (exit {p.returncode})")


print(f"env A/B over: {SETTINGS}")
for s in SETTINGS:
    run(s)
