#!/usr/bin/env python3
"""Resolve the #1324 (LRU RAM tier) merge conservatively.

Its elastically-sized stage pool is the interesting part and it is **off by default** (`stage_keep_` 0, the
watcher only started by start_elastic_lru), so this cannot disturb the current tuned state. Two blocks need
real merges:

  expert_source.hpp : upstream's `stage_buf_` (with its pinned-aware deleter, which is strictly better than
                      the PR's VirtualAlloc one) + the PR's LRU bookkeeping members. The PR's own StageFree
                      struct is dropped - upstream's StageBufFree already frees both pinned and pageable.
  expert_source.cpp : upstream's pinning allocation body + the LRU's `stage_live_` accounting. The PR's
                      freed-slot *reuse* is deliberately NOT taken: it is the half that could hand out a slot
                      the watcher freed, it only matters after a shrink (rare, opt-in), and a mistake there is
                      a use-after-free in the staging path. Without it a shrunk pool loses its capacity until
                      a restart - safe, and the keep-what-you-staged win is unaffected.
"""
import importlib.util
import pathlib
import sys

ROOT = pathlib.Path(r"D:\llm-dev\strata")
spec = importlib.util.spec_from_file_location("rm", ROOT / "scratch" / "scripts" / "resolve-merge.py")
rm = importlib.util.module_from_spec(spec)
spec.loader.exec_module(rm)

HPP_MERGE = """    std::vector<std::unique_ptr<uint8_t[], StageBufFree>> stage_buf_;
    // the elastic LRU (start_elastic_lru): the pool grows to lru_cap_ (at most stage_keep_), a watcher lowers
    // lru_cap_ and frees the coldest buffers when the available RAM falls below the floor, and raises it again
    // when RAM is free (#1324). Off until start_elastic_lru runs; a freed slot is not handed out again here.
    uint64_t stage_alloc_ = 0;                ///< bytes of each stage buffer, whole pages
    size_t stage_live_ = 0;                   ///< stage buffers allocated (a freed one leaves a null slot)
    std::vector<size_t> stage_free_;          ///< null slots (kept, not reused: see the allocator)
    std::thread lru_watch_;
    std::mutex lru_watch_mu_;
    std::condition_variable lru_watch_cv_;
    bool lru_watch_quit_ = false;
    std::atomic<int64_t> lru_freed_{0};
    void lru_watch_loop(uint64_t keep_free);
    void lru_shrink_to(uint64_t bytes);       ///< stage_mu_ held: frees the coldest free buffers down to `bytes`
    void stop_elastic_lru();
"""

CPP_MERGE = """        if (v == stage_buf_.size() || !stage_buf_[v]) {
            // Pinned, where the driver allows: a stage buffer is the source of the cache fill's cudaMemcpyAsync,
            // and a pageable source is staged through the driver's bounce buffer - an extra copy at a fraction of
            // the transfer rate, on the calling thread.  A failure falls back to pageable for this buffer.
            // STRATA_STAGE_PIN: 0 keeps them pageable, 1 always tries to pin, unset (the default) pins while
            // the host has kStagePinFloor of RAM to spare beside this buffer.
            // #1324: a slot the LRU freed is left null rather than handed out again (its reuse path is not
            // taken), so a shrunk pool only regrows by appending.
            static const int pin_mode = [] { const char* v = std::getenv("STRATA_STAGE_PIN"); return v == nullptr ? -1 : (std::atoi(v) != 0 ? 1 : 0); }();
            bool want_pin = pin_mode != 0;
            if (pin_mode < 0) {
                uint64_t avail = 0;
                want_pin = STAGE_PIN_DEFAULT && available_memory_bytes(avail) && avail >= (uint64_t) stage_blob_ + kStagePinFloor;
            }
            void* p = nullptr;
            cudaError_t pin_err = cudaSuccess;
            if (want_pin) pin_err = cudaHostAlloc(&p, (size_t) stage_blob_, cudaHostAllocDefault);
            const bool pinned = want_pin && pin_err == cudaSuccess && p != nullptr;
            if (!pinned) (void) cudaGetLastError();   // the failed alloc's sticky error is ours, not the caller's
            uint8_t* raw = pinned ? (uint8_t*) p : new (std::nothrow) uint8_t[(size_t) stage_blob_];
            if (raw == nullptr) return false;
            ++stage_live_;
            stage_buf_.emplace_back(raw, StageBufFree{pinned});
            stage_idx_[raw] = stage_buf_.size() - 1;
            stage_ev_.push_back(nullptr);
            stage_ev_live_.push_back(0);
            if (pinned && !stage_pin_said_) {
                stage_pin_said_ = true;
                std::fprintf(stderr, "FileExpertSource: the stage buffers are pinned (cudaHostAlloc)\\n");
            } else if (!pinned && want_pin && !stage_pin_failed_said_) {
                stage_pin_failed_said_ = true;
                std::fprintf(stderr, "FileExpertSource: cudaHostAlloc failed for a stage buffer (%s) - pageable it is\\n",
                             cudaGetErrorString(pin_err));
            }
            stage_key_.push_back(-1);
            stage_epoch_.push_back(0);
            stage_used_.push_back(0);
            stage_busy_.push_back(0);
            stage_pf_.push_back(0);
"""

PLAN = {
    "include/strata/core/expert_source.hpp": ["ours", ["custom", HPP_MERGE], "ours"],
    "src/core/expert_source.cpp": [["custom", CPP_MERGE], "ours", "both"],
    "src/prefill/prefill.cpp": ["ours", "ours", "ours", "ours"],
    "src/program/generate.cpp": ["ours"],
}

for rel, blocks in PLAN.items():
    n = rm.resolve(ROOT / rel, blocks)
    print(f"  resolved {n} block(s): {rel}")
