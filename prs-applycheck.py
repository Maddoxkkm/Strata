#!/usr/bin/env python3
"""For every open Tier A/B PR: make sure its diff is cached, check it applies to this tree, and pull out the
knobs (env vars / flags) that switch it on - so each can be tested one at a time after a single build.

    python prs-applycheck.py

`git apply --check` does not touch the working tree, so this is safe to run while a build is in progress.
"""
import json
import os
import pathlib
import re
import subprocess
import sys
import urllib.request

ROOT = pathlib.Path(r"D:\llm-dev\strata")
TIER_A = [1323, 1282, 1283, 1332, 1345]
TIER_B = [1297, 1298, 1181, 1184, 1151, 1324, 1232, 1231, 1262, 1340, 1316, 1305, 1325, 1265, 1266,
          1190, 1237, 1123, 1167]
NEW = [1368, 1367, 1370]
prs = {p["number"]: p for p in json.load(open(ROOT / "prs-open.json"))}


def fetch(n):
    path = ROOT / "prs" / f"{n}.diff"
    if not path.exists():
        req = urllib.request.Request(f"https://github.com/Niko1221/Strata/pull/{n}.diff",
                                     headers={"User-Agent": "probe"})
        with urllib.request.urlopen(req, timeout=90) as r:
            path.write_bytes(r.read())
    return path


def knobs(text):
    envs = sorted(set(re.findall(r"\bSTRATA_[A-Z0-9_]{2,}", text)))
    flags = sorted(set(re.findall(r'"?(--[a-z][a-z0-9-]{3,})', text)))
    return envs[:6], flags[:6]


print(f"{'PR':<7} {'tier':<5} {'applies':<8} {'files':<6} platforms          knobs")
for tier, lst in (("A", TIER_A), ("B", TIER_B), ("new", NEW)):
    for n in lst:
        try:
            d = fetch(n)
        except Exception as e:
            print(f"#{n:<6} {tier:<5} fetch failed: {e}")
            continue
        text = d.read_text(encoding="utf-8", errors="replace")
        chk = subprocess.run(["git", "apply", "--check", str(d)], cwd=str(ROOT), capture_output=True, text=True)
        ok = "yes" if chk.returncode == 0 else "NO"
        files = len([l for l in text.splitlines() if l.startswith("+++ b/")])
        added = "\n".join(l[1:] for l in text.splitlines() if l.startswith("+") and not l.startswith("+++"))
        hip = len(re.findall(r"\bhip\b|hipBLASLt|rocBLAS|gfx11|amd", added, re.I))
        cuda = len(re.findall(r"\bcuda\b|cudaHostAlloc|nvml|sm_\d|mma\.sync|wmma::|cp\.async", added, re.I))
        envs, flags = knobs(added)
        plat = f"hip {hip:<3} cuda {cuda:<3}"
        print(f"#{n:<6} {tier:<5} {ok:<8} {files:<6} {plat} {','.join(envs)} | {','.join(flags)}")
        if ok == "NO":
            print("        ", (chk.stderr or "").strip().splitlines()[0][:120] if chk.stderr else "")
