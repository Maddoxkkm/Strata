#!/usr/bin/env python3
"""Does a workload-fitted expert profile cut the prefill's disk streaming?

    1. `--dump-routing` from an engine run on a TRACE prompt (different text from the measurement prompt, so the
       test is not self-fitting)
    2. make_profile.py --reorder --base <shipped> <trace>  ->  a profile whose top ranks this workload
    3. one prefill run with that profile, against the same prompt the shipped profile was measured on

Reports the engine's `experts streamed / resident` split and prefill tok/s for both profiles.
"""
import json
import os
import pathlib
import re
import subprocess
import sys
import threading
import time

ROOT = pathlib.Path(r"D:\llm-dev\strata")
CFG = ROOT / "scratch/configs/strata-iq2_xs.json"
SHIPPED = r"D:\llm-dev\strata\data\expert-profile.bin"
TRACE_TOKENS = str(ROOT / "logs" / "trace-ids.txt")
MEASURE_TOKENS = str(ROOT / "logs" / "prompt-ids.txt")
NEW_PROFILE = str(ROOT / "data" / "expert-profile-workload.bin")


def base_cfg():
    cfg = json.loads(CFG.read_text(encoding="utf-8-sig"))
    env = dict(os.environ)
    env.update({k: str(v) for k, v in (cfg.get("env") or {}).items()})
    libs = [str(p) for p in cfg.get("lib_dirs", [])]
    if libs:
        env["PATH"] = os.pathsep.join(libs + [env.get("PATH", "")])
    return cfg, env


def swap_profile(args, path):
    out, i = [], 0
    while i < len(args):
        if args[i] == "--expert-profile" and i + 1 < len(args):
            out += ["--expert-profile", path]
            i += 2
            continue
        out.append(args[i])
        i += 1
    return out


def run_engine(extra, tag, sample_disk=True):
    cfg, env = base_cfg()
    cmd = [cfg["exe"], *extra]
    reads = []
    stop = threading.Event()

    def sample():
        import psutil
        prev = psutil.disk_io_counters()
        t_prev = time.time()
        while not stop.is_set():
            time.sleep(0.5)
            cur = psutil.disk_io_counters()
            dt = time.time() - t_prev
            if dt > 0:
                reads.append((cur.read_bytes - prev.read_bytes) / dt / 2**20)
            prev, t_prev = cur, time.time()

    if sample_disk:
        threading.Thread(target=sample, daemon=True).start()
    p = subprocess.run(cmd, cwd=cfg.get("cwd") or str(ROOT), env=env, capture_output=True, text=True)
    stop.set()
    text = (p.stderr or "") + "\n" + (p.stdout or "")
    (ROOT / "logs" / f"profile-{tag}.log").write_text(text, encoding="utf-8", errors="replace")
    return text, reads, p.returncode


def report(text, reads, label):
    pre = re.search(r"prefill (\d+) tokens in (\d+) chunks, ([\d.]+) ms \(([\d.]+) tok/s\); experts streamed (\d+)"
                    r" \((\d+) by DMA, host ([\d.]+) ms\), resident (\d+)", text)
    prof = re.search(r"profile ([^\s:]+): (\d+) ranked pairs, built for (\d+) slots", text)
    print(f"\n--- {label} ---", flush=True)
    if prof:
        print(f"   profile: {prof.group(1)}  ({prof.group(2)} pairs, {prof.group(3)} slots)")
    if pre:
        _, toks, chunks, ms, rate, streamed, dma, host_ms, resident = (None, *pre.groups())
        tot = int(streamed) + int(resident)
        print(f"   prefill {rate} tok/s | host {float(host_ms)/1000:.1f} s | streamed {streamed} of {tot} "
              f"({100*int(streamed)/max(tot,1):.0f}% from files), resident {resident}")
        if reads:
            print(f"   disk peak {max(reads):.0f} MB/s, median {sorted(reads)[len(reads)//2]:.0f} MB/s")
    else:
        print("   no prefill line")


cfg, _ = base_cfg()
args = list(cfg["args"])

print("1) dumping routing from a trace prompt ...", flush=True)
trace_args = swap_profile([*args], SHIPPED)
trace_args = [a for a in trace_args if a != "--stats"]
dump = [*trace_args, "--tokens-file", TRACE_TOKENS, "--dump-routing", str(ROOT / "logs" / "trace.bin")]
t, reads, rc = run_engine(dump, "dump-routing")
print(f"   exit {rc}; trace lines: {len(re.findall(r'routing|trace', t, re.I))}")

print("2) building the workload profile ...", flush=True)
mp = subprocess.run([str(ROOT / ".venv" / "Scripts" / "python.exe"), str(ROOT / "tools" / "make_profile.py"),
                     "--base", SHIPPED, "--reorder", str(ROOT / "logs" / "trace.bin"), "--out", NEW_PROFILE],
                    cwd=str(ROOT), capture_output=True, text=True)
print((mp.stdout or "")[-1200:])
print((mp.stderr or "")[-400:])

print("3) measuring: shipped profile vs workload profile ...", flush=True)
for label, path in (("shipped profile", SHIPPED), ("workload profile", NEW_PROFILE)):
    a = swap_profile(list(args), path)
    text, reads, rc = run_engine([*a, "--tokens-file", MEASURE_TOKENS, "--stats"], label.split()[0])
    report(text, reads, label)
