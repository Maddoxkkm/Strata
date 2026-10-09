#!/usr/bin/env python3
"""Bisect where ADLXPybind crashes on this machine: one step per argument, prints flushed.

    .venv/Scripts/python.exe adlx-bisect.py <step>

Steps: 1 initialize, 2 GetSystemServices, 3 GetGPUs, 4 first GPU's Name, 5 GPU properties,
6 GetPerformanceMonitoringServices, 7 GetCurrentGPUMetrics, 8 the four readings.
"""
import sys


def say(*a):
    print(*a, flush=True)


def main():
    step = int(sys.argv[1]) if len(sys.argv) > 1 else 8
    import ADLXPybind as adlx
    say(f"import ok, module {adlx.__name__}")
    helper = adlx.ADLXHelper()
    rc = helper.Initialize()
    say(f"step 1 Initialize -> {rc}")
    if step < 2:
        return
    sys_ = helper.GetSystemServices()
    say(f"step 2 GetSystemServices -> {sys_!r:.120}")
    if step < 3:
        return
    gpus = sys_.GetGPUs()
    say(f"step 3 GetGPUs -> {type(gpus).__name__} len {len(gpus)}")
    if step < 4:
        return
    gpu = gpus[0]
    say(f"step 4 first gpu object -> {gpu!r:.120}")
    name = gpu.Name()
    say(f"step 4 gpu.Name() -> {name!r}")
    if step < 5:
        return
    for meth in ("PCIBusNumber", "PCIDeviceNumber", "TotalVRAM", "UniqueId", "DeviceId", "RevisionId"):
        try:
            say(f"step 5 gpu.{meth}() -> {getattr(gpu, meth)()}")
        except Exception as e:
            say(f"step 5 gpu.{meth}() -> {type(e).__name__}: {e}")
    if step < 6:
        return
    perf = sys_.GetPerformanceMonitoringServices()
    say(f"step 6 GetPerformanceMonitoringServices -> {perf!r:.120}")
    if step < 7:
        return
    metrics = perf.GetCurrentGPUMetrics(gpu)
    say(f"step 7 GetCurrentGPUMetrics -> {metrics!r:.120}")
    if step < 8:
        return
    for meth in ("GPUUsage", "GPUVRAM", "GPUPower", "GPUTemperature", "GPUClock"):
        try:
            say(f"step 8 metrics.{meth}() -> {getattr(metrics, meth)()}")
        except Exception as e:
            say(f"step 8 metrics.{meth}() -> {type(e).__name__}: {e}")
    helper.Terminate()
    say("done")


if __name__ == "__main__":
    main()
