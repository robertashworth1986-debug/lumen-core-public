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
RECOVERY_ROOT="/var/backups/lumencore-gateway-repair"
RECOVERY_MANIFEST_SHA=""
RECOVERY_TIMEOUT_BIN=""
RECOVERY_SERVICE_RESULTS=""
RECOVERY_SERVICE_FAILURE=""
RECOVERY_RESTORE_ATTEMPTED=false
RECOVERY_RESTORE_FAILURE=""
RECOVERY_RESTORE_EXIT_CODE=0
RECOVERY_RESTORE_TARGET=""
RECOVERY_DROPIN_RESULT=NOT_CHECKED
RECOVERY_RUNTIME_DIRECTORY_RESULT=NOT_CHECKED
RECOVERY_DROPIN_DIRECTORY_RESULT=NOT_CHECKED
DROPIN_WRITE_STATE=UNTOUCHED
DROPIN_TARGET_VERSION=""
DROPIN_DIR_WRITE_STATE=UNTOUCHED
DROPIN_DIR_TARGET_VERSION=""
DROPIN_DIR_CANDIDATE_METADATA="0:0:755"
RUN_WRITE_STATE=UNTOUCHED
RUN_TARGET_VERSION=""
RUN_CANDIDATE_METADATA=""
declare -A SOURCE_WRITE_STATES=() SOURCE_CANDIDATE_SHA=() SOURCE_TARGET_VERSION=() SOURCE_RESULT_STATES=()

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
Private recovery files and hash-bound receipts remain under
/var/backups/lumencore-gateway-repair after every exit, including helper success.
Their presence does not establish verified restoration or external verification.
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
require_recovery_timeout() {
  # Resolve a real GNU executable before any forward runtime mutation. The
  # recovery deadline is fixed code policy, never an environment override.
  RECOVERY_TIMEOUT_BIN="$(type -P timeout)" || return 10
  [[ -x "$RECOVERY_TIMEOUT_BIN" ]] || return 10
  local version
  version="$("$RECOVERY_TIMEOUT_BIN" --version)" || return 10
  [[ "$version" == 'timeout (GNU coreutils)'* ]] || return 10
}
require_recovery_timeout || {
  echo "ERROR: GNU timeout is required before gateway mutation" >&2
  exit 10
}
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
RUN_CANDIDATE_METADATA="${service_uid}:$(id -g "$SERVICE_USER"):750"
[[ "$RUN_CANDIDATE_METADATA" =~ ^[0-9]+:[0-9]+:750$ ]] || exit 13

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

