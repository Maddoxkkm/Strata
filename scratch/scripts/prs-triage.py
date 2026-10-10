#!/usr/bin/env python3
"""Rank the repo's open PRs by how much they look like they would help THIS box.

    python prs-triage.py [--all]

Reads prs-open.json (the open-PR list from the GitHub API) and scores each PR's title+body against the local
stack: Windows 11, Radeon RX 7900 XTX (gfx1100, RDNA3), HIP/ROCm, IQ2_XS, 32 GB RAM low-RAM resident mode,
512K context with KV streaming, prefill-bound on I/O.  Negative weights are for PRs whose subject is another
platform's path (CUDA-only kernels, Pascal/Turing/Blackwell tuning, other GPU families, pure docs/bench rows).
"""
import json
import sys

HOT = [
    ("gfx1100", 9), ("7900 xtx", 9), ("rx 7900", 8), ("gfx110", 6), ("rdna3", 6), ("rdna 3", 6),
    ("hip", 5), ("rocm", 5), ("amd", 3), ("windows", 3), ("hipblaslt", 6), ("wmma", 5), ("rocblas", 4),
    ("iq2", 5), ("iq1", 3), ("k8v4", 6), ("iq3", 1),
    ("prefill", 6), ("stager", 4), ("mmq", 4), ("mmvq", 3),
    ("expert cache", 5), ("resident", 4), ("file tier", 4), ("mmap", 3), ("lru", 3), ("pin", 3),
    ("kv stream", 6), ("kv-stream", 6), ("streaming kv", 6), ("kv-grow", 4), ("long context", 3),
    ("draft", 4), ("mtp", 5), ("spec", 4), ("lookup", 3), ("suffix", 3),
    ("autotun", 5), ("tuning table", 4), ("tune", 3),
    ("monitor", 3), ("telemetry", 3), ("metrics", 2), ("adlx", 4),
    ("vision", 3), ("image", 2), ("updat", 3), ("calibrat", 4), ("voltage", 2), ("qsa", 3),
]
COLD = [
    ("cuda", -4), ("nvml", -5), ("sm_70", -4), ("sm_75", -4), ("sm_80", -4), ("sm_90", -4), ("sm_120", -4),
    ("blackwell", -3), ("hopper", -3), ("ampere", -3), ("pascal", -4), ("tensor core", -3),
    ("p100", -5), ("v100", -5), ("tesla", -4), ("titan", -4), ("rtx 20", -3), ("rtx 30", -2), ("rtx 40", -2),
    ("gfx906", -3), ("gfx115", -2), ("gfx120", -2), ("890m", -5), ("intel", -5), ("arc", -5),
    ("docker", -3), ("ipv6", -3), ("video", -3), ("prometheus", -1), ("docs:", -3), ("bench:", -3),
    ("community", -3), ("benchmark", -3), ("chinese", -4), ("中文", -4), ("arabic", -3), ("ui", -2),
    ("tool call", -1), ("responses api", -2), ("codex", -2),
]


def score(text):
    low = text.lower()
    s = 0
    hits = []
    for kw, w in HOT + COLD:
        if kw in low:
            s += w
            hits.append(kw if w > 0 else "-" + kw)
    return s, hits


def main():
    prs = json.load(open("prs-open.json"))
    rows = []
    for p in prs:
        text = f"{p['title']} {p.get('body') or ''}"
        s, hits = score(text)
        rows.append((s, p["number"], p["title"], p["head"]["ref"], p.get("draft"), p["created_at"][:10],
                     ", ".join(hits[:9])))
    rows.sort(reverse=True)
    limit = len(rows) if "--all" in sys.argv else 45
    print(f"187 open PRs scored against this box; top {limit}:\n")
    for s, n, title, ref, draft, created, hits in rows[:limit]:
        flag = "DRAFT " if draft else "      "
        print(f"{s:+3d} #{n:<5}{flag}{created} {title[:78]}")
        print(f"          hits: {hits}")
    print("\n--- bottom 10 (least relevant here) ---")
    for s, n, title, ref, draft, created, hits in rows[-10:]:
        print(f"{s:+3d} #{n:<5}{created} {title[:78]}")


if __name__ == "__main__":
    main()
