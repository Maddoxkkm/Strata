# IQ2_XS vs IQ3_S, same box, same config

Two ISTA quantizations of the same model on the single RX 7900 XTX, measured back to back after a reboot so
both got their biggest RAM tiers yet.

| | IQ2_XS | IQ3_S | ratio |
|---|---|---|---|
| raw GGUF (2 shards) | 63.35 GiB | 77.87 GiB | 1.23x |
| pack `experts.bin` | 33.02 GiB | 46.84 GiB | **1.42x** |
| pack `dense.bin` | 1.43 GiB | 1.43 GiB | 1.00x (byte-identical, as `iq_pack.py` promises) |
| RAM budget during the runs | 13.2-13.5 GiB | 13.9-14.1 GiB | ~1.04x |

Config identical apart from `--pack` / `--native` / `--ple-gguf`: `--prefill 16384`, `--kv int8`,
`--resident-budget-gib 18`, `--mmap-experts`, the same MTP head, and the same switch set (WMMA + SIMT select,
`PA_FAST`, `PF_GEMM`, `PF_PAD`, `PF_SWITCH_MIN_T`, `RAM_ADAPT`).

## Prefill, synthetic token-file ladder

| prompt | IQ2_XS | IQ3_S | delta |
|---|---|---|---|
| 4K | 969.0 | 556.3 | -43% |
| 16K | 2,143.0 | 1,601.7 | -25% |
| 32K | 2,193.6 | 1,620.1 | -26% |
| 16K (repeat) | 2,031.1 | 1,577.6 | -22% |

Host staging time at 16K doubles (3,254 ms -> 6,901 ms) and the share read from files rises 4-6 points
(72-84% -> 82-88%).

## Prefill, 73K real text through the server

| | IQ2_XS | IQ3_S | delta |
|---|---|---|---|
| 73,037-token prompt | 1,796.1 tok/s | 1,769.7 tok/s | **-1.5%** |

## Decode, 256-token answers, warm session (wall clock, 3 rounds)

| | round 1 (cold) | round 2 | round 3 |
|---|---|---|---|
| IQ2_XS | 40.6 tok/s | 78.5 | 82.6 |
| IQ3_S | 40.0 tok/s | 80.0 | 82.6 |

The same within noise. (The A/B harness's per-arm `decode` column is not usable for this: it gave IQ3_S 25.4 at
4K and 7.9 at 16K while IQ2_XS read 21-23 throughout. It samples a short cold burst right after a long prompt,
so it moves with cache state, not with the model.)

## Answers to the same five questions

Identical for four of them (`391`, `atarts`, `9/13`, and a comparable process/thread paragraph). The one
difference: the average-speed question, where **IQ3_S answered `84 km/h` (correct) and IQ2_XS answered
`100 km/h`**. One question out of five is not a benchmark, but it is the direction the extra bytes are meant to
buy.

## What this means

- **On real text, IQ3_S costs nothing measurable** (-1.5% prefill, identical decode) while carrying 23% more
  file bytes and a 42% bigger experts pack.
- **The synthetic token-file ladder overstates the difference** (-25%): a repeated-token prompt routes to a
  narrow expert set, so the bigger blobs hurt more there than they do on prose. Do not use the ladder alone to
  judge a quant — this is the second time it has flattered one model over another on this box.
- The cost is disk and memory footprint: 145 GiB for IQ3_S against 130 GiB for IQ2_XS on C:, and its expert
  blobs occupy 42% more of every tier.

Practical call: IQ2_XS stays the daily default (identical real-world speed for less disk and less tier
pressure); IQ3_S is worth keeping alongside it if the quality edge shows up on work that matters — it is
essentially free in time and there is room for both.

Footprint actually on disk: **IQ2_XS 97.8 GiB** (63.4 raw + 34.5 pack), **IQ3_S 126.2 GiB** (77.9 + 48.3) —
28.3 GiB more. C: went from 252.2 to 106.6 GiB free, so about **19 GiB of that is the HF downloader's leftover
chunk cache** under `models/.cache`: deleting that directory reclaims it once the shards are complete and
verified.
