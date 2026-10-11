#!/usr/bin/env python3
"""Local speed check for the running Strata server (this PC: RX 7900 XTX 24 GB + 32 GB RAM).

    .venv/Scripts/python.exe local-bench.py <run-label>

Posts a fixed prompt suite to http://127.0.0.1:8080/v1/chat/completions, records the timings the
server returns plus the engine's own line for each request, and appends one row per test to
bench-results.csv. Run it once per configuration (kv=int8, kv=k8v4, ...) with a different label.
"""
import csv
import json
import pathlib
import re
import sys
import time
import urllib.request

LABEL = sys.argv[1] if len(sys.argv) > 1 else "run"
URL = "http://127.0.0.1:8080/v1/chat/completions"
CSV_PATH = pathlib.Path(r"D:\llm-dev\strata\bench-raw.csv")
ENGINE_LOG = pathlib.Path(r"D:\llm-dev\strata\scratch/configs/strata-iq2_xs.log")

FILLER = ("The storage engine keeps a write-ahead log, flushes immutable segments to object storage "
          "and compacts them in the background while consensus replicates the log across five nodes. ")


def health():
    with urllib.request.urlopen("http://127.0.0.1:8080/health", timeout=10) as r:
        return json.load(r)


def post(content, max_tokens, effort="none", timeout=1800):
    payload = {"model": "strata", "messages": [{"role": "user", "content": content}],
               "max_tokens": max_tokens, "reasoning_effort": effort}
    req = urllib.request.Request(URL, data=json.dumps(payload).encode(),
                                headers={"Content-Type": "application/json"})
    t0 = time.time()
    with urllib.request.urlopen(req, timeout=timeout) as r:
        d = json.load(r)
    return d, time.time() - t0


def engine_stats():
    """The engine's own summary line for the request just made, plus the expert-tier counters."""
    try:
        txt = ENGINE_LOG.read_text(errors="ignore")
    except OSError:
        return "", ""
    prompt_lines = re.findall(r"strata serve: prompt .*", txt)
    tier_lines = re.findall(r"strata serve: expert tiers: .*", txt)
    return (prompt_lines[-1] if prompt_lines else ""), (tier_lines[-1] if tier_lines else "")


def cumulative_mb_read():
    """The engine counts expert bytes read from the model folder cumulatively ('since the start')."""
    try:
        txt = ENGINE_LOG.read_text(errors="ignore")
    except OSError:
        return None
    m = re.findall(r"since the start RAM \d+ blobs, files (\d+) blobs ([\d.]+) MB read", txt)
    return (int(m[-1][0]), float(m[-1][1])) if m else None


def run(label, content, max_tokens, effort="none"):
    before = cumulative_mb_read()
    d, wall = post(content, max_tokens, effort)
    t = d["timings"]
    eline, tline = engine_stats()
    after = cumulative_mb_read()
    dblobs = dmib = ""
    if before and after:
        dblobs = after[0] - before[0]
        dmib = round(after[1] - before[1], 1)
    text = (d["choices"][0]["message"].get("content") or "")[:120].replace("\n", " ")
    row = {
        "run": label, "test": label, "prompt_tokens": t["prompt_n"],
        "prefill_tok_s": round(t["prompt_per_second"], 1),
        "decode_tokens": t["predicted_n"], "decode_tok_s": round(t["predicted_per_second"], 1),
        "draft_n": t["draft_n"], "draft_accepted": t["draft_n_accepted"],
        "expert_cache_hit": (re.search(r"expert cache ([\d.]+)% hit", eline).group(1) if "cache" in eline else ""),
        "file_blob_reads_delta": dblobs, "file_mib_read_delta": dmib,
        "reasoning_effort": effort, "wall_s": round(wall, 1),
        "sample": text,
    }
    print(f"  {label:<22} prompt {row['prompt_tokens']:>5} tok @ {row['prefill_tok_s']:>6} t/s | "
          f"decode {row['decode_tokens']:>4} tok @ {row['decode_tok_s']:>5} t/s | "
          f"draft {row['draft_accepted']}/{row['draft_n']} | hit {row['expert_cache_hit']}% | "
          f"file {row['file_blob_reads_delta']} blobs/{row['file_mib_read_delta']} MiB | wall {row['wall_s']}s")
    if tline:
        print(f"      engine: {tline}")
    new = not CSV_PATH.exists()
    with CSV_PATH.open("a", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(row))
        if new:
            w.writeheader()
        w.writerow(row)
    return row


def main():
    h = health()
    print(f"server: model={h['model']} loaded={h['loaded']} max_context={h['max_context']} images={h['images']}")
    print(f"engine: {json.loads(pathlib.Path(r'D:\llm-dev\strata\engine\BUILD.json').read_text())['version']}"
          f"  label: {LABEL}")
    # warm-up (also the first-answer-after-load number)
    run(f"{LABEL}|cold_short", "Say hello in five words.", 64)
    run(f"{LABEL}|chat_200", "Explain in about 150 words why the sky is blue, for a curious 10-year-old.", 200)
    run(f"{LABEL}|code_220", "Write a Python function that returns the nth Fibonacci number iteratively, with a docstring.", 220)
    run(f"{LABEL}|prompt_2k", FILLER * 34 + "\n\nSummarize the above in three bullet points.", 150)
    run(f"{LABEL}|prompt_8k", FILLER * 135 + "\n\nSummarize the above in three bullet points.", 150)
    print(f"appended to {CSV_PATH}")


if __name__ == "__main__":
    main()
