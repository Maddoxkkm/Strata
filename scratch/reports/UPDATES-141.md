# v0.1.41 pull, rebuild, and the parameter work (2026-10-08 late)

Continues `TRIAGE-141.md` (the pull + issue/PR triage) and `UPDATES-1403.md`. Four things were asked for: the
rebuild on the new release, the commit-charge measurement, the CPU-share check at 1,000 tokens, and a regenerated
options reference. All four are below, plus what the triage said about each patch.

## 1. The patch set on 0.1.41, checked patch by patch

`main` is at `fb58e0db` (post-v0.1.41). Each of our patches was checked against upstream rather than re-applied
blindly - three of them turned out to be unnecessary or inert here:

| patch | verdict | why |
|---|---|---|
| **#1323** batched stager reads + close the mapping | **SKIPPED - upstream has it** | `ExpertSource::copy_blobs` and `FileExpertSource::drop_mapping` are both in 0.1.41, so the +52% we measured on 0.1.40.3 is now in the release |
| **#1372** GDN chunked | **SKIPPED - upstream, and CUDA-only** | `STRATA_GDN_CHUNKED` exists but sits inside `#if !defined(__HIPCC__)` (`src/prefill/kernels.cu:1980`) |
| **#1439** BF16→FP16 conversion cache | applied, **but inert on HIP** | its budget function is guarded the same way (`src/prefill/gemm.cu:571`) - kept only so the tree matches upstream's intent; drop it on the next pull |
| **#1448** q8_1 clamps | not re-applied | upstream cites the same fix (`e372d4ff`) |
| **#1457** HC scratch reuse | **SKIPPED** | conflicts with upstream's reworked scratch accounting in `prefill.cpp`; a memory-layout change taken blind risks corruption (the k8v4 lesson) |
| **#1416** CPU share, activations quantized on the GPU | not re-applied | upstream now carries the share base; measured instead (§3) |
| **#1381** MTP draft expert formats | applied | its format selection is live; the kernel half is CUDA-side |
| **#1451** PLE host buffers | applied | no guards - live on HIP |
| local | re-applied | **45-row** gfx1100/100500 hipBLASLt table (upstream still ships 34) and the ADLXPybind telemetry reader |

