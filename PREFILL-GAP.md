# Why our prefill was ~5x below the upstream author's — and the one flag that fixed it (2026-10-08)

The question: upstream's #1289 author measured **711 -> 938 tok/s** prompt on **the same GPU and the same quant**
(RX 7900 XTX, gfx1100, Qwen3.8-Flash-Next GSQ-RCO **IQ2_XS**, 192K ctx), and the docs' comparable tables show
~980-1,400 tok/s prompt on a 32 GB R9700. This box did **~180 tok/s**. Same GPU, same model, 4-5x apart.

## Where the time went (engine's own numbers, `--stats` on a 4,089-token prompt)

```
prefill 4089 tokens in 1 chunks, 22773.7 ms (179.5 tok/s); experts streamed 14667 (0 by DMA, host 21792.0 ms),
resident 6995; PLE 9.6 ms
expert tiers   ...; prompt copies 40914.2 MB
```

- **96% of prefill is the host staging path**: 21.8 s of 22.8 s, spent getting 14,667 expert blobs (~22 GB at
  ~1.5 MB each) into the GPU's arena. `0 by DMA` — every blob goes through the stager.
- **68% of the (layer, expert) pairs the prompt needs come from the files** (14,667 streamed of 21,662 total).
- **PLE is irrelevant**: `ple io: 65872 rows ... 888 SSD reads (3.7 MB), blocked 2.142 ms total`.
- Per token: 5.4 MB of expert data read per prompt token.

## Nothing was saturated — that was the clue

Sampling ADLX GPU utilisation + psutil disk + CPU once a second across a prefill:

```
  t     GPU%   power W   disk MB/s  cpu%
  55s     51      129         914
  60s     52      132         876
  67s     51      130         861
```

**GPU 30-52% busy at ~100 W of ~355 W, CPU ~20%, disk ~0.9 GB/s.** And in the *same* engine run the CPU pool
reported **4.2 GB/s over the rows phases** — so the drive was never the limit.

## What the drive can actually do (unbuffered, like the engine, measured directly)

| pattern | rate |
|---|---|
| 0.5 MB windows | 946 MB/s |
| 1.5 MB windows | 2,139 MB/s |
| 4.2 MB windows | 2,898 MB/s |
| 8.4 MB windows | 3,075 MB/s |
| 2 / 4 / 8 threads x 1.5 MB scattered | 3,368 / 3,446 / 3,448 MB/s |

The engine was sustaining ~1.0 GB/s against a drive capable of 2-3 GB/s. And re-running the identical prompt with
a warm page cache changed **nothing** (183.1 -> 182.1 tok/s; the same 14,667 blobs, same ~1.1 GB/s peak), which
ruled the page cache out as a helper: the reads were passing *through* it, on a 35.45 GB `experts.bin` with only
~7 GB of free RAM.

## Levers that did NOT help (each measured, same prompt, one variable)

| tried | result |
|---|---|
| `STRATA_IO_THREADS` 4 / 8 / 16 / 32 | 175.3 / 187.9 / 179.6 / 178.5 tok/s — **no effect** (queue depth is not the limit) |
| `STRATA_UNBUFFERED_LOAD=1` | **ignored**: `the file tier reads through the file cache (STRATA_UNBUFFERED_LOAD=1 ignored: without --resident-budget-gib the file cache holds the experts)` |
| workload-fitted expert profile (`--dump-routing` on a 3,806-token trace prompt -> `make_profile.py --reorder`, 5,460 ranks moved) | resident 6,995 -> 7,556 (+8%), from-files 68% -> 66%, prefill 184.1 -> 172.3 tok/s — **no gain** |

## The lever that did: `--resident-budget-gib`

The engine's own message named the missing flag. Setting it switches the file tier to **unbuffered** reads (and
gives the RAM complement an explicit budget instead of leaving the working set to the page cache):

