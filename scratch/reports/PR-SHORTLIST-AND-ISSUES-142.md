# Shortlist PRs + issues pass (2026-10-11)

The six remaining shortlist PRs are in, each merged as a real `git merge` of its branch (so every one is its
own commit, attributed), then the issue tracker was read for ideas. One of those ideas is the largest single
win of the session.

## 1. Applied

| PR | what | merged how |
| --- | --- | --- |
| **#1297** | gfx1100 decode autotuning: `decode_tuning.{hpp,cpp}`, the `iq_kernels` hook, `tools/hip/{autotune,tune_decode}` | auto-merged except CMakeLists (both), `setup.py` + `calibrate.py` taken from upstream (the PR's copies predate 0.1.42's tuning flow) |
| **#1909** | process all groups in fused GU and LDS down launches | applied |
| **#1324** | the RAM tier's LRU stage pool | conservative merge, see below |
| **#1167** | rocBLAS solution table for the FP16 prompt GEMMs | clean; inert on gfx1100 without a gfx1100 table |
| **#1298** | gfx110x fp16 rocWMMA qsa-select arm, opt-in | additive conflicts, both sides kept |
| **#1151** | FP32 tiled QSA block scorer on HIP, opt-in | additive conflicts, both sides kept |

**#1324 took four build fixes** before it linked: the header merge dropped `uint64_t lru_cap_` and the
`StageFree` struct, a brace was lost at the `cached_share`/`stage_keep_env` boundary, and the "both" pull left a
duplicate `copy_blobs` (upstream's own already consults the staged tier). The merge keeps upstream's **pinned**
allocator (strictly better than the PR's VirtualAlloc) and the LRU's bookkeeping, and deliberately does **not**
take the PR's freed-slot *reuse*: that is the half that could hand out a slot the watcher freed, it only
matters after a shrink, and a mistake there is a use-after-free in the staging path. The LRU is opt-in
(`--resident-lru-gib`, `STRATA_STAGE_KEEP_MIB`), so default behaviour is unchanged.

## 2. Measured

Shortlist binary vs the previous live one — no default change, as expected (every arm in it is opt-in or needs
a tuning table):

| arm | 4K | 16K |
| --- | --- | --- |
| 142-4pr (previous live) | 770.5 | 1596.4 |
| 142-all (the shortlist) | 770.5 | 1581.9 |
| + `--resident-lru-gib 4` | 837.7 (budget 11.9 -> 9.1 GiB) | 1572.4 |

**The ring sizing — from issue #1549 — is the win:**

| `STRATA_PREFILL_RING` | 4K | 16K |
| --- | --- | --- |
| 96 (ours, removed) | 872.9 | 1629.4 |
| 512 | 830.0 | - |
| **384** | **1017.3 (+16.5%)** | **1806.3 (+10.9%)** |
| 1024 | 998.1 | 1786.4 |

384 is exactly what the engine picks itself: `ring_default_slots()` returns 384 (1024 for a fused ring) when
`g_pinned_share >= 0.9`, and 96 otherwise — issue #1549 spells this out while investigating its own mirror
pathology. Our override to 96 was from tuning against the smaller earlier budget. **Adopted: the override is
gone**, so the engine's own rule applies. The LRU stays off for now (it buys prefill but eats the resident
budget: 11.9 -> 9.1 GiB).

## 3. Issues read

- **#1549** "prompt reading is 72x slower when experts come from the host mirror" → the ring-sizing insight
  above. The issue also documents the `g_pinned_share` threshold that explains why our 96-slot override was
  costing us.
- **#1712** 2x RX 7900 XTX (HIP) memory-access faults. Its `rocm-debug-agent` trace is the useful part: on
  **gfx1100 `qsa_prompt` returns false, so every prompt chunk runs the decode attention kernel** — which is
  precisely what #1298's rocWMMA arm and #1151's FP32 tiled scorer target. Its workaround,
  `--no-prefill-borrow`, costs 28% prefill (its sibling report #1910), so it stays a debugging lever, not a
  setting. Also worth knowing: our `--max-context 524288` doubles the attention page table the trace implicates
  (65536 entries at 262144).
- **#1910** "0.1.42 prefill 35-55% slower" is dual-GPU CUDA on a cold 40K prefix; the single-GPU HIP numbers
  here do not show it (0.1.42 was +5.6% over 0.1.41 at 16K), so it is not ours to chase.
- **#1906** agent client on 0.1.42: 9 full prompt re-reads (`reused 0`) in 23 minutes. Worth checking on this
  box: whether our conversation cache reuses a growing prefix, or re-reads it every turn.
- **#1913** decode speed bistable within a session: the per-layer host cost per expert entry jumps 3-5x and
  stays, while entries/window, GPU wait and CPU kernel time do not move. `STRATA_DECODE_TIMING=1` is the
  diagnostic; our decode (14-25 ms/token, pool 50-73%) is the right place to look for it.
- **#1903** Windows arena mode: ~3.2 ms of each window sits outside the timing breakdown, and WDDM
  page-locks only the first ~30 GiB, so layers beyond get no PCIe share. On a 32 GB box the second half is
  the relevant one: which layers hold the RAM residency is a tuning axis we have not tried (our expert
  profile picks by frequency).
