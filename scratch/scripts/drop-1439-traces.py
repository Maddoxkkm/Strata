#!/usr/bin/env python3
"""Drop the last #1439 traces from prefill.cpp (upstream's gemm has no bf16_immutable/report_bf16_cache)."""
import pathlib
import sys

P = pathlib.Path(r"D:\llm-dev\strata\src\prefill\prefill.cpp")
text = P.read_text(encoding="utf-8", errors="replace")

EDITS = [
    ("    // Resident WeightTable tensors outlive this Prefill; scratch/dequantized and drafter weights do not opt in.\n"
     "    gm.bf16_immutable(X, (const uint16_t*) w->data, Y, T, w->ne1 > 0 ? w->ne1 : 1, w->ne0, ldy, 0.0f, ldx);\n",
     "    gm.bf16(X, (const uint16_t*) w->data, Y, T, w->ne1 > 0 ? w->ne1 : 1, w->ne0, ldy, 0.0f, ldx);\n"),
    ("                        m.gemm.bf16_immutable(e16, pw.key_bf16, key, nb, HD, N);\n",
     "                        m.gemm.bf16(e16, pw.key_bf16, key, nb, HD, N);\n"),
    ("                    m.gemm.bf16_immutable(e16, pw.value_bf16, val, nb, N, N);\n",
     "                    m.gemm.bf16(e16, pw.value_bf16, val, nb, N, N);\n"),
    ("    m.gemm.report_bf16_cache();\n", ""),
]

for i, (old, new) in enumerate(EDITS, 1):
    n = text.count(old)
    if n != 1:
        print(f"  edit {i}: found {n} times, expected 1 - aborting")
        sys.exit(1)
    text = text.replace(old, new, 1)
    print(f"  edit {i}: ok")
P.write_bytes(text.encode("utf-8"))
left = [l for l in text.splitlines() if "bf16_immutable" in l or "report_bf16_cache" in l]
print(f"  #1439 traces left in prefill.cpp: {len(left)}")
