#!/usr/bin/env bash
# Repair the exact paper-ticker ledger ownership defect and bound its restart policy.
# Inspect-only by default. --apply is the only write path.
set -Eeuo pipefail

SERVICE="luma-paper-ticker"
SERVICE_USER="lumencore"
SERVICE_GROUP="lumencore"
STACK_ROOT="/opt/lumencore"
OUTPUT_ROOT="${STACK_ROOT}/out"
EXECUTION_OUTPUT="${OUTPUT_ROOT}/execution"
LEDGER="${EXECUTION_OUTPUT}/multi_exchange_paper_ticker_ledger.jsonl"
DROPIN_DIR="/etc/systemd/system/${SERVICE}.service.d"
DROPIN_FILE="${DROPIN_DIR}/10-restart-bounds.conf"
SOURCE_COMMIT="${LUMENCORE_PAPER_REPAIR_SOURCE_COMMIT:-}"
EXPECTED_SCRIPT_SHA="${LUMENCORE_EXPECTED_PAPER_REPAIR_SCRIPT_SHA256:-}"
EXPECTED_LEDGER_SHA="${LUMENCORE_EXPECTED_PAPER_LEDGER_SHA256:-}"
EXPECTED_LEDGER_OWNER="${LUMENCORE_EXPECTED_PAPER_LEDGER_OWNER:-}"
EXPECTED_LEDGER_GROUP="${LUMENCORE_EXPECTED_PAPER_LEDGER_GROUP:-}"
EXPECTED_LEDGER_MODE="${LUMENCORE_EXPECTED_PAPER_LEDGER_MODE:-}"
HUMAN_UNLOCK_FILE="${LUMENCORE_HUMAN_UNLOCK_FILE:-}"
APPLY=false
REPAIR_COMPLETE=false
METADATA_CHANGED=false
DROPIN_CHANGED=false
PREVIOUS_SERVICE_STATE=""
BACKUP_DIR=""
HAD_DROPIN=false
HAD_DROPIN_DIR=false

usage() {
  cat <<'EOF'
Usage:
  bash code/ops/REPAIR_PAPER_TICKER_LEDGER_ON_VPS.sh
  sudo bash code/ops/REPAIR_PAPER_TICKER_LEDGER_ON_VPS.sh --apply

Inspect mode reports only the exact ledger path-chain metadata, service-account
access predicates, and bounded service identity. Apply mode additionally
requires root, a private HumanUnlock value, the exact current-main commit, the
approved repair-script SHA-256, and the predeclared ledger SHA/owner/group/mode.
It stops only luma-paper-ticker, changes only the exact ledger metadata, installs
one bounded restart-policy drop-in, restarts only that paper service, verifies
stability, and rolls metadata and the drop-in back on failure.
EOF
}

for arg in "$@"; do
  case "$arg" in
    --apply) APPLY=true ;;
    -h|--help) usage; exit 0 ;;
    *) echo "ERROR: unknown argument: $arg" >&2; usage >&2; exit 2 ;;
  esac
done

for command_name in realpath stat sha256sum systemctl journalctl id getent sudo awk cut grep install mktemp chmod chown rm rmdir date sleep cat; do
  command -v "$command_name" >/dev/null 2>&1 || {
    echo "ERROR: required command is missing: $command_name" >&2
    exit 3
  }
done

SCRIPT_PATH="$(realpath -e -- "${BASH_SOURCE[0]}")"
SCRIPT_SHA="$(sha256sum "$SCRIPT_PATH" | awk '{print $1}')"
LEDGER_RESOLVED="$(realpath -m -- "$LEDGER")"
[[ "$LEDGER_RESOLVED" == "$LEDGER" ]] || {
  echo "ERROR: ledger path did not resolve to the exact approved target" >&2
  exit 4
}

for path in "$STACK_ROOT" "$OUTPUT_ROOT" "$EXECUTION_OUTPUT" "$LEDGER"; do
  [[ ! -L "$path" ]] || {
    echo "ERROR: symbolic path is not allowed: $path" >&2
    exit 4
  }
done
[[ -d "$STACK_ROOT" && -d "$OUTPUT_ROOT" && -d "$EXECUTION_OUTPUT" ]] || {
  echo "ERROR: required paper-ticker parent directory is missing" >&2
  exit 5
}
[[ -f "$LEDGER" ]] || {
  echo "ERROR: exact paper-ticker ledger is not a regular file" >&2
  exit 5
}
[[ "$(stat -c '%h' "$LEDGER")" == "1" ]] || {
  echo "ERROR: paper-ticker ledger has multiple hard links" >&2
  exit 5
}

