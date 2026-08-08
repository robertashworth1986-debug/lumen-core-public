#!/usr/bin/env bash
# Atomic deployment for the gateway's public booth projection dependency.
# Inspect-only by default. --apply is the only write path.
set -Eeuo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
SOURCE="${LUMENCORE_PUBLIC_CONTRACT_SOURCE:-${SCRIPT_DIR}/../booth_public_contract.py}"
TARGET="${LUMENCORE_PUBLIC_CONTRACT_TARGET:-/opt/lumencore/code/booth_public_contract.py}"
SERVICE="${LUMENCORE_GATEWAY_SERVICE:-luma-gateway}"
LOCAL_HEALTH_URL="${LUMENCORE_LOCAL_HEALTH_URL:-http://127.0.0.1:8787/health}"
PUBLIC_HEALTH_URL="${LUMENCORE_PUBLIC_HEALTH_URL:-https://lumen-core.ai/health}"
EXPECTED_SHA="${LUMENCORE_EXPECTED_PUBLIC_CONTRACT_SHA256:-}"
APPLY=false
CHANGED=false
HAD_TARGET=false
REPAIR_COMPLETE=false
ROLLBACK=""

usage() {
  cat <<'EOF'
Usage:
  bash code/ops/REPAIR_GATEWAY_PUBLIC_CONTRACT_ON_VPS.sh
  sudo bash code/ops/REPAIR_GATEWAY_PUBLIC_CONTRACT_ON_VPS.sh --apply

Inspect-only mode validates and compares the source dependency without writing.
Apply mode requires root, installs only booth_public_contract.py, restarts only
luma-gateway when the file changed, and rolls the file back unless local and
public health both return HTTP 200.
EOF
}

for arg in "$@"; do
  case "$arg" in
    --apply) APPLY=true ;;
    -h|--help) usage; exit 0 ;;
    *) echo "ERROR: unknown argument: $arg" >&2; usage >&2; exit 2 ;;
  esac
done

command -v python3 >/dev/null 2>&1 || {
  echo "ERROR: python3 is required" >&2
  exit 3
}
command -v sha256sum >/dev/null 2>&1 || {
  echo "ERROR: sha256sum is required" >&2
  exit 4
}
[[ -f "$SOURCE" ]] || {
  echo "ERROR: source dependency not found: $SOURCE" >&2
  exit 5
}

PYTHONDONTWRITEBYTECODE=1 PYTHONPATH="$(dirname -- "$SOURCE")" python3 - "$SOURCE" <<'PY'
import ast
import sys
from pathlib import Path

ast.parse(Path(sys.argv[1]).read_text(encoding="utf-8"))
from booth_public_contract import public_booth_projection

projected = public_booth_projection(
    {
        "generated_utc": "2026-08-08T00:00:00Z",
        "indexing": {
            "files_indexed": 42,
            "roots_present": 2,
            "roots_total": 3,
            "scan_capped": False,
        },
        "catalog": {"engine_count": 7, "assets_source_rows": 11},
        "founder_profile": {"ein": "12-3456789"},
        "live_execution": {"recent_trades": [{"txid": "OABCDE-FGHIJK-LMNOPQ"}]},
    }
)
assert projected["schema"] == "lumencore.public_booth_contract.v2"
assert projected["supported_maturity_level"] == 3
assert projected["live_execution_authority"] is False
assert projected["profit_claim_allowed"] is False
assert projected["indexing"]["files_indexed"] == 42
assert projected["catalog"]["engine_count"] == 7
assert "founder_profile" not in projected
assert "live_execution" not in projected
assert "12-3456789" not in repr(projected)
assert "OABCDE-FGHIJK-LMNOPQ" not in repr(projected)
PY

SOURCE_SHA="$(sha256sum "$SOURCE" | awk '{print $1}')"
if [[ -n "$EXPECTED_SHA" ]]; then
  [[ "$EXPECTED_SHA" =~ ^[0-9a-fA-F]{64}$ ]] || {
    echo "ERROR: expected SHA-256 must be exactly 64 hexadecimal characters" >&2
    exit 6
  }
  [[ "${SOURCE_SHA,,}" == "${EXPECTED_SHA,,}" ]] || {
    echo "ERROR: staged dependency does not match the expected SHA-256" >&2
    exit 6
  }
fi
TARGET_SHA="missing"
if [[ -f "$TARGET" ]]; then
  TARGET_SHA="$(sha256sum "$TARGET" | awk '{print $1}')"
fi

