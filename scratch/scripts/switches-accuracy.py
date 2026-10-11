#!/usr/bin/env python3
"""Correctness check for the bit-changing prefill switches (PA_FAST / PF_GEMM / PF_PAD).

    python scratch/scripts/switches-accuracy.py

STRATA_PA_FAST, STRATA_PF_GEMM and STRATA_PF_PAD are in arch_defaults.hpp's "switches that change bits" list,
so a faster prefill is only worth having if answers stay right. Two modes (off / on), one engine restart each,
answers graded rather than compared: a 2-bit model is not deterministic, so "the answers differ" proves nothing
while "both are wrong" or "only one is right" does. Includes a needle planted at ~16K so the prompt-attention
path is actually exercised, and a chunk boundary case (needle at the very end).
"""
import json
import pathlib
import subprocess
import time
import urllib.request

ROOT = pathlib.Path(r"D:\llm-dev\strata")
CFG = ROOT / "scratch" / "configs" / "strata-iq2_xs.json"
SWITCHES = {"STRATA_PA_FAST": "1", "STRATA_PF_SWITCH_MIN_T": "4096", "STRATA_PF_GEMM": "1", "STRATA_PF_PAD": "1",
            "STRATA_RAM_ADAPT": "1"}

FILLER = ("The quarterly maintenance procedure requires that each operator verify the replica lag, drain the "
          "queue, and confirm the failover path answers within budget before the window is declared open. ")


def needle_prompt(tokens: int) -> str:
    body = FILLER * max(1, tokens // 30)
    half = len(body) // 2
    return (body[:half] + "\n\nIMPORTANT: the maintenance code for this quarter is ZX-4471-Q.\n\n" + body[half:]
            + "\n\nQuestion: what is the maintenance code mentioned above? Reply with just the code.")


CASES = [
    ("17*23", "What is 17*23? Reply with just the number.", ["391"]),
    ("9/13 vs 7/11", "Which is larger, 9/13 or 7/11? Reply with just the fraction.", ["9/13"]),
    ("avg speed", "A train travels 240 km in 3 hours, then 180 km in 2 hours. What is the average speed for the "
                  "whole journey? Reply with just the number and unit.", ["84"]),
    ("reverse", "Write the word 'strata' backwards. Reply with just the word.", ["atarts"]),
    ("capital", "What is the capital of Australia? Reply with just the city.", ["canberra"]),
    ("needle 16K", needle_prompt(16000), ["ZX-4471-Q", "ZX-4471", "ZX 4471"]),
]


def set_switches(on: bool) -> None:
    c = json.loads(CFG.read_text(encoding="utf-8-sig"))
    for k, v in SWITCHES.items():
        if on:
            c["env"][k] = v
        else:
            c["env"].pop(k, None)
    CFG.write_text(json.dumps(c, indent=1), encoding="utf-8")


def restart() -> None:
    subprocess.run(["cmd", "/c", "stop-server.bat"], cwd=ROOT, capture_output=True, stdin=subprocess.DEVNULL)
    time.sleep(2)
    log = open(ROOT / "logs" / "server-swacc.log", "w", encoding="utf-8")
    subprocess.Popen(["cmd", "/c", "run-iq2_xs.bat"], cwd=ROOT, stdout=log, stderr=subprocess.STDOUT,
                     stdin=subprocess.DEVNULL)
    for _ in range(60):
        try:
            with urllib.request.urlopen("http://127.0.0.1:8080/health", timeout=4) as r:
                if b'"loaded": true' in r.read():
                    return
        except Exception:
            pass
        time.sleep(5)
    raise SystemExit("  server did not come up")


def ask(prompt: str) -> str:
    # 0 means UNCAPPED thinking, which with a small max_tokens yields an empty answer (all thinking).
    body = json.dumps({"model": "local", "messages": [{"role": "user", "content": prompt}],
                       "max_tokens": 512, "reasoning_budget_tokens": 64}).encode()
    req = urllib.request.Request("http://127.0.0.1:8080/v1/chat/completions", data=body,
                                headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=900) as r:
        return json.load(r)["choices"][0]["message"].get("content") or ""


def run(mode: str) -> dict[str, bool]:
    set_switches(mode == "on")
    restart()
    out = {}
    for name, prompt, expect in CASES:
        ans = ask(prompt)
        ok = any(e.lower() in ans.lower() for e in expect)
        out[name] = ok
        print(f"    {mode:>3} | {name:<14} {'OK ' if ok else 'BAD'} | {ans.strip()[:52]!r}")
    return out


def main():
    print("  == switches OFF ==")
    off = run("off")
    print("  == switches ON ==")
    on = run("on")
    print("\n  == graded ==")
    for name in off:
        mark = "same" if off[name] == on[name] else "DIFFERS"
        print(f"    {name:<14} off {'pass' if off[name] else 'fail'} / on {'pass' if on[name] else 'fail'}  ({mark})")
    broken = [k for k in off if not on[k]]
    print(f"  verdict: {'no case broken by the switches' if not broken else 'BROKEN: ' + ', '.join(broken)}")


if __name__ == "__main__":
    main()
