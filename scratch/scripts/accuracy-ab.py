#!/usr/bin/env python3
"""End-to-end answer comparison: the matrix-core prompt path ON vs OFF.

The parity test already bounds the kernel's numerics (4.05e-06 vs FP64, agreeing with the old kernel to
2.2e-06 of output scale on this card), so this is the coarser check that nothing about *answers* moves: the
same prompts, one engine restart per mode, same config otherwise.
"""
import json
import pathlib
import subprocess
import time
import urllib.request

ROOT = pathlib.Path(r"D:\llm-dev\strata")
CFG = ROOT / "scratch" / "configs" / "strata-iq2_xs.json"
QUESTIONS = [
    "What is 17*23? Reply with just the number.",
    "A train travels 240 km in 3 hours, then 180 km in 2 hours. Average speed for the whole journey? Just the number and unit.",
    "Which is larger: 9/13 or 7/11? Reply with just the fraction.",
]


def set_switches(on: bool) -> None:
    c = json.loads(CFG.read_text(encoding="utf-8-sig"))
    for k in ("STRATA_HIP_WMMA", "STRATA_SELECT_WMMA"):
        if on:
            c["env"][k] = "1"
        else:
            c["env"].pop(k, None)
    CFG.write_text(json.dumps(c, indent=1), encoding="utf-8")


def restart() -> None:
    subprocess.run(["cmd", "/c", "stop-server.bat"], cwd=ROOT, capture_output=True, stdin=subprocess.DEVNULL)
    time.sleep(2)
    log = open(ROOT / "logs" / "server-accuracy.log", "w", encoding="utf-8")
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


def ask(q: str) -> str:
    body = json.dumps({"model": "local", "messages": [{"role": "user", "content": q}], "max_tokens": 96}).encode()
    req = urllib.request.Request("http://127.0.0.1:8080/v1/chat/completions", data=body,
                                headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=600) as r:
        m = json.load(r)["choices"][0]["message"]
    return ((m.get("content") or "").strip().splitlines() or [""])[0][:44]


def main():
    out = {}
    for mode, on in (("WMMA ON ", True), ("WMMA OFF", False)):
        set_switches(on)
        restart()
        out[mode] = [ask(q) for q in QUESTIONS]
        print(f"  {mode}:")
        for q, a in zip(QUESTIONS, out[mode]):
            print(f"     {q[:52]:<52} -> {a!r}")
    print("\n  === same answers? ===")
    for i, q in enumerate(QUESTIONS):
        same = out["WMMA ON "][i] == out["WMMA OFF"][i]
        print(f"     q{i + 1}: {'identical' if same else 'DIFFERS'}   on={out['WMMA ON '][i]!r}  off={out['WMMA OFF'][i]!r}")
    set_switches(True)          # leave the adopted configuration in place
    restart()
    print("\n  restored: both switches on, server up")


if __name__ == "__main__":
    main()
