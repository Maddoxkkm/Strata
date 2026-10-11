#!/usr/bin/env python3
"""Remove the duplicate copy_blobs the #1324 'both' merge left behind.

Upstream 0.1.42's own copy_blobs already consults the staged tier (`copy_staged`), so the PR's older copy is
both redundant and a redefinition. Keeps upstream's; drops the PR's along with the comment block above it.
"""
import pathlib
import sys

P = pathlib.Path(r"D:\llm-dev\strata\src\core\expert_source.cpp")
SIG = "bool FileExpertSource::copy_blobs(const int32_t* layers, const int32_t* experts, uint8_t* const* dst, size_t n) {"

lines = P.read_text(encoding="utf-8", errors="replace").splitlines(keepends=True)
starts = [i for i, l in enumerate(lines) if l.startswith(SIG)]
print(f"  definitions found: {len(starts)} (lines {[s + 1 for s in starts]})")
if len(starts) != 2:
    print("  expected exactly 2 - not touching the file")
    sys.exit(1)

last = starts[-1]
# walk back over the comment block and blank line that belong to it
begin = last
while begin > 0 and (lines[begin - 1].lstrip().startswith("//") or not lines[begin - 1].strip()):
    begin -= 1
# walk forward to the closing brace at column 0
end = last
while end < len(lines) and lines[end].rstrip("\r\n") != "}":
    end += 1
if end >= len(lines):
    print("  no closing brace found")
    sys.exit(1)
end += 1                                  # include the brace
while end < len(lines) and not lines[end].strip():   # and the blank line after it
    end += 1
print(f"  removing lines {begin + 1}..{end} ({end - begin} lines)")
del lines[begin:end]
P.write_bytes("".join(lines).encode("utf-8"))
left = [i + 1 for i, l in enumerate(lines) if l.startswith(SIG)]
print(f"  definitions left: {left}")
