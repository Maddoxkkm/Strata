#!/usr/bin/env python3
"""Does this SSD have more than ~1.3 GB/s to give, and what unlocks it?  Unbuffered, like the engine.

    python disk-bench2.py

Tests window size (0.5 / 1.5 / 4 / 8 MB, sequential) and queue depth (4 threads x 1.5 MB windows, scattered).
If large windows or depth lift the rate well past 1.3 GB/s, the engine's read batching is the lever; if the rate
stays flat, the drive is the ceiling and only reading fewer bytes helps.
"""
import ctypes
import pathlib
import random
import threading
import time

k32 = ctypes.WinDLL("kernel32", use_last_error=True)
GENERIC_READ = 0x80000000
OPEN_EXISTING = 3
FILE_FLAG_NO_BUFFERING = 0x20000000
FILE_FLAG_SEQUENTIAL_SCAN = 0x08000000
MEM_COMMIT, MEM_RESERVE, PAGE_READWRITE = 0x1000, 0x2000, 0x04
k32.CreateFileW.restype = ctypes.c_void_p
k32.CreateFileW.argtypes = [ctypes.c_wchar_p, ctypes.c_uint32, ctypes.c_uint32, ctypes.c_void_p,
                            ctypes.c_uint32, ctypes.c_uint32, ctypes.c_void_p]
k32.VirtualAlloc.restype = ctypes.c_void_p
k32.VirtualAlloc.argtypes = [ctypes.c_void_p, ctypes.c_size_t, ctypes.c_uint32, ctypes.c_uint32]
k32.ReadFile.argtypes = [ctypes.c_void_p, ctypes.c_void_p, ctypes.c_uint32, ctypes.POINTER(ctypes.c_uint32),
                         ctypes.c_void_p]
k32.SetFilePointerEx.argtypes = [ctypes.c_void_p, ctypes.c_longlong, ctypes.c_void_p, ctypes.c_uint32]

FILE = r"C:\Users\maddo\.lmstudio\models\packs\iq2_xs\experts.bin"
TOTAL = pathlib.Path(FILE).stat().st_size
BUF = 8 << 20


def openf(seq=True):
    return k32.CreateFileW(FILE, GENERIC_READ, 1, None, OPEN_EXISTING,
                           FILE_FLAG_NO_BUFFERING | (FILE_FLAG_SEQUENTIAL_SCAN if seq else 0), None)


def seq_bench(win, total=2_000_000_000):
    h = openf(True)
    buf = k32.VirtualAlloc(None, BUF, MEM_COMMIT | MEM_RESERVE, PAGE_READWRITE)
    rd = ctypes.c_uint32()
    t0, done = time.time(), 0
    while done < total:
        n = min(BUF, total - done, win)
        if k32.ReadFile(h, buf, n, ctypes.byref(rd), None) == 0 or rd.value == 0:
            break
        done += rd.value
    dt = time.time() - t0
    k32.CloseHandle(h)
    print(f"  sequential, {win/1e6:>4.1f} MB windows   {done/1e9:.2f} GB in {dt:.2f} s -> {done/dt/1e6:>6.0f} MB/s")


def depth_bench(threads, win=1_536_000, per=120):
    handles = [openf(False) for _ in range(threads)]
    counts = [0] * threads

    def worker(i):
        h = handles[i]
        buf = k32.VirtualAlloc(None, BUF, MEM_COMMIT | MEM_RESERVE, PAGE_READWRITE)
        rd = ctypes.c_uint32()
        rnd = random.Random(1000 + i)
        got = 0
        for _ in range(per):
            off = rnd.randrange(0, TOTAL - win, 4096)
            k32.SetFilePointerEx(h, ctypes.c_longlong(off), None, 0)
            left = win
            while left > 0:
                n = min(BUF, left)
                if k32.ReadFile(h, buf, n, ctypes.byref(rd), None) == 0 or rd.value == 0:
                    break
                left -= rd.value
                got += rd.value
        counts[i] = got

    t0 = time.time()
    ts = [threading.Thread(target=worker, args=(i,)) for i in range(threads)]
    [t.start() for t in ts]
    [t.join() for t in ts]
    dt = time.time() - t0
    for h in handles:
        k32.CloseHandle(h)
    done = sum(counts)
    print(f"  {threads} threads × 1.5 MB scattered  {done/1e9:.2f} GB in {dt:.2f} s -> {done/dt/1e6:>6.0f} MB/s")


print(f"unbuffered, {FILE} ({TOTAL/1e9:.2f} GB)")
for w in (524_288, 1_536_000, 4_194_304, 8_388_608):
    seq_bench(w)
for d in (2, 4, 8):
    depth_bench(d)
