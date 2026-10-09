#!/usr/bin/env python3
"""What ADLXPybind actually returns for an AMD card on this machine (and where it crashes).

    .venv/Scripts/python.exe adlx-metrics.py

Prints every metric method of IADLXGPUMetrics with its value, then the identity fields used to match an ADLX GPU
to the engine's GPU index. Ends with os._exit(0): ADLXPybind 1.4.6 segfaults at interpreter teardown on this
machine (after Terminate(), the process dies with SIGSEGV), so the normal exit path cannot be used here.
"""
import os


def say(*a):
    print(*a, flush=True)


def main():
    import ADLXPybind as adlx
    helper = adlx.ADLXHelper()
    rc = helper.Initialize()
    say(f"Initialize -> {rc}")
    sys_ = helper.GetSystemServices()
    gpus = sys_.GetGPUs()
    perf = sys_.GetPerformanceMonitoringServices()
    for i, gpu in enumerate(gpus):
        say(f"\n[{i}] {gpu.Name()}")
        for f in ("VendorId", "DeviceId", "RevisionId", "UniqueId", "TotalVRAM", "VRAMType", "Type",
                  "ASICFamilyType", "IsExternal", "PNPString"):
            try:
                say(f"    {f:<14} : {getattr(gpu, f)()}")
            except Exception as e:
                say(f"    {f:<14} : {type(e).__name__}")
        m = perf.GetCurrentGPUMetrics(gpu)
        say(f"    metrics object : {m!r:.60}")
        names = [x for x in dir(m) if not x.startswith("__")]
        say(f"    methods ({len(names)}): {names}")
        for meth in names:
            if not callable(getattr(m, meth, None)):
                continue
            try:
                v = getattr(m, meth)()
                say(f"      {meth:<22} -> {v!r}")
            except Exception as e:
                say(f"      {meth:<22} -> {type(e).__name__}: {str(e)[:50]}")
    say("\n(readings collected; exiting with os._exit to avoid the teardown segfault)")
    os._exit(0)


if __name__ == "__main__":
    main()
