# Updating to 0.1.40.3, triaging the new PRs, and rebuilding locally (2026-10-08)

Continues `PR-TESTS.md`. This cycle: pull upstream, triage the PRs created since the last check, rebuild the engine
locally, and verify what we updated for.

## 1. Pull

`main` was moved to **`d5ea713` = release v0.1.40.3** (`MIN_ENGINE 0.1.40.3`), using the one-time history catch-up
the release notes prescribe. Our work is preserved on branches:

| branch | what it holds |
|---|---|
| `local-work` = `pre-cleanup-backup` | our pre-update commit (43-row table, telemetry patch, probes, docs) |
| `pr-tests` | the nine PRs tested on the 82f46a8-era tree |
| `wip-pre-update` | the refreshed PR list and test artifacts at the moment of the update |
| **`tuned-1403`** = `0061c32` | **0.1.40.3 + the tuned PR set, including #1323** |

Two upstream notes from the pull: upstream added a 4-line `gpu_note` to `serve/telemetry.py` (#1380, "no AMD
readings on Windows yet") that our patched copy lacks, and **PR #1434 now carries the upstream AMD/Windows
telemetry reader** — i.e. our local patch has an upstream counterpart we should adopt instead of maintaining.

## 2. Why 0.1.40.3 mattered to this box

- **Decode fix for 16 GB+ Windows cards:** the automatic expert cache could leave ~300 MiB VRAM free and Windows
  then paged GPU memory, halving decode (their RX 7900 XT: 24 vs 55 tok/s). Our logs showed exactly this pathology
  (`only 0 MiB free once the slots are written`). 0.1.40.3 keeps 2,560 MiB free.
- **k8v4 + `--kv-resident` corruption (#1188) was fixed in 0.1.40.2** — our engine was 0.1.40, so it predated the
  fix. That fix is what unlocks the k8v4 decode win we had to revert.
- The bundled HIP runtime is used again (#461).

## 3. Triage of the new PRs

100 open PRs; **64 created since the last triage**, 41 of them based on the new main. Relevant to gfx1100:

| PR | what | status here |
|---|---|---|
| #1372 | `STRATA_GDN_CHUNKED=1` — the prompt's GDN recurrence in 32-token chunks | applied; **no measurable gain on our box** (851 vs 842 tok/s with it off) |
| #1439 | cache immutable BF16→FP16 weight conversions (`STRATA_BF16_TC_CACHE`) | applied |
| #1448 | clamp the remaining unclamped q8_1 scale/sum emit sites | applied (correctness) |
| #1381 | MTP draft experts at Q8_0/BF16 (`STRATA_D_FMTS`/`GU_FMTS`/`MMVQ_FMTS`) | applied |
| #1457 | reuse shared scratch for the HC read | applied |
| #1416 / #1414 / #1379 | CPU-share cluster on top of merged #1282 | **not applied** - short-prompt work, our harness is 4K |
| #1454 | reuse embedding storage for half outputs (5 lines) | did not apply (context moved) |
| #1434 | upstream AMD/Windows telemetry (#1380) | **conflicts with our local patch**; adopt instead of ours |
| #1459 | bench: RX 7900 XTX + 6800 XT, 1M ctx, long outputs | read-only intel from our GPU |

Not for us: #1402 (a different model family, qwen35moe), #1370/#1367/#1465/#1437/#1424/#1418 (CUDA), #1441/#1438/#1461
(multi-GPU/peer), #1449 (Metal), #1426 (dflash), #1420 (GLM), #1450/#1427 (web UI), #1421/#1436 (k8s/Linux), and the
Intel/gfx1150/gfx1151 table PRs.

## 4. Rebuilds and the measured result

Both builds are from this tree with the HIP toolchain (`tools/hip/rebuild-windows.bat strata`):

| binary | what | build time |
|---|---|---|
| `logs/binaries/strata-1403-stock.exe` | stock 0.1.40.3 | 57 s |
| `logs/binaries/strata-1403-tuned.exe` | 0.1.40.3 + #1372, #1439, #1448, #1381, #1457, **#1323** | 28 s |

(#1323 was merged via `git fetch origin pull/1323/head:pr1323` + `git merge`; its rebased form applies the batching
unconditionally and adds `drop_mapping`, so the old `STRATA_STAGER_BATCH` knob no longer exists.)

A/B, same 4,089-token prompt, same config (budget clamped to ~8.3 GiB both arms), two interleaved rounds:

| variant | prefill | host staging | disk peak |
|---|---|---|---|
| stock 0.1.40.3 | 532.5 / 571.5 (≈552) | 6.1-6.3 s | 2.38 GB/s |
| **tuned 0.1.40.3** | **800.4 / 884.2 (≈842)** | 3.3-3.5 s | 3.12 GB/s |
| tuned, `STRATA_GDN_CHUNKED=0` | 835.1 / 867.7 (≈851) | 3.5-3.6 s | 3.13 GB/s |

**The tuned build is ~+52% on prefill over the stock 0.1.40.3**, and it is essentially all **#1323**: the same
optimization measured +27% on the 0.1.40 tree, here against a smaller RAM budget.

Other things 0.1.40.3 changed on this box, from its own log:
- `hipBLASLt summary launches=2880 fallbacks=0 unique_fallback_shapes=0` (our 43-row table, still 0 fallbacks)
- the RAM complement can now be **`mapped pinned ... pinned 6.12 GiB; page-locked and mapped`** (0.1.40 always
  answered `page-locking refused`)
- `pool multi ... 19.7-37.4 GB/s over the rows phases` (was 4.2 GB/s), `MTP prompt 48.9 ms` (was 183.5 ms)
- a whole engine run is **31 s** where 0.1.40 took 85 s; the server is ready in ~20 s (was ~45-50)

**Caveat on the numbers:** the RAM budget is clamped to whatever is free at start, and this box's free RAM moved
between runs (16.4 GiB earlier → 13.0 GiB in these). The budget went 12.2 → 8.33 GiB, which is why the tuned 1403
(≈842) sits below the tuned 0.1.40 measurement (≈947-975) even though the 1403 build is the better one. Comparisons
are only valid within a run.

## 5. Verification: the k8v4 fix we updated for

Server on the tuned engine, `--kv k8v4 --kv-resident 32768`:

```
kv-fidelity [k8v4-tuned]
  OK   expected 'alpha'      got 'alpha'
  OK   expected '391'        got '391'
  OK   expected 'k8v4 live'  got 'k8v4 live'
  OK   expected '391'        got '391'
  OK   expected 'Paris'      got 'Paris'
  -> 5/5 exact
```

On 0.1.40 this same check was **1/5**. So the k8v4 + streaming combination is now usable here, which is what makes
its decode gain (+30-58% measured earlier, −1.41 GiB pinned RAM) reachable.

## 6. k8v4 vs int8 on the new engine (inconclusive, and why)

With k8v4 verified correct (5/5), the next question was whether it *pays* here, as it once appeared to (+30-58%
decode on 0.1.40). Measured from the engine's own per-request lines, 256-token answers:

| mode | decode samples | median | pinned K/V |
|---|---|---|---|
| `--kv k8v4` | 60.6 / 67.0 / 71.4 | 67.0 tok/s | **4.78 GiB** |
| `--kv int8` | 72.2 / 69.2 / 71.6 | 71.6 tok/s | 6.19 GiB |

Decode is **within this box's noise either way**, and the earlier +30-58% did not reproduce (that number came from
runs taken while the k8v4+streaming path was still corrupt, so it should not be trusted). k8v4 does save **1.41 GiB
of pinned RAM**, which feeds the expert budget - but the follow-up prefill A/B that would have confirmed that came
out **unusable** (the int8 arm swung 128 -> 513 tok/s between rounds, and passing a second `--kv` alongside the
config's own is not a clean way to switch modes). So: k8v4 is correct and leaner, its speed is a wash — kept on
`int8` (the configuration with the longest track record here) with k8v4 one edit away.

## 7. State of the box after this cycle

- `main` = `d5ea713` (v0.1.40.3); tuned work on `tuned-1403` (`0061c32`); our pre-update work on `local-work`.
- The server runs **`logs/binaries/strata-1403-cpushare.exe`** = 0.1.40.3 + #1323 + #1372/#1439/#1448/#1381/#1457 +
  **#1416 (CPU share) + #1451 (PLE host buffers)**, with `--kv int8`, the 43-row gfx1100 table,
  `--resident-budget-gib 18` (clamped), the resident pin, and `STRATA_PREFILL_CPU_SHARE=auto`.
  Backups: `logs/strata-iq2_xs.json.pre-k8v4`, `logs/strata-iq2_xs.json.pre-cpushare`.
- Final measured state, server-side, best available RAM: **4,159-token prompt read in 6.0-6.4 s (648-694 tok/s)**,
  decode ~70 tok/s at ~78% draft acceptance, `17*23 -> 391`. Before this whole effort: the same prompt took 22-23 s
  (≈184 tok/s).
- **The RAM budget is the dominant variable** and it is clamped from whatever is free when the engine starts: it
  went 6.12 -> 12.66 GiB across today's runs (free RAM 10.4 -> >17 GiB), and prefill moved with it. Stopping stray
  servers matters: one was still holding port 8080 with a 22 GB working set and silently shrank every measurement
  until it was killed.

## 8. What 0.1.40.3 changed here, from the engine's own log

- `hipBLASLt summary launches=2880 fallbacks=0 unique_fallback_shapes=0` (our 43-row table; 0 fallbacks)
- the RAM complement can now report **`mapped pinned ... pinned 6.12 GiB; page-locked and mapped`** (0.1.40 always
  answered `page-locking refused`)
- `pool multi ... 19.7-37.4 GB/s over the rows phases` (was 4.2 GB/s), `MTP prompt 48.9 ms` (was 183.5 ms)
- a whole engine run is **31 s** where 0.1.40 took 85 s; the server is ready in ~20-25 s

## 9. The leftovers, tested one by one

Applied onto `tuned-1403` as `strata-1403-cpushare.exe` (build 24 s):

| leftover | verdict |
|---|---|
| **#1416** CPU share | **ADOPTED.** Short chat prompt (108 tok) in the CLI harness: 68.8 -> **88.6 tok/s (+29%)**, from-files 29% -> 12%, engine log `on the CPU 1885 (share 0.90)` while only 776 experts streamed. Server-side pairing with the knob off/on/off/on (73-tok prompts, engine-measured read): **1,897 / 1,844 ms off -> 1,507 / 1,548 ms on**, i.e. **~1.88 s -> ~1.51 s per short prompt (~20%)**. At 4K it is neutral (938.6 vs 928.4 tok/s) and decode is untouched at every size. |
| #1414 | does not apply — same feature as #1416 (identical claimed numbers), superseded by it |
| #1379 | does not apply — a debug gate over the same region #1416 rewrites |
| **#1451** PLE host buffers | applied and building; PLE is ~2 ms of a prefill, so no measurable effect is expected — memory hygiene only |
| **#1434** AMD telemetry (ADL + PDH) | **works on this box, except power**: name, VRAM used/total, temp 34 °C and util all read correctly, but `gpu_power` stays `None`. Our ADLXPybind patch returns **22 W** from `GPUTotalBoardPower()`. Kept ours; this is worth a comment on the PR (their ADL power sensor answers nothing on Adrenalin 32.0.31041 — the same wall #1224 hit). |
| #1454 | still conflicts (`src/prefill/prefill.cpp:1025`, moved by #1372/#1439/#1457) |
| #1324 / #1325 | still conflict with #1323 (they are the alternative file-tier design); testing them means a build with #1323 reverted, which is a different experiment from "more patches on top" |

So the two that paid are in: **#1416 for short prompts** and **#1451** as hygiene. #1434's route is viable but
loses the power reading we already have.

## 10. Streaming KV: how much resident window this box can afford

Streaming is the arrangement we want (it is what makes a 512K context cheap): the context's K/V lives in pinned RAM
and only the attention's window sits in VRAM, so the VRAM goes to experts instead. `--kv-resident N` sets that
window; **`0` means "keep every cell in VRAM"** (`src/core/layer.cpp:516`) and turns streaming off. Same 4K prompt,
two rounds each, everything else unchanged:

| KV arrangement | prefill | host | experts from files |
|---|---|---|---|
| **`--kv-resident 32768` (streaming, current)** | **948.4 / 931.4 (~940 tok/s)** | 2.2 s | **72%** |
| `--kv-resident 65536` | 947.7 / 931.7 (~940 tok/s) | 2.0-2.3 s | 73% |
| `--kv-resident 131072` | 880.8 / 875.1 (~878 tok/s) | 2.5-2.6 s | 75-76% |
| `--kv-resident 0` (**no streaming**, all in VRAM) | 772.3 / 711.5 (~742 tok/s) | 3.0 s | **87%** |

Reading it:
- **Full residency costs ~12%** (940 -> 742 tok/s): with `--max-context 524288` the KV wants ~6.19 GiB of VRAM
  whatever the live prompt length, and that comes straight out of the expert cache (72% -> 87% of experts read from
  files). Streaming a 4K prompt costs almost nothing, so paying 6 GiB to avoid it is a bad trade here.
- **The current window is at the plateau.** 32,768 and 65,536 are the same (~940); 131,072 starts to cost (~6.6%),
  which is where the bigger window begins displacing expert slots.
- So `--kv-resident 32768` stays, which also matches the author's own AMD page (`docs/AMD_HIP.md:284` uses exactly
  `--kv int8 --kv-resident 32768`).
- Streaming's price is RAM, not VRAM: ~13.7 KB per context token for int8 (6.19 GiB at 512K cells, confirmed live).
  `--kv k8v4` would cut that to 4.78 GiB (23% less, ~1.4 GiB more RAM for the expert complement); it is verified
  correct here but was a speed wash, so int8 stays.
- `--kv-grow` (the elastic K/V, "the whole K/V in VRAM, no streaming") is a separate feature and is **gated off when
  `--resident-budget-gib` is used** (`generate.cpp:1865` sets `resident_cpu_experts`, which `generate.cpp:3715`
  requires to be false), so it cannot be combined with the flag that fixed our prefill.

Post-sweep the server was restarted on the unchanged config and re-verified: `KV streaming: 32768 of 524288 cells
per QSA layer in VRAM, the K/V in 6.19 GiB of pinned RAM`, RAM budget 12.56 GiB, fidelity **5/5**. One early answer
read `39` for 17*23 at a 48-token budget and did not reproduce at the same budget (`finish_reason: stop`, `391`) -
a truncated tail, not corruption; the 5-prompt suite passes.

## 11. Where prefill and decode time actually goes (and what is left to get)

Measured with the engine's own `--stats` counters, with the server stopped so the CLI run owns the GPU. `ab-group.py`
now parses the staging fields (`host` ms, `by DMA`, budget, pinned), and `io-profile.py` runs the phases while
sampling the physical disk.

**The phase split, 4K prompt:** the read phase is 4,338.9 ms (942.4 tok/s); the whole prompt pass is 6,352.8 ms
(643.65 tok/s). Inside the read phase, **host staging of the 16,048 streamed experts is 2,349.3 ms - 37% of the
prefill** - and `0 by DMA`. Prompt copies 11,172.9 MB; the pass reads 21,443 blobs.

**The drive is not the wall.** Through the prefill it averaged 1,357 MB/s (peak 2,823) against ~3.4 GB/s unbuffered
capability, and the PCIe probe says 28.4 GB/s. With `0 by DMA` in every arm, every streamed byte goes
file -> host buffer -> copy, so the only per-byte lever is having fewer bytes to stage.

**Prefill sweep** (4K prompt, one pass per arm; compare by *budget*, since free RAM drifted between arms):

| arm | budget | prefill | host staging |
|---|---|---|---|
| baseline (4 GiB headroom) | 11.2 GiB | 872.3 tok/s | 2,351 ms |
| **`STRATA_RESIDENT_HEADROOM_GIB=2`** | **13.6 GiB** | **952.9** | **2,036 ms** |
| `STRATA_RESIDENT_HEADROOM_GIB=1` | 15.0 GiB | 943.9 | 1,998 ms |
| `STRATA_IO_THREADS=64` / `=16` | 12.5 / 12.4 | 931.4 / 931.2 | 2,113 / 2,236 ms |
| `STRATA_PREFILL_AUTO_MAX=8192` | 12.7 GiB | 891.5 | 2,051 ms |
| `STRATA_IO_PF_AHEAD=0` | 12.4 GiB | **823.8** (worst) | 2,086 ms |
| `STRATA_RESIDENT_PIN=0` | 12.3 GiB | 921.0 | 2,229 ms |

**Adopted: `STRATA_RESIDENT_HEADROOM_GIB=2`** (backup `logs/strata-iq2_xs.json.pre-headroom`) - the 4 GiB headroom
was costing 2.4 GiB of resident experts; giving it back is **+9% prefill and 315 ms less staging**. 2 GiB, not 1,
because leaving only 1 GiB free invites paging. Prefetch-ahead must stay on. I/O threads, chunk size and pinning
are neutral (`pinned 0.0` in every arm - the driver never grants the lock here). Custom attention/GEMM kernels would
not help staging; that is the other 32% of prefill and a separate project.

**Decode: the CPU is 50-73% of it, and its knobs are already right.** The pool costs 8-18 ms/token of a 14-25 ms/token
decode (41.6 GB/s effective). Interleaved arms, 160-token decodes:

| arm | decode |
|---|---|
| baseline | 70.5 / 72.1 tok/s |
| `--pool-workers 15` (SMT) | **58.6** (-19%) |
| `--pool-workers 16` | **46.2** (-36%) |
| `--pool-tasks 8` / `--pcie-frac 0.3` / `--pool-affinity all` / `--host-core last` | 71.7 / 71.2 / 69.5 / 71.0 (noise) |

The pool is bandwidth-bound, so hyperthreads contend: the default (7 workers + the host drain on 8 physical cores)
is the right shape. **AVX-512 is already in use** - the expert kernel is a dedicated `/arch:AVX512` TU
(VNNI `_mm256_dpbusd_epi32`, VBMI `_mm256_multishift_epi64_epi8`) behind a runtime feature check that passes.

**Decode warms up.** 16 tok -> 35.0 tok/s (pool 17.0 ms/token, 8 positions); 64 -> 55.5; 160 -> 61.3; 400 -> 66.0
(pool 8.2 ms/token, 202 positions). The first tokens after a long prompt cost about twice as much per token.

**`--adapt-every 0` is a short-answer setting, not a default.** It skips the periodic rebalance ("every
`adapt_every` rounds, swap up to `adapt_swaps` of the most-routed missing experts into the cache"); at 160 tokens it
is **+26%** (82.7 vs 65.6 median, two interleaved rounds), but at 400 tokens it **loses** (54.0 vs 58.6, one arm
48.8) even though it does *less* pool work per token - the frozen profile set accumulates misses instead. Left off.

So: prefill had ~9% for free and it is now on; decode's CPU-side configuration is tapped out, and further gains need
algorithmic work (faster IQ2 pool kernels, or computing fewer experts on the CPU via a better cache policy). That
also demotes #1324's LRU: it targets the ~8% file-read share of decode.
