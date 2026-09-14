#!/usr/bin/env bash
# Repair the exact reviewed gateway runtime closure: source plus service identity.
# Inspect-only by default. --apply is the only write path.
set -Eeuo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
SOURCE_ROOT="${LUMENCORE_GATEWAY_SOURCE_ROOT:-${SCRIPT_DIR}/..}"
TARGET_ROOT="${LUMENCORE_GATEWAY_TARGET_ROOT:-/opt/lumencore/code}"
STACK_ROOT="${LUMENCORE_GATEWAY_STACK_ROOT:-/opt/lumencore}"
PYTHON_BIN="${LUMENCORE_GATEWAY_PYTHON:-/opt/lumencore/.venv/bin/python}"
SERVICE="${LUMENCORE_GATEWAY_SERVICE:-luma-gateway}"
SERVICE_USER="${LUMENCORE_GATEWAY_SERVICE_USER:-lumencore}"
SERVICE_GROUP="${LUMENCORE_GATEWAY_SERVICE_GROUP:-lumencore}"
RUN_DIR="${LUMENCORE_GATEWAY_RUN_DIR:-${STACK_ROOT}/run}"
SERVICE_DROP_IN_DIR="${LUMENCORE_GATEWAY_SERVICE_DROP_IN_DIR:-/etc/systemd/system/luma-gateway.service.d}"
SERVICE_DROP_IN="${LUMENCORE_GATEWAY_SERVICE_DROP_IN:-${SERVICE_DROP_IN_DIR}/20-lumencore-runtime-hardening.conf}"
LOCK_FILE="${LUMENCORE_GATEWAY_LOCK_FILE:-${STACK_ROOT}/run/luma_experience_gateway.lock}"
LOCAL_HEALTH_URL="${LUMENCORE_LOCAL_HEALTH_URL:-http://127.0.0.1:8787/health}"
PUBLIC_HEALTH_URL="${LUMENCORE_PUBLIC_HEALTH_URL:-https://lumen-core.ai/health}"
LOCAL_STATUS_URL="${LUMENCORE_LOCAL_STATUS_URL:-http://127.0.0.1:8787/api/public/status}"
PUBLIC_STATUS_URL="${LUMENCORE_PUBLIC_STATUS_URL:-https://lumen-core.ai/api/public/status}"
LOCAL_GATEWAY_BASE_URL="${LUMENCORE_LOCAL_GATEWAY_BASE_URL:-http://127.0.0.1:8787}"
PUBLIC_GATEWAY_BASE_URL="${LUMENCORE_PUBLIC_GATEWAY_BASE_URL:-https://lumen-core.ai}"
EXPECTED_BUNDLE_SHA="${LUMENCORE_EXPECTED_GATEWAY_BUNDLE_SHA256:-}"
EXPECTED_HARDENING_SHA="${LUMENCORE_EXPECTED_GATEWAY_HARDENING_SHA256:-}"
SOURCE_COMMIT="${LUMENCORE_GATEWAY_SOURCE_COMMIT:-}"
HUMAN_UNLOCK_FILE="${LUMENCORE_HUMAN_UNLOCK_FILE:-}"
APPLY=false
PRINT_FILES=false
PRINT_BUNDLE_SHA=false
PRINT_HARDENING_SHA=false
CHANGED=false
SERVICE_STOPPED=false
SERVICE_WAS_ACTIVE=false
REPAIR_COMPLETE=false
STAGE_DIR=""
BACKUP_DIR=""
HARDENING_FILE=""

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

# These exact anonymous probes close the reviewer-visible introspection surface.
# Query-string cache busters do not affect path matching in the ASGI boundary.
PROTECTED_OPERATOR_HTTP_PATHS=(
  "/metrics"
  "/openapi.json"
  "/docs"
  "/redoc"
)
PROTECTED_OPERATOR_WEBSOCKET_PATH="/ws"

