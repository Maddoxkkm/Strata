#!/usr/bin/env python3
"""Resolve merge conflicts from a plan: python resolve-merge.py <plan.json>

The plan maps a file to its per-block decisions, in order:
    "ours"   keep the tree's side (upstream, on this branch)
    "theirs" take the merged branch's side
    "both"   keep both sides, ours first (for additive conflicts)
    ["custom", "text"] insert the text verbatim

Usable for any PR merge: stale PRs conflict mostly over files upstream has since rewritten, where "ours"
is right for the integration file and "theirs" only for genuinely new content.
"""
import json
import pathlib
import sys

ROOT = pathlib.Path(r"D:\llm-dev\strata")


def resolve(path: pathlib.Path, plan: list) -> int:
    lines = path.read_text(encoding="utf-8", errors="replace").splitlines(keepends=True)
    out, mode, ours, theirs, idx = [], None, [], [], 0
    for line in lines:
        if line.startswith("<<<<<<<"):
            mode, ours, theirs = "ours", [], []
            continue
        if line.startswith("=======") and mode == "ours":
            mode = "theirs"
            continue
        if line.startswith(">>>>>>>") and mode == "theirs":
            if idx >= len(plan):
                raise SystemExit(f"  {path.name}: block {idx} has no decision")
            pick = plan[idx]
            if isinstance(pick, list):
                out.append(pick[1])
            elif pick == "ours":
                out.extend(ours)
            elif pick == "theirs":
                out.extend(theirs)
            elif pick == "both":
                out.extend(ours)
                out.extend(theirs)
            else:
                raise SystemExit(f"  {path.name}: unknown decision {pick!r}")
            idx += 1
            mode = None
            continue
        (out if mode is None else (ours if mode == "ours" else theirs)).append(line)
    if idx != len(plan):
        raise SystemExit(f"  {path.name}: {idx} blocks found, {len(plan)} planned")
    path.write_bytes("".join(out).encode("utf-8"))
    return idx


def main():
    plan = json.loads(pathlib.Path(sys.argv[1]).read_text(encoding="utf-8"))
    for rel, blocks in plan.items():
        if rel.startswith("_"):
            continue
        p = ROOT / rel
        n = resolve(p, blocks)
        print(f"  resolved {n} block(s) in {rel}: {blocks}")


if __name__ == "__main__":
    main()
