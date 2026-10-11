#!/usr/bin/env python3
"""Fetch a set of PR diffs and report whether each still applies to this tree.

    python scratch/scripts/pr-check.py 1101 1237 1520 ...

Writes each diff to scratch/prs/cand/ and tests it three ways: `git apply --check` (clean), `git apply -3 --check`
(needs a 3-way merge, so some hunk's context has drifted), or neither (upstream has moved that region).
A PR that needs a 3-way merge is not disqualified - it just means the earlier application or upstream's own
edits touched nearby lines - but one that applies *neither* way has to be read hunk by hunk before trusting it.
"""
import json
import pathlib
import subprocess
import sys

ROOT = pathlib.Path(r"D:\llm-dev\strata")
OUT = ROOT / "scratch" / "prs" / "cand"
REPO = "Niko1221/Strata"


def main():
    prs = sys.argv[1:]
    if not prs:
        print("  usage: pr-check.py <pr-number> ...")
        return
    OUT.mkdir(parents=True, exist_ok=True)
    print(f"  {'PR':<7}{'files':>6}{'±':>12}  {'plain':<7}{'3-way':<7} title")
    for pr in prs:
        d = OUT / f"{pr}.diff"
        if not d.exists():
            out = subprocess.run(["gh", "pr", "diff", pr, "-R", REPO], capture_output=True, text=True)
            d.write_bytes(out.stdout.encode("utf-8", errors="replace"))
        text = d.read_text(encoding="utf-8", errors="replace")
        if not text.strip():
            print(f"  #{pr:<6}{'':>6}{'':>12}  {'--':<7}{'--':<7} (no diff: closed, or single-commit squashed?)")
            continue
        files = text.count("\ndiff --git ") + text.startswith("diff --git ")
        adds = sum(1 for l in text.splitlines() if l.startswith("+") and not l.startswith("+++"))
        dels = sum(1 for l in text.splitlines() if l.startswith("-") and not l.startswith("---"))
        plain = subprocess.run(["git", "-C", str(ROOT), "apply", "--check", str(d)],
                               capture_output=True, text=True).returncode == 0
        three = subprocess.run(["git", "-C", str(ROOT), "apply", "-3", "--check", str(d)],
                               capture_output=True, text=True).returncode == 0
        title = subprocess.run(["gh", "pr", "view", pr, "-R", REPO, "--json", "title"],
                               capture_output=True, text=True)
        try:
            t = json.loads(title.stdout)["title"]
        except Exception:
            t = "?"
        flag = "clean" if plain else ("3-way" if three else "READ FIRST")
        print(f"  #{pr:<6}{files:>6}{f'+{adds}/-{dels}':>12}  {flag:<7}{'' if plain else ('yes' if three else '--'):<7} {t[:50]}")


if __name__ == "__main__":
    main()
