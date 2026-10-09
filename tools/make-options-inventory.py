#!/usr/bin/env python3
"""Regenerate OPTIONS-REFERENCE.md + options-inventory.csv from the tree it is run in.

    python tools/make-options-inventory.py [--root .]

Compiled from the code, not from prose:
  * engine CLI flags   - the argument parser in src/program/generate.cpp
  * engine env vars    - every getenv("...") under src/ include/
  * server CLI flags   - argparse in serve/server.py
  * setup CLI flags    - argparse in setup.py
  * server config keys - the JSON keys serve/runconfig.py knows
Each row carries the file and line so a claim can be checked.  Run it after every pull: names do get renamed
(STRATA_PREFILL_FIRST / _SYNC / _STREAM_ALL existed in 0.1.40.3 and are gone in 0.1.41).
"""
import argparse
import csv
import json
import pathlib
import re

ENGINE = "src/program/generate.cpp"
SKIP_ENV = {"PATH", "HOME", "TEMP", "TMP", "USERPROFILE", "APPDATA", "LOCALAPPDATA", "PYTHONPATH",
            "CUDA_VISIBLE_DEVICES", "HIP_VISIBLE_DEVICES", "ROCR_VISIBLE_DEVICES", "VIRTUAL_ENV",
            "HTTP_PROXY", "HTTPS_PROXY", "NO_PROXY", "COMSPEC", "SYSTEMROOT", "WINDIR", "LANG", "LC_ALL"}


def read(p):
    try:
        return p.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return ""


def engine_flags(root):
    rows = {}
    text = read(root / ENGINE)
    for i, line in enumerate(text.splitlines(), 1):
        for m in re.finditer(r'a == "(--[a-z0-9-]+)"', line):
            rows.setdefault(m.group(1), (i, ""))
        for m in re.finditer(r'a\.rfind\("(--[a-z0-9-]+)", 0\)', line):
            rows.setdefault(m.group(1), (i, "prefix match"))
    # help text: "  --flag ARG   description" lines in the usage block
    help_re = re.compile(r'^\s*"  (--[a-z0-9-]+)(?: ([A-Z][A-Z0-9_|]*))?\s{2,}(.*?)\\n"')
    for line in text.splitlines():
        m = help_re.match(line)
        if m and m.group(1) in rows:
            line_no, note = rows[m.group(1)]
            rows[m.group(1)] = (line_no, m.group(3).strip()[:150] or note)
    return rows


def env_vars(root):
    pat = re.compile(r'(?:std::)?getenv\("([A-Z][A-Z0-9_]*)"\)')
    py = re.compile(r'(?:os\.environ(?:\.get)?\[?\(?["\'])([A-Z][A-Z0-9_]*)|'
                    r'os\.getenv\(["\']([A-Z][A-Z0-9_]*)["\']\)')
    rows = {}
    for p in list(root.glob("src/**/*")) + list(root.glob("include/**/*")) + list(root.glob("serve/**/*.py")) \
            + list(root.glob("tools/**/*.py")):
        if p.suffix not in (".cpp", ".hpp", ".cu", ".cuh", ".py", ".c", ".h"):
            continue
        text = read(p)
        for i, line in enumerate(text.splitlines(), 1):
            for m in pat.finditer(line):
                rows.setdefault(m.group(1), (str(p.relative_to(root)).replace("\\", "/"), i))
            for m in py.finditer(line):
                name = m.group(1) or m.group(2)
                if name:
                    rows.setdefault(name, (str(p.relative_to(root)).replace("\\", "/"), i))
    return {k: v for k, v in rows.items() if k not in SKIP_ENV}


def argparse_flags(root, path):
    rows = {}
    text = read(root / path)
    for i, line in enumerate(text.splitlines(), 1):
        for m in re.finditer(r'add_argument\(\s*"(--[a-z0-9-]+)"', line):
            rows.setdefault(m.group(1), (i, ""))
        for m in re.finditer(r'^\s*"(--[a-z0-9-]+)"', line):
            rows.setdefault(m.group(1), (i, ""))
    return rows


