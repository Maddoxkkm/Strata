# Open PRs triaged against this machine (2026-10-07)

187 open PRs at the time of checking. Every candidate below is based on **82f46a8 — our exact HEAD — so all of
them apply as-is**; the maintainer keeps them rebased on main.

The box: Windows 11, Radeon RX 7900 XTX (gfx1100, RDNA3, 24 GB), HIP build from
`.rocm-win` (TheRock ROCm 10.2.0a20260930, hipBLASLt 1.5.0 = version 100500), Qwen3.8-Flash-Next **IQ2_XS**,
32 GB RAM, low-RAM resident mode with `--mmap-experts`, 512K context with `--kv int8 --kv-resident`, prefill is
the bottleneck (I/O-bound: host streaming was 9.4 s of 17.8 s before `STRATA_RESIDENT_PIN=1`).

Method: scored all 187 titles+bodies against this stack (`prs-triage.py`), fetched the real diffs of the 40
candidates from github.com (`prs-probe.py`, saved in `prs/<n>.diff`), and checked the diffs for platform
gating (HIP vs CUDA-only), the knobs they add, and the authors' own numbers.

## Tier A — direct, measured benefit for this box; cheap to take

| PR | What | Evidence | Cost / catch |
|---|---|---|---|
| **#1289** | The gfx1100 hipBLASLt table gains the **small-T expert GEMM** geometry `f16 1280 2560 1280` (T=8..999) + `bf16 10240 2560 10240` | On **GSQ-RCO IQ2_XS on gfx1100** at 192K ctx: `STRATA_HIPBLASLT_VERBOSE=1` showed **642 fallbacks over 642 distinct T values** with the 26-row table; the extra rows gave **711 → 938 tok/s prefill (+31.9%)**, `fallbacks=0`, decode unchanged | **The rows ship in `...-100401.txt` (hipBLASLt 1.4.1) — our engine reads `...-100500.txt` (1.5.0), so the file does not transfer.** Our 100500 table has `bf16 10240 2560 10240` but **0 rows for `f16 1280 2560 1280`** → we have the same gap. Fix = re-tune those 2 geometries with our own `tune_hipblaslt.exe` (solution IDs are version-specific) and append the rows |
| **#1240** | Avoid an unused MTP branch stream on HIP | +3 lines, 1 file | Trivial, we use MTP; free |
| **#1323** | Prefill: batched unbuffered stager reads (`STRATA_STAGER_BATCH`), release the experts.bin view once reads are unbuffered (`STRATA_KEEP_MAPPING`) | Our prefill is I/O-bound; this is the stager read path | 4 files, platform-neutral |
| **#1282** | `STRATA_PREFILL_CPU_SHARE=auto`: a small chunk's least-routed experts go to the CPU pool | We already set `STRATA_PREFILL_AUTO_MAX/MMQ/RING`, which sit next to this | 3 files |
| **#1283** | `bytes_needed` sizes the MoE buffers for the layout the init picks | Correctness of the prefill buffer sizing | 3 files |
| **#1109** | docs: `GPU_PINNED_MIN_XFER_SIZE=1048576` stopped a gfx1030 `--mmap-experts` slowdown | We run `--mmap-experts` + `STRATA_RESIDENT_PIN=1`; a free env var to try (gfx1030, so verify on ours) | docs only |
| **#1332 / #1345** | `--calibrate`: the PCIe-share sweep reaches 1.0; the sweep visits every value in every round | Our `--calibrate` kept nothing (upstream gates calibration to NVIDIA); these are the AMD-relevant calibration fixes | tools only |

## Tier B — plausible, needs a build or more setup

