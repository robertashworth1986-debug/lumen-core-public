#!/usr/bin/env bash
set -euo pipefail

DASHBOARD_DIR="${1:-/opt/lumatrader/dashboard}"

if [[ ! -d "$DASHBOARD_DIR" ]]; then
  echo "ERROR: dashboard directory not found: $DASHBOARD_DIR" >&2
  exit 2
fi

# Production-facing pages we protect from localhost endpoint regressions.
PAGES=(
  "index.html"
  "mission_control.html"
  "grants.html"
  "quant_lab.html"
  "live_positions.html"
  "dashboard_portal.html"
  "investor_command_room.html"
  "investor_wallboard.html"
  "dashboard_analytics.html"
  "luma_experience.html"
  "lumencore_master_v2.html"
  "kraken_execution_dashboard.html"
  "LUMENCORE_MASTER_DASHBOARD_UNIFIED_20260425.html"
)

fail=0

echo "==> Endpoint hygiene check: $DASHBOARD_DIR"

for rel in "${PAGES[@]}"; do
  file="$DASHBOARD_DIR/$rel"
  if [[ ! -f "$file" ]]; then
    continue
  fi

  # 1) Hardcoded localhost usage in runtime calls or visible labels.
  if grep -nE "fetch\([[:space:]]*['\"]https?://(localhost|127\\.0\\.0\\.1)|new[[:space:]]+WebSocket\([[:space:]]*['\"]wss?://(localhost|127\\.0\\.0\\.1)|Gateway:[[:space:]]*localhost|ws://localhost" "$file" >/tmp/luma_endpoint_hits.txt; then
    echo "FAIL: disallowed localhost runtime endpoint usage in $file"
    cat /tmp/luma_endpoint_hits.txt
    fail=1
  fi

  # 2) Hardcoded endpoint constants (allow localhost only in conditional fallback returns).
  if grep -nE "(const|let|var)[[:space:]]+[A-Za-z_][A-Za-z0-9_]*[[:space:]]*=[[:space:]]*['\"]https?://(localhost|127\\.0\\.0\\.1)" "$file" >/tmp/luma_endpoint_consts.txt; then
    echo "FAIL: hardcoded localhost endpoint constant in $file"
    cat /tmp/luma_endpoint_consts.txt
    fail=1
  fi

done

if [[ "$fail" -ne 0 ]]; then
  echo "ERROR: endpoint hygiene check failed. Fix localhost usage before deploy." >&2
  exit 1
fi

echo "PASS: endpoint hygiene clean for monitored production pages."
