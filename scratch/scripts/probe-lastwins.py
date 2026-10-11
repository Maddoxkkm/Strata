#!/usr/bin/env python3
"""Does a --pack/--native given LATER on the command line override the config's?

That decides whether both models can be measured in one interleaved A/B run (the harness appends an arm's
extra args after the config's). Probe: append a bogus --pack last; if the engine fails, the last wins.
"""
import json
import os
import pathlib
import subprocess

ROOT = pathlib.Path(r"D:\llm-dev\strata")
c = json.loads((ROOT / "scratch/configs/strata-iq2_xs.json").read_text(encoding="utf-8-sig"))
exe = str(ROOT / c["exe"].split("/", 1)[-1].replace("logs", "logs", 1))
exe = str(ROOT / "logs" / "binaries" / c["exe"].rsplit("/", 1)[-1])
args = [exe] + c["args"] + ["--pack", r"D:\does-not-exist-pack",
                            "--tokens-file", str(ROOT / "logs" / "prompt-short-ids.txt"),
                            "--max-tokens", "2"]
env = {**os.environ, **{k: str(v) for k, v in c.get("env", {}).items()}}
print("  running:", " ".join(a if " " not in a else f'"{a}"' for a in args[-6:]))
r = subprocess.run(args, cwd=str(ROOT), capture_output=True, text=True, timeout=240, env=env)
out = (r.stdout or "") + (r.stderr or "")
hits = [l for l in out.splitlines() if any(k in l.lower() for k in
        ("pack", "native", "error", "cannot", "no such", "does-not-exist", "reading the prompt"))]
for l in hits[:8]:
    print("  |", l[:150])
print("  exit:", r.returncode)
print("  verdict:", "LAST WINS (bogus pack rejected)" if r.returncode != 0 and any("does-not-exist" in l for l in hits)
      else "inconclusive - read the lines above")
