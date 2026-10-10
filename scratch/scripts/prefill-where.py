#!/usr/bin/env python3
"""Where does prefill time actually go?  Runs one engine prefill while sampling, once a second:

  - GPU utilisation (ADLXPybind: what the card is actually doing)
  - disk read MB/s (psutil)
  - CPU % (psutil)

If the GPU sits low during prefill, the engine is waiting on the host path (staging/copies/disk); if it is near
saturated, prefill is GPU-bound and the host numbers are not the limiter.  Prints a per-second timeline plus the
engine's own summary lines.
"""
import json
import os
import pathlib
import re
import subprocess
import threading
import time

ROOT = pathlib.Path(r"D:\llm-dev\strata")
CFG = ROOT / "scratch/configs/strata-iq2_xs.json"
TOKENS = str(ROOT / "logs" / "prompt-ids.txt")
out_lines = []
stop = threading.Event()


def adlx_util():
    try:
        import ADLXPybind as adlx
    except ImportError:
        return None
    helper = adlx.ADLXHelper()
    if not str(helper.Initialize()).endswith("ADLX_OK"):
        return None
    sys_ = helper.GetSystemServices()
    perf = sys_.GetPerformanceMonitoringServices()
    gpu = sys_.GetGPUs()[0]

    def shutdown():
        # ADLXPybind 1.4.6 segfaults at interpreter teardown unless Terminate() ran (measured; see the telemetry
        # work): drop the references into the session first, then end it.
        try:
            globals().pop("_gpu", None)
            helper.Terminate()
        except Exception:
            pass

    import atexit
    atexit.register(shutdown)

    def read():
        try:
            m = perf.GetCurrentGPUMetrics(gpu)
            if m is None:
                return None, None, None
            out = (float(m.GPUUsage()), float(m.GPUVRAM()), float(m.GPUTotalBoardPower()))
            try:
                m.Release()
            except Exception:
                pass
            return out
        except Exception:
            return None, None, None
    return read


def sampler(read_gpu):
    import psutil
    prev = psutil.disk_io_counters()
    t_prev = time.time()
    while not stop.is_set():
        time.sleep(1.0)
        now = time.time()
        cur = psutil.disk_io_counters()
        dt = now - t_prev
        dr = (cur.read_bytes - prev.read_bytes) / dt / 2**20 if dt > 0 else 0
        prev, t_prev = cur, now
        g = read_gpu() if read_gpu else (None, None, None)
        cpu = psutil.cpu_percent(interval=None)
        out_lines.append((now, g[0], g[1] and g[1] / 2**20, g[2], dr, cpu))


def main():
    cfg = json.loads(CFG.read_text(encoding="utf-8-sig"))
    env = dict(os.environ)
    env.update({k: str(v) for k, v in (cfg.get("env") or {}).items()})
    libs = [str(p) for p in cfg.get("lib_dirs", [])]
    if libs:
        env["PATH"] = os.pathsep.join(libs + [env.get("PATH", "")])
    cmd = [cfg["exe"], *cfg["args"], "--tokens-file", TOKENS, "--stats"]
    read_gpu = adlx_util()
    th = threading.Thread(target=sampler, args=(read_gpu,), daemon=True)
    th.start()
    t0 = time.time()
    p = subprocess.run(cmd, cwd=cfg.get("cwd") or str(ROOT), env=env, capture_output=True, text=True)
    stop.set()
    text = (p.stderr or "") + "\n" + (p.stdout or "")
    (ROOT / "logs" / "prefill-where.log").write_text(text, encoding="utf-8", errors="replace")
    print(f"exit {p.returncode} after {time.time() - t0:.0f}s\n")
    print("  t     GPU%   VRAM GiB  power W   disk MB/s  cpu%")
    for i, (t, u, mem, pwr, dr, cpu) in enumerate(out_lines):
        flag = "  <-- prefill" if dr > 300 else ""
        print(f"  {i:>3}s {('%5.0f' % u) if u is not None else '   - ':>6}  "
              f"{('%8.1f' % mem) if mem else '       -':>8}  {('%7.1f' % pwr) if pwr is not None else '      -':>7}  "
              f"{dr:>9.0f}  {cpu:>5.0f}{flag}")
    for line in text.splitlines():
        if re.search(r"prefill \d|experts streamed|prompt copies|per token|pool multi|verify window", line):
            print("  |", line.strip()[:170])


if __name__ == "__main__":
    import atexit
    import sys
    try:
        main()
    finally:
        sys.stdout.flush()