usage() {
  cat <<'EOF'
Usage:
  bash code/ops/REPAIR_GATEWAY_PUBLIC_CONTRACT_ON_VPS.sh
  bash code/ops/REPAIR_GATEWAY_PUBLIC_CONTRACT_ON_VPS.sh --print-files
  bash code/ops/REPAIR_GATEWAY_PUBLIC_CONTRACT_ON_VPS.sh --bundle-sha
  bash code/ops/REPAIR_GATEWAY_PUBLIC_CONTRACT_ON_VPS.sh --hardening-sha
  sudo bash code/ops/REPAIR_GATEWAY_PUBLIC_CONTRACT_ON_VPS.sh --apply

Inspect mode validates every source, computes the deterministic bundle digest,
and compares source and target SHA-256 values without writing. It also reports
the deterministic systemd hardening digest and the current effective gateway
identity. Apply mode
requires root, a bounded private HumanUnlock file, exact production target
identities, exact expected source and service-hardening digests, and a full
source commit. It stages and validates the entire gateway import closure,
stops only luma-gateway, installs the exact files and a bounded systemd drop-in,
migrates only the gateway run directory to lumencore:lumencore mode 750,
removes only a verified dead-PID singleton lock, and restores source files,
service configuration, runtime-directory metadata, and prior service state on
failure unless identity, lock, source parity, all four public/local JSON
contracts, every anonymous HTTP introspection boundary, and the anonymous
WebSocket upgrade boundary pass.
EOF
}

for arg in "$@"; do
  case "$arg" in
    --apply) APPLY=true ;;
    --print-files) PRINT_FILES=true ;;
    --bundle-sha) PRINT_BUNDLE_SHA=true ;;
    --hardening-sha) PRINT_HARDENING_SHA=true ;;
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

