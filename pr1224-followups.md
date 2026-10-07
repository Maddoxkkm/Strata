# PR #1224 — validation on a Radeon RX 7900 XTX (Windows 11) and two fixes

Tested on the hardware the change targets: Windows 11, Adrenalin 26.8.1 (driver 32.0.31041.1004), Radeon
RX 7900 XTX (gfx1100), Python 3.13.15, `adlxpybind 1.4.6` (cp313 win_amd64 wheel), engine 0.1.40.

The reader works: `gpu_reader(0, amd=True)` returns `_AmdWindows`, `ok() True`,
`name() "AMD Radeon RX 7900 XTX"`, `_amd_windows_cards()` → `[('AMD Radeon RX 7900 XTX', 3)]`, and
`free_vram_mib(0, amd=True)` → 141 MiB. In the running server, `/metrics` goes from
`hardware_static.gpu_name None` + `history.gpu_{util,mem_used,temp,power}` all `None` to live series:

```
hardware_static.gpu_name : AMD Radeon RX 7900 XTX
hardware.gpu_util        : 1 %           history: [2, 2, 1, 1, 1]
hardware.gpu_mem_used    : 25578962944 B (24,394 of 24,560 MiB)
hardware.gpu_temp        : 35.0 °C       history: [35.0, 35.0, 35.0, 35.0]
hardware.gpu_power       : 22.0 W        history: [23.0, 23.0, 22.0, 22.0, 22.0]
```

The repo's own `serve/test_monitor.py` passes (10 tests, OK).

## Fix 1 — power reads 0 on this driver, so the card's power card stays blank

`GPUPower()` answers **0** on Adrenalin 32.0.31041 (the same not-supported shape the ADL Overdrive calls have),
so `out["power"] = power if power > 0 else None` leaves power at `None` while the driver exposes it elsewhere:
**`GPUTotalBoardPower()` reads 22-26 W on the same card.** Prefer it when `GPUPower()` is 0:

```python
            power = float(m.GPUPower())
            if not power:                          # GPUPower() answers 0 on current Adrenalin (measured on
                try:                               # 32.0.31041); GPUTotalBoardPower() is the one that reads the
                    power = float(m.GPUTotalBoardPower())   # board there (22-26 W on this 7900 XTX)
                except Exception:                  # noqa: BLE001 - telemetry must never take the server down
                    power = 0.0
            out["power"] = power if power > 0 else None
```

## Fix 2 — the process segfaults at exit without `Terminate()`

Measured, ADLXPybind 1.4.6 on this machine: **initialise + read + exit without `Terminate()` → SIGSEGV (139)**;
with `Terminate()` → exit 0. Reproduced twice, with and without other calls in between:

```
no Terminate, normal exit  -> read ok: 36.0 31.0 24419 ... (exit 139)
with Terminate, normal exit -> read ok: 36.0 ... terminated (exit 0)
```

As merged, the reader keeps `helper`/`gpus`/`performance` in `_ADLX_WINDOWS` and never ends the session, so the
server dies with a crash code on shutdown (a crash dialog and a 139 exit for a clean stop). Two parts are needed:
end the session at exit, and **drop every ADLX object before `Terminate()`** — an object still referenced when
`Terminate()` runs crashed the teardown in the probe even with the call present.

```python
_ADLX_READERS = []     # the _AmdWindows instances created: their ADLX refs must be dropped before Terminate()

# in _adlx_windows(), after the cache is filled:
        atexit.register(_adlx_shutdown)

def _adlx_shutdown():
    """End the ADLX session at exit.  ADLXPybind 1.4.6 segfaults on interpreter teardown if Terminate() has not
    run (verified here: skipping it exits 139, calling it exits 0), so the session is ended here and every ADLX
    object is dropped first.  A failure here must not change the exit path, so it is swallowed."""
    global _ADLX_WINDOWS
    state = _ADLX_WINDOWS
    if not state:
        return
    _ADLX_WINDOWS = None
    try:
        for reader in _ADLX_READERS:
            reader._gpu = None
            reader._performance = None
        _ADLX_READERS.clear()
        state["gpus"].clear()
        state["performance"] = None
        state["helper"].Terminate()
    except Exception:  # noqa: BLE001
        pass

# in _AmdWindows.__init__, when a card was picked:
            _ADLX_READERS.append(self)
```

## Not covered (the fifth card)

`history.gpu_pcie_rx_mb` (and the PCIe link) stay `None`: ADLXPybind has no PCIe method, and no source for the
throughput exists on this platform. The link generation/width can be had from the PnP device property
(`DEVPKEY_PciDevice_CurrentLinkSpeed` / `_CurrentLinkWidth`, Gen4 x16 here) — separate from this PR.