def config_keys(root):
    """Keys the engine config (strata-<model>.json) accepts.  Taken from the two places that define them: the
    defaults dicts at module level in serve/*.py, and the config/cfg/settings receivers in the readers.  A blanket
    dict-key scan is useless here - it also matches HTTP and request internals (358 rows)."""
    rows = {}
    recv = (r'\b(?:config|cfg|conf|settings|s)\.(?:get|setdefault)\(\s*["\']([a-z][a-z0-9_]{2,})["\']',
            r'^\s*["\']([a-z][a-z0-9_]{2,})["\']\s*:',           # dict literals (defaults blocks)
            r'\b(?:config|cfg|conf)\.(?:pop|update)\(\s*["\']([a-z][a-z0-9_]{2,})["\']')
    for p in sorted(list((root / "serve").glob("*.py")) + [root / "setup.py"]):
        text = read(p)
        in_defaults = False
        for i, line in enumerate(text.splitlines(), 1):
            if re.search(r'^\s*(?:DEFAULT[A-Z_]*|defaults|DEFAULT_CONFIG|_DEFAULTS)\s*=', line):
                in_defaults = True
            if in_defaults:
                if line.strip().endswith("}") or re.match(r'^\S', line):
                    in_defaults = False
                else:
                    for m in re.finditer(r'^\s*["\']([a-z][a-z0-9_]{2,})["\']\s*:', line):
                        rows.setdefault(m.group(1), (p.name, i))
            for pat in recv[:1] + recv[2:]:
                for m in re.finditer(pat, line):
                    rows.setdefault(m.group(1), (p.name, i))
    return rows


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", default=".")
    a = ap.parse_args()
    root = pathlib.Path(a.root).resolve()

    groups = [
        ("engine_cli", engine_flags(root), ENGINE),
        ("env", env_vars(root), "(all sources)"),
        ("server_cli", argparse_flags(root, "serve/server.py"), "serve/server.py"),
        ("setup_cli", argparse_flags(root, "setup.py"), "setup.py"),
        ("config_key", config_keys(root), "serve/runconfig.py"),
    ]

    out = root / "options-inventory.csv"
    with out.open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["kind", "name", "source", "line", "desc"])
        for kind, rows, default_src in groups:
            for name in sorted(rows):
                src, line = rows[name]
                if kind == "engine_cli":
                    desc = line if isinstance(line, str) and not str(line).isdigit() else ""
                    w.writerow([kind, name, default_src, "", desc])
                else:
                    w.writerow([kind, name, src, line, ""])

    counts = {kind: len(rows) for kind, rows, _ in groups}
    md = root / "OPTIONS-REFERENCE.md"
    body = [f"# Strata — every option that can be set (regenerated from {root.name})", "",
            "Machine-compiled from the code, not from a README.  Tidy long-format copy: `options-inventory.csv`.",
            "", f"Counts: " + ", ".join(f"**{v}** {k.replace('_', ' ')}" for k, v in counts.items()), ""]
    for kind, rows, default_src in groups:
        body += [f"## {kind} ({len(rows)})", "", "| name | source | line | description |", "|---|---|---|---|"]
        for name in sorted(rows):
            src, line = rows[name]
            desc = line if kind == "engine_cli" and not str(line).isdigit() else ""
            body.append(f"| `{name}` | {default_src if kind == 'engine_cli' else src} | "
                        f"{'' if kind == 'engine_cli' else line} | {desc} |")
        body.append("")
    md.write_text("\n".join(body) + "\n", encoding="utf-8")
    print(f"  wrote {out.name} and {md.name}: " + ", ".join(f"{v} {k}" for k, v in counts.items()))


if __name__ == "__main__":
    main()
