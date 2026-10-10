# Triage on the way to v0.1.41 — and the tuning breadcrumbs in the issues

Pulled upstream and triaged the open PRs **and issues** with an eye for engine-tuning knowledge. Continues
`UPDATES-1403.md` (§1-11). Date: 2026-10-08 evening.

## 1. What the pull brought

`main` fast-forwarded **d5ea713 → fb58e0db**: **128 commits**, two releases, plus one post-release fix.

- **v0.1.40.4** — hotfix: decode on Pascal (sm_61) halved since 0.1.40.2 (kernels lost `__restrict__`, gained a
  prefetch Pascal cannot overlap). Not our hardware; Volta+ code is byte-identical.
- **v0.1.41** (published today 12:14Z) — the interesting one, see §2.
- Post-release on main: **`STRATA_STAGE_PIN` is now opt-in** — "on by default it corrupted IQ3_S decode after a
  long prompt in the release gate" (`expert_source.cpp:1152`, PR #1237's pinned stage buffers).

Our work is untouched on `tuned-1403` (`778763d`); the tree was switched to `main` for these reads only.

## 2. What 0.1.41 changes for tuning (from its own notes)

| change | relevance to this box |
|---|---|
| **Short prompts: the CPU helps below 1,024-token chunks — now a default, but NVIDIA-only** ("layer splits, batch and AMD are as before") | **AMD is unchanged, so our manual `STRATA_PREFILL_CPU_SHARE=auto` is still how we get it.** `=0` gives exact 0.1.40.x answers |
| **"About twice as fast prompts on Windows with little RAM"** — RTX 5070 +16% / +23-25% at 4K / 20K with a RAM budget, decode +3% | this is *our* configuration class (Windows + RAM budget + 4K+ prompts) |
| `--batch-groups auto` default (one pipeline group per GPU; 8 clients +32-68%) | irrelevant, single GPU |
| `STRATA_HTTP_BACKLOG` (backlog 256; 0 resets at 40 clients) | only if we ever serve many clients |
| `STRATA_PREFILL_CPU_SHARE=0` restores bit-exact 0.1.40.x answers (first-token KL 0.004 avg) | the escape hatch we'd use if the share ever changes an answer |

## 3. Tuning breadcrumbs found in the issues (the point of the exercise)

| source | knob / fact | detail |
|---|---|---|
| **#1630** (our exact GPU: RX 7900 XTX, Windows, HIP, 0.1.41) | **prompt chunk size vs the Windows commit limit** | a long prompt with `--prefill auto` (which picks **8192** on this card) makes the **system commit charge jump ~70 GB in one second**; the engine then dies with `0xC0000409` and the server answers 503. **≤7500 stays flat.** Their triggers were 20-30K-token agent turns |
| **#1607** (Windows, detailed) | why the commit limit kills | the engine exits `0xC0000409` when commit (RAM+page file) is exhausted *even with GiB of physical RAM free*: the conversation-cache admission reads only `ullAvailPhys`; under WDDM **VRAM is charged to commit** too (#141). Reproduced 6× within 0.1 GiB of the limit, right after a prompt read |
| **#1549** (host mirror, 72x prompt slowdown) | diagnostic env knobs: `STRATA_PREFILL_TIMING`, `STRATA_GEMM_STATS`, `STRATA_DQ_STATS`, `STRATA_VERIFY_EAGER`, `--stream-experts` | the thread's numbers are an Intel OpenCL/eager-backend artefact (a Level-Zero machine with graphs reads the same IQ2_XS mirror at 718 tok/s), but the knob list is gold |
| **`STRATA_PREFILL_TIMING=1`** (new tree, `prefill.cpp:1878`) | **built-in prompt-path GPU phase timing** | "the prompt path's GPU time by phase. Events are recorded on the compute stream in order" — supersedes our hand-rolled prefill profiling |
| **`STRATA_WDDM_BUDGET`** (new tree, `src/core/device.cu:186`) | VRAM reporting under WDDM | `=0` turns the WDDM budget accounting off in `mem_get_info`; affects how much free VRAM the engine believes it has |
| **#1479** (HIP, AMD) | `STRATA_HEAD_MIX_MULTI` / `STRATA_ONE_TOKEN_COMMIT` are compiled to `return false` on HIP | the patch makes them opt-ins: head-mix is **+0.4% decode, bitwise identical** on R9700 (gfx1201); `ONE_TOKEN_COMMIT` was neutral. Small but exact and free |
| **#1595** (CPU share, V100, all experts resident) | the share can *cost* | 256/512 tokens: 0% / +0.3%; **1,000 tokens: +4.8% slower**; 4,096: share not used. "When every expert is already on the GPU there is nothing for the CPU to save" |
| **#1586** (tester report, 0.1.41 `fb58e0db`) | values from a **Ryzen 7 9800X3D + 32 GB** box (same CPU/RAM as ours) | `--resident-experts`, `layer_split 29`, `--pipeline-windows 2 --adapt-async 1`, `--vram-reserve-mib 700`, `--trim-stage-weights`, `STRATA_ADAPT_LAG=2`, `STRATA_PF_FUSED=1`, `--kv int8 --max-context 262144`; decode 100-140 tok/s over a 2x3090 split |
| #1571 | Windows `--resident-experts` keeps `experts.bin` mapped while building the RAM copy | the same mapped-file trap our #1323 fixed; worth watching |
| #1587 | Windows + AMD: the Monitor shows no GPU data at all | the telemetry gap our ADLX patch fills |
| #1644 | Windows HIP gfx1100 (7900 XT): `mtp prefill: unsupported` | our MTP path on gfx1100 |
| #1543 / #1500 / #1519 / #1607 | AMD idle power; engines "stopping unexpectedly" | the family of silent Windows deaths |

