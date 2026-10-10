#!/usr/bin/env python3
"""Run the engine CLI on a real tokenized prompt with --stats, for the prefill breakdown.

    python prefill-stats.py [tokens-file] [extra engine flags...]

Uses this install's config (exe, args, env, cwd - what serve/server.py does) plus --tokens-file and --stats.
Stop the server first: the engine needs the GPU. Prints the stage/breakdown lines and saves everything to
logs/prefill-stats.log.
"""
import json
import os
import pathlib
import re
import subprocess
import sys
import time

ROOT = pathlib.Path(r"D:\llm-dev\strata")
CFG = ROOT / "scratch/configs/strata-iq2_xs.json"
tokens = sys.argv[1] if len(sys.argv) > 1 else "logs/prompt-ids.txt"
extra = sys.argv[2:]


def main():
    cfg = json.loads(CFG.read_text(encoding="utf-8-sig"))
    env = dict(os.environ)
    env.update({k: str(v) for k, v in (cfg.get("env") or {}).items()})
    libs = [str(p) for p in cfg.get("lib_dirs", [])]
    if libs:
        env["PATH"] = os.pathsep.join(libs + [env.get("PATH", "")])
    cmd = [cfg["exe"], *cfg["args"], "--tokens-file", str(ROOT / tokens), "--stats", *extra]
    print("engine:", " ".join(cmd[:8]), "...", "--tokens-file", tokens, "--stats", *extra, flush=True)
    t0 = time.time()
    p = subprocess.run(cmd, cwd=cfg.get("cwd") or str(ROOT), env=env, capture_output=True, text=True)
    text = (p.stderr or "") + "\n" + (p.stdout or "")
    out = ROOT / "logs" / "prefill-stats.log"
    out.write_text(text, encoding="utf-8", errors="replace")
    print(f"exit {p.returncode} after {time.time() - t0:.0f}s -> {out}\n")
    keep = re.compile(r"prefill|stage|streamed|DMA|PLE|resident|ms\b|tok/s|expert|PCIe|pool|read", re.I)
    for line in text.splitlines():
        s = line.strip()
        if s and keep.search(s) and "Lt " not in s and len(s) < 200:
            print(" |", s)


if __name__ == "__main__":
    main()
