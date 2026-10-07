#!/usr/bin/env python3
"""What can this SSD actually deliver for the expert-read pattern?  Unbuffered (FILE_FLAG_NO_BUFFERING), like the
engine, so the page cache cannot flatter the numbers.

    python disk-bench.py [file] 

Three patterns over the pack's experts.bin:
  - sequential, 1.5 MB chunks (one expert blob)
  - sequential, 128 KiB chunks (smaller windows)
  - scattered, 1.5 MB chunks at random 1.5 MB-aligned offsets (what a prompt's expert mix looks like)
Uses a 4 KiB-aligned buffer via VirtualAlloc; FILE_FLAG_NO_BUFFERING needs sector-aligned offsets and sizes.
"""
import ctypes
import pathlib
import random
import sys
import time

k32 = ctypes.WinDLL("kernel32", use_last_error=True)
GENERIC_READ = 0x80000000
OPEN_EXISTING = 3
FILE_FLAG_NO_BUFFERING = 0x20000000
FILE_FLAG_SEQUENTIAL_SCAN = 0x08000000
MEM_COMMIT = 0x1000
MEM_RESERVE = 0x2000
PAGE_READWRITE = 0x04

k32.CreateFileW.restype = ctypes.c_void_p
k32.CreateFileW.argtypes = [ctypes.c_wchar_p, ctypes.c_uint32, ctypes.c_uint32, ctypes.c_void_p,
                            ctypes.c_uint32, ctypes.c_uint32, ctypes.c_void_p]
k32.VirtualAlloc.restype = ctypes.c_void_p
k32.VirtualAlloc.argtypes = [ctypes.c_void_p, ctypes.c_size_t, ctypes.c_uint32, ctypes.c_uint32]
k32.ReadFile.argtypes = [ctypes.c_void_p, ctypes.c_void_p, ctypes.c_uint32, ctypes.POINTER(ctypes.c_uint32),
                         ctypes.c_void_p]

FILE = sys.argv[1] if len(sys.argv) > 1 else r"C:\Users\maddo\.lmstudio\models\packs\iq2_xs\experts.bin"
CHUNK = 1 << 20          # 1 MiB buffer, sector-aligned
BLOB = 1_536_000         # 1.5 MB, one expert blob (rounded up to 4 KiB below)


def open_unbuffered(path, sequential=True):
    flags = FILE_FLAG_NO_BUFFERING | (FILE_FLAG_SEQUENTIAL_SCAN if sequential else 0)
    h = k32.CreateFileW(path, GENERIC_READ, 1, None, OPEN_EXISTING, flags, None)
    if h in (None, 0, ctypes.c_void_p(-1).value):
        raise OSError(f"CreateFileW failed: {ctypes.get_last_error()}")
    return h


def bench_seq(name, blob, total_bytes):
    h = open_unbuffered(FILE, sequential=True)
    buf = k32.VirtualAlloc(None, CHUNK, MEM_COMMIT | MEM_RESERVE, PAGE_READWRITE)
    read = ctypes.c_uint32()
    off, done = 0, 0
    t0 = time.time()
    while done < total_bytes:
        n = min(CHUNK, blob - (done % blob)) if blob else CHUNK
        if k32.ReadFile(h, buf, n, ctypes.byref(read), None) == 0:
            raise OSError(f"ReadFile failed at {off}: {ctypes.get_last_error()}")
        if read.value == 0:
            break
        done += read.value
        off += read.value
    dt = time.time() - t0
    k32.CloseHandle(h)
    print(f"  {name:<34} {done/1e9:.2f} GB in {dt:.2f} s  ->  {done/dt/1e6:.0f} MB/s")


def bench_random(name, blobs, size):
    h = open_unbuffered(FILE, sequential=False)
    buf = k32.VirtualAlloc(None, CHUNK, MEM_COMMIT | MEM_RESERVE, PAGE_READWRITE)
    read = ctypes.c_uint32()
    total = pathlib.Path(FILE).stat().st_size
    rnd = random.Random(1234)
    t0 = time.time()
    done = 0
    for _ in range(blobs):
        off = rnd.randrange(0, total - size, 4096)
        k32.SetFilePointerEx(h, ctypes.c_longlong(off), None, 0)
        left = size
        while left > 0:
            n = min(CHUNK, left)
            if k32.ReadFile(h, buf, n, ctypes.byref(read), None) == 0 or read.value == 0:
                break
            left -= read.value
            done += read.value
    dt = time.time() - t0
    k32.CloseHandle(h)
    print(f"  {name:<34} {blobs} × {size/1e6:.1f} MB payload = {done/1e9:.2f} GB in {dt:.2f} s  -> {done/dt/1e6:.0f} MB/s")


print(f"unbuffered reads from {FILE}")
bench_seq("sequential, 1.5 MB windows", BLOB, 3_000_000_000)
bench_seq("sequential, 128 KiB windows", 131_072, 1_000_000_000)
bench_random("scattered, 1.5 MB windows", 300, BLOB)
