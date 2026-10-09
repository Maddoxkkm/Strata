# Strata — every option that can be set, in one place

Machine-compiled from the code, not from a README: the engine's `Options` struct and its argument parser
(`src/program/generate.cpp`), the server's config reader (`serve/server.py`, `serve/runconfig.py`), `setup.py`'s
writer, and every `getenv` / `os.environ` call in the tree. Tidy long-format copy: `options-inventory.csv`.

Counts: 161 engine CLI flags, 360 environment variables, 45 config keys, 17 server CLI flags, 41 setup CLI flags, 19 per-request keys.

## 0. How the layers fit together

```
strata-<model>.json                     <- the file you edit
  exe, args, env, cwd, lib_dirs         -> the engine process: args = CLI flags (§2), env = its environment (§3)
  every other key                       -> the server itself: network, security, sampling defaults, lifecycle (§1)
  the run command                       -> setup.py writes it; --port and --open come from the .bat, not the JSON
  strata-<model>.shared-settings.json   -> POST /settings values, persisted next to the config (§6)
```

Precedence as the code implements it: an explicit CLI flag beats the model file's own keys, which beat the
struct defaults; a request's own sampling fields beat the config's `sampling` block, which beats the built-in
defaults; `runconfig.py`'s Settings view can change only the 12 keys it lists and preserves everything else.

## 1. Keys the JSON config accepts

`default` is what the code falls back to when the key is absent.

### 1.1 Top level

