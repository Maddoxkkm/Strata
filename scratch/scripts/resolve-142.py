#!/usr/bin/env python3
"""Resolve the 0.1.42 merge conflicts: keep upstream's newer code, keep our working changes.

Decisions, per block:
  expert_source.hpp : upstream's `note_async_read` decl + our #1520 doc (both)
  prefill.hpp       : upstream (its signatures gained `bool src = true`; our #1439 decl goes)
  mtp.cpp           : both - upstream's `rr_res_` route-resident path, then our #1381 format-agnostic
                      grouped path
  gemm.cu           : upstream (its #1757 Pascal/Volta tiled conversion rewrote the same region)
  prefill.cpp       : our ple_host_buffer include + upstream's includes; upstream's `bool src`
                      signature with our #1107 `stage_slots`
  generate.cpp      : upstream in both blocks (drops #1439's persistent_* accounting)

Then #1439's leftovers are removed: on HIP it is inert (`#if !defined(__HIPCC__)`) and upstream rewrote the
gemm conversion path for Pascal, so merging its cache into the new code would be work with no benefit here.
Re-port only if this box ever runs CUDA.
"""
import pathlib
import subprocess
import sys

ROOT = pathlib.Path(r"D:\llm-dev\strata")

# name -> {block_index: "ours"|"theirs"|("custom", replacement_text)}
PLAN = {
    "include/strata/core/expert_source.hpp": {0: ("custom",
        "    void note_async_read(const uint8_t* blob, void* stream) override;\n"
        "    /// Windows, opt-in with STRATA_FILE_RELEASE=1: trim the file mapping's full pages after a GPU upload or host\n"
        "    /// staging copy completes. Never touches the resident complement or staging buffers. Disabled by default.\n")},
    "include/strata/prefill/prefill.hpp": {0: "ours"},
    "src/core/mtp.cpp": {0: ("custom",
        "        if (rr_res_ != nullptr && rr_margin_ > 0.0f && g.n_expert == 512 && K == 10) {\n"
        "            try {\n"
        "                native_route_resident(logits_, ids_, w_, rr_res_, T, rr_margin_, rr_lo_, rr_hi_, nullptr, cs);\n"
        "            } catch (const std::exception& e) { err = std::string(\"mtp route-resident: \") + e.what(); return false; }\n"
        "        }\n"
        "        // The group arrays are the same for both paths, and `moe_group_resident` only needs the per-expert stride:\n"
        "        // it is format-agnostic.  `hit_dst_` is the flattened routing index and `hit_slot_` the token it belongs to,\n"
        "        // which is exactly the (ent_dst, ent_tok) pair the native kernel's out[ent_dst*N + r] wants.\n"
        "        moe_group_resident(ids_, (int) (T * K), (int) K, experts_, (int64_t) expert_stride(expert_lay_, native_experts_),\n"
        "                           grp_ptr_, grp_start_, grp_counts_, hit_dst_, hit_slot_, cs);\n"
        "        if (native_experts_) {\n"
        "            quantize_q8_1_rows(mixed_, (int64_t) T, (int64_t) N, hit_xq_, cs);\n"
        "            native_expert_grouped(expert_lay_, grp_ptr_, grp_start_, grp_counts_, hit_dst_, hit_slot_, (int64_t) (T * K),\n"
        "                                  (int64_t) (T * K), hit_xq_, hit_scratch_, parts_, cs);\n"
        "        } else {\n"
        "            quantize_q8_0_scaled(mixed_, hit_xq_, hit_xs_, (int64_t) T * N, cs);\n"
        "            moe_grouped_s2(grp_ptr_, grp_start_, grp_counts_, hit_dst_, hit_slot_, (int64_t) T * K, (int64_t) T * K,\n"
        "                           hit_xq_, hit_xs_, hit_scratch_, parts_, cs);\n"
        "        }\n")},
    "src/prefill/gemm.cu": {0: "ours"},
    "src/prefill/prefill.cpp": {0: ("custom",
        "// src/prefill/prefill.cpp - see include/strata/prefill/prefill.hpp.\n"
        "#include \"strata/prefill/prefill.hpp\"\n"
        "#include \"ple_host_buffer.hpp\"\n"),
        1: ("custom",
        "uint64_t Prefill::bytes_needed_no_ring(const core::ModelGeometry& g, const core::SessionState& ss, int64_t chunk,\n"
        "                                        bool src) {\n"
        "    return bytes_needed(g, ss, chunk, src) - (uint64_t) stage_slots((size_t) chunk) * (uint64_t) MAXBLOB();\n")},
    "src/program/generate.cpp": {0: "ours", 1: "ours"},
}


def resolve(path: pathlib.Path, plan: dict) -> int:
    lines = path.read_text(encoding="utf-8", errors="replace").splitlines(keepends=True)
    out, mode, ours, theirs, idx = [], None, [], [], 0
    for line in lines:
        if line.startswith("<<<<<<<"):
            mode, ours, theirs = "ours", [], []
            continue
        if line.startswith("=======") and mode == "ours":
            mode = "theirs"
            continue
        if line.startswith(">>>>>>>") and mode == "theirs":
            pick = plan.get(idx)
            if pick is None:
                raise SystemExit(f"  {path.name}: block {idx} has no decision")
            if isinstance(pick, tuple):
                out.append(pick[1])
            elif pick == "ours":
                out.extend(ours)
            else:
                out.extend(theirs)
            idx += 1
            mode = None
            continue
        (out if mode is None else (ours if mode == "ours" else theirs)).append(line)
    if idx != len(plan):
        raise SystemExit(f"  {path.name}: {idx} blocks but {len(plan)} planned")
    path.write_bytes("".join(out).encode("utf-8"))
    return idx


def main():
    for rel, plan in PLAN.items():
        p = ROOT / rel
        n = resolve(p, plan)
        print(f"  resolved {n} block(s): {rel}")

    # #1439's leftovers
    for rel in ("include/strata/prefill/gemm.hpp", "CMakeLists.txt"):
        subprocess.run(["git", "checkout", "origin/main", "--", rel], cwd=ROOT, check=True)
        print(f"  reverted to upstream: {rel}")
    for rel in ("src/prefill/gemm_bf16_parity.cu",):
        p = ROOT / rel
        if p.exists():
            p.unlink()
            print(f"  removed (ours, #1439): {rel}")

    pre = ROOT / "src/prefill/prefill.cpp"
    text = pre.read_text(encoding="utf-8", errors="replace")
    marker = "uint64_t Prefill::persistent_bytes_needed() {"
    if marker in text:
        i = text.index(marker)
        j = text.index("\n}\n", i) + len("\n}\n")
        # drop the function and the blank line that follows it
        text = text[:i] + text[j:]
        pre.write_bytes(text.encode("utf-8"))
        print("  removed Persistent_bytes_needed definition (ours, #1439)")
    left = subprocess.run(["git", "grep", "-n", "-e", "persistent_bytes_needed", "-e", "bf16_cache_reserve_bytes",
                           "--", "src", "include", "CMakeLists.txt"], cwd=ROOT, capture_output=True, text=True)
    hits = [l for l in left.stdout.splitlines() if l.strip()]
    print(f"  #1439 identifiers left: {hits if hits else 'none'}")


if __name__ == "__main__":
    main()
