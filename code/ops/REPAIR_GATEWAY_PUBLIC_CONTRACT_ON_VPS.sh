#!/usr/bin/env bash
# Atomic deployment for the gateway facade and fixed public booth contract.
# Inspect-only by default. --apply is the only write path.
set -Eeuo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
CONTRACT_SOURCE="${LUMENCORE_PUBLIC_CONTRACT_SOURCE:-${SCRIPT_DIR}/../booth_public_contract.py}"
FACADE_SOURCE="${LUMENCORE_GATEWAY_FACADE_SOURCE:-${SCRIPT_DIR}/../luma_experience_gateway.py}"
LEGACY_SOURCE="${LUMENCORE_GATEWAY_LEGACY_SOURCE:-${SCRIPT_DIR}/../luma_experience_gateway_legacy.py}"
CONTRACT_TARGET="${LUMENCORE_PUBLIC_CONTRACT_TARGET:-/opt/lumencore/code/booth_public_contract.py}"
FACADE_TARGET="${LUMENCORE_GATEWAY_FACADE_TARGET:-/opt/lumencore/code/luma_experience_gateway.py}"
LEGACY_TARGET="${LUMENCORE_GATEWAY_LEGACY_TARGET:-/opt/lumencore/code/luma_experience_gateway_legacy.py}"
SERVICE="${LUMENCORE_GATEWAY_SERVICE:-luma-gateway}"
LOCAL_BASE="${LUMENCORE_LOCAL_GATEWAY_BASE:-http://127.0.0.1:8787}"
PUBLIC_BASE="${LUMENCORE_PUBLIC_GATEWAY_BASE:-https://lumen-core.ai}"
EXPECTED_CONTRACT_SHA="${LUMENCORE_EXPECTED_PUBLIC_CONTRACT_SHA256:-}"
EXPECTED_FACADE_SHA="${LUMENCORE_EXPECTED_GATEWAY_FACADE_SHA256:-}"
EXPECTED_LEGACY_SHA="${LUMENCORE_EXPECTED_GATEWAY_LEGACY_SHA256:-}"
PROBE_ATTEMPTS="${LUMENCORE_GATEWAY_PROBE_ATTEMPTS:-12}"
PROBE_DELAY_SECONDS="${LUMENCORE_GATEWAY_PROBE_DELAY_SECONDS:-2}"
APPLY=false
CONTRACT_CHANGED=false
FACADE_CHANGED=false
LEGACY_CHANGED=false
CONTRACT_HAD_TARGET=false
FACADE_HAD_TARGET=false
LEGACY_HAD_TARGET=false
REPAIR_COMPLETE=false
CONTRACT_ROLLBACK=""
FACADE_ROLLBACK=""
LEGACY_ROLLBACK=""

usage() {
  cat <<'EOF'
Usage:
  bash code/ops/REPAIR_GATEWAY_PUBLIC_CONTRACT_ON_VPS.sh
  sudo bash code/ops/REPAIR_GATEWAY_PUBLIC_CONTRACT_ON_VPS.sh --apply

Inspect-only mode validates and compares all three source files without writing.
Apply mode requires root, installs the fixed booth projection, default-deny
gateway facade, and private-identifier-safe legacy provider; restarts only
luma-gateway when needed; and rolls all files back unless bounded health,
booth, and blocked-route probes pass. Apply also requires a private
LUMA_HUMAN_UNLOCK_TOKEN of at least 32 characters and at least 1 MiB of free
space on the target filesystem.
EOF
}

for arg in "$@"; do
  case "$arg" in
    --apply) APPLY=true ;;
    -h|--help) usage; exit 0 ;;
    *) echo "ERROR: unknown argument: $arg" >&2; usage >&2; exit 2 ;;
  esac
done

