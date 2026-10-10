#!/usr/bin/env python3
"""Rank the project's open PRs for *this* machine (RX 7900 XTX / gfx1100, HIP, Windows, IQ2_XS).

    python scratch/scripts/pr-triage.py [--all]

Scoring is keyword-based and deliberately crude: it separates the pile into "worth reading the diff of" and
"not our hardware" so the judgement happens on a short list. Titles carry the signal; a PR whose title says
SYCL/XMX/Pascal/Blackwell/Docker cannot affect a gfx1100 Windows/HIP build, while one that says HIP, MMQ,
resource, expert, KV, prefill or prompt can. Read the printed match terms before trusting a score.
"""
import json
import subprocess
import sys

REPO = "Niko1221/Strata"

# (regex-ish substring, weight) - substrings, matched case-insensitively against the title
GOOD = [
    ("hip", 6), ("rocm", 6), ("amd", 5), ("gfx10", 6), ("gfx11", 6), ("rdna", 6), ("wsl", 4),
    ("windows", 3), ("vulkan", 2),
    ("prefill", 7), ("prompt", 6), ("decode", 4), ("mmq", 6), ("qsa", 5), ("gemm", 5), ("attention", 4),
    ("expert", 6), ("resident", 6), ("stage", 5), ("stager", 6), ("ring", 4), ("loan", 5), ("cache", 4),
    ("kv", 4), ("mtp", 5), ("draft", 4), ("spec", 3),
    ("iq2", 6), ("iq3", 3), ("q2_0", 4), ("moe", 4), ("qwen35", 5), ("qwen3.8", 5), ("flash-next", 5),
    ("memory", 5), ("ram", 4), ("vram", 4), ("pinned", 5), ("page", 3), ("oom", 5), ("commit", 3),
    ("perf", 4), ("faster", 5), ("speed", 3), ("throughput", 3), ("latency", 3),
    ("fix", 2), ("correctness", 4), ("corrupt", 5), ("hang", 3), ("crash", 3), ("stall", 4),
]

BAD = [
    ("sycl", -8), ("xmx", -8), ("intel", -6), ("arc", -4), ("oneapi", -8),
    ("cuda12", -4), ("cuda 12", -4), ("docker", -8), ("container", -6),
    ("pascal", -7), ("sm_61", -7), ("blackwell", -5), ("sm_120", -6), ("h100", -8), ("a100", -8),
    ("rtx 50", -3), ("rtx 40", -2), ("multi-gpu", -3), ("multi gpu", -3),
    ("web", -5), ("ui", -5), ("frontend", -6), ("css", -6), ("html", -6), ("theme", -6),
    ("mathjax", -8), ("katex", -8), ("latex", -8), ("tex", -6), ("markdown", -5),
    ("chinese", -5), ("language switch", -6), ("translate", -6), ("translation", -6),
    ("readme", -6), ("docs", -5), ("typo", -6), ("comment", -3), ("changelog", -6),
    ("benchmark report", -4), ("community", -3), ("setup", -3), ("installer", -2), ("mcp", -4),
    ("license", -6), ("sponsor", -6), ("donation", -6), ("swift", -1), ("vision", -2), ("image", -4),
]


def main():
    limit = "500" if "--all" in sys.argv else "500"
    out = subprocess.run(["gh", "pr", "list", "-R", REPO, "--state", "open", "--limit", limit,
                          "--json", "number,title,updatedAt,createdAt,changedFiles,additions,deletions,isDraft,author,labels"],
                         capture_output=True, text=True)
    prs = json.loads(out.stdout or "[]")
    if not prs:
        print("  no data from gh")
        return
    scored = []
    for p in prs:
        t = p["title"].lower()
        good = [(k, w) for k, w in GOOD if k in t]
        bad = [(k, w) for k, w in BAD if k in t]
        score = sum(w for _, w in good) + sum(w for _, w in bad)
        scored.append((score, p, [k for k, _ in good], [k for k, _ in bad]))
    scored.sort(key=lambda s: -s[0])

    print(f"  open PRs: {len(prs)}   (ranking by keyword fit for gfx1100/HIP/Windows + prefill/decode/memory)")
    print(f"  {'#':<6}{'score':>6}  {'updated':<11}{'files':>6}{'±':>12}  title")
    for score, p, good, bad in scored[:30]:
        plus = f"+{p['additions']}/-{p['deletions']}"
        flag = "" if score > 0 else "  (not ours)"
        print(f"  #{p['number']:<5}{score:>6}  {p['updatedAt'][:10]:<11}{p['changedFiles']:>6}{plus:>12}  {p['title'][:58]}{flag}")
        print(f"         match: {'/'.join(good) if good else '-'}{'   avoid: ' + '/'.join(bad) if bad else ''}")
    print(f"\n  --- the rest ({max(0, len(prs) - 30)} PRs) score at or below {scored[29][0] if len(scored) > 29 else 0}")


if __name__ == "__main__":
    main()
