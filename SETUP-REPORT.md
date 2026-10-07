# Strata on this PC — setup report

Installed following `docs/AI_SETUP.md` from https://github.com/Niko1221/Strata (commit `d9ab843`, engine 0.1.35).

## Where things live

| What | Path |
| --- | --- |
| Strata (code, `.venv`, `engine/`, logs, start script) | `D:\llm-dev\strata` |
| Model data dir (`--data-dir`) | `C:\Users\maddo\.lmstudio\models` — 108 GB |
| GGUF weights (raw model, incl. the PLE shard) | `C:\Users\maddo\.lmstudio\models\models\IQ2_XS\` — 64 GB |
| Native pack (experts, tokenizer) | `C:\Users\maddo\.lmstudio\models\packs\iq2_xs\` — 35 GB |
| MTP draft layer | `C:\Users\maddo\.lmstudio\models\mtp\` — 6.5 GB |
| Start script | `D:\llm-dev\strata\run-iq2_xs.bat` |
| Server config | `D:\llm-dev\strata\strata-iq2_xs.json` |
| Engine log | `D:\llm-dev\strata\strata-iq2_xs.log` |
| Remembered data dir (per user) | `%APPDATA%\Strata\settings.json` |

Model data went to C: because the per-token SSD reads come from the **raw GGUF** (the 28.8 GB PLE
"n-gram" table is deliberately kept out of the pack: `tools/iq_pack.py: NOT_IN_PACK = {"per_layer_token_embd.weight"}`,
passed to the engine as `--ple-gguf <shard 2>.gguf`). C: is the NVMe SSD (Seagate FireCuda 510);
D: is a mechanical SATA HDD (Seagate ST4000DM004), which would be far too slow for those random reads.

## Configuration setup chose (all defaults, `--yes --family qwen --model IQ2_XS`)

* Model: Qwen3.8-Flash-Next GSQ-RCO **IQ2_XS** (2 shards, 68 GB download)
* Context **131,072** tokens, **8-bit** KV cache
* Images **off** — the CPU image encoder is Linux-only on AMD today (`docs/AMD_HIP.md`)
* Backend **hip**, one card (`--gpus` is Linux-only for now)
* Low-RAM mode: **resident** (`--resident-experts`, `STRATA_RESIDENT_PIN=0`)
* Engine: ready-made `strata-windows-x64-hip.zip` 0.1.35 for gfx1100/1101/1102/1200/1201/1030,
  ROCm 10.2.0a20260930 bundled — **nothing was compiled**
* Runtime actually loaded: `engine\amdhip64_7.dll` (the bundled one next to `strata.exe`, fix #468/#461)

## Measured facts at start (engine 0.1.35, engine log)

```
GPU: AMD Radeon RX 7900 XTX, 24.0 GB VRAM, gfx1100
expert cache auto: 17.65 GiB free, 700 MiB reserved (+143 MiB draft head) -> 12551 slots, 16.82 GiB VRAM
7 expert-pool workers + the host thread            (Ryzen 7 9800X3D, 8 cores)
WARNING: the whole resident RAM mode does not fit
  (resident complement 16.20 GiB exceeds available RAM (11.31 GiB) minus the 4 GiB safety headroom)
  -> 7.06 GiB of the experts the GPU does not hold are kept in RAM (pageable), the rest come from the
     model folder through the OS file cache
594 MiB of VRAM free with everything loaded
decode expert cache hit rate: 70.5% (2369 hits / 3360 lookups)
```

## Measured speed (server `/v1/chat/completions`, `timings` block)

| Test | prompt tokens | prefill tok/s | decode tok/s | MTP draft accepted |
| --- | ---: | ---: | ---: | ---: |
| cold first answer, 7 tokens, reasoning off | 18 | 11.6 | 16.4 | 4/4 |
| code answer, 220 tokens, reasoning off | 30 | 31.4 | 10.2 | 155/174 |
| warm chat answer, ~200 tokens | 36 | 17.5 | 15.3 | 101/191 |
| 2,063-token prompt + ~124-token answer | 2,063 | 117.8 | 17.8 | 66/98 |

Roughly **15-18 tok/s decode** when warm, which is usable but well below the README's 52-95 tok/s:
those numbers are from a 64 GB PC with an RTX 5070, i.e. a full resident expert set and the CUDA path.

## Deviations from the upstream supported configuration (called out)

1. **RAM is the limiting factor, not the GPU.** 32 GB here (the docs recommend 64 GB; IQ2_XS "needs ~48 GB").
   Only 11.31 GiB was free at load time, so just 7.06 GiB of the non-GPU experts are resident in RAM
   instead of the ~16-18 GB the docs describe for 32 GB + 24 GB. Closing RAM-hungry apps before starting
   (or moving to 64 GB) should raise the RAM tier and decode speed. Reload with
   `D:\llm-dev\strata\run-iq2_xs.bat`.
2. **No hipBLASLt tuning table for this pair.** setup reported: `no hipBLASLt tuning table for gfx1100 with
   hipBLASLt 100500 (have: gfx1100-hipblaslt-100100.txt, gfx1100-hipblaslt-100200.txt)` — the bundled ROCm
   ships hipBLASLt 1.5.0, so the prompt path's dense matrix products use plain hipBLAS (slower prompts,
   same answers). A table can be built with `tune_hipblaslt` (`docs/AMD_HIP.md`, "Tuning table"), which
   needs an engine build from source — not done here.
3. **No images** on AMD/Windows (Linux-only CPU encoder); **one card per model** (`--gpus` Linux-only).
4. **Windows AMD is new** (0.1.34/0.1.35) and the maintainers own no Windows AMD card — upstream asks
   users to report how it runs: https://github.com/Niko1221/Strata/issues
5. Running `run-iq2_xs.bat`/`START-HERE.bat` touches nothing outside `D:\llm-dev\strata` and the data dir;
   no driver install and no admin were needed.

## Verified

* `curl http://127.0.0.1:8080/health` -> `{"status": "ok", "model": "qwen3.8-flash-next-iq2_xs",
  "max_context": 131072, "images": false, "api_key": false, "loaded": true}`
* `curl http://127.0.0.1:8080/v1/models` -> one model, `status.value: loaded`, `n_ctx: 131072`
* `POST /v1/chat/completions` returns coherent answers (plain text and Python code)
* `POST /v1/messages` (Anthropic shape) works, including `thinking` blocks
* `GET /` -> HTTP 200, 13,905-byte chat page

---

# Update to engine 0.1.38 (later the same day)

