# v0.1.42 merge + RDNA3 PR reassessment (2026-10-11)

## 1. What the pull brought

`main` fast-forwarded **fb58e0db (0.1.41) → 61b3fb5d (v0.1.42)**: 235 commits, one release. Nothing in it
invalidated our tree: the same GGUF, the same pack, the same mount/flags.

Relevant to this box, from the release's own commits:

- **`115e8ce3` Windows HIP: the auto cache's 2560 MiB reserve floor also covers 16 GB cards** (#1709) - the
  sizing rule we lean on (`--expert-cache auto`).
- **`a6346cdc` conversation snapshot copies: a private non-blocking stream instead of the legacy stream** -
  it names a HIP capture conflict, i.e. a Windows/HIP stability fix.
- `47cb7310` / `7f3c0da2` telemetry: the AMD PCIe link reader - **Linux sysfs only** (it walks
  `/sys/bus/pci` hops), so it does not overlap our Windows ADLXPybind reader.
- CUDA-only and therefore inert here: `aa7b0cb1` (adaptive `--pcie-frac` from the CPU pool's speed),
  `b4e3407b` (`STRATA_ROUTE_TAIL_SKIP=7` on by default - explicitly "not ... HIP"), `f63a57e7` (#1757,
  Pascal/Volta tiled BF16 conversion).
- `268647d2` (expert blobs from a helper's VRAM cache) and `35405002`/`10be33ff` (HAL) are helper-GPU/SYCL.
- **#1841 and #1656 merged upstream** - the two we had ported and measured in batch 2 are now redundant, so
  they were dropped from our set rather than re-ported.

## 2. The merge

Carried over untouched (upstream never touched them): the 45-row `gfx1100-hipblaslt-100500.txt`, the
ADLXPybind telemetry patch, `tools/hip/*` build tooling, `stop-server.bat`, `tools/make-options-inventory.py`,
`scratch/`.

Re-applied and hand-merged where upstream had moved the same code:

| patch | resolution |
| --- | --- |
| #1451 PLE host buffers, lazy | kept (live on HIP); upstream added a `src` argument to `bytes_needed_no_ring` - both kept |
| #1107 grouped short-prompt staging | kept (`stage_slots` behind upstream's new `bool src` signature) |
| #1660 native-layout MMQ resident sort | kept as-is |
| #1520 `release()` doc | kept (upstream's `note_async_read` decl preserved alongside) |
| #1381 format-agnostic MTP grouped path | kept; upstream's new `rr_res_` route-resident block kept too |
| #1439 BF16->FP16 conversion cache | **dropped**: inert on HIP (`!defined(__HIPCC__)`) and upstream rewrote that path for Pascal/Volta |

Measured (same config, one restart per arm):

| arm | 4K | 16K |
| --- | --- | --- |
| 0.1.41 + batch 1 (what was live) | 573.4 (cold first arm) | 1436.6 |
| **0.1.42 + local set** | **783.9** | **1516.6 (+5.6%)** |

## 3. RDNA3 reassessment: what is worth having

Applied on top, all applying cleanly to 0.1.42, measured **+4.4% at 16K** and +1.9-8.7% at 4K over the
0.1.42 merge alone (adopted; the live config now runs `strata-142-4pr.exe`):

| PR | what | size |
| --- | --- | --- |
| **#1752** | HIP: unbuffered file-tier reads **and a locked expert arena** (#1691) | 11 lines |
| **#1897** | setup: build the HIP engine **with the K-quant MMQ prompt kernels** | 23/5 |
| **#1911** | expert cache: `STRATA_VRAM_FREE=device` reads the whole card's free VRAM | 96/1 |
| **#1499** | core: helper rows written straight to the mapped output | 5/1 |

Still open, and the shortlist for the next cycle:

1. **#1297** gfx1100 decode autotuning - needs the **bisect** we planned: batch 2 showed its `iq_kernels.cu`
   half costs 23% when no tuning table is present.
2. **#1909** kernels: process all groups in fused GU and LDS down launches (+148/-103, applies cleanly).
3. **#1324** LRU RAM tier - a dedicated port (its CLI half alone does not compile).
4. **#1167** rocBLAS prompt table - RDNA2-measured; a gfx1100 table needs `tools/hip/tune_rocblas` first.
5. **#1298 / #1151** QSA scorer arms - opt-in; inside the batch-2 set the SIMT arm recovered most of the loss
   (836.8 vs 666.9), worth a standalone measure.

Reading, for breadcrumbs on our exact card: **#1459** (RX 7900 XTX + 6800 XT helper layout, 1M contexts),
**#1406** (RX 7900 XTX on WSL2, Coder), **#1376** (RX 7900 XT IQ3_S/IQ3_XXS), **#1655** (4x RX 7900 XT,
Flash-Next IQ3_S at 262K, five opt-ins on/off - merged in 0.1.42), and #1873/#1749/#1360 for gfx1151
(Strix Halo, RDNA3.5 - adjacent, not ours).

Telemetry cluster still open: #1224 (ADLX Windows readings - the work our patch is based on), #1434, #1871,
#1877, #1152. Ours remains the only Windows path that reports AMD **power** (14-22 W).

Skipped: **#1820** (qwen35moe - not this model: our GGUF says `general.architecture = qwen4exp`), **#1471**
(needs fully resident KV, which costs us 12% prefill), **#1912** (`--pool-affinity` for hybrid CPUs; the
9800X3D is not hybrid).
