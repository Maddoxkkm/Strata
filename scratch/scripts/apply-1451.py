#!/usr/bin/env python3
"""Apply the current #1451 revision's prefill.cpp delta (the helper's call sites).

On tuned-141 we landed #1451's helper file and its test but never wired them up, so the PLE host buffers
are still allocated eagerly in init() and the helper is dead code. The PR's current revision moves that
allocation into run_impl, lazily, sized by what the run needs (buffer two only when a following chunk
exists) and keeping the retained capacity. Four exact-match edits, each asserted so a drift in upstream's
text stops the script instead of writing something wrong.
"""
import pathlib
import sys

P = pathlib.Path(r"D:\llm-dev\strata\src\prefill\prefill.cpp")
text = P.read_text(encoding="utf-8", errors="replace")
orig = text

EDITS = [
    # 1. the helper's include
    ('#include "strata/prefill/prefill.hpp"\n#include "mmq_resident_sort.hpp"',
     '#include "strata/prefill/prefill.hpp"\n#include "ple_host_buffer.hpp"\n#include "mmq_resident_sort.hpp"'),
    # 2. the retained-capacity member
    ('    std::vector<float> ple_pageable[2];      // the fallback when no more RAM can be pinned\n',
     '    std::vector<float> ple_pageable[2];      // the fallback when no more RAM can be pinned\n'
     '    size_t ple_host_elements[2] = {};        // retained capacity; allocated only when a run needs PLE\n'),
    # 3. drop the eager allocation: it is the lazy path's job now (unused T*N*4 buffers cost pinned RAM)
    ('        if (!m.ple_emb_host[b] &&\n'
     '            (force_pageable() || cudaHostAlloc((void**) &m.ple_emb_host[b], (size_t) T * N * 4, cudaHostAllocDefault) != cudaSuccess)) {\n'
     '            cudaGetLastError();\n'
     '            m.ple_pageable[b].resize(T * N);          // pageable: the upload is staged before it returns\n'
     '            m.ple_emb_host[b] = m.ple_pageable[b].data();\n'
     '        }\n',
     ''),
    # 4. allocate lazily at the start of the PLE section, for the buffers this run will actually use
    ('    const bool ple_on = ss.ple.ready() && LB <= 1 && 1 < LE;\n',
     '    const bool ple_on = ss.ple.ready() && LB <= 1 && 1 < LE;\n'
     '    // A run starts in buffer zero. Only a following chunk needs the second buffer.\n'
     '    if (ple_on) for (int b = 0; b < (n > m.T ? 2 : 1); ++b) {\n'
     '        if (!detail::ensure_ple_host(m.ple_emb_host[b], m.ple_pageable[b], m.ple_host_elements[b],\n'
     '                                     (size_t) m.T * N, m.ple_copied[b], force_pageable())) {\n'
     '            err = "prefill: PLE host buffers could not be prepared";\n'
     '            return false;\n'
     '        }\n'
     '    }\n'),
]

for i, (old, new) in enumerate(EDITS, 1):
    n = text.count(old)
    if n != 1:
        print(f"  edit {i}: FOUND {n} times, expected 1 - aborting without writing")
        sys.exit(1)
    text = text.replace(old, new, 1)
    print(f"  edit {i}: ok")

if text == orig:
    print("  no change")
    sys.exit(1)
P.write_bytes(text.encode("utf-8"))
print(f"  wrote {P.name}: {len(orig.splitlines())} -> {len(text.splitlines())} lines")
