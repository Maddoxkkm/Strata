#!/usr/bin/env python3
"""Run the engine's own measurement modes with this install's configuration.

    .venv/Scripts/python.exe run-engine-measure.py --gpu-only-full
    .venv/Scripts/python.exe run-engine-measure.py --gpu-stages
    .venv/Scripts/python.exe run-engine-measure.py --stats

Starts engine/strata.exe with the args, env and working directory from strata-iq2_xs.json (what serve/server.py
does), plus the measurement flag, and prints what it says. Stop the server first: these need the GPU to itself.
"""
import json
import os
import pathlib
import subprocess
import sys
import time

ROOT = pathlib.Path(r"D:\llm-dev\strata")
CFG = ROOT / "strata-iq2_xs.json"


def main():
    flag = sys.argv[1] if len(sys.argv) > 1 else "--gpu-only-full"
    cfg = json.loads(CFG.read_text(encoding="utf-8-sig"))
    env = dict(os.environ)
    env.update({k: str(v) for k, v in (cfg.get("env") or {}).items()})
    libs = [str(p) for p in cfg.get("lib_dirs", [])]
    if libs:
        env["PATH"] = os.pathsep.join(libs + [env.get("PATH", "")])
    cmd = [cfg["exe"], *cfg["args"], flag]
    print("running:", " ".join(cmd[:6]), "...", flag)
    print("env:", {k: v for k, v in cfg.get("env", {}).items()})
    t0 = time.time()
    p = subprocess.run(cmd, cwd=cfg.get("cwd") or str(ROOT), env=env, capture_output=True, text=True)
    print(f"--- exit {p.returncode} after {time.time() - t0:.1f}s ---")
    out = (p.stderr or "") + (p.stdout or "")
    for line in out.splitlines():
        if "strata" in line or "floor" in line.lower() or "tok" in line.lower() or "ms" in line:
            print(line)


if __name__ == "__main__":
    main()
