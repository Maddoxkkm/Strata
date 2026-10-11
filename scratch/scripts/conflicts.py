#!/usr/bin/env python3
"""Summarise every conflict block in the working tree so each can be classified fast.

    python scratch/scripts/conflicts.py

For each unmerged file: each block's line, how many lines "ours" and "theirs" contribute, and the first
line of each side. That is usually enough to see that upstream already carries the change (ours == the
feature, theirs == the PR's older shape) without reading the whole region.
"""
import pathlib
import subprocess

ROOT = pathlib.Path(r"D:\llm-dev\strata")


def conflicted() -> list[pathlib.Path]:
    out = subprocess.run(["git", "-C", str(ROOT), "diff", "--name-only", "--diff-filter=U"],
                         capture_output=True, text=True).stdout.split()
    files = [ROOT / p for p in out]
    # also catch files that carry markers but are not "unmerged" (partial 3-way writes)
    for p in ROOT.rglob("*.cpp"):
        pass
    return files


def blocks(path: pathlib.Path):
    mode = None
    ours, theirs, start = [], [], 0
    for i, line in enumerate(path.read_text(encoding="utf-8", errors="replace").splitlines(), 1):
        if line.startswith("<<<<<<<"):
            mode, start = "ours", i
            ours, theirs = [], []
            continue
        if line.startswith("=======") and mode == "ours":
            mode = "theirs"
            continue
        if line.startswith(">>>>>>>") and mode == "theirs":
            yield start, ours, theirs
            mode = None
            continue
        if mode == "ours":
            ours.append(line)
        elif mode == "theirs":
            theirs.append(line)


def main():
    files = conflicted()
    if not files:
        print("  no unmerged files")
        return
    print(f"  unmerged files: {len(files)}")
    for f in files:
        if not f.exists():
            print(f"\n  {f.name}: (deleted)")
            continue
        bs = list(blocks(f))
        print(f"\n  {f.relative_to(ROOT)}  -- {len(bs)} conflict block(s)  [{len(f.read_text(encoding='utf-8', errors='replace').splitlines())} lines]")
        for start, ours, theirs in bs:
            o = (ours[0].strip()[:70] if ours else "")
            t = (theirs[0].strip()[:70] if theirs else "")
            print(f"    line {start:<6} ours({len(ours):>3}) {o}")
            print(f"    {'':<11} theirs({len(theirs):>3}) {t}")


if __name__ == "__main__":
    main()
