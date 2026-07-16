#!/usr/bin/env bash
# Bounded production repair for https://lumen-core.ai/evidence/
# Default behavior is inspect-only. Pass --apply to write, validate, and reload.
set -Eeuo pipefail

CONFIG="${LUMENCORE_NGINX_CONFIG:-/etc/nginx/conf.d/lumatrader.conf}"
DOCUMENT_ROOT="${LUMENCORE_DASHBOARD_ROOT:-/opt/lumencore/dashboard}"
SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
REPAIR_TOOL="${SCRIPT_DIR}/repair_evidence_route.py"
APPLY=false

usage() {
  cat <<'EOF'
Usage:
  bash code/ops/REPAIR_EVIDENCE_ROUTE_ON_VPS.sh
  sudo bash code/ops/REPAIR_EVIDENCE_ROUTE_ON_VPS.sh --apply

Environment overrides:
  LUMENCORE_NGINX_CONFIG=/path/to/lumatrader.conf
  LUMENCORE_DASHBOARD_ROOT=/opt/lumencore/dashboard

The default run is read-only and prints the proposed diff. --apply requires root,
creates backups, runs nginx -t, reloads nginx only after validation, and reports
the external HTTP status without changing any application service or credentials.
EOF
}

for arg in "$@"; do
  case "$arg" in
    --apply) APPLY=true ;;
    -h|--help) usage; exit 0 ;;
    *) echo "ERROR: unknown argument: $arg" >&2; usage >&2; exit 2 ;;
  esac
done

if [[ ! -f "$REPAIR_TOOL" ]]; then
  echo "ERROR: repair tool not found: $REPAIR_TOOL" >&2
  exit 3
fi
if [[ ! -f "$CONFIG" ]]; then
  echo "ERROR: nginx config not found: $CONFIG" >&2
  exit 4
fi
if [[ ! -f "$DOCUMENT_ROOT/evidence/index.html" ]]; then
  echo "ERROR: evidence page not found: $DOCUMENT_ROOT/evidence/index.html" >&2
  exit 5
fi

PYTHON_BIN="${PYTHON_BIN:-python3}"
command -v "$PYTHON_BIN" >/dev/null 2>&1 || {
  echo "ERROR: python3 is required" >&2
  exit 6
}

if [[ "$APPLY" != true ]]; then
  "$PYTHON_BIN" "$REPAIR_TOOL" \
    --config "$CONFIG" \
    --document-root "$DOCUMENT_ROOT" \
    --show-diff
  exit $?
fi

if [[ "${EUID}" -ne 0 ]]; then
  echo "ERROR: --apply must run as root so nginx can be validated and reloaded" >&2
  exit 7
fi

command -v nginx >/dev/null 2>&1 || {
  echo "ERROR: nginx command not found" >&2
  exit 8
}
command -v systemctl >/dev/null 2>&1 || {
  echo "ERROR: systemctl command not found" >&2
  exit 9
}

STAMP="$(date -u +%Y%m%dT%H%M%SZ)"
ROLLBACK="${CONFIG}.pre-evidence-repair.${STAMP}"
cp -a -- "$CONFIG" "$ROLLBACK"
echo "Rollback copy: $ROLLBACK"

rollback_config() {
  echo "Validation failed; restoring $ROLLBACK" >&2
  cp -a -- "$ROLLBACK" "$CONFIG"
  nginx -t || true
}
trap 'echo "ERROR: evidence route repair stopped on line $LINENO" >&2' ERR

"$PYTHON_BIN" "$REPAIR_TOOL" \
  --config "$CONFIG" \
  --document-root "$DOCUMENT_ROOT" \
  --show-diff \
  --apply

if ! nginx -t; then
  rollback_config
  exit 10
fi

systemctl reload nginx

echo "Nginx reloaded after a successful configuration test."
LOCAL_STATUS="$(curl -sS --max-time 10 -o /dev/null -w '%{http_code}' \
  -H 'Host: lumen-core.ai' https://127.0.0.1/evidence/ -k 2>/dev/null || true)"
PUBLIC_STATUS="$(curl -sS --max-time 15 -o /dev/null -w '%{http_code}' \
  https://lumen-core.ai/evidence/ 2>/dev/null || true)"

echo "Local HTTPS route status: ${LOCAL_STATUS:-000}"
echo "Public HTTPS route status: ${PUBLIC_STATUS:-000}"

if [[ "$LOCAL_STATUS" != "200" ]]; then
  echo "WARNING: nginx accepted the configuration, but the local /evidence/ route is not yet HTTP 200." >&2
  echo "Inspect: ls -la '$DOCUMENT_ROOT/evidence/' and tail -n 100 /var/log/nginx/lumatrader_error.log" >&2
  exit 11
fi

if [[ "$PUBLIC_STATUS" != "200" ]]; then
  echo "WARNING: local route is healthy, but the public check is not yet HTTP 200; inspect DNS/CDN propagation." >&2
  exit 12
fi

echo "OK: /evidence/ is serving the static evidence page locally and publicly."
