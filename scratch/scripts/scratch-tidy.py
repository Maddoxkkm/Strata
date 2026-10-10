#!/usr/bin/env python3
"""Second pass: the stray root-level run logs / dumps and the two scripts the first pass missed.

Run logs go to `logs/` (the project's existing output directory, which every harness already writes to and
which the engine binaries live under) rather than being duplicated inside `scratch/`; `scratch/` holds what
you would edit or re-run by hand: harnesses, engine configs, cached PR diffs, notes.
"""
import pathlib
import shutil

ROOT = pathlib.Path(r"D:\llm-dev\strata")
LOGS = ROOT / "logs"
SCRIPTS = ROOT / "scratch" / "scripts"

UPSTREAM = {"AGENTS.md", "chat.py", "CMakeLists.txt", "docker-entrypoint.sh", "Dockerfile", "LICENSE",
            "README.md", "README.de.md", "README.es.md", "README.fr.md", "README.ja.md", "README.pt-BR.md",
            "README.zh-CN.md", "requirements.txt", "SECURITY.md", "SETUP.bat", "setup.py", "setup.sh",
            "START-HERE.bat", "UPDATE.bat", "update.sh", "run-iq2_xs.bat", "stop-server.bat"}
SCRIPTS_TO_MOVE = {"breadcrumbs.py", "triage-141.py", "scratch-migrate.py"}


def main():
    moved, kept = [], []
    for f in sorted(ROOT.iterdir()):
        if f.is_dir():
            continue
        if f.name in UPSTREAM:
            continue
        if f.name in SCRIPTS_TO_MOVE:
            dst = SCRIPTS / f.name
            if not dst.exists():
                shutil.move(str(f), str(dst))
                moved.append(f"{f.name} -> scratch/scripts/{f.name}")
            continue
        if f.suffix in (".log", ".dmp"):
            dst = LOGS / ("dumps" if f.suffix == ".dmp" else "") / f.name
            dst.parent.mkdir(parents=True, exist_ok=True)
            if dst.exists():
                dst = dst.with_name(dst.stem + f"-root{f.suffix}")
            shutil.move(str(f), str(dst))
            moved.append(f"{f.name} -> {dst.relative_to(ROOT)}")
        else:
            kept.append(f.name)

    # the engine log belongs beside its config, where the engine now appends to it
    eng = ROOT / "strata-iq2_xs.log"
    if eng.exists():
        dst = ROOT / "scratch" / "configs" / "strata-iq2_xs.log"
        if dst.exists():
            dst.write_text(dst.read_text(encoding="utf-8", errors="replace")
                           + eng.read_text(encoding="utf-8", errors="replace"), encoding="utf-8")
            eng.unlink()
            moved.append("strata-iq2_xs.log -> scratch/configs/strata-iq2_xs.log (appended)")
        else:
            shutil.move(str(eng), str(dst))
            moved.append("strata-iq2_xs.log -> scratch/configs/strata-iq2_xs.log")

    for d in ("prs", "scratch/data"):
        p = ROOT / d if d == "prs" else ROOT / "scratch" / "data"
        if p.exists() and p.is_dir() and not any(p.rglob("*")):
            p.rmdir()
            moved.append(f"removed empty {d}/")

    print(f"=== moved {len(moved)} ===")
    for m in moved:
        print("  ", m)
    print(f"\n=== left at root, unclassified ({len(kept)}) ===")
    for k in kept:
        print("  ", k)


if __name__ == "__main__":
    main()
