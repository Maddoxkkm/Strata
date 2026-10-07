#!/usr/bin/env bash
# Sweep prefill arms on this PC: for each variant config, restart the server, measure, stop it.
# Usage: bash prefill-sweep.sh <arm-json-1> [<arm-json-2> ...]
set -u
cd /d/llm-dev/strata

kill_server() {
  # stop-strata.ps1 matches only python.exe running serve/server.py and the engine exes (never this shell)
  powershell -NoProfile -ExecutionPolicy Bypass -File stop-strata.ps1 >/dev/null 2>&1 || true
  sleep 3
  local listeners
  listeners=$(netstat -ano 2>/dev/null | grep -E ':8080 .*LISTENING' | wc -l)
  [ "$listeners" -eq 0 ] || echo "    WARNING: port 8080 still held by $listeners process(es)"
}

wait_ready() {   # $1 = arm name; fails fast when the server refused to start
  local arm="$1" i
  for i in $(seq 1 45); do
    if grep -q "already in use" "server-$arm.out" 2>/dev/null; then
      echo "    FAILED: port already in use"; return 1
    fi
    if curl -s --max-time 5 http://127.0.0.1:8080/health | grep -q '"loaded": true'; then
      echo "    ready after ~$((i*5))s"; return 0
    fi
    sleep 5
  done
  echo "    NOT READY after 300s"; return 1
}

for cfg in "$@"; do
  arm=$(basename "$cfg" .json)
  echo "=== ARM $arm  ($(date +%H:%M:%S)) ==="
  kill_server
  : > "server-$arm.out"
  .venv/Scripts/python.exe serve/server.py --engine strata --config "$cfg" --port 8080 > "server-$arm.out" 2>&1 &
  srv=$!
  if wait_ready "$arm"; then
    grep -i "expert cache auto\|resident RAM mode\|prefill\|mmq\|VRAM free with everything" strata-iq2_xs.log | tail -8
    .venv/Scripts/python.exe prefill-bench.py "$arm"
    cp strata-iq2_xs.log "bench-logs/engine-$arm.log" 2>/dev/null || true
  else
    echo "    (arm $arm failed to become ready)"
    tr '\r' '\n' < "server-$arm.out" | tail -8
    cp strata-iq2_xs.log "bench-logs/engine-$arm-FAILED.log" 2>/dev/null || true
  fi
  kill "$srv" 2>/dev/null || true
  kill_server
  echo "=== ARM $arm done ($(date +%H:%M:%S)) ==="
  echo
done
echo "SWEEP COMPLETE"
