#!/usr/bin/env python3
"""Where prefill and decode time actually goes, on the current build.

    python io-profile.py

Runs the configured engine in CLI mode with --stats (the only mode that prints the phase split), twice: a
4K-token prefill and a decode-heavy run. While each runs, samples the physical disk's read throughput, so the
engine's own numbers can be read against what the drive was doing.
"""
import json
import pathlib
import re
import subprocess
import sys
import threading
import time

ROOT = pathlib.Path(r"D:\llm-dev\strata")
CFG = ROOT / "strata-iq2_xs.json"
LOG = ROOT / "strata-iq2_xs.log"


class DiskSampler(threading.Thread):
    def __init__(self, interval=1.0):
        super().__init__(daemon=True)
        self.interval = interval
        self.samples = []
        self._stop = threading.Event()

    def run(self):
        cmd = ["powershell", "-NoProfile", "-Command",
               "Get-Counter '\\PhysicalDisk(_Total)\\Disk Read Bytes/sec' -SampleInterval 1 -MaxSamples 300 | "
               "ForEach-Object { $_.CounterSamples.CookedValue }"]
        p = subprocess.Popen(cmd, stdout=subprocess.PIPE, text=True)
        while not self._stop.is_set():
            line = p.stdout.readline()
            if not line:
                break
            try:
                self.samples.append(float(line.strip()))
            except ValueError:
                pass
        p.terminate()

    def stop(self):
        self._stop.set()


def run_engine(label, tokens_file, extra=()):
    cfg = json.loads(CFG.read_text(encoding="utf-8-sig"))
    cmd = [cfg["exe"], *cfg["args"], *extra, "--tokens-file", str(ROOT / tokens_file), "--stats"]
    env = dict(**{k: str(v) for k, v in (cfg.get("env") or {}).items()})
    import os
    full = dict(os.environ)
    full.update(env)
    for d in cfg.get("lib_dirs", []):
        full["PATH"] = str(d) + os.pathsep + full.get("PATH", "")

    print(f"\n=== {label} ===", flush=True)
    ds = DiskSampler()
    ds.start()
    t0 = time.time()
    p = subprocess.run(cmd, capture_output=True, text=True, timeout=1800, cwd=str(ROOT), env=full)
    wall = time.time() - t0
    time.sleep(1)
    ds.stop()

    out = (p.stdout or "") + (p.stderr or "")
    keys = ("prefill", "experts streamed", "host", "DMA", "resident", "pool", "mtp", "MTP", "decode",
            "profile rank", "RAM budget", "blob", "GB/s", "reading the prompt", "generated", "tok/s")
    for line in out.splitlines():
        if any(k in line for k in keys):
            print("   " + line.strip()[:200])
    rd = [s for s in ds.samples if s > 0]
    if rd:
        print(f"   [disk] read {min(rd)/1e6:.0f}-{max(rd)/1e6:.0f} MB/s during the run, "
              f"avg {sum(rd)/len(rd)/1e6:.0f} MB/s over {len(rd)} samples")
    print(f"   [wall] {wall:.1f} s")
    return out


def main():
    run_engine("PREFILL 4K prompt", "logs/prompt-ids.txt")
    run_engine("SHORT prompt (chat-sized)", "logs/prompt-short-ids.txt")
    print("\n--- server-side comparison for the same shapes ---")
    lines = LOG.read_text(encoding="utf-8", errors="replace").splitlines()[-400:]
    for l in lines[-40:]:
        if "prompt " in l and "read in" in l:
            print("   " + l.strip()[:170])


if __name__ == "__main__":
    main()
