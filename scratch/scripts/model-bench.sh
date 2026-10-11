#!/usr/bin/env bash
# Compare IQ2_XS (2.4 bpw, 63.4 GiB) with IQ3_S (3.4 bpw, 77.9 GiB) on this box, same config otherwise.
#
#   scratch/scripts/model-bench.sh
#
# Four measurements per model: the prefill ladder from token files, decode samples from the engine's own line,
# the 73K real-text number through the server, and the same five questions answered. IQ3_S prefill/decode run
# through scratch/configs/strata-iq3s.json, which differs from the live config only in --pack/--native/--ple-gguf.
#
# The watchdog here only intervenes under 500 MiB of free RAM: the engine legitimately takes nearly all of it
# (a 1.2 GiB threshold killed an earlier run and produced 503s).
set -u
cd /d/llm-dev/strata
export PATH="/d/llm-dev/strata/engine/rocm/bin:$PATH"
LOG=logs/model-bench.log
exec > "$LOG" 2>&1
echo "=== MODEL BENCH $(date +%H:%M:%S) ==="

cmd /c "stop-server.bat" < /dev/null >/dev/null 2>&1; sleep 3
echo "  engines before: $(tasklist 2>/dev/null | grep -icE '^strata')"

( while :; do
    free=$(powershell -NoProfile -Command "[int]((Get-CimInstance Win32_OperatingSystem).FreePhysicalMemory/1KB)" 2>/dev/null | tr -d '\r')
    echo "$(date +%H:%M:%S) free=${free}MiB engines=$(tasklist 2>/dev/null | grep -ciE '^strata')" >> logs/watch-model.txt
    if [ -n "$free" ] && [ "$free" -lt 500 ]; then
      echo "$(date +%H:%M:%S) LOW RAM (<500MiB) - killing engines to protect the box" >> logs/watch-model.txt
      taskkill /F /IM strata-142-b.exe >/dev/null 2>&1
    fi
    sleep 15; done ) &
WATCH=$!

echo; echo "########## IQ2_XS ##########"
.venv/Scripts/python.exe -u scratch/scripts/decode-ab.py int8 2>&1 | tail -16
PRE_TOKENS=73000 .venv/Scripts/python.exe -u scratch/scripts/prefill-server-ab.py 16384 2>&1 | tail -4
echo "--- answers (IQ2_XS) ---"
.venv/Scripts/python.exe -u scratch/scripts/model-answers.py iq2 2>&1 | tail -20

echo; echo "########## IQ3_S ##########"
.venv/Scripts/python.exe -u scratch/scripts/ab-group.py scratch/configs/variants/model-iq3s.json scratch/configs/strata-iq3s.json
AB_CONFIG=scratch/configs/strata-iq3s.json .venv/Scripts/python.exe -u scratch/scripts/decode-ab.py int8 2>&1 | tail -16
PRE_CONFIG=scratch/configs/strata-iq3s.json PRE_TOKENS=73000 .venv/Scripts/python.exe -u scratch/scripts/prefill-server-ab.py 16384 2>&1 | tail -4
echo "--- answers (IQ3_S) ---"
.venv/Scripts/python.exe -u scratch/scripts/model-answers.py iq3 scratch/configs/strata-iq3s.json 2>&1 | tail -20

kill $WATCH 2>/dev/null
cmd /c "stop-server.bat" < /dev/null >/dev/null 2>&1; sleep 2

echo; echo "########## restore the user's server on the live config ##########"
cmd /c "run-iq2_xs.bat" > logs/server-restored.log 2>&1 &
for i in $(seq 1 40); do curl -s --max-time 5 http://127.0.0.1:8080/health | grep -q '"loaded": true' && { echo "  healthy after ~$((i*5))s"; break; }; sleep 5; done
echo "  engines: $(tasklist 2>/dev/null | grep -icE '^strata')"
echo "=== MODEL BENCH COMPLETE $(date +%H:%M:%S) ==="
