# Strata — every option that can be set (regenerated from strata)

Machine-compiled from the code, not from a README.  Tidy long-format copy: `options-inventory.csv`.

Counts: **166** engine cli, **342** env, **17** server cli, **49** setup cli, **71** config key

## engine_cli (166)

| name | source | line | description |
|---|---|---|---|
| `--adapt-async` | src/program/generate.cpp |  |  |
| `--adapt-decay` | src/program/generate.cpp |  |  |
| `--adapt-every` | src/program/generate.cpp |  |  |
| `--adapt-swaps` | src/program/generate.cpp |  |  |
| `--batch` | src/program/generate.cpp |  |  |
| `--batch-groups` | src/program/generate.cpp |  | --batch with a layer split: the slots in G groups pipelined through the GPUs |
| `--batch-mtp` | src/program/generate.cpp |  | --batch (opt-in, one GPU, needs --mtp and --spec): each slot also verifies one MTP |
| `--check-logits` | src/program/generate.cpp |  | copy and check all logits in the stream-token path |
| `--control-vector` | src/program/generate.cpp |  |  |
| `--control-vector-layer-range` | src/program/generate.cpp |  |  |
| `--control-vector-scaled` | src/program/generate.cpp |  |  |
| `--conversation-cache-mib` | src/program/generate.cpp |  | --serve: RAM budget for parked conversations (default 0 = off) |
| `--conversation-cache-min-free-mib` | src/program/generate.cpp |  | --serve: physical RAM floor when parking or restoring a |
| `--conversation-cache-slots` | src/program/generate.cpp |  | --serve: at most N parked conversations (default 4) |
| `--coupled-draft` | src/program/generate.cpp |  | enable coupled draft sampling for MTP drafter under sampling (STRATA_SPEC_COUPLED) |
| `--cpu-oracle-q8-0` | src/program/generate.cpp |  | experimental pinned CPU expert quantization and dot reduction |
| `--cvec-dir` | src/program/generate.cpp |  |  |
| `--cvec-mode` | src/program/generate.cpp |  |  |
| `--dump-final-r` | src/program/generate.cpp |  |  |
| `--dump-halves` | src/program/generate.cpp |  | write both halves' block_out and inject per layer: the half bisection |
| `--dump-layers` | src/program/generate.cpp |  | write R after EVERY layer, per position: the C1 bisection ladder |
| `--dump-logits` | src/program/generate.cpp |  | write one line of raw logits per position |
| `--dump-mixed` | src/program/generate.cpp |  | write the post-attention residual (n_embd, f32) |
| `--dump-residual` | src/program/generate.cpp |  |  |
| `--dump-routing` | src/program/generate.cpp |  | write the routed expert ids and weights per layer per position (P0.S8) |
| `--embd-gguf` | src/program/generate.cpp |  | the token embedding from this GGUF instead of --native's (tools/embd_bf16_pack.py: |
| `--eos-ids` | src/program/generate.cpp |  |  |
| `--expert-cache` | src/program/generate.cpp |  | R4: keep N expert blobs resident in VRAM and compute their rows on the |
| `--expert-cache-cpu-order` | src/program/generate.cpp |  | experimental GPU expert reduction matching CPU order |
| `--expert-cache-device1` | src/program/generate.cpp |  |  |
| `--expert-cache-device2` | src/program/generate.cpp |  |  |
| `--expert-cache-device3` | src/program/generate.cpp |  |  |
| `--expert-cache-per-layer` | src/program/generate.cpp |  | R4.2g: give each layer its OWN slots instead of letting the first |
| `--expert-cache-remote-placement` | src/program/generate.cpp |  |  |
| `--expert-profile` | src/program/generate.cpp |  | R4.2e: pre-load the VRAM tier from a `profile.bin` (see |
| `--expert-profile-save` | src/program/generate.cpp |  | --serve, #477: save what the adaptive tier learned (the experts in |
| `--expert-profile-save-every` | src/program/generate.cpp |  |  |
| `--gpu` | src/program/generate.cpp |  | run on these GPUs, comma-separated nvidia-smi/PCI indices (default: every |
| `--gpu-only-full` | src/program/generate.cpp |  | MEASURE: replay pre+post for all 48 layers plus the LM head, no pool. |
| `--gpu-stages` | src/program/generate.cpp |  | R0.9: capture the layer as three graphs (mixer / ffn+router / post) |
| `--gr-fp32-activations` | src/program/generate.cpp |  | experimental CUDA-oracle GR activation precision |
| `--gr-native-mmvf` | src/program/generate.cpp |  | experimental pinned GR norm/projections; implies FP32 activations |
| `--graph-only` | src/program/generate.cpp |  | MEASURE: replay the 48 `pre` graphs only.  OMITS the 48 `post` graphs |
| `--greedy` | src/program/generate.cpp |  | argmax (the default) |
| `--help` | src/program/generate.cpp |  |  |
| `--host-core` | src/program/generate.cpp |  | The host thread's core: first (the default: the first physical core, as always) or |
| `--keep-canonical` | src/program/generate.cpp |  | A/B: also load canonical copies of natively served tensors (more VRAM) |
| `--kv` | src/program/generate.cpp |  |  |
| `--kv-grow` | src/program/generate.cpp |  | the K/V takes VRAM only for the cells the requests reach and the expert |
| `--kv-resident` | src/program/generate.cpp |  | KV streaming: keep N cells of each QSA layer in VRAM (min 20480) and the |
| `--layer-split` | src/program/generate.cpp |  |  |
| `--logits-stride` | src/program/generate.cpp |  | store every Nth row plus final input (default 1); N>1 requires --max-new 1 |
| `--lookup-chain` | src/program/generate.cpp |  | opt-in: after the MTP's drafts, add up to K prompt-lookup drafts that continue |
| `--lookup-chain-min` | src/program/generate.cpp |  | the shortest context match --lookup-chain extends on (default 3) |
| `--max-context` | src/program/generate.cpp |  | KV/state capacity (default 4096) |
| `--max-new` | src/program/generate.cpp |  | tokens to generate (default 16) |
| `--mmap-experts` | src/program/generate.cpp |  | R2.1: opt OUT of the resident expert arena, back to MapViewOfFile. |
| `--mtp` | src/program/generate.cpp |  |  |
| `--mtp-draft-vocab` | src/program/generate.cpp |  | opt-in: the draft head's token subset (default <mtp>/draft_vocab.bin) |
| `--mtp-hnorm` | src/program/generate.cpp |  |  |
| `--mtp-max-t` | src/program/generate.cpp |  | cap the MTP's windows at M tokens (0 = --spec; longer ones come from suffixes) |
| `--mtp-q4` | src/program/generate.cpp |  |  |
| `--mtp-window` | src/program/generate.cpp |  |  |
| `--native` | src/program/generate.cpp |  | every full-context native path at once (plan v0.3 P1): stream-token, |
| `--native-bf16` | src/program/generate.cpp |  | experimental CUDA-oracle SSM/router/indexer BF16 projections |
| `--native-bf16-extra` | src/program/generate.cpp |  | experimental CUDA-oracle PLE/shared gate BF16 projections |
| `--native-dense-gguf` | src/program/generate.cpp |  |  |
| `--native-flash-attn-short` | src/program/generate.cpp |  | diagnostic pinned vector attention; --max-context <=256 |
| `--native-gdn` | src/program/generate.cpp |  | experimental pinned CUDA GDN norms/gates/recurrence |
| `--native-head-gguf` | src/program/generate.cpp |  | native Q5_K head from model shard 1; requires --stream-token |
| `--native-moe-combine` | src/program/generate.cpp |  | experimental pinned CUDA routed/shared combination |
| `--native-ple-key` | src/program/generate.cpp |  | experimental native PLE key; requires --native-dense-gguf |
| `--native-ple-postops` | src/program/generate.cpp |  | experimental pinned PLE postprojection arithmetic |
| `--native-qsa` | src/program/generate.cpp |  | experimental pinned QSA normalization and output gate |
| `--native-qsa-indexer` | src/program/generate.cpp |  | experimental pinned indexer key cache and pooling |
| `--native-rope` | src/program/generate.cpp |  | experimental pinned text-only CUDA rotary arithmetic |
| `--native-router` | src/program/generate.cpp |  | experimental pinned CUDA 512-expert top-10 routing |
| `--no-capture` | src/program/generate.cpp |  | run the layers directly instead of replaying graphs |
| `--no-coupled-draft` | src/program/generate.cpp |  | disable coupled draft sampling (propose argmax drafts) |
| `--no-fast-attn` | src/program/generate.cpp |  |  |
| `--no-fast-select` | src/program/generate.cpp |  |  |
| `--no-fused-gdn` | src/program/generate.cpp |  |  |
| `--no-fused-gr` | src/program/generate.cpp |  | A/B: the six-kernel hyper-connection read and a separate write (native) |
| `--no-hit-poke` | src/program/generate.cpp |  | R4.2d's A/B arm.  The hit path pokes the driver once right after its |
| `--no-host-worker` | src/program/generate.cpp |  | R2.2: the A/B arm.  By default the HOST THREAD joins the drain, so the |
| `--no-kv-grow` | src/program/generate.cpp |  |  |
| `--no-ple` | src/program/generate.cpp |  | explicit diagnostic ablation of the PLE layer |
| `--no-ple-prefetch` | src/program/generate.cpp |  | A/B arm: read the PLE table's sixteen rows one at a time, instead of |
| `--no-pool` | src/program/generate.cpp |  | skip the CPU expert pool (the GPU-only floor) |
| `--no-prefill-borrow` | src/program/generate.cpp |  |  |
| `--no-publish-kernel` | src/program/generate.cpp |  |  |
| `--no-spec-split` | src/program/generate.cpp |  |  |
| `--no-split-rows` | src/program/generate.cpp |  |  |
| `--no-token-graph` | src/program/generate.cpp |  | A/B: two graphs per layer (the host launches each) instead of one per token |
| `--pack` | src/program/generate.cpp |  | the pack directory (default pack/full) |
| `--pcie-frac` | src/program/generate.cpp |  |  |
| `--pcie-mode` | src/program/generate.cpp |  |  |
| `--peer-adapt-swaps` | src/program/generate.cpp |  | peer cache swaps per adaptation step (default: --adapt-swaps) |
| `--peer-device` | src/program/generate.cpp |  | a second GPU as an adaptive expert-cache tier (rows over P2P; it also |
| `--peer-prefill-rows` | src/program/generate.cpp |  | prompt rows per layer the peer computes (default half of chunk x top-k; |
| `--peer-reserve-mib` | src/program/generate.cpp |  | VRAM the peer tier leaves free on its card (default 600) |
| `--peer-slots` | src/program/generate.cpp |  | expert slots on the peer (default: what fits) |
| `--pipeline-windows` | src/program/generate.cpp |  |  |
| `--ple-delay-us` | src/program/generate.cpp |  | fault injection: each row read completes no earlier than U us |
| `--ple-gguf` | src/program/generate.cpp |  | the n-gram/PLE shard.  WITHOUT IT LAYER 1's PLE IS SILENTLY SKIPPED, |
| `--ple-inflight` | src/program/generate.cpp |  | outstanding SSD reads (default 256) |
| `--ple-io` | src/program/generate.cpp |  |  |
| `--ple-row-cache` | src/program/generate.cpp |  | bounded cache of fetched rows, 90 B each (default 1048576; 0 = off) |
| `--ple-sync-submit` | src/program/generate.cpp |  | A/B arm: submit table reads on the token thread (default: an I/O thread) |
| `--pool-affinity` | src/program/generate.cpp |  |  |
| `--pool-tasks` | src/program/generate.cpp |  | Batched CPU expert tasks per GU/Down phase (0..4096). Default 0 = |
| `--pool-workers` | src/program/generate.cpp |  | R2.2: CPU expert pool worker count.  Default 0 = every physical core |
| `--prefill` | src/program/generate.cpp |  | batched prompt processing in chunks of CHUNK tokens (needs --native); auto = |
| `--prefill-until` | src/program/generate.cpp |  |  |
| `--prompt-cache` | src/program/generate.cpp |  | --serve: keep N conversation checkpoints between requests (default 6, ~118 MB |
| `--prompt-cache-every` | src/program/generate.cpp |  | --serve: also checkpoint every N fresh prompt tokens (default 16384, 0 = off) |
| `--prompt-cache-root` | src/program/generate.cpp |  |  |
| `--prompt-cache-tail` | src/program/generate.cpp |  | --serve, single GPU: one extra checkpoint near the prompt's end, at an existing |
| `--remote-expert-opt` | src/program/generate.cpp |  | enable remote-expert decode optimizations (serve mode) |
| `--resident-budget-gib` | src/program/generate.cpp |  |  |
| `--resident-cpu-experts` | src/program/generate.cpp |  | with mmap and a static profile, keep the experts the GPU cache does not |
| `--resident-experts` | src/program/generate.cpp |  | the low-RAM PC's resident mode (setup): --mmap-experts --resident-cpu-experts |
| `--rope-freq-base` | src/program/generate.cpp |  | the raw ggml knobs: the frequency base (0 = the model's 1e7) and |
| `--rope-freq-scale` | src/program/generate.cpp |  | the angle shrink (0 = 1/--rope-scale) |
| `--rope-scale` | src/program/generate.cpp |  | the extension factor for linear/yarn (default: the model file's |
| `--rope-scaling` | src/program/generate.cpp |  | extend the context past the trained one: none, linear |
| `--seed` | src/program/generate.cpp |  | enable sampling with this Philox seed |
| `--serve` | src/program/generate.cpp |  |  |
| `--session-min-free-mib` | src/program/generate.cpp |  | --serve: disk space a SAVE must leave free (default 4096; 0 = no check) |
| `--shared-expert-arena` | src/program/generate.cpp |  | Linux: back the resident arena with one MAP_SHARED file. |
| `--shared-late` | src/program/generate.cpp |  | A/B: shared expert after the CPU pool (default: overlapped with it) |
| `--short-read` | src/program/generate.cpp |  | --serve: read at most N fresh text tokens through the decode windows instead |
| `--slots` | src/program/generate.cpp |  |  |
| `--spec` | src/program/generate.cpp |  | the MTP drafter's verify window: how many tokens it proposes per check (setup |
| `--spec-corrupt` | src/program/generate.cpp |  |  |
| `--spec-follow` | src/program/generate.cpp |  | benchmarks: emit this continuation (token ids) instead of the argmax and |
| `--spec-min-p` | src/program/generate.cpp |  | how sure the draft layer must be to extend a verify window by another guess |
| `--spec-oracle` | src/program/generate.cpp |  |  |
| `--spec-split` | src/program/generate.cpp |  |  |
| `--split-device` | src/program/generate.cpp |  |  |
| `--split-skip-if-fits` | src/program/generate.cpp |  |  |
| `--stage-timing` | src/program/generate.cpp |  | per-stage KERNEL-COUNT shares.  NOT a time profile: an uncaptured |
| `--stats` | src/program/generate.cpp |  | print the per-stage breakdown |
| `--stop-eos` | src/program/generate.cpp |  |  |
| `--stream-token` | src/program/generate.cpp |  | enqueue token work on the session stream (experimental) |
| `--suffix-draft` | src/program/generate.cpp |  | prompt lookup: draft from an earlier repeat of the last N+ tokens of context |
| `--sync-every-layer` | src/program/generate.cpp |  | debug: synchronise after every layer |
| `--tail-role-token` | src/program/generate.cpp |  |  |
| `--temperature` | src/program/generate.cpp |  |  |
| `--tokens` | src/program/generate.cpp |  | the prompt as comma-separated token IDS (required) |
| `--tokens-file` | src/program/generate.cpp |  | pretokenized prompt, commas or whitespace (alternative to --tokens) |
| `--top-k` | src/program/generate.cpp |  |  |
| `--top-p` | src/program/generate.cpp |  |  |
| `--trim-stage-weights` | src/program/generate.cpp |  |  |
| `--turn-token` | src/program/generate.cpp |  | --serve: the token that opens a chat turn (default 248045, <|im_start|>) |
| `--vision` | src/program/generate.cpp |  | --serve takes images too (GENI requests; embeddings from strata-vision) |
| `--vram-elastic` | src/program/generate.cpp |  | --serve (#533, opt-in, NVIDIA): the expert cache in segments (--vram-segment-mib, |
| `--vram-reserve-later-mib` | src/program/generate.cpp |  |  |
| `--vram-reserve-mib` | src/program/generate.cpp |  |  |
| `--vram-segment-mib` | src/program/generate.cpp |  |  |
| `--window-hashes` | src/program/generate.cpp |  |  |
| `--yarn-attn-factor` | src/program/generate.cpp |  |  |
| `--yarn-beta-fast` | src/program/generate.cpp |  |  |
| `--yarn-beta-slow` | src/program/generate.cpp |  |  |
| `--yarn-ext-factor` | src/program/generate.cpp |  |  |
| `--yarn-orig-ctx` | src/program/generate.cpp |  | the trained context the correction targets (0 = 262144) |

## env (342)

| name | source | line | description |
|---|---|---|---|
| `BATCH_TEST_LOG` | tools/batch_test.py | 49 |  |
| `CUDA_DEVICE_ORDER` | serve/server.py | 2281 |  |
| `CUDA_LAUNCH_BLOCKING` | src/program/generate.cpp | 1191 |  |
| `CUDA_MODULE_LOADING` | src/program/generate.cpp | 1586 |  |
| `FAKE_MCP_LOG` | serve/mcp_fake_server.py | 37 |  |
| `GPU_MAX_HW_QUEUES` | src/core/verify.cpp | 576 |  |
| `HF_ENDPOINT` | tools/mtp_fetch.py | 35 |  |
| `HIP_HOST_COHERENT` | src/core/verify.cpp | 574 |  |
| `HIP_PATH` | serve/test_server.py | 1714 |  |
| `HSA_ENABLE_SDMA` | src/core/verify.cpp | 575 |  |
| `MODELSCOPE_ENDPOINT` | tools/mtp_fetch.py | 42 |  |
| `P` | serve/telemetry.py | 38 |  |
| `PROF` | tools/batch_test.py | 95 |  |
| `QA_DUMP` | src/kernels/qsa_prompt_attn_parity.cpp | 153 |  |
| `QA_LAYER` | src/kernels/qsa_prompt_attn_parity.cpp | 154 |  |
| `QA_SAME` | src/kernels/qsa_prompt_attn_parity.cpp | 130 |  |
| `ROCM_PATH` | tools/test_setup_amd.py | 111 |  |
| `S` | serve/server.py | 1830 |  |
| `STRATA_ADAPT_JOB_CPU` | src/program/generate.cpp | 1323 |  |
| `STRATA_ADAPT_LAG` | src/program/generate.cpp | 1267 |  |
| `STRATA_ADAPT_NOWAIT` | src/program/generate.cpp | 1257 |  |
| `STRATA_ALLOWED_HOSTS` | serve/server.py | 5764 |  |
| `STRATA_API_KEY` | serve/server.py | 5631 |  |
| `STRATA_ARENA_LOCK` | src/core/pinned.cu | 414 |  |
| `STRATA_ARENA_MMAP` | src/core/expert_source.cpp | 3895 |  |
| `STRATA_ARENA_PIN_GIB` | src/core/pinned.cu | 300 |  |
| `STRATA_ARENA_RELEASE` | src/program/generate.cpp | 5605 |  |
| `STRATA_ARGMAX_MULTI` | src/kernels/cuda/sampler.cu | 1256 |  |
| `STRATA_ATTN_LANECELL` | src/kernels/cuda/qsa_decode_attn.cu | 548 |  |
| `STRATA_ATTN_PRE75` | src/kernels/cuda/qsa_decode_attn.cu | 490 |  |
| `STRATA_BATCH_DECODE_SHARE` | src/program/generate.cpp | 9706 |  |
| `STRATA_BATCH_MTP` | src/program/generate.cpp | 3878 |  |
| `STRATA_BATCH_TRACE` | serve/server.py | 554 |  |
| `STRATA_BF16_TC` | src/prefill/gemm.cu | 545 |  |
| `STRATA_BF16_TC_CACHE` | src/prefill/gemm.cu | 574 |  |
| `STRATA_BF16_TC_CACHE_MIB` | src/prefill/gemm.cu | 576 |  |
| `STRATA_CACHE_MESSAGE_BOUNDARY` | src/program/generate.cpp | 9858 |  |
| `STRATA_CKPT_REREAD` | src/program/generate.cpp | 9351 |  |
| `STRATA_COMMIT_SYNC` | src/core/verify.cpp | 2259 |  |
| `STRATA_CPU_YMM` | src/kernels/cpu/expert.cpp | 151 |  |
| `STRATA_CVEC_FUSE` | src/prefill/prefill.cpp | 340 |  |
| `STRATA_CVEC_FUSE_CHECK` | src/prefill/prefill.cpp | 3845 |  |
| `STRATA_DBG_CPU_GATE` | src/prefill/prefill.cpp | 3049 |  |
| `STRATA_DBG_FEAT` | src/prefill/prefill.cpp | 2800 |  |
| `STRATA_DBG_FEAT_LAYERS` | src/prefill/prefill.cpp | 2806 |  |
| `STRATA_DBG_FORCE_SLOW_LAYER` | src/prefill/prefill.cpp | 2895 |  |
| `STRATA_DBG_GDN` | src/kernels/cuda/verify_kernels.cu | 944 |  |
| `STRATA_DBG_NAN` | src/core/verify.cpp | 2108 |  |
| `STRATA_DBG_ROUTE_OVERRIDE` | src/prefill/prefill.cpp | 2801 |  |
| `STRATA_DEBUG` | serve/mcp.py | 131 |  |
| `STRATA_DECODE_TIMING` | src/program/generate.cpp | 9985 |  |
| `STRATA_DEC_BATCH` | src/core/expert_source.cpp | 3267 |  |
| `STRATA_DEFERRED_REGISTER` | src/core/expert_source.cpp | 3977 |  |
| `STRATA_DENSE_MMQ` | src/prefill/gemm.cu | 844 |  |
| `STRATA_DF_BRANCH` | src/core/verify.cpp | 619 |  |
| `STRATA_DF_PDL` | src/kernels/pdl_parity.cpp | 252 |  |
| `STRATA_DF_PLE` | src/core/verify.cpp | 875 |  |
| `STRATA_DF_QB_Q4` | src/core/verify.cpp | 1077 |  |
| `STRATA_DISJOINT_ADAPT` | src/program/generate.cpp | 4953 |  |
| `STRATA_DMA_BATCH` | include/strata/core/dma_batch.hpp | 32 |  |
| `STRATA_DRAFT_TIMING` | src/prefill/prefill.cpp | 1345 |  |
| `STRATA_DUMP_FIRST_LOGITS` | src/program/generate.cpp | 10705 |  |
| `STRATA_EARLY_REMOTE_CONTEXTS` | src/program/generate.cpp | 2440 |  |
| `STRATA_EMB_REUSE_ACCOUNT` | src/prefill/prefill.cpp | 257 |  |
| `STRATA_EMULATE_CC` | include/strata/core/emulate.hpp | 17 |  |
| `STRATA_EXCHANGE_ROTATE` | src/core/expert_source.cpp | 2765 |  |
| `STRATA_EXPERT_V2` | src/kernels/cuda/iq_kernels.cu | 3484 |  |
| `STRATA_EXPERT_V2K` | src/kernels/cuda/iq_kernels.cu | 3498 |  |
| `STRATA_EXP_MODE` | src/kernels/cuda/iq_kernels.cu | 3432 |  |
| `STRATA_FETCH_PVM` | src/core/expert_source.cpp | 1424 |  |
| `STRATA_FETCH_THREADS` | src/program/generate.cpp | 4162 |  |
| `STRATA_FILE_RELEASE` | src/core/expert_source.cpp | 2133 |  |
| `STRATA_FILL_AHEAD` | src/program/generate.cpp | 4672 |  |
| `STRATA_FORCE_AVX2` | src/kernels/cpu/expert_layout.cpp | 43 |  |
| `STRATA_FORCE_ISA` | src/kernels/cpu/expert_layout.cpp | 29 |  |
| `STRATA_FS_AHEAD` | src/program/generate.cpp | 4976 |  |
| `STRATA_FS_SLOTS` | src/core/expert_source.cpp | 4394 |  |
| `STRATA_FUSED_SWIGLU_Q81` | src/kernels/cuda/shared_expert.cu | 207 |  |
| `STRATA_FUSE_HEAD_GR` | src/core/mtp.cpp | 903 |  |
| `STRATA_GDN_CHUNKED` | src/prefill/gdn_rec_parity.cu | 567 |  |
| `STRATA_GDN_COMMIT_SPLIT` | src/kernels/cuda/verify_kernels.cu | 940 |  |
| `STRATA_GDN_CONVL2` | src/prefill/kernels.cu | 1912 |  |
| `STRATA_GDN_CONV_SERIAL` | src/prefill/kernels.cu | 1908 |  |
| `STRATA_GDN_HEAD` | src/prefill/kernels.cu | 2001 |  |
| `STRATA_GDN_KEYHEAD` | src/prefill/kernels.cu | 697 |  |
| `STRATA_GDN_NOY` | src/prefill/kernels.cu | 1960 |  |
| `STRATA_GDN_PIPELINE` | src/prefill/kernels.cu | 1978 |  |
| `STRATA_GDN_PP` | src/prefill/kernels.cu | 1953 |  |
| `STRATA_GDN_REC_HEADS` | src/prefill/kernels.cu | 1974 |  |
| `STRATA_GDN_SPLIT` | src/kernels/cuda/verify_kernels.cu | 921 |  |
| `STRATA_GFX1151_DEFAULTS` | src/core/arch_defaults.cpp | 15 |  |
| `STRATA_GGUF_PY` | tools/_paths.py | 16 |  |
| `STRATA_GROUPED_PAIR_MIN_HITS` | src/kernels/cuda/s2_expert_grouped.cu | 540 |  |
| `STRATA_GROUP_COPY` | src/prefill/prefill.cpp | 1068 |  |
| `STRATA_GR_DOWN_MAX4` | src/kernels/cuda/fused_gr.cu | 861 |  |
| `STRATA_GR_FAST` | src/kernels/cuda/fused_gr.cu | 1635 |  |
| `STRATA_GR_SPLIT` | src/kernels/cuda/fused_gr.cu | 1754 |  |
| `STRATA_GR_UNFUSED` | src/prefill/prefill.cpp | 357 |  |
| `STRATA_GR_V3` | src/kernels/gr_parity.cpp | 342 |  |
| `STRATA_HCD_EXACT` | src/prefill/prefill.cpp | 335 |  |
| `STRATA_HC_Q8` | src/core/native_dense.cpp | 42 |  |
| `STRATA_HC_Q8_INJECT` | src/core/native_dense.cpp | 327 |  |
| `STRATA_HC_SPLIT` | src/kernels/cuda/fused_gr.cu | 942 |  |
| `STRATA_HC_UPMIX` | src/prefill/prefill.cpp | 317 |  |
| `STRATA_HC_UPMIX_CHECK` | src/prefill/prefill.cpp | 2495 |  |
| `STRATA_HEAD_MIX_MULTI` | src/core/mtp.cpp | 910 |  |
| `STRATA_HIPBLASLT_TUNING` | src/prefill/gemm.cu | 195 |  |
| `STRATA_HIPBLASLT_VERBOSE` | src/prefill/gemm.cu | 150 |  |
| `STRATA_HIP_ADAPT_KERNEL_COPY` | src/program/generate.cpp | 169 |  |
| `STRATA_HIP_PROMPT_F16` | src/prefill/gemm.cu | 367 |  |
| `STRATA_HIP_ROUTER_FAST` | src/kernels/cuda/router_top10.cu | 429 |  |
| `STRATA_HIP_ROUTER_OLD` | src/kernels/cuda/router_top10.cu | 431 |  |
| `STRATA_HIP_WMMA` | src/prefill/prefill.cpp | 276 |  |
| `STRATA_HOST_CORE` | src/program/generate.cpp | 1964 |  |
| `STRATA_HTTP_BACKLOG` | serve/server.py | 5220 |  |
| `STRATA_IDX_FP16_CHECK` | src/prefill/prefill.cpp | 2701 |  |
| `STRATA_INDEXER_PER_TOKEN` | src/prefill/prefill.cpp | 2646 |  |
| `STRATA_IO_PF_AHEAD` | src/core/expert_source.cpp | 582 |  |
| `STRATA_IO_PF_STAGE` | src/core/expert_source.cpp | 584 |  |
| `STRATA_IO_PF_THREADS` | src/program/generate.cpp | 4189 |  |
| `STRATA_IO_PREFETCH` | src/program/generate.cpp | 4188 |  |
| `STRATA_IO_PREFETCH_DEPTH` | src/program/generate.cpp | 4992 |  |
| `STRATA_IO_STATS` | src/program/generate.cpp | 4215 |  |
| `STRATA_IO_THREADS` | src/platform/direct_file.cpp | 63 |  |
| `STRATA_IQ256_GATHER` | src/kernels/cpu/expert_layout.cpp | 204 |  |
| `STRATA_IQ3S_MT1` | src/kernels/cpu/native_expert.cpp | 120 |  |
| `STRATA_IQ_GATHER` | src/kernels/cpu/iq_avx512.cpp | 33 |  |
| `STRATA_IQ_MT_MIN` | src/kernels/native_expert_parity.cpp | 538 |  |
| `STRATA_IQ_PREFETCH` | src/kernels/cpu/iq_avx2.cpp | 185 |  |
| `STRATA_IQ_STAGE_GRID` | src/kernels/cuda/iq_kernels.cu | 1976 |  |
| `STRATA_IQ_STAGE_GRID_MMVQ` | src/kernels/cuda/iq_kernels.cu | 1983 |  |
| `STRATA_KEEP_EMPTY_TURNS` | serve/frontend.py | 60 |  |
| `STRATA_KEEP_MAPPING` | src/program/generate.cpp | 6202 |  |
| `STRATA_KEY` | tools/early_close_test.py | 9 |  |
| `STRATA_KQ256` | src/kernels/cpu/native_expert.cpp | 145 |  |
| `STRATA_KV_GROW` | src/program/generate.cpp | 3800 |  |
| `STRATA_KV_GROW_FLOOR` | src/program/generate.cpp | 5889 |  |
| `STRATA_KV_GROW_HOLD` | src/program/generate.cpp | 9330 |  |
| `STRATA_KV_GROW_INIT` | src/program/generate.cpp | 3812 |  |
| `STRATA_KV_GROW_STEP` | src/program/generate.cpp | 5887 |  |
| `STRATA_KV_HOST_DMA` | src/prefill/prefill.cpp | 2596 |  |
| `STRATA_KV_MAIN_OFF` | src/core/layer.cpp | 642 |  |
| `STRATA_KV_PREFETCH` | src/prefill/prefill.cpp | 1986 |  |
| `STRATA_KV_RING_OFF` | src/core/layer.cpp | 641 |  |
| `STRATA_KV_ROT` | src/program/generate.cpp | 2179 |  |
| `STRATA_KV_STAGE_OWN` | src/prefill/prefill.cpp | 807 |  |
| `STRATA_LAYER_SPLIT_GATE` | src/program/generate.cpp | 3526 |  |
| `STRATA_LAYER_SPLIT_PROBE` | src/program/generate.cpp | 4795 |  |
| `STRATA_LFUSE` | src/core/verify.cpp | 66 |  |
| `STRATA_LFUSE_GATE` | src/core/verify.cpp | 101 |  |
| `STRATA_LFUSE_PAIR` | src/core/verify.cpp | 102 |  |
| `STRATA_LOGPOS` | src/program/generate.cpp | 9534 |  |
| `STRATA_LOGPOS_EXTRA` | src/program/generate.cpp | 9566 |  |
| `STRATA_LOGPOS_TOPK` | src/core/verify.cpp | 2241 |  |
| `STRATA_LOOKAHEAD` | src/program/generate.cpp | 4978 |  |
| `STRATA_LOOKAHEAD_K` | src/program/generate.cpp | 4989 |  |
| `STRATA_LOOKUP_CHAIN_FIXED` | src/program/generate.cpp | 9976 |  |
| `STRATA_MAX_BODY_MIB` | serve/server.py | 4187 |  |
| `STRATA_MMQ_RESIDENT_SORT_NE` | src/prefill/mmq_resident_sort.hpp | 17 |  |
| `STRATA_MMVF_ROWS` | src/kernels/cuda/native_bf16.cu | 272 |  |
| `STRATA_MMVQ_IL` | src/core/verify.cpp | 107 |  |
| `STRATA_MMVQ_IL_ROWS` | src/kernels/cuda/native_mmvq.cu | 2534 |  |
| `STRATA_MMVQ_WAVE` | src/kernels/mmvq_multi_parity.cpp | 245 |  |
| `STRATA_MTP_BATCH` | src/prefill/prefill.cpp | 1277 |  |
| `STRATA_MTP_BATCH_F16` | src/prefill/prefill.cpp | 1314 |  |
| `STRATA_MTP_BATCH_RING` | src/prefill/prefill.cpp | 1282 |  |
| `STRATA_MTP_CATCHUP_ALL` | src/core/mtp.cpp | 62 |  |
| `STRATA_MTP_FULL_HEAD` | src/core/mtp.cpp | 508 |  |
| `STRATA_MTP_PREFILL_SYNC` | src/core/mtp.cpp | 1217 |  |
| `STRATA_MTP_PRIORITY` | src/core/mtp.cpp | 471 |  |
| `STRATA_MTP_REVISION` | tools/mtp_fetch.py | 33 |  |
| `STRATA_MTP_SHARED_BRANCH` | src/core/mtp.cpp | 920 |  |
| `STRATA_MTP_TOP2` | src/core/mtp.cpp | 514 |  |
| `STRATA_MULTI_BLOCK_ARGMAX` | src/kernels/cuda/verify_kernels.cu | 828 |  |
| `STRATA_NORM_ROPE` | src/kernels/cuda/native_rope.cu | 180 |  |
| `STRATA_NO_ARENA_THP` | src/core/pinned.cu | 256 |  |
| `STRATA_NO_AVXVNNI` | src/kernels/cpu/expert_layout.cpp | 254 |  |
| `STRATA_NO_BATCH_KV_STEP` | src/core/mtp.cpp | 785 |  |
| `STRATA_NO_IQ256` | src/program/generate.cpp | 2479 |  |
| `STRATA_NO_IQ4NL` | src/kernels/cpu/native_expert.cpp | 182 |  |
| `STRATA_NO_IQ512` | src/kernels/cpu/native_expert.cpp | 132 |  |
| `STRATA_NO_LARGEPAGES` | src/core/pinned.cu | 89 |  |
| `STRATA_NO_MMVQ_ROWS2` | src/kernels/cuda/native_mmvq.cu | 1279 |  |
| `STRATA_NO_MULTI_GR` | src/core/mtp.cpp | 976 |  |
| `STRATA_NO_NORM_ROPE` | src/kernels/cuda/native_rope.cu | 177 |  |
| `STRATA_NO_Q8K_AVX2` | src/kernels/cpu/native_expert.cpp | 91 |  |
| `STRATA_OLD_GROUPED` | src/kernels/cuda/s2_expert_grouped.cu | 527 |  |
| `STRATA_ONE_TOKEN_COMMIT` | src/core/verify.cpp | 178 |  |
| `STRATA_OWNED_PRICE` | src/program/generate.cpp | 4309 |  |
| `STRATA_PARALLEL_SOLO` | serve/server.py | 1166 |  |
| `STRATA_PARTIAL_PIN` | src/core/expert_source.cpp | 2465 |  |
| `STRATA_PARTIAL_PIN_GIB` | src/core/expert_source.cpp | 2471 |  |
| `STRATA_PA_FAST` | src/kernels/cuda/qsa_prompt_attn.cu | 1431 |  |
| `STRATA_PEER_DIRECT` | src/core/peer_experts.cpp | 189 |  |
| `STRATA_PEER_HOT` | src/program/generate.cpp | 3157 |  |
| `STRATA_PEER_HOT_AT` | src/program/generate.cpp | 3159 |  |
| `STRATA_PEER_NO_P2P` | src/core/peer_experts.cpp | 101 |  |
| `STRATA_PF_BK64` | src/prefill/wmma_gemm.cu | 693 |  |
| `STRATA_PF_FUSED` | src/prefill/moe_fused.cu | 657 |  |
| `STRATA_PF_FUSED_KQ` | src/prefill/moe_fused_iq.cu | 991 |  |
| `STRATA_PF_FUSED_NATIVE` | src/prefill/moe_fused_iq.cu | 1040 |  |
| `STRATA_PF_FUSED_TILE` | src/prefill/moe_fused_iq.cu | 1027 |  |
| `STRATA_PF_GEMM` | src/prefill/gemm.cu | 812 |  |
| `STRATA_PF_HCDOWN` | src/prefill/prefill.cpp | 327 |  |
| `STRATA_PF_OCC` | src/prefill/moe_fused.cu | 588 |  |
| `STRATA_PF_PAD` | src/prefill/gemm.cu | 933 |  |
| `STRATA_PF_PEER_COMPACT` | src/prefill/prefill.cpp | 1618 |  |
| `STRATA_PF_PEER_F16` | src/prefill/prefill.cpp | 1663 |  |
| `STRATA_PF_PEER_GATHER` | src/prefill/prefill.cpp | 1666 |  |
| `STRATA_PF_PEER_HOST` | src/prefill/prefill.cpp | 1575 |  |
| `STRATA_PF_PEER_OUT_PIPE` | src/prefill/prefill.cpp | 1602 |  |
| `STRATA_PF_PEER_RING` | src/prefill/prefill.cpp | 1636 |  |
| `STRATA_PF_PEER_STREAM` | src/prefill/prefill.cpp | 1632 |  |
| `STRATA_PF_PEER_SUMS` | src/prefill/prefill.cpp | 1659 |  |
| `STRATA_PF_PEER_XSTREAM` | src/prefill/prefill.cpp | 1587 |  |
| `STRATA_PF_STEP_SYNC` | src/prefill/prefill.cpp | 2388 |  |
| `STRATA_PF_SWITCH_MIN_T` | src/prefill/gemm.cu | 813 |  |
| `STRATA_PIN_GUARD` | src/core/expert_source.cpp | 2384 |  |
| `STRATA_PIN_RESERVE_GIB` | src/core/expert_source.cpp | 2377 |  |
| `STRATA_PIPELINE_ADAPT_ASYNC` | src/program/generate.cpp | 6091 |  |
| `STRATA_PIPELINE_DEBUG` | src/program/generate.cpp | 242 |  |
| `STRATA_PLE_BATCH` | src/core/verify.cpp | 831 |  |
| `STRATA_PLE_GGUF` | src/kernels/ple_parity.cpp | 257 |  |
| `STRATA_POOL_SPIN_US` | src/kernels/cpu/pool.cpp | 439 |  |
| `STRATA_POOL_TRACE` | src/core/expert_source.cpp | 3128 |  |
| `STRATA_PREFILL_AUTO_MAX` | src/program/generate.cpp | 1773 |  |
| `STRATA_PREFILL_BF16X2` | src/prefill/prefill.cpp | 303 |  |
| `STRATA_PREFILL_CPU_SHARE` | src/prefill/prefill.cpp | 165 |  |
| `STRATA_PREFILL_CPU_SHARE_MAX` | src/prefill/prefill.cpp | 182 |  |
| `STRATA_PREFILL_DUMP_R` | src/prefill/prefill.cpp | 3921 |  |
| `STRATA_PREFILL_DUMP_R_ALL` | src/prefill/prefill.cpp | 3934 |  |
| `STRATA_PREFILL_EQUAL` | src/program/generate.cpp | 5744 |  |
| `STRATA_PREFILL_GROUP_GATHER` | src/prefill/prefill.cpp | 3598 |  |
| `STRATA_PREFILL_HELP` | src/prefill/prefill.cpp | 1444 |  |
| `STRATA_PREFILL_HELP_FRAC` | src/prefill/prefill.cpp | 1456 |  |
| `STRATA_PREFILL_ISSUER` | src/prefill/prefill.cpp | 2322 |  |
| `STRATA_PREFILL_LEND_PCT` | src/program/generate.cpp | 3383 |  |
| `STRATA_PREFILL_MMQ` | src/prefill/prefill.cpp | 926 |  |
| `STRATA_PREFILL_RING` | src/prefill/prefill.cpp | 271 |  |
| `STRATA_PREFILL_STREAM_AHEAD` | src/prefill/prefill.cpp | 106 |  |
| `STRATA_PREFILL_STREAM_MIN` | src/prefill/prefill.cpp | 144 |  |
| `STRATA_PREFILL_TIMING` | src/prefill/prefill.cpp | 1895 |  |
| `STRATA_PROMPT_ATTN_OLD` | src/prefill/prefill.cpp | 2769 |  |
| `STRATA_PROMPT_ATTN_Q4` | src/kernels/cuda/qsa_prompt_attn.cu | 1498 |  |
| `STRATA_PROMPT_ATTN_V1` | src/kernels/cuda/qsa_prompt_attn.cu | 1515 |  |
| `STRATA_Q2_BITPLANE` | src/kernels/cpu/q2_avx2.cpp | 147 |  |
| `STRATA_Q6P_GRID` | src/kernels/cuda/native_mmvq.cu | 1778 |  |
| `STRATA_Q6P_SELFTEST` | src/kernels/cuda/native_mmvq.cu | 1976 |  |
| `STRATA_Q6_PACKED` | src/kernels/cuda/native_mmvq.cu | 1938 |  |
| `STRATA_Q8_PACKED` | src/kernels/cuda/native_mmvq.cu | 1903 |  |
| `STRATA_QFUSE` | src/core/arch_defaults_test.cpp | 52 |  |
| `STRATA_QSA_CLUSTER` | src/kernels/cuda/qsa_select.cu | 1305 |  |
| `STRATA_QSA_DUMP` | src/prefill/prefill.cpp | 2747 |  |
| `STRATA_QSA_DUMP_LAST` | src/prefill/prefill.cpp | 2748 |  |
| `STRATA_QSA_EARLY_EXIT` | src/kernels/cuda/qsa_select.cu | 1103 |  |
| `STRATA_QSA_WARP` | src/kernels/cuda/qsa_prompt_attn.cu | 1475 |  |
| `STRATA_READ_AHEAD` | src/platform/memory.cpp | 152 |  |
| `STRATA_REFILL_BLOCKING` | src/program/generate.cpp | 233 |  |
| `STRATA_REFILL_SERIAL` | src/program/generate.cpp | 9623 |  |
| `STRATA_REMOTE_SPIN` | src/core/remote_experts.cpp | 78 |  |
| `STRATA_REMOTE_ZEROCOPY` | src/core/remote_experts.cpp | 209 |  |
| `STRATA_REQUEST_LINES` | serve/server.py | 636 |  |
| `STRATA_RESIDENT_HEADROOM_GIB` | src/program/generate.cpp | 1920 |  |
| `STRATA_RESIDENT_PIN` | src/program/generate.cpp | 1918 |  |
| `STRATA_RING_BYTES` | src/prefill/prefill.cpp | 261 |  |
| `STRATA_ROPE_TABLE` | src/kernels/cuda/native_rope.cu | 154 |  |
| `STRATA_ROUTER_BLOCK` | src/kernels/cuda/router_top10.cu | 462 |  |
| `STRATA_ROUTE_PER_TOKEN` | src/core/layer.cpp | 399 |  |
| `STRATA_ROUTE_PROJ_PER_TOKEN` | src/core/layer.cpp | 411 |  |
| `STRATA_ROUTE_RESIDENT` | src/core/verify.cpp | 95 |  |
| `STRATA_ROUTE_RESIDENT_RANKS` | src/core/verify.cpp | 96 |  |
| `STRATA_RSS_TRACE` | src/program/generate.cpp | 219 |  |
| `STRATA_S2_SWIGLU_Q8` | src/kernels/cuda/s2_expert_grouped.cu | 1155 |  |
| `STRATA_SCORES_MULTI` | src/kernels/cuda/qsa_select.cu | 1100 |  |
| `STRATA_SELECT_OLD` | src/prefill/prefill.cpp | 2668 |  |
| `STRATA_SELECT_SIMT` | src/kernels/cuda/qsa_select.cu | 1159 |  |
| `STRATA_SELECT_WMMA` | src/kernels/cuda/qsa_select.cu | 1126 |  |
| `STRATA_SEL_OVERLAP` | src/prefill/prefill.cpp | 2679 |  |
| `STRATA_SESSION_BUFFERED` | src/core/conversation_file.cpp | 340 |  |
| `STRATA_SESSION_GOLDEN_PRINT` | src/core/conversation_file_test.cpp | 179 |  |
| `STRATA_SHARD1` | tools/canonical_xcheck.py | 46 |  |
| `STRATA_SH_FORK_LATE` | src/core/verify.cpp | 1277 |  |
| `STRATA_SH_STREAM` | src/core/verify.cpp | 146 |  |
| `STRATA_SKIP_SHA256` | tools/test_setup_engine_hash.py | 239 |  |
| `STRATA_SM70_TABLE` | src/kernels/cuda/fused_gr.cu | 1641 |  |
| `STRATA_SNAPSHOT_FULL_CAPTURE` | src/program/generate.cpp | 9302 |  |
| `STRATA_SNAPSHOT_VERIFY` | src/program/generate.cpp | 7312 |  |
| `STRATA_SOURCE` | tools/mtp_fetch.py | 41 |  |
| `STRATA_SPEC_COUPLED` | include/strata/core/coupled_draft.hpp | 59 |  |
| `STRATA_SPEC_DEPTH` | src/program/generate.cpp | 11115 |  |
| `STRATA_SPEC_MIN_TEMP` | include/strata/core/spec_prob.hpp | 69 |  |
| `STRATA_SPEC_PROB` | include/strata/core/coupled_draft.hpp | 69 |  |
| `STRATA_SPEC_PROB_DT` | include/strata/core/spec_prob.hpp | 57 |  |
| `STRATA_SPEC_PROB_GATE` | include/strata/core/spec_prob.hpp | 47 |  |
| `STRATA_SPLIT_COVER_B` | src/program/generate.cpp | 3361 |  |
| `STRATA_SPLIT_MISS_MS` | src/program/generate.cpp | 3335 |  |
| `STRATA_SPLIT_OWN` | src/program/generate.cpp | 2079 |  |
| `STRATA_SPLIT_OWN_BUFFERS` | src/program/generate.cpp | 6441 |  |
| `STRATA_SPLIT_OWN_PLACE` | src/program/generate.cpp | 3282 |  |
| `STRATA_SPLIT_RING` | src/program/generate.cpp | 6279 |  |
| `STRATA_SPLIT_SMALL_MAX` | src/program/generate.cpp | 6634 |  |
| `STRATA_SPLIT_SMALL_OWN` | src/program/generate.cpp | 6632 |  |
| `STRATA_SPLIT_TIMING` | src/program/generate.cpp | 11086 |  |
| `STRATA_SSD_KEEPALIVE` | src/program/generate.cpp | 2856 |  |
| `STRATA_SSD_KEEPALIVE_WINDOW` | src/program/generate.cpp | 2857 |  |
| `STRATA_STAGER_BATCH` | src/prefill/prefill.cpp | 1057 |  |
| `STRATA_STAGER_RING` | src/prefill/prefill.cpp | 429 |  |
| `STRATA_STAGER_SLEEP` | src/prefill/prefill.cpp | 126 |  |
| `STRATA_STAGER_SSD` | src/prefill/prefill.cpp | 1045 |  |
| `STRATA_STAGER_THREADS` | src/prefill/prefill.cpp | 1033 |  |
| `STRATA_STAGE_PIN` | src/core/expert_source.cpp | 1196 |  |
| `STRATA_STAGE_TRIM` | src/program/generate.cpp | 2631 |  |
| `STRATA_STATE_HASH` | src/program/generate.cpp | 10820 |  |
| `STRATA_STATE_HASH_GDN` | src/prefill/prefill.cpp | 4042 |  |
| `STRATA_TEST_CACHE_FAIL` | src/program/generate.cpp | 4567 |  |
| `STRATA_TEST_PAGEABLE` | src/prefill/prefill.cpp | 117 |  |
| `STRATA_TEST_VERIFY_STALL` | src/core/verify.cpp | 268 |  |
| `STRATA_TG_FLUSH_US` | src/core/session.cpp | 922 |  |
| `STRATA_TOKENIZER` | serve/test_detok.py | 21 |  |
| `STRATA_TOPK_ACTIVE_ANY` | src/kernels/cuda/qsa_select.cu | 1323 |  |
| `STRATA_TOPK_CAPACITY_GUARD` | src/kernels/cuda/qsa_select.cu | 1320 |  |
| `STRATA_TOPK_OLD` | src/kernels/cuda/qsa_select.cu | 1299 |  |
| `STRATA_TOPK_STREAM` | src/kernels/cuda/qsa_select.cu | 1350 |  |
| `STRATA_TRACE` | src/prefill/prefill.cpp | 2065 |  |
| `STRATA_TRACE_ADAPT` | src/program/generate.cpp | 11576 |  |
| `STRATA_TSUM` | src/core/arch_defaults_test.cpp | 51 |  |
| `STRATA_UMA_HEADROOM_GIB` | src/core/expert_cache.cpp | 55 |  |
| `STRATA_UNBUFFERED_LOAD` | src/core/expert_source.cpp | 430 |  |
| `STRATA_VERIFY_ALL_RESIDENT` | src/core/verify.cpp | 637 |  |
| `STRATA_VERIFY_ARENA` | src/core/expert_source.cpp | 4041 |  |
| `STRATA_VERIFY_DEBUG` | src/core/verify.cpp | 65 |  |
| `STRATA_VERIFY_DEVICE_PLAN` | src/core/expert_source.cpp | 3270 |  |
| `STRATA_VERIFY_NODES` | src/core/verify.cpp | 1704 |  |
| `STRATA_VERIFY_PROFILE` | src/core/verify.cpp | 581 |  |
| `STRATA_VERIFY_QDEDUP` | src/core/verify.cpp | 103 |  |
| `STRATA_WATCHDOG_IO_S` | src/program/generate.cpp | 8085 |  |
| `STRATA_WATCHDOG_S` | src/program/generate.cpp | 8081 |  |
| `STRATA_WDDM_BUDGET` | src/core/device.cu | 186 |  |
| `STRATA_WMMA_BF16` | src/prefill/gemm.cu | 699 |  |
| `STRATA_WMMA_GEMM` | src/prefill/gemm.cu | 698 |  |
| `VCT` | tools/hip/package_windows.py | 61 |  |
| `XDG_CONFIG_HOME` | tools/strata_mcp.py | 439 |  |

## server_cli (17)

| name | source | line | description |
|---|---|---|---|
| `--api-key` | 5631 |  |  |
| `--api-monitor` | 5638 |  |  |
| `--before-load` | 5648 |  |  |
| `--config` | 5614 |  |  |
| `--engine` | 5613 |  |  |
| `--fit-max-tokens` | 5628 |  |  |
| `--gpu` | 5623 |  |  |
| `--host` | 5616 |  |  |
| `--idle-unload` | 5641 |  |  |
| `--lazy` | 5637 |  |  |
| `--mcp-config` | 5634 |  |  |
| `--min-free-vram-mib` | 5645 |  |  |
| `--open` | 5627 |  |  |
| `--port` | 5622 |  |  |
| `--script` | 5619 |  |  |
| `--slot-save-path` | 5650 |  |  |
| `--tokenizer` | 5625 |  |  |

## setup_cli (49)

| name | source | line | description |
|---|---|---|---|
| `--accept-source-agreements` | 3067 |  |  |
| `--api-key` | 4609 |  |  |
| `--backend` | 4667 |  |  |
| `--browser` | 4613 |  |  |
| `--build` | 4628 |  |  |
| `--calibrate` | 4643 |  |  |
| `--check` | 4642 |  |  |
| `--context` | 4576 |  |  |
| `--cuda` | 4636 |  |  |
| `--cvec-mode` | 5452 |  |  |
| `--data-dir` | 4615 |  |  |
| `--draft-vocab` | 4645 |  |  |
| `--experimental-speed-projection` | 4593 |  |  |
| `--expert-profile` | 5352 |  |  |
| `--experts-bin` | 5319 |  |  |
| `--family` | 4574 |  |  |
| `--gguf-dir` | 4618 |  |  |
| `--gpu` | 4597 |  |  |
| `--gpus` | 4599 |  |  |
| `--host` | 4607 |  |  |
| `--inspect` | 4633 |  |  |
| `--kv` | 4584 |  |  |
| `--kv-resident` | 5543 |  |  |
| `--kv-streaming` | 4664 |  |  |
| `--layer-split` | 4602 |  |  |
| `--low-ram` | 4650 |  |  |
| `--max-context` | 5354 |  |  |
| `--model` | 4575 |  |  |
| `--models-dir` | 4617 |  |  |
| `--no-browser` | 4610 |  |  |
| `--no-remote-expert-opt` | 4605 |  |  |
| `--no-start` | 4622 |  |  |
| `--out` | 5306 |  |  |
| `--parallel` | 4661 |  |  |
| `--port` | 4087 |  |  |
| `--prebuilt` | 4640 |  |  |
| `--prefill` | 5353 |  |  |
| `--resident-budget-gib` | 4655 |  |  |
| `--rollback-engine` | 4626 |  |  |
| `--rope-scale` | 4581 |  |  |
| `--rope-scaling` | 4577 |  |  |
| `--setup` | 4621 |  |  |
| `--skip-build` | 4671 |  |  |
| `--source` | 4629 |  |  |
| `--update` | 4623 |  |  |
| `--vision` | 4587 |  |  |
| `--vision-tokens` | 4589 |  |  |
| `--vram-reserve-mib` | 4658 |  |  |
| `--yes` | 4620 |  |  |

## config_key (71)

| name | source | line | description |
|---|---|---|---|
| `aliases` | server.py | 5742 |  |
| `allowed_hosts` | server.py | 5764 |  |
| `anthropic_thinking` | server.py | 5793 |  |
| `api_key` | server.py | 5754 |  |
| `api_monitor` | server.py | 5770 |  |
| `args` | mcp.py | 105 |  |
| `backend` | server.py | 2341 |  |
| `before_load` | server.py | 5782 |  |
| `busy` | server.py | 3004 |  |
| `codex_compaction_cache` | server.py | 5740 |  |
| `codex_thread_titles` | server.py | 5739 |  |
| `command` | mcp.py | 611 |  |
| `cors_origins` | server.py | 5761 |  |
| `cuda` | setup.py | 886 |  |
| `cwd` | mcp.py | 106 |  |
| `data_dir` | setup.py | 3593 |  |
| `draft_vocab` | setup.py | 4023 |  |
| `effort_position` | server.py | 2095 |  |
| `engine_silence_s` | server.py | 2118 |  |
| `env` | mcp.py | 95 |  |
| `exe` | setup.py | 886 |  |
| `expert_profile_save` | server.py | 2243 |  |
| `expert_profile_save_every` | server.py | 2247 |  |
| `first_token` | server.py | 3004 |  |
| `fit_max_tokens` | server.py | 5737 |  |
| `generated` | server.py | 3078 |  |
| `gpu` | server.py | 1846 |  |
| `gpu_order` | server.py | 2336 |  |
| `gpus_asked` | setup.py | 1171 |  |
| `headers` | mcp.py | 258 |  |
| `held_tokens` | server.py | 4579 |  |
| `hip_ordinal` | server.py | 2267 |  |
| `host` | server.py | 5657 |  |
| `idle_unload_s` | server.py | 5779 |  |
| `installs` | setup.py | 3512 |  |
| `layer_split` | server.py | 2131 |  |
| `lazy_load` | server.py | 5687 |  |
| `lib_dirs` | server.py | 2363 |  |
| `log` | server.py | 2395 |  |
| `max_tokens` | server.py | 1850 |  |
| `mcp` | mcp.py | 633 |  |
| `mcp_servers` | mcp.py | 652 |  |
| `min_free_vram_mib` | server.py | 5781 |  |
| `min_tokens` | server.py | 1852 |  |
| `model_name` | server.py | 5735 |  |
| `open_browser` | server.py | 5865 |  |
| `parallel` | server.py | 2207 |  |
| `phase` | server.py | 3076 |  |
| `port` | setup.py | 3810 |  |
| `prompt_tokens` | server.py | 3077 |  |
| `queued` | server.py | 3063 |  |
| `reasoning_budget_tokens` | server.py | 5806 |  |
| `reasoning_close_retry` | server.py | 5738 |  |
| `reasoning_effort` | server.py | 2962 |  |
| `reasoning_loop_recovery` | server.py | 5815 |  |
| `remote_expert_opt` | setup.py | 1141 |  |
| `repeat_stop_tokens` | server.py | 5801 |  |
| `sampling` | runconfig.py | 54 |  |
| `slot_save_path` | server.py | 5785 |  |
| `split_skip_if_fits` | server.py | 2185 |  |
| `started` | server.py | 3080 |  |
| `tail` | server.py | 3386 |  |
| `threads` | server.py | 1848 |  |
| `tokenizer` | server.py | 5662 |  |
| `tool_call_recovery` | server.py | 5797 |  |
| `trusted_origins` | server.py | 5762 |  |
| `type` | mcp.py | 605 |  |
| `url` | mcp.py | 385 |  |
| `vision` | runconfig.py | 92 |  |
| `vram_elastic` | server.py | 2189 |  |
| `vram_segment_mib` | server.py | 2191 |  |

