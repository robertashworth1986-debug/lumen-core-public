#!/usr/bin/env bash
# Repair the exact reviewed gateway entrypoint and its local import closure.
# Inspect-only by default. --apply is the only write path.
set -Eeuo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
SOURCE_ROOT="${LUMENCORE_GATEWAY_SOURCE_ROOT:-${SCRIPT_DIR}/..}"
TARGET_ROOT="${LUMENCORE_GATEWAY_TARGET_ROOT:-/opt/lumencore/code}"
STACK_ROOT="${LUMENCORE_GATEWAY_STACK_ROOT:-/opt/lumencore}"
PYTHON_BIN="${LUMENCORE_GATEWAY_PYTHON:-/opt/lumencore/.venv/bin/python}"
SERVICE="${LUMENCORE_GATEWAY_SERVICE:-luma-gateway}"
LOCK_FILE="${LUMENCORE_GATEWAY_LOCK_FILE:-${STACK_ROOT}/run/luma_experience_gateway.lock}"
LOCAL_HEALTH_URL="${LUMENCORE_LOCAL_HEALTH_URL:-http://127.0.0.1:8787/health}"
PUBLIC_HEALTH_URL="${LUMENCORE_PUBLIC_HEALTH_URL:-https://lumen-core.ai/health}"
LOCAL_STATUS_URL="${LUMENCORE_LOCAL_STATUS_URL:-http://127.0.0.1:8787/api/public/status}"
PUBLIC_STATUS_URL="${LUMENCORE_PUBLIC_STATUS_URL:-https://lumen-core.ai/api/public/status}"
EXPECTED_BUNDLE_SHA="${LUMENCORE_EXPECTED_GATEWAY_BUNDLE_SHA256:-}"
SOURCE_COMMIT="${LUMENCORE_GATEWAY_SOURCE_COMMIT:-}"
APPLY=false
PRINT_FILES=false
PRINT_BUNDLE_SHA=false
CHANGED=false
SERVICE_STOPPED=false
REPAIR_COMPLETE=false
STAGE_DIR=""
BACKUP_DIR=""

# This list is the recursively resolved local-Python import closure of the
# reviewed gateway entrypoint. Keep it explicit so a partial copy cannot be
# mistaken for a complete deployment.
BUNDLE_FILES=(
  "application_context_resolver.py"
  "autonomous_agent_manifest.py"
  "booth_public_contract.py"
  "execution/__init__.py"
  "execution/order_safety_gate.py"
  "forecast_api.py"
  "grant_application_factory.py"
  "grant_hunter_v2.py"
  "grant_submission_kit.py"
  "grants_api.py"
  "linkedin_oauth.py"
  "linkedin_router.py"
  "luma_experience_gateway.py"
  "luma_experience_gateway_legacy.py"
  "master_universe_benchmark.py"
  "master_universe_benchmark_v2.py"
  "meta_router.py"
  "operator_api_access.py"
  "opportunities_api.py"
  "universe_v2_fetchers.py"
)

usage() {
  cat <<'EOF'
Usage:
  bash code/ops/REPAIR_GATEWAY_PUBLIC_CONTRACT_ON_VPS.sh
  bash code/ops/REPAIR_GATEWAY_PUBLIC_CONTRACT_ON_VPS.sh --print-files
  bash code/ops/REPAIR_GATEWAY_PUBLIC_CONTRACT_ON_VPS.sh --bundle-sha
  sudo bash code/ops/REPAIR_GATEWAY_PUBLIC_CONTRACT_ON_VPS.sh --apply

Inspect mode validates every source, computes the deterministic bundle digest,
and compares source and target SHA-256 values without writing. Apply mode
requires root, a private HumanUnlock value, an exact expected bundle digest,
and a full source commit. It stages and validates the entire gateway import
closure, stops only luma-gateway, installs the exact files, removes only a
verified dead-PID singleton lock, and rolls every file back unless local and
public health plus the minimal public-status contract all pass.
EOF
}

for arg in "$@"; do
  case "$arg" in
    --apply) APPLY=true ;;
    --print-files) PRINT_FILES=true ;;
    --bundle-sha) PRINT_BUNDLE_SHA=true ;;
    -h|--help) usage; exit 0 ;;
    *) echo "ERROR: unknown argument: $arg" >&2; usage >&2; exit 2 ;;
  esac
done

if [[ "$PRINT_FILES" == true ]]; then
  printf '%s\n' "${BUNDLE_FILES[@]}"
  exit 0
fi

command -v python3 >/dev/null 2>&1 || {
  echo "ERROR: python3 is required" >&2
  exit 3
}
command -v sha256sum >/dev/null 2>&1 || {
  echo "ERROR: sha256sum is required" >&2
  exit 4
}
command -v realpath >/dev/null 2>&1 || {
  echo "ERROR: realpath is required" >&2
  exit 5
}

