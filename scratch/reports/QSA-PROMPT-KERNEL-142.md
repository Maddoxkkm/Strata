# The QSA prompt attention on gfx1100 (0.1.42)

## 1. Why the prompt path was running the decode kernel

Issue **#1712**'s `rocm-debug-agent` trace (2x RX 7900 XTX) says it plainly: on gfx1100 `qsa_prompt` returns
false, so **every prompt chunk runs the decode attention kernel**. The tree agrees - `qsa_prompt_attn_batch`
has a HIP branch that only takes the matrix-core path when `hip_wmma_usable()` is true, and that helper
requires `STRATA_HIP_WMMA=1` plus `gfx12* | gfx_arch_is_gfx11_wmma(arch)`. So the kernel existed, was
compiled for this card (`#if defined(__gfx1100__) || ... || defined(__gfx1151__)` with its own
`STRATA_PA_GFX11` fragment layout), and was simply switched off. The "gfx12 only" notes in the header and in
CMake are stale.

## 2. Measured (ab-group, one engine restart per arm, same prompt files)

| arm | 4K | 16K |
| --- | --- | --- |
| matrix-core attention off | 885.7 | 1577.8 |
| **+ `STRATA_HIP_WMMA=1`** | **987.3 (+11.5%)** | **1936.4 (+22.7%)** |
| attention only | 890.6 | 1766.8 |
| **+ `STRATA_SELECT_WMMA=1`** (#1298's scorer arm) | **935.4 (+5.0%)** | **1967.9 (+11.4%)** |

Both are now in the live config: `STRATA_HIP_WMMA=1`, `STRATA_SELECT_WMMA=1`. The path needs `--kv int8`
(mode 1: `k_q`/`v_q` + scales); a `k8v4`/`q4_0` KV would refuse it, so the int8 KV choice now also gates this.

## 3. Validation

The HIP parity test for exactly this kernel is `hip_prompt_attn_wmma` (CMake: "skips off gfx12", but the
test's own guard skips only for arches that are neither gfx11 nor gfx12, so it does run here). Built with
`-DSTRATA_BUILD_TESTS=ON` and run on gfx1100:

```
PASS int8 ctx 32768, 2048 queries: vs FP64 old 2.51e-06 new 4.05e-06 (output scale 3.3);
      new vs old 8.2e-06 (2.2e-06 of scale); 34.340 -> 8.362 ms per chunk (4.11x)
PASS int8 ctx 1500, 1500 queries:  ... new vs old 2.6e-06 of scale; 13.888 -> 2.239 ms (6.20x)
PASS int8 ctx 2100, 256 queries:   ... new vs old 1.4e-06 of scale;  6.368 -> 1.065 ms (5.98x)
FAILURES: 0
```

So on this card the matrix-core kernel is at FP32-level accuracy (4e-06 against FP64, the old kernel's is
2.5e-06), agrees with the old kernel to ~2e-06 of output scale (the test's criterion is 1e-4), and the
attention chunk itself is **4-6x faster** - which is what the prefill numbers above are made of.
`scratch/scripts/accuracy-ab.py` additionally compares answers with the path on and off.

## 4. Checked and NOT ours

- **#1821** "qsa_prompt_attn: int8 K/V prefetched in registers": the CUDA v1/v2 kernel (it reasons about
  Turing's 64 KB SMEM), not the WMMA path.
- **#1888** "QSA decode attention: split each query's cells": `#if defined(__HIPCC__) return false;` - CUDA
  sm_80+ only.
- **#1367** INT8 tensor-core prompt attention: CUDA IMMA.
- **#1297**'s gfx1100 decode autotuning still needs a table: `tools/hip/tune_decode` has to run once and the
  engine reads it via `STRATA_DECODE_TUNING=<path>` (untried so far - the kernels and the tool are in).

## 5. Accuracy, end to end

`accuracy-ab.py`, three prompts, one restart per mode: `17*23` -> `391` both ways, the train-average -> `84
km/h` both ways, and the fraction comparison differed once (matrix cores said `7/11`, the old kernel said
`9/13`). That last one is **sampling noise, not the kernel**: asking the live matrix-core path six times in
one session returns `9/13`, `7/11`, `7/11`, `7/11`, `9/13`, `7/11` - a 2-bit model flipping a comparison whose
margin is 8%, while the kernel's perturbation is 2e-06 of the output scale. The parity numbers above are the
bound that matters; the model is simply not deterministic on that question at IQ2_XS.
