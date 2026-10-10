#!/usr/bin/env python3
"""Condensed read of selected issues/PRs: title, body and the first comments, trimmed.

    python breadcrumbs.py 1549 1630 1607 ...

Prints knob-looking tokens (STRATA_*, --flags) and any tok/s or GiB numbers found, so a long thread can be
triaged without dumping it all into a context window.
"""
import json
import re
import subprocess
import sys

REPO = "Niko1221/Strata"
KNOB = re.compile(r"(STRATA_[A-Z0-9_]+|--[a-z][a-z0-9-]{3,})")
NUM = re.compile(r"(\d[\d,\.]*\s*(?:tok/s|tokens/s|GiB|GB|MB/s|ms|%))")


def view(num):
    p = subprocess.run(["gh", "issue", "view", str(num), "--repo", REPO,
                        "--json", "number,title,body,comments,labels,state,author,createdAt"],
                       capture_output=True, text=True)
    if p.returncode != 0:
        return None
    return json.loads(p.stdout)


def trim(text, n):
    text = re.sub(r"\r", "", text or "")
    text = re.sub(r"\n{2,}", "\n", text).strip()
    return text[:n] + (" …" if len(text) > n else "")


def main():
    for num in sys.argv[1:]:
        d = view(num)
        if not d:
            print(f"\n### #{num}: (not found)")
            continue
        body = d.get("body") or ""
        comments = d.get("comments") or []
        blob = body + " " + " ".join((c.get("body") or "") for c in comments)
        knobs = sorted(set(KNOB.findall(blob)))[:14]
        nums = sorted(set(NUM.findall(blob)))[:10]
        print(f"\n{'='*100}")
        print(f"#{d['number']} [{d['state']}] {d['author']['login']} {d['createdAt'][:10]} — {d['title']}")
        print(f"  knobs: {', '.join(knobs) if knobs else '-'}")
        print(f"  numbers: {', '.join(nums) if nums else '-'}")
        print(f"  --- body ---\n{trim(body, 1100)}")
        for i, c in enumerate(comments[:2]):
            print(f"  --- comment {i+1} by {c.get('author', {}).get('login', '?')} ---\n{trim(c.get('body'), 650)}")


if __name__ == "__main__":
    main()