printf 'Source: %s\n' "$SOURCE"
printf 'Target: %s\n' "$TARGET"
printf 'Source SHA-256: %s\n' "$SOURCE_SHA"
printf 'Target SHA-256: %s\n' "$TARGET_SHA"

if [[ "$APPLY" != true ]]; then
  if command -v systemctl >/dev/null 2>&1; then
    systemctl is-active "$SERVICE" 2>/dev/null || true
  fi
  if command -v curl >/dev/null 2>&1; then
    curl -sS --max-time 10 -o /dev/null -w 'Local health HTTP: %{http_code}\n' \
      "$LOCAL_HEALTH_URL" || true
  fi
  exit 0
fi

human_unlock_token="${LUMA_HUMAN_UNLOCK_TOKEN:-}"
if [[ ${#human_unlock_token} -lt 32 ]]; then
  echo "ERROR: --apply requires a private HumanUnlock value of at least 32 characters" >&2
  exit 7
fi
unset human_unlock_token LUMA_HUMAN_UNLOCK_TOKEN

[[ "${EUID}" -eq 0 ]] || {
  echo "ERROR: --apply must run as root" >&2
  exit 8
}
command -v systemctl >/dev/null 2>&1 || {
  echo "ERROR: systemctl is required" >&2
  exit 9
}
command -v curl >/dev/null 2>&1 || {
  echo "ERROR: curl is required" >&2
  exit 10
}
systemctl cat "$SERVICE" >/dev/null
install -d -o root -g root -m 755 "$(dirname -- "$TARGET")"

STAMP="$(date -u +%Y%m%dT%H%M%SZ)"
ROLLBACK="${TARGET}.deploy-rollback.${STAMP}"

rollback() {
  local rc="${1:-1}"
  if [[ "$CHANGED" == true && "$REPAIR_COMPLETE" != true ]]; then
    echo "Rolling back gateway public-contract dependency..." >&2
    if [[ "$HAD_TARGET" == true && -f "$ROLLBACK" ]]; then
      cp -a -- "$ROLLBACK" "$TARGET"
    else
      rm -f -- "$TARGET"
    fi
    systemctl restart "$SERVICE" || true
  fi
  exit "$rc"
}

trap 'rc=$?; echo "ERROR: gateway dependency deployment stopped on line $LINENO" >&2; rollback "$rc"' ERR
trap 'echo "Deployment interrupted." >&2; rollback 130' INT TERM

if [[ "$SOURCE_SHA" != "$TARGET_SHA" ]]; then
  if [[ -f "$TARGET" ]]; then
    HAD_TARGET=true
    cp -a -- "$TARGET" "$ROLLBACK"
  fi
  CHANGED=true
  install -o root -g root -m 0644 "$SOURCE" "$TARGET"
  [[ "$(sha256sum "$TARGET" | awk '{print $1}')" == "$SOURCE_SHA" ]]
  systemctl restart "$SERVICE"
else
  echo "Dependency already matches; service restart is not required."
fi

probe_health() {
  local url="$1"
  local output="$2"
  local status="000"
  local attempt
  for attempt in $(seq 1 10); do
    status="$(curl -sS --max-time 15 -o "$output" -w '%{http_code}' \
      "${url}?deploy=${STAMP}-${attempt}" || true)"
    if [[ "$status" == "200" ]]; then
      printf '%s\n' "$status"
      return 0
    fi
    sleep 3
  done
  printf '%s\n' "$status"
  return 1
}

LOCAL_BODY="$(mktemp)"
PUBLIC_BODY="$(mktemp)"
trap 'rm -f "$LOCAL_BODY" "$PUBLIC_BODY"' EXIT

LOCAL_STATUS="$(probe_health "$LOCAL_HEALTH_URL" "$LOCAL_BODY")" || {
  echo "ERROR: local gateway health failed (HTTP ${LOCAL_STATUS:-000})" >&2
  rollback 10
}
python3 -m json.tool "$LOCAL_BODY" >/dev/null

PUBLIC_STATUS="$(probe_health "$PUBLIC_HEALTH_URL" "$PUBLIC_BODY")" || {
  echo "ERROR: public gateway health failed (HTTP ${PUBLIC_STATUS:-000})" >&2
  rollback 11
}
python3 -m json.tool "$PUBLIC_BODY" >/dev/null

REPAIR_COMPLETE=true
trap - ERR INT TERM
echo "OK: gateway dependency is installed and local/public health return valid JSON."
echo "Local HTTP: $LOCAL_STATUS | Public HTTP: $PUBLIC_STATUS"
