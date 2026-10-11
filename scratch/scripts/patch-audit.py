#!/usr/bin/env python3
"""How much of a PR's patch is already in a tree?

    python scratch/scripts/patch-audit.py <tree-or-worktree> <pr-number> [<pr-number> ...]

`git apply -R --check` answers "can this diff be reverted as written?", which is *not* the question: a patch
that upstream rebased or reworked (a batch loop made unconditional, a helper renamed) fails the reverse test
even though every line of it is present. So this compares the diff's own added code lines against the tree:

  * take the added lines of the diff, skip comments/blank/short ones (they match everywhere and prove nothing)
  * keep the most distinctive ones first (longest)
  * `git grep -F` them into the tree and count how many appear verbatim

High coverage = the tree carries the change (whether we applied it or upstream landed it). Low coverage with a
few high-value hits usually means the change is present in a reworked form: read those lines before concluding.
Diffs live in scratch/prs/ and scratch/prs/audit/ (fetch with `gh pr diff N -R Niko1221/Strata`).
"""
import pathlib
import subprocess
import sys
import tempfile

ROOT = pathlib.Path(r"D:\llm-dev\strata")
DIFF_DIRS = [ROOT / "scratch" / "prs", ROOT / "scratch" / "prs" / "audit"]


def diff_for(pr: str) -> pathlib.Path | None:
    for d in DIFF_DIRS:
        p = d / f"{pr}.diff"
        if p.exists():
            return p
    return None


def added_lines(diff: pathlib.Path, min_len: int = 25) -> list[str]:
    out = []
    cur = ""
    for line in diff.read_text(encoding="utf-8", errors="replace").splitlines():
        if line.startswith("+++ "):
            cur = line[4:].strip()
            if cur.startswith("b/"):
                cur = cur[2:]
            continue
        if not line.startswith("+") or line.startswith("+++"):
            continue
        # docs prose matches the release notes and benchmark tables of any version: it proves nothing
        if cur.lower().endswith((".md", ".txt", ".csv", ".rst")):
            continue
        body = line[1:]
        stripped = body.strip()
        if not stripped or len(stripped) < min_len:
            continue
        if stripped.startswith(("//", "#", "*", "/*", "<!")):   # comments and doc prose match too easily
            continue
        out.append(body)
    return sorted(set(out), key=len, reverse=True)


def present(tree: str, lines: list[str]) -> list[str]:
    # the pattern file must be at a native path: git is a native binary here and cannot open an MSYS /tmp one
    path = ROOT / "logs" / ".patch-audit-patterns.txt"
    # exact bytes: write_text would turn \n into CRLF on Windows, leaving a stray \r on every pattern,
    # and git then matches nothing at all
    path.write_bytes("\n".join(lines).encode("utf-8"))
    # never search our own artefacts: scratch/prs holds the very diffs these lines came from
    r = subprocess.run(["git", "-C", tree, "grep", "-n", "-F", "-f", str(path), "--",
                        ":(exclude)scratch", ":(exclude)logs"],
                       capture_output=True, text=True, errors="replace")
    hits = set()
    for line in r.stdout.splitlines():
        parts = line.split(":", 2)
        if len(parts) == 3:
            hits.add(parts[2])
    return [l for l in lines if l in hits]


def main():
    tree = sys.argv[1]
    prs = sys.argv[2:]
    if not prs:
        prs = ["1323", "1372", "1381", "1416", "1439", "1448", "1451", "1457"]
    head = subprocess.run(["git", "-C", tree, "rev-parse", "--short", "HEAD"],
                          capture_output=True, text=True).stdout.strip()
    print(f"  tree {tree} @ {head}")
    print(f"  {'PR':<7}{'code lines':>11}{'verbatim':>10}{'coverage':>10}   examples of what matched")
    for pr in prs:
        d = diff_for(pr)
        if not d:
            print(f"  #{pr:<6}  no diff cached")
            continue
        lines = added_lines(d)[:60]
        m = present(tree, lines)
        cov = 100 * len(m) / max(1, len(lines))
        eg = ""
        if m:
            eg = " | ".join(x.strip()[:38] for x in m[:2])
        print(f"  #{pr:<6}{len(lines):>11}{len(m):>10}{cov:>9.0f}%   {eg}")


if __name__ == "__main__":
    main()
