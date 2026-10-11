# What the community reports say, and what they mean for this box

Source: issues #1655 (4x RX 7900 XT layer split), #1459 (XTX + 6800 XT helper), #1406 (single XTX on WSL2),
#1292 (single XTX, docs row) — read in full, comments included. Plus the single-card numbers they cite from
`docs/AMD_HIP.md` (issue #1389).

Everything here is HIP/gfx1100; nothing in these four issues needs CUDA or NVIDIA. The multi-GPU items are
explicitly marked.

## The three levers worth testing on a single gfx1100 card

| # | knob | evidence | expected |
|---|---|---|---|
| 1 | RAM tier coverage (the "lendable slots" line) | #1389: 74K prompt read **2,583 tok/s with 6201/6201 slots covered vs 1,810 with 5093/6202**; `--resident-experts` 1,092 → 2,503 tok/s | ~+40% prefill at long prompts |
| 2 | `STRATA_PF_GEMM=1` (+`STRATA_PF_PAD=1`) with `STRATA_PF_SWITCH_MIN_T=4096`, and `STRATA_PA_FAST=1` | #1389 single XTX v0.1.40.2: the trio took prefill **925 → 1,092 tok/s (+18%)**; `PA_FAST` + `SWITCH_MIN_T` is the fast prompt-attention route (read in `qsa_prompt_attn.cu`) | ~+18% prefill |
| 3 | `--prefill auto:32768` (from a fixed 16384) | #1389: **+23% at 74K**; a chunk above 32768 measured flat | ~+20% at long prompts |

Caveat carried from the issues: `PF_GEMM`/`PF_FUSED`/`PF_PAD`/`PA_FAST` are in the "switches that change bits"
list (`arch_defaults.hpp`), so they round differently — measure accuracy as well as speed.

## Measured on this box (73K real text through the server)

- The RAM-tier lever **does** apply here: the same 16K arm read **1,373.3 tok/s at a 0.7 GiB RAM budget vs
  1,913.6 tok/s at 12.2 GiB (+39%)**, and our own coverage line reads only **1,226-1,588 of 5,986 lendable
  slots** ("the others are read from the file when lent: not enough RAM"). Working the resident tier harder,
  and freeing system RAM, is worth more than every switch in the list above.
- `#1292`'s "on-device kernel-shape autotuning kept every shipped shape" **matches our own #1297 run exactly**.
- `#1292`'s docs row was produced with **no WMMA opt-ins**, and its table claims our `STRATA_HIP_WMMA` /
  `STRATA_SELECT_WMMA` are gfx12-only. That **contradicts our measurement** (+5.0%/ +11.4% from the WMMA
  select, +4% from SIMT, and the engine logging "prompt attention on matrix cores on (gfx1100)"). Our A/B
  wins; treat the docs' arch coverage as conservative, not authoritative.

## Measured here: the switches, 16K, matched budgets (8.2-8.9 GiB)

| arm | prefill | vs base |
|---|---|---|
| base | 1,870.9 | - |
| `STRATA_RAM_ADAPT=1` | 1,950.7 | **+4.3%** |
| `STRATA_PA_FAST=1` + `STRATA_PF_SWITCH_MIN_T=4096` | 1,979.0 | **+5.8%** |
| `STRATA_PF_GEMM=1` + `STRATA_PF_PAD=1` | 1,990.1 | **+6.4%** |
| `--prefill 32768` | 1,919.0 | +2.6% |
| `STRATA_PF_FUSED=1` | 1,898.2 | +1.5% |

All are one-armed comparisons (±2% noise), so the first three are solid and the last two marginal. They are
bit-changing switches: correctness is checked by `scratch/scripts/switches-accuracy.py` (graded answers plus a
needle planted at ~16K, so the prompt-attention path is exercised).

## Measured flat / no action

- `--spec` at or above 4 (#1389 measured flat; we already run 4), `--kv-resident` changes (ours is harmless),
  a prefill chunk above 32768, on-device kernel-shape autotuning.
- `STRATA_PREFILL_STREAM_MIN=65536` (#1406, WSL2, ROCm 7.14) recovered a 5x-looking regression, but the docs
  say a discrete card's floor is 1,024 — setup-specific, worth one A/B and nothing more.
- `--mtp-window 8192`: not from these issues; `docs/STRIX_HALO.md` measures 64K output +3.5%, 32K -0.4%.

## Not applicable (multi-GPU / layer split)

`STRATA_SPLIT_OWN`, `STRATA_STAGE_TRIM` (#1655's big 1.8-2.7x is these, not the PF_* flags — do not attribute
it to them), `--pipeline-windows` (#1656), and the whole of #1459 (XTX + 6800 XT helper on a historical
0.1.40.2 research build with no flag list — context only, nothing transferable).

## Config hygiene

The hipBLASLt tuning table is only used when its version matches the installed library, otherwise prefill
falls back to plain hipBLAS (~45% slower at 131K). Re-confirm the pairing after any ROCm update.
