#!/usr/bin/env python3
"""Ask the engine where the time goes, on this install's configuration.

    .venv/Scripts/python.exe measure-kernels.py --gpu-only-full     # the true per-token GPU floor
    .venv/Scripts/python.exe measure-kernels.py --gpu-stages        # mixer / ffn+router / post, outside the capture
    .venv/Scripts/python.exe measure-kernels.py --stats             # per-stage breakdown of a real run

Builds a token list with the pack's own tokenizer (tools/strata_tokenizer.py, via
tools/conversation_cache_parity.load_tokenizer), writes it to measure-tokens.txt, and runs engine/strata.exe with
the args, env, cwd and lib_dirs from scratch/configs/strata-iq2_xs.json - the same launch serve/server.py makes - plus the
measurement mode. Stop the server first: these want the GPU to themselves.

Every line the engine prints is kept in measure-<mode>.log next to it.
"""
import json
import os
import pathlib
import subprocess
import sys
import time

ROOT = pathlib.Path(r"D:\llm-dev\strata")
CFG = ROOT / "scratch/configs/strata-iq2_xs.json"
TOKENS = ROOT / "measure-tokens.txt"
PROMPT_TOKENS = 4096


def build_tokens(cfg) -> int:
    sys.path.insert(0, str(ROOT / "tools"))
    from conversation_cache_parity import load_tokenizer
    tok = load_tokenizer(pathlib.Path(cfg["tokenizer"]))
    parts, chars, n = [], 0, 0
    while chars < PROMPT_TOKENS * 4:
        n += 1
        s = (f"Ledger entry {n:06d} records a compaction of segment {n * 7 % 4093} at offset "
             f"{n * 977 % 1048573} with checksum {n * 31 % 65521}; the replica set acked it after {n % 97} ms.")
        parts.append(s)
        chars += len(s) + 1
    ids = tok.encode("\n".join(parts) + "\nSummarize the ledger.")
    TOKENS.write_text(",".join(str(i) for i in ids), encoding="utf-8")
    return len(ids)


def main():
    modes = sys.argv[1:] or ["--gpu-only-full"]
    mode = " ".join(modes)
    cfg = json.loads(CFG.read_text(encoding="utf-8-sig"))
    n = build_tokens(cfg)
    print(f"tokenized prompt: {n} tokens -> {TOKENS.name}")
    env = dict(os.environ)
    env.update({k: str(v) for k, v in (cfg.get("env") or {}).items()})
    libs = [str(p) for p in cfg.get("lib_dirs", [])]
    if libs:
        env["PATH"] = os.pathsep.join(libs + [env.get("PATH", "")])
    cmd = [cfg["exe"], *cfg["args"], "--tokens-file", str(TOKENS), "--max-new", "8", *modes]
    log = ROOT / f"measure-{mode.replace(' ', '_').lstrip('-')}.log"
    print(f"running: strata.exe <config args> --tokens-file measure-tokens.txt --max-new 8 {mode}")
    t0 = time.time()
    with log.open("w", encoding="utf-8") as f:
        p = subprocess.run(cmd, cwd=cfg.get("cwd") or str(ROOT), env=env, stdout=f, stderr=subprocess.STDOUT)
    print(f"exit {p.returncode} after {time.time() - t0:.1f}s; full output in {log.name}\n--- output ---")
    for line in log.read_text(encoding="utf-8", errors="replace").splitlines():
        print(line)
    return log.name


if __name__ == "__main__":
    main()
