#!/usr/bin/env python3
"""Triage the open PRs and issues on Niko1221/Strata for engine-tuning breadcrumbs.

    python triage-141.py            # uses logs/prs-open-141.json + logs/issues-open-141.json
                                    # (fetch them first: see the gh lines in the docstring)

    gh pr list    --repo Niko1221/Strata --state open --limit 400 \
       --json number,title,createdAt,updatedAt,author,labels,comments > logs/prs-open-141.json
    gh issue list --repo Niko1221/Strata --state open --limit 400 \
       --json number,title,createdAt,updatedAt,author,labels,comments > logs/issues-open-141.json

Prints the new PRs since the last snapshot, then every open issue newest-first with a tuning flag, then a
keyword-scored list of the issues/PRs most likely to describe knobs, values and measured settings.
"""
import json
import pathlib
import re

ROOT = pathlib.Path(r"D:\llm-dev\strata")
PRS = ROOT / "logs" / "prs-open-141.json"
ISS = ROOT / "logs" / "issues-open-141.json"
OLD = ROOT / "prs-open.json"

TUNING = ("tune", "tuning", "bench", "benchmark", "tok/s", "tokens/s", "perf", "performance", "speed",
          "faster", "slow", "latency", "memory", "ram", "vram", "flag", "config", "setting", "option",
          "budget", "cache", "prefill", "decode", "prompt", "kv", "thread", "pool", "profile")
MODEL = ("iq2", "iq3", "q2_0", "qwen", "glm", "deepseek", "flash", "coder", "swe", "moe", "expert")


def load(p):
    return json.loads(p.read_text(encoding="utf-8", errors="replace"))


def main():
    prs, iss = load(PRS), load(ISS)
    # reference: the d5ea713 / v0.1.40.3 era.  Anything created after it is new to us; the repo has ~300 open
    # PRs and ~250 open issues, so page-1 snapshots are useless as a diff base - filter by date instead.
    CUT = "2026-10-08T00:00:00Z"
    old = set()

    print(f"open PRs: {len(prs)}   open issues: {len(iss)}   (cutoff {CUT})")

    new = sorted((p for p in prs if p["createdAt"] >= CUT), key=lambda p: p["number"])
    print(f"\n=== PRs created since the cutoff ({len(new)}) ===")
    for p in new:
        print(f"  #{p['number']:<5} {p['createdAt'][:10]} {p['author']['login'][:12]:<12} {p['title'][:92]}")

    print(f"\n=== ISSUES created since the cutoff ===")
    for i in sorted((x for x in iss if x["createdAt"] >= CUT), key=lambda x: x["number"]):
        labels = ",".join(l["name"] for l in i["labels"])
        print(f"  #{i['number']:<5} {i['createdAt'][:10]} {i['author']['login'][:11]:<11} "
              f"c={len(i.get('comments') or [])} [{labels[:18]:<18}] {i['title'][:80]}")

    print("\n=== most likely to carry knobs / values (issues AND prs) ===")
    scored = []
    for kind, items in (("ISSUE", iss), ("PR", prs)):
        for e in items:
            text = (e["title"] + " " + " ".join((c.get("body") or "") for c in (e.get("comments") or []))).lower()
            s = sum(2 for k in TUNING if k in text) + sum(1 for k in MODEL if k in text)
            knobs = len(set(re.findall(r"STRATA_[A-Z0-9_]+|--[a-z][a-z0-9-]{3,}", text)))
            if knobs:
                s += knobs
            if s >= 8:
                scored.append((s, knobs, kind, e["number"], e["title"][:78]))
    for s, knobs, kind, num, title in sorted(scored, reverse=True)[:25]:
        print(f"  {kind} #{num:<5} score {s:>3} knobs {knobs:>2}  {title}")


if __name__ == "__main__":
    main()