Build notes, for the record: the first attempt failed because `tools/hip/rebuild-windows.bat` and our harnesses
(`ab-group.py`, `now.py`, ...) are **local-only files** that don't exist on a branch from upstream - restored from
`tuned-1403`. The second failed to link (`undefined symbol: Prefill::persistent_bytes_needed`) because my own
`git checkout HEAD -- src/prefill/prefill.cpp` (done to clear the #1457 conflict) had also reverted #1439's hunk in
that file; re-applied with `git apply -3 --include=src/prefill/prefill.cpp`.

Binary: `logs/binaries/strata-141-tuned.exe` (21,720,064 B, `0.1.41` in its strings).

## 2. A/B: 0.1.41-tuned vs our 0.1.40.3-tuned build

4K prompt, same config, two interleaved rounds. The first round is budget-confounded (8.8 vs 11.1 GiB), the second
is the comparable pair:

| arm | R1 | R2 | budget |
|---|---|---|---|
| 1403-tuned (previous build) | 776.9 | 862.3 | 8.8 / 11.6 GiB |
| **141-tuned** | 861.0 | **895.1** | 11.1 / 11.5 GiB |
| 141-tuned `--prefill 4096` | **889.0** | 876.6 | 11.6 GiB |

At equal budget: **+3.8%** (862.3 -> 895.1). Modest, and expected: our old build already carried #1323, so this is
0.1.41's own work. The release's headline "+16-25% at 4K/20K on Windows with a RAM budget" is measured against
0.1.40.4 on an RTX 5070 with IQ3_XXS/S - a different starting point and model. `--prefill 4096` costs nothing at
this length (889/877 vs 861/895), which is what makes the safety change in §4 free.

## 3. CPU share at 1,000 tokens (issue #1595's case)

`STRATA_PREFILL_CPU_SHARE` on/off, 1,000-token prompt, two rounds:

| arm | R1 | R2 | from files |
|---|---|---|---|
| `=auto` | 270.1 | 273.8 | **48%** |
| `=0` | 266.8 | 268.6 | 55-56% |

**+1.2% / +1.9% for the share** - mildly positive, and the from-files share drops 7 points, so it is doing real
work. This differs from #1595 (V100, ~-4.8% at 1,000 tokens) for the reason their own report gives: on their box
*every expert was already in VRAM*, so the CPU had nothing to save. We stream, so it helps. **Keep `=auto`.**

## 4. The Windows commit limit (issues #1607, #1630) - measured, and the change adopted

`STRATA_PREFILL_AUTO_MAX` is **clamped to 8192/16384/32768** (`generate.cpp:1775`), so 7,500 from #1630's
recommendation is not selectable - and 8,192 is the value that spikes the commit charge on this exact card. Our
config had `auto` + `AUTO_MAX=16384`, i.e. above the reported crash threshold. **Adopted: `--prefill 4096`** with the
env removed (it only ever applied to `auto`). Measured with `commit-watch.py`:

| state | committed | limit | headroom |
|---|---|---|---|
| idle, engine loaded | 72.5 GiB | 77.6 GiB | **5.1 GiB** |
| during/after an 18,321-token prompt | 73.3 GiB | 77.6 GiB | **4.3 GiB** |

An 18K prompt read in 4,096-token chunks (~25 s, 733 tok/s) moves the commit charge by **0.8 GiB** - flat, no spike,
which is what #1630 predicts for chunks <= 7,500. Two things still to respect:

- The margin is **thin** (4-5 GiB of 77.6 GiB, and 24 GB of VRAM is charged to commit under WDDM). Windows filed a
  **`RADAR_PRE_LEAK_64`** report against the engine, which is its leak *heuristic*, not a crash - but it is a signal.
- The cheapest real fix is a **larger page file** (currently 46 GiB on C:, peak use 27 GiB). The alternative is
  raising `STRATA_RESIDENT_HEADROOM_GIB` from 2 back to 4, which commits ~2 GiB less for the resident set and costs
  a few percent of prefill. **Kept at 2 for now**, with the page file as the recommended change.

## 5. Options reference, regenerated

`tools/make-options-inventory.py` (new, committed) compiles the reference from the code and can be re-run after every
pull. Against this tree: **166 engine CLI flags, 342 env names, 17 server flags, 49 setup flags, 71 config keys**,
each row with its file and line. The previous files were built from the 0.1.40.3 tree and listed names that no
longer exist (`STRATA_PREFILL_FIRST`, `_SYNC`, `_STREAM_ALL`) while missing the new ones (`STRATA_STAGE_PIN`,
`STRATA_ROUTE_RESIDENT`, `STRATA_WDDM_BUDGET`, `STRATA_PREFILL_TIMING`). Counts are method-dependent: this one
filters non-`STRATA_` environment names and reads config keys from the defaults dicts and the config receivers, so
its numbers differ from the old file's by construction.

## 6. Live state after this cycle

- Engine **`strata-141-tuned.exe`** (0.1.41 + #1381 + #1451 + the 45-row table + the ADLX telemetry reader),
  `--prefill 4096`, `--kv int8 --kv-resident 32768 --max-context 524288`, `STRATA_RESIDENT_HEADROOM_GIB=2`,
  `STRATA_PREFILL_CPU_SHARE=auto`. Backup: `logs/strata-iq2_xs.json.pre-141`.
- `KV streaming: 32768 of 524288 cells per QSA layer in VRAM, the K/V in 6.19 GiB of pinned RAM`; RAM budget 11.05 GiB
  (8,198 experts); fidelity **5/5 exact**; `17*23 -> 391`.
- Started with `persist_on_release` this time, so a Hermes lifecycle cleanup cannot take it down - the failure mode
  from earlier today.

## 7. Still queued

- Adopt from the open PRs: **#1520** (release copied Windows expert pages after host staging), **#1533** (do not hold
  VRAM experts in RAM - our prefill lever), **#1524** (wider speculative batches), **#1525** (dense IQ4_XS -> FP16),
  **#1548** (`STRATA_PCIE_BALANCE`), **#1547** (routing metrics), **#1551** (the 16 under-documented flags).
- `STRATA_PREFILL_TIMING=1` replaces the hand-rolled prompt-phase profiling.
- Enlarge the page file, then re-measure commit headroom.

## 12. Prefill regression: the chunk size, not the engine (fixed)

`--prefill` was left at 4096 to sidestep #1630's Windows commit-charge spike. That is the wrong trade for
long prompts: a small chunk re-stages the overlapping expert sets once per chunk and pays the per-chunk
overhead each time, so the cost grows with prompt length.

Same prompt through the live server (73,367 real-text tokens, one engine restart per arm, same box state):

| `--prefill` | prefill | note |
|---|---|---|
| 4096 | 878.0 tok/s | the regression: my #1630-safety value |
| 7500 | 1,110.1 tok/s | +26%; the largest value #1630 documents as safe |
| 16384 | 1,264.5 tok/s | +44%; adopted |

CLI ladder on the same binary (synthetic token file, which flatters the rate ~25%: repeated tokens route to
a narrow expert set): 16K prompt 907.6 -> 982.7 -> 1,589.9; 32K prompt 933.6 -> 1,146.3 -> 1,609.3.

#1630's spike does not reproduce here: committed went 69.6 -> 70.3 GiB of 77.6 (+0.7 GiB) across a
24,402-token prefill with 16384-token chunks. If the engine ever dies mid-prefill with 0xC0000409, fall
back to 7500, which still beats 4096 by 26%.

Why 1.3k+ was real and 4K prompts never show it: rate rises with prompt length (per-chunk overhead
amortises). Measured server reads: ~950-990 at 4.5K tokens, 1,290.6 at 31,871, 1,335.9 at 110,780,
1,400.2 at 72,993 (these recorded with 16384 chunks and a 13.6 GiB budget). At the same 73K size today we
read 1,264.5 with a ~11 GiB budget; the known budget dose-response (~4%/GiB) accounts for the rest, and the
budget is squeezed now because Steam / VS Code / Sunshine / OneDrive are resident (0.5 GiB free physical at
one point, commit 69.8/77.6 GiB).

Harness: `scratch/scripts/prefill-server-ab.py <chunk>...` measures real text through the server, per arm,
from the engine's own `prompt N tokens = ... read in T ms (R tok/s)` line.