service_user_uid="$(id -u "$SERVICE_USER")"
service_group_gid="$(getent group "$SERVICE_GROUP" | cut -d: -f3)"
[[ "$service_user_uid" =~ ^[0-9]+$ && "$service_group_gid" =~ ^[0-9]+$ ]] || {
  echo "ERROR: paper-ticker service identity is unavailable" >&2
  exit 6
}

show_path() {
  local label="$1"
  local path="$2"
  echo "--- $label ---"
  stat --printf='type=%F mode=%a owner=%U group=%G bytes=%s links=%h modified=%y\n' "$path"
  for permission in e r w x; do
    if sudo -n -u "$SERVICE_USER" test "-$permission" "$path" 2>/dev/null; then
      echo "${SERVICE_USER}_test_${permission}=true"
    else
      echo "${SERVICE_USER}_test_${permission}=false"
    fi
  done
}

echo "PAPER_TICKER_LEDGER_REPAIR_INSPECTION"
echo "Repair script SHA-256: $SCRIPT_SHA"
echo "Source commit: ${SOURCE_COMMIT:-not-declared}"
show_path stack_root "$STACK_ROOT"
show_path output_root "$OUTPUT_ROOT"
show_path execution_output "$EXECUTION_OUTPUT"
show_path paper_ticker_ledger "$LEDGER"

systemctl cat "$SERVICE" >/dev/null
service_user="$(systemctl show "$SERVICE" --property=User --value)"
service_group="$(systemctl show "$SERVICE" --property=Group --value)"
working_directory="$(systemctl show "$SERVICE" --property=WorkingDirectory --value)"
exec_start="$(systemctl show "$SERVICE" --property=ExecStart --value)"
exec_start_pre="$(systemctl show "$SERVICE" --property=ExecStartPre --value)"
printf 'service_active=%s\n' "$(systemctl is-active "$SERVICE" 2>/dev/null || true)"
printf 'service_user=%s\nservice_group=%s\nworking_directory=%s\n' \
  "$service_user" "$service_group" "$working_directory"
[[ "$service_user" == "$SERVICE_USER" ]] || {
  echo "ERROR: paper-ticker service user is not the approved identity" >&2
  exit 7
}
[[ "$service_group" == "$SERVICE_GROUP" ]] || {
  echo "ERROR: paper-ticker service group is not the approved identity" >&2
  exit 7
}
[[ "$working_directory" == "/opt/lumencore/code" ]] || {
  echo "ERROR: paper-ticker working directory is not approved" >&2
  exit 7
}
[[ "$exec_start" == *"/opt/lumencore/code/multi_exchange_paper_ticker.py"* ]] || {
  echo "ERROR: paper-ticker executable identity does not match" >&2
  exit 7
}
[[ "$exec_start" == *"--profile apex"* && "$exec_start" == *"--seed-capital 250000"* ]] || {
  echo "ERROR: paper-ticker execution profile does not match" >&2
  exit 7
}
[[ "$exec_start_pre" == *"/opt/lumencore/code/ops/assert_runtime_safety.py"* ]] || {
  echo "ERROR: paper-only runtime preflight is missing" >&2
  exit 7
}

if [[ "$APPLY" != true ]]; then
  exit 0
fi