if [[ "$APPLY" == true ]]; then
  human_unlock_token="${LUMA_HUMAN_UNLOCK_TOKEN:-}"
  if (( ${#human_unlock_token} < 32 )); then
    echo "ERROR: --apply requires a private HumanUnlock value of at least 32 characters" >&2
    exit 2
  fi
  unset human_unlock_token LUMA_HUMAN_UNLOCK_TOKEN
fi

if ! [[ "$PROBE_ATTEMPTS" =~ ^[0-9]+$ ]] \
  || (( PROBE_ATTEMPTS < 1 || PROBE_ATTEMPTS > 30 )) \
  || ! [[ "$PROBE_DELAY_SECONDS" =~ ^[0-9]+$ ]] \
  || (( PROBE_DELAY_SECONDS < 1 || PROBE_DELAY_SECONDS > 10 )); then
  echo "ERROR: probe attempts/delay are outside bounded integer limits" >&2
  exit 2
fi

for required in python3 sha256sum; do
  command -v "$required" >/dev/null 2>&1 || {
    echo "ERROR: $required is required" >&2
    exit 3
  }
done
for source in "$CONTRACT_SOURCE" "$FACADE_SOURCE" "$LEGACY_SOURCE"; do
  [[ -f "$source" ]] || {
    echo "ERROR: staged source not found" >&2
    exit 5
  }
done

PYTHONDONTWRITEBYTECODE=1 python3 - "$CONTRACT_SOURCE" "$FACADE_SOURCE" "$LEGACY_SOURCE" <<'PY'
import ast
import sys
from pathlib import Path

contract_path = Path(sys.argv[1])
facade_path = Path(sys.argv[2])
legacy_path = Path(sys.argv[3])
ast.parse(contract_path.read_text(encoding="utf-8"))
facade_text = facade_path.read_text(encoding="utf-8")
facade_tree = ast.parse(facade_text)
legacy_text = legacy_path.read_text(encoding="utf-8")
ast.parse(legacy_text)
names = {
    node.name
    for node in ast.walk(facade_tree)
    if isinstance(node, (ast.ClassDef, ast.FunctionDef))
}
assert "PublicGatewayAllowlistApp" in names
assert "public_gateway_request_allowed" in names
assert '"/health"' in facade_text
assert '"/api/master/booth-brief"' in facade_text
for env_name in (
    "LUMENCORE_PRIVATE_FOUNDER_DISPLAY_NAME",
    "LUMENCORE_PRIVATE_UEI",
    "LUMENCORE_PRIVATE_CAGE",
    "LUMENCORE_PRIVATE_EIN",
    "LUMENCORE_PRIVATE_PATENT_APPLICATION",
    "LUMENCORE_PRIVATE_PATENT_TITLE",
):
    assert env_name in legacy_text

sys.path.insert(0, str(contract_path.parent))
from booth_public_contract import public_booth_projection

projected = public_booth_projection(
    {
        "indexing": {"files_indexed": 7, "private_path": "/private/path"},
        "catalog": {"engine_count": 4, "unknown": {"secret": "synthetic"}},
    }
)
assert projected["schema"] == "lumencore.public_booth_contract.v2"
assert projected["supported_maturity_level"] == 3
assert projected["live_execution_authority"] is False
assert projected["profit_claim_allowed"] is False
assert projected["indexing"]["files_indexed"] == 7
assert "private_path" not in projected["indexing"]
assert "unknown" not in projected["catalog"]
assert "live_execution" not in projected
PY

sha_of() {
  sha256sum "$1" | awk '{print $1}'
}

validate_expected_sha() {
  local expected="$1"
  local observed="$2"
  if [[ -n "$expected" ]]; then
    [[ "$expected" =~ ^[0-9a-fA-F]{64}$ ]] || return 1
    [[ "${expected,,}" == "${observed,,}" ]] || return 1
  fi
}

CONTRACT_SOURCE_SHA="$(sha_of "$CONTRACT_SOURCE")"
FACADE_SOURCE_SHA="$(sha_of "$FACADE_SOURCE")"
LEGACY_SOURCE_SHA="$(sha_of "$LEGACY_SOURCE")"
validate_expected_sha "$EXPECTED_CONTRACT_SHA" "$CONTRACT_SOURCE_SHA" || {
  echo "ERROR: staged public contract does not match its expected SHA-256" >&2
  exit 6
}
validate_expected_sha "$EXPECTED_FACADE_SHA" "$FACADE_SOURCE_SHA" || {
  echo "ERROR: staged gateway facade does not match its expected SHA-256" >&2
  exit 6
}
validate_expected_sha "$EXPECTED_LEGACY_SHA" "$LEGACY_SOURCE_SHA" || {
  echo "ERROR: staged legacy gateway does not match its expected SHA-256" >&2
  exit 6
}

CONTRACT_TARGET_SHA="missing"
FACADE_TARGET_SHA="missing"
LEGACY_TARGET_SHA="missing"
[[ -f "$CONTRACT_TARGET" ]] && CONTRACT_TARGET_SHA="$(sha_of "$CONTRACT_TARGET")"
[[ -f "$FACADE_TARGET" ]] && FACADE_TARGET_SHA="$(sha_of "$FACADE_TARGET")"
[[ -f "$LEGACY_TARGET" ]] && LEGACY_TARGET_SHA="$(sha_of "$LEGACY_TARGET")"

echo "Public contract source SHA-256: $CONTRACT_SOURCE_SHA"
echo "Public contract target SHA-256: $CONTRACT_TARGET_SHA"
echo "Gateway facade source SHA-256: $FACADE_SOURCE_SHA"
echo "Gateway facade target SHA-256: $FACADE_TARGET_SHA"
echo "Legacy gateway source SHA-256: $LEGACY_SOURCE_SHA"
echo "Legacy gateway target SHA-256: $LEGACY_TARGET_SHA"

if [[ "$APPLY" != true ]]; then
  command -v systemctl >/dev/null 2>&1 && systemctl is-active "$SERVICE" 2>/dev/null || true
  exit 0
fi

[[ "${EUID}" -eq 0 ]] || {
  echo "ERROR: --apply must run as root" >&2
  exit 7
}
for required in systemctl curl; do
  command -v "$required" >/dev/null 2>&1 || {
    echo "ERROR: $required is required" >&2
    exit 8
  }
done
systemctl cat "$SERVICE" >/dev/null
TARGET_PARENT="$(dirname -- "$CONTRACT_TARGET")"
AVAILABLE_KB="$(df -Pk "$TARGET_PARENT" | awk 'NR == 2 {print $4}')"
if ! [[ "$AVAILABLE_KB" =~ ^[0-9]+$ ]] || (( AVAILABLE_KB < 1024 )); then
  echo "ERROR: at least 1 MiB of free target-filesystem space is required" >&2
  exit 9
fi
install -d -o root -g root -m 755 "$(dirname -- "$CONTRACT_TARGET")"
install -d -o root -g root -m 755 "$(dirname -- "$FACADE_TARGET")"
install -d -o root -g root -m 755 "$(dirname -- "$LEGACY_TARGET")"

STAMP="$(date -u +%Y%m%dT%H%M%SZ)"
CONTRACT_ROLLBACK="${CONTRACT_TARGET}.deploy-rollback.${STAMP}"
FACADE_ROLLBACK="${FACADE_TARGET}.deploy-rollback.${STAMP}"
LEGACY_ROLLBACK="${LEGACY_TARGET}.deploy-rollback.${STAMP}"

rollback() {
  local rc="${1:-1}"
  if [[ "$REPAIR_COMPLETE" != true ]]; then
    echo "Rolling back gateway facade, legacy provider, and public contract..." >&2
    if [[ "$CONTRACT_CHANGED" == true ]]; then
      if [[ "$CONTRACT_HAD_TARGET" == true ]]; then
        cp -a -- "$CONTRACT_ROLLBACK" "$CONTRACT_TARGET"
      else
        rm -f -- "$CONTRACT_TARGET"
      fi
    fi
    if [[ "$FACADE_CHANGED" == true ]]; then
      if [[ "$FACADE_HAD_TARGET" == true ]]; then
        cp -a -- "$FACADE_ROLLBACK" "$FACADE_TARGET"
      else
        rm -f -- "$FACADE_TARGET"
      fi
    fi
    if [[ "$LEGACY_CHANGED" == true ]]; then
      if [[ "$LEGACY_HAD_TARGET" == true ]]; then
        cp -a -- "$LEGACY_ROLLBACK" "$LEGACY_TARGET"
      else
        rm -f -- "$LEGACY_TARGET"
      fi
    fi
    systemctl restart "$SERVICE" || true
  fi
  exit "$rc"
}

trap 'rc=$?; echo "ERROR: gateway repair stopped on line $LINENO" >&2; rollback "$rc"' ERR
trap 'rollback 130' INT TERM

if [[ "$CONTRACT_SOURCE_SHA" != "$CONTRACT_TARGET_SHA" ]]; then
  if [[ -f "$CONTRACT_TARGET" ]]; then
    CONTRACT_HAD_TARGET=true
    cp -a -- "$CONTRACT_TARGET" "$CONTRACT_ROLLBACK"
  fi
  CONTRACT_CHANGED=true
  install -o root -g root -m 0644 "$CONTRACT_SOURCE" "$CONTRACT_TARGET"
fi
if [[ "$FACADE_SOURCE_SHA" != "$FACADE_TARGET_SHA" ]]; then
  if [[ -f "$FACADE_TARGET" ]]; then
    FACADE_HAD_TARGET=true
    cp -a -- "$FACADE_TARGET" "$FACADE_ROLLBACK"
  fi
  FACADE_CHANGED=true
  install -o root -g root -m 0644 "$FACADE_SOURCE" "$FACADE_TARGET"
fi
if [[ "$LEGACY_SOURCE_SHA" != "$LEGACY_TARGET_SHA" ]]; then
  if [[ -f "$LEGACY_TARGET" ]]; then
    LEGACY_HAD_TARGET=true
    cp -a -- "$LEGACY_TARGET" "$LEGACY_ROLLBACK"
  fi
  LEGACY_CHANGED=true
  install -o root -g root -m 0644 "$LEGACY_SOURCE" "$LEGACY_TARGET"
fi

[[ "$(sha_of "$CONTRACT_TARGET")" == "$CONTRACT_SOURCE_SHA" ]]
[[ "$(sha_of "$FACADE_TARGET")" == "$FACADE_SOURCE_SHA" ]]
[[ "$(sha_of "$LEGACY_TARGET")" == "$LEGACY_SOURCE_SHA" ]]
if [[ "$CONTRACT_CHANGED" == true || "$FACADE_CHANGED" == true || "$LEGACY_CHANGED" == true ]]; then
  systemctl restart "$SERVICE"
fi

probe_status() {
  local base="$1"
  local method="$2"
  local path="$3"
  local output="$4"
  curl -sS --connect-timeout 2 --max-time 5 -X "$method" -o "$output" -w '%{http_code}' \
    "${base}${path}?deploy=${STAMP}" || true
}

probe_until_status() {
  local base="$1"
  local method="$2"
  local path="$3"
  local output="$4"
  local expected="$5"
  local attempt observed
  for ((attempt = 1; attempt <= PROBE_ATTEMPTS; attempt += 1)); do
    observed="$(probe_status "$base" "$method" "$path" "$output")"
    if [[ "$observed" == "$expected" ]]; then
      return 0
    fi
    if (( attempt < PROBE_ATTEMPTS )); then
      sleep "$PROBE_DELAY_SECONDS"
    fi
  done
  echo "ERROR: bounded probe did not reach expected status path=${path} expected=${expected} observed=${observed:-000}" >&2
  return 1
}

LOCAL_HEALTH="$(mktemp)"
LOCAL_BOOTH="$(mktemp)"
LOCAL_PRIVATE="$(mktemp)"
PUBLIC_HEALTH="$(mktemp)"
PUBLIC_BOOTH="$(mktemp)"
PUBLIC_PRIVATE="$(mktemp)"
trap 'rm -f "$LOCAL_HEALTH" "$LOCAL_BOOTH" "$LOCAL_PRIVATE" "$PUBLIC_HEALTH" "$PUBLIC_BOOTH" "$PUBLIC_PRIVATE"' EXIT

probe_until_status "$LOCAL_BASE" GET /health "$LOCAL_HEALTH" 200
probe_until_status "$LOCAL_BASE" GET /api/master/booth-brief "$LOCAL_BOOTH" 200
probe_until_status "$LOCAL_BASE" GET /api/master/approval-queue "$LOCAL_PRIVATE" 404
probe_until_status "$PUBLIC_BASE" GET /health "$PUBLIC_HEALTH" 200
probe_until_status "$PUBLIC_BASE" GET /api/master/booth-brief "$PUBLIC_BOOTH" 200
probe_until_status "$PUBLIC_BASE" GET /api/master/approval-queue "$PUBLIC_PRIVATE" 404

python3 -m json.tool "$LOCAL_HEALTH" >/dev/null
python3 -m json.tool "$PUBLIC_HEALTH" >/dev/null
python3 - "$LOCAL_BOOTH" "$PUBLIC_BOOTH" <<'PY'
import json
import sys
from pathlib import Path

for value in sys.argv[1:]:
    payload = json.loads(Path(value).read_text(encoding="utf-8"))
    assert payload["schema"] == "lumencore.public_booth_contract.v2"
    assert payload["supported_maturity_level"] == 3
    assert payload["public_claim_allowed"] is False
    assert payload["live_execution_authority"] is False
PY

REPAIR_COMPLETE=true
trap - ERR INT TERM
echo "OK: gateway facade and fixed public booth contract passed bounded probes."