```
strata generate: the file tier reads unbuffered (17.3 GiB available, ... the file cache cannot keep them)
FileExpertSource: --resident-budget-gib 18.00 exceeds available RAM (16.65 GiB minus 4 GiB headroom and a
                  0.25 GiB margin): 12.40 GiB
FileExpertSource: RAM budget 12.40 GiB: 9198 of the 17.21 GiB of experts the GPU cache does not hold, by profile rank
```

| measurement | before | with `--resident-budget-gib 18` |
|---|---|---|
| engine prefill tok/s (CLI, 4,089 tok) | 179.5 (175-188 across runs) | **751.8** |
| host staging | 21.8 - 23.6 s | **2.9 s** |
| disk peak | ~1.5 GB/s | **2.65 GB/s** |
| live server, 4,159-token prompt (wall) | 22.1 / 23.0 / 23.0 / 22.3 s | **7.3 / 6.7 / 6.6 s** |
| live server engine-side rate | ~189 tok/s | **~590 tok/s** |
| server startup | ~45-50 s | ~20 s |

That puts this box back inside the upstream band (711-938 tok/s at the same quant on the same card), and the
mechanism is now fully accounted for: **the expert reads were going through the Windows page cache of a 35 GB
file whose working set (22 GB per prompt) exceeds free RAM, at ~1 GB/s; unbuffered reads of the same volume run at
2.6 GB/s and the RAM complement serves most of the stragglers.** The 4-5x "gap vs upstream" was this read path,
not the GPU, the GEMM, the table, the thread count or the profile.

## Notes and caveats

- The budget **clamps to available RAM** (asked 18, got 12.17-12.40 GiB, keeping the documented 4 GiB headroom).
  Freeing RAM before launch raises it; running other RAM-heavy apps at launch lowers it, and the engine says so.
- Page-locking is still refused (`locked 12465 MiB via working-set minimum + VirtualLock`) - the pre-existing
  Windows/AMD limitation. With unbuffered reads it no longer costs us the prefill.
- `STRATA_RESIDENT_PIN=1` (restored earlier) is now largely redundant: the budget's complement locks itself.
- The shape of the earlier finding still holds: the 43-row hipBLASLt table removed 383 expert-GEMM fallbacks, which
  was worth only ~5-9% end-to-end because the GEMM was never the critical path. This is the critical path.

## What is on the box now

- `strata-iq2_xs.json`: `args` gained `--resident-budget-gib 18` (backup: `strata-iq2_xs.json.bak-prebudget`).
- Verified after the change: `17*23 -> 391` correct, `hipBLASLt tuning enabled (43 rows, gfx1100, version 100500)`,
  0 `Lt fallback`, server healthy, startup ~20 s.
- Instruments written for this (reusable): `prefill-stats.py` (engine `--stats` on a tokenized prompt),
  `make-tokens.py` (token ids for the CLI, which has no tokenizer), `prefill-disk.py` (cold vs warm re-read),
  `prefill-where.py` (GPU/CPU/disk timeline during a prefill), `disk-bench.py` / `disk-bench2.py` (unbuffered drive
  rates by window size and queue depth), `io-thread-sweep.py` / `env-ab.py` / `args-test.py` (one-variable A/Bs),
  `profile-ab.py` (routing trace -> profile -> measure), `prefill-ab.py` (live-server A/B).
- Logs: `logs/prefill-stats.log`, `logs/prefill-disk-run1.log` / `-run2-warm.log`, `logs/prefill-where.out`,
  `logs/disk-bench*.out`, `logs/io-thread-sweep.out`, `logs/env-ab-unbuffered.out`, `logs/profile-ab.out`,
  `logs/args-budget18.out`, `logs/ab-*.out`.

## Where the remaining upside is

1. **#1323** (batched unbuffered stager reads, open PR, based on our HEAD): the drive does 3.0-3.4 GB/s with
   bigger windows / more depth; we now run 2.65 GB/s peak. A further ~20-25% of the read time may be there.
2. **Free RAM before launch** to raise the clamped budget (12.2 -> e.g. 16 GiB), cutting the residual file reads.
3. **More VRAM for experts** (fewer/`--kv-resident` cells), if decode can spare it.