| PR | What | Notes |
|---|---|---|
| **#1297** | **On-device autotuning for gfx1100 decode** (`tools/hip/tune_decode.cpp`, `tools/hip/autotune.py`, writes `STRATA_DECODE_TUNING`): rows per block of the decode GPU expert kernels (gate/up, down) and `iq_mmvq`, plus draft floor (`--spec-min-p`) and CPU workers (`--pool-workers`) | Explicitly written for the RX 7900 XTX: *"Strata's AMD backend runs CUDA-shaped kernels whose launch shapes were chosen on an RTX 5070."* Bitwise-equal outputs, ~1–3 min + 4 engine starts, needs a HIP build of the `tune_decode` target (~2000 lines, 15 files). Knobs like `STRATA_EXPERT_V2` invalidate it |
| **#1298** | gfx110x fp16 (rocWMMA) qsa-select scorer arm (`STRATA_SELECT_WMMA`) | gfx110x is our arch; we already proved gfx11 WMMA is exact and fast locally (27.2M MMAs/s) |
| **#1181** | The verify window's GPU plan in O(n) instead of O(n²) | Long-context verify-window planning; 4 files |
| **#1184** | AMD HIP: the primary ordinal, and the helper caches beside the resident RAM mode (`STRATA_PRIMARY_DEVICE`, `STRATA_HIP_ARCHS`) | Our exact mode (resident RAM + HIP) |
| **#1151** | The QSA block scores on rocBLAS SGEMM, measured at engine start (`STRATA_SELECT_SGEMM`, opt-in) | HIP-general; 178 HIP mentions |
| **#1324** | File tier: an LRU part of the RAM budget (`--resident-lru-gib`), elastic under memory pressure | Directly about our 32 GB + resident mode pressure |
| **#1232 / #1231** | `--kv-grow` with `--batch`; a run that cannot lend cache slots maps the whole window up front | Long-context memory behaviour |
| **#1262** | `STRATA_HC_REQ8`: hyper-connection projections requantized to int8 + fp32 scale per 32 | Memory/bandwidth; numbers in the diff are 91–99.7% |
| **#1340** | Core: retain fixed RAM originals during native async exchanges (`STRATA_EXCHANGE_*`) | +5881 lines, 13–14% numbers — heavy, later |
| **#1264** | **verify**: the batched K/V append writes a streamed K8V4 state's host copy (#1188, #1169) | 7 lines, a test, not the fix — relevant to our known k8v4 + streaming corruption |
| **#1281** | Sampler: coupled drafts with Gumbel-max (`STRATA_SPEC_GUMBEL=1`): +7 points | Decode via spec acceptance |
| **#1316 / #1305** | Spec/lookup: re-probe stale lookup window costs; `--lookup-chain 1/2` window cap | Draft path |
| **#1287** | **feat(vision): Windows HIP image encoding** | Would enable image input on our box (today it is Linux-only on AMD); 647 lines + a build |
| **#1325** | File tier (Windows): each expert from experts.bin **and a mirror on a second drive** (+8.7%) | For us the second drive is a mechanical HDD, so a mirror would likely *cost*; its `STRATA_STAGER_BATCH` / `STRATA_UNBUFFERED_LOAD` knobs are the reusable part |
| **#1265 / #1266** | Engine updater: verify, stage, all-or-nothing swap, rollback (+ a UI card) | Ops convenience for our manual `--update` + git pull |

## Tier C — information from the same or similar hardware (tuning guidance, no code win)

- **#1293** — RX 7900 XTX, **ROCm 7.1.1 vs ROCm 10.2 nightly**: tells us whether our TheRock 10.2 nightly is right.
- **#1292** — RX 7900 XTX (gfx1100) IQ3_S rates row, 1K–128K.
- **#1318** — R9700 numbers for hipBLASLt 1.4.1 and `STRATA_HIP_WMMA`.
- **#1321** — IQ2_XS speed report on a Radeon AI PRO R9700 (our quant).
- **#1278** — run the K-quant MMQ test on HIP builds; UD-Q4_K_XL measured on an R9700.
- **#1173** — community report, RX 7900 XTX on Windows 11, IQ3_S, 0.1.40 (our platform).
- **#1354** — docs: the expert cache is a budget, and **on Windows an over-sized one pages instead of failing**.
- **#1140 / #1270 / #1078 / #1199** — 2× RX 7900 GRE (gfx1100) layer split, 2× RX 6900 XT, RX 6800M self-built HIP on Windows, RTX 3090 eGPU IQ2_XS vs IQ3_XXS.
- **#1148** — `hip_prefill_wmma_gemm_parity` skips on a card without matrix cores.

## Tier D — not for this box