`git pull` (83 commits, `d9ab843` -> `99f3dbd`) then `setup.py --update --yes` (the user-facing path is
`UPDATE.bat`, added in 0.1.36; it pulls and updates engine + packages + settings without touching the model):
`ready-made AMD engine 0.1.38 for gfx1100, ... (ROCm 10.2.0a20260930)`, `qwen3.8-flash-next-iq2_xs: up to date`.

What 0.1.36-0.1.38 bring (from `setup.py: MIN_ENGINE`): faster prompts (one gather per expert group #372, the
first chunk's PLE rows beside layer 0 #374, DeltaNet three heads per thread #413), `--kv q4_0` prompts on tensor
cores #452, Q5_0 experts on the GPU #473, IQ4_XS on AVX-2 #415, unbuffered expert loading on Windows #357 #362,
`--peer-device` #531, a 6 GB card starts #496; 0.1.37 added a silent-engine restart #481 and **Windows AMD now
counts the desktop's VRAM** (#380 #377 #497); 0.1.36 added `UPDATE.bat` and `--expert-profile-save`.

That last 0.1.37 change is visible on this PC: the expert cache went from 12,551 slots / 16.82 GiB (0.1.35) to
11,214 slots / 15.03 GiB (0.1.38) at the same context, because the engine now leaves the desktop's VRAM alone.

## The reported "crash"

No crash evidence: `server-out.log` and `strata-iq2_xs.log` both end with normally completed requests (no
traceback, no exception, no `.dmp` in the folder), and the Windows Application log shows
*"A system shutdown is in progress"* at 11:32 — i.e. the PC was shut down/restarted, which took the server with it.
Nothing in Strata failed. If it happens while the PC stays up, collect `strata-iq2_xs.log` (and any
`strata-stall-<pid>.dmp`) and open an issue; 0.1.37's #481 also restarts an engine that goes silent.

## KV cache precision: what the options are

`--kv` has three values and **no fp16/f16 option** — the KV cache is always quantized:

| `--kv` | meaning | KV size | streaming |
| --- | --- | --- | --- |
| `int8` | 8-bit K and V — the **default**, and the highest fidelity available | 1056 B/cell (setup's model) | allowed from 64K |
| `k8v4` | INT8 K + 4-bit V (hybrid) | 816 B/cell (~0.77x) | never (engine refuses the pair) |
| `q4_0` | 4-bit K and V, "half the memory, a little less precise" | 576 B/cell (~0.55x) | allowed from 64K |

So "pull it down to 8-bit" is already the installed setting: `int8` is where a fresh install starts, and there is
no higher-precision step to come down from. The steps down are `k8v4` and `q4_0`. Note that at 131,072 context and
32 GB of RAM, **KV streaming is off on this PC either way** (auto needs `RAM >= 48 GB + KV size + 1`), so the KV
cache lives in VRAM and a smaller KV buys *expert-cache slots*, not RAM.

Measured (this PC): `k8v4` freed 0.38 GiB of VRAM -> 11,349 expert-cache slots instead of 11,063, and prompt
speed was equal or a little better (177.9 vs 171.2 tok/s on the 1,145-token prompt when the two were run
back to back); decode was within the run-to-run noise. **`int8` (the default) is left installed**: no measured
speed gain from `k8v4` survived the noise, so there is no reason to give up 4-bit-V precision.

## Benchmarks (engine 0.1.38, `local-bench.py`, `/v1/chat/completions`, reasoning off)

Numbers are from the server's own `timings` block. `cold_short` = 7-token answer, `chat_200` = 200-token chat
answer, `code_220` = Python answer, `prompt_2k`/`prompt_8k` = long-prompt prefill + short answer (actual prompt
tokens 1,145 and 4,478 — the labels are the intent, the table shows the real count).

| test | prompt tok | 0.1.35 decode | 0.1.38 decode (1st) | 0.1.38 decode (2nd) | 0.1.38 decode (3rd) | 0.1.38 k8v4 decode |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| cold_short | 18 | 16.4 | 38.9 | 22.3 | 76.3 | 18.5 |
| chat_200 | 36 | 15.3 | 43.5 | 32.3 | 51.9 | 33.2 |
| code_220 | 30 | 10.2 | 37.1 | 35.5 | 70.6 | 40.9 |
| prompt_2k | 1,145 | 17.8 | 79.4 | 57.7 | 63.1 | 58.0 |
| prompt_8k | 4,478 | - | 77.4 | 59.1 | 68.2 | 63.0 |

| test | prompt tok | 0.1.35 prefill | 0.1.38 prefill (1st) | 0.1.38 prefill (2nd) | 0.1.38 prefill (3rd) | 0.1.38 k8v4 prefill |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| prompt_2k | 1,145 | 117.8 | 130.5 | 171.2 | 412.9 | 177.9 |
| prompt_8k | 4,478 | - | 595.9 | 673.9 | 712.5 | 707.4 |

Read it carefully:

* **Run-to-run variance is large: two back-to-back passes of the *same* config on the same server measured
  49.7 and 61.1 tok/s decode (+23%), and prefill 422 vs 563 tok/s.** Differences under ~25% mean nothing here.
* The 0.1.35 column is not a clean engine comparison: that run only got a **7.06 GiB** resident RAM tier
  (15.47-20.33 GiB in the 0.1.38 runs — more RAM was free then), so engine 0.1.38 and the bigger RAM tier both
  contribute to the jump.
* The engine log shows the resident tier is the lever on this 32 GB box: with the full complement resident,
  nothing is read from the model folder during a request (`files 0 blobs`), while the first 0.1.38 pass read
  16,750 expert blobs / ~40 GB from the pack.
* Upstream measured a 12-20% A/B spread on one AMD machine (#432); this PC is noisier.

Artifacts: `bench-results-tidy.csv` (all passes, one row per test), `bench-raw.csv` (append-only raw log),
`bench-logs/engine-0.1.38-{int8,k8v4}.log`, `local-bench.py` (rebuild any time with
`.venv/Scripts/python.exe local-bench.py "<label>"` while the server runs).

---

# Tuning round: `--calibrate` and `--draft-vocab en`

Order run: `setup.py --setup --draft-vocab en --no-start` (the flag must go through a setup/start run to be kept),
then `setup.py --calibrate --yes --no-start`, then a restart and two bench passes. The server must be stopped for
the calibration (it needs the GPU to itself).

## `--draft-vocab en` — applied, small win

`[ok] draft layer: the token subset for English and code (less VRAM)`; the config now carries `"draft_vocab": "en"`
and the engine reports `draft head over 40525 tokens (52.6 MiB)` with the cache reserving `+58 MiB for the draft
head` (the CJK subset reserved `+143 MiB`). Saves ~85 MiB of VRAM and 1-2% of English decode speed per upstream.
Cost: the draft layer no longer speculates Chinese/Japanese/Korean tokens, so CJK output loses the MTP speed-up
(it still answers correctly).

## `--calibrate` — ran on AMD/HIP (upstream-guarded, untested here) and kept nothing

Upstream only offers the tuning on NVIDIA (`cal = None if hip else saved_calibration(cfg)`), but the explicit
`--calibrate` path has no backend check and `tools/calibrate.py` has none either, so it really measured. It ran
the whole sequence against one running engine:

```
PCIe share 0.00: 76.6 tok/s     draft floor 0.30: 26.6    7 workers: 80.0 tok/s
PCIe share 0.20: 26.3 tok/s     draft floor 0.50: 28.1    5 workers: 26.4 tok/s
PCIe share 0.35: 26.1 tok/s     draft floor 0.70: 27.0    4 workers: 79.9 tok/s
PCIe share 0.55: 26.3 tok/s
PCIe share 0.75: 27.4 tok/s
[ok] tuned for this PC: the default settings are already the fastest here (80.0 tok/s)
```

* Result: `settings: {}` — **no change**; only the arg order moved. The stored calibration is
  `{"?|0GB|AMD Ryzen 7 9800X3D 8-Core Processor|32GB|qwen3.8-flash-next-iq2_xs|131072|text": {...}}` — note the
  `?|0GB` for the GPU: `gpu_info()` does not resolve an AMD card, so the calibration's hardware key has no GPU
  identity (a second AMD card would collide with this entry). No flags were written into the config, so nothing
  was risked.
* The measurements are **bimodal, 26 vs 80 tok/s**, and the fast reading always falls on the first measurement
  after a fresh engine start (PCIe 0.00 = first, 7 workers = after a restart, 4 workers = after a restart). That
  is the same ~3x swing the benches show as "warm" vs "cold" passes, not a property of the settings: the tuner's
  defaults are fine, the spread is the machine.
* Likely cause (hypothesis, not verified): on 32 GB the engine copies ~20.4 GiB of experts into RAM as the
  resident tier, which competes with the OS file cache that has to hold the 28.8 GB PLE table read on every
  token; after a fresh start the cache is still populated from the load, later it is not. If it turns out to
  matter, `--low-ram mmap` (no RAM copy at all, everything through the page cache) is the A/B worth running.

## Bench after both (engine 0.1.38, kv=int8, draft-vocab en, 20.44 GiB resident tier)

| test | prompt tok | pass A decode | pass B decode | pass A prefill | pass B prefill |
| --- | ---: | ---: | ---: | ---: | ---: |
| cold_short | 18 | 34.9 | 61.0 | 18.9 | 124.7 |
| chat_200 | 36 | 41.8 | 75.8 | 44.7 | 156.7 |
| code_220 | 30 | 42.9 | 96.2 | 75.2 | 152.9 |
| prompt_2k | 1,145 | 86.2 | 86.9 | 182.2 | 419.6 |
| prompt_8k | 4,478 | 88.9 | 104.1 | 694.2 | 714.8 |

Against the original install (engine 0.1.35, 7.06 GiB resident tier, cjk draft): **10-18 tok/s decode and
118 tok/s prefill** -> the best measured here is **104 tok/s decode / 715 tok/s prefill**. Two passes back to back
still differ by ~2x (A mean 58.9, B mean 84.8 tok/s), so take the pair as the range, not the peak.

`cfg-before-calibration.json` holds the config as it was before this round, for a diff.

---

# Raising the prefill (prompt-reading) speed

Goal: prefill was reading long prompts at ~430-735 tok/s. The reference in `docs/AMD_HIP_PERFORMANCE.md`
(64 GB RAM, ROCm 7.1, same card) measures 447-966 tok/s with MMQ + a gfx1100 hipBLASLt table + `--prefill 8192`
+ `--kv-resident 32768`. Measured here with `prefill-bench.py` (unique ~6k and ~13k-token prompts, 128-token
answer cap, zero reused KV tokens; one line per request, two samples per arm, arms in `make-prefill-arms.py`):

| arm (what differs from what was installed) | ~6k prompt | ~13k prompt |
| --- | ---: | ---: |
| A - baseline (`--prefill auto`, no engine env) | 431, 443 | 735, 744 |
| B - `--prefill 8192` + `STRATA_PREFILL_MMQ=1`/`RING=96`/`IO_THREADS=32` | 354, 468 | 763, 777 |
| D - `--prefill auto:16384` + the same env | 512 | **600** |
| **C - `--prefill auto:16384` + env + `--kv-resident 32768`** | **496, 486** | **768, 764** |

* **C wins on every sample at both sizes**: +13% at ~6k and +4% at ~13k against A. The two samples within each
  arm agree for C (496/486 and 768/764) while every other arm disagrees by 10-20% between samples, so C is the
  only arm whose difference survives this box's noise.
* What C changes, and why it plausibly works: `--kv-resident 32768` keeps the KV cache's K/V in 1.55 GiB of RAM
  and only the attention window in VRAM ("KV streaming: 32768 of 131072 cells per QSA layer in VRAM"), which
  **frees 1.4 GiB of VRAM -> the expert cache goes from ~11,100 to 12,303 slots**. Fewer experts have to be
  streamed during a prompt. The engine's own line: `KV streaming: 93-98% of block reads hit VRAM`.
* Bigger chunks alone are a **trap**: D (16k chunks) was +18% at ~6k but **-18% at ~13k**, because a 16k chunk
  borrows 5,892 cache slots (7.89 GiB) against 3,042 (4.08 GiB) for 8k, starving the resident tier on a long prompt.
* The MMQ opt-in (`STRATA_PREFILL_MMQ=1`) is compiled into the shipped Windows engine
  (`tools/hip/build_windows.bat` passes `-DSTRATA_PREFILL_MMQ=ON`) and is enabled, but its effect cannot be
  separated from noise in these samples (B is not consistently ahead of A).
* Prefill scales with prompt length (fixed per-request overhead): a 125,346-token prompt read at **748 tok/s**.
  So a sub-500 reading is a *short-to-medium prompt* effect, not a ceiling.

## Installed configuration (winning arm)

`strata-iq2_xs.json` now carries `--kv-resident 32768` (written by setup via `--kv-streaming on`, with setup's
own warning that it wants 1.8 GB of RAM beside the model's 48 GB), plus in the config's `env` block:

```
STRATA_PREFILL_AUTO_MAX=16384   the engine's --prefill auto cap (default 8192)
STRATA_PREFILL_MMQ=1            HIP MMQ, opt-in at runtime
STRATA_PREFILL_RING=96          the AMD_HIP_PERFORMANCE.md measured arm
STRATA_IO_THREADS=32
```

Env keys survive a later `setup.py --setup` (it only `setdefault`s on AMD), but the `--kv-resident` arg would be
reset to off by a `--setup` without `--kv-streaming on` - pass it again after any setup run.

Live after the change: `expert cache 12303 slots, 16.49 GiB of VRAM`, `resident RAM mode: 19.42 GiB of experts in
RAM (pageable)`, `prompt chunk auto: 16384 tokens`, `KV streaming ... K/V in 1.55 GiB of pinned RAM`.

Final pass with it installed: prefill **450 t/s at 5,827 tokens, 689 t/s at 12,391** (two samples of the suite
above: 421.8 at 1,145 and 732.7 at 4,478); decode 45.7 / 68.8 / 88.7 / 80.9 / 92.1 tok/s across the five tests.

## What is left on the table (not done)

1. **A gfx1100 hipBLASLt tuning table for the bundled hipBLASLt 1.5.0.** Upstream ships tables for 1.0.0 and
   1.0.2 only; the engine refuses a version mismatch, so today the prompt path's dense matrix products use plain
   hipBLAS. Making the table means building `tune_hipblaslt` from source: `tools\hip\build_windows.bat` installs
   ROCm from TheRock wheels into `.rocm-win` (~10 GB) and compiles (~20-40 min). Upstream's own RDNA4 note
   measures a *matching* table at only 0-4% end-to-end prompt speed, so this is a large cost for a small,
   uncertain gain.
2. **RAM.** The reference box has 64 GB; this one has 32 GB, which caps the resident expert tier at ~19-20 GiB
   and forces the rest through the file cache. That is the structural ceiling above everything else here.

Artifacts: `prefill-arms.csv` (raw), `analyze-prefill.py` (the table above), `make-prefill-arms.py` (the arms),
`prefill-bench.py`, `prefill-sweep.sh` + `stop-strata.ps1` (restart-between-arms runner), `prefill-sweep*.log`,
`bench-logs/engine-arm*.log`.

---

# Where the time actually goes, and what is left for RDNA3

## How to look (what works on this install)

| Tool | Works here? | What it gave |
| --- | --- | --- |
| `--stats` (engine) | **yes** | full per-stage breakdown of a real prompt+decode run - `measure-stats.log`, 31 KB |
| `--gpu-only-full` | no | `session_replay_full: not captured with post graphs` (the CUDA-stream graph capture the floor needs does not happen on this Windows/HIP path) |
| `--gpu-stages` | no | `session_replay_stages: not captured with the split` |
| `--stage-timing --no-capture` | not completed | needs a manual pass; `--stage-timing` alone is refused inside a capture |
| source reading | yes | the RDNA3 gaps below are comments and `#if`s in the tree, not guesses |

`measure-kernels.py` runs any of these with this install's exact args/env (the same launch `serve/server.py`
makes); `run-engine-measure.py` is the earlier, single-flag version. Stop the server first.

## The measurement (`--stats`, 6,173-token prompt, engine 0.1.38, installed config)

```
PCIe probe: 28.3 GB/s host->device -> pcie_frac 0.55
prefill chunk auto: 6400 tokens; borrows 2515 cache slots (3.38 GiB); 2515 lent slots refilled in 553.9 ms
prefill 6173 tokens in 1 chunk, 17789.0 ms (347.0 tok/s); experts streamed 15048
        (0 by DMA, host 9409.7 ms), resident 7908; PLE 6.1 ms
per token 46.985 ms/token; CPU expert pool 15.050 ms/token over 48 layers (drain 12.626)
adaptive tier 96 experts swapped into the VRAM tier (every 4 rounds, 5.767 ms/round)
verify window: wait for rings 14.336, pool 15.056, host 0.404, commit 0.108 ms/round
R4 overlap 0 of 0 layers the hit work was DONE when the pool returned
expert tiers: decode RAM 584 blobs, files 24 blobs, 0.0 MB read; prompt copies 27200.0 MB
ple io: 98976 rows, 0.0% row-cache hits, 11840 SSD reads (49.4 MB), p50 814 us, blocked 41.747 ms total
R4 expert-cache hits 5477 of 6240 = 87.8% (763 refused, cache 100% full)
```

Reading that:

1. **Prefill is I/O-bound and the copy path is the cost, not the kernels.** 9,409.7 ms of the 17,789 ms prefill
   (53%) is *host* expert streaming, and it says `0 by DMA`, at ~2.4 GB/s - while the PCIe probe measures
   **28.3 GB/s**. The GPU work is a minority of the prompt.
2. **The PLE/n-gram table is a non-issue here: 6.1 ms.** (An earlier hypothesis of mine - that PLE reads from
   the 28.8 GB GGUF were the drag - is wrong, per the engine's own counter. The `ple io` line's 0.0% row-cache
   hits and an 11,856/1,048,576-row cache look bad in isolation but cost nothing measurable.)
3. **Decode is CPU-pool- and wait-bound**: pool 15.05 ms of the 46.99 ms token (drain 12.6), ring wait 14.3,
   adaptive swaps 5.77 (12%), MTP 2.74. `R4 overlap 0 of 0 layers` says the GPU's cached-expert work and the
   CPU pool never overlap on this config.
4. Prompt chunk 16,384 borrows **5,985 slots / 8.02 GiB** and the restore shows up as `prompt copies 27200.0 MB`.
   That is why a smaller chunk can win even at lower peak chunk size: fewer borrowed slots = less copy traffic.

## RDNA3 gaps in the kernels (source evidence)

* `src/kernels/cuda/qsa_prompt_attn.cu:740-770` - the int8-KV **prompt attention on matrix cores is gfx12-only**
  (`#if defined(__gfx1200__) || defined(__gfx1201__)`, `v_wmma_f32_16x16x16_f16_w32_gfx12`), opt-in via
  `STRATA_HIP_WMMA=1`; everything else on AMD "keeps the old kernel". Upstream measured this kernel at
  **7.2-7.5x the portable one**, and +29-34% end to end on an R9700.
* `src/kernels/cuda/qsa_select.cu:421` - the block scorer's gfx12 kernel is gated the same way, and the comment
  says outright: **"gfx1100 has WMMA too, with another layout"**. RDNA3's WMMA is a different fragment layout and
  a different intrinsic (`__builtin_amdgcn_wmma_f32_16x16x16_f16_w32`, not the `_gfx12` form), which is the whole
  of the porting work.
* `src/kernels/cuda/native_qsa_score.cu:144` - on AMD the indexer score is an **ordered scalar F32 dot per head**
  ("gfx1100 has no CUDA ldmatrix/mma instruction sequence"), i.e. a fallback that also has a WMMA shape.
* `src/kernels/cuda/qsa_select.cu:1090` - a constant tuned on RDNA4 (`kRegMinBlocks = 7168`, "gfx1201: below ~28K
  cells the 1,024-thread kernel's fixed cost loses to the ref") with no gfx1100 counterpart measured.
* `src/kernels/cuda/fused_gr.cu:715` - the one place that already reasons about gfx1100's 64 KiB LDS ("all eight
  tokens fit gfx1100's 64 KiB LDS at this tile").
* The engine honours ~60 `STRATA_*` runtime A/B switches (`--no-hit-poke`, `--no-ple-prefetch`,
  `STRATA_GR_DOWN_MAX4`, `STRATA_ADAPT_NOWAIT`, `STRATA_QSA_WARP`, `STRATA_STAGER_RING`, ...) plus the
  `--no-token-graph` / `--no-fused-gr` / `--sync-every-layer` flags - all free to flip, no build needed.

## Tried and rejected this round

| Attempt | Result |
| --- | --- |
| `STRATA_RESIDENT_PIN=1` (pin the resident complement so uploads could go by DMA) | **the driver refused it**: `page-locking refused (out of memory); locked 18897 MiB via working-set minimum + VirtualLock`. Speed: +19% at ~6k, -45% at ~13k vs baseline -> noise, no win. On a 32 GB box the page-lock path is not available. |
| `--adapt-every 0` (drop the 5.77 ms/round swaps) | took effect (`adaptive swaps off`) but the two prompt sizes disagreed (+11% / -24%) -> no adoptable win in one sample each |
| the earlier arms (MMQ env, 8k vs 16k chunk, KV streaming) | KV streaming was the only reproducible win (see above) |

## The gate for any real kernel work

Nothing in the list above can be *changed* without building the engine from source: `tools\hip\build_windows.bat`
installs ROCm from AMD's TheRock wheels into `.rocm-win` (~10 GB, no admin), needs Visual Studio 2022 Build Tools
with the C++ workload (already on this PC) + Python + git, and compiles for `gfx1100` in ~20-40 minutes. That
build is also what would produce the missing `tools/hip/gfx1100-hipblaslt-100500.txt` via `tune_hipblaslt`.

Priority if it is built, given the numbers above:

1. **The prompt-path expert upload** (`0 by DMA`, host 9.4 s of a 17.8 s prefill). This is the biggest single
   line in the whole profile and it is not a math kernel: it is the staging/copy path on Windows HIP.
2. **The CPU-pool / overlap side** (`R4 overlap 0 of 0 layers`, pool 15 ms/token): making the GPU's cached-expert
   work overlap the pool is a decode win and needs no new math.
3. **gfx11 WMMA prompt attention + QSA scorer** (the ports above). Big upstream numbers, but on *this* box the
   prompt is I/O bound, so expect the compute share to shrink the return - worth it mainly if the I/O side is
   fixed first.
4. `--pool-workers` / `--pool-affinity` sweeps and the ~60 A/B switches: free, but each pair costs ~4 minutes of
   2-sample measurement at this box's noise floor.

---

# From-source build + the missing hipBLASLt table

## The build (done)

```
cmd /c "set STRATA_HIP_ARCHS=gfx1100 & tools\hip\build_windows.bat"
  -> ROCm 10.2.0a20260930 (TheRock wheels) into D:\llm-dev\strata\.rocm-win   (4.7 GB)
  -> build-hip-win\strata.exe, strata-device.exe
  -> dist\strata-windows-x64-hip.zip  129 MiB (383 MiB unpacked), gfx1100 only
```

Prerequisites were all present: `py -3` = Python 3.13.15 (the script prefers it over the 3.14 in PATH), VS 2022
Build Tools at `C:\Program Files (x86)\Microsoft Visual Studio\2022\BuildTools`, cmake, git. One thing had to be
added: **`cmake -G Ninja` needs ninja on PATH**, which it is not - the launcher therefore prepends the Strata
`.venv\Scripts` (which carries `ninja.exe`):

```
cmd /c "set PATH=D:\llm-dev\strata\.venv\Scripts;%PATH% & set STRATA_HIP_ARCHS=gfx1100 & tools\hip\build_windows.bat"
```

Total ~15 minutes, no admin. `tools\hip\rebuild-windows.bat <target>` (added here) rebuilds one target with the
same ROCm+MSVC environment, which is the loop for any kernel change.

## The table that upstream does not ship: `gfx1100-hipblaslt-100500.txt` (done)

`docs/AMD_HIP.md` says the engine's tuned dense path applies "only when it matches both the card's architecture
and the installed hipBLASLt version" and that gfx1100 tables exist for 1.0.0 and 1.0.2 - the bundled/engine ROCm
reports **hipBLASLt 1.5.0 (100500)**, so this PC has been running the plain hipBLAS fallback all along.

```
build-hip-win\tune_hipblaslt.exe --tokens 4096,8192 --tuning-out tools\hip\gfx1100-hipblaslt-100500.txt
  -> 6 rows (the tool's default three shapes x f16/bf16), engine picks it up:
     "prefill gemm: hipBLASLt tuning enabled (6 rows, gfx1100, version 100500)"
```

Isolated GEMM speedups vs the hipBLAS baseline (what the table buys per call):

| shape | f16 | bf16 |
| --- | ---: | ---: |
| N=10240 K=2560 | 5.41 ms **7.22x** | 5.24 ms **6.97x** |
| N=320 K=10240 | 0.83 ms **5.65x** | 0.81 ms **6.11x** |
| N=2560 K=320 | 0.44 ms **4.38x** | 0.45 ms **3.38x** |

Two things worth knowing about making it:

* **The `awk` in `docs/AMD_HIP.md`'s "Tuning table" section is wrong for this tool.** It assembles
  `--case dtype,T,N,K,ldy` as `dtype, $5, $2, $3, $4`, which puts `n` where `ldy` belongs; the engine's own parser
  (`src/prefill/hipblaslt_tuning.hpp`) requires `ldy >= n`, and the resulting invalid strides make rocBLAS fail
  with `hipErrorInvalidDeviceFunction` after the first case (exit 2, no table). Using the tool's default shapes
  (or `--shape T,N,K`) works.
* Column order in a tuning row is `dtype n k ldy t_bucket solution_id` - not `dtype M K N T id` as the header
  comment elsewhere suggests.

## End-to-end result: no measurable prefill change (honest null)

| run | ~6k prompt | ~13k prompt |
| --- | ---: | ---: |
| best previous arm (KV streaming, `armC-kvstream`) | 496, 486 | 768, 764 |
| with the hipBLASLt table (this table) | 363, 521 | 571, 592 |
| the suite with the table | 134.6 t/s at 1,145 tok, 695.7 at 4,478 | decode 37-77 t/s |

Within this box's ±25% spread the table changed nothing, and it is probably not even being hit: the table is keyed
on the **exact** `(type, n, k, ldy)` with only the token bucket nearest-matched (`closest()` in
`hipblaslt_tuning.hpp`), while the tool's default shapes cover 3 of the 13 shapes upstream's table lists (n up to
12,288, k in {320, 640, 2560, 6144, 10240}). Making the rest needs `--shape T,N,K` per shape and a re-tune.

That null is consistent with everything else measured here: `--stats` puts 9.4 s of a 17.8 s prefill in *host
expert streaming*, so the prompt is not waiting on dense GEMM.

## Correction to an earlier claim in this report

A `setup.py --setup` run does **not** preserve extra `env` keys when it finds a tuning table: setup.py:3639 does
`cfg["env"] = {"STRATA_HIPBLASLT_TUNING": ...}` (assignment, not `setdefault`), which wiped this install's
`STRATA_PREFILL_AUTO_MAX` / `MMQ` / `RING` / `IO_THREADS` keys. They were restored by hand afterwards; re-check
the env block after any setup run that mentions a table.

Artifacts: `build-windows.log`, `build-tune.log`, `tune-defaults.log` (all candidates + timings),
`tools/hip/gfx1100-hipblaslt-100500.txt`, `tools/hip/rebuild-windows.bat`, `prefill-table-{A,B}.log`.

---

# Three fronts, and what each was worth

Everything below was measured on this PC (RX 7900 XTX / 32 GB / gfx1100, engine 0.1.38, HIP). The box's
run-to-run spread is the constant that makes small effects unprovable here: two back-to-back passes of an
unchanged config differ by up to 2-3x, so only effects that reproduce in both directions or across several
samples are called wins below.

## What worked

| Change | Mechanism, verified in the engine's own counters | Measured benefit |
| --- | --- | --- |
| **`STRATA_RESIDENT_PIN=1`** (lock the resident expert complement) | the driver refuses a real page-lock (`page-locking refused (out of memory)`, `pinned 0.00 GiB`), so the fallback locks ~18-19 GiB via *working-set minimum + VirtualLock* - and that removes the page faults on the prompt path's expert reads: `experts streamed ... host 9,409.7 ms` -> **5,722-5,845.6 ms** | **prefill 347 -> 600-631 t/s on the same 6,173-token prompt (+73%)**; two locked runs agreed within 4% while pageable runs spread 347-548 t/s, i.e. it also removes a variance mode. Server-side: 630.9 t/s at 6,047 tokens vs 433-521 before |
| **`--kv-resident 32768`** (KV streaming) | KV in 1.55 GiB of RAM, `93-98% of block reads hit VRAM`, expert cache 11,100 -> 12,303 slots | **+13% at ~6k prompts, +4% at ~13k** (2 samples each, the only arm whose two samples agreed at both sizes) |
| **From-source Windows HIP build** | `tools\hip\build_windows.bat` -> ROCm 10.2.0a20260930 into `.rocm-win` (4.7 GB), `build-hip-win\strata.exe`, `dist\strata-windows-x64-hip.zip` | not a speedup itself: it is the **gate** for every kernel change below, and it produced the tuning tool. ~15 min, no admin |
| **`tune_hipblaslt` + a gfx1100 table for hipBLASLt 100500** | no upstream table matches the bundled hipBLASLt 1.5.0, so the prompt's dense GEMMs ran on plain hipBLAS. `hipBLASLt tuning enabled (28 rows, gfx1100, version 100500)` | **per GEMM 3.4x-10.0x vs the hipBLAS baseline** (14 shapes, 28 rows). End-to-end: **not established** - see below |
| **`--prefill auto:16384` via `STRATA_PREFILL_AUTO_MAX`** | part of the KV-streaming arm above; the engine reports `prompt chunk auto: 16384 tokens` | kept as part of that win; on its own it is a **trap** (next table) |

## What did not work (tested and rejected)

| Attempt | Result |
| --- | --- |
| The hipBLASLt table, **end to end** | per-GEMM 3.4-10x but prefill unchanged: 464-676 t/s at ~6k vs 433-521 without a table, 590-761 at ~13k vs 517-768. The two best single samples of the whole session came with it (1,103.7 t/s at 6,272 tokens; 903.5 t/s on the 4,478-token test) but do not reproduce. Consistent with `--stats`: prefill is dominated by expert streaming, not dense GEMM. Kept (no harm, and it should pay on a box that is not I/O bound) |
| `STRATA_PREFILL_MMQ=1` | compiled into the shipped engine (`-DSTRATA_PREFILL_MMQ=ON`), enabled, but arm B never beat arm A consistently -> no measurable effect |
| `--prefill auto:16384` **alone** | +18% at ~6k but **-18% at ~13k**: a 16k chunk borrows 5,892 cache slots (7.89 GiB) against 3,042 (4.08 GiB) for 8k, starving the resident tier on a long prompt |
| `STRATA_PARTIAL_PIN` / `_GIB` | the `cudaHostRegister` prefix loop never engaged (no "registered for the GPU" line) - the arena is `malloc`ed and the driver refuses registration too. The gain above comes from the working-set lock, not from registration. Dropped |
| `--adapt-every 0` | took effect (`adaptive swaps off`, removing 5.77 ms/round) but the two prompt sizes disagreed (+11% / -24%) -> no adoptable win |
| `docs/AMD_HIP.md`'s tuning `awk` | builds `--case dtype,$5,$2,$3,$4`, putting `n` where `ldy` belongs; the parser requires `ldy >= n`, so rocBLAS fails (`hipErrorInvalidDeviceFunction`) after the first case and no table is written |
| The `n=1, k=2560` shape | this ROCm's rocBLAS cannot do it on gfx1100 at all (same error); 1 of 15 reference shapes is skipped (the engine falls back for that row, which is safe) |
| rocWMMA's CMake package | its imported target links `OpenMP::OpenMP_CXX`, which this project does not `find_package` -> the configure fails and the build tree cannot regenerate. Used the headers directly instead |

## The gfx11 WMMA port: feasibility proven, port not done

* This clang has both WMMA families - gfx11 (`__builtin_amdgcn_wmma_f32_16x16x16_f16_w32`) and gfx12
  (`..._w32_gfx12`); the engine only uses the gfx12 ones, gated `#if defined(__gfx1200__) || defined(__gfx1201__)`.
* `tools/hip/wmma_probe.cpp` (added, built as target `wmma_probe`) through **rocWMMA 2.2**:
  ```
  device: AMD Radeon RX 7900 XTX (gfx1100), hip 7.17
  correctness: 16x16x16 f16 WMMA vs FP32 reference, max abs diff 0.000000 -> OK
  throughput: 27,238,457 MMAs/s in one wave32 (0.037 us per MMA)
  ```
  So RDNA3's matrix cores are usable from HIP here and are exact against an FP32 reference. Using rocWMMA
  sidesteps the fragment-layout question entirely (`qsa_select.cu:421`'s "gfx1100 has WMMA too, with another layout").
* **Not done:** the actual port of `qsa_prompt_attn.cu` / `qsa_select.cu`. The remaining work is (a) a gfx11 branch
  in those kernels (rocWMMA fragments, or the gfx11 builtin with its own layout), (b) `hip_wmma_usable()` extended
  from `gfx12` to accept gfx1100, (c) validation with the existing parity tests - which need
  `-DSTRATA_BUILD_TESTS=ON` (`tools\hip\build_windows.bat tests`), not built yet.
* Expected value on **this** box is limited by the numbers above: the prompt path is I/O bound, so a faster
  attention kernel shrinks an already-minor term. It is the right port for a machine where the GPU is the limit.

## Installed configuration after this round

```
strata-iq2_xs.json args: --prefill auto --kv int8 --kv-resident 32768 --resident-experts --spec 4 ...
env: STRATA_RESIDENT_PIN=1                 (locked complement; the biggest single win)
     STRATA_HIPBLASLT_TUNING=<repo>/tools/hip/gfx1100-hipblaslt-100500.txt   (28 rows)
     STRATA_PREFILL_AUTO_MAX=16384  STRATA_PREFILL_MMQ=1  STRATA_PREFILL_RING=96  STRATA_IO_THREADS=32
     draft_vocab: en
live: resident 18.94 GiB locked, expert cache ~11,900 slots, KV streaming 32768 cells, hipBLASLt 28 rows
```

Prompt-path summary for this box, best measured: **1,103.7 t/s** (one sample); typical now **540-631 t/s** at
6-13k-token prompts, against **347-496 t/s** at the start of this round. Decode 35-100 t/s depending on the
state of the box.

## Follow-up: what the resident tier costs in RAM (the three low-RAM modes)

The locked complement that won above is real memory: with it, `strata.exe` held **20,313 MB working set /
39,327 MB private commit** and the box had **0.4 GB of RAM free** (system commit 69.9 of a 79.6 GB limit, a
48 GB pagefile). Switching to `--mmap-experts` (no resident copy at all - experts come through the OS file
cache) and measuring three passes each:

| | locked resident (`--resident-experts`, `STRATA_RESIDENT_PIN=1`) | pageable resident (`PIN=0`) | `--mmap-experts` |
| --- | ---: | ---: | ---: |
| prefill, ~6.2k prompt | **600-631 t/s** | 347-548 (variable) | 251-306 t/s |
| prefill, ~13k prompt | 544 t/s | 543-768 | 510-563 t/s |
| repeatability | 2 runs within 4% | 347 vs 548 across runs | **3 runs within 20%** |
| free RAM, idle | 0.4 GB | 0.4 GB | **4.1 GB** |
| `strata.exe` private commit | 39.3 GB | ~38 GB | **19.5 GB** |
| system commit used | 69.9 / 79.6 GB | ~70 GB | **50.3 / 79.6 GB** |
| can the OS take the pages back? | no (VirtualLock) | yes | yes (clean file-backed) |

So: **the lock is worth ~2x on a short (~6k-token) prompt, and ~nothing on a long (~13k) one**, and it costs
~20 GB of committed, non-evictable memory. The mmap mode's pages are clean file mappings, so the OS can evict
them under pressure - the right default on a 32 GB box shared with other work; the locked mode is right when
Strata is the only thing running. Both are one config edit away from each other (the file-cache pages refill
either way, so "free RAM" alone is not the measure - private commit and evictability are).

Note what is *not* the cause, per the engine's own counters: the experts are not "missing". The GPU holds
~12,000 of the 24,576, the resident tier holds the next ~12,000 by profile rank, the rest come from the pack
through the file cache, and the CPU pool computes any the GPU does not. The cost that dominates a prompt is
**copying** the experts the chunk needs into the GPU cache (`experts streamed 15,219, 0 by DMA, host 5,846 ms`
with the lock vs 9,410 ms without), plus the faults on unlocked pages - not a shortage of where the experts live.

Artifacts: `measure-stats.log` (the profile that drove all of this), `measure-{partial,pin-r2,nopin}.log`
(the lock A/B), `extend-table.log` + `tune-extend-8192.log` (per-shape tuning), `tools/hip/wmma_probe.cpp`,
`build-hip-win/wmma_probe.exe`, `prefill-table28-{A,B,C}.log`, `bench-table28{,-r2,-r3}.log`.

---

# On 0.1.40: `--kv k8v4` with KV streaming produces corrupt output

Tested on the user's 0.1.40 install (512K context, `--mmap-experts`, the control vector on, the 32-row table),
with `kv-fidelity.py` - five prompts whose exact answer is known:

| configuration | result | sample replies |
| --- | --- | --- |
| `--kv k8v4 --kv-resident 32768` (streaming on, **new in 0.1.40**) | **1/5** | `` '```json{"answer": "```"}' ``, `'user'`, `'100'` for 17x23 |
| `--kv k8v4`, **no** `--kv-resident` (KV in VRAM, the pre-0.1.40 arrangement) | **5/5** | `alpha`, `391`, `k8v4 live`, `391`, `Paris` |
| `--kv int8 --kv-resident 32768` (restored) | **5/5** | same |

So the corruption is specific to **k8v4 + KV streaming**, which is exactly the combination 0.1.40 introduced
(#711, "`--kv k8v4` with KV streaming"; `docs/INTEL.md` still said "`--kv k8v4` does not support streaming yet"
as of 0.1.39). `generate.cpp:663` describes the format: "hybrid: INT8 K (exact attention scores) + rotated Q4_0 V,
816 B/cell" - with the V stored rotated and 4-bit, the streamed read path is the suspect. Everything else was held
constant across the three runs, so no other knob (context, rope scaling, mmap, the control vector, the table) is
implicated.

Speed of the broken arm, for the record: k8v4 + streaming was **+8.6% prefill at ~6.9k / +3.3% at ~14.5k,
+30-58% decode**, and the KV's pinned RAM fell from 6.19 to 4.78 GiB with the expert cache at 11,867 slots
(vs 11,800) - a real win that cannot be used until the answer corruption is fixed. k8v4 *without* streaming is
correct but puts the whole 512K KV in VRAM, dropping the expert cache to **8,119 slots / 10.88 GiB** (-3,748 slots),
so it is a bad trade on this box. Installed: int8 + streaming.

Repro for an upstream issue: engine 0.1.40, Windows/HIP, gfx1100, Qwen3.8-Flash-Next IQ2_XS, IQ2_XS pack,
`--max-context 524288 --rope-scaling yarn --rope-scale 2 --kv k8v4 --kv-resident 32768 --mmap-experts` ->
1/5 exact; the same command without `--kv-resident` -> 5/5; with `--kv int8 --kv-resident 32768` -> 5/5.

# The experimental speed projection: what it is and what it costs here

The package's own README (`data/experimental-speed-projection/README.md`): a 480 KB control vector, one unit
direction of 2,560 values per layer (`direction.1`..`direction.47`), applied as `h -= (h . v) v` on every
hyper-connection stream after each of layers 4-44. The authors describe it as a **refusal-direction projection**
(1 of 50 refusals vs 50 of 50 on their test set): it removes a safety behaviour, which the README says makes the
operator responsible for what the model writes, and it shifts predictions slightly on ordinary text. It is not an
optimization - it changes what the model answers.

Cost, measured per request via the `"experimental_speed_projection": false` API field (no restart needed), 3 paired
rounds on the same prompt shape:

| | median prefill | median decode | median wall | text written |
| --- | ---: | ---: | ---: | ---: |
| projection on | 64.7 t/s | 62.6 t/s | 19.1 s | 346 chars |
| projection off | 67.8 t/s | 69.3 t/s | 17.8 s | 240-346 chars |

**-9.7% decode, -4.6% prefill** here, against upstream's 0.2-0.4% per token on an RTX 5070. The kernel
(`src/kernels/cuda/cvec.cu`) is "one block per (stream, token): the pending write, then `h . v` over the stream,
then the update" - 41 layers x 4 streams = ~164 extra small blocks per token, which costs more on a box whose
decode is launch/memory bound than on one that is compute bound. The README's other warning showed up too: with it
on the model wrote longer text, so wall-clock per request grows even at equal tok/s.

It is switchable per request (the web app's Sampling drawer, or the API field), so it can be left installed and
turned off per chat. `cvec-ab.py` re-measures it.

## The Monitor's empty AMD readings on Windows (2026-10-07)

The Monitor's GPU cards read nothing on this machine (`hardware_static.gpu_name None`, all five history series
`None`) because `serve/telemetry.py` read NVIDIA through NVML and AMD only on Linux through the amdgpu sysfs
files. Upstream, this is **PR #1224** (open, based on our commit 82f46a8, `serve/telemetry.py` +168/-3,
branch `contrib-amd-windows-monitor`): AMD on Windows through the **ADLXPybind wheel**, as an optional import.
Issue #1152 (with #712 history) is the other, broader contribution in this area.

Both paths that look obvious do not work, per the PR's own measurements, and it was worth not re-deriving them:
the old ADL Overdrive calls answer *not supported* on current Adrenalin (`ADL2_Overdrive6_Temperature_Get`
rc=-9, `..._CurrentPower_Get` 0 W), and the raw ADLX entry points are not a stable ctypes client (the 1.4
runtime's vtables close over internal objects; calling them faults).

Installed for our venv (Python 3.13.15, so the cp313 wheel fits): `pip install adlxpybind` → **1.4.6**, import
name `ADLXPybind`. The PR was applied, then validated here and fixed:

- **Works**: `gpu_reader(0, amd=True)` → `_AmdWindows`, `ok() True`, name `AMD Radeon RX 7900 XTX`,
  `_amd_windows_cards()` → `[('AMD Radeon RX 7900 XTX', 3)]`, `free_vram_mib` → 141 MiB. In the live server,
  `/metrics` gained `gpu_util 1 %`, `gpu_mem_used 24,394 of 24,560 MiB`, `gpu_temp 35.0 °C`, `gpu_power 22.0 W`
  and the four sparklines fill; `serve/test_monitor.py` passes 10/10.
- **Fixed — power**: the PR reads `GPUPower()`, which answers **0** on Adrenalin 32.0.31041 → power stayed
  `None`. `GPUTotalBoardPower()` reads the board (22-26 W) and is now the fallback.
- **Fixed — teardown**: the PR never calls `Terminate()`. Measured: skipping it **SIGSEGVs at exit (139)**,
  calling it exits 0 — so a clean stop of the server would report a crash. Now an `atexit` hook drops every
  live reader's ADLX references **before** `Terminate()` (an object outliving `Terminate()` crashed even with
  the call present) → exit 0.
- **Still blank**: `gpu_pcie_rx_mb` and the PCIe link card — ADLXPybind has no PCIe method and no throughput
  source exists on this platform. The link gen/width is available from the PnP device property
  (`DEVPKEY_PciDevice_CurrentLinkSpeed` / `_CurrentLinkWidth` → Gen4 x16 here), a separate change.

Artifacts: `pr1224.diff` (the PR as fetched), `pr1224-followups.md` (a ready-to-post comment with both fixes and
this evidence), `adlx-probe.py` / `adlx-metrics.py` / `adlx-bisect.py` (the probes),
`metrics-gpu.py` (dump the Monitor's GPU series from `/metrics`), `serve/telemetry.py.orig` (pre-PR file).

