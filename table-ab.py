#!/usr/bin/env python3
"""A/B the hipBLASLt tuning table with the engine's own measurement run.

    python table-ab.py <label>

Starts engine/strata.exe with this install's config (exe, args, env, cwd - what serve/server.py does) plus
`--stats`, captures the FULL stderr/stdout to logs/table-ab-<label>.log, and summarises:
  - the tuning-table load line (rows, arch, hipBLASLt version)
  - every `Lt fallback` line: how many launches fell back and which (dtype, T, N, K, ldy) geometries were missing
  - the engine's own prefill/decode numbers

Stop the server first: this needs the GPU to itself.
"""
import collections
import json
import os
import pathlib
import re
import subprocess
import sys
import time

ROOT = pathlib.Path(r"D:\llm-dev\strata")
CFG = ROOT / "strata-iq2_xs.json"
LABEL = sys.argv[1] if len(sys.argv) > 1 else "run"


def main():
    cfg = json.loads(CFG.read_text(encoding="utf-8-sig"))
    env = dict(os.environ)
    env.update({k: str(v) for k, v in (cfg.get("env") or {}).items()})
    env["STRATA_HIPBLASLT_VERBOSE"] = "1"
    libs = [str(p) for p in cfg.get("lib_dirs", [])]
    if libs:
        env["PATH"] = os.pathsep.join(libs + [env.get("PATH", "")])
    cmd = [cfg["exe"], *cfg["args"], "--stats"]
    logs = ROOT / "logs"
    logs.mkdir(exist_ok=True)
    out_path = logs / f"table-ab-{LABEL}.log"
    print(f"[{LABEL}] running engine --stats (this takes a minute) ...", flush=True)
    t0 = time.time()
    p = subprocess.run(cmd, cwd=cfg.get("cwd") or str(ROOT), env=env, capture_output=True, text=True)
    text = (p.stderr or "") + "\n" + (p.stdout or "")
    out_path.write_text(text, encoding="utf-8", errors="replace")
    print(f"[{LABEL}] exit {p.returncode} after {time.time() - t0:.0f}s -> {out_path}")

    for line in text.splitlines():
        if "tuning enabled" in line or "using hipBLASEx" in line:
            print(f"  TABLE: {line.strip()}")
    fallbacks = [l for l in text.splitlines() if "Lt fallback" in l]
    shapes = collections.Counter()
    for l in fallbacks:
        m = re.search(r"dtype=(\w+) T=(\d+) N=(\d+) K=(\d+) ldy=(\d+)", l)
        if m:
            shapes[(m.group(1), m.group(3), m.group(4), m.group(5))] += 1
    print(f"  FALLBACKS: {len(fallbacks)} launches")
    for (dt, n, k, ldy), c in shapes.most_common(12):
        print(f"    geometry dtype={dt} N={n} K={k} ldy={ldy}: {c} launch(es)  -> row needed: {dt} {n} {k} {ldy} T <bucket> <id>")
    ts = re.findall(r"(\d[\d,]*)\s*tokens?.*?([\d.]+)\s*ms.*?\(([\d.]+)\s*tok/s\)", text)
    for a, b, c in ts[:6]:
        print(f"  ENGINE: {a} tokens in {b} ms -> {c} tok/s")
    for line in text.splitlines():
        if re.search(r"prefill|decode|tok/s", line) and "Lt fallback" not in line:
            s = line.strip()
            if s and len(s) < 160:
                print(f"  | {s}")


if __name__ == "__main__":
    main()
