#!/usr/bin/env python3
"""Write the prefill A/B configs from the installed one, changing only the knobs under test.

    .venv/Scripts/python.exe make-prefill-arms.py

armA-baseline      : exactly what is installed (--prefill auto, no engine env)
armB-prefill8192   : --prefill 8192 (the AMD_HIP_PERFORMANCE.md measured setting) + the runtime opt-ins
                     STRATA_PREFILL_MMQ=1, STRATA_PREFILL_RING=96, STRATA_IO_THREADS=32
armC-kvstream      : armB plus --kv-resident 32768 (KV streaming: the KV cache in RAM, the attention window in
                     VRAM, so more experts stay in the GPU cache)
"""
import json
import pathlib

ROOT = pathlib.Path(r"D:\llm-dev\strata")
base = json.loads((ROOT / "strata-iq2_xs.json").read_text(encoding="utf-8-sig"))


def variant(name, args_tweak=None, env_extra=None):
    cfg = json.loads(json.dumps(base))
    if args_tweak:
        cfg["args"] = args_tweak(list(cfg["args"]))
    cfg["env"] = {**cfg.get("env", {}), **(env_extra or {})}
    cfg.pop("port", None)
    (ROOT / f"{name}.json").write_text(json.dumps(cfg, indent=1), encoding="utf-8")
    print(f"wrote {name}.json  kv={cfg['args'][cfg['args'].index('--kv')+1]} "
          f"prefill={cfg['args'][cfg['args'].index('--prefill')+1]} env={cfg['env']}")


def set_arg(flag, value):
    def f(args):
        if flag in args:
            args[args.index(flag) + 1] = value
        else:
            args += [flag, value]
        return args
    return f


variant("armA-baseline")
variant("armB-prefill8192", set_arg("--prefill", "8192"),
        {"STRATA_PREFILL_MMQ": "1", "STRATA_PREFILL_RING": "96", "STRATA_IO_THREADS": "32"})


def add_kv_resident(args):
    args = set_arg("--prefill", "8192")(args)
    if "--kv-resident" not in args:
        args += ["--kv-resident", "32768"]
    return args


variant("armC-kvstream", add_kv_resident,
        {"STRATA_PREFILL_MMQ": "1", "STRATA_PREFILL_RING": "96", "STRATA_IO_THREADS": "32"})
# armD: bigger prefill chunks (the engine's own --prefill auto:16384, since plain auto caps at 8192)
variant("armD-chunk16k", set_arg("--prefill", "auto:16384"),
        {"STRATA_PREFILL_MMQ": "1", "STRATA_PREFILL_RING": "96", "STRATA_IO_THREADS": "32"})
