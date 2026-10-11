# PR triage, second pass: 0.1.41 line (2026-10-10)

Continues `TRIAGE-141.md` (the 0.1.41 pull). Upstream `main` has **not** moved since that pull — still
`fb58e0db`, 2026-10-08 — so this pass is about the **PR pile only**: 381 open PRs, against the ~150 that
existed at the last pass.

Method, all three tools are in `scratch/scripts/`:
`pr-triage.py` ranks the pile by keyword fit for this box (gfx1100 / HIP / Windows / IQ2_XS, prefill+decode+memory);
`pr-check.py` fetches the selected diffs and says whether each still applies (`plain`, `3-way`, or "read first");
`patch-audit.py` measures line-level coverage of a diff against a tree, which is the only thing that distinguishes
"upstream landed it in another shape" from "we never had it".

## 1. #1451 — ported (it was never actually wired up)

Our 0.1.41 application landed #1451's helper (`src/prefill/ple_host_buffer.hpp`) and its test, but **`prefill.cpp`
had zero `ensure_ple_host` call sites** (tuned-1403 has one): the helper was dead code and `init()` still allocated
both PLE host buffers eagerly at `T*N*4`. The commit that claimed "#1451 applied; live on HIP" was wrong; the
line-level audit is what caught it (48/53 of the PR's lines present, and the 5 missing ones were exactly the call
sites).

Took the PR's current shape (commit `cfb55dca`): the allocation moves into `run_impl`, lazily, buffer two only when
a following chunk exists, retained capacity kept.

| prompt | before | after | host staging |
| --- | --- | --- | --- |
| 4K | 795.1 tok/s | **840.5** | 3438 → 3059 ms |
| 16K | 1525.3 tok/s | **1572.0** | 4530 → 4417 ms |

## 2. #1416 — nothing to port; upstream is *ahead* of the PR

The conflict against our tree is the answer: `ours` is `arm_cpu_share(bool applies, bool by_default = false)` with
measured-path defaults, `theirs` is the PR's older one-argument form. Upstream 0.1.41 already carries the staged
limit the PR adds (`STRATA_PREFILL_CPU_SHARE_MAX`, default 3072; `g_stream_min_share = cpu_share_max()`) and guards
its default-on path `#if !defined(STRATA_USE_HIP)` — on HIP the share runs only when the variable is set, which our
config does (`STRATA_PREFILL_CPU_SHARE=auto`). The old "not re-applied" note was right, for the wrong reason.

## 3. #1101 and #1237 — superseded, and #1237's form is unsafe

- **#1101** (stager threads sleep instead of yield-spinning): upstream already has it *plus* a `stager_sleep()`
  helper with a separate Windows path and a batched `copy_blobs(rl, re, rd, nr)` loop where the PR has a per-job
  `copy_blob`. Applying the PR would move the stager backwards.
- **#1237** (pinned cache-fill stage buffers): upstream has the feature **and the fix for what it broke** —
  `STAGE_PIN_DEFAULT 0` with the note that pinning "corrupted IQ3_S decode after a 4096-token prompt in the 0.1.41
  release gate (48 tokens of id 0) ... a recycled stage buffer can be overwritten before its copy finishes". The
  PR revision predates that, so its always-pin form would re-arm the corruption. Skipped deliberately.

## 4. Applied: #1660 + #1520 + #1107 (commit `35320949`)

| PR | what it does | why it is on target here |
| --- | --- | --- |
| **#1660** | MMQ resident sort takes native-layout packs (`(void) native_layout`) | our config passes `--native` + `STRATA_PREFILL_MMQ=1`; the PR measures 1.2K 7.27→5.32 s, 35K 63.3→54.1 s (same bits) |
| **#1520** | `STRATA_FILE_RELEASE` extends to prefill staging copies (opt-in) | our RAM budget is the clamp: 32 GB box, `--mmap-experts`, budget ~10 GiB |
| **#1107** | short-prompt staged walk through a grouped ring (`STAGE_GRP=32`) | chat-sized prompts are our common case |

Measured (4K / 16K prompts, one engine restart per arm):

| arm | prefill | host staging |
| --- | --- | --- |
| #1451 only | 791.5 / 1420.6 | 3049 / 4557 ms |
| **+ batch** | **829.1 / 1481.2** (+4.7% / +4.3%) | 2931 / 4551 ms |
| + batch, `STRATA_FILE_RELEASE=1` | 777.2 (−6.3%, no budget gain) | 3023 ms |

`STRATA_FILE_RELEASE` stays **off**: the PR's own numbers (+11.7 GiB available RAM for 3.7-4.4% throughput) do not
pay here, and the budget did not rise (10.4 → 10.2 GiB). The code is in, the switch is not. The live config now runs
`strata-141-batch.exe`.

## 5. Shortlist for the next cycle (read, not applied)

Ranked by (fit for this box) x (plausible size of win); each applies cleanly or with a 3-way merge:

1. **#1324** — file tier: an LRU part of the RAM budget (`--resident-lru-gib`). +506/−32. The one left from the
   previous pass: the PR's replay cut decode drive reads 182 → ~100 GiB.
2. **#1297** — HIP on-device autotuning for **gfx1100** decode (kernel shapes). +2078/−75. Our decode pool is
   50-73% of a token; this is aimed exactly there.
3. **#1167** — rocBLAS solution table for the FP16 prompt GEMMs. +1309/−6. We carry a 45-row hipBLASLt table;
   this is the same lever for the other library.
4. **#1298 / #1151** — the rocWMMA gfx110x qsa-select arm and the FP32 tiled QSA block scorer (both opt-in arms,
   both previously tried on the 82f46a8-era tree with inconclusive results — worth a re-run on this base).
5. **#1841** — opt-in VRAM headroom for `--expert-cache auto` (OOM safety rather than speed).
6. **#1656** — pipeline-windows, three or more layer-split stages (+14% decode there) — only if we ever split.
7. **#1820** — qwen35moe follow-ups (VRAM cap, quality mode, MTP for F16): our architecture, but 69 files and
   +5450/−905; needs a careful read rather than a blind apply.

## 6. What the pile looks like now

381 open, of which the keyword filter puts ~30 within reach of a gfx1100/HIP/Windows build; the rest are SYCL/XMX,
Intel Arc, CUDA-12/Docker, Pascal/Blackwell, web-UI, math-rendering, translation or bench-report PRs. Long prompt
reads are now at 1.48k tok/s (16K synthetic) and 1.26k (73K real text), decode ~30 tok/s short-turn with 33/36 drafts
accepted.
