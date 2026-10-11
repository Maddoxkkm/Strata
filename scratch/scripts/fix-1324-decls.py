#!/usr/bin/env python3
"""Fix the two declarations my #1324 header merge dropped: lru_cap_ and the StageFree struct.

The cpp (auto-merged from the PR) references both. Freeing matters here: with this merge the buffers are
allocated through StageBufFree{pinned} (cudaFreeHost or delete[]), so the LRU must free with `.reset()` on the
unique_ptr, which invokes that same deleter. StageFree is kept only because the PR's definition remains in the
cpp; it must not be used on a pinned pointer. This prints the shrink path so that assumption is visible.
"""
import pathlib
import re
import sys

ROOT = pathlib.Path(r"D:\llm-dev\strata")
H = ROOT / "include" / "strata" / "core" / "expert_source.hpp"
C = ROOT / "src" / "core" / "expert_source.cpp"

text = H.read_text(encoding="utf-8", errors="replace")

ANCHOR = "    std::vector<std::unique_ptr<uint8_t[], StageBufFree>> stage_buf_;\n"
ADD = ("    uint64_t lru_cap_ = ~0ull;                ///< the elastic LRU's current ceiling on the pool's bytes\n"
       "    struct StageFree { void operator()(uint8_t* p) const; };   ///< the PR's page-aligned free: unused here,\n"
       "                                                              ///< this merge allocates through StageBufFree\n")
if ANCHOR not in text:
    print("  anchor missing"); sys.exit(1)
if "lru_cap_ = ~0ull" in text:
    print("  lru_cap_ already declared")
else:
    text = text.replace(ANCHOR, ANCHOR + ADD, 1)
    H.write_bytes(text.encode("utf-8"))
    print("  added lru_cap_ + StageFree to expert_source.hpp")

print("\n=== the LRU's free path (must free through the unique_ptr's deleter) ===")
src = C.read_text(encoding="utf-8", errors="replace").splitlines()
start = next((i for i, l in enumerate(src, 1) if "lru_shrink_to" in l and "::" in l), None)
if start:
    for l in src[start - 1:start + 26]:
        print("   ", l[:118])
frees = [l.strip()[:110] for l in src if ".reset()" in l or "StageFree{}" in l or "VirtualFree" in l]
print("\n=== free sites ===")
for f in frees[:10]:
    print("   ", f)
