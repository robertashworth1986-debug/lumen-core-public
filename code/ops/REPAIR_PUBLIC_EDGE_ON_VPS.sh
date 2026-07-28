#!/usr/bin/env bash
# Atomic nginx public-edge repair. Inspect-only unless --apply is supplied.
set -Eeuo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
REPAIR_TOOL="${SCRIPT_DIR}/repair_public_edge.py"
DOMAIN="${LUMENCORE_DOMAIN:-lumen-core.ai}"
APPLY=false
CONFIG=""
ROLLBACK=""
REPAIR_COMPLETE=false

usage() {
  cat <<'EOF'
Usage:
  bash code/ops/REPAIR_PUBLIC_EDGE_ON_VPS.sh
  sudo bash code/ops/REPAIR_PUBLIC_EDGE_ON_VPS.sh --apply

Inspect-only mode prints the proposed public-edge guard diff. Apply mode
requires root, creates a rollback copy, runs nginx -t, reloads nginx, verifies
the explicit static manifest, confirms bounded proxy routes are not blocked by
the edge, and verifies representative private routes are 404.
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
    [[ -f "$LUMENCORE_NGINX_CONFIG" ]] || return 1
    printf '%s\n' "$LUMENCORE_NGINX_CONFIG"
    return 0
  fi
  if [[ -L /etc/nginx/sites-enabled/lumatrader ]]; then
    readlink -f /etc/nginx/sites-enabled/lumatrader
    return 0
  fi
  local found=()
  local candidate
  for candidate in \
    /etc/nginx/sites-available/lumatrader \
    /etc/nginx/conf.d/lumatrader.conf; do
    [[ -f "$candidate" ]] && found+=("$candidate")
  done
  [[ "${#found[@]}" -eq 1 ]] || return 1
  printf '%s\n' "${found[0]}"
}

CONFIG="$(detect_config)" || {
  echo "ERROR: identify exactly one nginx config or set LUMENCORE_NGINX_CONFIG" >&2
  exit 3
}
[[ -f "$REPAIR_TOOL" ]] || {
  echo "ERROR: repair tool not found" >&2
  exit 4
}
command -v python3 >/dev/null 2>&1 || {
  echo "ERROR: python3 is required" >&2
  exit 5
}

if [[ "$APPLY" != true ]]; then
  python3 "$REPAIR_TOOL" --config "$CONFIG" --show-diff
  exit $?
fi

[[ "${EUID}" -eq 0 ]] || {
  echo "ERROR: --apply must run as root" >&2
  exit 6
}
for required in nginx systemctl curl; do
  command -v "$required" >/dev/null 2>&1 || {
    echo "ERROR: $required is required" >&2
    exit 7
  }
done

STAMP="$(date -u +%Y%m%dT%H%M%SZ)"
ROLLBACK="${CONFIG}.deploy-rollback.${STAMP}"
cp -a -- "$CONFIG" "$ROLLBACK"

rollback() {
  local rc="${1:-1}"
  if [[ "$REPAIR_COMPLETE" != true && -f "$ROLLBACK" ]]; then
    cp -a -- "$ROLLBACK" "$CONFIG"
    if nginx -t; then systemctl reload nginx || true; fi
  fi
  exit "$rc"
}

trap 'rc=$?; echo "ERROR: public-edge repair stopped on line $LINENO" >&2; rollback "$rc"' ERR
trap 'rollback 130' INT TERM

python3 "$REPAIR_TOOL" --config "$CONFIG" --show-diff --apply
nginx -t
systemctl reload nginx

LOCAL_BASE=(--resolve "${DOMAIN}:443:127.0.0.1")
request_status() {
  local method="$1"
  local path="$2"
  shift 2
  curl -sS --max-time 15 -X "$method" -o /dev/null -w '%{http_code}' \
    "$@" "https://${DOMAIN}${path}?edge=${STAMP}" || true
}

edge_allows_backend_route() {
  local method="$1"
  local path="$2"
  shift 2
  local observed
  observed="$(request_status "$method" "$path" "$@")"
  [[ "$observed" == 200 || "$observed" == 502 ]]
}

for curl_scope in local public; do
  extra=()
  [[ "$curl_scope" == local ]] && extra=("${LOCAL_BASE[@]}")
  [[ "$(request_status GET / "${extra[@]}")" == 200 ]]
  [[ "$(request_status GET /operator_home.html "${extra[@]}")" == 200 ]]
  [[ "$(request_status GET /assets/lumencore.css "${extra[@]}")" == 200 ]]
  [[ "$(request_status GET /assets/luma_command_fabric.css "${extra[@]}")" == 200 ]]
  [[ "$(request_status GET /proof_to_pilot.html "${extra[@]}")" == 302 ]]
  edge_allows_backend_route GET /health "${extra[@]}"
  edge_allows_backend_route GET /api/master/booth-brief "${extra[@]}"
  edge_allows_backend_route GET /evidence/ "${extra[@]}"
  [[ "$(request_status POST /api/master/booth-brief "${extra[@]}")" == 404 ]]
  for private_path in \
    /api/master/approval-queue \
    /auth/session \
    /dashboard \
    /dashboard/ \
    /quant_lab.html \
    /evidence/index.html \
    /evidence/private.json \
    /ws/live \
    /proof/ \
    /out/ \
    /trading \
    /unknown.html; do
    [[ "$(request_status GET "$private_path" "${extra[@]}")" == 404 ]]
  done
done

REPAIR_COMPLETE=true
trap - ERR INT TERM
echo "OK: public edge exposes only the explicit read-only manifest."
