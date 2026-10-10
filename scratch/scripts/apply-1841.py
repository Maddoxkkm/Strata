#!/usr/bin/env python3
"""Port #1841's functional half into generate.cpp, then report the new arms' switches.

The generate.cpp conflict resolution kept upstream's text and dropped this hunk; the whole point of #1841 is
the opt-in STRATA_EXPERT_CACHE_HEADROOM knob, so only the sizing half is ported (the PR's extra log line is
cosmetic and its context has drifted in this tree). The default is zero on HIP, so the default path stays as
it was - this just makes the knob available to A/B.
"""
import pathlib
import re
import subprocess
import sys

ROOT = pathlib.Path(r"D:\llm-dev\strata")
P = ROOT / "src" / "program" / "generate.cpp"
text = P.read_text(encoding="utf-8", errors="replace")

OLD = """            const size_t keep_free = ((size_t) o.vram_reserve_mib << 20) + (size_t) pipe_first +
                                     (size_t) persistent_prefill_b;
            size_t free_room = free_b > keep_free ? free_b - keep_free : 0;
"""
NEW = """            const size_t keep_free = ((size_t) o.vram_reserve_mib << 20) + (size_t) pipe_first +
                                     (size_t) persistent_prefill_b;
            // #1549/#1841: opt-in VRAM headroom for --expert-cache auto, STRATA_EXPERT_CACHE_HEADROOM=<fraction>.
            // Zero on HIP by default, so the default path is unchanged (see core/expert_cache.hpp).
            const size_t headroom = auto_cache ? (size_t) (free_b * strata::core::expert_cache_headroom()) : 0;
            size_t free_room = free_b > keep_free ? free_b - keep_free : 0;
            if (free_b > keep_free + headroom) free_room = free_b - keep_free - headroom;   // the old sizing stands when it cannot fit
"""

n = text.count(OLD)
if n != 1:
    print(f"  anchor found {n} times, expected 1 - not writing")
    sys.exit(1)
P.write_bytes(text.replace(OLD, NEW, 1).encode("utf-8"))
print("  #1841 headroom knob ported into generate.cpp")

print("\n=== the switches the new arms use ===")
for pat in ("STRATA_DECODE_TUNING", "STRATA_SELECT_WMMA", "STRATA_SELECT_SIMT", "STRATA_EXPERT_CACHE_HEADROOM",
            "STRATA_SGEMM", "STRATA_ROCBLAS_TUNING"):
    r = subprocess.run(["git", "-C", str(ROOT), "grep", "-n", pat, "--", "src", "include", "tools", "setup.py"],
                       capture_output=True, text=True)
    lines = [l for l in r.stdout.splitlines() if l.strip()][:3]
    print(f"  {pat}:")
    for l in lines:
        print("     ", l[:120])
    if not lines:
        print("      (not referenced)")