require_safe_recovery_directory() {
  local directory="$1" private="${2:-false}" owner mode
  [[ -d "$directory" && ! -L "$directory" ]] || return 13
  owner="$(stat -c '%u' "$directory")"
  mode="$(stat -c '%a' "$directory")"
  [[ "$owner" == 0 && "$mode" =~ ^[0-7]{3,4}$ ]] || return 13
  (( (8#$mode & 0022) == 0 )) || return 13
  if [[ "$private" == true ]]; then
    [[ "$(stat -c '%u:%g:%a' "$directory")" == "0:0:700" ]] || return 13
  fi
}

prepare_recovery_directory() {
  local directory
  for directory in / /var /var/backups; do
    require_safe_recovery_directory "$directory" || return 13
  done
  if [[ -e "$RECOVERY_ROOT" || -L "$RECOVERY_ROOT" ]]; then
    require_safe_recovery_directory "$RECOVERY_ROOT" true || return 13
  else
    install -d -o root -g root -m 0700 -- "$RECOVERY_ROOT"
  fi
  [[ "$(realpath -e -- "$RECOVERY_ROOT")" == "$RECOVERY_ROOT" ]] || return 13
  require_safe_recovery_directory "$RECOVERY_ROOT" true || return 13
  BACKUP_DIR="$(mktemp -d "$RECOVERY_ROOT/recovery.XXXXXXXXXX")"
  require_safe_recovery_directory "$BACKUP_DIR" true || return 13
  printf 'Private gateway recovery directory: %s\n' "$BACKUP_DIR"
}

record_recovery_evidence() {
  local kind="$1" trigger_code="${2:-0}" requested_source="${3:-}"
  [[ $# -le 3 ]] || return 14
  [[ "$kind" != dropin_result || $# -eq 2 ]] || return 14
  [[ "$kind" != runtime_directory_result || $# -eq 2 ]] || return 14
  [[ "$kind" != dropin_directory_result || $# -eq 2 ]] || return 14
  local source_states="" source_relative
  for source_relative in "${BUNDLE_FILES[@]}"; do
    source_states+="$source_relative:${SOURCE_WRITE_STATES[$source_relative]:-UNKNOWN}:${SOURCE_CANDIDATE_SHA[$source_relative]:-}:${SOURCE_TARGET_VERSION[$source_relative]:-}:${SOURCE_RESULT_STATES[$source_relative]:-NOT_CHECKED}"$'\n'
  done
  python3 - "$BACKUP_DIR" "$kind" "$trigger_code" "$SOURCE_COMMIT" \
    "$BUNDLE_SHA" "$HARDENING_SHA" "$RECOVERY_MANIFEST_SHA" \
    "${RECOVERY_SERVICE_RESULTS:-}" "${RECOVERY_SERVICE_FAILURE:-}" \
    "${RECOVERY_RESTORE_ATTEMPTED:-false}" "${RECOVERY_RESTORE_FAILURE:-}" \
    "${RECOVERY_RESTORE_EXIT_CODE:-0}" "${RECOVERY_RESTORE_TARGET:-}" "$requested_source" "$source_states" "$TARGET_ROOT" \
    "$SERVICE_DROP_IN" "${RECOVERY_DROPIN_RESULT:-NOT_CHECKED}" \
    "$RUN_DIR" "${RECOVERY_RUNTIME_DIRECTORY_RESULT:-NOT_CHECKED}" \
    "$SERVICE_DROP_IN_DIR" "${RECOVERY_DROPIN_DIRECTORY_RESULT:-NOT_CHECKED}" \
    "${DROPIN_WRITE_STATE:-UNKNOWN}" "${DROPIN_TARGET_VERSION:-}" \
    "${RUN_WRITE_STATE:-UNKNOWN}" "${RUN_TARGET_VERSION:-}" "${RUN_CANDIDATE_METADATA:-}" \
    "${DROPIN_DIR_WRITE_STATE:-UNKNOWN}" "${DROPIN_DIR_TARGET_VERSION:-}" "${DROPIN_DIR_CANDIDATE_METADATA:-}" "${BUNDLE_FILES[@]}" <<'PY'
import hashlib
import json
import os
import re
import stat
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path

directory = Path(sys.argv[1])
kind, trigger_code, source, bundle, hardening, expected_manifest = sys.argv[2:8]
service_results, service_failure, restore_attempted = sys.argv[8:11]
restore_failure, restore_exit_code, restore_target = sys.argv[11:14]
requested_source, source_states, target_root = sys.argv[14:17]
dropin_target, dropin_result = sys.argv[17:19]
runtime_directory_target, runtime_directory_result = sys.argv[19:21]
dropin_directory_target, dropin_directory_result = sys.argv[21:23]
dropin_write_state, dropin_target_version = sys.argv[23:25]
run_write_state, run_target_version, run_candidate_metadata = sys.argv[25:28]
dropin_dir_write_state, dropin_dir_target_version, dropin_dir_candidate_metadata = sys.argv[28:31]
relatives = sys.argv[31:]
query_kinds = {"source_state", "source_result"}
if kind not in {"prepared", "helper", "rollback", "verify", "rollback_refused", "dropin_result", "runtime_directory_result", "dropin_directory_result"} | query_kinds:
    raise SystemExit("invalid_recovery_receipt_kind")
if ((kind in query_kinds and requested_source not in relatives)
        or (kind not in query_kinds and requested_source)):
    raise SystemExit("invalid_recovery_source_query")
if not re.fullmatch(r"[0-9a-f]{40}", source) or any(
    not re.fullmatch(r"[0-9a-f]{64}", value) for value in (bundle, hardening)
):
    raise SystemExit("invalid_recovery_source_binding")
if (not directory.is_dir() or directory.is_symlink()
        or directory.resolve(strict=True) != directory.absolute()
        or any(parent.is_symlink() for parent in directory.parents)):
    raise SystemExit("unsafe_recovery_directory")

def inventory(relative, capture=False, *, root=directory):
    if not isinstance(relative, str) or not re.fullmatch(r"[A-Za-z0-9_/.-]+", relative) or any(
        part in {"", ".", ".."} for part in relative.split("/")
    ):
        raise SystemExit("unsafe_recovery_inventory_path")
    path = root / relative
    for parent in path.parents:
        if parent == root:
            break
        if parent.is_symlink() or not parent.is_dir():
            raise SystemExit("unsafe_recovery_parent")
    info = path.lstat()
    if not stat.S_ISREG(info.st_mode) or info.st_nlink != 1:
        raise SystemExit("unsafe_recovery_file")
    def identity(value):
        return (value.st_dev, value.st_ino, value.st_mode, value.st_nlink,
                value.st_uid, value.st_gid, value.st_size, value.st_mtime_ns, value.st_ctime_ns)
    digest = hashlib.sha256()
    chunks = []
    descriptor = os.open(path, os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0))
    with os.fdopen(descriptor, "rb") as stream:
        if identity(os.fstat(stream.fileno())) != identity(info):
            raise SystemExit("recovery_file_changed_during_read")
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
            if capture:
                chunks.append(chunk)
        xattrs_sha256 = None
        if os.name == "posix" and hasattr(os, "listxattr"):
            attributes = [(name, os.getxattr(stream.fileno(), name).hex())
                          for name in sorted(os.listxattr(stream.fileno()))]
            xattrs_sha256 = hashlib.sha256(json.dumps(attributes).encode()).hexdigest()
        if os.name == "posix":
            os.fsync(stream.fileno())
        if identity(os.fstat(stream.fileno())) != identity(info) or identity(path.lstat()) != identity(info):
            raise SystemExit("recovery_file_changed_during_read")
    entry = dict(path=relative, sha256=digest.hexdigest(), bytes=info.st_size,
                 uid=info.st_uid, gid=info.st_gid, mode=format(stat.S_IMODE(info.st_mode), "04o"),
                 mtime_ns=info.st_mtime_ns, xattrs_sha256=xattrs_sha256)
    return (entry, b"".join(chunks)) if capture else entry

payload = dict(schema="lumencore.gateway_private_recovery.v1", kind=kind,
               generated_utc=datetime.now(timezone.utc).isoformat(), source_commit=source,
               bundle_sha256=bundle, hardening_sha256=hardening,
               trigger_exit_code=int(trigger_code), restoration_verified=False,
               external_verification="NOT_RECORDED_BY_HELPER")
if kind in {"helper", "rollback", "rollback_refused"}:
    if dropin_result not in {"NOT_CHECKED", "UNCHECKED_UNTOUCHED", "FAILED", "MATCHED_PREPARED_PRESENT", "MATCHED_PREPARED_ABSENCE"}:
        raise SystemExit("invalid_dropin_result_observation")
    if (dropin_write_state not in {"UNTOUCHED", "WRITE_PENDING", "INSTALLED", "UNKNOWN"}
            or (dropin_target_version and not re.fullmatch(r"[0-9a-f]{64}", dropin_target_version))
            or (dropin_result == "UNCHECKED_UNTOUCHED" and dropin_write_state != "UNTOUCHED")
            or (dropin_result in {"FAILED", "MATCHED_PREPARED_PRESENT", "MATCHED_PREPARED_ABSENCE"}
                and dropin_write_state != "INSTALLED")):
        raise SystemExit("invalid_dropin_write_state_record")
    payload["dropin_write_state"] = dict(state=dropin_write_state, candidate_sha256=hardening,
                                        installed_version_sha256=dropin_target_version or None)
    payload["dropin_result_observation"] = dropin_result
    if runtime_directory_result not in {"NOT_CHECKED", "UNCHECKED_UNTOUCHED", "FAILED", "MATCHED_PREPARED_PRESENT", "MATCHED_PREPARED_ABSENCE"}:
        raise SystemExit("invalid_runtime_directory_result_observation")
    if (run_write_state not in {"UNTOUCHED", "WRITE_PENDING", "INSTALLED", "UNKNOWN"}
            or (run_target_version and not re.fullmatch(r"[0-9a-f]{64}", run_target_version))
            or (run_candidate_metadata and not re.fullmatch(r"[0-9]+:[0-9]+:750", run_candidate_metadata))
            or (runtime_directory_result == "UNCHECKED_UNTOUCHED" and run_write_state != "UNTOUCHED")
            or (runtime_directory_result in {"FAILED", "MATCHED_PREPARED_PRESENT", "MATCHED_PREPARED_ABSENCE"}
                and run_write_state != "INSTALLED")):
        raise SystemExit("invalid_runtime_directory_write_state_record")
    payload["runtime_directory_write_state"] = dict(state=run_write_state,
        candidate_metadata=run_candidate_metadata or None, installed_version_sha256=run_target_version or None)
    payload["runtime_directory_result_observation"] = runtime_directory_result
    if dropin_directory_result not in {"NOT_CHECKED", "UNCHECKED_UNTOUCHED", "FAILED", "MATCHED_PREPARED_PRESENT", "MATCHED_PREPARED_ABSENCE"}:
        raise SystemExit("invalid_dropin_directory_result_observation")
    if (dropin_dir_write_state not in {"UNTOUCHED", "WRITE_PENDING", "INSTALLED", "UNKNOWN"}
            or (dropin_dir_target_version and not re.fullmatch(r"[0-9a-f]{64}", dropin_dir_target_version))
            or dropin_dir_candidate_metadata != "0:0:755"
            or (dropin_directory_result == "UNCHECKED_UNTOUCHED" and dropin_dir_write_state != "UNTOUCHED")
            or (dropin_directory_result in {"FAILED", "MATCHED_PREPARED_PRESENT", "MATCHED_PREPARED_ABSENCE"}
                and dropin_dir_write_state != "INSTALLED")):
        raise SystemExit("invalid_dropin_directory_write_state_record")
    payload["dropin_directory_write_state"] = dict(state=dropin_dir_write_state,
        candidate_metadata=dropin_dir_candidate_metadata, installed_version_sha256=dropin_dir_target_version or None)
    payload["dropin_directory_result_observation"] = dropin_directory_result
    states = []
    for row in source_states.splitlines():
        fields = row.split(":")
        if len(fields) != 5 or fields[0] not in relatives:
            raise SystemExit("invalid_source_write_state_record")
        relative, state, candidate, version, result = fields
        if (state not in {"UNTOUCHED", "WRITE_PENDING", "INSTALLED", "UNKNOWN"}
                or (candidate and not re.fullmatch(r"[0-9a-f]{64}", candidate))
                or (version and not re.fullmatch(r"[0-9a-f]{64}", version))
                or result not in {"NOT_CHECKED", "UNCHECKED_UNTOUCHED", "FAILED",
                                  "MATCHED_PREPARED_PRESENT", "MATCHED_PREPARED_ABSENCE"}
                or (result in {"FAILED", "MATCHED_PREPARED_PRESENT", "MATCHED_PREPARED_ABSENCE"} and state != "INSTALLED")
                or (result == "UNCHECKED_UNTOUCHED" and state != "UNTOUCHED")):
            raise SystemExit("invalid_source_write_state_record")
        states.append(dict(path=relative, state=state, candidate_sha256=candidate or None,
                           installed_version_sha256=version or None,
                           restoration_result_observation=result))
    if [item["path"] for item in states] != relatives:
        raise SystemExit("invalid_source_write_state_inventory")
    payload["source_write_states"] = states
def expected_backup_inventory():
    if len(set(relatives)) != len(relatives) or any(
        not re.fullmatch(r"[A-Za-z0-9_/.-]+", item) or
        any(part in {"", ".", ".."} for part in item.split("/")) for item in relatives
    ):
        raise SystemExit("invalid_recovery_file_allowlist")
    missing_file = directory / "missing-before.txt"
    missing_rows = inventory("missing-before.txt", capture=True)[1].decode().splitlines() if missing_file.exists() else []
    missing = set(missing_rows)
    if len(missing) != len(missing_rows) or not missing.issubset(relatives):
        raise SystemExit("invalid_missing_file_inventory")
    names = ["service-drop-in.state", "service-drop-in-dir.state", "run-dir.state", "service.state"]
    for relative in relatives:
        backup = directory / "existing" / relative
        if relative in missing:
            if backup.exists() or backup.is_symlink():
                raise SystemExit("contradictory_missing_file_inventory")
        else:
            names.append("existing/" + relative)
    if missing_file.exists():
        names.append("missing-before.txt")
    for state_name, snapshot in (
        ("service-drop-in", "service-drop-in.before"),
        ("service-drop-in-dir", "service-drop-in-dir.metadata"),
        ("run-dir", "run-dir.metadata"),
    ):
        state = inventory(state_name + ".state", capture=True)[1].decode().strip()
        if state not in {"present", "missing"}:
            raise SystemExit("invalid_recovery_state")
        if state == "present":
            names.append(snapshot)
    return names, missing

def require_exact_inventory(names):
    allowed_files = set(names) | {"prepared.json", "helper.json", "rollback.json", "rollback_refused.json"}
    allowed_dirs = {"existing"}
    for name in names:
        allowed_dirs.update(str(parent).replace(os.sep, "/") for parent in Path(name).parents if str(parent) != ".")
    for current, directories, files in os.walk(directory, followlinks=False):
        for name in directories + files:
            path = Path(current) / name
            relative = path.relative_to(directory).as_posix()
            info = path.lstat()
            if stat.S_ISDIR(info.st_mode):
                if relative not in allowed_dirs:
                    raise SystemExit("unexpected_recovery_directory")
            elif not stat.S_ISREG(info.st_mode) or info.st_nlink != 1:
                raise SystemExit("unsafe_recovery_file")
            elif relative not in allowed_files:
                raise SystemExit("unexpected_recovery_file")

def observe_source_result(prepared):
    root = Path(target_root)
    if not root.is_absolute() or root.resolve(strict=True) != root:
        raise SystemExit("unsafe_source_result_root")
    path = root / requested_source

    def parents():
        observed = []
        for parent in path.parents:
            info = parent.lstat()
            if not stat.S_ISDIR(info.st_mode):
                raise SystemExit("unsafe_source_result_parent")
            if parent == root or root in parent.parents:
                if os.name == "posix" and (info.st_uid != os.geteuid() or stat.S_IMODE(info.st_mode) & 0o022):
                    raise SystemExit("unsafe_source_result_parent_permissions")
                # Sibling changes alter directory timestamps, not its identity.
                observed.append((str(parent), info.st_dev, info.st_ino, info.st_uid, info.st_gid, info.st_mode))
        return observed

    before = parents()
    if requested_source in prepared["missing_source_files"]:
        try:
            path.lstat()
        except FileNotFoundError:
            result = b"observed_absent\n"
        else:
            raise SystemExit("source_result_expected_absence")
    else:
        expected = next(item for item in prepared["files"] if item["path"] == "existing/" + requested_source)
        actual = inventory(requested_source, root=root)
        # A valid copy changes inode and ctime. Inventory checks their stability
        # during this read, but compares only prepared bytes/preserved metadata.
        if actual != dict(expected, path=requested_source):
            raise SystemExit("source_result_mismatch")
        result = b"observed_present\n"
    if parents() != before:
        raise SystemExit("source_result_parent_changed")
    sys.stdout.buffer.write(result)

def observe_dropin_result(prepared):
    # This fixed configuration object is not a member of the Python source set.
    # Apply mode already pins its exact production path; no query path is accepted.
    path = Path(dropin_target)
    if not path.is_absolute() or path.resolve(strict=False) != path:
        raise SystemExit("unsafe_dropin_result_path")
    safe_root = path.parent.parent

    def parents():
        observed = []
        for parent in path.parents:
            try:
                info = parent.lstat()
            except FileNotFoundError:
                # A missing immediate service drop-in directory can be legitimate.
                if parent != path.parent:
                    raise SystemExit("unsafe_dropin_result_parent")
                observed.append((str(parent), "missing"))
                continue
            if not stat.S_ISDIR(info.st_mode):
                raise SystemExit("unsafe_dropin_result_parent")
            if parent in {path.parent, safe_root} and os.name == "posix":
                if info.st_uid != os.geteuid() or stat.S_IMODE(info.st_mode) & 0o022:
                    raise SystemExit("unsafe_dropin_result_parent_permissions")
            observed.append((str(parent), info.st_dev, info.st_ino, info.st_uid, info.st_gid, info.st_mode))
        return observed

    before = parents()
    expected = next((item for item in prepared["files"] if item["path"] == "service-drop-in.before"), None)
    if expected is None:
        try:
            path.lstat()
        except FileNotFoundError:
            result = b"dropin_absent\n"
        else:
            raise SystemExit("dropin_result_expected_absence")
    else:
        actual = inventory(path.name, root=path.parent)
        # Copied inode/ctime need not match the backup; read stability still must.
        if actual != dict(expected, path=path.name):
            raise SystemExit("dropin_result_mismatch")
        result = b"dropin_present\n"
    if parents() != before:
        raise SystemExit("dropin_result_parent_changed")
    sys.stdout.buffer.write(result)

def expected_runtime_directory(prepared):
    # Parse exactly the captured bytes whose inventory matches the pinned entry.
    def captured(name):
        expected = next((item for item in prepared["files"] if item["path"] == name), None)
        actual, raw = inventory(name, capture=True)
        if expected is None or actual != expected:
            raise SystemExit("runtime_directory_preparation_changed")
        return raw
    state = captured("run-dir.state")
    if state == b"missing\n":
        if any(item["path"] == "run-dir.metadata" for item in prepared["files"]):
            raise SystemExit("runtime_directory_preparation_contradiction")
        return None
    if state != b"present\n":
        raise SystemExit("invalid_runtime_directory_prepared_state")
    match = re.fullmatch(rb"([0-9]+) ([0-9]+) ([0-7]{3,4})\n", captured("run-dir.metadata"))
    if not match:
        raise SystemExit("invalid_runtime_directory_prepared_metadata")
    return int(match[1]), int(match[2]), int(match[3], 8)

def observe_runtime_directory_result(prepared):
    # Fixed apply-mode object; this query accepts no caller-selected path.
    expected = expected_runtime_directory(prepared)
    path = Path(runtime_directory_target)
    if not path.is_absolute() or path.resolve(strict=False) != path:
        raise SystemExit("unsafe_runtime_directory_result_path")

    def identity(info):
        return (info.st_dev, info.st_ino, info.st_mode, info.st_nlink, info.st_uid,
                info.st_gid, info.st_mtime_ns, info.st_ctime_ns)

    def parents():
        observed = []
        for parent in path.parents:
            info = parent.lstat()
            if not stat.S_ISDIR(info.st_mode):
                raise SystemExit("unsafe_runtime_directory_result_parent")
            if parent == path.parent and os.name == "posix":
                if info.st_uid != os.geteuid() or stat.S_IMODE(info.st_mode) & 0o022:
                    raise SystemExit("unsafe_runtime_directory_result_parent_permissions")
            observed.append((str(parent), info.st_dev, info.st_ino, info.st_mode, info.st_uid, info.st_gid))
        return observed

    before = parents()
    if expected is None:
        try:
            path.lstat()
        except FileNotFoundError:
            result = b"runtime_directory_absent\n"
        else:
            raise SystemExit("runtime_directory_result_expected_absence")
    else:
        info = path.lstat()
        if not stat.S_ISDIR(info.st_mode):
            raise SystemExit("runtime_directory_result_not_directory")
        if (info.st_uid, info.st_gid, stat.S_IMODE(info.st_mode)) != expected:
            raise SystemExit("runtime_directory_result_metadata_mismatch")
        # Keep identity stable during observation, without claiming equality to
        # an old inode or restoration of contents, timestamps, ACLs or xattrs.
        if os.name == "posix":
            descriptor = os.open(path, os.O_RDONLY | os.O_DIRECTORY | getattr(os, "O_NOFOLLOW", 0))
            try:
                if identity(os.fstat(descriptor)) != identity(info) or identity(path.lstat()) != identity(info):
                    raise SystemExit("runtime_directory_result_changed")
            finally:
                os.close(descriptor)
        elif identity(path.lstat()) != identity(info):
            raise SystemExit("runtime_directory_result_changed")
        result = b"runtime_directory_present\n"
    if parents() != before:
        raise SystemExit("runtime_directory_result_parent_changed")
    sys.stdout.buffer.write(result)

def expected_dropin_directory(prepared):
    # Parse exactly the captured bytes whose inventory matches the pinned entry.
    def captured(name):
        expected = next((item for item in prepared["files"] if item["path"] == name), None)
        actual, raw = inventory(name, capture=True)
        if expected is None or actual != expected:
            raise SystemExit("dropin_directory_preparation_changed")
        return raw
    state = captured("service-drop-in-dir.state")
    if state == b"missing\n":
        if any(item["path"] == "service-drop-in-dir.metadata" for item in prepared["files"]):
            raise SystemExit("dropin_directory_preparation_contradiction")
        return None
    if state != b"present\n":
        raise SystemExit("invalid_dropin_directory_prepared_state")
    match = re.fullmatch(rb"([0-9]+) ([0-9]+) ([0-7]{3,4})\n", captured("service-drop-in-dir.metadata"))
    if not match:
        raise SystemExit("invalid_dropin_directory_prepared_metadata")
    return int(match[1]), int(match[2]), int(match[3], 8)

def observe_dropin_directory_result(prepared):
    # Fixed apply-mode object; this query accepts no caller-selected path.
    expected = expected_dropin_directory(prepared)
    path = Path(dropin_directory_target)
    if not path.is_absolute() or path.resolve(strict=False) != path:
        raise SystemExit("unsafe_dropin_directory_result_path")

    def identity(info):
        return (info.st_dev, info.st_ino, info.st_mode, info.st_nlink, info.st_uid,
                info.st_gid, info.st_mtime_ns, info.st_ctime_ns)

    def parents():
        observed = []
        for parent in path.parents:
            info = parent.lstat()
            if not stat.S_ISDIR(info.st_mode):
                raise SystemExit("unsafe_dropin_directory_result_parent")
            if parent == path.parent and os.name == "posix":
                if info.st_uid != os.geteuid() or stat.S_IMODE(info.st_mode) & 0o022:
                    raise SystemExit("unsafe_dropin_directory_result_parent_permissions")
            observed.append((str(parent), info.st_dev, info.st_ino, info.st_mode, info.st_uid, info.st_gid))
        return observed

    before = parents()
    if expected is None:
        try:
            path.lstat()
        except FileNotFoundError:
            result = b"dropin_directory_absent\n"
        else:
            raise SystemExit("dropin_directory_result_expected_absence")
    else:
        info = path.lstat()
        if not stat.S_ISDIR(info.st_mode):
            raise SystemExit("dropin_directory_result_not_directory")
        if (info.st_uid, info.st_gid, stat.S_IMODE(info.st_mode)) != expected:
            raise SystemExit("dropin_directory_result_metadata_mismatch")
        # Keep identity stable during observation, without claiming equality to
        # an old inode or restoration of contents, timestamps, ACLs or xattrs.
        if os.name == "posix":
            descriptor = os.open(path, os.O_RDONLY | os.O_DIRECTORY | getattr(os, "O_NOFOLLOW", 0))
            try:
                if identity(os.fstat(descriptor)) != identity(info) or identity(path.lstat()) != identity(info):
                    raise SystemExit("dropin_directory_result_changed")
            finally:
                os.close(descriptor)
        elif identity(path.lstat()) != identity(info):
            raise SystemExit("dropin_directory_result_changed")
        result = b"dropin_directory_present\n"
    if parents() != before:
        raise SystemExit("dropin_directory_result_parent_changed")
    sys.stdout.buffer.write(result)

if kind == "rollback_refused":
    # This receipt describes refusal only; it does not authenticate invalid input.
    payload.update(status="ROLLBACK_REFUSED_INVALID_RECOVERY_EVIDENCE", restore_attempted=False,
                   expected_manifest_sha256=expected_manifest, recovery_evidence_verified=False)
elif kind == "prepared":
    names, missing = expected_backup_inventory()
    require_exact_inventory(names)
    payload.update(status="PREPARED_BEFORE_MUTATION", files=[inventory(name) for name in names],
                   missing_source_files=sorted(missing))
else:
    entry, manifest_raw = inventory("prepared.json", capture=True)
    if entry["sha256"] != expected_manifest:
        raise SystemExit("recovery_manifest_hash_mismatch")
    prepared = json.loads(manifest_raw)
    if (prepared.get("schema") != payload["schema"] or prepared.get("kind") != "prepared"
            or prepared.get("status") != "PREPARED_BEFORE_MUTATION"):
        raise SystemExit("invalid_prepared_manifest")
    if any(prepared.get(key) != payload[key] for key in
           ("source_commit", "bundle_sha256", "hardening_sha256")):
        raise SystemExit("recovery_manifest_binding_mismatch")
    names, missing = expected_backup_inventory()
    entries = prepared.get("files", [])
    if (not isinstance(entries, list) or len(entries) != len(names)
            or sorted(item["path"] for item in entries) != sorted(names)
            or prepared.get("missing_source_files") != sorted(missing)):
        raise SystemExit("recovery_inventory_mismatch")
    require_exact_inventory(names)
    if any(inventory(item["path"]) != item for item in prepared["files"]):
        raise SystemExit("recovery_backup_changed")
    if kind == "source_state":
        # Intent comes only from the same-read, hash-bound manifest. Complete
        # inventory validation above must pass again before each source mutation.
        sys.stdout.buffer.write(b"missing\n" if requested_source in prepared["missing_source_files"] else b"present\n")
        raise SystemExit(0)
    if kind == "source_result":
        observe_source_result(prepared)
        raise SystemExit(0)
    if kind == "dropin_result":
        observe_dropin_result(prepared)
        raise SystemExit(0)
    if kind == "runtime_directory_result":
        observe_runtime_directory_result(prepared)
        raise SystemExit(0)
    if kind == "dropin_directory_result":
        observe_dropin_directory_result(prepared)
        raise SystemExit(0)
    if kind == "verify":
        print("RECOVERY_EVIDENCE_VERIFIED_BEFORE_RESTORATION")
        raise SystemExit(0)
    dropin_present = any(item["path"] == "service-drop-in.before" for item in prepared["files"])
    if ((dropin_result == "MATCHED_PREPARED_PRESENT" and not dropin_present)
            or (dropin_result == "MATCHED_PREPARED_ABSENCE" and dropin_present)):
        raise SystemExit("dropin_result_inventory_mismatch")
    if runtime_directory_result in {"MATCHED_PREPARED_PRESENT", "MATCHED_PREPARED_ABSENCE"}:
        runtime_present = expected_runtime_directory(prepared) is not None
        if (runtime_directory_result == "MATCHED_PREPARED_PRESENT") != runtime_present:
            raise SystemExit("runtime_directory_result_inventory_mismatch")
    if dropin_directory_result in {"MATCHED_PREPARED_PRESENT", "MATCHED_PREPARED_ABSENCE"}:
        dropin_directory_present = expected_dropin_directory(prepared) is not None
        if (dropin_directory_result == "MATCHED_PREPARED_PRESENT") != dropin_directory_present:
            raise SystemExit("dropin_directory_result_inventory_mismatch")
    payload.update(manifest_sha256=expected_manifest,
                   status="HELPER_CHECKS_PASSED_EXTERNAL_VERIFICATION_PENDING" if kind == "helper"
                   else "ROLLBACK_ATTEMPTED_UNVERIFIED")
if kind == "rollback":
    commands = []
    for row in service_results.splitlines():
        match = re.fullmatch(r"(stop|daemon-reload|reset-failed|start):([0-9]{1,3})", row)
        if not match or int(match[2]) > 255:
            raise SystemExit("invalid_recovery_service_result")
        verb, code = match[1], int(match[2])
        outcome = ("COMPLETED" if code == 0 else "DEADLINE_EXCEEDED_OR_COMMAND_EXIT_124" if code == 124
                   else "FORCED_TERMINATION_OR_SIGKILL" if code == 137
                   else "LAUNCHER_OR_COMMAND_FAILURE" if code in {125, 126, 127} else "COMMAND_FAILED")
        commands.append(dict(verb=verb, exit_code=code, outcome=outcome,
                             timeout_seconds=60, kill_after_seconds=5))
    order = ["stop", "daemon-reload", "reset-failed", "start"]
    if ([item["verb"] for item in commands] != order[:len(commands)]
            or len(commands) > 4 or restore_attempted not in {"true", "false"}
            or any(item["exit_code"] != 0 for item in commands[:-1])
            or service_failure != (commands[-1]["verb"] if commands and commands[-1]["exit_code"] else "")):
        raise SystemExit("invalid_recovery_service_sequence")
    payload.update(service_commands=commands, restore_attempted=restore_attempted == "true",
                   service_state_verified=False, systemd_job_cancellation_verified=False)
    if service_failure:
        payload["status"] = ("ROLLBACK_ABORTED_SERVICE_STOP_UNCONFIRMED" if service_failure == "stop"
                             else "ROLLBACK_INCOMPLETE_SERVICE_COMMAND_FAILED")
    restoration_targets = {
        "dead_lock": {"gateway_lock"}, "source_state": set(relatives),
        "target_state": set(relatives), "target_absent": set(relatives),
        "source_remove": set(relatives), "source_copy": set(relatives), "source_result": set(relatives),
        "dropin_remove": {"service_drop_in"}, "dropin_state_read": {"service_drop_in"}, "dropin_result": {"service_drop_in"},
        "dropin_target_state": {"service_drop_in"}, "dropin_target_absent": {"service_drop_in"},
        "dropin_directory_target_state": {"service_drop_in_directory"},
        "dropin_parent_create": {"service_drop_in_directory"}, "dropin_copy": {"service_drop_in"},
        "dropin_directory_state_read": {"service_drop_in_directory"},
        "dropin_metadata_read": {"service_drop_in_directory"},
        "dropin_chown": {"service_drop_in_directory"}, "dropin_chmod": {"service_drop_in_directory"},
        "dropin_directory_remove": {"service_drop_in_directory"},
        "dropin_directory_result": {"service_drop_in_directory"},
        "run_directory_state_read": {"run_directory"}, "run_metadata_read": {"run_directory"},
        "run_chown": {"run_directory"}, "run_chmod": {"run_directory"},
        "run_target_state": {"run_directory"},
        "run_directory_remove": {"run_directory"}, "runtime_directory_result": {"run_directory"},
    }
    if restore_failure:
        if (restore_failure not in restoration_targets or restore_target not in restoration_targets[restore_failure]
                or not re.fullmatch(r"[0-9]{1,3}", restore_exit_code) or not 1 <= int(restore_exit_code) <= 255
                or restore_attempted != "true" or service_failure
                or [(item["verb"], item["exit_code"]) for item in commands] != [("stop", 0)]):
            raise SystemExit("invalid_restoration_failure_record")
        payload.update(status="ROLLBACK_INCOMPLETE_RESTORATION_COMMAND_FAILED", partial_state_possible=True,
                       further_restoration_stopped=True, service_restart_attempted=False,
                       failed_restoration_operation=dict(operation=restore_failure, target=restore_target,
                                                         exit_code=int(restore_exit_code)))
        if restore_failure in {"source_copy", "dropin_copy"}:
            code = int(restore_exit_code)
            outcome = ("DEADLINE_EXCEEDED_OR_COMMAND_EXIT_124" if code == 124
                       else "FORCED_TERMINATION_OR_SIGKILL" if code == 137
                       else "LAUNCHER_OR_COMMAND_FAILURE" if code in {125, 126, 127}
                       else "COMMAND_FAILED")
            payload["failed_restoration_operation"].update(
                outcome=outcome, timeout_seconds=60, kill_after_seconds=5,
                partial_destination_possible=True)
    elif restore_exit_code != "0" or restore_target:
        raise SystemExit("unexpected_restoration_failure_fields")
raw = (json.dumps(payload, sort_keys=True, indent=2) + "\n").encode()
destination = directory / (kind + ".json")
fd, temporary = tempfile.mkstemp(prefix=".receipt-", dir=directory)
try:
    with os.fdopen(fd, "wb") as stream:
        os.chmod(temporary, 0o600)
        stream.write(raw)
        stream.flush()
        os.fsync(stream.fileno())
    # Publish without replacing an earlier receipt or following an existing link.
    os.link(temporary, destination)
finally:
    os.unlink(temporary)
if destination.read_bytes() != raw:
    raise SystemExit("recovery_receipt_readback_failed")
if os.name == "posix":
    directory_fd = os.open(directory, os.O_RDONLY | os.O_DIRECTORY)
    try:
        os.fsync(directory_fd)
    finally:
        os.close(directory_fd)
print(hashlib.sha256(raw).hexdigest())
PY
}

recorded_target_version() {
  [[ $# -eq 4 ]] || return 14
  python3 - "$TARGET_ROOT" "$SERVICE_DROP_IN" "$RUN_DIR" "$1" "$2" "$3" "$4" "${BUNDLE_FILES[@]}" <<'PY'
import hashlib
import json
import os
import re
import stat
import sys
from pathlib import Path

root, dropin, runtime = map(Path, sys.argv[1:4])
object_kind, mode, relative, expected = sys.argv[4:8]
allowlist = sys.argv[8:]
if object_kind == "dropin":
    # Apply pins this exact configuration path. The fixed-object wrapper accepts
    # no caller-selected path; sharing the reader does not expand source authority.
    if relative or not dropin.is_absolute():
        raise SystemExit("invalid_dropin_version_query")
    root, relative = dropin.parent.parent, dropin.parent.name + "/" + dropin.name
    allowlist = [relative]
elif object_kind == "runtime":
    if relative or mode != "capture" or not runtime.is_absolute():
        raise SystemExit("invalid_runtime_directory_version_query")
    root, relative = runtime.parent, runtime.name
    allowlist = [relative]
elif object_kind == "dropin_directory":
    if relative or mode != "capture" or not dropin.is_absolute() or expected != "0:0:755":
        raise SystemExit("invalid_dropin_directory_version_query")
    root, relative = dropin.parent.parent, dropin.parent.name
    allowlist = [relative]
elif object_kind != "source":
    raise SystemExit("invalid_target_object")
if (mode not in {"capture", "absent"} or relative not in allowlist
        or not re.fullmatch(r"[A-Za-z0-9_/.-]+", relative)
        or any(part in {"", ".", ".."} for part in relative.split("/"))
        or (mode == "capture" and not re.fullmatch(r"[0-9]+:[0-9]+:750" if object_kind == "runtime" else r"0:0:755" if object_kind == "dropin_directory" else r"[0-9a-f]{64}", expected))
        or (mode == "absent" and expected)):
    raise SystemExit("invalid_target_version_query")
if not root.is_absolute() or root.resolve(strict=True) != root:
    raise SystemExit("unsafe_target_root")
path = root / relative

def parents():
    result = []
    for parent in path.parents:
        info = parent.lstat()
        if not stat.S_ISDIR(info.st_mode):
            raise SystemExit("unsafe_target_parent")
        # Apply already requires root. Fixture processes may run unprivileged;
        # within-root parents must belong to this same caller and reject writes
        # by other accounts. No permission repair is performed here.
        if parent == root or root in parent.parents:
            if os.name == "posix" and (info.st_uid != os.geteuid() or stat.S_IMODE(info.st_mode) & 0o022):
                raise SystemExit("unsafe_target_parent_permissions")
        if object_kind != "source" or parent == root or root in parent.parents:
            result.append([str(parent) if object_kind != "source" else str(parent.relative_to(root)), info.st_dev, info.st_ino,
                           info.st_uid, info.st_gid, info.st_mode])
    return result

parent_version = parents()
if mode == "absent":
    try:
        path.lstat()
    except FileNotFoundError:
        if parents() != parent_version:
            raise SystemExit("target_parent_changed")
        sys.stdout.buffer.write(b"absent\n")
        raise SystemExit(0)
    raise SystemExit("target_reappeared")

def identity(info):
    return [info.st_dev, info.st_ino, info.st_mode, info.st_nlink, info.st_uid,
            info.st_gid, info.st_size, info.st_mtime_ns, info.st_ctime_ns]

before = path.lstat()
if object_kind in {"runtime", "dropin_directory"}:
    if not stat.S_ISDIR(before.st_mode):
        raise SystemExit("unsafe_runtime_directory_target")
    uid, gid, permissions = (int(part, 8 if i == 2 else 10) for i, part in enumerate(expected.split(":")))
    if (before.st_uid, before.st_gid, stat.S_IMODE(before.st_mode)) != (uid, gid, permissions):
        raise SystemExit("runtime_directory_candidate_mismatch")
    # Child/lock operations legitimately change directory timestamps and link
    # counts. Bind stable ownership/type/identity, not contents or ACLs/xattrs.
    def directory_identity(info):
        return [info.st_dev, info.st_ino, info.st_mode, info.st_uid, info.st_gid]
    if os.name == "posix":
        descriptor = os.open(path, os.O_RDONLY | os.O_DIRECTORY | getattr(os, "O_NOFOLLOW", 0))
        try:
            if directory_identity(os.fstat(descriptor)) != directory_identity(before):
                raise SystemExit("runtime_directory_changed_during_read")
        finally:
            os.close(descriptor)
    if directory_identity(path.lstat()) != directory_identity(before) or parents() != parent_version:
        raise SystemExit("runtime_directory_changed_during_read")
    version = dict(identity=directory_identity(before), parents=parent_version, candidate_metadata=expected)
    sys.stdout.buffer.write(hashlib.sha256(json.dumps(version, sort_keys=True).encode()).hexdigest().encode() + b"\n")
    raise SystemExit(0)
if not stat.S_ISREG(before.st_mode) or before.st_nlink != 1:
    raise SystemExit("unsafe_target_file")
digest = hashlib.sha256()
descriptor = os.open(path, os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0))
with os.fdopen(descriptor, "rb") as stream:
    if identity(os.fstat(stream.fileno())) != identity(before):
        raise SystemExit("target_changed_during_read")
    for chunk in iter(lambda: stream.read(1024 * 1024), b""):
        digest.update(chunk)
    attributes = None
    if os.name == "posix" and hasattr(os, "listxattr"):
        attributes = [(name, os.getxattr(stream.fileno(), name).hex())
                      for name in sorted(os.listxattr(stream.fileno()))]
    if (identity(os.fstat(stream.fileno())) != identity(before)
            or identity(path.lstat()) != identity(before) or parents() != parent_version):
        raise SystemExit("target_changed_during_read")
if digest.hexdigest() != expected:
    raise SystemExit("target_candidate_mismatch")
version = dict(sha256=digest.hexdigest(), identity=identity(before), parents=parent_version,
               xattrs_sha256=hashlib.sha256(json.dumps(attributes).encode()).hexdigest())
sys.stdout.buffer.write(hashlib.sha256(json.dumps(version, sort_keys=True).encode()).hexdigest().encode() + b"\n")
PY
}

source_target_version() {
  [[ $# -eq 3 ]] || return 14
  recorded_target_version source "$@"
}

dropin_target_version() {
  [[ $# -eq 1 ]] || return 14
  case "$1" in
    capture) recorded_target_version dropin capture '' "$HARDENING_SHA" ;;
    absent) recorded_target_version dropin absent '' '' ;;
    *) return 14 ;;
  esac
}

capture_dropin_target_version() {
  local response
  [[ $# -eq 0 ]] || return 14
  response="$(dropin_target_version capture && printf '.')" || return $?
  [[ "$response" =~ ^([0-9a-f]{64})$'\n.'$ ]] || return 14
  CAPTURED_DROPIN_TARGET_VERSION="${BASH_REMATCH[1]}"
}

install_gateway_dropin() {
  [[ $# -eq 0 && "$DROPIN_WRITE_STATE" == UNTOUCHED
    && "$HARDENING_SHA" =~ ^[0-9a-f]{64}$ ]] || return 14
  DROPIN_WRITE_STATE=WRITE_PENDING
  install -o root -g root -m 0644 -- "$STAGE_DIR/20-lumencore-runtime-hardening.conf" "$SERVICE_DROP_IN" || return $?
  capture_dropin_target_version || return $?
  DROPIN_TARGET_VERSION="$CAPTURED_DROPIN_TARGET_VERSION"
  DROPIN_WRITE_STATE=INSTALLED
}

read_recovery_dropin_target_state() {
  [[ $# -eq 0 && "$HARDENING_SHA" =~ ^[0-9a-f]{64}$ ]] || return 14
  case "${DROPIN_WRITE_STATE:-UNKNOWN}" in
    UNTOUCHED)
      [[ -z "${DROPIN_TARGET_VERSION:-}" ]] || return 14
      RECOVERY_DROPIN_TARGET_STATE=untouched ;;
    INSTALLED)
      [[ "${DROPIN_TARGET_VERSION:-}" =~ ^[0-9a-f]{64}$ ]] || return 14
      capture_dropin_target_version || return $?
      [[ "$CAPTURED_DROPIN_TARGET_VERSION" == "$DROPIN_TARGET_VERSION" ]] || return 14
      RECOVERY_DROPIN_TARGET_STATE=installed ;;
    *) return 14 ;;
  esac
}

require_recovery_dropin_absent() {
  local response
  [[ $# -eq 0 ]] || return 14
  response="$(dropin_target_version absent && printf '.')" || return $?
  [[ "$response" == $'absent\n.' ]] || return 14
}

dropin_directory_target_version() {
  [[ $# -eq 0 && "$DROPIN_DIR_CANDIDATE_METADATA" == 0:0:755 ]] || return 14
  recorded_target_version dropin_directory capture '' "$DROPIN_DIR_CANDIDATE_METADATA"
}

capture_dropin_directory_target_version() {
  local response
  [[ $# -eq 0 ]] || return 14
  response="$(dropin_directory_target_version && printf '.')" || return $?
  [[ "$response" =~ ^([0-9a-f]{64})$'\n.'$ ]] || return 14
  CAPTURED_DROPIN_DIR_TARGET_VERSION="${BASH_REMATCH[1]}"
}

install_gateway_dropin_directory() {
  [[ $# -eq 0 && "$DROPIN_DIR_WRITE_STATE" == UNTOUCHED
    && "$DROPIN_DIR_CANDIDATE_METADATA" == 0:0:755 ]] || return 14
  DROPIN_DIR_WRITE_STATE=WRITE_PENDING
  install -d -o 0 -g 0 -m 0755 -- "$SERVICE_DROP_IN_DIR" || return $?
  capture_dropin_directory_target_version || return $?
  DROPIN_DIR_TARGET_VERSION="$CAPTURED_DROPIN_DIR_TARGET_VERSION"
  DROPIN_DIR_WRITE_STATE=INSTALLED
}

read_recovery_dropin_directory_target_state() {
  [[ $# -eq 0 && "$DROPIN_DIR_CANDIDATE_METADATA" == 0:0:755 ]] || return 14
  case "${DROPIN_DIR_WRITE_STATE:-UNKNOWN}" in
    UNTOUCHED)
      # A child write cannot be authorized through an untouched parent. Skip
      # both only when the actual forward sequence reached neither install.
      [[ -z "${DROPIN_DIR_TARGET_VERSION:-}" && "${DROPIN_WRITE_STATE:-UNKNOWN}" == UNTOUCHED
        && -z "${DROPIN_TARGET_VERSION:-}" ]] || return 14
      RECOVERY_DROPIN_DIRECTORY_TARGET_STATE=untouched ;;
    INSTALLED)
      [[ "${DROPIN_DIR_TARGET_VERSION:-}" =~ ^[0-9a-f]{64}$ ]] || return 14
      capture_dropin_directory_target_version || return $?
      [[ "$CAPTURED_DROPIN_DIR_TARGET_VERSION" == "$DROPIN_DIR_TARGET_VERSION" ]] || return 14
      RECOVERY_DROPIN_DIRECTORY_TARGET_STATE=installed ;;
    *) return 14 ;;
  esac
}

runtime_directory_target_version() {
  [[ $# -eq 0 ]] || return 14
  recorded_target_version runtime capture '' "$RUN_CANDIDATE_METADATA"
}

capture_runtime_directory_target_version() {
  local response
  [[ $# -eq 0 ]] || return 14
  response="$(runtime_directory_target_version && printf '.')" || return $?
  [[ "$response" =~ ^([0-9a-f]{64})$'\n.'$ ]] || return 14
  CAPTURED_RUN_TARGET_VERSION="${BASH_REMATCH[1]}"
}

install_gateway_runtime_directory() {
  [[ $# -eq 0 && "$RUN_WRITE_STATE" == UNTOUCHED
    && "$RUN_CANDIDATE_METADATA" =~ ^[0-9]+:[0-9]+:750$ ]] || return 14
  RUN_WRITE_STATE=WRITE_PENDING
  local run_uid run_gid run_mode
  IFS=: read -r run_uid run_gid run_mode <<< "$RUN_CANDIDATE_METADATA"
  install -d -o "$run_uid" -g "$run_gid" -m "$run_mode" -- "$RUN_DIR" || return $?
  capture_runtime_directory_target_version || return $?
  RUN_TARGET_VERSION="$CAPTURED_RUN_TARGET_VERSION"
  RUN_WRITE_STATE=INSTALLED
}

read_recovery_runtime_directory_target_state() {
  [[ $# -eq 0 && "$RUN_CANDIDATE_METADATA" =~ ^[0-9]+:[0-9]+:750$ ]] || return 14
  case "${RUN_WRITE_STATE:-UNKNOWN}" in
    UNTOUCHED)
      [[ -z "${RUN_TARGET_VERSION:-}" ]] || return 14
      RECOVERY_RUN_TARGET_STATE=untouched ;;
    INSTALLED)
      [[ "${RUN_TARGET_VERSION:-}" =~ ^[0-9a-f]{64}$ ]] || return 14
      capture_runtime_directory_target_version || return $?
      [[ "$CAPTURED_RUN_TARGET_VERSION" == "$RUN_TARGET_VERSION" ]] || return 14
      RECOVERY_RUN_TARGET_STATE=installed ;;
    *) return 14 ;;
  esac
}

capture_source_target_version() {
  local response
  response="$(source_target_version capture "$1" "$2" && printf '.')" || return $?
  [[ "$response" =~ ^([0-9a-f]{64})$'\n.'$ ]] || return 14
  CAPTURED_TARGET_VERSION="${BASH_REMATCH[1]}"
}

install_gateway_source() {
  local relative="$1"
  [[ $# -eq 1 && "${SOURCE_WRITE_STATES[$relative]:-}" == UNTOUCHED
    && "${SOURCE_CANDIDATE_SHA[$relative]:-}" =~ ^[0-9a-f]{64}$ ]] || return 14
  # Pending is set before the write. Any failed/partial install or readback
  # remains unknown and must not authorize overwriting that target in recovery.
  SOURCE_WRITE_STATES[$relative]=WRITE_PENDING
  install -D -o root -g root -m 0644 -- "$STAGE_DIR/$relative" "$TARGET_ROOT/$relative" || return $?
  capture_source_target_version "$relative" "${SOURCE_CANDIDATE_SHA[$relative]}" || return $?
  SOURCE_TARGET_VERSION[$relative]="$CAPTURED_TARGET_VERSION"
  SOURCE_WRITE_STATES[$relative]=INSTALLED
}

read_recovery_target_state() {
  local relative="$1"
  [[ $# -eq 1 && "${SOURCE_CANDIDATE_SHA[$relative]:-}" =~ ^[0-9a-f]{64}$ ]] || return 14
  case "${SOURCE_WRITE_STATES[$relative]:-}" in
    UNTOUCHED)
      [[ -z "${SOURCE_TARGET_VERSION[$relative]:-}" ]] || return 14
      RECOVERY_TARGET_STATE=untouched ;;
    INSTALLED)
      [[ "${SOURCE_TARGET_VERSION[$relative]:-}" =~ ^[0-9a-f]{64}$ ]] || return 14
      capture_source_target_version "$relative" "${SOURCE_CANDIDATE_SHA[$relative]:-}" || return $?
      [[ "$CAPTURED_TARGET_VERSION" == "${SOURCE_TARGET_VERSION[$relative]}" ]] || return 14
      RECOVERY_TARGET_STATE=installed ;;
    *) return 14 ;;
  esac
}

require_recovery_target_absent() {
  local response
  response="$(source_target_version absent "$1" '' && printf '.')" || return $?
  [[ "$response" == $'absent\n.' ]] || return 14
}

STAGE_DIR="$(mktemp -d /tmp/lumencore-gateway-stage.XXXXXX)"
chmod 0700 "$STAGE_DIR"

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
    printf 'Private gateway recovery evidence retained: %s\n' "$BACKUP_DIR"
    printf 'Prepared recovery manifest SHA-256: %s\n' "${RECOVERY_MANIFEST_SHA:-PREPARATION_INCOMPLETE}"
  fi
  cleanup_manifest
}
trap cleanup EXIT
prepare_recovery_directory
install -d -m 0700 -- "$BACKUP_DIR/existing"

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
  SOURCE_WRITE_STATES[$rel]=UNTOUCHED
  SOURCE_CANDIDATE_SHA[$rel]="$(awk -v relative="$rel" '$2 == relative { print $1 }' "$MANIFEST_FILE")"
  [[ "${SOURCE_CANDIDATE_SHA[$rel]}" =~ ^[0-9a-f]{64}$ ]]
  [[ "$(sha256sum "$staged" | awk '{print $1}')" == "${SOURCE_CANDIDATE_SHA[$rel]}" ]]
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

# This private manifest and its readback must complete before service mutation.
RECOVERY_MANIFEST_SHA="$(record_recovery_evidence prepared 0)"
[[ "$RECOVERY_MANIFEST_SHA" =~ ^[0-9a-f]{64}$ ]]

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

read_gateway_lock_pid() {
  [[ $# -eq 0 ]] || return 14
  # Keep original file bytes out of shell substitution until their grammar is
  # validated. Never collapse internal whitespace or discard NUL bytes.
  "$PYTHON_BIN" - "$LOCK_FILE" <<'PY'
import os
import re
import stat
import sys

if len(sys.argv) != 2:
    raise SystemExit(14)
try:
    before = os.lstat(sys.argv[1])
    if not stat.S_ISREG(before.st_mode):
        raise SystemExit(14)
    flags = os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0) | getattr(os, "O_NONBLOCK", 0)
    with os.fdopen(os.open(sys.argv[1], flags), "rb") as stream:
        opened = os.fstat(stream.fileno())
        if not stat.S_ISREG(opened.st_mode) or (opened.st_dev, opened.st_ino) != (before.st_dev, before.st_ino):
            raise SystemExit(14)
        raw = stream.read(13)  # Ten digits plus one CRLF; the extra byte rejects oversize.
        after = os.fstat(stream.fileno())
    current = os.lstat(sys.argv[1])
    def version(info):
        return (info.st_dev, info.st_ino, info.st_mode, info.st_size, info.st_mtime_ns, info.st_ctime_ns)
    if version(before) != version(opened) or version(opened) != version(after) or version(after) != version(current):
        raise SystemExit(14)
    if len(raw) != opened.st_size or re.fullmatch(rb"[1-9][0-9]{0,9}(?:\r?\n)?", raw) is None:
        raise SystemExit(14)
    pid = int(raw)
    if pid > 2147483647:
        raise SystemExit(14)
except OSError:
    raise SystemExit(14)
sys.stdout.write(str(pid))
PY
}

require_absent_lock_owner() {
  [[ $# -eq 1 ]] || return 14
  # A failed signal-zero probe is not proof of absence. Authorize removal only
  # for explicit ESRCH; permission, range and unknown errors must fail closed.
  "$PYTHON_BIN" - "$1" <<'PY'
import errno
import os
import re
import sys

if len(sys.argv) != 2 or re.fullmatch(r"[1-9][0-9]{0,9}", sys.argv[1]) is None:
    raise SystemExit(14)
pid = int(sys.argv[1])
if pid > 2147483647:
    raise SystemExit(14)
try:
    os.kill(pid, 0)
except OSError as exc:
    raise SystemExit(0 if exc.errno == errno.ESRCH else 14)
except (OverflowError, ValueError):
    raise SystemExit(14)
raise SystemExit(14)
PY
}

read_gateway_lock_presence() {
  [[ $# -eq 0 ]] || return 14
  local observation
  # Only explicit ENOENT establishes absence. Preserve the interpreter status
  # and exact output, including unexpected trailing newlines, before trusting it.
  observation="$(
    "$PYTHON_BIN" - "$LOCK_FILE" <<'PY'
import errno
import os
import sys

if len(sys.argv) != 2:
    raise SystemExit(14)
try:
    os.lstat(sys.argv[1])
except OSError as exc:
    if exc.errno != errno.ENOENT:
        raise SystemExit(14)
    sys.stdout.write("ABSENT")
else:
    sys.stdout.write("PRESENT")
PY
    observation_rc=$?
    [[ "$observation_rc" -eq 0 ]] || exit "$observation_rc"
    printf ':LOCK_PRESENCE_END'
  )" || return $?
  case "$observation" in
    ABSENT:LOCK_PRESENCE_END) printf ABSENT ;;
    PRESENT:LOCK_PRESENCE_END) printf PRESENT ;;
    *) return 14 ;;
  esac
}

remove_verified_dead_lock() {
  local lock_presence lock_pid
  lock_presence="$(read_gateway_lock_presence)" || return $?
  if [[ "$lock_presence" == ABSENT ]]; then
    return 0
  fi
  [[ -f "$LOCK_FILE" && ! -L "$LOCK_FILE" ]] || {
    echo "ERROR: singleton lock is not a regular file" >&2
    return 14
  }
  lock_pid="$(read_gateway_lock_pid)" || return $?
  require_absent_lock_owner "$lock_pid" || {
    local probe_rc=$?
    echo "ERROR: singleton lock owner absence was not confirmed; refusing removal" >&2
    return "$probe_rc"
  }
  rm -f -- "$LOCK_FILE" || return $?
  lock_presence="$(read_gateway_lock_presence)" || return $?
  [[ "$lock_presence" == ABSENT ]] || return 14
  echo "Removed verified dead-PID gateway singleton lock."
}

bounded_recovery_systemctl() {
  local verb="${1:-}" command_rc=0
  local -a arguments=()
  [[ $# -eq 1 ]] || return 125
  case "$verb" in
    stop|reset-failed|start) arguments=("$SERVICE") ;;
    daemon-reload) ;;
    *) return 125 ;;
  esac
  # A separate process group lets timeout terminate its command, not this
  # recovery shell. KILL is required when inherited/child TERM is ignored.
  "$RECOVERY_TIMEOUT_BIN" --signal=TERM --kill-after=5s 60s \
    systemctl "$verb" "${arguments[@]}" >/dev/null 2>&1 || command_rc=$?
  RECOVERY_SERVICE_RESULTS+="$verb:$command_rc"$'\n'
  if [[ "$command_rc" -ne 0 ]]; then
    RECOVERY_SERVICE_FAILURE="$verb"
    echo "ERROR: recovery systemctl $verb failed (exit $command_rc); service state and manager job completion remain unverified" >&2
  fi
  return "$command_rc"
}

finish_rollback() {
  local rc="$1"
  if ! record_recovery_evidence rollback "$rc"; then
    echo "ERROR: private rollback receipt persistence failed; retained backups require manual review" >&2
  fi
  exit "$rc"
}

bounded_recovery_copy() {
  [[ $# -eq 2 ]] || return 125
  # Bound only this copy process group. A failed/terminated copy can leave a
  # partial destination; the caller stops recovery without retry or cleanup.
  "$RECOVERY_TIMEOUT_BIN" --signal=TERM --kill-after=5s 60s \
    cp -a -- "$1" "$2"
}

checked_restore_step() {
  local operation="$1" target_id="$2" operation_rc=0
  shift 2
  "$@" || operation_rc=$?
  if [[ "$operation_rc" -ne 0 ]]; then
    # Calls below use fixed operation IDs and bounded target identifiers. Keep
    # the first failure, never raw output, separately from the triggering rc.
    if [[ -z "$RECOVERY_RESTORE_FAILURE" ]]; then
      RECOVERY_RESTORE_FAILURE="$operation"
      RECOVERY_RESTORE_TARGET="$target_id"
      RECOVERY_RESTORE_EXIT_CODE="$operation_rc"
    fi
    echo "ERROR: restoration operation $operation failed (exit $operation_rc); partial state requires review" >&2
  fi
  return "$operation_rc"
}

read_recovery_state() {
  RECOVERY_STATE="$(< "$1")" || return $?
  [[ "$RECOVERY_STATE" == present || "$RECOVERY_STATE" == missing ]] || return 14
}

read_recovery_source_state() {
  local response
  # The sentinel preserves trailing newlines so extra/empty output cannot be
  # accepted accidentally. Query failure propagates even if it printed a state.
  response="$(record_recovery_evidence source_state 0 "$1" && printf '.')" || return $?
  case "$response" in
    $'present\n.') RECOVERY_SOURCE_STATE=present ;;
    $'missing\n.') RECOVERY_SOURCE_STATE=missing ;;
    *) return 14 ;;
  esac
  [[ -z "${2:-}" || "$RECOVERY_SOURCE_STATE" == "$2" ]] || return 14
}

read_recovery_source_result() {
  local relative="${1:-}" expected="${2:-}" response
  [[ $# -eq 2 && -n "$relative" && ( "$expected" == present || "$expected" == missing ) ]] || return 14
  SOURCE_RESULT_STATES[$relative]=FAILED
  response="$(record_recovery_evidence source_result 0 "$relative" && printf '.')" || return $?
  case "$response" in
    $'observed_present\n.')
      [[ "$expected" == present ]] || return 14
      SOURCE_RESULT_STATES[$relative]=MATCHED_PREPARED_PRESENT ;;
    $'observed_absent\n.')
      [[ "$expected" == missing ]] || return 14
      SOURCE_RESULT_STATES[$relative]=MATCHED_PREPARED_ABSENCE ;;
    *) return 14 ;;
  esac
}

read_recovery_dropin_result() {
  local expected="${1:-}" response
  [[ $# -eq 1 && ( "$expected" == present || "$expected" == missing ) ]] || return 14
  RECOVERY_DROPIN_RESULT=FAILED
  response="$(record_recovery_evidence dropin_result 0 && printf '.')" || return $?
  case "$response" in
    $'dropin_present\n.')
      [[ "$expected" == present ]] || return 14
      RECOVERY_DROPIN_RESULT=MATCHED_PREPARED_PRESENT ;;
    $'dropin_absent\n.')
      [[ "$expected" == missing ]] || return 14
      RECOVERY_DROPIN_RESULT=MATCHED_PREPARED_ABSENCE ;;
    *) return 14 ;;
  esac
}

read_recovery_metadata() {
  local metadata
  metadata="$(< "$1")" || return $?
  [[ "$metadata" =~ ^([0-9]+)[[:blank:]]+([0-9]+)[[:blank:]]+([0-7]{3,4})$ ]] || return 14
  RECOVERY_UID="${BASH_REMATCH[1]}"
  RECOVERY_GID="${BASH_REMATCH[2]}"
  RECOVERY_MODE="${BASH_REMATCH[3]}"
}

read_recovery_runtime_directory_result() {
  local expected="${1:-}" response
  [[ $# -eq 1 && ( "$expected" == present || "$expected" == missing ) ]] || return 14
  RECOVERY_RUNTIME_DIRECTORY_RESULT=FAILED
  response="$(record_recovery_evidence runtime_directory_result 0 && printf '.')" || return $?
  case "$response" in
    $'runtime_directory_present\n.')
      [[ "$expected" == present ]] || return 14
      RECOVERY_RUNTIME_DIRECTORY_RESULT=MATCHED_PREPARED_PRESENT ;;
    $'runtime_directory_absent\n.')
      [[ "$expected" == missing ]] || return 14
      RECOVERY_RUNTIME_DIRECTORY_RESULT=MATCHED_PREPARED_ABSENCE ;;
    *) return 14 ;;
  esac
}

read_recovery_dropin_directory_result() {
  local expected="${1:-}" response
  [[ $# -eq 1 && ( "$expected" == present || "$expected" == missing ) ]] || return 14
  RECOVERY_DROPIN_DIRECTORY_RESULT=FAILED
  response="$(record_recovery_evidence dropin_directory_result 0 && printf '.')" || return $?
  case "$response" in
    $'dropin_directory_present\n.')
      [[ "$expected" == present ]] || return 14
      RECOVERY_DROPIN_DIRECTORY_RESULT=MATCHED_PREPARED_PRESENT ;;
    $'dropin_directory_absent\n.')
      [[ "$expected" == missing ]] || return 14
      RECOVERY_DROPIN_DIRECTORY_RESULT=MATCHED_PREPARED_ABSENCE ;;
    *) return 14 ;;
  esac
}

remove_recovery_directory() {
  # Missing is the intended state; nonempty, linked or inaccessible is not.
  if [[ ! -e "$1" && ! -L "$1" ]]; then return 0; fi
  rmdir -- "$1" || return $?
}

rollback() {
  local rc="${1:-1}"
  # Recovery failures must not re-enter rollback or replace the triggering code.
  trap - ERR
  trap '' INT TERM
  set +e
  if [[ "$REPAIR_COMPLETE" != true ]]; then
    # Validate before the first service, lock or target-file mutation. This is a
    # point-in-time check, not protection against a subsequent concurrent edit.
    if ! require_safe_recovery_directory "$BACKUP_DIR" true || ! record_recovery_evidence verify "$rc"; then
      echo "ERROR: ROLLBACK_REFUSED_INVALID_RECOVERY_EVIDENCE; no restoration attempted; original failure retained" >&2
      if ! require_safe_recovery_directory "$BACKUP_DIR" true || ! record_recovery_evidence rollback_refused "$rc"; then
        echo "ERROR: private rollback refusal receipt unavailable; retained evidence requires manual review" >&2
      fi
      exit "$rc"
    fi
    echo "Rolling back the complete gateway dependency closure and service identity..." >&2
    if ! bounded_recovery_systemctl stop; then
      finish_rollback "$rc"
    fi
    RECOVERY_RESTORE_ATTEMPTED=true
    checked_restore_step dead_lock gateway_lock remove_verified_dead_lock || finish_rollback "$rc"
    for rel in "${BUNDLE_FILES[@]}"; do
      target="$TARGET_ROOT/$rel"
      backup="$BACKUP_DIR/existing/$rel"
      checked_restore_step source_state "$rel" read_recovery_source_state "$rel" || finish_rollback "$rc"
      checked_restore_step target_state "$rel" read_recovery_target_state "$rel" || finish_rollback "$rc"
      if [[ "$RECOVERY_TARGET_STATE" == untouched ]]; then
        SOURCE_RESULT_STATES[$rel]=UNCHECKED_UNTOUCHED
        continue
      fi
      checked_restore_step source_remove "$rel" rm -f -- "$target" || finish_rollback "$rc"
      if [[ "$RECOVERY_SOURCE_STATE" == present ]]; then
        # Recheck before copy as well: a removal may already have happened, but
        # changed recovery bytes must not be copied or followed by service start.
        checked_restore_step source_state "$rel" read_recovery_source_state "$rel" present || finish_rollback "$rc"
        checked_restore_step target_absent "$rel" require_recovery_target_absent "$rel" || finish_rollback "$rc"
        checked_restore_step source_copy "$rel" bounded_recovery_copy "$backup" "$target" || finish_rollback "$rc"
      fi
      checked_restore_step source_result "$rel" read_recovery_source_result "$rel" "$RECOVERY_SOURCE_STATE" || finish_rollback "$rc"
    done

    checked_restore_step dropin_directory_target_state service_drop_in_directory read_recovery_dropin_directory_target_state || finish_rollback "$rc"
    checked_restore_step dropin_target_state service_drop_in read_recovery_dropin_target_state || finish_rollback "$rc"
    if [[ "$RECOVERY_DROPIN_TARGET_STATE" == untouched ]]; then
      RECOVERY_DROPIN_RESULT=UNCHECKED_UNTOUCHED
    else
      checked_restore_step dropin_remove service_drop_in rm -f -- "$SERVICE_DROP_IN" || finish_rollback "$rc"
      checked_restore_step dropin_state_read service_drop_in read_recovery_state "$BACKUP_DIR/service-drop-in.state" || finish_rollback "$rc"
      prior_drop_in_state="$RECOVERY_STATE"
      if [[ "$prior_drop_in_state" == "present" ]]; then
        checked_restore_step dropin_directory_target_state service_drop_in_directory read_recovery_dropin_directory_target_state || finish_rollback "$rc"
        checked_restore_step dropin_parent_create service_drop_in_directory install -d -o root -g root -m 0755 -- "$SERVICE_DROP_IN_DIR" || finish_rollback "$rc"
        checked_restore_step dropin_target_absent service_drop_in require_recovery_dropin_absent || finish_rollback "$rc"
        checked_restore_step dropin_copy service_drop_in bounded_recovery_copy "$BACKUP_DIR/service-drop-in.before" "$SERVICE_DROP_IN" || finish_rollback "$rc"
      fi
      checked_restore_step dropin_result service_drop_in read_recovery_dropin_result "$prior_drop_in_state" || finish_rollback "$rc"
    fi
    if [[ "$RECOVERY_DROPIN_DIRECTORY_TARGET_STATE" == untouched ]]; then
      RECOVERY_DROPIN_DIRECTORY_RESULT=UNCHECKED_UNTOUCHED
    else
      checked_restore_step dropin_directory_state_read service_drop_in_directory read_recovery_state "$BACKUP_DIR/service-drop-in-dir.state" || finish_rollback "$rc"
      prior_drop_in_dir_state="$RECOVERY_STATE"
      if [[ "$prior_drop_in_dir_state" == "present" ]]; then
        checked_restore_step dropin_metadata_read service_drop_in_directory read_recovery_metadata "$BACKUP_DIR/service-drop-in-dir.metadata" || finish_rollback "$rc"
        checked_restore_step dropin_directory_target_state service_drop_in_directory read_recovery_dropin_directory_target_state || finish_rollback "$rc"
        checked_restore_step dropin_chown service_drop_in_directory chown --no-dereference "$RECOVERY_UID:$RECOVERY_GID" "$SERVICE_DROP_IN_DIR" || finish_rollback "$rc"
        checked_restore_step dropin_chmod service_drop_in_directory chmod "$RECOVERY_MODE" "$SERVICE_DROP_IN_DIR" || finish_rollback "$rc"
      else
        checked_restore_step dropin_directory_target_state service_drop_in_directory read_recovery_dropin_directory_target_state || finish_rollback "$rc"
        checked_restore_step dropin_directory_remove service_drop_in_directory remove_recovery_directory "$SERVICE_DROP_IN_DIR" || finish_rollback "$rc"
      fi
      checked_restore_step dropin_directory_result service_drop_in_directory read_recovery_dropin_directory_result "$prior_drop_in_dir_state" || finish_rollback "$rc"
    fi

    checked_restore_step run_target_state run_directory read_recovery_runtime_directory_target_state || finish_rollback "$rc"
    if [[ "$RECOVERY_RUN_TARGET_STATE" == untouched ]]; then
      RECOVERY_RUNTIME_DIRECTORY_RESULT=UNCHECKED_UNTOUCHED
    else
      checked_restore_step run_directory_state_read run_directory read_recovery_state "$BACKUP_DIR/run-dir.state" || finish_rollback "$rc"
      prior_run_dir_state="$RECOVERY_STATE"
      if [[ "$prior_run_dir_state" == "present" ]]; then
        checked_restore_step run_metadata_read run_directory read_recovery_metadata "$BACKUP_DIR/run-dir.metadata" || finish_rollback "$rc"
        checked_restore_step run_chown run_directory chown --no-dereference "$RECOVERY_UID:$RECOVERY_GID" "$RUN_DIR" || finish_rollback "$rc"
        checked_restore_step run_chmod run_directory chmod "$RECOVERY_MODE" "$RUN_DIR" || finish_rollback "$rc"
      else
        checked_restore_step run_directory_remove run_directory remove_recovery_directory "$RUN_DIR" || finish_rollback "$rc"
      fi
      checked_restore_step runtime_directory_result run_directory read_recovery_runtime_directory_result "$prior_run_dir_state" || finish_rollback "$rc"
    fi

    if ! bounded_recovery_systemctl daemon-reload; then
      finish_rollback "$rc"
    fi
    if ! bounded_recovery_systemctl reset-failed; then
      finish_rollback "$rc"
    fi
    if [[ "$SERVICE_WAS_ACTIVE" == true ]]; then
      if ! bounded_recovery_systemctl start; then
        finish_rollback "$rc"
      fi
    fi
    SERVICE_STOPPED=false
  fi
  finish_rollback "$rc"
}

trap 'rc=$?; echo "ERROR: gateway closure repair stopped on line $LINENO" >&2; rollback "$rc"' ERR
trap 'echo "Gateway closure repair interrupted." >&2; rollback 130' INT TERM

systemctl stop "$SERVICE"
SERVICE_STOPPED=true
remove_verified_dead_lock

install_gateway_dropin_directory
install_gateway_dropin
[[ "$(sha256sum "$SERVICE_DROP_IN" | awk '{print $1}')" == "$HARDENING_SHA" ]] || {
  echo "ERROR: installed gateway service hardening SHA-256 mismatch" >&2
  rollback 17
}
install_gateway_runtime_directory
systemctl daemon-reload

POST_APPLY_HASH_MATCHES=0
printf '%-64s  %-64s  %s\n' "POST_APPLY_SOURCE_SHA256" "POST_APPLY_TARGET_SHA256" "RELATIVE_PATH"
for rel in "${BUNDLE_FILES[@]}"; do
  install_gateway_source "$rel"
  post_apply_source_sha="$(sha256sum "$SOURCE_ROOT/$rel" | awk '{print $1}')"
  post_apply_target_sha="$(sha256sum "$TARGET_ROOT/$rel" | awk '{print $1}')"
  printf '%-64s  %-64s  %s\n' "$post_apply_source_sha" "$post_apply_target_sha" "$rel"
  [[ "$post_apply_source_sha" == "$post_apply_target_sha" ]] || {
    echo "ERROR: post-apply source/target SHA-256 mismatch: $rel" >&2
    rollback 17
  }
  POST_APPLY_HASH_MATCHES=$((POST_APPLY_HASH_MATCHES + 1))
done
printf 'POST_APPLY_HASH_PARITY=%s/%s\n' "$POST_APPLY_HASH_MATCHES" "${#BUNDLE_FILES[@]}"

systemctl reset-failed "$SERVICE" >/dev/null 2>&1 || true
systemctl start "$SERVICE"
SERVICE_STOPPED=false

systemctl is-active --quiet "$SERVICE" || {
  echo "ERROR: gateway service did not become active" >&2
  rollback 18
}
effective_user="$(systemctl show "$SERVICE" --property=User --value)"
effective_group="$(systemctl show "$SERVICE" --property=Group --value)"
effective_restart="$(systemctl show "$SERVICE" --property=Restart --value)"
effective_umask="$(systemctl show "$SERVICE" --property=UMask --value)"
effective_no_new_privileges="$(systemctl show "$SERVICE" --property=NoNewPrivileges --value)"
effective_private_tmp="$(systemctl show "$SERVICE" --property=PrivateTmp --value)"
[[ "$effective_user" == "$SERVICE_USER" && "$effective_group" == "$SERVICE_GROUP" ]] || {
  echo "ERROR: effective gateway service identity is not lumencore:lumencore" >&2
  rollback 18
}
[[ "$effective_restart" == "on-failure" ]] || {
  echo "ERROR: effective gateway restart policy is not bounded to on-failure" >&2
  rollback 18
}
[[ "$effective_umask" == "0027" ]] || {
  echo "ERROR: effective gateway umask is not 0027" >&2
  rollback 18
}
[[ "$effective_no_new_privileges" == "yes" || "$effective_no_new_privileges" == "true" ]] || {
  echo "ERROR: effective gateway NoNewPrivileges control is not enabled" >&2
  rollback 18
}
[[ "$effective_private_tmp" == "yes" || "$effective_private_tmp" == "true" ]] || {
  echo "ERROR: effective gateway PrivateTmp control is not enabled" >&2
  rollback 18
}
[[ "$(stat -c '%U:%G:%a' "$SERVICE_DROP_IN")" == "root:root:644" ]] || {
  echo "ERROR: gateway service hardening file ownership or mode is unsafe" >&2
  rollback 18
}
[[ "$(stat -c '%U:%G:%a' "$RUN_DIR")" == "${SERVICE_USER}:${SERVICE_GROUP}:750" ]] || {
  echo "ERROR: gateway run directory identity is not bounded" >&2
  rollback 18
}

lock_ready=false
for attempt in $(seq 1 12); do
  if [[ -f "$LOCK_FILE" && ! -L "$LOCK_FILE" ]]; then
    main_pid="$(systemctl show "$SERVICE" --property=MainPID --value)"
    lock_pid="$(read_gateway_lock_pid)" || rollback 18
    if [[ "$main_pid" =~ ^[1-9][0-9]*$ && "$lock_pid" == "$main_pid" ]]; then
      lock_ready=true
      break
    fi
  fi
  sleep 1
done
[[ "$lock_ready" == true ]] || {
  echo "ERROR: gateway singleton lock did not bind to the systemd main PID" >&2
  rollback 18
}
[[ "$(stat -c '%U:%G:%a' "$LOCK_FILE")" == "${SERVICE_USER}:${SERVICE_GROUP}:640" ]] || {
  echo "ERROR: gateway singleton lock identity is not bounded" >&2
  rollback 18
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

if ! helper_receipt_sha="$(record_recovery_evidence helper 0)"; then
  echo "ERROR: private helper receipt persistence failed after mutation" >&2
  rollback 23
fi
REPAIR_COMPLETE=true
trap - ERR INT TERM
echo "GATEWAY_RUNTIME_CLOSURE_REPAIR_OK"
echo "GATEWAY_DEPENDENCY_CLOSURE_REPAIR_OK"
echo "Source commit: $SOURCE_COMMIT"
echo "Bundle SHA-256: $BUNDLE_SHA"
echo "Service hardening SHA-256: $HARDENING_SHA"
echo "Private helper outcome receipt SHA-256: $helper_receipt_sha"
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
