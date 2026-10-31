"""Opt-in: one durable line per finished generation (STRATA_USAGE_LOG=<directory or file>).

Why this exists. The server's own totals (``GET /metrics``) describe the process that is running now, and an upgrade
restarts that process; the numbers an owner actually wants - what the rig has produced over months - outlive it. Today
those numbers can only be recovered after the fact by reading the engine's text log, which carries no per-request
timestamps and no ids an outside program can use, while ``/metrics`` keeps only the last 500 finished generations and
forgets them at the next restart. The two are reconciled by pairing their session start times, which is why a
long-running account always has a small "unaccounted" column: cancelled requests, requests still in flight, and a poll
that happened a few seconds after a log read.

This writes the record once, at the moment the server has already computed every figure in it, to an append-only file
the engine does not have to be alive to read. It carries the instance id and pid that ``/metrics`` does not expose, so
a restart is a new value in the same file rather than a session that has to be matched by time.

Off by default. ``STRATA_USAGE_LOG`` is a directory (files ``usage-YYYYMM.jsonl`` - a month boundary opens a new file
instead of growing one forever) or a path ending in ``.jsonl``, used as given.  Created if missing.

It never raises and never interrupts a request: a usage record is worth having, but not at the price of the generation
that just finished. An unwritable directory, a full disk or a handle closed under us costs one counted failure; after
``MAX_FAILURES`` in a row the writer turns itself off and says so once. The cost on the serving path is one ``open``
per process (kept open), one small line and one flush per generation - against a decode that took seconds.
"""
from __future__ import annotations

import json
import os
import threading
import time

SCHEMA_VERSION = 1
MAX_FAILURES = 3                      # consecutive write failures before we stop trying, for this process

_lock = threading.Lock()              # generations finish on different threads; one line must not split another
_state = {"path": None, "fh": None, "month": None, "fails": 0, "disabled": False, "written": 0}


def target(env=None) -> str | None:
    """Where to append, or None when the feature is off."""
    env = os.environ if env is None else env
    return (env.get("STRATA_USAGE_LOG") or "").strip() or None


def _month(now: float) -> str:
    return time.strftime("%Y%m", time.gmtime(now))


def _open(spec: str, now: float):
    """Resolve the month's file and open it for appending, creating directories as needed."""
    if os.path.basename(spec).endswith(".jsonl"):
        path = spec                                     # an explicit file: honoured as given, no rotation
    else:
        os.makedirs(spec, exist_ok=True)
        path = os.path.join(spec, f"usage-{_month(now)}.jsonl")
    return path, open(path, "a", encoding="utf-8")      # noqa: SIM115 - held open on purpose, closed by close()


def _close_locked():
    fh = _state["fh"]
    _state["fh"] = _state["path"] = _state["month"] = None
    if fh is not None:
        try:
            fh.close()
        except OSError:
            pass


def generation(svc, request_id: str, started: float, finish: str,
               prompt_read: int, prompt_total: int, engine_last: dict, output_tokens: int) -> bool:
    """Append one finished generation. Called from the same place that adds it to the totals, so the file and the
    counters describe exactly the same set of requests - that is the whole point of hooking it here.

    `svc` is the running service: only `instance_id` and `model` are read from it. Returns whether a line was
    written; it does not raise for any reason, including a bug in this module."""
    spec = target()
    if not spec or _state["disabled"]:
        return False
    now = time.time()
    try:
        with _lock:
            if _state["fh"] is None or _state["month"] != _month(now):
                _close_locked()
                _state["path"], _state["fh"] = _open(spec, now)
                _state["month"] = _month(now)
            row = {
                "v": SCHEMA_VERSION, "t": round(now, 3), "t_start": round(float(started), 3),
                "id": request_id, "instance_id": getattr(svc, "instance_id", None),
                "pid": os.getpid(), "model": getattr(svc, "model", None), "finish": finish,
                "prompt_read": int(prompt_read or 0), "prompt_total": int(prompt_total or 0),
                "reused": int((engine_last or {}).get("reused") or 0),
                "output": int(output_tokens or 0),
                "prompt_ms": float((engine_last or {}).get("prompt_ms") or 0.0),
                "decode_ms": float((engine_last or {}).get("decode_ms") or 0.0),
                "drafts_offered": int((engine_last or {}).get("drafts_offered") or 0),
                "drafts_accepted": int((engine_last or {}).get("drafts_accepted") or 0)}
            _state["fh"].write(json.dumps(row, separators=(",", ":")) + "\n")
            _state["fh"].flush()                        # durable before the next request's tokens are billed
            _state["fails"], _state["written"] = 0, _state["written"] + 1
            if _state["written"] == 1:
                print(f"[strata] usage: appending each finished generation to {_state['path']}", flush=True)
            return True
    except Exception as e:                              # noqa: BLE001 - never fail a request over bookkeeping
        _state["fails"] += 1
        if _state["fails"] >= MAX_FAILURES:
            _state["disabled"] = True
            print(f"[strata] usage: disabled after {_state['fails']} failures ({type(e).__name__}: {e}); "
                  "the server keeps serving without it", flush=True)
        return False


def status() -> dict:
    """What the writer is doing, for whoever wants it on a status endpoint later: a target and a count, never a
    claim that history was complete (a process that died mid-generation can miss one row)."""
    return {"enabled": bool(target()) and not _state["disabled"], "target": target(),
            "path": _state["path"], "written": _state["written"], "failures": _state["fails"],
            "schema_version": SCHEMA_VERSION}


def close() -> None:
    """Release the handle (tests, and a clean shutdown)."""
    with _lock:
        _close_locked()
