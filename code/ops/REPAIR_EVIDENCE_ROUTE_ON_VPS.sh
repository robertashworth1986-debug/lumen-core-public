#!/usr/bin/env bash
# Atomic production repair for https://lumen-core.ai/evidence/
# Inspect-only by default. --apply is the only write path.
set -Eeuo pipefail

DOCUMENT_ROOT="${LUMENCORE_DASHBOARD_ROOT:-/opt/lumencore/dashboard}"
SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
REPAIR_TOOL="${SCRIPT_DIR}/repair_evidence_route.py"
DOMAIN="${LUMENCORE_DOMAIN:-lumen-core.ai}"
MARKER='name="lumencore-surface" content="proof-to-pilot-evidence-v1"'
APPLY=false
CONFIG=""
ROLLBACK=""
REPAIR_COMPLETE=false

usage() {
  cat <<'EOF'
Usage:
  bash code/ops/REPAIR_EVIDENCE_ROUTE_ON_VPS.sh
  sudo bash code/ops/REPAIR_EVIDENCE_ROUTE_ON_VPS.sh --apply

Optional environment:
  LUMENCORE_NGINX_CONFIG=/path/to/active/lumatrader.conf
  LUMENCORE_DASHBOARD_ROOT=/opt/lumencore/dashboard
  LUMENCORE_DOMAIN=lumen-core.ai

Inspect-only mode prints the exact proposed diff. Apply mode requires root,
creates a rollback copy, validates nginx, reloads only after validation, and
requires both the local and public route to return the bounded page marker.
EOF
}

for arg in "$@"; do
  case "$arg" in
    --apply) APPLY=true ;;
    -h|--help) usage; exit 0 ;;
    *) echo "ERROR: unknown argument: $arg" >&2; usage >&2; exit 2 ;;
  esac
done

detect_config() {
  if [[ -n "${LUMENCORE_NGINX_CONFIG:-}" ]]; then
    [[ -f "$LUMENCORE_NGINX_CONFIG" ]] || {
      echo "ERROR: configured nginx file does not exist: $LUMENCORE_NGINX_CONFIG" >&2
      return 1
    }
    printf '%s\n' "$LUMENCORE_NGINX_CONFIG"
    return 0
  fi

  local enabled="/etc/nginx/sites-enabled/lumatrader"
  if [[ -L "$enabled" ]]; then
    local target
    target="$(readlink -f "$enabled")"
    if [[ -f "$target" ]]; then
      printf '%s\n' "$target"
      return 0
    fi
  fi

  local candidates=(
    "/etc/nginx/sites-available/lumatrader"
    "/etc/nginx/conf.d/lumatrader.conf"
  )
  local found=()
  local candidate
  for candidate in "${candidates[@]}"; do
    [[ -f "$candidate" ]] && found+=("$candidate")
  done

  if [[ "${#found[@]}" -eq 1 ]]; then
    printf '%s\n' "${found[0]}"
    return 0
  fi
  if [[ "${#found[@]}" -eq 0 ]]; then
    echo "ERROR: no lumatrader nginx config found" >&2
  else
    echo "ERROR: multiple nginx configs found; set LUMENCORE_NGINX_CONFIG explicitly" >&2
    printf '  %s\n' "${found[@]}" >&2
  fi
  return 1
}

CONFIG="$(detect_config)"

[[ -f "$REPAIR_TOOL" ]] || { echo "ERROR: repair tool not found: $REPAIR_TOOL" >&2; exit 3; }
[[ -f "$DOCUMENT_ROOT/evidence/index_bounded.html" ]] || {
  echo "ERROR: bounded page not found: $DOCUMENT_ROOT/evidence/index_bounded.html" >&2
  exit 4
}
command -v python3 >/dev/null 2>&1 || { echo "ERROR: python3 is required" >&2; exit 5; }

echo "Nginx config: $CONFIG"
echo "Dashboard root: $DOCUMENT_ROOT"

if [[ "$APPLY" != true ]]; then
  python3 "$REPAIR_TOOL" --config "$CONFIG" --document-root "$DOCUMENT_ROOT" --show-diff
  exit $?
fi

[[ "${EUID}" -eq 0 ]] || { echo "ERROR: --apply must run as root" >&2; exit 6; }
command -v nginx >/dev/null 2>&1 || { echo "ERROR: nginx command not found" >&2; exit 7; }
command -v systemctl >/dev/null 2>&1 || { echo "ERROR: systemctl command not found" >&2; exit 8; }
command -v curl >/dev/null 2>&1 || { echo "ERROR: curl command not found" >&2; exit 9; }

STAMP="$(date -u +%Y%m%dT%H%M%SZ)"
ROLLBACK="${CONFIG}.deploy-rollback.${STAMP}"
cp -a -- "$CONFIG" "$ROLLBACK"
echo "Rollback copy: $ROLLBACK"

rollback() {
  local rc="${1:-1}"
  if [[ "$REPAIR_COMPLETE" != true && -f "$ROLLBACK" ]]; then
    echo "Rolling back nginx configuration..." >&2
    cp -a -- "$ROLLBACK" "$CONFIG"
    if nginx -t; then systemctl reload nginx || true; fi
  fi
  exit "$rc"
}

trap 'rc=$?; echo "ERROR: evidence deployment stopped on line $LINENO" >&2; rollback "$rc"' ERR
trap 'echo "Deployment interrupted." >&2; rollback 130' INT TERM

python3 "$REPAIR_TOOL" --config "$CONFIG" --document-root "$DOCUMENT_ROOT" --show-diff --apply
nginx -t
systemctl reload nginx
echo "Nginx reloaded after a successful configuration test."

LOCAL_BODY="$(mktemp)"
PUBLIC_BODY="$(mktemp)"
trap 'rm -f "$LOCAL_BODY" "$PUBLIC_BODY"' EXIT

LOCAL_STATUS="000"
for attempt in $(seq 1 10); do
  LOCAL_STATUS="$(curl -sS --max-time 15 --resolve "${DOMAIN}:443:127.0.0.1" -o "$LOCAL_BODY" -w '%{http_code}' "https://${DOMAIN}/evidence/?deploy=${STAMP}-local-${attempt}" || true)"
  if [[ "$LOCAL_STATUS" == "200" ]] && grep -Fq "$MARKER" "$LOCAL_BODY"; then break; fi
  sleep 1
done
if [[ "$LOCAL_STATUS" != "200" ]] || ! grep -Fq "$MARKER" "$LOCAL_BODY"; then
  echo "ERROR: local evidence route failed marker check (HTTP ${LOCAL_STATUS:-000})" >&2
  rollback 10
fi

PUBLIC_STATUS="000"
for attempt in $(seq 1 10); do
  PUBLIC_STATUS="$(curl -sS --max-time 15 -o "$PUBLIC_BODY" -w '%{http_code}' "https://${DOMAIN}/evidence/?deploy=${STAMP}-${attempt}" || true)"
  if [[ "$PUBLIC_STATUS" == "200" ]] && grep -Fq "$MARKER" "$PUBLIC_BODY"; then break; fi
  sleep 3
done

if [[ "$PUBLIC_STATUS" != "200" ]] || ! grep -Fq "$MARKER" "$PUBLIC_BODY"; then
  echo "ERROR: public evidence route failed marker check (HTTP ${PUBLIC_STATUS:-000})" >&2
  rollback 11
fi

REPAIR_COMPLETE=true
trap - ERR INT TERM
echo "OK: /evidence/ serves the bounded proof-to-pilot page locally and publicly."
echo "Local HTTP: $LOCAL_STATUS | Public HTTP: $PUBLIC_STATUS"