| key | what the code does with it | default | read at |
|---|---|---|---|
| `aliases` | other model names the server answers to | unset | `serve/server.py:5458` |
| `allowed_hosts` | Host allow-list (also `STRATA_ALLOWED_HOSTS`) | unset | `serve/server.py:5480` |
| `anthropic_thinking` | Anthropic requests that do not ask for thinking | unset | `serve/server.py:5509` |
| `api_key` | required from clients (also `STRATA_API_KEY`) | "" | `serve/server.py:5470` |
| `api_monitor` | keep the last 100 requests for /api-monitor | unset | `serve/server.py:5486` |
| `backend` | `hip`: AMD device numbering and readings | unset | `serve/server.py:2148` |
| `before_load` | command run before the model is loaded again | unset | `serve/server.py:5498` |
| `codex_compaction_cache` | opt-in (#924) | unset | `serve/server.py:5456` |
| `codex_thread_titles` | opt-in (#923) | unset | `serve/server.py:5455` |
| `cors_origins` | Origin allow-list | unset | `serve/server.py:5477` |
| `cwd` | work directory; relative paths resolve against it | unset | `serve/server.py:2120` |
| `effort_position` | where a non-default reasoning effort goes | "start" | `serve/server.py:1975` |
| `engine_silence_s` | end a request when the engine says nothing this long | unset | `serve/server.py:1998` |
| `env` | the engine process environment — §3 | unset | `serve/server.py:2153` |
| `expert_profile_save` | -> adds `--expert-profile-save`; replaces `--expert-profile` with the learned profile when shapes match (#477) | unset | `serve/server.py:2111` |
| `expert_profile_save_every` | -> adds `--expert-profile-save-every` | unset | `serve/server.py:2115` |
| `fit_max_tokens` | shorten an oversized max_tokens instead of answering 400 | unset | `serve/server.py:5453` |
| `gpu` | device index or list; a list means a layer split | unset | `serve/server.py:1726` |
| `hip_ordinal` | the HIP ordinal setup recorded (#325); wins for a one-card config | unset | `serve/server.py:2135` |
| `host` | bind address | unset | `serve/server.py:5373` |
| `idle_unload_s` | unload after N seconds without requests (0 = never) | unset | `serve/server.py:5495` |
| `layer_split` | `auto`, `K` or `K1,K2,...` — the server adds `--layer-split` | unset | `serve/server.py:2011` |
| `lazy_load` | start unloaded, load on first request (text only; refused when `vision` is set) | unset | `serve/server.py:5403` |
| `lib_dirs` | library dirs prepended to PATH (Windows) / LD_LIBRARY_PATH | unset | `serve/server.py:2155` |
| `log` | engine log, opened in append mode | unset | `serve/server.py:2187` |
| `max_tokens` |  | unset | `serve/server.py:1730` |
| `min_free_vram_mib` | refuse to start below this free VRAM | unset | `serve/server.py:5497` |
| `min_tokens` |  | unset | `serve/server.py:1732` |
| `model_name` | the name clients send as `model` | "qwen3.8-flash-next" | `serve/server.py:5451` |
| `open_browser` | open the chat page when ready | unset | `serve/server.py:5581` |
| `parallel` | N -> the server adds `--batch N` (max 8; warns, never forces) | unset | `serve/server.py:2075` |
| `reasoning_budget_tokens` | thinking cap for every request | unset | `serve/server.py:5522` |
| `reasoning_close_retry` | opt-in (#1053) | unset | `serve/server.py:5454` |
| `reasoning_loop_recovery` | false \| "stop" \| "recover" (#728) | False | `serve/server.py:5531` |
| `repeat_stop_tokens` | stop on repeated end tokens; 0 opts out (#606) | REPEAT_STOP_TOKENS | `serve/server.py:5517` |
| `sampling` |  | unset | `serve/server.py:5278` |
| `slot_save_path` | directory for batch-slot saves | unset | `serve/server.py:5501` |
| `split_skip_if_fits` | -> adds `--split-skip-if-fits` | unset | `serve/server.py:2053` |
| `threads` |  | unset | `serve/server.py:1728` |
| `tokenizer` | tokenizer directory | unset | `serve/server.py:5378` |
| `tool_call_recovery` | OutputParser recovery | False | `serve/server.py:5513` |
| `trusted_origins` | Origin allow-list, no wildcard | unset | `serve/server.py:5478` |
| `vision` |  | unset | `serve/server.py:2209` |
| `vram_elastic` | -> adds `--vram-elastic` | unset | `serve/server.py:2057` |
| `vram_segment_mib` | -> adds `--vram-segment-mib` | unset | `serve/server.py:2059` |

### 1.2 The `vision` block

| key | what the code does with it | read at |
|---|---|---|
| `vision.exe` | encoder binary | `serve/server.py:1725` |
| `vision.mmproj` | the multimodal projector GGUF | `serve/server.py:1725` |
| `vision.model` | the model GGUF the encoder reads | `serve/server.py:1725` |
| `vision.gpu` | passed as `--gpu` to the encoder | `serve/server.py:1726` |
| `vision.threads` | `--threads` | `serve/server.py:1728` |
| `vision.max_tokens` | `--max-tokens` | `serve/server.py:1730` |
| `vision.min_tokens` | `--min-tokens` (mtmd's image_min_tokens, #767) | `serve/server.py:1732` |
| `vision.cuda_device` | the encoder runs on that card alone (#408) | `serve/server.py:0` |

### 1.3 The `sampling` block

Validated at start; a bad value refuses to start the server, an unknown key is named and ignored. Request fields always win.

| `sampling.temperature` | number >= 0 (0 = greedy) | `serve/server.py:5282` |
| `sampling.top_p` | 0 < x <= 1 | `serve/server.py:5286` |
| `sampling.min_p` | 0 <= x <= 1 | `serve/server.py:5290` |
| `sampling.top_k` | integer 1..64 | `serve/server.py:5294` |
| `sampling.presence_penalty` | number >= 0 | `serve/server.py:5298` |
| `sampling.frequency_penalty` | number >= 0 | `serve/server.py:5302` |
| `sampling.repetition_penalty` | number > 0 (1 = off) | `serve/server.py:5306` |
| `sampling.penalty_last_n` | non-negative integer | `serve/server.py:5310` |
| `sampling.seed` | positive integer | `serve/server.py:5314` |
| `sampling.experimental_speed_projection` | bool (default on when the engine has a vector) | `serve/server.py:5318` |

### 1.4 The `mcp` block and `mcp_servers`

| key | what the code does with it | read at |
|---|---|---|
| `mcp.timeout_s` | checked at start (seconds > 0 / positive integer); unknown keys named and ignored | `serve/mcp.py:633` |
| `mcp.max_result_chars` | checked at start (seconds > 0 / positive integer); unknown keys named and ignored | `serve/mcp.py:633` |
| `mcp.max_rounds` | checked at start (seconds > 0 / positive integer); unknown keys named and ignored | `serve/mcp.py:633` |
| `mcp.start_timeout_s` | checked at start (seconds > 0 / positive integer); unknown keys named and ignored | `serve/mcp.py:633` |
| `mcp_servers.<name>.command` | a program Strata starts, or a Streamable HTTP endpoint | `serve/mcp.py:4` |
| `mcp_servers.<name>.args` | a program Strata starts, or a Streamable HTTP endpoint | `serve/mcp.py:4` |
| `mcp_servers.<name>.env` | a program Strata starts, or a Streamable HTTP endpoint | `serve/mcp.py:4` |
| `mcp_servers.<name>.cwd` | a program Strata starts, or a Streamable HTTP endpoint | `serve/mcp.py:4` |
| `mcp_servers.<name>.url` | a program Strata starts, or a Streamable HTTP endpoint | `serve/mcp.py:4` |

### 1.5 Inert keys in your current config

In `strata-iq2_xs.json`, not read by `serve/server.py`: `exe`, `args`, `port`, `draft_vocab`.

## 2. Engine CLI flags (what goes in `args`)

Defaults are the `Options` struct values. 142 of the 161 flags the parser accepts are mentioned in `--help`; 19 are accepted but never printed there — those are the A/B arms and measurement switches.

A `—` default means the flag has no value default: the flag itself is the setting (paths, modes, names). Two
exceptions worth knowing: `--pool-affinity` defaults to `all` (not 0), `--coupled-draft` defaults from
`STRATA_SPEC_COUPLED` rather than a constant, and `--tokens` is required unless `--tokens-file` is given.


### CPU pool (5)

| flag | value | default | in --help | what it does | env twin |
|---|---|---|---|---|---|
| `--host-core` | WHERE | `—` | yes | The host thread's core: first (the default: the first physical core, as always) or last (the last physical core, the workers on the others).  Windows  | STRATA_HOST_CORE |
| `--no-pool` |  | `false` | yes | skip the CPU expert pool (the GPU-only floor) |  |
| `--pool-affinity` |  | `—` | yes | MODE Worker CPU affinity: all (default: one worker per physical core, as always), auto (hybrid CPUs: P-cores first, then their SMT siblings, then E-co |  |
| `--pool-tasks` | N | `0` | yes | Batched CPU expert tasks per GU/Down phase (0..4096). Default 0 = 3 per participating thread; positive counts are capped by row count. |  |
| `--pool-workers` | N | `0` | yes | R2.2: CPU expert pool worker count.  Default 0 = every physical core except the one the host loop spins on (with --pool-affinity auto or p-cores on a  |  |

### KV & memory (21)

| flag | value | default | in --help | what it does | env twin |
|---|---|---|---|---|---|
| `--expert-cache` | N | `0` | yes | R4: keep N expert blobs resident in VRAM and compute their rows on the GPU via `moe_hit_grouped_s2`.  DEFAULT 0.  Measured at 4096 slots with --expert |  |
| `--expert-cache-cpu-order` |  | `false` | yes | experimental GPU expert reduction matching CPU order |  |
| `--expert-cache-per-layer` |  | `false` | yes | R4.2g: give each layer its OWN slots instead of letting the first position take all of them.  The default policy fills in arrival order from one share |  |
| `--expert-cache-remote-placement` |  | `"stripe"` | yes | stripe\|layer  distribute expert ranks or whole layers across CUDA1..3 (default: stripe) |  |
| `--kv` |  | `"fp16"` | yes | fp16\|int8       KV storage (plan v0.3 P7): int8 codes + fp16 scale per 64 values, half the VRAM; default fp16 until gate G-C accepts int8 slightly low |  |
| `--kv-grow` |  | `false` | yes | the K/V takes VRAM only for the cells the requests reach and the expert cache holds the rest, giving slots back as the context grows (one GPU, with -- | STRATA_KV_GROW |
| `--kv-resident` | N | `0` | yes | KV streaming: keep N cells of each QSA layer in VRAM (min 20480) and the whole K/V in pinned RAM; the freed VRAM goes to expert slots. 0 (default): al |  |
| `--mmap-experts` |  | `false` | yes | R2.1: opt OUT of the resident expert arena, back to MapViewOfFile. The A/B arm: the mmap's rate depends on the OS page cache holding 34 GB, and measur |  |
| `--no-kv-grow` |  | `—` | no |  |  |
| `--peer-adapt-swaps` | N | `-1` | yes | peer cache swaps per adaptation step (default: --adapt-swaps) |  |
| `--peer-device` | N | `-1` | yes | a second GPU as an adaptive expert-cache tier (rows over P2P; it also computes its experts' prompt rows).  Not with --layer-split or --expert-cache-de |  |
| `--peer-prefill-rows` | N | `-1` | yes | prompt rows per layer the peer computes (default half of chunk x top-k; 0 = the prompt path stays on the primary) |  |
| `--peer-reserve-mib` | N | `600` | yes | VRAM the peer tier leaves free on its card (default 600) |  |
| `--peer-slots` | N | `0` | yes | expert slots on the peer (default: what fits) |  |
| `--resident-budget-gib` |  | `—` | no |  |  |
| `--resident-cpu-experts` |  | `false` | yes | with mmap and a static profile, keep the experts the GPU cache does not hold resident in ordinary RAM (and the prompt path's lend region as far as RAM |  |
| `--resident-experts` |  | `—` | yes | the low-RAM PC's resident mode (setup): --mmap-experts --resident-cpu-experts with the copy page-locked when possible, 4 GiB headroom, plain mmap if i |  |
| `--vram-elastic` |  | `false` | yes | --serve (#533, opt-in, NVIDIA): the expert cache in segments (--vram-segment-mib, default 512), so the command `VRAM <reserve_mib>` (the server's POST |  |
| `--vram-reserve-later-mib` |  | `-1` | no |  |  |
| `--vram-reserve-mib` |  | `700` | no |  |  |
| `--vram-segment-mib` |  | `512` | yes | --vram-elastic       --serve (#533, opt-in, NVIDIA): the expert cache in segments (--vram-segment-mib, |  |

### adapt (cache tier) (4)

| flag | value | default | in --help | what it does | env twin |
|---|---|---|---|---|---|
| `--adapt-async` | 1 | `0` | yes | --serve with the resident RAM mode (opt-in): the adaptive tier's swaps advance between verify windows instead of a window waiting for a whole round.   |  |
| `--adapt-decay` |  | `0.7f` | no |  |  |
| `--adapt-every` |  | `4` | yes | arithmetic write the same file (use with --spec-follow, --adapt-every 0) |  |
| `--adapt-swaps` |  | `96` | yes | --peer-adapt-swaps N  peer cache swaps per adaptation step (default: --adapt-swaps) |  |

### context & rope (10)

| flag | value | default | in --help | what it does | env twin |
|---|---|---|---|---|---|
| `--max-context` | N | `4096` | yes | KV/state capacity (default 4096) |  |
| `--rope-freq-base` | N | `0` | yes | the raw ggml knobs: the frequency base (0 = the model's 1e7) and |  |
| `--rope-freq-scale` | F | `0` | yes | the angle shrink (0 = 1/--rope-scale) |  |
| `--rope-scale` | F | `0` | yes | the extension factor for linear/yarn (default: the model file's factor, else 1 = off) |  |
| `--rope-scaling` | T | `—` | yes | extend the context past the trained one: none, linear (position interpolation) or yarn - llama.cpp's types and names. Default: the model file's rope k |  |
| `--yarn-attn-factor` |  | `1.0` | yes | --yarn-ext-factor F --yarn-attn-factor F --yarn-beta-fast F --yarn-beta-slow F |  |
| `--yarn-beta-fast` |  | `32.0` | yes | --yarn-ext-factor F --yarn-attn-factor F --yarn-beta-fast F --yarn-beta-slow F |  |
| `--yarn-beta-slow` |  | `1.0` | yes | --yarn-ext-factor F --yarn-attn-factor F --yarn-beta-fast F --yarn-beta-slow F |  |
| `--yarn-ext-factor` |  | `-1.0` | yes | F --yarn-attn-factor F --yarn-beta-fast F --yarn-beta-slow F YaRN's knobs; defaults: -1 (auto: 1 for yarn), 1, 32, 1 |  |
| `--yarn-orig-ctx` | N | `0` | yes | the trained context the correction targets (0 = 262144) |  |

### file I/O (8)

| flag | value | default | in --help | what it does | env twin |
|---|---|---|---|---|---|
| `--no-ple-prefetch` |  | `false` | yes | A/B arm: read the PLE table's sixteen rows one at a time, instead of issuing them in one PrefetchVirtualMemory call. |  |
| `--pcie-frac` |  | `-1.0` | no |  |  |
| `--pcie-mode` |  | `"auto"` | no |  |  |
| `--ple-delay-us` | U | `0` | yes | fault injection: each row read completes no earlier than U us |  |
| `--ple-inflight` | N | `256` | yes | outstanding SSD reads (default 256) |  |
| `--ple-io` |  | `"direct"` | yes | direct\|mmap\|ram  n-gram table reads (plan v0.3 P2). direct (default): unbuffered SSD reads, the table never enters RAM or the file cache; mmap: A/B ar |  |
| `--ple-row-cache` | N | `1 << 20` | yes | bounded cache of fetched rows, 90 B each (default 1048576; 0 = off) |  |
| `--ple-sync-submit` |  | `false` | yes | A/B arm: submit table reads on the token thread (default: an I/O thread) |  |

### inputs & paths (31)

| flag | value | default | in --help | what it does | env twin |
|---|---|---|---|---|---|
| `--batch-mtp` |  | `false` | yes | --batch (opt-in, one GPU, needs --mtp and --spec): each slot also verifies one MTP proposal per window (STRATA_BATCH_MTP=1 does the same); needs VRAM  | STRATA_BATCH_MTP |
| `--embd-gguf` | PATH | `—` | yes | the token embedding from this GGUF instead of --native's (tools/embd_bf16_pack.py: BF16 as the checkpoint ships it; mapped host memory, no VRAM) |  |
| `--expert-profile` | P | `—` | yes | R4.2e: pre-load the VRAM tier from a `profile.bin` (see tools/make_profile.py) instead of admitting on first use. |  |
| `--expert-profile-save` | P | `—` | yes | --serve, #477: save what the adaptive tier learned (the experts in VRAM, then the routing counted since the start) as a profile at P, on QUIT and ever |  |
| `--expert-profile-save-every` |  | `—` | yes | MIN minutes (default 10; |  |
| `--gr-native-mmvf` |  | `false` | yes | experimental pinned GR norm/projections; implies FP32 activations |  |
| `--mtp` |  | `—` | yes | --batch-mtp          --batch (opt-in, one GPU, needs --mtp and --spec): each slot also verifies one MTP |  |
| `--mtp-draft-vocab` | FILE | `—` | yes | opt-in: the draft head's token subset (default <mtp>/draft_vocab.bin) |  |
| `--mtp-hnorm` |  | `—` | yes | pooled\|stream  the draft layer's hidden-input norm: one RMS over all four streams (default) or one per stream (llama.cpp's MTP graph) |  |
| `--mtp-max-t` | M | `0` | yes | cap the MTP's windows at M tokens (0 = --spec; longer ones come from suffixes) |  |
| `--mtp-q4` |  | `—` | yes | all\|proj\|head  opt-in: the draft layer's projections and/or draft head as 4-bit copies |  |
| `--mtp-window` |  | `32768` | no |  |  |
| `--native` | SHARD1 | `—` | yes | every full-context native path at once (plan v0.3 P1): stream-token, GR MMVF, BF16, head, dense + PLE key, MoE combine, GDN, router, QSA, indexer, RoP |  |
| `--native-bf16` |  | `false` | yes | experimental CUDA-oracle SSM/router/indexer BF16 projections |  |
| `--native-bf16-extra` |  | `false` | yes | experimental CUDA-oracle PLE/shared gate BF16 projections |  |
| `--native-dense-gguf` |  | `—` | yes | PATH native GDN/QSA/shared projections; repeat for each source model shard |  |
| `--native-flash-attn-short` |  | `false` | yes | diagnostic pinned vector attention; --max-context <=256 |  |
| `--native-gdn` |  | `false` | yes | experimental pinned CUDA GDN norms/gates/recurrence |  |
| `--native-head-gguf` | PATH | `—` | yes | native Q5_K head from model shard 1; requires --stream-token |  |
| `--native-moe-combine` |  | `false` | yes | experimental pinned CUDA routed/shared combination |  |
| `--native-ple-key` |  | `false` | yes | experimental native PLE key; requires --native-dense-gguf |  |
| `--native-ple-postops` |  | `false` | yes | experimental pinned PLE postprojection arithmetic |  |
| `--native-qsa` |  | `false` | yes | experimental pinned QSA normalization and output gate |  |
| `--native-qsa-indexer` |  | `false` | yes | experimental pinned indexer key cache and pooling |  |
| `--native-rope` |  | `false` | yes | experimental pinned text-only CUDA rotary arithmetic |  |
| `--native-router` |  | `false` | yes | experimental pinned CUDA 512-expert top-10 routing |  |
| `--pack` | DIR | `"pack/full"` | yes | the pack directory (default pack/full) |  |
| `--ple-gguf` | PATH | `—` | yes | required PLE table (original second GGUF shard); with --native, the model's shard that holds per_layer_token_embd.weight when not given which changes  | STRATA_PLE_GGUF |
| `--shared-expert-arena` | FILE | `—` | yes | Linux: back the resident arena with one MAP_SHARED file. Put this file on /dev/shm, not ordinary SSD storage. A small header binds an existing backing |  |
| `--tokens` | LIST | `—` | yes | the prompt as comma-separated token IDS (required) |  |
| `--tokens-file` | PATH | `—` | yes | pretokenized prompt, commas or whitespace (alternative to --tokens) |  |

### kernel experiments (A/B) (14)

| flag | value | default | in --help | what it does | env twin |
|---|---|---|---|---|---|
| `--check-logits` |  | `false` | yes | copy and check all logits in the stream-token path |  |
| `--cpu-oracle-q8-0` |  | `false` | yes | experimental pinned CPU expert quantization and dot reduction |  |
| `--gr-fp32-activations` |  | `false` | yes | experimental CUDA-oracle GR activation precision |  |
| `--keep-canonical` |  | `false` | yes | A/B: also load canonical copies of natively served tensors (more VRAM) |  |
| `--no-fast-attn` |  | `false` | no |  |  |
| `--no-fast-select` |  | `false` | no |  |  |
| `--no-fused-gdn` |  | `false` | no |  |  |
| `--no-fused-gr` |  | `false` | yes | A/B: the six-kernel hyper-connection read and a separate write (native) |  |
| `--no-hit-poke` |  | `false` | yes | R4.2d's A/B arm.  The hit path pokes the driver once right after its launch so the GPU starts while the CPU pool runs; without it the work waits for t |  |
| `--no-publish-kernel` |  | `false` | no |  |  |
| `--no-split-rows` |  | `false` | no |  |  |
| `--no-token-graph` |  | `false` | yes | A/B: two graphs per layer (the host launches each) instead of one per token |  |
| `--shared-late` |  | `false` | yes | A/B: shared expert after the CPU pool (default: overlapped with it) |  |
| `--stream-token` |  | `false` | yes | enqueue token work on the session stream (experimental) |  |

### measurement / dumps (12)

| flag | value | default | in --help | what it does | env twin |
|---|---|---|---|---|---|
| `--dump-final-r` |  | `—` | no |  |  |
| `--dump-halves` | PATH | `—` | yes | write both halves' block_out and inject per layer: the half bisection |  |
| `--dump-layers` | PATH | `—` | yes | write R after EVERY layer, per position: the C1 bisection ladder |  |
| `--dump-logits` | PATH | `—` | yes | write one line of raw logits per position |  |
| `--dump-mixed` | PATH | `—` | yes | write the post-attention residual (n_embd, f32) |  |
| `--dump-residual` |  | `—` | yes | PATH write the final R (hc x n_embd, f32) for head bisection |  |
| `--dump-routing` | PATH | `—` | yes | write the routed expert ids and weights per layer per position (P0.S8) |  |
| `--graph-only` |  | `false` | yes | MEASURE: replay the 48 `pre` graphs only.  OMITS the 48 `post` graphs and the LM head, so it is NOT the GPU floor (R0.3, Memory/ERRORS.md A4) |  |
| `--no-capture` |  | `false` | yes | run the layers directly instead of replaying graphs |  |
| `--stage-timing` |  | `false` | yes | per-stage KERNEL-COUNT shares.  NOT a time profile: an uncaptured event interval includes host gaps, so run with --gpu-only-full first |  |
| `--stats` |  | `false` | yes | print the per-stage breakdown |  |
| `--sync-every-layer` |  | `false` | yes | debug: synchronise after every layer |  |

### multi-GPU (7)

| flag | value | default | in --help | what it does | env twin |
|---|---|---|---|---|---|
| `--gpu` | LIST | `—` | yes | run on these GPUs, comma-separated nvidia-smi/PCI indices (default: every visible one); sets CUDA_VISIBLE_DEVICES/CUDA_DEVICE_ORDER inside the engine, |  |
| `--gpu-only-full` |  | `false` | yes | MEASURE: replay pre+post for all 48 layers plus the LM head, no pool. THE TRUE PER-TOKEN GPU FLOOR.  Quote this one, not --graph-only. |  |
| `--gpu-stages` |  | `false` | yes | R0.9: capture the layer as three graphs (mixer / ffn+router / post) and time them from OUTSIDE the capture.  The per-stage table on the real graph tha |  |
| `--layer-split` |  | `—` | yes | or |  |
| `--pipeline-windows` |  | `0` | yes | N --serve with a layer split on two GPUs (opt-in): one conversation's verify windows with the GPUs overlapped - 1 = the prompt's short reads, 2 = deco |  |
| `--split-device` |  | `—` | no |  |  |
| `--trim-stage-weights` |  | `false` | yes | an explicit --layer-split: each GPU loads only its own layers' dense weights |  |

### other (11)

| flag | value | default | in --help | what it does | env twin |
|---|---|---|---|---|---|
| `--control-vector` |  | `—` | yes | FILE = scale 1).  --serve: requests switch it (cvec=0\|1) |  |
| `--control-vector-layer-range` | A B | `—` | yes | the layers it follows (inclusive; default 1 .. the last) |  |
| `--control-vector-scaled` |  | `—` | yes | FILE:SCALE[,...]  a control vector GGUF on the residual stream (llama.cpp's format; --control-vector FILE = scale 1).  --serve: requests switch it (cv |  |
| `--cvec-dir` |  | `—` | yes | per-layer\|single:L  each layer's own direction (default) or layer L's everywhere (project) |  |
| `--cvec-mode` |  | `1` | yes | add\|project  h += s v (default) or h -= s (h.v) v with v unit |  |
| `--logits-stride` | N | `1` | yes | store every Nth row plus final input (default 1); N>1 requires --max-new 1 |  |
| `--max-new` | N | `16` | yes | tokens to generate (default 16) |  |
| `--no-host-worker` |  | `false` | yes | R2.2: the A/B arm.  By default the HOST THREAD joins the drain, so the pool is six threads on six cores instead of five plus an idle core; this flag r |  |
| `--no-ple` |  | `false` | yes | explicit diagnostic ablation of the PLE layer |  |
| `--remote-expert-opt` |  | `false` | yes | enable remote-expert decode optimizations (serve mode) |  |
| `--split-skip-if-fits` |  | `false` | no |  |  |

### prompt / serve (18)

| flag | value | default | in --help | what it does | env twin |
|---|---|---|---|---|---|
| `--batch` |  | `0` | yes | N / --slots N  --serve (opt-in): up to N requests decode together in batch slots (2..8 normally; --batch-mtp waves more through eight-row windows), ea |  |
| `--batch-groups` | G | `1` | yes | --batch with a layer split: the slots in G groups pipelined through the GPUs |  |
| `--conversation-cache-mib` | N | `0` | yes | --serve: RAM budget for parked conversations (default 0 = off) |  |
| `--conversation-cache-min-free-mib` | N | `2560` | yes | --serve: physical RAM floor when parking or restoring a session file (default 2560) |  |
| `--no-prefill-borrow` |  | `false` | no |  |  |
| `--prefill` | CHUNK | `0` | yes | batched prompt processing in chunks of CHUNK tokens (needs --native); auto = the largest chunk up to 8192 whose buffers the expert cache can lend; aut |  |
| `--prefill-until` |  | `0` | no |  |  |
| `--prompt-cache` | N | `6` | yes | --serve: keep N conversation checkpoints between requests (default 6, ~118 MB of RAM each; 0 = read every prompt from the start) |  |
| `--prompt-cache-every` | N | `16384` | yes | --serve: also checkpoint every N fresh prompt tokens (default 16384, 0 = off) |  |
| `--prompt-cache-root` |  | `2048` | no |  |  |
| `--prompt-cache-tail` |  | `false` | yes | --serve, single GPU: one extra checkpoint near the prompt's end, at an existing chunk boundary (default off; requires --prompt-cache and --prompt-cach |  |
| `--serve` |  | `false` | yes | --adapt-async 1      --serve with the resident RAM mode (opt-in): the adaptive tier's swaps |  |
| `--session-min-free-mib` | N | `4096` | yes | --serve: disk space a SAVE must leave free (default 4096; 0 = no check) |  |
| `--short-read` | N | `64` | yes | --serve: read at most N fresh text tokens through the decode windows instead of the batched prompt path (default 64, 0 = off) |  |
| `--slots` |  | `0` | yes | --batch N / --slots N  --serve (opt-in): up to N requests decode together in batch slots (2..8 |  |
| `--tail-role-token` |  | `-1` | yes | ID --serve: a turn of this role right before the last turn is left out of the conversation checkpoint (a trailing effort turn; default -1 = off) |  |
| `--turn-token` | ID | `248045` | yes | --serve: the token that opens a chat turn (default 248045, <\|im_start\|>) |  |
| `--vision` |  | `false` | yes | --serve takes images too (GENI requests; embeddings from strata-vision) |  |

### sampling (7)

| flag | value | default | in --help | what it does | env twin |
|---|---|---|---|---|---|
| `--eos-ids` |  | `{248044, 248046}` | no |  |  |
| `--greedy` |  | `true` | yes | argmax (the default) |  |
| `--seed` | S | `0` | yes | enable sampling with this Philox seed |  |
| `--stop-eos` |  | `false` | no |  |  |
| `--temperature` |  | `1.0f` | yes | --top-k N --top-p F --temperature F |  |
| `--top-k` |  | `20` | yes | N --top-p F --temperature F |  |
| `--top-p` |  | `0.95f` | yes | --top-k N --top-p F --temperature F |  |

### speculation (13)

| flag | value | default | in --help | what it does | env twin |
|---|---|---|---|---|---|
| `--coupled-draft` |  | `strata::core::coupled_draft_env()` | yes | enable coupled draft sampling for MTP drafter under sampling (STRATA_SPEC_COUPLED) |  |
| `--lookup-chain` | K | `0` | yes | opt-in: after the MTP's drafts, add up to K prompt-lookup drafts that continue them (the window grows to at most 8; default 0 = off) |  |
| `--lookup-chain-min` | M | `3` | yes | the shortest context match --lookup-chain extends on (default 3) |  |
| `--no-coupled-draft` |  | `—` | yes | disable coupled draft sampling (propose argmax drafts) |  |
| `--no-spec-split` |  | `—` | no |  |  |
| `--spec` | N | `0` | yes | the MTP drafter's verify window: how many tokens it proposes per check (setup writes 4; --suffix-draft lets it grow by 2, up to 8, where a repeat is l |  |
| `--spec-corrupt` |  | `0` | no |  |  |
| `--spec-follow` | PATH | `—` | yes | benchmarks: emit this continuation (token ids) instead of the argmax and accept the drafts that match it, so speculation settings compare on the same  |  |
| `--spec-min-p` | P | `0.0` | yes | how sure the draft layer must be to extend a verify window by another guess (setup writes 0.5; --calibrate measures it on this PC, see docs/DETAILS.md |  |
| `--spec-oracle` |  | `—` | no |  |  |
| `--spec-split` |  | `false` | no |  |  |
| `--suffix-draft` | N | `3` | yes | prompt lookup: draft from an earlier repeat of the last N+ tokens of context when it pays (default 3; 0 = MTP only) |  |
| `--window-hashes` |  | `—` | yes | PATH per verify window, a line with its index, position, size, a 64-bit hash of its final residual rows and its argmaxes: two builds that do the same  |  |

## 3. Environment variables (what goes in `env`)

`default` is the polarity the code implements, read off the `getenv` call.


### _paths.py (1)

| variable | default / polarity | note | in a doc | read at |
|---|---|---|---|---|
| `STRATA_GGUF_PY` | presence flag | `iq_pack.py` needs NumPy and the `gguf-py` module from the pinned llama.cpp dependency (`STRATA_GGUF_PY` can point to that directory). It writes a rou | yes | `tools/_paths.py:16` |

### canonical_xcheck.py (1)

| variable | default / polarity | note | in a doc | read at |
|---|---|---|---|---|
| `STRATA_SHARD1` | presence flag |  | no | `tools/canonical_xcheck.py:46` |

### core (67)

| variable | default / polarity | note | in a doc | read at |
|---|---|---|---|---|
| `STRATA_ARENA_LOCK` | presence flag |  | no | `src/core/pinned.cu:414` |
| `STRATA_ARENA_MMAP` | opt-in (needs 1) | A mapped arena for small RAM (Linux, opt-in, 0.1.39, PR #640): `STRATA_ARENA_MMAP=1` maps a native pack's expert | yes | `src/core/expert_source.cpp:3797` |
| `STRATA_ARENA_PIN_GIB` | presence flag | 8 GiB to leave room for the contexts and MTP on CUDA0 (`STRATA_ARENA_PIN_GIB` overrides it; on Linux the whole | yes | `src/core/pinned.cu:300` |
| `STRATA_COMMIT_SYNC` | presence flag |  | no | `src/core/verify.cpp:2216` |
| `STRATA_DBG_NAN` | opt-in (presence) | debug: the state the prompt leaves for the token path | yes | `src/core/verify.cpp:2065` |
| `STRATA_DEC_BATCH` | integer; on by default (0 turns off) | - Environment: `STRATA_DEC_BATCH=1`, `STRATA_PF_FUSED=1`. | yes | `src/core/expert_source.cpp:3169` |
| `STRATA_DEFERRED_REGISTER` | presence flag |  | no | `src/core/expert_source.cpp:3879` |
| `STRATA_DF_BRANCH` | presence flag |  | no | `src/core/verify.cpp:584` |
| `STRATA_DF_PLE` | presence flag |  | no | `src/core/verify.cpp:840` |
| `STRATA_DF_QB_Q4` | presence flag |  | no | `src/core/verify.cpp:1042` |
| `STRATA_EXCHANGE_ROTATE` | presence flag | - `STRATA_EXCHANGE_ROTATE=1` (opt-in): an adaptive swap hands buffer ownership over instead of copying the evicted | yes | `src/core/expert_source.cpp:2670` |
| `STRATA_FETCH_PVM` | presence flag |  | no | `src/core/expert_source.cpp:1386` |
| `STRATA_FILE_RELEASE` | presence flag | Releasing mapped expert pages on Windows (opt-in): `STRATA_FILE_RELEASE=1` lets `FileExpertSource` trim the | yes | `src/core/expert_source.cpp:2049` |
| `STRATA_FUSE_HEAD_GR` | presence flag |  | no | `src/core/mtp.cpp:903` |
| `STRATA_GFX1151_DEFAULTS` | presence flag | (`STRATA_GFX1151_DEFAULTS=0` turns the whole table off, and the start-up line names what was set). Every one of them gave | yes | `src/core/arch_defaults.cpp:15` |
| `STRATA_HC_Q8` | opt-in (needs 1) | export STRATA_HC_Q8=1           # the hyper-connection read from the GGUF's own Q8_0 projections | yes | `src/core/native_dense.cpp:42` |
| `STRATA_HC_Q8_INJECT` | opt-in (needs 1) |  | no | `src/core/native_dense.cpp:327` |
| `STRATA_HEAD_MIX_MULTI` | presence flag |  | no | `src/core/mtp.cpp:910` |
| `STRATA_IO_PF_AHEAD` | integer | expert in a buffer and makes the layer wait for them; `STRATA_IO_PF_AHEAD=0` keeps only the demand reads. The per-request | yes | `src/core/expert_source.cpp:580` |
| `STRATA_IO_PF_STAGE` | presence flag | same (greedy IQ3_XXS and Q2_0 hashes identical, prefetch off vs on). `STRATA_IO_PF_STAGE=1` instead stages every uncached | yes | `src/core/expert_source.cpp:582` |
| `STRATA_KV_MAIN_OFF` | opt-in (presence) |  | no | `src/core/layer.cpp:642` |
| `STRATA_KV_RING_OFF` | opt-in (presence) |  | no | `src/core/layer.cpp:641` |
| `STRATA_LFUSE` | opt-in (needs 1) | \| `STRATA_EXPERT_V2`, `STRATA_TSUM`, `STRATA_LFUSE` \| the grouped decode experts (IQ3_S / IQ4_NL), single-butterfly warp sums, fewer launches around t | yes | `src/core/verify.cpp:66` |
| `STRATA_LFUSE_GATE` | on by default (0 turns off) |  | no | `src/core/verify.cpp:67` |
| `STRATA_LFUSE_PAIR` | on by default (0 turns off) |  | no | `src/core/verify.cpp:68` |
| `STRATA_LOGPOS_TOPK` | presence flag | The method of `docs/UNSLOTH_Q4.md`: `STRATA_LOGPOS=<file> STRATA_LOGPOS_TOPK=256` on a serve engine (`--short-read 640 --adapt-every 100000`, greedy, | yes | `src/core/verify.cpp:2198` |
| `STRATA_MMVQ_IL` | on by default (0 turns off) |  | no | `src/core/verify.cpp:73` |
| `STRATA_MTP_CATCHUP_ALL` | presence flag |  | no | `src/core/mtp.cpp:62` |
| `STRATA_MTP_FULL_HEAD` | opt-in (needs 1) |  | no | `src/core/mtp.cpp:508` |
| `STRATA_MTP_PREFILL_SYNC` | integer |  | no | `src/core/mtp.cpp:1217` |
| `STRATA_MTP_PRIORITY` | integer; on by default (0 turns off) |  | no | `src/core/mtp.cpp:471` |
| `STRATA_MTP_SHARED_BRANCH` | presence flag |  | no | `src/core/mtp.cpp:920` |
| `STRATA_MTP_TOP2` | opt-in (needs 1) |  | no | `src/core/mtp.cpp:514` |
| `STRATA_NO_ARENA_THP` | opt-in (presence); string compare | for `MADV_HUGEPAGE` on top (a fragmented machine spent minutes compacting memory, #771); `STRATA_NO_ARENA_THP=1` skips | yes | `src/core/pinned.cu:256` |
| `STRATA_NO_BATCH_KV_STEP` | presence flag |  | no | `src/core/mtp.cpp:785` |
| `STRATA_NO_LARGEPAGES` | opt-in (presence) |  | no | `src/core/pinned.cu:89` |
| `STRATA_NO_MULTI_GR` | presence flag |  | no | `src/core/mtp.cpp:976` |
| `STRATA_ONE_TOKEN_COMMIT` | presence flag |  | no | `src/core/verify.cpp:144` |
| `STRATA_PARTIAL_PIN` | presence flag | \| `STRATA_PARTIAL_PIN=1` \| Registers the hottest part of the RAM budget (up to `STRATA_PARTIAL_PIN_GIB`, default 24) with the GPU driver, so the GPU c | yes | `src/core/expert_source.cpp:2381` |
| `STRATA_PARTIAL_PIN_GIB` | presence flag | \| `STRATA_PARTIAL_PIN=1` \| Registers the hottest part of the RAM budget (up to `STRATA_PARTIAL_PIN_GIB`, default 24) with the GPU driver, so the GPU c | yes | `src/core/expert_source.cpp:2387` |
| `STRATA_PEER_DIRECT` | integer; on by default (0 turns off) |  | no | `src/core/peer_experts.cpp:188` |
| `STRATA_PIN_GUARD` | presence flag | are the same, only the copies of the pageable part to the GPU go through the CPU. `STRATA_PIN_GUARD=0` turns this off, | yes | `src/core/expert_source.cpp:2300` |
| `STRATA_PIN_RESERVE_GIB` | presence flag | `STRATA_PIN_RESERVE_GIB=N` sets the RAM that must stay free (default: `STRATA_RESIDENT_HEADROOM_GIB`, 4 GiB). | yes | `src/core/expert_source.cpp:2293` |
| `STRATA_PLE_BATCH` | opt-in (needs 1) | \| `STRATA_GDN_SPLIT`, `STRATA_QFUSE`, `STRATA_PLE_BATCH` \| the GDN step over four blocks per head, activation images written by their producers, the P | yes | `src/core/verify.cpp:796` |
| `STRATA_POOL_TRACE` | opt-in (presence) |  | no | `src/core/expert_source.cpp:3033` |
| `STRATA_QFUSE` | integer; opt-in (needs 1); opt-in (presence) | \| `STRATA_GDN_SPLIT`, `STRATA_QFUSE`, `STRATA_PLE_BATCH` \| the GDN step over four blocks per head, activation images written by their producers, the P | yes | `src/core/arch_defaults_test.cpp:52` |
| `STRATA_REMOTE_SPIN` | presence flag |  | no | `src/core/remote_experts.cpp:78` |
| `STRATA_REMOTE_ZEROCOPY` | presence flag |  | no | `src/core/remote_experts.cpp:209` |
| `STRATA_ROUTE_PER_TOKEN` | presence flag | \| verify-window routing (256-expert router) \| the window's tokens in one multi-column BF16 projection + one top-k, ~3 ms of a ~55 ms window \| `STRATA_ | yes | `src/core/layer.cpp:399` |
| `STRATA_ROUTE_PROJ_PER_TOKEN` | presence flag |  | no | `src/core/layer.cpp:411` |
| `STRATA_SESSION_BUFFERED` | presence flag | `STRATA_SESSION_BUFFERED=1`); on Windows with buffered I/O. The engine has been run on Linux/CUDA only. An earlier | yes | `src/core/conversation_file.cpp:340` |
| `STRATA_SESSION_GOLDEN_PRINT` | presence flag |  | no | `src/core/conversation_file_test.cpp:179` |
| `STRATA_SH_FORK_LATE` | presence flag |  | no | `src/core/verify.cpp:1242` |
| `STRATA_SH_STREAM` | on by default (0 turns off) | \| [2026-10-04-community-rx-6800-windows](2026-10-04-community-rx-6800-windows/) \| RX 6800, Windows \| Flash-Next (see README) \| 326 (7.9K) / 311 (30.3K | yes | `src/core/verify.cpp:112` |
| `STRATA_TEST_VERIFY_STALL` | presence flag |  | no | `src/core/verify.cpp:234` |
| `STRATA_TG_FLUSH_US` | presence flag |  | no | `src/core/session.cpp:922` |
| `STRATA_TSUM` | opt-in (needs 1); opt-in (presence) | \| `STRATA_EXPERT_V2`, `STRATA_TSUM`, `STRATA_LFUSE` \| the grouped decode experts (IQ3_S / IQ4_NL), single-butterfly warp sums, fewer launches around t | yes | `src/core/arch_defaults_test.cpp:51` |
| `STRATA_UMA_HEADROOM_GIB` | presence flag | the memory plan use) counts what Linux can give back (`MemAvailable` less 6 GiB for the system, `STRATA_UMA_HEADROOM_GIB` | yes | `src/core/expert_cache.cpp:55` |
| `STRATA_UNBUFFERED_LOAD` | opt-in (presence) | \| #1325 \| File tier (Windows): each expert from experts.bin and a mirror on a second drive (+8.7%) \| For us the second drive is a mechanical HDD, so a | yes | `src/core/expert_source.cpp:428` |
| `STRATA_VERIFY_ALL_RESIDENT` | presence flag | - Batch runs: no vision, `--vram-reserve-mib 700`, `--batch 2` or `--batch 4`, each with `--batch-groups 2 --trim-stage-weights`. No `STRATA_*` enviro | yes | `src/core/verify.cpp:602` |
| `STRATA_VERIFY_ARENA` | opt-in (presence) | tests: the loaded arena's checksum, any loader | no | `src/core/expert_source.cpp:3943` |
| `STRATA_VERIFY_DEBUG` | opt-in (presence) | SYCL port: the per-layer residual ladder (token 0) | yes | `src/core/verify.cpp:65` |
| `STRATA_VERIFY_DEVICE_PLAN` | integer; opt-in (presence) | `ZES_ENABLE_SYSMAN=1` and `STRATA_VERIFY_DEVICE_PLAN=1`, then run `build-sycl-aot/strata` or `sycl/serve/server_intel.py` with an `exe` that does this | yes | `src/core/expert_source.cpp:3172` |
| `STRATA_VERIFY_NODES` | opt-in (presence) | what the window graph holds | no | `src/core/verify.cpp:1661` |
| `STRATA_VERIFY_PROFILE` | opt-in (presence) | `STRATA_VERIFY_PROFILE=1` for the GPU's side) in the environment. After each request the engine log then has one | yes | `src/core/verify.cpp:546` |
| `STRATA_VERIFY_QDEDUP` | integer; opt-in (presence) |  | no | `src/core/verify.cpp:69` |
| `STRATA_WDDM_BUDGET` | presence flag | card's M MiB ...`; `STRATA_WDDM_BUDGET=0` turns it off). And the PCIe probe times its copies on the host clock | yes | `src/core/device.cu:186` |

### frontend.py (1)

| variable | default / polarity | note | in a doc | read at |
|---|---|---|---|---|
| `STRATA_KEEP_EMPTY_TURNS` | opt-in (needs 1); string compare | `STRATA_KEEP_EMPTY_TURNS=1` and `STRATA_TOPK_STREAM=0` in [TROUBLESHOOTING.md](TROUBLESHOOTING.md). | yes | `serve/frontend.py:60` |

### hip (2)

| variable | default / polarity | note | in a doc | read at |
|---|---|---|---|---|
| `STRATA_TEST_VERBOSE` | opt-in (presence) |  | no | `tests/hip/prefill_wmma_gemm_parity.cpp:338` |
| `STRATA_WMMA_PARITY_EXACT` | opt-in (presence) |  | no | `tests/hip/prefill_wmma_gemm_parity.cpp:237` |

### include (3)

| variable | default / polarity | note | in a doc | read at |
|---|---|---|---|---|
| `STRATA_ARENA_ALIAS_CHECK` | on by default (0 turns off) | `STRATA_ARENA_ALIAS_CHECK=0` skips it). `sycl/probe/arena_rw.cpp` and `alias_scan.cpp` do not reproduce it on their own: it | yes | `sycl/include/strata/sycl_queue.hpp:167` |
| `STRATA_CHUNKED_FILL` | presence flag |  | no | `sycl/include/strata/sycl_queue.hpp:22` |
| `STRATA_HOST_UNCACHED` | presence flag |  | no | `sycl/include/strata/sycl_queue.hpp:65` |

### kernels (67)

| variable | default / polarity | note | in a doc | read at |
|---|---|---|---|---|
| `STRATA_ARGMAX_MULTI` | presence flag | IQ3 packs about even); `STRATA_QSA_CLUSTER=0` / `STRATA_ARGMAX_MULTI=0` turn the decode kernels off. The tables | yes | `src/kernels/cuda/sampler.cu:1256` |
| `STRATA_ATTN_LANECELL` | opt-in (needs 1) | \| `STRATA_Q8_PACKED`, `STRATA_Q6_PACKED`, `STRATA_MMVF_ROWS`, `STRATA_ATTN_LANECELL` \| decode layouts and kernels (packed Q8_0 / Q6_K weights, 4-row B | yes | `src/kernels/cuda/qsa_decode_attn.cu:548` |
| `STRATA_ATTN_PRE75` | presence flag | \| QSA attention for decode and verify windows (and prompts with `STRATA_PROMPT_ATTN_OLD=1`) \| #540's kernel (fewer shuffles, bit-exact; `STRATA_ATTN_P | yes | `src/kernels/cuda/qsa_decode_attn.cu:490` |
| `STRATA_CPU_YMM` | presence flag |  | no | `src/kernels/cpu/expert.cpp:153` |
| `STRATA_DBG_GDN` | opt-in (needs 1) |  | no | `src/kernels/cuda/verify_kernels.cu:944` |
| `STRATA_DF_PDL` | integer; opt-in (presence); value; code default 1 | opt-in until the A/B says otherwise | no | `src/kernels/pdl_parity.cpp:252` |
| `STRATA_EXPERT_V2` | opt-in (needs 1) | \| `STRATA_EXPERT_V2`, `STRATA_TSUM`, `STRATA_LFUSE` \| the grouped decode experts (IQ3_S / IQ4_NL), single-butterfly warp sums, fewer launches around t | yes | `src/kernels/cuda/iq_kernels.cu:3412` |
| `STRATA_EXPERT_V2K` | opt-in (needs 1) |  | no | `src/kernels/cuda/iq_kernels.cu:3426` |
| `STRATA_EXP_MODE` | integer; value; code default 7 | \| grouped native experts \| mode 7: signs as `dp4a(g ^ m, u) - dp4a(m, u)` (no byte SIMD), grids and activations in LDS, one weight load per group; the | yes | `src/kernels/cuda/iq_kernels.cu:3378` |
| `STRATA_FORCE_AVX2` | opt-in (needs 1) |  | no | `src/kernels/cpu/expert_layout.cpp:42` |
| `STRATA_FORCE_ISA` | presence flag | (`STRATA_FORCE_ISA=avx` or `sse`): the answers were sane and passed the engine's checks, but not the same token for | yes | `src/kernels/cpu/expert_layout.cpp:28` |
| `STRATA_FUSED_SWIGLU_Q81` | presence flag |  | no | `src/kernels/cuda/shared_expert.cu:207` |
| `STRATA_GDN_COMMIT_SPLIT` | presence flag |  | no | `src/kernels/cuda/verify_kernels.cu:940` |
| `STRATA_GDN_SPLIT` | opt-in (needs 1) | \| `STRATA_GDN_SPLIT`, `STRATA_QFUSE`, `STRATA_PLE_BATCH` \| the GDN step over four blocks per head, activation images written by their producers, the P | yes | `src/kernels/cuda/verify_kernels.cu:921` |
| `STRATA_GROUPED_PAIR_MIN_HITS` | presence flag |  | no | `src/kernels/cuda/s2_expert_grouped.cu:540` |
| `STRATA_GR_DOWN_MAX4` | integer | fixes (the fused layout's buffers, the streamed walk's resident lookup), `STRATA_GR_DOWN_MAX4=1` (opt-in; neutral on | yes | `src/kernels/cuda/fused_gr.cu:845` |
| `STRATA_GR_FAST` | integer; value; code default true | \| hyper-connection read \| norm loads in flight, 8 lanes per row for `up` \| `STRATA_GR_FAST=0` \| | yes | `src/kernels/cuda/fused_gr.cu:1614` |
| `STRATA_GR_SPLIT` | opt-in (needs 1) | \| `gr_down_multi`, opt-in \| split along K (8 rows x 5 slices of 2048), ~3% per window; sums in another order than the single-token read, so off by def | yes | `src/kernels/cuda/fused_gr.cu:1727` |
| `STRATA_GR_V3` | integer; opt-in (presence) | #   env: STRATA_PREFILL_RING=96 STRATA_GR_V3=1 STRATA_SELECT_WMMA=1 (see confound) | yes | `src/kernels/gr_parity.cpp:342` |
| `STRATA_HC_SPLIT` | presence flag |  | no | `src/kernels/cuda/fused_gr.cu:926` |
| `STRATA_HIP_ROUTER_FAST` | presence flag |  | no | `src/kernels/cuda/router_top10.cu:429` |
| `STRATA_HIP_ROUTER_OLD` | opt-in (presence) | `STRATA_HIP_ROUTER_OLD=1` runs the portable kernel. | yes | `src/kernels/cuda/router_top10.cu:431` |
| `STRATA_HIP_WMMA` | presence flag | - `STRATA_HIP_WMMA=1` (opt-in, gfx12 only, int8 KV): the prompt path's QSA attention on RDNA4 matrix cores (the engine prints a one-line hint about it | yes | `src/kernels/cuda/qsa_prompt_attn.cu:1404` |
| `STRATA_IQ256_GATHER` | presence flag | \| 0.1.39s, IQ3_XXS \| `STRATA_IQ256_GATHER=1` \| 46.5 \| 38.5 \| 50.9 \| 60% \| | yes | `src/kernels/cpu/expert_layout.cpp:203` |
| `STRATA_IQ3S_MT1` | opt-in (presence) | without AVX-512, where the AVX-2 kernel gathers the IQ3_S grid, `STRATA_IQ3S_MT1=1` (opt-in) gives IQ3_S the multi-token | yes | `src/kernels/cpu/native_expert.cpp:106` |
| `STRATA_IQ_GATHER` | opt-in (presence) |  | no | `src/kernels/cpu/iq_avx512.cpp:33` |
| `STRATA_IQ_MT_MIN` | integer; value; code default 2 | Caveat: IQ models are not byte-reproducible at temperature 0 between runs unless `STRATA_IQ_MT_MIN=1` (DETAILS.md); | yes | `src/kernels/native_expert_parity.cpp:538` |
| `STRATA_IQ_PREFETCH` | presence flag | \| same + `--kv-resident 20480` + `STRATA_IQ_PREFETCH=16384` \| 33.3 \| 37.5–39.0 \| ~1.2 GB, 28 GB/s over the rows \| | yes | `src/kernels/cpu/iq_avx2.cpp:185` |
| `STRATA_IQ_STAGE_GRID` | presence flag | \| `STRATA_IQ_STAGE_GRID=0` \| 43.5 \| 34.6 \| 51.8 \| | yes | `src/kernels/cuda/iq_kernels.cu:1976` |
| `STRATA_IQ_STAGE_GRID_MMVQ` | presence flag |  | no | `src/kernels/cuda/iq_kernels.cu:1983` |
| `STRATA_KQ256` | integer; opt-in (presence) | \| `STRATA_KQ256=1` \| Multi-token AVX2 kernels for the Q4_K / Q5_1 / Q8_0 experts. Bit-exact with ggml's, but measured no faster, so off. \| | yes | `src/kernels/cpu/native_expert.cpp:131` |
| `STRATA_MMVF_ROWS` | opt-in (needs 1) | \| `STRATA_Q8_PACKED`, `STRATA_Q6_PACKED`, `STRATA_MMVF_ROWS`, `STRATA_ATTN_LANECELL` \| decode layouts and kernels (packed Q8_0 / Q6_K weights, 4-row B | yes | `src/kernels/cuda/native_bf16.cu:270` |
| `STRATA_MMVQ_WAVE` | presence flag | \| MMVQ \| one wavefront per row, 64-lane butterfly, no LDS \| `STRATA_MMVQ_WAVE=0` \| | yes | `src/kernels/mmvq_multi_parity.cpp:245` |
| `STRATA_MULTI_BLOCK_ARGMAX` | presence flag |  | no | `src/kernels/cuda/verify_kernels.cu:828` |
| `STRATA_NORM_ROPE` | presence flag | AMD: opt in until rope_parity check 6 passes there | no | `src/kernels/cuda/native_rope.cu:180` |
| `STRATA_NO_AVXVNNI` | integer; opt-in (presence) | `STRATA_NO_AVXVNNI=1` turns the AVX-VNNI forms of the i-quant, IQ4_NL and Q2_0 rows off on CPUs that have them | yes | `src/kernels/cpu/expert_layout.cpp:253` |
| `STRATA_NO_IQ256` | presence flag | `STRATA_NO_IQ256=1` (which drops that path; the IQ4_NL `down` rows have their own switch and stayed on | yes | `src/kernels/cpu/native_expert.cpp:126` |
| `STRATA_NO_IQ4NL` | presence flag |  | no | `src/kernels/cpu/native_expert.cpp:168` |
| `STRATA_NO_IQ512` | presence flag |  | no | `src/kernels/cpu/native_expert.cpp:118` |
| `STRATA_NO_MMVQ_ROWS2` | presence flag |  | no | `src/kernels/cuda/native_mmvq.cu:1277` |
| `STRATA_NO_NORM_ROPE` | presence flag |  | no | `src/kernels/cuda/native_rope.cu:177` |
| `STRATA_NO_Q8K_AVX2` | presence flag |  | no | `src/kernels/cpu/native_expert.cpp:77` |
| `STRATA_OLD_GROUPED` | presence flag |  | no | `src/kernels/cuda/s2_expert_grouped.cu:527` |
| `STRATA_PA_FAST` | opt-in (needs 1) | export STRATA_PA_FAST=1         # the prompt attention with single FP16 q and p | yes | `src/kernels/cuda/qsa_prompt_attn.cu:1431` |
| `STRATA_PF_SWITCH_MIN_T` | integer; value; code default (int64_t) 0 | intermediate), so they are opt-in and the maintainers gate them with KL against the default (`STRATA_PF_SWITCH_MIN_T=4096` keeps | yes | `src/kernels/cuda/qsa_prompt_attn.cu:1432` |
| `STRATA_PLE_GGUF` | presence flag |  | no | `src/kernels/ple_parity.cpp:257` |
| `STRATA_POOL_SPIN_US` | presence flag | a test knob; see kSpinBeforeSleep | no | `src/kernels/cpu/pool.cpp:439` |
| `STRATA_PROMPT_ATTN_Q4` | presence flag |  | no | `src/kernels/cuda/qsa_prompt_attn.cu:1498` |
| `STRATA_PROMPT_ATTN_V1` | opt-in (presence) |  | no | `src/kernels/cuda/qsa_prompt_attn.cu:1515` |
| `STRATA_Q2_BITPLANE` | presence flag | - `STRATA_Q2_BITPLANE=1`: a bit-plane row kernel for Q2_0 on CPUs with AVX2 and no AVX-512 (changes the last bits). | yes | `src/kernels/cpu/q2_avx2.cpp:147` |
| `STRATA_Q6P_GRID` | presence flag |  | no | `src/kernels/cuda/native_mmvq.cu:1776` |
| `STRATA_Q6P_SELFTEST` | opt-in (needs 1) |  | no | `src/kernels/cuda/native_mmvq.cu:1974` |
| `STRATA_Q6_PACKED` | presence flag | \| `STRATA_Q8_PACKED`, `STRATA_Q6_PACKED`, `STRATA_MMVF_ROWS`, `STRATA_ATTN_LANECELL` \| decode layouts and kernels (packed Q8_0 / Q6_K weights, 4-row B | yes | `src/kernels/cuda/native_mmvq.cu:1936` |
| `STRATA_Q8_PACKED` | presence flag | \| `STRATA_Q8_PACKED`, `STRATA_Q6_PACKED`, `STRATA_MMVF_ROWS`, `STRATA_ATTN_LANECELL` \| decode layouts and kernels (packed Q8_0 / Q6_K weights, 4-row B | yes | `src/kernels/cuda/native_mmvq.cu:1901` |
| `STRATA_QSA_CLUSTER` | presence flag | IQ3 packs about even); `STRATA_QSA_CLUSTER=0` / `STRATA_ARGMAX_MULTI=0` turn the decode kernels off. The tables | yes | `src/kernels/cuda/qsa_select.cu:1305` |
| `STRATA_QSA_EARLY_EXIT` | integer; on by default (0 turns off) |  | no | `src/kernels/cuda/qsa_select.cu:1103` |
| `STRATA_QSA_WARP` | presence flag | `STRATA_GR_DOWN_MAX4`, `STRATA_ADAPT_NOWAIT`, `STRATA_QSA_WARP`, `STRATA_STAGER_RING`, ...) plus the | yes | `src/kernels/cuda/qsa_prompt_attn.cu:1475` |
| `STRATA_ROPE_TABLE` | presence flag |  | no | `src/kernels/cuda/native_rope.cu:154` |
| `STRATA_ROUTER_BLOCK` | presence flag |  | no | `src/kernels/cuda/router_top10.cu:462` |
| `STRATA_S2_SWIGLU_Q8` | presence flag |  | no | `src/kernels/cuda/s2_expert_grouped.cu:1155` |
| `STRATA_SCORES_MULTI` | integer; on by default (0 turns off) |  | no | `src/kernels/cuda/qsa_select.cu:1100` |
| `STRATA_SELECT_SIMT` | presence flag |  | no | `src/kernels/cuda/qsa_select.cu:1159` |
| `STRATA_SELECT_WMMA` | presence flag | \| #1298 \| gfx110x fp16 (rocWMMA) qsa-select scorer arm (`STRATA_SELECT_WMMA`) \| gfx110x is our arch; we already proved gfx11 WMMA is exact and fast lo | yes | `src/kernels/cuda/qsa_select.cu:1126` |
| `STRATA_TOPK_ACTIVE_ANY` | opt-in (needs 1) |  | no | `src/kernels/cuda/qsa_select.cu:1323` |
| `STRATA_TOPK_CAPACITY_GUARD` | opt-in (presence) |  | no | `src/kernels/cuda/qsa_select.cu:1320` |
| `STRATA_TOPK_OLD` | opt-in (presence) |  | no | `src/kernels/cuda/qsa_select.cu:1299` |
| `STRATA_TOPK_STREAM` | presence flag | The prompt's top-k selection takes a wider kernel there, with the same ids. `STRATA_TOPK_STREAM=0` restores the old one. | yes | `src/kernels/cuda/qsa_select.cu:1350` |

### mcp.py (1)

| variable | default / polarity | note | in a doc | read at |
|---|---|---|---|---|
| `STRATA_DEBUG` | presence flag |  | no | `serve/mcp.py:131` |

### mtp_fetch.py (1)

| variable | default / polarity | note | in a doc | read at |
|---|---|---|---|---|
| `STRATA_MTP_REVISION` | presence flag |  | no | `tools/mtp_fetch.py:33` |

### other (12)

| variable | default / polarity | note | in a doc | read at |
|---|---|---|---|---|
| `STRATA_CUDA` | presence flag | \| `--cuda 12` (or `STRATA_CUDA=12`) \| the CUDA 12 engine for this model, on any card \| | yes | `setup.py:4577` |
| `STRATA_EXECV` | presence flag |  | no | `setup.py:4124` |
| `STRATA_EXPERIMENTAL_GFX1103` | opt-in (needs 1) |  | no | `setup.py:1647` |
| `STRATA_EXPERIMENTAL_SM60` | opt-in (needs 1) | with a 32,768-token context on the experimental CUDA 12 engine for Pascal (`-DSTRATA_EXPERIMENTAL_SM60=ON`, sm_61), once on a | yes | `setup.py:806` |
| `STRATA_ISA_FLOOR` | presence flag | What differs in that build (`STRATA_ISA_FLOOR=avx` or `none`, chosen from the CPU): | yes | `setup.py:650` |
| `STRATA_NVCC` | presence flag | - Build: local source build through setup: `CXX=g++-13 CUDAHOSTCXX=g++-13 STRATA_NVCC=/usr/bin/nvcc ./setup.sh --family qwen --model IQ2_XS --context  | yes | `setup.py:1203` |
| `STRATA_PREBUILT_URL` | presence flag |  | no | `setup.py:4421` |
| `STRATA_ROCM_INDEX` | presence flag | the same 7.x line, else of the same major. `STRATA_ROCM_VERSION` / `STRATA_ROCM_INDEX` override them; the gfx1030 | yes | `setup.py:1668` |
| `STRATA_ROCM_VERSION` | presence flag | the same 7.x line, else of the same major. `STRATA_ROCM_VERSION` / `STRATA_ROCM_INDEX` override them; the gfx1030 | yes | `setup.py:1642` |
| `STRATA_SKIP_SHA256` | opt-in (needs 1) | Setup checks the downloaded ready-made engine against the SHA-256 GitHub publishes. On a mismatch the file is corrupt or was changed on the way, so se | yes | `setup.py:2637` |
| `STRATA_SOURCE` | presence flag | itself (a download that fails says how): use `--source modelscope` (`STRATA_SOURCE=modelscope`). ModelScope serves a | yes | `setup.py:124` |
| `STRATA_TEST_EXE` | presence flag |  | no | `args-test.py:24` |

### platform (2)

| variable | default / polarity | note | in a doc | read at |
|---|---|---|---|---|
| `STRATA_IO_THREADS` | presence flag | \| the PLE row reader's default queue depth 16 -> 64 blocking O_DIRECT threads (`STRATA_IO_THREADS`; 128 and 256 change nothing: the drive tops out nea | yes | `src/platform/direct_file.cpp:63` |
| `STRATA_READ_AHEAD` | integer; on by default (0 turns off) | `STRATA_READ_AHEAD=0` turns it off; `STRATA_FILL_AHEAD=N` sets how many fill pairs are asked for ahead (default 256). | yes | `src/platform/memory.cpp:152` |

### prefill (77)

| variable | default / polarity | note | in a doc | read at |
|---|---|---|---|---|
| `STRATA_BF16_TC` | presence flag | \| BF16 projections (hyper-connection, router, indexer, ...) \| converted to FP16 and run on the FP16 tensor cores (#655, #540; `STRATA_BF16_TC=0`: cuBL | yes | `src/prefill/gemm.cu:545` |
| `STRATA_BF16_TC_CACHE` | presence flag | `STRATA_BF16_TC_CACHE=1` retains FP16 copies of explicitly immutable BF16 prompt weights when the FP16 | yes | `src/prefill/gemm.cu:574` |
| `STRATA_BF16_TC_CACHE_MIB` | presence flag | The cache is off by default; only the exact value `1` enables it. `STRATA_BF16_TC_CACHE_MIB` sets the per-`Gemm` | yes | `src/prefill/gemm.cu:576` |
| `STRATA_CVEC_FUSE` | opt-in (needs 1) | \| `STRATA_CVEC_FUSE`, `STRATA_PF_PAD` \| a steered layer's write, control vector and next norm in one pass; padded GEMM row strides \| | yes | `src/prefill/prefill.cpp:319` |
| `STRATA_CVEC_FUSE_CHECK` | integer; value; code default 0 |  | no | `src/prefill/prefill.cpp:3576` |
| `STRATA_DBG_FORCE_SLOW_LAYER` | opt-in (needs 1) |  | no | `src/prefill/prefill.cpp:2711` |
| `STRATA_DENSE_MMQ` | presence flag | \| A \| `STRATA_DENSE_MMQ=0`, no tuning table; SH stream default on \| [`gfx1151-plain.json`](gfx1151-plain.json) \| [`engine-A.log`](engine-A.log) \| | yes | `src/prefill/gemm.cu:844` |
| `STRATA_DRAFT_TIMING` | opt-in (presence) | debug: where this pass's time goes | no | `src/prefill/prefill.cpp:1297` |
| `STRATA_GDN_CHUNKED` | integer; opt-in (presence) | \| #1372 \| `STRATA_GDN_CHUNKED=1` — the prompt's GDN recurrence in 32-token chunks \| applied; no measurable gain on our box (851 vs 842 tok/s with it o | yes | `src/prefill/kernels.cu:1978` |
| `STRATA_GDN_CONVL2` | integer | \| `STRATA_GDN_HEAD`, `STRATA_GDN_PP=2`, `STRATA_GDN_CONVL2`, `STRATA_GDN_NOY` \| the prompt's gated-delta-net recurrence: four lanes per column, two co | yes | `src/prefill/kernels.cu:1908` |
| `STRATA_GDN_CONV_SERIAL` | opt-in (presence) | the old walk (A/B) | no | `src/prefill/kernels.cu:1904` |
| `STRATA_GDN_HEAD` | integer; opt-in (presence) | \| `STRATA_GDN_HEAD`, `STRATA_GDN_PP=2`, `STRATA_GDN_CONVL2`, `STRATA_GDN_NOY` \| the prompt's gated-delta-net recurrence: four lanes per column, two co | yes | `src/prefill/kernels.cu:1997` |
| `STRATA_GDN_KEYHEAD` | integer; opt-in (presence) | sampler and QSA top-k (no SYCL counterpart; the callers take the plain kernels). `STRATA_GDN_KEYHEAD=1` stays opt-in | yes | `src/prefill/kernels.cu:697` |
| `STRATA_GDN_NOY` | integer | \| `STRATA_GDN_HEAD`, `STRATA_GDN_PP=2`, `STRATA_GDN_CONVL2`, `STRATA_GDN_NOY` \| the prompt's gated-delta-net recurrence: four lanes per column, two co | yes | `src/prefill/kernels.cu:1956` |
| `STRATA_GDN_PIPELINE` | integer; on by default (0 turns off) |  | no | `src/prefill/kernels.cu:1974` |
| `STRATA_GDN_PP` | integer; value; code default 0 | \| `STRATA_GDN_HEAD`, `STRATA_GDN_PP=2`, `STRATA_GDN_CONVL2`, `STRATA_GDN_NOY` \| the prompt's gated-delta-net recurrence: four lanes per column, two co | yes | `src/prefill/kernels.cu:1949` |
| `STRATA_GDN_REC_HEADS` | opt-in (presence) | the one-block-per-head kernel (A/B) | no | `src/prefill/kernels.cu:1970` |
| `STRATA_GROUP_COPY` | presence flag |  | no | `src/prefill/prefill.cpp:1025` |
| `STRATA_GR_UNFUSED` | opt-in (needs 1) |  | no | `src/prefill/prefill.cpp:336` |
| `STRATA_HCD_EXACT` | opt-in (needs 1) | \| `STRATA_HCD_EXACT` \| the hyper-connection down projection (N 320, K 10240) in a WMMA kernel that reproduces hipBLASLt solution 1176 / 1177's summati | yes | `src/prefill/prefill.cpp:314` |
| `STRATA_HC_UPMIX` | opt-in (needs 1) | title *("on CUDA")* — its body, though, reveals that the gfx11 side (`STRATA_HC_UPMIX=1`) already exists in main, | yes | `src/prefill/prefill.cpp:296` |
| `STRATA_HC_UPMIX_CHECK` | integer; value; code default 0 |  | no | `src/prefill/prefill.cpp:2371` |
| `STRATA_HIPBLASLT_TUNING` | presence flag | The file's second line names the architecture and version (`STRATA_HIPBLASLT_TUNING_V1 gfx1201 100401`); save it | yes | `src/prefill/gemm.cu:195` |
| `STRATA_HIPBLASLT_VERBOSE` | opt-in (presence) | `STRATA_HIPBLASLT_VERBOSE=1` reported 642 fallbacks over 642 distinct T values (1..1873) with the | yes | `src/prefill/gemm.cu:150` |
| `STRATA_HIP_PROMPT_F16` | presence flag | N = 10240, T = 7313, K = 2560). `STRATA_HIP_PROMPT_F16=1` (opt-in, off by default; the engine prints a tip on gfx103x) runs the 16-bit prompt GEMMs FP | yes | `src/prefill/gemm.cu:367` |
| `STRATA_IDX_FP16_CHECK` | opt-in (presence) |  | no | `src/prefill/prefill.cpp:2577` |
| `STRATA_INDEXER_PER_TOKEN` | opt-in (presence) |  | no | `src/prefill/prefill.cpp:2522` |
| `STRATA_KV_HOST_DMA` | opt-in (needs 1) | 3. `"STRATA_KV_HOST_DMA": "1"` in the same `"env"` block: no GPU kernel writes the RAM copy of the K/V during a | yes | `src/prefill/prefill.cpp:2472` |
| `STRATA_KV_PREFETCH` | presence flag | # What two opt-ins cost on a single-GPU RTX 4090: `STRATA_KV_PREFETCH=1`, and `"parallel": 2` with `--batch-mtp` | yes | `src/prefill/prefill.cpp:1854` |
| `STRATA_KV_STAGE_OWN` | opt-in (presence) |  | no | `src/prefill/prefill.cpp:752` |
| `STRATA_MMQ_RESIDENT_SORT_NE` | presence flag |  | no | `src/prefill/mmq_resident_sort.hpp:17` |
| `STRATA_MTP_BATCH` | opt-in (presence) |  | no | `src/prefill/prefill.cpp:1229` |
| `STRATA_MTP_BATCH_F16` | opt-in (needs 1) |  | no | `src/prefill/prefill.cpp:1266` |
| `STRATA_MTP_BATCH_RING` | on by default (0 turns off) |  | no | `src/prefill/prefill.cpp:1234` |
| `STRATA_PF_BK64` | on by default (0 turns off) |  | no | `src/prefill/wmma_gemm.cu:693` |
| `STRATA_PF_FUSED` | presence flag | \| [2026-10-03-dev-5090](2026-10-03-dev-5090/) \| RTX 5090, Ryzen 9 9950X3D \| IQ3_S (0.1.34 / 0.1.38 / `STRATA_PF_FUSED=1`) \| 4K: 4,308 / 4,846 / 5,361  | yes | `src/prefill/moe_fused.cu:657` |
| `STRATA_PF_FUSED_KQ` | presence flag |  | no | `src/prefill/moe_fused_iq.cu:991` |
| `STRATA_PF_FUSED_NATIVE` | presence flag |  | no | `src/prefill/moe_fused_iq.cu:1040` |
| `STRATA_PF_FUSED_TILE` | presence flag | \| B \| `q4_0` \| `auto:32768` \| `STRATA_PF_FUSED=1`, `STRATA_PF_FUSED_TILE=128`, `STRATA_GR_DOWN_MAX4=1` \| | yes | `src/prefill/moe_fused_iq.cu:1027` |
| `STRATA_PF_GEMM` | opt-in (needs 1) | export STRATA_PF_GEMM=1         # the prompt's FP16 projections on the 128 x 256 WMMA GEMM | yes | `src/prefill/gemm.cu:812` |
| `STRATA_PF_HCDOWN` | opt-in (needs 1) |  | no | `src/prefill/prefill.cpp:306` |
| `STRATA_PF_OCC` | presence flag |  | no | `src/prefill/moe_fused.cu:588` |
| `STRATA_PF_PAD` | opt-in (needs 1) | \| `STRATA_CVEC_FUSE`, `STRATA_PF_PAD` \| a steered layer's write, control vector and next norm in one pass; padded GEMM row strides \| | yes | `src/prefill/gemm.cu:933` |
| `STRATA_PF_PEER_COMPACT` | presence flag |  | no | `src/prefill/prefill.cpp:1557` |
| `STRATA_PF_PEER_OUT_PIPE` | presence flag | =0: one copy after the last group (the A/B) | no | `src/prefill/prefill.cpp:1541` |
| `STRATA_PF_PEER_RING` | integer; opt-in (presence) |  | no | `src/prefill/prefill.cpp:1575` |
| `STRATA_PF_PEER_STREAM` | presence flag |  | no | `src/prefill/prefill.cpp:1571` |
| `STRATA_PF_STEP_SYNC` | opt-in (needs 1) | 2. Find the step that hangs: add `"STRATA_PF_STEP_SYNC": "1"` to the `"env"` block of `strata-<model>.json` | yes | `src/prefill/prefill.cpp:2264` |
| `STRATA_PREFILL_BF16X2` | presence flag | The reference is the old path with `STRATA_PREFILL_BF16X2=1` (every BF16 activation image carries its low part too, close | yes | `src/prefill/prefill.cpp:282` |
| `STRATA_PREFILL_CPU_SHARE` | presence flag | \| #1282 \| `STRATA_PREFILL_CPU_SHARE=auto`: a small chunk's least-routed experts go to the CPU pool \| We already set `STRATA_PREFILL_AUTO_MAX/MMQ/RING` | yes | `src/prefill/prefill.cpp:158` |
| `STRATA_PREFILL_CPU_SHARE_MAX` | presence flag | streaming every expert from 1,024 tokens on; `STRATA_PREFILL_CPU_SHARE_MAX=1024` keeps the old limit. The CPU takes | yes | `src/prefill/prefill.cpp:171` |
| `STRATA_PREFILL_DUMP_R` | presence flag | debug: the final residuals, every 64th | no | `src/prefill/prefill.cpp:3652` |
| `STRATA_PREFILL_DUMP_R_ALL` | presence flag |  | no | `src/prefill/prefill.cpp:3665` |
| `STRATA_PREFILL_GROUP_GATHER` | presence flag |  | no | `src/prefill/prefill.cpp:3342` |
| `STRATA_PREFILL_HELP` | integer; opt-in (presence) | The idle card can help one-chunk prompts (opt-in, `STRATA_PREFILL_HELP=1`). A prompt that fits one chunk runs the stages one after the other, so while | yes | `src/prefill/prefill.cpp:1396` |
| `STRATA_PREFILL_HELP_FRAC` | presence flag | `STRATA_PF_FUSED=1`, nor with `--peer-device`). With it on, `STRATA_PREFILL_HELP_FRAC=f` fixes the share. | yes | `src/prefill/prefill.cpp:1408` |
| `STRATA_PREFILL_ISSUER` | presence flag |  | no | `src/prefill/prefill.cpp:2198` |
| `STRATA_PREFILL_MMQ` | presence flag | -DCMAKE_HIP_ARCHITECTURES=gfx1030 -DSTRATA_PREFILL_MMQ=ON` (the options setup uses for AMD), llama.cpp at the pinned | yes | `src/prefill/prefill.cpp:895` |
| `STRATA_PREFILL_RING` | presence flag | threads now read the blobs themselves, and the port uses the per-layer routed-only walk (`STRATA_PREFILL_RING=8` | yes | `src/prefill/prefill.cpp:250` |
| `STRATA_PREFILL_STREAM_AHEAD` | presence flag |  | no | `src/prefill/prefill.cpp:106` |
| `STRATA_PREFILL_STREAM_MIN` | integer; value; code default (int64_t) -1; value; code default (int64_t) 1024 |  | no | `src/prefill/prefill.cpp:144` |
| `STRATA_PREFILL_TIMING` | opt-in (presence) | STRATA_SELECT_WMMA=1 STRATA_PREFILL_TIMING=1 \ | yes | `src/prefill/prefill.cpp:1763` |
| `STRATA_PROMPT_ATTN_OLD` | opt-in (presence) | \| QSA attention for decode and verify windows (and prompts with `STRATA_PROMPT_ATTN_OLD=1`) \| #540's kernel (fewer shuffles, bit-exact; `STRATA_ATTN_P | yes | `src/prefill/prefill.cpp:2645` |
| `STRATA_QSA_DUMP` | opt-in (presence) |  | no | `src/prefill/prefill.cpp:2623` |
| `STRATA_QSA_DUMP_LAST` | integer |  | no | `src/prefill/prefill.cpp:2624` |
| `STRATA_RING_BYTES` | on by default (0 turns off) | chunk: a smaller ring only slowed it). RTX 5070, 32K prompts against `STRATA_RING_BYTES=0`, 2-3 interleaved | yes | `src/prefill/prefill.cpp:240` |
| `STRATA_SELECT_OLD` | opt-in (presence) |  | no | `src/prefill/prefill.cpp:2544` |
| `STRATA_SEL_OVERLAP` | opt-in (presence) |  | no | `src/prefill/prefill.cpp:2555` |
| `STRATA_STAGER_BATCH` | presence flag | \| #1323 \| Prefill: batched unbuffered stager reads (`STRATA_STAGER_BATCH`), release the experts.bin view once reads are unbuffered (`STRATA_KEEP_MAPPI | yes | `src/prefill/prefill.cpp:1014` |
| `STRATA_STAGER_RING` | integer | flight when the experts are read from the GGUF in place (`STRATA_STAGER_THREADS` / `STRATA_STAGER_RING` override | yes | `src/prefill/prefill.cpp:408` |
| `STRATA_STAGER_SLEEP` | presence flag |  | yes | `src/prefill/prefill.cpp:126` |
| `STRATA_STAGER_THREADS` | presence flag | D-5: the host copy threads of unpinned blobs | yes | `src/prefill/prefill.cpp:1002` |
| `STRATA_STATE_HASH_GDN` | opt-in (presence) | debug: the GDN states as the prompt path leaves them | no | `src/prefill/prefill.cpp:3773` |
| `STRATA_TEST_PAGEABLE` | opt-in (needs 1) |  | no | `src/prefill/prefill.cpp:117` |
| `STRATA_TRACE` | opt-in (presence) | OS page cache remains warm/retained, prompt reuse/adaptation off. STRATA_TRACE=1 | yes | `src/prefill/prefill.cpp:1941` |
| `STRATA_WMMA_BF16` | on by default (0 turns off) |  | no | `src/prefill/gemm.cu:699` |
| `STRATA_WMMA_GEMM` | on by default (0 turns off) |  | no | `src/prefill/gemm.cu:698` |

### program (66)

| variable | default / polarity | note | in a doc | read at |
|---|---|---|---|---|
| `STRATA_ADAPT_JOB_CPU` | presence flag |  | no | `src/program/generate.cpp:1277` |
| `STRATA_ADAPT_LAG` | integer; value; code default 1 | - 0.1.39 path: `STRATA_Q2_LEGACY=1` (#706's switch back to the current Q2_0 kernel), `STRATA_ADAPT_LAG=1` (#463's | yes | `src/program/generate.cpp:1221` |
| `STRATA_ADAPT_NOWAIT` | opt-in (needs 1) | \| `STRATA_ADAPT_NOWAIT=1` \| +0.6% = noise (clean ABBA couplets −1.8/−0.1/+2.0/+2.0) \| trades the #463 determinism fix for nothing \| | yes | `src/program/generate.cpp:1211` |
| `STRATA_ARENA_RELEASE` | presence flag | self-tests were left out of the repository). The switch was called `STRATA_ARENA_RELEASE` in the prototype that measured this; | yes | `src/program/generate.cpp:5494` |
| `STRATA_BATCH_DECODE_SHARE` | presence flag | 2048-8192 tokens) they decode for half as long as the chunk took (`STRATA_BATCH_DECODE_SHARE`, default 0.5), so | yes | `src/program/generate.cpp:9524` |
| `STRATA_BATCH_MTP` | presence flag | On one GPU with MTP (`--mtp` and `--spec`), `--batch-mtp` (in the config's `args`, or `STRATA_BATCH_MTP=1` in the | yes | `src/program/generate.cpp:3789` |
| `STRATA_CACHE_MESSAGE_BOUNDARY` | presence flag | Set `STRATA_CACHE_MESSAGE_BOUNDARY=1` before starting the engine. | yes | `src/program/generate.cpp:9676` |
| `STRATA_CKPT_REREAD` | opt-in (presence) |  | no | `src/program/generate.cpp:9169` |
| `STRATA_DECODE_TIMING` | opt-in (presence) | Where a decode window's time goes (profiling, #610): start the server with `STRATA_DECODE_TIMING=1` (and | yes | `src/program/generate.cpp:9803` |
| `STRATA_DISJOINT_ADAPT` | integer; opt-in (presence) | Set `STRATA_DISJOINT_ADAPT=1` before starting the engine. It is off by default. | yes | `src/program/generate.cpp:4848` |
| `STRATA_DUMP_FIRST_LOGITS` | presence flag |  | no | `src/program/generate.cpp:11632` |
| `STRATA_EARLY_REMOTE_CONTEXTS` | presence flag |  | no | `src/program/generate.cpp:2378` |
| `STRATA_FETCH_THREADS` | integer; opt-in (presence) | \| `STRATA_FETCH_THREADS=N` \| Threads that read the experts from the GGUF while it answers (default 8; 16 was no faster). The prompt path has its own:  | yes | `src/program/generate.cpp:4057` |
| `STRATA_FILL_AHEAD` | presence flag | `STRATA_READ_AHEAD=0` turns it off; `STRATA_FILL_AHEAD=N` sets how many fill pairs are asked for ahead (default 256). | yes | `src/program/generate.cpp:4567` |
| `STRATA_HIP_ADAPT_KERNEL_COPY` | presence flag | - Elsewhere: HIP `STRATA_DENSE_MMQ=1` and `STRATA_HIP_ADAPT_KERNEL_COPY=1` in [AMD_HIP.md](AMD_HIP.md#model-and-serving-configuration); | yes | `src/program/generate.cpp:168` |
| `STRATA_HOST_CORE` | presence flag | - `--host-core last` (or `STRATA_HOST_CORE=last`, Windows): the host thread runs on the last physical core and the | yes | `src/program/generate.cpp:1902` |
| `STRATA_IO_PF_THREADS` | presence flag | `STRATA_IO_PREFETCH_DEPTH`, default 2 when on) are read by I/O threads (`STRATA_IO_PF_THREADS`, default 8) with whole-blob | yes | `src/program/generate.cpp:4084` |
| `STRATA_IO_PREFETCH` | integer; opt-in (presence) | Linux file-tier I/O path (opt in, `STRATA_IO_PREFETCH=1`; 0.1.40.2): the mapped file tier reads experts through | yes | `src/program/generate.cpp:4083` |
| `STRATA_IO_PREFETCH_DEPTH` | integer; opt-in (presence) | `STRATA_IO_PREFETCH_DEPTH`, default 2 when on) are read by I/O threads (`STRATA_IO_PF_THREADS`, default 8) with whole-blob | yes | `src/program/generate.cpp:4882` |
| `STRATA_IO_STATS` | integer; opt-in (presence) | reads; `STRATA_IO_STATS=1` (or prefetch on) adds the page-cache hit / miss split (mincore) and the read-ahead used / unused counts. | yes | `src/program/generate.cpp:4110` |
| `STRATA_KEEP_MAPPING` | presence flag | \| #1323 \| Prefill: batched unbuffered stager reads (`STRATA_STAGER_BATCH`), release the experts.bin view once reads are unbuffered (`STRATA_KEEP_MAPPI | yes | `src/program/generate.cpp:6091` |
| `STRATA_KV_GROW` | presence flag | - `--kv-grow` (or `STRATA_KV_GROW=1`; `--no-kv-grow` turns it off): the K/V takes VRAM only for the cells the requests | yes | `src/program/generate.cpp:3711` |
| `STRATA_KV_GROW_FLOOR` | integer; opt-in (presence) |  | no | `src/program/generate.cpp:5778` |
| `STRATA_KV_GROW_HOLD` | integer; opt-in (presence) |  | no | `src/program/generate.cpp:9148` |
| `STRATA_KV_GROW_INIT` | presence flag |  | no | `src/program/generate.cpp:3723` |
| `STRATA_KV_GROW_STEP` | integer; opt-in (presence) |  | no | `src/program/generate.cpp:5776` |
| `STRATA_KV_ROT` | presence flag | `--kv`, `STRATA_KV_ROT`, `--kv-resident`, `--max-context`, `--mtp-window`, the resolved rope configuration (type, | yes | `src/program/generate.cpp:2117` |
| `STRATA_LAYER_SPLIT_GATE` | opt-in (presence) |  | no | `src/program/generate.cpp:3437` |
| `STRATA_LAYER_SPLIT_PROBE` | presence flag |  | no | `src/program/generate.cpp:4690` |
| `STRATA_LOGPOS` | presence flag | The method of `docs/UNSLOTH_Q4.md`: `STRATA_LOGPOS=<file> STRATA_LOGPOS_TOPK=256` on a serve engine (`--short-read 640 --adapt-every 100000`, greedy, | yes | `src/program/generate.cpp:9352` |
| `STRATA_LOGPOS_EXTRA` | presence flag |  | no | `src/program/generate.cpp:9384` |
| `STRATA_LOOKAHEAD` | integer; on by default (0 turns off) | page faults. With this on, the layer's uncached experts and the router-predicted ones of the next layer (`STRATA_LOOKAHEAD_K`, | yes | `src/program/generate.cpp:4868` |
| `STRATA_LOOKAHEAD_K` | presence flag | page faults. With this on, the layer's uncached experts and the router-predicted ones of the next layer (`STRATA_LOOKAHEAD_K`, | yes | `src/program/generate.cpp:4879` |
| `STRATA_LOOKUP_CHAIN_FIXED` | opt-in (presence) | no policy gate | no | `src/program/generate.cpp:9794` |
| `STRATA_OWNED_PRICE` | opt-in (presence); string compare | short last one (changes the rounding). `STRATA_OWNED_PRICE=exact` (#796): the cache sizing prices the prompt path's | yes | `src/program/generate.cpp:4204` |
| `STRATA_PEER_HOT` | presence flag |  | no | `src/program/generate.cpp:3095` |
| `STRATA_PEER_HOT_AT` | presence flag |  | no | `src/program/generate.cpp:3097` |
| `STRATA_PIPELINE_ADAPT_ASYNC` | presence flag | that were in flight when they were decided have completed (`STRATA_PIPELINE_ADAPT_ASYNC=0`: the blocking tier | yes | `src/program/generate.cpp:5980` |
| `STRATA_PIPELINE_DEBUG` | on by default (0 turns off) | `STRATA_PIPELINE_DEBUG=1`. `--pipeline-windows` and `--adapt-async 1` exclude each other (the engine says so and keeps the | yes | `src/program/generate.cpp:241` |
| `STRATA_PREFILL_AUTO_MAX` | presence flag | \| #1282 \| `STRATA_PREFILL_CPU_SHARE=auto`: a small chunk's least-routed experts go to the CPU pool \| We already set `STRATA_PREFILL_AUTO_MAX/MMQ/RING` | yes | `src/program/generate.cpp:1716` |
| `STRATA_PREFILL_EQUAL` | opt-in (needs 1) | as 0.1.39). `STRATA_PREFILL_EQUAL=1` (#693): a prompt segment is read in chunks of equal size, not full chunks and a | yes | `src/program/generate.cpp:5633` |
| `STRATA_PREFILL_LEND_PCT` | presence flag |  | no | `src/program/generate.cpp:3301` |
| `STRATA_REFILL_BLOCKING` | opt-in (presence) |  | no | `src/program/generate.cpp:232` |
| `STRATA_REFILL_SERIAL` | opt-in (presence) |  | no | `src/program/generate.cpp:9441` |
| `STRATA_RESIDENT_HEADROOM_GIB` | float; opt-in (presence) | - The engine leaves 4 GB of the RAM it finds free (`STRATA_RESIDENT_HEADROOM_GIB`); when even the experts the GPU does | yes | `src/program/generate.cpp:1858` |
| `STRATA_RESIDENT_PIN` | opt-in (presence) | The budget is pinned (locked) in RAM, which leaves the OS and the CPU workers little room. `STRATA_RESIDENT_PIN=0` keeps | yes | `src/program/generate.cpp:1856` |
| `STRATA_RSS_TRACE` | opt-in (presence) |  | no | `src/program/generate.cpp:218` |
| `STRATA_SNAPSHOT_FULL_CAPTURE` | presence flag | sizes and K/V bytes reused during capture. `STRATA_SNAPSHOT_FULL_CAPTURE=1` disables | yes | `src/program/generate.cpp:9120` |
| `STRATA_SNAPSHOT_VERIFY` | opt-in (presence) |  | no | `src/program/generate.cpp:7180` |
| `STRATA_SPEC_DEPTH` | opt-in (presence) |  | yes | `src/program/generate.cpp:10916` |
| `STRATA_SPLIT_COVER_B` | float; opt-in (presence) |  | no | `src/program/generate.cpp:3279` |
| `STRATA_SPLIT_MISS_MS` | float | - missed mass costing 190 ms per unit (fitted to the sweep's best K; `STRATA_SPLIT_MISS_MS` overrides). | yes | `src/program/generate.cpp:3253` |
| `STRATA_SPLIT_OWN` | presence flag | 1,265 tok/s, 16K 1,852 -> 1,950, decode unchanged. `STRATA_SPLIT_OWN=1` (opt-in) gives every card its own buffers: | yes | `src/program/generate.cpp:2017` |
| `STRATA_SPLIT_OWN_BUFFERS` | presence flag |  | no | `src/program/generate.cpp:6330` |
| `STRATA_SPLIT_OWN_PLACE` | presence flag |  | no | `src/program/generate.cpp:3214` |
| `STRATA_SPLIT_RING` | presence flag |  | no | `src/program/generate.cpp:6168` |
| `STRATA_SPLIT_SMALL_MAX` | presence flag |  | no | `src/program/generate.cpp:6523` |
| `STRATA_SPLIT_SMALL_OWN` | presence flag |  | no | `src/program/generate.cpp:6521` |
| `STRATA_SPLIT_TIMING` | opt-in (presence) | No calibration comparison, upstream prompt comparison, `STRATA_SPLIT_TIMING` stage timing, or under-load power-draw capture has been done. Treat all p | yes | `src/program/generate.cpp:10887` |
| `STRATA_SSD_KEEPALIVE` | presence flag |  | no | `src/program/generate.cpp:2794` |
| `STRATA_SSD_KEEPALIVE_WINDOW` | presence flag |  | no | `src/program/generate.cpp:2795` |
| `STRATA_STAGE_TRIM` | presence flag | \| `--trim-stage-weights` \| with an explicit `--layer-split` (e.g. `12,24,36`, not `auto`): every GPU loads only the dense weights of its own layers in | yes | `src/program/generate.cpp:2569` |
| `STRATA_STATE_HASH` | opt-in (presence) |  | no | `src/program/generate.cpp:10621` |
| `STRATA_TEST_CACHE_FAIL` | integer |  | no | `src/program/generate.cpp:4462` |
| `STRATA_TRACE_ADAPT` | opt-in (presence) |  | no | `src/program/generate.cpp:11377` |
| `STRATA_WATCHDOG_S` | presence flag |  | yes | `src/program/generate.cpp:7930` |

### results (14)

| variable | default / polarity | note | in a doc | read at |
|---|---|---|---|---|
| `STRATA_API_KEY` | presence flag | add `"api_key": "some-long-secret"` to `strata-<model>.json` (or set the `STRATA_API_KEY` environment variable); | yes | `bench/results/2026-09-29-rtx3090-epyc-milan/data/strata-bench.py:250` |
| `STRATA_CFG` | presence flag |  | no | `bench/results/2026-10-06-community-rtx4090-opt-ins/conc_bench.py:34` |
| `STRATA_KEY` | presence flag | `STRATA_KEY`), and the captured JSON has the host name, the host address and local paths shortened. | yes | `bench/results/2026-10-04-community-2x-rtx3060/bench-0.1.39.py:41` |
| `STRATA_MAXTOK` | presence flag |  | no | `bench/results/2026-10-04-community-2x-rtx3060/bench-0.1.39.py:46` |
| `STRATA_MODEL` | presence flag |  | no | `bench/results/2026-10-04-community-2x-rtx3060/bench-0.1.39.py:42` |
| `STRATA_PORT` | presence flag | - Build: `-DSTRATA_HIP_GFX906=ON -DCMAKE_HIP_ARCHITECTURES=gfx906 -DSTRATA_PORTABLE=ON`, ROCm clang, Ninja, | yes | `bench/results/2026-10-06-community-rtx4090-opt-ins/conc_bench.py:35` |
| `STRATA_REPO` | presence flag |  | no | `bench/results/2026-10-06-community-rtx4090-opt-ins/conc_bench.py:33` |
| `STRATA_RUNS` | presence flag |  | no | `bench/results/2026-10-04-community-2x-rtx3060/bench-0.1.39.py:45` |
| `STRATA_SCRUB_PREFIX` | presence flag | engine and server log lines. Paths in these files are shortened to `<workspace>` (`common.py`, `STRATA_SCRUB_PREFIX`). | yes | `bench/results/2026-10-02-community-rtx2080ti-11gb/common.py:121` |
| `STRATA_TARGETS` | presence flag |  | no | `bench/results/2026-10-04-community-2x-rtx3060/bench-0.1.39.py:47` |
| `STRATA_TOKENS_PER_CHAR` | presence flag |  | no | `bench/results/2026-10-06-community-rtx4090-opt-ins/conc_bench.py:236` |
| `STRATA_TOOLS` | presence flag |  | no | `bench/results/2026-10-04-community-2x-rtx3060/retry-512k.py:12` |
| `STRATA_TTFT` | opt-in (needs 1) |  | no | `bench/results/2026-10-04-community-2x-rtx3060/bench-0.1.39.py:48` |
| `STRATA_URL` | presence flag | 127.0.0.1:8081").rstrip("/") + "/v1/chat/completions" | yes | `bench/results/2026-10-04-community-2x-rtx3060/bench-0.1.39.py:40` |

### server.py (4)

| variable | default / polarity | note | in a doc | read at |
|---|---|---|---|---|
| `STRATA_ALLOWED_HOSTS` | presence flag | `strata-<model>.json` or `STRATA_ALLOWED_HOSTS=strata.example.com` (comma-separated); `".example.com"` allows that | yes | `serve/server.py:5480` |
| `STRATA_BATCH_TRACE` | presence flag |  | no | `serve/server.py:538` |
| `STRATA_PARALLEL_SOLO` | presence flag | `--prompt-cache 0` it stays in the slot; `STRATA_PARALLEL_SOLO=0` turns it off). The draft layer's own K/V was | yes | `serve/server.py:1141` |
| `STRATA_REQUEST_LINES` | presence flag |  | no | `serve/server.py:619` |

### setup_intel.py (1)

| variable | default / polarity | note | in a doc | read at |
|---|---|---|---|---|
| `STRATA_SYCL_ROOT` | presence flag | checkout, or `STRATA_SYCL_ROOT`). An earlier Strata install on the same PC keeps its data folder in | yes | `sycl/setup_intel.py:40` |

### src (32)

| variable | default / polarity | note | in a doc | read at |
|---|---|---|---|---|
| `STRATA_DBG_DRAFT` | opt-in (presence) | the window the drafter built and what the target said | no | `sycl/src/program/generate.cpp:12279` |
| `STRATA_DUMP_SEL` | presence flag | Measured on the last chunk of an 80K prompt (first QSA layer, `STRATA_DUMP_SEL=<file>`): the union of 8 consecutive | yes | `sycl/src/prefill/prefill.cpp:3135` |
| `STRATA_FILL_SERIAL` | presence flag | 120 s -> 41 s (its 8.2 GB host mirror is ~9 s of the rest). Output identical. `STRATA_FILL_SERIAL=1` is the old fill. | yes | `sycl/src/program/generate.cpp:4530` |
| `STRATA_GGUF_PLAN_READ` | opt-in (needs 1) |  | no | `sycl/src/prefill/prefill.cpp:2485` |
| `STRATA_GR_DOWN_DIRECT` | integer; on by default (0 turns off) | 6 tokens (bitwise equal). Switches to the old paths: `STRATA_PLAN_PARALLEL=0`, `STRATA_GR_DOWN_DIRECT=0`, | yes | `sycl/src/kernels/cuda/fused_gr.dp.cpp:597` |
| `STRATA_GR_DOWN_SLICED` | integer; on by default (0 turns off) | ~1e-7) flips that near-tie back: its output is the original one. `STRATA_GR_DOWN_SLICED=0` restores the direct kernel. | yes | `sycl/src/kernels/cuda/fused_gr.dp.cpp:583` |
| `STRATA_GR_NORM_SPLIT` | integer; on by default (0 turns off) |  | no | `sycl/src/kernels/cuda/fused_gr.dp.cpp:377` |
| `STRATA_HC_CHECK` | presence flag | B70, so on SYCL it runs only with `STRATA_HC_CHECK=1` (open). The port's split-norm kernel was renamed | yes | `sycl/src/kernels/cuda/fused_gr.dp.cpp:2192` |
| `STRATA_MIRROR_MIB` | presence flag | counts the other card's layers; the lines `100% of the experts resident` that follow are the ones to read. Set `STRATA_MIRROR_MIB=0` there, | yes | `sycl/src/program/generate.cpp:4706` |
| `STRATA_MMVQ_A2` | integer; on by default (0 turns off) | identical. Coder decode 44.9 -> 54 tok/s (2k prompt, greedy). `STRATA_MMVQ_A2=0` restores the old path. | yes | `sycl/src/kernels/cuda/native_mmvq.dp.cpp:1535` |
| `STRATA_MMVQ_PF` | integer |  | no | `sycl/src/kernels/cuda/native_mmvq.dp.cpp:1690` |
| `STRATA_MMVQ_RPW` | integer | default: the shared kernel (measured equal at warm clocks) | no | `sycl/src/kernels/cuda/native_mmvq.dp.cpp:2001` |
| `STRATA_MMVQ_SG` | integer | Tried, no gain: SIMD16 builds of the multi-column mmvq and the wide Q6_K kernel (`STRATA_MMVQ_SG`: 16 all, | yes | `sycl/src/kernels/cuda/native_mmvq.dp.cpp:165` |
| `STRATA_MMVQ_WIDE` | integer; on by default (0 turns off) | 16-byte chunk without a needed byte and cannot cross a page at the end of an allocation. `STRATA_MMVQ_WIDE_32=0` | yes | `sycl/src/kernels/mmvq_bench.cpp:35` |
| `STRATA_MMVQ_WIDE_32` | integer; on by default (0 turns off) | 16-byte chunk without a needed byte and cannot cross a page at the end of an allocation. `STRATA_MMVQ_WIDE_32=0` | yes | `sycl/src/kernels/cuda/native_mmvq.dp.cpp:1960` |
| `STRATA_MMVQ_WIDE_K` | integer; on by default (0 turns off) | `STRATA_MMVQ_WIDE_K=0`. (`iq_parity` reports 10 "missing fixture" failures with and without the change: the oracle | yes | `sycl/src/kernels/cuda/native_mmvq.dp.cpp:1871` |
| `STRATA_MMVQ_WIDE_MAXC` | integer |  | no | `sycl/src/kernels/cuda/native_mmvq.dp.cpp:3434` |
| `STRATA_MMVQ_WIDE_MIN` | integer |  | no | `sycl/src/kernels/cuda/native_mmvq.dp.cpp:3433` |
| `STRATA_MMVQ_WIDE_RPW` | integer |  | no | `sycl/src/kernels/cuda/native_mmvq.dp.cpp:1694` |
| `STRATA_PLE_TRACE` | opt-in (presence) | trace of the PLE reader (`STRATA_PLE_TRACE=1`) shows the slow runs pay one 226 ms PLE read stall in the first | yes | `sycl/src/ngram/ple_reader.cpp:97` |
| `STRATA_PREFILL_FIRST` | presence flag | \| a short first prompt chunk (`STRATA_PREFILL_FIRST`, default 256 tokens) so the GPU starts while the remaining rows are still being read \| 2,184 toke | yes | `sycl/src/prefill/prefill.cpp:2164` |
| `STRATA_PREFILL_STREAM_ALL` | opt-in (needs 1); value; code default 0) : -1 | upstream, the port's default; `STRATA_PREFILL_STREAM_ALL=1` restores the other for debugging). | yes | `sycl/src/prefill/prefill.cpp:220` |
| `STRATA_PREFILL_SYNC` | opt-in (presence) | after every phase (`STRATA_PREFILL_SYNC=1`, kept as a debug switch). The fix: the copy queue writes a sequence | yes | `sycl/src/prefill/prefill.cpp:1958` |
| `STRATA_PROMPT_ATTN_XMX` | integer; value; code default 0 | `STRATA_PROMPT_ATTN_XMX=1`). Where the prompt time goes now (2,184 / 8,000 tokens): dequant 28% / 27%, GEMMs | yes | `sycl/src/kernels/cuda/qsa_prompt_attn_xmx.dp.cpp:367` |
| `STRATA_RING_TIMEOUT_S` | presence flag |  | no | `sycl/src/core/verify.cpp:157` |
| `STRATA_VERIFY_ALL_SLOTS` | opt-in (presence) | debug: every filled slot read back and compared with the GGUF | yes | `sycl/src/program/generate.cpp:4586` |
| `STRATA_VERIFY_DUMP` | opt-in (presence) | (`STRATA_VERIFY_FIND=1`, `STRATA_VERIFY_DUMP=dir`) reads every filled slot back and compares it with the GGUF; that is how | yes | `sycl/src/program/generate.cpp:4617` |
| `STRATA_VERIFY_EAGER` | opt-in (presence) | eager (SYCL port): prof_h_ already holds the host clocks | yes | `sycl/src/core/verify.cpp:751` |
| `STRATA_VERIFY_FIND` | opt-in (presence) | whose blob is the wrong data? | yes | `sycl/src/program/generate.cpp:4604` |
| `STRATA_VERIFY_NO_HOST` | presence flag | All experts were resident in VRAM on both cards in both runs (engine line `layer split: 100% of the experts resident`), so `STRATA_VERIFY_NO_HOST=1` w | yes | `sycl/src/core/verify.cpp:1941` |
| `STRATA_WARM_GRAPHS` | presence flag | \| every window graph and the drafter's graphs captured at load (`STRATA_WARM_GRAPHS=0`: as before) \| the first request no longer pays 250-290 ms of ca | yes | `sycl/src/program/generate.cpp:12142` |
| `STRATA_WINDOW_SYNC` | presence flag |  | no | `sycl/src/core/verify.cpp:1905` |

### strata (7)

| variable | default / polarity | note | in a doc | read at |
|---|---|---|---|---|
| `STRATA_DMA_BATCH` | presence flag | With `--pcie-mode dma`, `STRATA_DMA_BATCH=1` submits a verifier group's independent | yes | `include/strata/core/dma_batch.hpp:32` |
| `STRATA_EMULATE_CC` | presence flag |  | no | `include/strata/core/emulate.hpp:17` |
| `STRATA_SPEC_COUPLED` | presence flag | Coupled drafts with Gumbel-max picks (opt-in, `STRATA_SPEC_COUPLED=1` and `STRATA_SPEC_GUMBEL=1`): for a request | yes | `include/strata/core/coupled_draft.hpp:59` |
| `STRATA_SPEC_MIN_TEMP` | presence flag |  | yes | `include/strata/core/spec_prob.hpp:69` |
| `STRATA_SPEC_PROB` | presence flag |  | yes | `include/strata/core/coupled_draft.hpp:69` |
| `STRATA_SPEC_PROB_DT` | presence flag |  | no | `include/strata/core/spec_prob.hpp:57` |
| `STRATA_SPEC_PROB_GATE` | presence flag |  | no | `include/strata/core/spec_prob.hpp:47` |

### test_detok.py (1)

| variable | default / polarity | note | in a doc | read at |
|---|---|---|---|---|
| `STRATA_TOKENIZER` | presence flag |  | no | `serve/test_detok.py:21` |

## 3.5 Build-time CMake options (not settable from the JSON)

These are `option()` flags in `CMakeLists.txt` / `cmake/hip_backend.cmake` — they decide what the engine binary
contains, so they cannot be changed by the config file. Listed for completeness because several names collide
with runtime env vars (STRATA_ISA_FLOOR, STRATA_PREFILL_MMQ, STRATA_HIP_ARCHS ...).

- `STRATA_ENABLE_SYCL` — default `OFF` — EXPERIMENTAL: build the Intel Arc (SYCL) engine from sycl/ - docs/INTEL_ARC.md (CMakeLists.txt:14)
- `STRATA_PORTABLE` — default `OFF` — build for other PCs: AVX2 baseline, static MSVC runtime (CMakeLists.txt:34)
- `STRATA_ENABLE_CUDA` — default `OFF` — Build the CUDA targets (Phase 2+) (CMakeLists.txt:58)
- `STRATA_HIP_GFX906` — default `OFF` — Build the CUDA targets for AMD gfx906 through HIP (wave64 compat layer) (CMakeLists.txt:64)
- `STRATA_ENABLE_HIP` — default `OFF` — Build the HIP targets for wave32 AMD GPUs (gfx1100, gfx1201; gfx1012/gfx1030 unvalidated) (CMakeLists.txt:71)
- `STRATA_PREFILL_MMQ` — default `OFF` — Build the optional GGML MMQ prefill path for HIP (CMakeLists.txt:72)
- `STRATA_MMQ_KQUANTS` — default `OFF` — Build the MMQ prompt kernels for Q4_K / Q5_K / Q5_1 / Q6_K: the CUDA experts of Unsloth's UD-Q4_K_XL, and on HIP the dense GGUF projections (STRATA_DENSE_MMQ) (CMakeLists.txt:76)
- `STRATA_Q6K_EXPERTS` — default `OFF` — Build the Q6_K gate/up grouped expert kernels (UD-Q6_K_XL) (CMakeLists.txt:80)
- `STRATA_ORCA_Q4KS_MMQ` — default `OFF` — Build the GGML Q5_0 MMQ instance for OrcaRouter Q4_K_S (CMakeLists.txt:84)
- `STRATA_BUILD_CONVERSATION_TESTS` — default `OFF` — Build standalone conversation cache tests (CMakeLists.txt:100)
- `STRATA_WERROR` — default `OFF` — Treat compiler warnings as errors (CMakeLists.txt:101)
- `STRATA_EXPERIMENTAL_SM60` — default `OFF` — community build for GPUs below compute capability 7.5: Pascal sm_60, Volta sm_70 (#236) (CMakeLists.txt:151)
- `STRATA_NATIVE_EXPERTS` — default `ON` — Native (IQ) expert support through ggml-cpu (CMakeLists.txt:1141)

## 4. Server CLI flags

| flag | as the code defines it | source |
|---|---|---|
| `--api-key` | ap.add_argument("--api-key", default=os.environ.get("STRATA_API_KEY", ""), | `serve/server.py:5348` |
| `--api-monitor` | ap.add_argument("--api-monitor", action="store_true", | `serve/server.py:5354` |
| `--before-load` | ap.add_argument("--before-load", help="a command run before the model is loaded again (e.g. to unload another " | `serve/server.py:5364` |
| `--config` | ap.add_argument("--config", help="strata engine config (JSON: exe, args, cwd, tokenizer, model_name), " | `serve/server.py:5331` |
| `--engine` | ap.add_argument("--engine", choices=["mock", "strata"], default="mock") | `serve/server.py:5330` |
| `--fit-max-tokens` | ap.add_argument("--fit-max-tokens", action="store_true", | `serve/server.py:5345` |
| `--gpu` | ap.add_argument("--gpu", help="the GPU to run on, as nvidia-smi numbers them, or several for a layer split " | `serve/server.py:5340` |
| `--host` | ap.add_argument("--host", default=None, | `serve/server.py:5333` |
| `--idle-unload` | ap.add_argument("--idle-unload", type=float, default=None, metavar="SECONDS", | `serve/server.py:5357` |
| `--lazy` | ap.add_argument("--lazy", action="store_true", help="start the API unloaded (the engine and the vision encoder start with the first request)") | `serve/server.py:5353` |
| `--mcp-config` | ap.add_argument("--mcp-config", help="a JSON file with MCP servers in Claude Desktop's format ({\"mcpServers\": " | `serve/server.py:5350` |
| `--min-free-vram-mib` | ap.add_argument("--min-free-vram-mib", type=int, default=None, | `serve/server.py:5361` |
| `--open` | ap.add_argument("--open", action="store_true", help="open the local page in the browser once the model is ready") | `serve/server.py:5344` |
| `--port` | ap.add_argument("--port", type=int, default=8095) | `serve/server.py:5339` |
| `--script` | ap.add_argument("--script", action="append", | `serve/server.py:5336` |
| `--slot-save-path` | ap.add_argument("--slot-save-path", default=None, metavar="DIR", | `serve/server.py:5366` |
| `--tokenizer` | ap.add_argument("--tokenizer", default=str(ROOT / "pack/full/tokenizer"), | `serve/server.py:5342` |

## 5. Setup CLI flags (what writes the JSON)

| flag | as the code defines it | source |
|---|---|---|
| `--api-key` | ap.add_argument("--api-key", help="require this key from clients (recommended with --host 0.0.0.0)") | `setup.py:4550` |
| `--backend` | ap.add_argument("--backend", choices=["cuda", "hip", "sycl"], | `setup.py:4608` |
| `--browser` | ap.add_argument("--browser", dest="browser", action="store_true", | `setup.py:4554` |
| `--build` | ap.add_argument("--build", action="store_true", help="compile the engine instead of using the ready-made one") | `setup.py:4569` |
| `--calibrate` | ap.add_argument("--calibrate", action="store_true", | `setup.py:4584` |
| `--check` | ap.add_argument("--check", action="store_true", help="only check this PC and exit") | `setup.py:4583` |
| `--context` | ap.add_argument("--context", type=int) | `setup.py:4517` |
| `--cuda` | ap.add_argument("--cuda", choices=["12", "13", "auto"], default=os.environ.get("STRATA_CUDA") or None, | `setup.py:4577` |
| `--data-dir` | ap.add_argument("--data-dir", help="where the model files go (~70-120 GB): default Strata-data next to this folder, " | `setup.py:4556` |
| `--draft-vocab` | ap.add_argument("--draft-vocab", choices=list(DRAFT_VOCABS), | `setup.py:4586` |
| `--experimental-speed-projection` | ap.add_argument("--experimental-speed-projection", metavar="on\|off\|GGUF", | `setup.py:4534` |
| `--family` | ap.add_argument("--family", choices=list(FAMILIES), help="qwen = Qwen3.8-Flash-Next, swift = Swift 1.5") | `setup.py:4515` |
| `--gguf-dir` | ap.add_argument("--gguf-dir", help="use GGUF files you already have (a folder with every shard: " | `setup.py:4559` |
| `--gpu` | ap.add_argument("--gpu", help="one GPU, numbered as nvidia-smi numbers them (default: asked when several can be " | `setup.py:4538` |
| `--gpus` | ap.add_argument("--gpus", help="several GPUs sharing one model, as nvidia-smi numbers them (AMD: as setup lists " | `setup.py:4540` |
| `--host` | ap.add_argument("--host", help="where the server listens: 127.0.0.1 = this PC only (default), 0.0.0.0 = also other " | `setup.py:4548` |
| `--inspect` | ap.add_argument("--inspect", nargs="+", metavar=("SOURCE", "VARIANT"), | `setup.py:4574` |
| `--kv` | ap.add_argument("--kv", choices=["int8", "q4_0", "k8v4"], | `setup.py:4525` |
| `--kv-streaming` | ap.add_argument("--kv-streaming", choices=["auto", "on", "off"], default="auto", | `setup.py:4605` |
| `--layer-split` | ap.add_argument("--layer-split", help="with --gpus: where each later GPU's layers start (\"18\", \"16,32\"), one " | `setup.py:4543` |
| `--low-ram` | ap.add_argument("--low-ram", choices=["auto", "on", "off", "resident", "mmap"], default="auto", | `setup.py:4591` |
| `--model` | ap.add_argument("--model", choices=list(MODELS)) | `setup.py:4516` |
| `--models-dir` | ap.add_argument("--models-dir", help="where the GGUF files go (default: <data folder>/models)") | `setup.py:4558` |
| `--no-browser` | ap.add_argument("--no-browser", dest="browser", action="store_false", default=None, | `setup.py:4551` |
| `--no-remote-expert-opt` | ap.add_argument("--no-remote-expert-opt", action="store_true", | `setup.py:4546` |
| `--no-start` | ap.add_argument("--no-start", action="store_true", help="install only, do not start the model") | `setup.py:4563` |
| `--parallel` | ap.add_argument("--parallel", type=int, metavar="N", | `setup.py:4602` |
| `--port` | ap.add_argument("--port", type=int, help="the server's port (default: the one the install was set up with, 8080 for a new one)") | `setup.py:4537` |
| `--prebuilt` | ap.add_argument("--prebuilt", default=os.environ.get("STRATA_PREBUILT_URL", PREBUILT_URL), | `setup.py:4581` |
| `--resident-budget-gib` | ap.add_argument("--resident-budget-gib", type=float, metavar="N", | `setup.py:4596` |
| `--rollback-engine` | ap.add_argument("--rollback-engine", action="store_true", | `setup.py:4567` |
| `--rope-scale` | ap.add_argument("--rope-scale", type=float, | `setup.py:4522` |
| `--rope-scaling` | ap.add_argument("--rope-scaling", choices=["none", "linear", "yarn"], | `setup.py:4518` |
| `--setup` | ap.add_argument("--setup", action="store_true", help="install another model or change settings") | `setup.py:4562` |
| `--skip-build` | ap.add_argument("--skip-build", action="store_true", help=argparse.SUPPRESS) | `setup.py:4612` |
| `--source` | ap.add_argument("--source", choices=SOURCES, default=None, | `setup.py:4570` |
| `--update` | ap.add_argument("--update", action="store_true", | `setup.py:4564` |
| `--vision` | ap.add_argument("--vision", choices=["yes", "no", "none", "gpu", "cpu"], | `setup.py:4528` |
| `--vision-tokens` | ap.add_argument("--vision-tokens", type=int, metavar="N", | `setup.py:4530` |
| `--vram-reserve-mib` | ap.add_argument("--vram-reserve-mib", type=int, metavar="N", | `setup.py:4599` |
| `--yes` | ap.add_argument("--yes", action="store_true", help="accept the recommended answers") | `setup.py:4561` |

## 6. Per-request keys and POST /settings

| key | scope | source |
|---|---|---|
| `sampling.experimental_speed_projection` | on = sampling.get("experimental_speed_projection") | `serve/server.py:961` |
| `sampling.frequency_penalty` | pf = sampling.get("frequency_penalty") | `serve/server.py:917` |
| `sampling.min_p` | mp = sampling.get("min_p") | `serve/server.py:912` |
| `sampling.penalty_last_n` | pln = sampling.get("penalty_last_n") | `serve/server.py:929` |
| `sampling.presence_penalty` | pp = sampling.get("presence_penalty") | `serve/server.py:919` |
| `sampling.repetition_penalty` | rp = sampling.get("repetition_penalty") | `serve/server.py:915` |
| `sampling.seed` | seed = sampling.get("seed") | `serve/server.py:934` |
| `sampling.strata_checkpoint` | if sampling.get("strata_checkpoint") is False: | `serve/server.py:946` |
| `sampling.strata_prefix` | prefix = sampling.get("strata_prefix") | `serve/server.py:950` |
| `sampling.strata_tune` | tune = sampling.get("strata_tune") | `serve/server.py:938` |
| `sampling.temperature` | t = sampling.get("temperature") | `serve/server.py:902` |
| `sampling.top_k` | tk = sampling.get("top_k") | `serve/server.py:908` |
| `sampling.top_p` | tp = sampling.get("top_p") | `serve/server.py:905` |
| `POST /settings experimental_speed_projection` | elif key == "experimental_speed_projection": | `serve/server.py:5261` |
| `POST /settings reasoning_budget_tokens` | elif key == "reasoning_budget_tokens":                 # #123: 0 means no budget, so 0 is allowed here | `serve/server.py:5257` |
| `POST /settings reasoning_effort` | if key == "reasoning_effort": | `serve/server.py:5240` |
| `POST /settings temperature` | elif key == "temperature": | `serve/server.py:5243` |
| `POST /settings top_k` | elif key == "top_k": | `serve/server.py:5249` |
| `POST /settings top_p` | elif key == "top_p": | `serve/server.py:5246` |

## 7. The same setting reachable two ways (flag + env)

Only the pairs the code itself states — the name-normalised twins plus the ones written as "or" in the usage
text. Everything else in §3 is env-only, and everything else in §2 is flag-only.

- `--kv-grow` ↔ `STRATA_KV_GROW` — usage text: `--kv-grow (or STRATA_KV_GROW=1)`; read at src/program/generate.cpp:3711
- `--no-kv-grow` ↔ `STRATA_KV_GROW` — the env can turn it on, the flag turns it off
- `--host-core` ↔ `STRATA_HOST_CORE` — usage: `STRATA_HOST_CORE sets it too`; read at src/program/generate.cpp:1902
- `--batch-mtp` ↔ `STRATA_BATCH_MTP` — usage: `STRATA_BATCH_MTP=1 does the same`; read at src/program/generate.cpp:3789
- `--coupled-draft` ↔ `STRATA_SPEC_COUPLED` — usage names the env as the same switch; read at include/strata/core/coupled_draft.hpp:59
- `--prefill auto:N` ↔ `STRATA_PREFILL_AUTO_MAX` — `auto:16384 / auto:32768 (or STRATA_PREFILL_AUTO_MAX)`; read at src/program/generate.cpp:1716
- `--resident-experts` ↔ `STRATA_RESIDENT_PIN`, `STRATA_RESIDENT_HEADROOM_GIB` — the flag sets the mode, the env overrides pin and headroom; read at src/program/generate.cpp:1856-1869
- `--mmap-experts` ↔ `STRATA_ARENA_MMAP` — the env is the Linux mapped-arena form of the same choice; src/core/expert_source.cpp:3797
- `--api-key (server)` ↔ `STRATA_API_KEY` — serve/server.py:5348
- `--allowed-hosts` ↔ `STRATA_ALLOWED_HOSTS` — serve/server.py:5480
- `--tokenizer` ↔ `STRATA_TOKENIZER` — serve/test_detok.py:21
- `--cuda (setup)` ↔ `STRATA_CUDA` — setup.py:4577
- `--prebuilt (setup)` ↔ `STRATA_PREBUILT_URL` — setup.py:4581
- `--open / open_browser` ↔ `—` — the config key wins over the flag only in the negative direction (#609): serve/server.py:5581
- `--gpu / "gpu"` ↔ `CUDA_VISIBLE_DEVICES`, `HIP_VISIBLE_DEVICES` — the engine sets these itself from --gpu, so a caller never has to export them (usage text); the server also sets them from the config: serve/server.py:2148-2152

## 8. Your current config, mapped

- `exe`
- `args`: 20 flags — `--pack`, `--native`, `--ple-gguf`, `--expert-profile`, `--expert-cache`, `--prefill`, `--spec`, `--spec-min-p`, `--mtp`, `--max-context`, `--rope-scaling`, `--rope-scale`, `--kv`, `--mmap-experts`, `--control-vector-scaled`, `--control-vector-layer-range`, `--cvec-mode`, `--cvec-dir`, `--kv-resident`, `--resident-budget-gib`
- `cwd`
- `tokenizer`
- `model_name`
- `log`
- `lib_dirs`
- `port`
- `host`
- `backend`
- `env` (8 vars): `STRATA_HIPBLASLT_TUNING`, `STRATA_PREFILL_AUTO_MAX`, `STRATA_PREFILL_MMQ`, `STRATA_PREFILL_RING`, `STRATA_IO_THREADS`, `STRATA_RESIDENT_PIN`, `STRATA_PREFILL_CPU_SHARE`, `STRATA_RESIDENT_HEADROOM_GIB`
- `draft_vocab`
- `fit_max_tokens`
- `anthropic_thinking`
- `effort_position`
- `api_monitor`
