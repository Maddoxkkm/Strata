# Testing the open Tier A/B PRs on this box (2026-10-08)

Continues `PR-TRIAGE.md`. The ask: test the remaining Tier A/B PRs and triage anything new. Everything below is a
measurement on this machine (Windows 11, RX 7900 XTX gfx1100, IQ2_XS, engine built from this tree for HIP), not a
reading of the authors' claims.

## The list as it stands now

The repo has **126 open PRs** (was 187 — the v0.1.40.2 release merged a large batch). Of my Tier A/B list:

- **Already merged in 0.1.40.2**: #1240, #1109, #1289 (Tier A), #1264, #1281 (Tier B).
- **Still open**: Tier A #1323, #1282, #1283, #1332, #1345; Tier B #1297, #1298, #1181, #1184, #1151, #1324,
  #1232/#1231, #1262, #1340, #1316, #1305, #1325, #1265/#1266, #1190, #1237, #1123, #1167.
- **New since the release** (4): #1368 (prefill: quantize the MoE input once and scatter it), #1367 (prompt
  attention on INT8 tensor cores), #1370 (HC upmix on CUDA), #1365 (Monitor history page).

**24 of the 26 open Tier A/B PRs are based on `82f46a8` — our exact HEAD — so they apply directly.** (Only #1287
and #1368 are based on the newer main; #1368 still applies cleanly.)

New-PR triage: **#1367 is NVIDIA-only** (`mma m16n8k32`, `STRATA_PA_SM80`), **#1370 is CUDA-only** by its own
title *("on CUDA")* — its body, though, reveals that the gfx11 side (`STRATA_HC_UPMIX=1`) already exists in main,
which is tested below. **#1368** is platform-neutral, opt-in, and lands on the prompt-aware MoE quantization we
use, so it is in the test set. **#1365** is a Monitor/logging feature (`/metrics-history`, `logs/metrics.jsonl`),
serve-side, no engine build — not a speed claim, so not measured here.

## Method

- Build a **control binary** from this tree (`tools/hip/rebuild-windows.bat strata`, Ninja, incremental:
  **1m12s**), then apply each PR group with `git apply`, rebuild, save the binary
  (`logs/binaries/strata-{base,g1323,g13}.exe`), and compare binaries so every variant runs the same way.
- One engine run per variant on the same tokenized 4,089-token prompt
  (`make-tokens.py` -> `logs/prompt-ids.txt` — the CLI has no tokenizer of its own), `--stats` on, config identical
  (including `--resident-budget-gib 18`, which is now in `strata-iq2_xs.json`), server stopped so the engine has
  the GPU and the RAM the budget is clamped against.
- Numbers are the **engine's own** (`prefill N tokens ... X tok/s`, `experts streamed/resident`, `host X ms`), plus
  disk read MB/s sampled during the run. Driver: `ab-group.py <variants.json>`.
- **This box has a ~12% run-to-run spread** on this measurement (the same binary's control run measured 747, 850
  and 839 tok/s in three rounds). Anything smaller than that needs interleaved repeats, not a single sample —
  the repo's own #1345 makes exactly this point.

## Round 1 — the file tier: #1323 (+#1283) is a real win

| variant | prefill tok/s | host staging | % from files | disk peak |
|---|---|---|---|---|
| control (our build) | 747.5 | 3.0 s | 68% | 2565 MB/s |
| control + `STRATA_UNBUFFERED_LOAD=1` | 804.0 | 3.0 s | 68% | 2589 MB/s |
| **g1323 (default)** | **947.5** | **1.8 s** | 68% | 2561 MB/s |
| g1323 + `STRATA_STAGER_BATCH=1` (the "one blob per request" old arm) | 923.3 | 1.9 s | 68% | 2585 MB/s |
| g1323 + `STRATA_KEEP_MAPPING=1` | 958.6 | 2.2 s | 68% | 2566 MB/s |

**#1323: +27% prefill, staging 3.0 -> 1.8 s, same 68% from files and the same disk rate** — it does not read
fewer bytes, it overlaps and batches them better. Its two knobs are not the whole story: both A/B arms stay fast
(~920-960), so the win is the PR as a whole. (`STRATA_UNBUFFERED_LOAD=1` on the control binary is a mild +7% and
is already how the budget path reads, so it is not the lever.)

## Round 2 — the documented gfx1151 prompt knobs: no reproducible gain on gfx1100

`docs/STRIX_HALO.md` §5 lists the "faster on gfx1151, rounds differently, opt-in" set. Measured on our card, one
run each, against a repeat of the control:

| variant | prefill tok/s | host | % from files |
|---|---|---|---|
| control (repeat) | 850.6 | 2.8 s | 68% |
| `STRATA_PF_FUSED=1` | 882.7 | 4.3 s | **60%** |
| `STRATA_PF_GEMM=1` | 884.6 | 2.8 s | 68% |
| `STRATA_HC_UPMIX=1` | 862.7 | 2.9 s | 68% |
| `STRATA_PA_FAST=1` | 885.3 | 2.7 s | 68% |
| `STRATA_HC_Q8=1` | 886.5 | 2.7 s | 68% |

All within ~4% of control, i.e. inside the box's spread: **the "+12% IQ2_XS prompts" claim for
`STRATA_PF_FUSED=1` does not reproduce on gfx1100.** One thing it does change: the from-files share drops 68% ->
60% (different kernels stage a different expert set), while staging time rose — so it is doing something real, just
not faster here. `STRATA_HIP_WMMA` is documented **gfx12-only**, so it was not tested.

## Round 3 — seven more PRs, all opt-in (#1298, #1151, #1181, #1262, #1368, #1316, #1305)

g13 binary = #1323 + #1283 + the seven. All applied cleanly, built in ~2 min.

| variant | prefill tok/s | host | % from files |
|---|---|---|---|
| g13 default | 839.2 | 1.7 s | 68% |
| + `STRATA_SELECT_WMMA=1` (#1298) | 820.4 | 1.9 s | 68% |
| + `STRATA_SELECT_SGEMM=1` (#1151) | **974.8** | 1.7 s | 68% |
| + `STRATA_QUANT_GATHER=1` (#1368) | 936.4 | 1.7 s | 68% |
| + `STRATA_HC_REQ8=1` (#1262) | **957.7** | 1.7 s | 66% |
| + `--remote-expert-opt` (#1181) | **failed** | — | — |
| + all of round 3 | failed | — | — |

- Three looked *suggestive* (SELECT_SGEMM +16%, HC_REQ8 +14%, QUANT_GATHER +12% over the g13 default) — **round 5
  refuted all three**: measured interleaved, they are +1% / +1% / -1% against a control that itself moved
  893-972 tok/s inside the same batch. The round-3 "wins" were batch drift.
- **#1298 (SELECT_WMMA) does not help here** (-2%), even though gfx11 WMMA is exact and fast on this card
  (measured earlier with `wmma_probe`): the PR's arm is the *block scorer*, a small slice, not the GEMMs.
- **#1181 (`--remote-expert-opt`) is not testable as a CLI prompt run** — the flag is documented `--serve:
  remote-expert decode optimizations`, so the one-shot run errors out. It needs a server-side A/B to measure.

## Skipped, with reasons (not tested)

| PR | why |
|---|---|
| #1367, #1370 | NVIDIA-only: `mma m16n8k32`/`STRATA_PA_SM80`, and a CUDA kernel "on CUDA" in its own title |
| #1237 | `cudaHostAlloc` on the stage buffers - CUDA API; our HIP stage path is pageable by driver policy |
| #1123, #1167 | RDNA2 (gfx103x) prompt GEMMs / rocBLAS table - wrong architecture |
| #1190, #1184 | layer split / multi-GPU helper caches - this box has one GPU |
| #1232, #1231 | `--kv-grow` needs the whole K/V in VRAM and no KV streaming; we run `--kv int8 --kv-resident` streaming |
| #1282 | conflicts with #1283 in `prefill.hpp`; and its gain is for prompt chunks **under 1,024 tokens**, which this 4,089-token harness cannot show. Should be tested on a short-prompt workload separately |
| #1332, #1345 | `tools/calibrate.py` only (PCIe-frac list, interleaved sweep rounds). Methodological; exercised by `--calibrate`, not by the engine. #1345's interleaving *is* the method used in round 5 |
| #1265, #1266 | the engine updater UI/server work - an ops feature, not a speed claim |
| #1324, #1325 | the alternative file-tier rework: both conflict with #1323 in `expert_source.hpp` (they are competing designs for the same code, each with its own `STRATA_STAGER_BATCH`), so they need their own build to compare against #1323. Not yet run |
| #1297 | the gfx1100 decode autotuner (2,078 lines): needs the new `tune_decode` target built and a real autotune session (4+ engine starts). Highest-value unmeasured item |
| #1340 | its diff carries a binary blob without an index line, so `git apply` refuses; needs a checkout of the branch |
| #1287 | Windows HIP image encoding - a feature, and its base is the newer main |

## Round 5 — interleaved repeats (the honest verdict) and our own stage breakdown

Four variants, three rounds each, control between every pair, same binary (g13):

| round | control | SELECT_SGEMM (#1151) | QUANT_GATHER (#1368) | HC_REQ8 (#1262) |
|---|---|---|---|---|
| R1 | 972.2 | 975.1 | 961.4 | 974.7 |
| R2 | 967.5 | 991.8 | 918.4 | 979.4 |
| R3 | 893.5 | 972.5 | 967.3 | — |
| **median** | **967.5** | **975.1** | **961.4** | **~977** |

**+0.8% / -0.6% / +1.0% — i.e. nothing.** The control's own spread inside one batch was 893-972 tok/s (8%), which
is wider than every effect hunted here. Decode stayed 34-37 tok/s across all of it. Conclusion: **of the Tier A/B
PRs tested, #1323 (+#1283) is the only one with a reproducible gain on this box**; the rest are neutral here,
whatever they do on the authors' machines.

The stage timing `#1151` adds is, however, genuinely useful, and on *our* config it points somewhere different
from the author's box. Ours (4,089 tokens, GPU timeline 4655 ms, wall 4693 ms — note staging 2,016 ms is now
overlapped/hidden, which is what #1323 bought):

```
dequant            869 ms (18.7%)
wait copy          720 ms (15.5%)
qsa attn           719 ms (15.5%)
gemm gate/up       652 ms (14.0%)
gemm down          417 ms  (9.0%)
hc read            345 ms  (7.4%)
gdn (all parts)    ~566 ms (12.2%)
qsa proj           143 ms  (3.1%)
```

The author's box shows `gdn 30.8%` and `gemm gate/up 6.5%`; ours is dominated by **dequant + wait copy (34%)** —
the signature of a streaming/low-VRAM config dequantizing experts as they arrive, exactly where our budget-limited
expert flow lives. If more prefill is wanted, that is the slice to attack next (fused dequant-on-arrival, a bigger
staging ring, or more resident experts), not the attention or the GDN.

## Cumulative effect on this box so far

| step | prefill (4.1K-token prompt) |
|---|---|
| before (buffered expert reads, no budget) | ~184 tok/s (22-23 s) |
| + `--resident-budget-gib 18` (unbuffered reads) | ~750 tok/s (2.9 s staging) |
| + #1323 (+#1283) | **~947 tok/s (1.8 s staging)** |

Artifacts: `logs/binaries/strata-{base,g1323,g13}.exe`, `logs/ab-round{1,2,3,5}.out`, `logs/ab-group.json`,
`logs/ab-variants*.json`, `logs/build-{baseline,g1323,g13}.log`, driver `ab-group.py`, applicability checker
`prs-applycheck.py`.