CUDA-only kernels/builds (#1336 #1338 #1339 Q8 SM120/SM90 paths, #1279 P100 VMAD, #1246 #1358 #1359 CUDA
toolkit, #1335 QFUSE, #1237 `cudaHostAlloc`, #1118-series), other GPUs (#1295 Intel Arc, #1334 890M,
#1127/#1361 gfx1151, #1313/#1321 gfx1201, gfx906 series), other models (#1343 CYBER-FROST, #1315 GLM-5.3 —
its author says prefill "really sucks, avoid testing"), and serve/UI features that do not touch our
performance (#1328 JSON layouts, #1327 video, #1326 IPv6, #1204 Chinese UI, #1202 dashboard path,
#1362/#1314 tool-call rendering, #1209 concurrency, #1249 pipelined batch, #1253 multi-GPU batch MTP,
#1251/#1223 peer-device, #1269/#1271/#1273 session spill, #1093/#1114 Monitor UX).

## What I would take, in order

1. **The #1289 idea, re-tuned for hipBLASLt 1.5.0**: tune `f16 1280 2560 1280` (T=8..999, buckets) and
   `bf16 10240 2560 10240` with `tune_hipblaslt.exe` against 100500, append to our
   `gfx1100-hipblaslt-100500.txt`, then verify `fallbacks=0` with `STRATA_HIPBLASLT_VERBOSE=1` and measure
   prefill at long context. No build, no code change, and the evidence is on our exact GPU + quant.
2. **#1240** (+3 lines) — take it for free.
3. **#1323 + #1282 + #1283**: the prefill stager/CPU-share path, where our remaining I/O time sits.
4. **#1297**: build `tune_decode` and run the gfx1100 decode autotuner (kernels + draft floor + pool workers).
5. **#1287** if image input on Windows is wanted, and **#1264** to keep an eye on the k8v4 + streaming fix.

Artifacts: `prs-open.json` (all 187), `prs-triage.py`, `prs-probe.py`, `prs/<n>.diff` (40 cached diffs),
`prs-probe-out.txt` / `prs-probe-out2.txt` (the per-PR summaries).

---

# #1289 taken locally: the rows had to be re-tuned for hipBLASLt 1.5.0 (2026-10-07)

## What landed upstream and why it did not reach us

The content of #1289 is in main, committed by hand as **`a45783c7`** ("hip: the gfx1100 100401 table covers the
small-T expert GEMM (prompt +31.9%)", 2026-10-07 01:23) - the PR itself is `closed`, `merged: false` - and
v0.1.40.2's notes carry it ("RX 7900 XTX hipBLASLt table rows for small prompt chunks (+32% prompt, measured by
the author, #1289)"). The rows went into **`gfx1100-hipblaslt-100401.txt`** (28 -> 45 lines: 9 `f16 1280 2560 1280`
rows and 8 `bf16 10240 2560 10240` rows). This install runs hipBLASLt **1.5.0 = version 100500**, and
`src/prefill/hipblaslt_tuning.hpp:68` requires an **exact version match** ("hipBLASLt version mismatch: file=..."),
so the 100401 table is never read here. main's `gfx1100-hipblaslt-100500.txt` is unchanged from ours: 34 lines,
0 small-T rows. Updating the checkout would not have changed this.

## The defect reproduced on this box

With `STRATA_HIPBLASLT_VERBOSE=1`, an engine run on our config logged:

```
prefill gemm: hipBLASLt tuning enabled (32 rows, gfx1100, version 100500)
prefill gemm: Lt fallback; no calibration for dtype=f16 T=99 N=1280 K=2560 ldy=1280
prefill gemm: Lt fallback; no calibration for dtype=f16 T=4  N=1280 K=2560 ldy=1280
...
```

**383 fallbacks in the "before" arm, every one on `dtype=f16 N=1280 K=2560 ldy=1280`, T = 1..2089, all distinct** -
the geometry the PR adds, and the same failure shape the author reported (642 fallbacks over T 1..1873 there).
Only the f16 geometry was missing; our table already carries `bf16 10240 2560 10240`.

## What was done

