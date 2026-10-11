#!/usr/bin/env python3
"""Move our scratch scripts / configs / notes into D:\llm-dev\strata\scratch\.

Everything stays runnable: the scripts resolve their paths from ROOT (or absolute literals), so after the
move their references to the engine config, its log and the settings file are rewritten to the new homes.
Upstream files (setup.py, serve/, tools/, README*, AGENTS.md, SECURITY.md) and the two launchers
(run-iq2_xs.bat, stop-server.bat) do not move. `logs/` stays where it is: it is the harnesses' output
directory (binaries, bench logs, prompt token files) rather than a script or a config.
"""
import pathlib
import shutil
import sys

ROOT = pathlib.Path(r"D:\llm-dev\strata")
SCRATCH = ROOT / "scratch"

OURS = """ab-group adlx-bisect adlx-metrics adlx-probe analyze-prefill args-test commit-watch cvec-ab
decode-ab disk-bench disk-bench2 env-ab io-profile io-thread-sweep kv-fidelity local-bench
make-prefill-arms make-tokens measure-kernels metrics-gpu now prefill-ab prefill-disk prefill-probe
prefill-stats prefill-where profile-ab prs-applycheck prs-probe prs-triage rate-ladder
run-engine-measure""".split()
CONFIGS = ["strata-iq2_xs.json", "strata-iq2_xs.shared-settings.json"]
NOTES = ["TRIAGE-141.md", "UPDATES-141.md", "OPTIONS-REFERENCE.md", "options-inventory.csv"]
LAUNCHERS = ["run-iq2_xs.bat", "stop-server.bat"]

REPL = [
    # longest first: the settings name contains the config name
    ("strata-iq2_xs.shared-settings.json", "scratch/configs/strata-iq2_xs.shared-settings.json"),
    ("strata-iq2_xs.json", "scratch/configs/strata-iq2_xs.json"),
    ("strata-iq2_xs.log", "scratch/configs/strata-iq2_xs.log"),
]


def move(src, dst_dir, log):
    if not src.exists():
        return
    dst_dir.mkdir(parents=True, exist_ok=True)
    dst = dst_dir / src.name
    if dst.exists():
        log.append(f"  KEEP  {src.name} (already in place)")
        return
    shutil.move(str(src), str(dst))
    log.append(f"  moved {src.relative_to(ROOT)} -> {dst.relative_to(ROOT)}")


def main():
    log = []
    for d in ("scripts", "configs", "configs/variants", "reports", "prs", "data"):
        (SCRATCH / d).mkdir(parents=True, exist_ok=True)

    for n in OURS:
        move(ROOT / f"{n}.py", SCRATCH / "scripts", log)
    for n in CONFIGS:
        move(ROOT / n, SCRATCH / "configs", log)
    for f in sorted((ROOT / "logs").glob("ab-variants-*.json")):
        move(f, SCRATCH / "configs" / "variants", log)
    for n in NOTES:
        move(ROOT / n, SCRATCH / "reports", log)
    if (ROOT / "prs").is_dir():
        for f in sorted((ROOT / "prs").rglob("*")):
            if f.is_file():
                move(f, SCRATCH / "prs" / f.parent.relative_to(ROOT / "prs"), log)
        for d in sorted((ROOT / "prs").rglob("*"), reverse=True):
            if d.is_dir() and not any(d.iterdir()):
                d.rmdir()

    # rewrite the references the move invalidated
    targets = (list((SCRATCH / "scripts").glob("*.py")) + [ROOT / n for n in LAUNCHERS]
               + list((SCRATCH / "configs").glob("*.json")))
    rewritten = []
    for t in targets:
        if not t.exists() or t.suffix == ".exe":
            continue
        text = t.read_text(encoding="utf-8", errors="replace")
        new = text
        for old, rep in REPL:
            new = new.replace(old, rep)
        if new != text:
            t.write_text(new, encoding="utf-8")
            rewritten.append(str(t.relative_to(ROOT)))

    print("=== moves ===")
    for line in log:
        print(line)
    print(f"\n=== rewritten references ({len(rewritten)}) ===")
    for r in rewritten:
        print("  ", r)
    print("\n=== launcher now points at ===")
    bat = (ROOT / "run-iq2_xs.bat").read_text(encoding="utf-8", errors="replace")
    for line in bat.splitlines():
        if "--config" in line:
            print("  ", line.strip()[:150])


if __name__ == "__main__":
    sys.exit(main())
