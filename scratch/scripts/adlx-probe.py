#!/usr/bin/env python3
"""Read an AMD card's load, VRAM, temperature and power on Windows through ADLXPybind.

    .venv/Scripts/python.exe adlx-probe.py

AMD's supported client for this is the ADLXPybind wheel (the raw ADLX vtables cannot be called from ctypes and
the old ADL Overdrive calls answer "not supported" on current Adrenalin), so it is used the way PR #1224
specifies: as an optional import, absent meaning "no readings" rather than an error.

This probe is the groundwork for the `serve/telemetry.py` change: it prints what the API actually returns on this
machine, including the PCI bus number HIP orders cards by.
"""
import sys


def main():
    try:
        import ADLXPybind as adlx
    except ImportError:
        print("ADLXPybind is not installed: on Windows the AMD cards would keep reading nothing (as before).")
        return 1

    helper = adlx.ADLXHelper()
    rc = helper.Initialize()
    print(f"ADLXPybind {getattr(adlx, 'ADLX_PY_VERSION', '?')}  Initialize() -> {rc} "
          f"({'ok' if rc == adlx.ADLX_OK else 'failed'})")
    if rc != adlx.ADLX_OK:
        return 1
    try:
        sys_ = helper.GetSystemServices()
        gpus = sys_.GetGPUs()                       # a plain list through pybind11
        print(f"GPUs: {len(gpus)}")
        print(f"  system services methods: {[m for m in dir(sys_) if not m.startswith('_')][:14]}\n")
        perf = sys_.GetPerformanceMonitoringServices()
        print(f"  perf services methods  : {[m for m in dir(perf) if not m.startswith('_')][:16]}\n")
        for i, gpu in enumerate(gpus):
            name = gpu.Name()
            print(f"[{i}] {name}")
            print(f"    gpu methods: {[m for m in dir(gpu) if not m.startswith('_')][:26]}")
            metrics = None
            for call in (lambda: perf.GetCurrentGPUMetrics(gpu),
                         lambda: perf.GetCurrentGPUMetrics(0, gpu),
                         lambda: perf.GetGPUMetrics(0, gpu)):
                try:
                    metrics = call()
                    break
                except Exception as e:
                    last = e
            if metrics is None:
                print(f"    no metrics object ({last})")
                continue
            print(f"    metric methods: {[m for m in dir(metrics) if not m.startswith('_')][:26]}")
    finally:
        helper.Terminate()
    return 0


if __name__ == "__main__":
    sys.exit(main())
