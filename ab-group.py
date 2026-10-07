#!/usr/bin/env python3
"""A/B a list of engine variants on the same prompt, one engine run each, GPU to itself.

    python ab-group.py                 # runs the built-in variant list

Each variant is (label, exe path, extra CLI args, extra env).  Parses the engine's own prefill and decode lines so
the comparison is in its numbers, not in wall clock.  Stops the server first (the engine needs the GPU and the RAM
the budget is clamped against).
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

VARIANTS_FILE = pathlib.Path(sys.argv[1]) if len(sys.argv) > 1 else ROOT / "logs" / "ab-variants.json"
if VARIANTS_FILE.exists():          # data-driven: [(label, exe, [args], [[env,val],...]), ...]
    VARIANTS = [(v[0], v[1], v[2], [tuple(e) for e in v[3]]) for v in json.loads(VARIANTS_FILE.read_text())]
else:
    VARIANTS = [
        ("control",                "logs/binaries/strata-base.exe",  [], []),
        ("control+unbuf=1",        "logs/binaries/strata-base.exe",  [], [("STRATA_UNBUFFERED_LOAD", "1")]),
    ]


def stop_server():
    subprocess.run(["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-File",
                    str(ROOT / "stop-strata.ps1")], cwd=str(ROOT), capture_output=True, text=True)


def run(label, exe, extra_args, extra_env):
    cfg = json.loads(CFG.read_text(encoding="utf-8-sig"))
    cfg["exe"] = str(ROOT / exe)
    env = dict(os.environ)
    env.update({k: str(v) for k, v in (cfg.get("env") or {}).items()})
    for k, v in extra_env:
        env[k] = v
    libs = [str(p) for p in cfg.get("lib_dirs", [])]
    if libs:
        env["PATH"] = os.pathsep.join(libs + [env.get("PATH", "")])
    cmd = [cfg["exe"], *cfg["args"], *extra_args, "--tokens-file", TOKENS, "--stats"]
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
    (ROOT / "logs" / f"ab-{label.replace(' ', '_').replace('+','').replace('(','').replace(')','')}.log").write_text(
        text, encoding="utf-8", errors="replace")
    pre = re.search(r"prefill (\d+) tokens in (\d+) chunks, ([\d.]+) ms \(([\d.]+) tok/s\); experts streamed (\d+)"
                    r" \((\d+) by DMA, host ([\d.]+) ms\), resident (\d+)", text)
    dec = re.search(r"decode\s+(\d+) tokens in ([\d.]+) ms\s+->\s+([\d.]+) tok/s", text)
    unb = "unbuffered" in text and "reads unbuffered" in text
    out = {"label": label, "exit": p.returncode, "wall": time.time() - t0}
    if pre:
        _, toks, chunks, ms, rate, streamed, dma, host_ms, resident = (None, *pre.groups())
        tot = int(streamed) + int(resident)
        out.update(prefill=float(rate), host_s=float(host_ms) / 1000, from_files=100 * int(streamed) / max(tot, 1))
    if dec:
        out.update(decode=float(dec.group(3)))
    out.update(unbuffered=unb, disk_peak=max(reads) if reads else 0)
    return out


if __name__ == "__main__":
    stop_server()
    rows = []
    for label, exe, extra_args, extra_env in VARIANTS:
        if not (ROOT / exe).exists():
            print(f"  {label}: MISSING {exe}", flush=True)
            continue
        r = run(label, exe, extra_args, extra_env)
        rows.append(r)
        print(f"  {label:<24} prefill {r.get('prefill', float('nan')):>7.1f} tok/s | decode "
              f"{r.get('decode', float('nan')):>5.1f} tok/s | host {r.get('host_s', 0):>5.1f} s | "
              f"{r.get('from_files', 0):>3.0f}% from files | disk {r.get('disk_peak', 0):>5.0f} MB/s | "
              f"unbuffered={r.get('unbuffered')}", flush=True)
    (ROOT / "logs" / "ab-group.json").write_text(json.dumps(rows, indent=1))
    print("\nwrote logs/ab-group.json")
