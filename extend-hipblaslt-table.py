#!/usr/bin/env python3
"""Extend a hipBLASLt tuning table to every shape upstream's gfx1100 table lists.

    .venv/Scripts/python.exe extend-hipblaslt-table.py <reference-table> <out-table> [T]

Reads the unique (n, k) shapes out of a reference table (tools/hip/gfx1100-hipblaslt-100200.txt, which lists the
engine's real GEMM shapes), runs tune_hipblaslt for each of them at the token bucket T (default 8192), and writes
one merged table. A strict-superset merge of an existing out-table is done too (rows are keyed by
dtype+n+k+ldy+t, and the engine rejects duplicate keys), so re-running only adds what is missing.

Run it with the ROCm DLL directories on PATH and the server stopped:
    export PATH="<repo>/.rocm-win/Lib/site-packages/_rocm_sdk_{core,devel,libraries}/bin:$PATH"
"""
import os
import pathlib
import subprocess
import sys

ROOT = pathlib.Path(r"D:\llm-dev\strata")
TOOL = ROOT / "build-hip-win" / "tune_hipblaslt.exe"


def shapes_from(table: pathlib.Path) -> list[tuple[int, int]]:
    seen = []
    # the tuner's own three default shapes too, in case the engine looks those up
    for pair in ((10240, 2560), (320, 10240), (2560, 320)):
        seen.append(pair)
    for line in table.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or line.startswith("STRATA_"):
            continue
        f = line.split()
        n, k = int(f[1]), int(f[2])            # row: dtype n k ldy t id
        if (n, k) not in seen:
            seen.append((n, k))
    return seen


def rows_of(text: str) -> dict:
    out = {}
    for line in text.splitlines():
        line = line.strip()
        if not line or line.startswith("#") or line.startswith("STRATA_"):
            continue
        f = line.split()
        out[(f[0], int(f[1]), int(f[2]), int(f[3]), int(f[4]))] = int(f[5])
    return out


def main():
    ref = pathlib.Path(sys.argv[1]) if len(sys.argv) > 1 else ROOT / "tools/hip/gfx1100-hipblaslt-100200.txt"
    out = pathlib.Path(sys.argv[2]) if len(sys.argv) > 2 else ROOT / "tools/hip/gfx1100-hipblaslt-100500.txt"
    t = int(sys.argv[3]) if len(sys.argv) > 3 else 8192
    shapes = shapes_from(ref)
    print(f"{len(shapes)} shapes from {ref.name} at T={t}: {shapes}", flush=True)

    have = rows_of(out.read_text(encoding="utf-8")) if out.exists() else {}
    print(f"existing rows in {out.name}: {len(have)}", flush=True)

    # One tuner run per shape: this ROCm's rocBLAS cannot do some of them on gfx1100 (a tiny n=1 GEMV fails with
    # hipErrorInvalidDeviceFunction) and the tuner exits 2 on the first failure, discarding every later shape.
    log = ROOT / f"tune-extend-{t}.log"
    merged = dict(have)
    speeds = []
    with log.open("w", encoding="utf-8") as lf:
        for n, k in shapes:
            tmp = ROOT / "tune-one.txt"
            if tmp.exists():
                tmp.unlink()
            cmd = [str(TOOL), "--workspace-mib", "32", "--shape", f"{t},{n},{k}", "--tuning-out", str(tmp)]
            p = subprocess.run(cmd, capture_output=True, text=True, env=dict(os.environ))
            body = (p.stderr or "") + (p.stdout or "")
            lf.write(f"===== shape T={t} N={n} K={k}: exit {p.returncode}\n{body}\n")
            lf.flush()
            if p.returncode != 0 or not tmp.exists():
                why = next((ln for ln in body.splitlines() if "error" in ln.lower()), "no output")
                print(f"  N={n:<6} K={k:<6} SKIPPED ({why.strip()[:70]})", flush=True)
                continue
            merged.update(rows_of(tmp.read_text(encoding="utf-8")))
            best = next((ln for ln in body.splitlines() if ln.startswith("lt_best")), "")
            if best:
                d = dict(x.split("=") for x in best.split() if "=" in x)
                speeds.append((d.get("dtype"), d.get("N"), d.get("K"), d.get("mean_ms"), d.get("speedup_vs_blas")))
                print(f"  N={n:<6} K={k:<6} ok  {d.get('mean_ms')}ms  {d.get('speedup_vs_blas')}x vs hipBLAS", flush=True)
            else:
                print(f"  N={n:<6} K={k:<6} ok (no best line)", flush=True)

    rows = "".join(f"{dt} {n} {k} {ldy} {tb} {sid}\n" for (dt, n, k, ldy, tb), sid in sorted(merged.items()))
    out.write_text("# solution IDs are scoped to this hipBLASLt version and device architecture\n"
                   "STRATA_HIPBLASLT_TUNING_V1 gfx1100 100500\n" + rows, encoding="utf-8")
    print(f"\nwrote {out.name}: {len(merged)} rows (was {len(have)})", flush=True)
    speeds.sort(key=lambda x: -float(x[4].rstrip("x")) if x[4] else 0)
    print(f"\n{'dtype':6}{'N':>7}{'K':>7}{'best_ms':>10}{'vs hipBLAS':>12}")
    for s in speeds:
        print(f"{s[0]:6}{s[1]:>7}{s[2]:>7}{s[3]:>10}{s[4]:>12}")
    print(f"\n{len(speeds)} shapes measured")


if __name__ == "__main__":
    main()