SOURCE_ROOT="$(realpath -e -- "$SOURCE_ROOT")"
TARGET_ROOT="$(realpath -m -- "$TARGET_ROOT")"
[[ -d "$SOURCE_ROOT" ]] || {
  echo "ERROR: gateway source root is not a directory" >&2
  exit 6
}
[[ "$TARGET_ROOT" == /* && "$TARGET_ROOT" != "/" ]] || {
  echo "ERROR: gateway target root must be a bounded absolute path" >&2
  exit 6
}

manifest_line() {
  local rel="$1"
  local source="$SOURCE_ROOT/$rel"
  [[ -f "$source" && ! -L "$source" ]] || {
    echo "ERROR: required regular source is missing or symbolic: $rel" >&2
    return 1
  }
  printf '%s  %s\n' "$(sha256sum "$source" | awk '{print $1}')" "$rel"
}

MANIFEST_FILE="$(mktemp)"
cleanup_manifest() {
  rm -f -- "$MANIFEST_FILE"
}
trap cleanup_manifest EXIT
for rel in "${BUNDLE_FILES[@]}"; do
  manifest_line "$rel" >> "$MANIFEST_FILE"
done
BUNDLE_SHA="$(sha256sum "$MANIFEST_FILE" | awk '{print $1}')"

if [[ -n "$EXPECTED_BUNDLE_SHA" ]]; then
  [[ "$EXPECTED_BUNDLE_SHA" =~ ^[0-9a-fA-F]{64}$ ]] || {
    echo "ERROR: expected gateway bundle SHA-256 must be exactly 64 hexadecimal characters" >&2
    exit 7
  }
  [[ "${EXPECTED_BUNDLE_SHA,,}" == "$BUNDLE_SHA" ]] || {
    echo "ERROR: source closure does not match the approved bundle SHA-256" >&2
    exit 7
  }
fi

if [[ "$PRINT_BUNDLE_SHA" == true ]]; then
  printf '%s\n' "$BUNDLE_SHA"
  exit 0
fi

python3 - "$SOURCE_ROOT" "${BUNDLE_FILES[@]}" <<'PY'
import ast
import sys
from pathlib import Path

root = Path(sys.argv[1])
for relative in sys.argv[2:]:
    source = root / relative
    ast.parse(source.read_text(encoding="utf-8"), filename=relative)
PY

printf 'Gateway bundle file count: %s\n' "${#BUNDLE_FILES[@]}"
printf 'Gateway bundle SHA-256: %s\n' "$BUNDLE_SHA"
printf 'Gateway source commit: %s\n' "${SOURCE_COMMIT:-not-declared}"
printf '%-64s  %-64s  %s\n' "SOURCE_SHA256" "TARGET_SHA256" "RELATIVE_PATH"
for rel in "${BUNDLE_FILES[@]}"; do
  source_sha="$(sha256sum "$SOURCE_ROOT/$rel" | awk '{print $1}')"
  target="$TARGET_ROOT/$rel"
  target_sha="missing"
  if [[ -L "$target" ]]; then
    target_sha="symbolic-target-blocked"
  elif [[ -f "$target" ]]; then
    target_sha="$(sha256sum "$target" | awk '{print $1}')"
  fi
  printf '%-64s  %-64s  %s\n' "$source_sha" "$target_sha" "$rel"
  if [[ "$source_sha" != "$target_sha" ]]; then
    CHANGED=true
  fi
done

if [[ "$APPLY" != true ]]; then
  if command -v systemctl >/dev/null 2>&1; then
    printf 'Gateway service active: '
    systemctl is-active "$SERVICE" 2>/dev/null || true
  fi
  exit 0
fi

[[ -n "$EXPECTED_BUNDLE_SHA" ]] || {
  echo "ERROR: --apply requires an exact expected gateway bundle SHA-256" >&2
  exit 7
}
[[ "$SOURCE_COMMIT" =~ ^[0-9a-f]{40}$ ]] || {
  echo "ERROR: --apply requires the exact 40-character source commit" >&2
  exit 8
}

human_unlock_token="${LUMA_HUMAN_UNLOCK_TOKEN:-}"
if [[ ${#human_unlock_token} -lt 32 ]]; then
  echo "ERROR: --apply requires a private HumanUnlock value of at least 32 characters" >&2
  exit 9
fi
unset human_unlock_token LUMA_HUMAN_UNLOCK_TOKEN

[[ "${EUID}" -eq 0 ]] || {
  echo "ERROR: --apply must run as root" >&2
  exit 10
}
for required_command in systemctl curl install cp stat mktemp; do
  command -v "$required_command" >/dev/null 2>&1 || {
    echo "ERROR: $required_command is required" >&2
    exit 11
  }
done
[[ -x "$PYTHON_BIN" ]] || {
  echo "ERROR: gateway Python runtime is not executable" >&2
  exit 12
}
systemctl cat "$SERVICE" >/dev/null

STAGE_DIR="$(mktemp -d /tmp/lumencore-gateway-stage.XXXXXX)"
BACKUP_DIR="$(mktemp -d /tmp/lumencore-gateway-rollback.XXXXXX)"
chmod 0700 "$STAGE_DIR" "$BACKUP_DIR"

cleanup() {
  rm -rf -- "$STAGE_DIR" "$BACKUP_DIR"
  cleanup_manifest
}
trap cleanup EXIT

for rel in "${BUNDLE_FILES[@]}"; do
  source="$SOURCE_ROOT/$rel"
  staged="$STAGE_DIR/$rel"
  target="$TARGET_ROOT/$rel"
  resolved_target="$(realpath -m -- "$target")"
  [[ "$resolved_target" == "$TARGET_ROOT/"* ]] || {
    echo "ERROR: target escaped the bounded gateway root: $rel" >&2
    exit 13
  }
  [[ ! -L "$target" ]] || {
    echo "ERROR: symbolic gateway target is not allowed: $rel" >&2
    exit 13
  }
  install -D -m 0644 -- "$source" "$staged"
  [[ "$(sha256sum "$staged" | awk '{print $1}')" == "$(sha256sum "$source" | awk '{print $1}')" ]]
  if [[ -f "$target" ]]; then
    install -D -m 0600 -- "$target" "$BACKUP_DIR/existing/$rel"
  else
    printf '%s\n' "$rel" >> "$BACKUP_DIR/missing-before.txt"
  fi
done

# Import the staged entrypoint against an isolated writable stack root before
# touching the running service. Target-root fallback supplies non-local assets,
# while every source-controlled local import in the explicit closure resolves
# from the stage directory first.
PREFLIGHT_ROOT="$STAGE_DIR/preflight-root"
install -d -m 0700 "$PREFLIGHT_ROOT/run" "$PREFLIGHT_ROOT/out" "$PREFLIGHT_ROOT/data"
PYTHONDONTWRITEBYTECODE=1 \
LUMA_STACK_ROOT="$PREFLIGHT_ROOT" \
LUMA_DASHBOARD_DIR="${LUMENCORE_GATEWAY_DASHBOARD_DIR:-${STACK_ROOT}/dashboard}" \
PYTHONPATH="$STAGE_DIR:$TARGET_ROOT" \
  "$PYTHON_BIN" - <<'PY'
import luma_experience_gateway as gateway

assert gateway.app is not None
assert gateway.ORDER_SAFETY_POLICY == "validate_only_fail_closed"
decision = gateway.evaluate_order_request(gateway.ADD_ORDER_PATH, {"type": "buy"})
assert decision.allowed is False
assert decision.mode == "blocked_live_order"
PY

rollback() {
  local rc="${1:-1}"
  set +e
  if [[ "$REPAIR_COMPLETE" != true ]]; then
    echo "Rolling back the complete gateway dependency closure..." >&2
    systemctl stop "$SERVICE" >/dev/null 2>&1 || true
    for rel in "${BUNDLE_FILES[@]}"; do
      target="$TARGET_ROOT/$rel"
      backup="$BACKUP_DIR/existing/$rel"
      if [[ -f "$backup" ]]; then
        install -D -o root -g root -m 0644 -- "$backup" "$target"
      else
        rm -f -- "$target"
      fi
    done
    systemctl reset-failed "$SERVICE" >/dev/null 2>&1 || true
    systemctl start "$SERVICE" >/dev/null 2>&1 || true
  fi
  exit "$rc"
}

trap 'rc=$?; echo "ERROR: gateway closure repair stopped on line $LINENO" >&2; rollback "$rc"' ERR
trap 'echo "Gateway closure repair interrupted." >&2; rollback 130' INT TERM

systemctl stop "$SERVICE"
SERVICE_STOPPED=true

if [[ -e "$LOCK_FILE" ]]; then
  [[ -f "$LOCK_FILE" && ! -L "$LOCK_FILE" ]] || {
    echo "ERROR: singleton lock is not a regular file" >&2
    exit 14
  }
  lock_pid="$(tr -d '[:space:]' < "$LOCK_FILE")"
  [[ "$lock_pid" =~ ^[1-9][0-9]*$ ]] || {
    echo "ERROR: singleton lock PID is not a positive integer" >&2
    exit 14
  }
  if kill -0 "$lock_pid" 2>/dev/null; then
    echo "ERROR: singleton lock owner is still alive; refusing removal" >&2
    exit 14
  fi
  rm -f -- "$LOCK_FILE"
  echo "Removed verified dead-PID gateway singleton lock."
fi

for rel in "${BUNDLE_FILES[@]}"; do
  install -D -o root -g root -m 0644 -- "$STAGE_DIR/$rel" "$TARGET_ROOT/$rel"
  [[ "$(sha256sum "$TARGET_ROOT/$rel" | awk '{print $1}')" == "$(sha256sum "$SOURCE_ROOT/$rel" | awk '{print $1}')" ]]
done

systemctl reset-failed "$SERVICE" >/dev/null 2>&1 || true
systemctl start "$SERVICE"
SERVICE_STOPPED=false

probe_json() {
  local url="$1"
  local output="$2"
  local status="000"
  local attempt
  for attempt in $(seq 1 12); do
    status="$(curl -sS --max-time 15 -o "$output" -w '%{http_code}' \
      "${url}?repair=${SOURCE_COMMIT:0:12}-${attempt}" || true)"
    if [[ "$status" == "200" ]] && python3 -m json.tool "$output" >/dev/null 2>&1; then
      printf '%s\n' "$status"
      return 0
    fi
    sleep 3
  done
  printf '%s\n' "$status"
  return 1
}

LOCAL_HEALTH_BODY="$(mktemp)"
PUBLIC_HEALTH_BODY="$(mktemp)"
LOCAL_STATUS_BODY="$(mktemp)"
PUBLIC_STATUS_BODY="$(mktemp)"
trap 'rm -f -- "$LOCAL_HEALTH_BODY" "$PUBLIC_HEALTH_BODY" "$LOCAL_STATUS_BODY" "$PUBLIC_STATUS_BODY"; cleanup' EXIT

LOCAL_HEALTH_STATUS="$(probe_json "$LOCAL_HEALTH_URL" "$LOCAL_HEALTH_BODY")" || {
  echo "ERROR: local gateway health failed (HTTP ${LOCAL_HEALTH_STATUS:-000})" >&2
  rollback 15
}
PUBLIC_HEALTH_STATUS="$(probe_json "$PUBLIC_HEALTH_URL" "$PUBLIC_HEALTH_BODY")" || {
  echo "ERROR: public gateway health failed (HTTP ${PUBLIC_HEALTH_STATUS:-000})" >&2
  rollback 16
}
LOCAL_PUBLIC_STATUS="$(probe_json "$LOCAL_STATUS_URL" "$LOCAL_STATUS_BODY")" || {
  echo "ERROR: local public-status contract failed (HTTP ${LOCAL_PUBLIC_STATUS:-000})" >&2
  rollback 17
}
PUBLIC_PUBLIC_STATUS="$(probe_json "$PUBLIC_STATUS_URL" "$PUBLIC_STATUS_BODY")" || {
  echo "ERROR: public public-status contract failed (HTTP ${PUBLIC_PUBLIC_STATUS:-000})" >&2
  rollback 18
}

for body in "$LOCAL_STATUS_BODY" "$PUBLIC_STATUS_BODY"; do
  python3 - "$body" <<'PY'
import json
import sys
from pathlib import Path

payload = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
assert payload == {
    "status": "ok",
    "service": "luma-experience-gateway",
    "access_boundary": "operator_api_v1",
    "public_surface": "minimal",
}
PY
done

for body in "$LOCAL_HEALTH_BODY" "$PUBLIC_HEALTH_BODY"; do
  python3 - "$body" <<'PY'
import json
import re
import sys
from pathlib import Path

payload = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
assert set(payload) == {
    "status",
    "service",
    "access_boundary",
    "public_surface",
    "generated_utc",
}
assert payload["status"] == "ok"
assert payload["service"] == "luma-experience-gateway"
assert payload["access_boundary"] == "operator_api_v1"
assert payload["public_surface"] == "minimal"
assert re.fullmatch(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z", payload["generated_utc"])
PY
done

REPAIR_COMPLETE=true
trap - ERR INT TERM
echo "GATEWAY_DEPENDENCY_CLOSURE_REPAIR_OK"
echo "Source commit: $SOURCE_COMMIT"
echo "Bundle SHA-256: $BUNDLE_SHA"
echo "Local health HTTP: $LOCAL_HEALTH_STATUS | Public health HTTP: $PUBLIC_HEALTH_STATUS"
echo "Local status HTTP: $LOCAL_PUBLIC_STATUS | Public status HTTP: $PUBLIC_PUBLIC_STATUS"
