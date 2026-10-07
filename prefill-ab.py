#!/usr/bin/env python3
"""Warm prefill A/B: same prompt shape, a unique nonce each round so the conversation cache cannot answer it.

    python prefill-ab.py <rounds> <label>

For every round it posts a ~3.1K-token prompt (max_tokens=1, so almost no decode), then reads the engine's own
progress line from the server's engine log ("reading the prompt: N tokens, X s so far") and reports N/X tok/s.
Round timings come from the engine, not from HTTP, so queueing and decode do not pollute the number.
"""
import json
import pathlib
import re
import sys
import time
import urllib.request

ROUNDS = int(sys.argv[1]) if len(sys.argv) > 1 else 4
LABEL = sys.argv[2] if len(sys.argv) > 2 else "arm"
URL = "http://127.0.0.1:8080/v1/chat/completions"
ENGINE_LOG = pathlib.Path(r"D:\llm-dev\strata\strata-iq2_xs.log")
BODY = ("The following is a long technical note about GPU memory hierarchies and expert streaming. " * 240)


def post(nonce):
    prompt = f"{BODY}\n\n[run {nonce}] Summarise the note in one sentence."
    payload = {"model": "local", "messages": [{"role": "user", "content": prompt}], "max_tokens": 1}
    req = urllib.request.Request(URL, data=json.dumps(payload).encode(),
                                 headers={"Content-Type": "application/json"})
    t0 = time.time()
    with urllib.request.urlopen(req, timeout=900) as r:
        d = json.load(r)
    return time.time() - t0, (d.get("usage") or {}).get("prompt_tokens")


def engine_prefill(mark):
    """The last 'reading the prompt: N tokens, X s so far' line written since byte offset `mark`."""
    if not ENGINE_LOG.exists():
        return None
    data = ENGINE_LOG.read_bytes()
    chunk = data[mark:].decode("utf-8", errors="replace")
    hits = re.findall(r"reading the prompt: ([\d,]+)(?: of ([\d,]+))? tokens, (\d+) s so far", chunk)
    if not hits:
        return None
    total, _, secs = hits[-1]
    n = int(total.replace(",", ""))
    s = int(secs)
    return n, s, (n / s if s else 0)


def main():
    print(f"--- {LABEL}: {ROUNDS} rounds, ~{len(BODY)//4} token body, unique nonce each round ---")
    rates = []
    for i in range(ROUNDS):
        mark = ENGINE_LOG.stat().st_size if ENGINE_LOG.exists() else 0
        wall, pt = post(f"{LABEL}-{i}-{int(time.time())}")
        time.sleep(1.0)
        e = engine_prefill(mark)
        if e:
            n, s, rate = e
            rates.append(rate)
            print(f"  round {i+1}: engine read {n} tokens in {s}s -> {rate:.1f} tok/s   (wall {wall:.1f}s, http prompt_tokens {pt})")
        else:
            print(f"  round {i+1}: no engine prefill line seen (wall {wall:.1f}s, http prompt_tokens {pt})")
    if rates:
        rates_sorted = sorted(rates)
        med = rates_sorted[len(rates_sorted) // 2]
        print(f"  {LABEL} median prefill: {med:.1f} tok/s  (rounds: {', '.join(f'{r:.0f}' for r in rates)})")


if __name__ == "__main__":
    main()
