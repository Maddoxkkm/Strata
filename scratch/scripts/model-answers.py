#!/usr/bin/env python3
"""Ask the same questions of whichever model the server currently serves, and print the answers.

    python scratch/scripts/model-answers.py <label> [config]

Used by scratch/scripts/model-bench.sh: answers are saved per model so the two can be compared side by side
(quality is the reason to pay IQ3_S's extra bytes, so it has to be looked at, not assumed).
"""
import json
import pathlib
import subprocess
import sys
import time
import urllib.request

ROOT = pathlib.Path(r"D:\llm-dev\strata")
CFG = pathlib.Path(sys.argv[2]) if len(sys.argv) > 2 else ROOT / "scratch" / "configs" / "strata-iq2_xs.json"

QUESTIONS = [
    "What is 17*23? Reply with just the number.",
    "A train travels 240 km in 3 hours, then 180 km in 2 hours. What is the average speed for the whole "
    "journey? Reply with just the number and unit.",
    "Write the word 'strata' backwards. Reply with just the word.",
    "In one sentence, what is the difference between a process and a thread?",
    "Which is larger, 9/13 or 7/11? Reply with just the fraction.",
]


def up() -> bool:
    try:
        with urllib.request.urlopen("http://127.0.0.1:8080/health", timeout=5) as r:
            return b'"loaded": true' in r.read()
    except Exception:
        return False


def main():
    label = sys.argv[1] if len(sys.argv) > 1 else "model"
    subprocess.run(["cmd", "/c", "stop-server.bat"], cwd=ROOT, capture_output=True, stdin=subprocess.DEVNULL)
    time.sleep(2)
    log = open(ROOT / "logs" / f"server-answers-{label}.log", "w", encoding="utf-8")
    subprocess.Popen(["cmd", "/c", "run-iq2_xs.bat"], cwd=ROOT, stdout=log, stderr=subprocess.STDOUT,
                     stdin=subprocess.DEVNULL)
    for _ in range(90):          # a bigger model takes longer to come up
        if up():
            break
        time.sleep(5)
    else:
        raise SystemExit("  server never reported loaded")
    time.sleep(10)               # let the first request's load path settle before timing anything
    for q in QUESTIONS:
        body = json.dumps({"model": "local", "messages": [{"role": "user", "content": q}],
                           "max_tokens": 512, "reasoning_budget_tokens": 64}).encode()
        req = urllib.request.Request("http://127.0.0.1:8080/v1/chat/completions", data=body,
                                    headers={"Content-Type": "application/json"})
        try:
            with urllib.request.urlopen(req, timeout=600) as r:
                ans = (json.load(r)["choices"][0]["message"].get("content") or "").strip()
        except Exception as e:
            ans = f"<error {e}>"
        print(f"  Q: {q[:80]}")
        print(f"  A: {ans[:200]}")
        print()
    subprocess.run(["cmd", "/c", "stop-server.bat"], cwd=ROOT, capture_output=True, stdin=subprocess.DEVNULL)


if __name__ == "__main__":
    main()
