#!/usr/bin/env python3
"""Print the Monitor's GPU-relevant readings from the server's /metrics, for a before/after comparison.

    .venv/Scripts/python.exe metrics-gpu.py [label]
"""
import json
import sys
import urllib.request

LABEL = sys.argv[1] if len(sys.argv) > 1 else "metrics"


def main():
    with urllib.request.urlopen("http://127.0.0.1:8080/metrics", timeout=20) as r:
        d = json.load(r)
    hw = d.get("hardware") or {}
    st = d.get("hardware_static") or {}
    print(f"--- {LABEL} ---")
    print(f"  hardware_static.gpu_name : {st.get('gpu_name')}")
    for k in sorted(hw):
        if any(s in k for s in ("gpu", "temp", "power", "util", "mem", "pcie")):
            print(f"  hardware.{k:<22} : {hw[k]}")
    hist = d.get("history") or {}
    for k in ("gpu_util", "gpu_mem_used", "gpu_temp", "gpu_power", "gpu_pcie_rx_mb"):
        v = hist.get(k)
        if v:
            tail = [x for x in v[-5:]]
            print(f"  history.{k:<20} : last 5 of {len(v)}: {tail}")


if __name__ == "__main__":
    main()