`build-hip-win/tune_hipblaslt.exe` (built from this tree, workspace 32 MiB as the engine uses) was run for
`--case f16,<T>,1280,2560,1280` at T = 8, 16, 32, 42, 64, 128, 256, 512, 999, 1536, 2089. Launched from git-bash
the MSVC exe cannot resolve the UCRT DLLs, so `tools/hip/run-tuner.bat` wraps it with the same ROCm + vcvars64
environment `rebuild-windows.bat` sets up. The 11 winning rows were appended to
`tools/hip/gfx1100-hipblaslt-100500.txt` (32 -> 43 rows; backup at `...100500.txt.bak-preregress`, tuned copy at
`logs/table-43rows-tuned.txt`):

```
f16 1280 2560 1280 8 2117      f16 1280 2560 1280 256 2106
f16 1280 2560 1280 16 2104     f16 1280 2560 1280 512 2106
f16 1280 2560 1280 32 2104     f16 1280 2560 1280 999 2106
f16 1280 2560 1280 42 2104     f16 1280 2560 1280 1536 2106
f16 1280 2560 1280 64 2104     f16 1280 2560 1280 2089 2106
f16 1280 2560 1280 128 2105
```

The solution IDs match upstream's 100401 table almost exactly (16-64 -> 2104, 128 -> 2105, 256+ -> 2106), except
T=8 (2117 here vs 2104 there) - independent confirmation that the tuning is right and that IDs do shift between
hipBLASLt versions. The tuner measured this solution at **3.68x the hipBLAS path the fallback uses** for T=64.

## Measured result: the fallbacks go, the end-to-end gain does not follow

Same protocol both arms (server restarted, 3 warm-up requests, then 4 rounds of a ~4,159-token prompt with a
unique nonce each round so the conversation cache cannot answer, `max_tokens=1`):

| arm | table | `Lt fallback` | engine prefill, 4,159 tokens | HTTP wall |
|---|---|---|---|---|
| before | 32 rows | **383** | ~22 s (≈189 tok/s) | 22.1 / 23.0 / 23.0 / 22.3 s |
| after | 43 rows | **0** | ~20-22 s (≈190-208 tok/s) | 22.8 / 21.7 / 16.7 / 19.6 s |

So: **launch-level fix complete (383 -> 0, deterministic), per-GEMM 3.68x, end-to-end prefill ~5-9% on wall
median (22.65 -> 20.65 s) - inside this box's run-to-run spread, not the +31.9% upstream measured.** The likely
reason is the one already established here: **our prefill is I/O-bound** (host expert streaming was 9.4 s of
17.8 s in the `--stats` profile), so removing GEMM fallbacks shortens a slice that is not the critical path. The
upstream author's box reached 711-938 tok/s on this geometry; ours does ~190 tok/s on the same shape, i.e. our
prefill is 4-5x slower before the table even matters.

Conclusion for this box: keep the 43-row table (strictly better, no fallbacks), but the prefill lever that
matters here is the **I/O path** - #1323 (batched unbuffered stager reads), #1325 / #1324 (RAM/disk tier), and the
resident-pin behaviour - not the expert GEMM.

## Side finding: the config had lost `STRATA_RESIDENT_PIN`

`strata-iq2_xs.json`'s `env` no longer carried `STRATA_RESIDENT_PIN=1` (the setting accepted earlier - the
347 -> 634 tok/s change), leaving the `STRATA_PREFILL_*` keys in place. It was restored (backup
`strata-iq2_xs.json.bak-pretune`), and the engine confirms it engages:
`FileExpertSource: locked resident cache complement ready: resident 18.94 GiB, pinned 0.00 GiB; page-locking
refused (out of memory); locked 19394 MiB via working-set minimum + VirtualLock` - the working-set lock, as
before, not a true page-lock. `STRATA_HIPBLASLT_VERBOSE=1` was also added and is still set: it prints the table
summary and a line per fallback, and is silent otherwise.

Artifacts: `tools/hip/run-tuner.bat` (tuner wrapper), `tools/hip/gfx1100-hipblaslt-100500.txt` (43 rows),
`logs/tune-newrows.log` + `logs/newrows-100500.txt` (the tuning run and its rows), `logs/ab-before.out`,
`logs/ab-after.out`, `logs/server-before.log`, `logs/server-after.log`, `prefill-ab.py` (the warm A/B probe),
`logs/table-ab-*.log` (the engine-level harness attempt - the CLI needs `--tokens`, so the server's engine log
was used instead).