write_service_hardening() {
  local destination="$1"
  cat > "$destination" <<'EOF'
[Unit]
StartLimitIntervalSec=300
StartLimitBurst=10

[Service]
User=lumencore
Group=lumencore
Restart=on-failure
RestartSec=3
UMask=0027
NoNewPrivileges=true
PrivateTmp=true
EOF
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
HARDENING_FILE="$(mktemp)"
cleanup_manifest() {
  rm -f -- "$MANIFEST_FILE"
  if [[ -n "$HARDENING_FILE" ]]; then
    rm -f -- "$HARDENING_FILE"
    HARDENING_FILE=""
  fi
}
trap cleanup_manifest EXIT
for rel in "${BUNDLE_FILES[@]}"; do
  manifest_line "$rel" >> "$MANIFEST_FILE"
done
BUNDLE_SHA="$(sha256sum "$MANIFEST_FILE" | awk '{print $1}')"
write_service_hardening "$HARDENING_FILE"
HARDENING_SHA="$(sha256sum "$HARDENING_FILE" | awk '{print $1}')"

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

if [[ -n "$EXPECTED_HARDENING_SHA" ]]; then
  [[ "$EXPECTED_HARDENING_SHA" =~ ^[0-9a-fA-F]{64}$ ]] || {
    echo "ERROR: expected gateway hardening SHA-256 must be exactly 64 hexadecimal characters" >&2
    exit 7
  }
  [[ "${EXPECTED_HARDENING_SHA,,}" == "$HARDENING_SHA" ]] || {
    echo "ERROR: service hardening does not match the approved SHA-256" >&2
    exit 7
  }
fi

if [[ "$PRINT_BUNDLE_SHA" == true ]]; then
  printf '%s\n' "$BUNDLE_SHA"
  exit 0
fi

if [[ "$PRINT_HARDENING_SHA" == true ]]; then
  printf '%s\n' "$HARDENING_SHA"
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
printf 'Gateway service hardening SHA-256: %s\n' "$HARDENING_SHA"
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
    systemctl show "$SERVICE" \
      --property=User \
      --property=Group \
      --property=Restart \
      --property=UMask \
      --property=NoNewPrivileges \
      --property=PrivateTmp \
      --property=DropInPaths 2>/dev/null || true
  fi
  if [[ -e "$RUN_DIR" ]]; then
    printf 'Gateway run directory: '
    stat -c '%U:%G:%a:%F' "$RUN_DIR" 2>/dev/null || true
  else
    echo 'Gateway run directory: missing'
  fi
  if [[ -e "$LOCK_FILE" ]]; then
    printf 'Gateway singleton lock: '
    stat -c '%U:%G:%a:%F' "$LOCK_FILE" 2>/dev/null || true
  else
    echo 'Gateway singleton lock: missing'
  fi
  exit 0
fi

[[ -n "$EXPECTED_BUNDLE_SHA" ]] || {
  echo "ERROR: --apply requires an exact expected gateway bundle SHA-256" >&2
  exit 7
}
[[ -n "$EXPECTED_HARDENING_SHA" ]] || {
  echo "ERROR: --apply requires an exact expected gateway hardening SHA-256" >&2
  exit 7
}
[[ "$SOURCE_COMMIT" =~ ^[0-9a-f]{40}$ ]] || {
  echo "ERROR: --apply requires the exact 40-character source commit" >&2
  exit 8
}

[[ "${EUID}" -eq 0 ]] || {
  echo "ERROR: --apply must run as root" >&2
  exit 9
}
for required_command in \
  systemctl curl install cp stat mktemp id getent chown chmod dirname rmdir \
  awk grep seq sleep tr; do
  command -v "$required_command" >/dev/null 2>&1 || {
    echo "ERROR: $required_command is required" >&2
    exit 10
  }
done
[[ "$TARGET_ROOT" == "/opt/lumencore/code" \
  && "$STACK_ROOT" == "/opt/lumencore" \
  && "$PYTHON_BIN" == "/opt/lumencore/.venv/bin/python" \
  && "$SERVICE" == "luma-gateway" \
  && "$SERVICE_USER" == "lumencore" \
  && "$SERVICE_GROUP" == "lumencore" \
  && "$RUN_DIR" == "/opt/lumencore/run" \
  && "$SERVICE_DROP_IN_DIR" == "/etc/systemd/system/luma-gateway.service.d" \
  && "$SERVICE_DROP_IN" == "/etc/systemd/system/luma-gateway.service.d/20-lumencore-runtime-hardening.conf" \
  && "$LOCK_FILE" == "/opt/lumencore/run/luma_experience_gateway.lock" \
  && "$LOCAL_HEALTH_URL" == "http://127.0.0.1:8787/health" \
  && "$PUBLIC_HEALTH_URL" == "https://lumen-core.ai/health" \
  && "$LOCAL_STATUS_URL" == "http://127.0.0.1:8787/api/public/status" \
  && "$PUBLIC_STATUS_URL" == "https://lumen-core.ai/api/public/status" \
  && "$LOCAL_GATEWAY_BASE_URL" == "http://127.0.0.1:8787" \
  && "$PUBLIC_GATEWAY_BASE_URL" == "https://lumen-core.ai" ]] || {
  echo "ERROR: apply target, service, lock, runtime, or probe identity is not approved" >&2
  exit 11
}
[[ "$HUMAN_UNLOCK_FILE" =~ ^/tmp/lumencore-gateway-repair-[0-9]+-[0-9]+/human-unlock$ ]] || {
  echo "ERROR: --apply requires the bounded private HumanUnlock file" >&2
  exit 12
}
[[ -f "$HUMAN_UNLOCK_FILE" && ! -L "$HUMAN_UNLOCK_FILE" ]] || {
  echo "ERROR: private HumanUnlock file is missing or symbolic" >&2
  exit 12
}
[[ "$(stat -c '%U:%a' "$HUMAN_UNLOCK_FILE")" == "opc:600" ]] || {
  echo "ERROR: private HumanUnlock file ownership or mode is unsafe" >&2
  exit 12
}
human_unlock_token="$(<"$HUMAN_UNLOCK_FILE")"
if [[ ${#human_unlock_token} -lt 32 ]]; then
  echo "ERROR: --apply requires a private HumanUnlock value of at least 32 characters" >&2
  exit 12
fi
unset human_unlock_token
service_uid="$(id -u "$SERVICE_USER" 2>/dev/null)" || {
  echo "ERROR: required gateway service account does not exist" >&2
  exit 13
}
[[ "$service_uid" -ne 0 ]] || {
  echo "ERROR: refusing to run the gateway as root" >&2
  exit 13
}
[[ "$(id -gn "$SERVICE_USER" 2>/dev/null)" == "$SERVICE_GROUP" ]] || {
  echo "ERROR: gateway service account primary group is not approved" >&2
  exit 13
}
getent group "$SERVICE_GROUP" >/dev/null || {
  echo "ERROR: required gateway service group does not exist" >&2
  exit 13
}
[[ -x "$PYTHON_BIN" ]] || {
  echo "ERROR: gateway Python runtime is not executable" >&2
  exit 13
}
systemctl cat "$SERVICE" >/dev/null
if [[ -e "$SERVICE_DROP_IN_DIR" ]]; then
  [[ -d "$SERVICE_DROP_IN_DIR" && ! -L "$SERVICE_DROP_IN_DIR" ]] || {
    echo "ERROR: gateway service drop-in directory is not a regular directory" >&2
    exit 13
  }
else
  [[ -d "/etc/systemd/system" && ! -L "/etc/systemd/system" ]] || {
    echo "ERROR: systemd configuration root is not an approved directory" >&2
    exit 13
  }
fi
if [[ -e "$SERVICE_DROP_IN" ]]; then
  [[ -f "$SERVICE_DROP_IN" && ! -L "$SERVICE_DROP_IN" ]] || {
    echo "ERROR: gateway service drop-in is not a regular file" >&2
    exit 13
  }
fi
if [[ -e "$RUN_DIR" ]]; then
  [[ -d "$RUN_DIR" && ! -L "$RUN_DIR" ]] || {
    echo "ERROR: gateway run path is not a regular directory" >&2
    exit 13
  }
else
  [[ -d "$STACK_ROOT" && ! -L "$STACK_ROOT" ]] || {
    echo "ERROR: gateway stack root is not an approved directory" >&2
    exit 13
  }
fi

STAGE_DIR="$(mktemp -d /tmp/lumencore-gateway-stage.XXXXXX)"
BACKUP_DIR="$(mktemp -d /tmp/lumencore-gateway-rollback.XXXXXX)"
chmod 0700 "$STAGE_DIR" "$BACKUP_DIR"

cleanup() {
  if [[ -n "$STAGE_DIR" ]]; then
    [[ "$STAGE_DIR" =~ ^/tmp/lumencore-gateway-stage\.[A-Za-z0-9]+$ ]] || {
      echo "ERROR: refusing unexpected gateway-stage cleanup target" >&2
      return 1
    }
    rm -rf -- "$STAGE_DIR"
    STAGE_DIR=""
  fi
  if [[ -n "$BACKUP_DIR" ]]; then
    [[ "$BACKUP_DIR" =~ ^/tmp/lumencore-gateway-rollback\.[A-Za-z0-9]+$ ]] || {
      echo "ERROR: refusing unexpected gateway-rollback cleanup target" >&2
      return 1
    }
    rm -rf -- "$BACKUP_DIR"
    BACKUP_DIR=""
  fi
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
    install -d -m 0700 -- "$(dirname -- "$BACKUP_DIR/existing/$rel")"
    cp -a -- "$target" "$BACKUP_DIR/existing/$rel"
  else
    printf '%s\n' "$rel" >> "$BACKUP_DIR/missing-before.txt"
  fi
done

install -m 0644 -- "$HARDENING_FILE" "$STAGE_DIR/20-lumencore-runtime-hardening.conf"
[[ "$(sha256sum "$STAGE_DIR/20-lumencore-runtime-hardening.conf" | awk '{print $1}')" == "$HARDENING_SHA" ]]

if [[ -f "$SERVICE_DROP_IN" ]]; then
  cp -a -- "$SERVICE_DROP_IN" "$BACKUP_DIR/service-drop-in.before"
  printf 'present\n' > "$BACKUP_DIR/service-drop-in.state"
else
  printf 'missing\n' > "$BACKUP_DIR/service-drop-in.state"
fi

if [[ -d "$SERVICE_DROP_IN_DIR" ]]; then
  stat -c '%u %g %a' "$SERVICE_DROP_IN_DIR" > "$BACKUP_DIR/service-drop-in-dir.metadata"
  printf 'present\n' > "$BACKUP_DIR/service-drop-in-dir.state"
else
  printf 'missing\n' > "$BACKUP_DIR/service-drop-in-dir.state"
fi

if [[ -d "$RUN_DIR" ]]; then
  stat -c '%u %g %a' "$RUN_DIR" > "$BACKUP_DIR/run-dir.metadata"
  printf 'present\n' > "$BACKUP_DIR/run-dir.state"
else
  printf 'missing\n' > "$BACKUP_DIR/run-dir.state"
fi

if systemctl is-active --quiet "$SERVICE"; then
  SERVICE_WAS_ACTIVE=true
fi
printf 'service_was_active=%s\n' "$SERVICE_WAS_ACTIVE" > "$BACKUP_DIR/service.state"

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

remove_verified_dead_lock() {
  if [[ ! -e "$LOCK_FILE" ]]; then
    return 0
  fi
  [[ -f "$LOCK_FILE" && ! -L "$LOCK_FILE" ]] || {
    echo "ERROR: singleton lock is not a regular file" >&2
    return 14
  }
  local lock_pid
  lock_pid="$(tr -d '[:space:]' < "$LOCK_FILE")"
  [[ "$lock_pid" =~ ^[1-9][0-9]*$ ]] || {
    echo "ERROR: singleton lock PID is not a positive integer" >&2
    return 14
  }
  if kill -0 "$lock_pid" 2>/dev/null; then
    echo "ERROR: singleton lock owner is still alive; refusing removal" >&2
    return 14
  fi
  rm -f -- "$LOCK_FILE"
  echo "Removed verified dead-PID gateway singleton lock."
}

rollback() {
  local rc="${1:-1}"
  set +e
  if [[ "$REPAIR_COMPLETE" != true ]]; then
    echo "Rolling back the complete gateway dependency closure and service identity..." >&2
    systemctl stop "$SERVICE" >/dev/null 2>&1 || true
    remove_verified_dead_lock || true
    for rel in "${BUNDLE_FILES[@]}"; do
      target="$TARGET_ROOT/$rel"
      backup="$BACKUP_DIR/existing/$rel"
      if [[ -f "$backup" ]]; then
        rm -f -- "$target"
        cp -a -- "$backup" "$target"
      else
        rm -f -- "$target"
      fi
    done

    rm -f -- "$SERVICE_DROP_IN"
    prior_drop_in_state="$(< "$BACKUP_DIR/service-drop-in.state")"
    if [[ "$prior_drop_in_state" == "present" ]]; then
      install -d -o root -g root -m 0755 -- "$SERVICE_DROP_IN_DIR"
      cp -a -- "$BACKUP_DIR/service-drop-in.before" "$SERVICE_DROP_IN"
    fi
    prior_drop_in_dir_state="$(< "$BACKUP_DIR/service-drop-in-dir.state")"
    if [[ "$prior_drop_in_dir_state" == "present" ]]; then
      read -r prior_drop_in_uid prior_drop_in_gid prior_drop_in_mode < \
        "$BACKUP_DIR/service-drop-in-dir.metadata"
      chown --no-dereference "$prior_drop_in_uid:$prior_drop_in_gid" "$SERVICE_DROP_IN_DIR"
      chmod "$prior_drop_in_mode" "$SERVICE_DROP_IN_DIR"
    else
      rmdir -- "$SERVICE_DROP_IN_DIR" >/dev/null 2>&1 || true
    fi

    prior_run_dir_state="$(< "$BACKUP_DIR/run-dir.state")"
    if [[ "$prior_run_dir_state" == "present" ]]; then
      read -r prior_run_uid prior_run_gid prior_run_mode < "$BACKUP_DIR/run-dir.metadata"
      chown --no-dereference "$prior_run_uid:$prior_run_gid" "$RUN_DIR"
      chmod "$prior_run_mode" "$RUN_DIR"
    else
      rmdir -- "$RUN_DIR" >/dev/null 2>&1 || true
    fi

    systemctl daemon-reload >/dev/null 2>&1 || true
    systemctl reset-failed "$SERVICE" >/dev/null 2>&1 || true
    if [[ "$SERVICE_WAS_ACTIVE" == true ]]; then
      systemctl start "$SERVICE" >/dev/null 2>&1 || true
    fi
    SERVICE_STOPPED=false
  fi
  exit "$rc"
}

trap 'rc=$?; echo "ERROR: gateway closure repair stopped on line $LINENO" >&2; rollback "$rc"' ERR
trap 'echo "Gateway closure repair interrupted." >&2; rollback 130' INT TERM

systemctl stop "$SERVICE"
SERVICE_STOPPED=true
remove_verified_dead_lock

install -d -o root -g root -m 0755 -- "$SERVICE_DROP_IN_DIR"
install -o root -g root -m 0644 -- \
  "$STAGE_DIR/20-lumencore-runtime-hardening.conf" "$SERVICE_DROP_IN"
[[ "$(sha256sum "$SERVICE_DROP_IN" | awk '{print $1}')" == "$HARDENING_SHA" ]] || {
  echo "ERROR: installed gateway service hardening SHA-256 mismatch" >&2
  exit 17
}
install -d -o "$SERVICE_USER" -g "$SERVICE_GROUP" -m 0750 -- "$RUN_DIR"
systemctl daemon-reload

POST_APPLY_HASH_MATCHES=0
printf '%-64s  %-64s  %s\n' "POST_APPLY_SOURCE_SHA256" "POST_APPLY_TARGET_SHA256" "RELATIVE_PATH"
for rel in "${BUNDLE_FILES[@]}"; do
  install -D -o root -g root -m 0644 -- "$STAGE_DIR/$rel" "$TARGET_ROOT/$rel"
  post_apply_source_sha="$(sha256sum "$SOURCE_ROOT/$rel" | awk '{print $1}')"
  post_apply_target_sha="$(sha256sum "$TARGET_ROOT/$rel" | awk '{print $1}')"
  printf '%-64s  %-64s  %s\n' "$post_apply_source_sha" "$post_apply_target_sha" "$rel"
  [[ "$post_apply_source_sha" == "$post_apply_target_sha" ]] || {
    echo "ERROR: post-apply source/target SHA-256 mismatch: $rel" >&2
    exit 17
  }
  POST_APPLY_HASH_MATCHES=$((POST_APPLY_HASH_MATCHES + 1))
done
printf 'POST_APPLY_HASH_PARITY=%s/%s\n' "$POST_APPLY_HASH_MATCHES" "${#BUNDLE_FILES[@]}"

systemctl reset-failed "$SERVICE" >/dev/null 2>&1 || true
systemctl start "$SERVICE"
SERVICE_STOPPED=false

systemctl is-active --quiet "$SERVICE" || {
  echo "ERROR: gateway service did not become active" >&2
  exit 18
}
effective_user="$(systemctl show "$SERVICE" --property=User --value)"
effective_group="$(systemctl show "$SERVICE" --property=Group --value)"
effective_restart="$(systemctl show "$SERVICE" --property=Restart --value)"
effective_umask="$(systemctl show "$SERVICE" --property=UMask --value)"
effective_no_new_privileges="$(systemctl show "$SERVICE" --property=NoNewPrivileges --value)"
effective_private_tmp="$(systemctl show "$SERVICE" --property=PrivateTmp --value)"
[[ "$effective_user" == "$SERVICE_USER" && "$effective_group" == "$SERVICE_GROUP" ]] || {
  echo "ERROR: effective gateway service identity is not lumencore:lumencore" >&2
  exit 18
}
[[ "$effective_restart" == "on-failure" ]] || {
  echo "ERROR: effective gateway restart policy is not bounded to on-failure" >&2
  exit 18
}
[[ "$effective_umask" == "0027" ]] || {
  echo "ERROR: effective gateway umask is not 0027" >&2
  exit 18
}
[[ "$effective_no_new_privileges" == "yes" || "$effective_no_new_privileges" == "true" ]] || {
  echo "ERROR: effective gateway NoNewPrivileges control is not enabled" >&2
  exit 18
}
[[ "$effective_private_tmp" == "yes" || "$effective_private_tmp" == "true" ]] || {
  echo "ERROR: effective gateway PrivateTmp control is not enabled" >&2
  exit 18
}
[[ "$(stat -c '%U:%G:%a' "$SERVICE_DROP_IN")" == "root:root:644" ]] || {
  echo "ERROR: gateway service hardening file ownership or mode is unsafe" >&2
  exit 18
}
[[ "$(stat -c '%U:%G:%a' "$RUN_DIR")" == "${SERVICE_USER}:${SERVICE_GROUP}:750" ]] || {
  echo "ERROR: gateway run directory identity is not bounded" >&2
  exit 18
}

lock_ready=false
for attempt in $(seq 1 12); do
  if [[ -f "$LOCK_FILE" && ! -L "$LOCK_FILE" ]]; then
    main_pid="$(systemctl show "$SERVICE" --property=MainPID --value)"
    lock_pid="$(tr -d '[:space:]' < "$LOCK_FILE")"
    if [[ "$main_pid" =~ ^[1-9][0-9]*$ && "$lock_pid" == "$main_pid" ]]; then
      lock_ready=true
      break
    fi
  fi
  sleep 1
done
[[ "$lock_ready" == true ]] || {
  echo "ERROR: gateway singleton lock did not bind to the systemd main PID" >&2
  exit 18
}
[[ "$(stat -c '%U:%G:%a' "$LOCK_FILE")" == "${SERVICE_USER}:${SERVICE_GROUP}:640" ]] || {
  echo "ERROR: gateway singleton lock identity is not bounded" >&2
  exit 18
}

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

probe_operator_http_boundary() {
  local url="$1"
  local body_file="$2"
  local header_file="$3"
  local status="000"
  local content_type=""
  local curl_result
  local normalized_headers
  local attempt
  for attempt in $(seq 1 12); do
    : > "$body_file"
    : > "$header_file"
    curl_result="$(curl -sS --max-time 15 \
      --header 'Cache-Control: no-cache' \
      --output "$body_file" \
      --dump-header "$header_file" \
      --write-out '%{http_code}\t%{content_type}' \
      "${url}?repair=${SOURCE_COMMIT:0:12}-${attempt}" || true)"
    IFS=$'\t' read -r status content_type <<< "$curl_result"
    if [[ "$status" == "401" || "$status" == "503" ]]; then
      if [[ "${content_type,,}" == application/json* ]] && \
        python3 - "$body_file" "$status" <<'PY'
import json
import sys
from pathlib import Path

payload = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
expected_detail = (
    "operator API authentication required"
    if sys.argv[2] == "401"
    else "operator API access unavailable"
)
assert payload == {"detail": expected_detail}
PY
      then
        normalized_headers="$(tr -d '\r' < "$header_file")"
        if grep -Eiq '^cache-control:[[:space:]]*no-store([[:space:]]|$)' \
          <<< "$normalized_headers" && \
          grep -Eiq '^pragma:[[:space:]]*no-cache([[:space:]]|$)' \
          <<< "$normalized_headers"; then
          if [[ "$status" != "401" ]] || \
            grep -Eiq '^www-authenticate:[[:space:]]*Bearer([[:space:]]|$)' \
              <<< "$normalized_headers"; then
            printf '%s\n' "$status"
            return 0
          fi
        fi
      fi
    fi
    sleep 3
  done
  printf '%s\n' "${status:-000}"
  return 1
}

probe_operator_websocket_boundary() {
  local url="$1"
  local output="$2"
  local allow_not_found="${3:-false}"
  local status="000"
  local attempt
  for attempt in $(seq 1 12); do
    status="$(curl -sS --max-time 15 --http1.1 \
      --header 'Cache-Control: no-cache' \
      --header 'Connection: Upgrade' \
      --header 'Upgrade: websocket' \
      --header 'Sec-WebSocket-Key: dGhlIHNhbXBsZSBub25jZQ==' \
      --header 'Sec-WebSocket-Version: 13' \
      --output "$output" \
      --write-out '%{http_code}' \
      "${url}?repair=${SOURCE_COMMIT:0:12}-${attempt}" || true)"
    if [[ "$status" == "403" || ( "$allow_not_found" == "true" && "$status" == "404" ) ]]; then
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
OPERATOR_HTTP_BODY="$(mktemp)"
OPERATOR_HTTP_HEADERS="$(mktemp)"
OPERATOR_WEBSOCKET_BODY="$(mktemp)"
trap 'rm -f -- "$LOCAL_HEALTH_BODY" "$PUBLIC_HEALTH_BODY" "$LOCAL_STATUS_BODY" "$PUBLIC_STATUS_BODY" "$OPERATOR_HTTP_BODY" "$OPERATOR_HTTP_HEADERS" "$OPERATOR_WEBSOCKET_BODY"; cleanup' EXIT

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

LOCAL_OPERATOR_HTTP_STATUSES=()
PUBLIC_OPERATOR_HTTP_STATUSES=()
for path in "${PROTECTED_OPERATOR_HTTP_PATHS[@]}"; do
  route_label="${path#/}"
  route_label="${route_label//\//_}"
  route_label="${route_label//./_}"
  local_operator_status="$(
    probe_operator_http_boundary \
      "${LOCAL_GATEWAY_BASE_URL}${path}" \
      "$OPERATOR_HTTP_BODY" \
      "$OPERATOR_HTTP_HEADERS"
  )" || {
    echo "ERROR: local anonymous operator boundary failed for ${path} (HTTP ${local_operator_status:-000})" >&2
    rollback 19
  }
  public_operator_status="$(
    probe_operator_http_boundary \
      "${PUBLIC_GATEWAY_BASE_URL}${path}" \
      "$OPERATOR_HTTP_BODY" \
      "$OPERATOR_HTTP_HEADERS"
  )" || {
    echo "ERROR: public anonymous operator boundary failed for ${path} (HTTP ${public_operator_status:-000})" >&2
    rollback 20
  }
  LOCAL_OPERATOR_HTTP_STATUSES+=("${route_label}:${local_operator_status}")
  PUBLIC_OPERATOR_HTTP_STATUSES+=("${route_label}:${public_operator_status}")
done

LOCAL_OPERATOR_WEBSOCKET_STATUS="$(
  probe_operator_websocket_boundary \
    "${LOCAL_GATEWAY_BASE_URL}${PROTECTED_OPERATOR_WEBSOCKET_PATH}" \
    "$OPERATOR_WEBSOCKET_BODY"
)" || {
  echo "ERROR: local anonymous WebSocket boundary failed (HTTP ${LOCAL_OPERATOR_WEBSOCKET_STATUS:-000})" >&2
  rollback 21
}
PUBLIC_OPERATOR_WEBSOCKET_STATUS="$(
  probe_operator_websocket_boundary \
    "${PUBLIC_GATEWAY_BASE_URL}${PROTECTED_OPERATOR_WEBSOCKET_PATH}" \
    "$OPERATOR_WEBSOCKET_BODY" \
    true
)" || {
  echo "ERROR: public anonymous WebSocket boundary failed (HTTP ${PUBLIC_OPERATOR_WEBSOCKET_STATUS:-000})" >&2
  rollback 22
}