## 4. Risks this raises for our current config

1. **`STRATA_PREFILL_AUTO_MAX=16384` is above the reported safe chunk size on our exact card.** #1630 puts the
   threshold between **7500 and 8192** on a 7900 XTX, with the crash at 8192. Any long agent-style prompt (20-30K
   tokens) would chunk at 16,384 here. **Action: set 8192 or 7500** — nothing we run today (4K prompts) is affected
   either way, so this is pure insurance.
2. **Commit-limit exposure.** Our commit limit is **77.6 GB** (32 GB RAM + a 46 GiB `C:\pagefile.sys`, currently
   25 GB used, peak 27 GB). Under WDDM the 24 GB of VRAM is charged to it as well, and `STRATA_RESIDENT_HEADROOM_GIB=2`
   deliberately leaves less RAM free. The +9% prefill we took may be buying that with margin. **Action: measure
   commit charge while the server is loaded** (`\Memory\% Committed Bytes In Use`) before trusting it under long prompts.
3. **`STRATA_PREFILL_CPU_SHARE=auto` may cost ~5% at ~1,000 tokens** (#1595). We measured a win at 87-108 tokens and
   neutral at 4K, but never at 1,000. **Action: measure 1,000-token prompts with the share on/off.**
4. **Pinned stage buffers are now off by default upstream** because they corrupted IQ3_S decode after a long prompt
   (`STRATA_STAGE_PIN`). Our own corruption history (k8v4 + streaming, #1188) says the same class of bug is easy to
   reintroduce with pinning. Keep pinning strictly to what we've verified.

## 5. Newly relevant PRs from today's 138

| PR | what | why it matters |
|---|---|---|
| **#1520** | prefill: release copied Windows expert pages after host staging | Windows + host staging is exactly our 37% |
| **#1533** | free RAM on machines with more VRAM by not holding VRAM experts in RAM | our 11-13 GiB resident complement is the prefill lever |
| **#1524** | wider speculative batches + shared experts: 1.31-2.07x c4 throughput | decode/spec, our other half |
| **#1525** | dense IQ4_XS / Q8_0 to FP16 with 16-byte stores, swiglu + q8_1, MoE combine | our dense/embedding weights are IQ4_XS |
| **#1548** | `STRATA_PCIE_BALANCE=1`: per-layer PCIe count from measured costs | replaces our fixed `--pcie-frac 0.55` |
| **#1551** | `--help`: the 16 options accepted without a line of their own | documentation of hidden knobs |
| **#1547** | opt-in per-layer expert routing metrics for `/metrics` | tuning telemetry |
| #1516 | PLE prompt rows through 8 batch readers (32K chunk -3%) | a regression, not a win — avoid |
| #1498 | KV streaming under WSL: pin the host copy with `cudaHostRegister` | WSL only |
| #1507 | chat context gauge, per-request timings, compaction | UI-side visibility |

## 6. Housekeeping

The local `OPTIONS-REFERENCE.md` / `options-inventory.csv` (161 flags / 360 env vars) were compiled from the
**0.1.40.3-era** tree: `STRATA_PREFILL_FIRST`, `STRATA_PREFILL_SYNC`, `STRATA_PREFILL_STREAM_ALL` **no longer exist**
in `fb58e0db`, and the new knobs (`STRATA_STAGE_PIN`, `STRATA_PCIE_BALANCE`, `STRATA_HC_REQ8`,
`STRATA_ROUTE_RESIDENT`) are absent. Regenerate it against `main` before leaning on it. Its counting also differs
the new tree reads ~312 distinct env names.

## 7. Suggested order of work

1. Reduce `STRATA_PREFILL_AUTO_MAX` to **8192** (or 7500) — one line, removes a documented crash path on this GPU.
2. Measure commit charge under load, then decide whether `STRATA_RESIDENT_HEADROOM_GIB=2` is worth keeping.
3. Measure `STRATA_PREFILL_CPU_SHARE` on/off at **1,000 tokens** (#1595's case) before it stays default in our config.
4. Rebuild on 0.1.41 (`fb58e0db`) with our patch set re-applied (#1323/#1372/#1439/#1448/#1381/#1457/#1416/#1451),
   then re-run the A/B harnesses — the release claims +16-25% at 4K/20K on Windows-with-a-RAM-budget, which is us.
5. Regenerate the options inventory on the new tree; use `STRATA_PREFILL_TIMING=1` instead of hand-rolled profiling.