[[ "${EUID}" -eq 0 ]] || {
  echo "ERROR: --apply must run as root" >&2
  exit 8
}
[[ "$SOURCE_COMMIT" =~ ^[0-9a-f]{40}$ ]] || {
  echo "ERROR: --apply requires the exact 40-character source commit" >&2
  exit 9
}
[[ "$EXPECTED_SCRIPT_SHA" =~ ^[0-9a-f]{64}$ && "$EXPECTED_SCRIPT_SHA" == "$SCRIPT_SHA" ]] || {
  echo "ERROR: repair script does not match the approved SHA-256" >&2
  exit 9
}
[[ "$EXPECTED_LEDGER_SHA" =~ ^[0-9a-f]{64}$ ]] || {
  echo "ERROR: --apply requires the expected ledger SHA-256" >&2
  exit 9
}
[[ "$EXPECTED_LEDGER_OWNER" == "opc" && "$EXPECTED_LEDGER_GROUP" == "opc" && "$EXPECTED_LEDGER_MODE" == "644" ]] || {
  echo "ERROR: predeclared ledger metadata does not match the approved incident" >&2
  exit 9
}
[[ "$HUMAN_UNLOCK_FILE" =~ ^/tmp/lumencore-paper-ticker-repair-[0-9]+-[0-9]+/human-unlock$ ]] || {
  echo "ERROR: --apply requires the bounded private HumanUnlock file" >&2
  exit 10
}
[[ -f "$HUMAN_UNLOCK_FILE" && ! -L "$HUMAN_UNLOCK_FILE" ]] || {
  echo "ERROR: private HumanUnlock file is missing or symbolic" >&2
  exit 10
}
[[ "$(stat -c '%U:%a' "$HUMAN_UNLOCK_FILE")" == "opc:600" ]] || {
  echo "ERROR: private HumanUnlock file ownership or mode is unsafe" >&2
  exit 10
}
human_unlock_token="$(<"$HUMAN_UNLOCK_FILE")"
[[ ${#human_unlock_token} -ge 32 ]] || {
  echo "ERROR: --apply requires a private HumanUnlock value of at least 32 characters" >&2
  exit 10
}
unset human_unlock_token

initial_sha="$(sha256sum "$LEDGER" | awk '{print $1}')"
initial_owner="$(stat -c '%U' "$LEDGER")"
initial_group="$(stat -c '%G' "$LEDGER")"
initial_uid="$(stat -c '%u' "$LEDGER")"
initial_gid="$(stat -c '%g' "$LEDGER")"
initial_mode="$(stat -c '%a' "$LEDGER")"
[[ "$initial_sha" == "$EXPECTED_LEDGER_SHA" ]] || {
  echo "ERROR: ledger bytes changed after the approved diagnostic" >&2
  exit 11
}
[[ "$initial_owner" == "$EXPECTED_LEDGER_OWNER" && "$initial_group" == "$EXPECTED_LEDGER_GROUP" && "$initial_mode" == "$EXPECTED_LEDGER_MODE" ]] || {
  echo "ERROR: ledger metadata changed after the approved diagnostic" >&2
  exit 11
}
[[ "$(stat -c '%U:%G:%a' "$OUTPUT_ROOT")" == "lumencore:lumencore:755" ]] || {
  echo "ERROR: output-root metadata differs from the approved diagnostic" >&2
  exit 11
}
[[ "$(stat -c '%U:%G:%a' "$EXECUTION_OUTPUT")" == "lumencore:lumencore:755" ]] || {
  echo "ERROR: execution-output metadata differs from the approved diagnostic" >&2
  exit 11
}
sudo -n -u "$SERVICE_USER" test -w "$EXECUTION_OUTPUT"

if [[ -e "$DROPIN_FILE" ]]; then
  [[ -f "$DROPIN_FILE" && ! -L "$DROPIN_FILE" ]] || {
    echo "ERROR: existing restart-policy drop-in is not a regular file" >&2
    exit 12
  }
  HAD_DROPIN=true
fi
if [[ -e "$DROPIN_DIR" ]]; then
  [[ -d "$DROPIN_DIR" && ! -L "$DROPIN_DIR" ]] || {
    echo "ERROR: restart-policy drop-in directory is not a regular directory" >&2
    exit 12
  }
  HAD_DROPIN_DIR=true
fi

PREVIOUS_SERVICE_STATE="$(systemctl is-active "$SERVICE" 2>/dev/null || true)"
BACKUP_DIR="$(mktemp -d /tmp/lumencore-paper-ticker-rollback.XXXXXX)"
chmod 0700 "$BACKUP_DIR"
if [[ "$HAD_DROPIN" == true ]]; then
  install -m 0600 -- "$DROPIN_FILE" "$BACKUP_DIR/restart-bounds.conf"
fi

cleanup() {
  if [[ -n "$BACKUP_DIR" ]]; then
    [[ "$BACKUP_DIR" =~ ^/tmp/lumencore-paper-ticker-rollback\.[A-Za-z0-9]+$ ]] || {
      echo "ERROR: refusing unexpected rollback-directory cleanup target" >&2
      return 1
    }
    rm -rf -- "$BACKUP_DIR"
    BACKUP_DIR=""
  fi
}

rollback() {
  local rc="${1:-1}"
  set +e
  if [[ "$REPAIR_COMPLETE" != true ]]; then
    echo "Rolling back paper-ticker ledger metadata and restart policy..." >&2
    systemctl stop "$SERVICE" >/dev/null 2>&1 || true
    if [[ "$METADATA_CHANGED" == true ]]; then
      chown --no-dereference "$initial_uid:$initial_gid" "$LEDGER" >/dev/null 2>&1 || true
      chmod "$initial_mode" "$LEDGER" >/dev/null 2>&1 || true
    fi
    if [[ "$DROPIN_CHANGED" == true ]]; then
      if [[ "$HAD_DROPIN" == true ]]; then
        install -D -o root -g root -m 0644 -- "$BACKUP_DIR/restart-bounds.conf" "$DROPIN_FILE" >/dev/null 2>&1 || true
      else
        rm -f -- "$DROPIN_FILE"
      fi
    fi
    if [[ "$HAD_DROPIN_DIR" != true ]]; then
      rmdir -- "$DROPIN_DIR" >/dev/null 2>&1 || true
    fi
    systemctl daemon-reload >/dev/null 2>&1 || true
    systemctl reset-failed "$SERVICE" >/dev/null 2>&1 || true
    case "$PREVIOUS_SERVICE_STATE" in
      active|activating|reloading) systemctl start "$SERVICE" >/dev/null 2>&1 || true ;;
    esac
  fi
  cleanup
  exit "$rc"
}

trap 'rc=$?; echo "ERROR: paper-ticker repair stopped on line $LINENO" >&2; rollback "$rc"' ERR
trap 'echo "Paper-ticker repair interrupted." >&2; rollback 130' INT TERM
trap cleanup EXIT

repair_started_utc="$(date -u '+%Y-%m-%d %H:%M:%S UTC')"
systemctl stop "$SERVICE"

# Recheck the exact action binding after the service is stopped.
[[ "$(sha256sum "$LEDGER" | awk '{print $1}')" == "$initial_sha" ]]
[[ "$(stat -c '%U:%G:%a:%h' "$LEDGER")" == "${initial_owner}:${initial_group}:${initial_mode}:1" ]]

METADATA_CHANGED=true
chown --no-dereference "$SERVICE_USER:$SERVICE_GROUP" "$LEDGER"
chmod 0640 "$LEDGER"
[[ "$(sha256sum "$LEDGER" | awk '{print $1}')" == "$initial_sha" ]]
[[ "$(stat -c '%U:%G:%a:%h' "$LEDGER")" == "lumencore:lumencore:640:1" ]]
sudo -n -u "$SERVICE_USER" test -w "$LEDGER"

install -d -o root -g root -m 0755 "$DROPIN_DIR"
dropin_stage="$(mktemp "$BACKUP_DIR/restart-bounds.XXXXXX")"
cat > "$dropin_stage" <<'EOF'
[Unit]
StartLimitIntervalSec=300
StartLimitBurst=5

[Service]
Restart=on-failure
RestartSec=20s
UMask=0027
EOF
DROPIN_CHANGED=true
install -o root -g root -m 0644 -- "$dropin_stage" "$DROPIN_FILE"
systemctl daemon-reload
systemctl reset-failed "$SERVICE" >/dev/null 2>&1 || true
systemctl start "$SERVICE"

sleep 12
[[ "$(systemctl is-active "$SERVICE")" == "active" ]]
restart_count_before="$(systemctl show "$SERVICE" --property=NRestarts --value)"
sleep 5
[[ "$(systemctl is-active "$SERVICE")" == "active" ]]
restart_count_after="$(systemctl show "$SERVICE" --property=NRestarts --value)"
[[ "$restart_count_before" == "$restart_count_after" ]]
[[ "$(stat -c '%U:%G:%a:%h' "$LEDGER")" == "lumencore:lumencore:640:1" ]]
sudo -n -u "$SERVICE_USER" test -w "$LEDGER"

post_window="$(journalctl -u "$SERVICE" --since "$repair_started_utc" --no-pager -o cat 2>&1 || true)"
if printf '%s\n' "$post_window" | grep -F "Permission denied: '$LEDGER'" >/dev/null; then
  echo "ERROR: paper-ticker ledger PermissionError recurred after repair" >&2
  rollback 13
fi

REPAIR_COMPLETE=true
trap - ERR INT TERM
echo "PAPER_TICKER_LEDGER_REPAIR_OK"
echo "Source commit: $SOURCE_COMMIT"
echo "Repair script SHA-256: $SCRIPT_SHA"
echo "Pre-repair ledger SHA-256: $initial_sha"
echo "Ledger metadata: lumencore:lumencore:640"
echo "Restart count stable: $restart_count_after"
