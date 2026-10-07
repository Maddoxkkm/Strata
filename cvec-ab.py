#!/usr/bin/env python3
"""Cost of the experimental speed projection (the refusal-direction control vector), per request.

    .venv/Scripts/python.exe cvec-ab.py [rounds]

The vector is switched per request with the API field "experimental_speed_projection" (the web app's Sampling
drawer does the same), so no engine restart is needed. Each round sends the same shape of fresh prompt twice -
once with the projection on, once off - and reports the server's own timings. The prompts differ per round
(a counter in the text), so nothing is served from the prompt cache.

The package says the projection costs 0.2-0.4% per token and that "a chat's speed with it on depends on the text
the model writes", so this measures both the tok/s and how much text the model actually writes.
"""
import json
import statistics
import sys
import time
import urllib.request

ROUNDS = int(sys.argv[1]) if len(sys.argv) > 1 else 3
URL = "http://127.0.0.1:8080/v1/chat/completions"
FILLER = ("The write-ahead log is flushed to immutable segments, compaction runs in the background and the "
          "consensus group replicates the log across five nodes. ")


def prompt(salt: int) -> str:
    return FILLER * 40 + f"\nSummarize the above in three bullet points. (case {salt})"


def ask(salt: int, cvec: bool, max_tokens=200, timeout=1800):
    body = {"model": "strata", "messages": [{"role": "user", "content": prompt(salt)}],
            "max_tokens": max_tokens, "reasoning_effort": "none", "temperature": 0,
            "experimental_speed_projection": cvec}
    req = urllib.request.Request(URL, data=json.dumps(body).encode(),
                                 headers={"Content-Type": "application/json"})
    t0 = time.time()
    with urllib.request.urlopen(req, timeout=timeout) as r:
        d = json.load(r)
    t = d["timings"]
    return {"prefill": t["prompt_per_second"], "decode": t["predicted_per_second"],
            "ptok": t["prompt_n"], "gen": t["predicted_n"], "wall": time.time() - t0,
            "text": (d["choices"][0]["message"].get("content") or "")}


def main():
    print(f"engine: {json.load(open(r'D:\llm-dev\strata\engine\BUILD.json'))['version']}, {ROUNDS} rounds\n")
    rows = {"on": [], "off": []}
    for i in range(ROUNDS):
        for label, flag in (("on", True), ("off", False)):
            m = ask(1000 + i * 10 + (1 if flag else 2), flag)
            rows[label].append(m)
            print(f"  round {i + 1} cvec {label:<3} prompt {m['ptok']:>5} tok @ {m['prefill']:>6.1f} t/s | "
                  f"decode {m['gen']:>3} tok @ {m['decode']:>5.1f} t/s | wall {m['wall']:>5.1f}s | "
                  f"{len(m['text'])} chars", flush=True)
    print()
    for k in ("on", "off"):
        v = rows[k]
        print(f"  cvec {k:<3} median prefill {statistics.median(x['prefill'] for x in v):6.1f} t/s | "
              f"median decode {statistics.median(x['decode'] for x in v):5.1f} t/s | "
              f"median wall {statistics.median(x['wall'] for x in v):5.1f}s")
    on = statistics.median(x["decode"] for x in rows["on"])
    off = statistics.median(x["decode"] for x in rows["off"])
    print(f"\n  projection on/off decode difference: {100 * (on / off - 1):+.1f}%")


if __name__ == "__main__":
    main()
