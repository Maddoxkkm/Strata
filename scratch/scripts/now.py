#!/usr/bin/env python3
"""Where the box stands right now, measured from the engine's own per-request lines.

    python now.py

Long prompt (prefill), short prompt (read + decode) and a 256-token answer, all against the RUNNING server.
Each case takes the log size before the request and polls the new bytes for the engine's summary line, so the
numbers are the engine's own timings, not HTTP wall clock.
"""
import json
import pathlib
import re
import time
import urllib.request

URL = "http://127.0.0.1:8080/v1/chat/completions"
LOG = pathlib.Path(r"D:\llm-dev\strata\scratch/configs/strata-iq2_xs.log")
BODY = ("The following is a long technical note about GPU memory hierarchies and expert streaming. " * 240)
SUMMARY = re.compile(
    r"prompt (\d+) tokens = (\d+) reused \+ (\d+) read in (\d+) ms \(([\d.]+) tok/s\), "
    r"(\d+) generated in (\d+) ms \(([\d.]+) tok/s\)")
STREAM = re.compile(r"experts streamed (\d+) \((\d+) by DMA, host ([\d.]+) ms\)")


def ask(prompt, max_tokens):
    payload = {"model": "local", "messages": [{"role": "user", "content": prompt}],
               "max_tokens": max_tokens}
    req = urllib.request.Request(URL, data=json.dumps(payload).encode(),
                                 headers={"Content-Type": "application/json"})
    mark = LOG.stat().st_size if LOG.exists() else 0
    t0 = time.time()
    with urllib.request.urlopen(req, timeout=900) as r:
        json.load(r)
    wall = time.time() - t0
    for _ in range(20):
        time.sleep(1)
        chunk = LOG.read_bytes()[mark:].decode("utf-8", errors="replace")
        m = SUMMARY.search(chunk)
        if m:
            g = m.groups()
            s = STREAM.search(chunk)
            return {"read_tok": int(g[2]), "read_ms": int(g[3]), "prefill": float(g[4]),
                    "gen_tok": int(g[5]), "gen_ms": int(g[6]), "decode": float(g[7]),
                    "wall": wall, "streamed": (int(s.group(1)), float(s.group(3))) if s else None}
    return {"error": f"no summary line (wall {wall:.1f}s)"}


def main():
    print(f"--- {time.strftime('%H:%M:%S')} ---")

    ask("warm-up: reply with the single word ready", 8)

    print("LONG PROMPT (prefill)")
    long_rates = []
    for i in range(2):
        r = ask(f"{BODY}\n\n[run now-{i}-{int(time.time())}] Summarise the note in one sentence.", 1)
        if "error" in r:
            print("   ", r["error"])
            continue
        long_rates.append(r["prefill"])
        extra = ""
        if r["streamed"]:
            extra = f" | streamed {r['streamed'][0]} experts, host {r['streamed'][1]:.0f} ms"
        print(f"    {r['read_tok']} tokens read in {r['read_ms']} ms = {r['prefill']:.1f} tok/s "
              f"(wall {r['wall']:.1f}s){extra}")

    print("SHORT PROMPT (chat-sized)")
    for i in range(3):
        r = ask(f"Prompt {i}: why does an expert cache hit rate matter more than raw disk bandwidth? "
                f"Answer in one sentence. [{int(time.time())}]", 64)
        if "error" in r:
            print("   ", r["error"])
            continue
        print(f"    {r['read_tok']} tokens read in {r['read_ms']} ms ({r['prefill']:.1f} tok/s) | "
              f"{r['gen_tok']} generated in {r['gen_ms']} ms ({r['decode']:.1f} tok/s)")

    print("DECODE (256 tokens)")
    r = ask(f"Write two short paragraphs about expert streaming and bandwidth. [{int(time.time())}]", 256)
    if "error" in r:
        print("   ", r["error"])
    else:
        print(f"    {r['read_tok']} read in {r['read_ms']} ms ({r['prefill']:.1f} tok/s) | "
              f"{r['gen_tok']} generated in {r['gen_ms']} ms ({r['decode']:.1f} tok/s)")

    if long_rates:
        print(f"LONG-PROMPT PREFILL: {sum(long_rates)/len(long_rates):.1f} tok/s average of {len(long_rates)}")


if __name__ == "__main__":
    main()