REPAIR_COMPLETE=true
trap - ERR INT TERM
echo "GATEWAY_RUNTIME_CLOSURE_REPAIR_OK"
echo "GATEWAY_DEPENDENCY_CLOSURE_REPAIR_OK"
echo "Source commit: $SOURCE_COMMIT"
echo "Bundle SHA-256: $BUNDLE_SHA"
echo "Service hardening SHA-256: $HARDENING_SHA"
echo "Effective service identity: ${effective_user}:${effective_group}"
echo "Effective restart/umask/no-new-privileges/private-tmp: ${effective_restart}/${effective_umask}/${effective_no_new_privileges}/${effective_private_tmp}"
echo "Run directory identity: $(stat -c '%U:%G:%a' "$RUN_DIR")"
echo "Singleton lock identity: $(stat -c '%U:%G:%a' "$LOCK_FILE") pid_matches_main=true"
echo "Local health HTTP: $LOCAL_HEALTH_STATUS | Public health HTTP: $PUBLIC_HEALTH_STATUS"
echo "Local status HTTP: $LOCAL_PUBLIC_STATUS | Public status HTTP: $PUBLIC_PUBLIC_STATUS"
echo "Local anonymous operator HTTP boundaries: ${LOCAL_OPERATOR_HTTP_STATUSES[*]}"
echo "Public anonymous operator HTTP boundaries: ${PUBLIC_OPERATOR_HTTP_STATUSES[*]}"
echo "Local anonymous WebSocket boundary: ws:${LOCAL_OPERATOR_WEBSOCKET_STATUS}"
echo "Public anonymous WebSocket boundary: ws:${PUBLIC_OPERATOR_WEBSOCKET_STATUS}"
