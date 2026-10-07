#!/usr/bin/env python3
"""Prefill throughput check for a running Strata server (mirrors tools/hip/bench_prefill.py's shape).

    .venv/Scripts/python.exe prefill-bench.py <arm-label>

Two prompt sizes (about 4.2k and 8.8k tokens, the sizes AMD_HIP_PERFORMANCE.md reports), a fresh request
followed by a follow-up that shares the prefix, 128 output tokens each (the intentional throughput cap).
Every request's text is unique so the fresh ones reuse zero KV tokens. One line per request, appended to
prefill-arms.csv; the fresh request's prefill rate is the comparison number.
"""
import csv
import json
import pathlib
import re
import sys
import time
import urllib.error
import urllib.request

ARM = sys.argv[1] if len(sys.argv) > 1 else "arm"
URL = "http://127.0.0.1:8080/v1/chat/completions"
CSV_PATH = pathlib.Path(r"D:\llm-dev\strata\prefill-arms.csv")
ENGINE_LOG = pathlib.Path(r"D:\llm-dev\strata\strata-iq2_xs.log")
SIZES = (4200, 8830)


def make_prompt(target_tokens: int, salt: str) -> str:
    """Unique filler: every sentence carries a counter, so nothing is a repeat of an earlier request.
    Sentence text is ~150 chars (about 40 tokens), so the loop counts characters, not sentences."""
    parts, chars, n = [], 0, 0
    while chars < target_tokens * 4:                  # ~4 chars per token for this filler
        n += 1
        sentence = (f"Ledger entry {salt}-{n:06d} records a compaction of segment {n * 7 % 4093} at "
                    f"offset {n * 977 % 1048573} with checksum {n * 31 % 65521}; the replica set acked it "
                    f"after {n % 97} milliseconds.")
        parts.append(sentence)
        chars += len(sentence) + 1
    return "\n".join(parts) + "\n\nIn two sentences, what kind of records are these?"


def post(content, max_tokens=128, timeout=1800):
    body = json.dumps({"model": "strata", "messages": [{"role": "user", "content": content}],
                       "max_tokens": max_tokens, "reasoning_effort": "none", "temperature": 0}).encode()
    req = urllib.request.Request(URL, data=body, headers={"Content-Type": "application/json"})
    t0 = time.time()
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            d = json.load(r)
    except urllib.error.HTTPError as e:               # show the server's own reason, not just the status
        raise SystemExit(f"HTTP {e.code} for {len(content)} chars of prompt: "
                         f"{e.read().decode(errors='replace')[:300]}") from None
    return d, time.time() - t0


def engine_line():
    try:
        txt = ENGINE_LOG.read_text(errors="ignore")
    except OSError:
        return ""
    m = re.findall(r"strata serve: prompt .*", txt)
    return m[-1] if m else ""


def run(label, content):
    d, wall = post(content)
    t = d["timings"]
    row = {"arm": ARM, "request": label, "prompt_tokens": t["prompt_n"], "reused_tokens": t.get("cache_n", 0),
           "prefill_tok_s": round(t["prompt_per_second"], 1), "prefill_ms": round(t["prompt_ms"]),
           "decode_tokens": t["predicted_n"], "decode_tok_s": round(t["predicted_per_second"], 1),
           "draft_n": t["draft_n"], "draft_accepted": t["draft_n_accepted"], "wall_s": round(wall, 2)}
    print(f"  {label:<26} prompt {row['prompt_tokens']:>5} tok (reused {row['reused_tokens']:>5}) "
          f"@ {row['prefill_tok_s']:>6.1f} t/s prefill | decode {row['decode_tok_s']:>5.1f} t/s | "
          f"wall {row['wall_s']:>5}s", flush=True)
    new = not CSV_PATH.exists()
    with CSV_PATH.open("a", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(row))
        if new:
            w.writeheader()
        w.writerow(row)
    return row


def main():
    print(f"arm: {ARM}  engine log line before: {engine_line()[:0]}", flush=True)
    for size in SIZES:
        salt = f"{ARM}-{size}"
        print(f"  --- target {size} tokens ---", flush=True)
        run(f"fresh_{size}", make_prompt(size, salt))
        run(f"followup_{size}", f"Continue, then name the single most common segment id you saw above.")


if __name__ == "__main__":
    main()
