#!/usr/bin/env python3
"""Probe the candidate PRs' real diffs: what they touch, what knobs they add, what they claim, and whether the
change lands on HIP or only on CUDA.

    python prs-probe.py 1289 1297 1323 ...

Saves each diff to prs/<n>.diff and prints a compact per-PR summary:
  - base sha vs our HEAD (82f46a8): does it apply here as-is?
  - files touched, grouped by directory
  - new env vars / flags and the STRATA_* knobs it introduces
  - every percentage/ratio the added lines mention (the author's own claims)
  - whether the added code is HIP-reachable, CUDA-only, or neither
"""
import json
import os
import re
import sys
import urllib.request

HEAD = "82f46a8"
CANDIDATES = [int(a) for a in sys.argv[1:]] or [1289, 1297, 1296, 1298, 1151, 1184, 1209, 1323, 1282, 1283,
                                                 1181, 1133, 1324, 1232, 1109, 1281, 1237, 1240, 1287, 1345,
                                                 1332, 1265, 1354, 1179, 1190, 1264]
prs = {p["number"]: p for p in json.load(open("prs-open.json"))}
os.makedirs("prs", exist_ok=True)


def fetch(n):
    path = f"prs/{n}.diff"
    if not os.path.exists(path):
        req = urllib.request.Request(f"https://github.com/Niko1221/Strata/pull/{n}.diff",
                                     headers={"User-Agent": "probe"})
        with urllib.request.urlopen(req, timeout=90) as r:
            open(path, "wb").write(r.read())
    return open(path, encoding="utf-8", errors="replace").read()


for n in CANDIDATES:
    p = prs.get(n)
    if not p:
        print(f"#{n}: not in the open list")
        continue
    try:
        d = fetch(n)
    except Exception as e:
        print(f"#{n}: diff fetch failed ({e})")
        continue
    files, added = [], []
    cur = None
    nadd = ndel = 0
    for line in d.splitlines():
        if line.startswith("+++ b/"):
            cur = line[6:]
            files.append(cur)
        elif line.startswith("+"):
            if not line.startswith("+++"):
                added.append(line[1:])
                nadd += 1
        elif line.startswith("-") and not line.startswith("---"):
            ndel += 1
    addedtext = "\n".join(added)
    dirs = sorted({f.split("/")[0] + ("/" + f.split("/")[1] if f.count("/") > 1 else "") for f in files})
    flags = sorted(set(re.findall(r"\bSTRATA_[A-Z0-9_]+", addedtext)))
    cli = sorted(set(re.findall(r"--[a-z][a-z0-9-]{2,}", addedtext)))
    claims = sorted(set(re.findall(r"[+-]?\d+(?:\.\d+)?\s?%", addedtext)))[:14]
    hip = len(re.findall(r"\bhip\b|hipBLASLt|rocBLAS|gfx11|amd", addedtext, re.I))
    cuda = len(re.findall(r"\bcuda\b|cudaHostAlloc|nvml|sm_\d", addedtext, re.I))
    base = p["base"]["sha"][:7]
    print(f"\n{'='*100}\n#{n} {p['title'][:90]}")
    print(f"  base {base}{' (== our HEAD: applies as-is)' if base == HEAD else ''} | +{nadd}/-{ndel} "
          f"in {len(files)} file(s) | created {p['created_at'][:10]}")
    print(f"  dirs: {', '.join(dirs[:8])}")
    if flags:
        print(f"  knobs: {', '.join(flags[:10])}")
    if cli:
        print(f"  flags: {', '.join(cli[:10])}")
    if claims:
        print(f"  numbers in the diff: {', '.join(claims)}")
    print(f"  added lines mention hip/amd {hip}x vs cuda/nvml {cuda}x")
