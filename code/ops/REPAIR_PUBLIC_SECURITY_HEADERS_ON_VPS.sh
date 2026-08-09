#!/usr/bin/env bash
# Atomic public-security-header repair for https://lumen-core.ai.
# Inspect-only by default. --apply is the only write path.
set -Eeuo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
REPAIR_TOOL="${SCRIPT_DIR}/repair_public_security_headers.py"
DOMAIN="${LUMENCORE_DOMAIN:-lumen-core.ai}"
APPLY=false
CONFIG=""
ROLLBACK=""
REPAIR_COMPLETE=false

usage() {
  cat <<'EOF'
Usage:
  bash code/ops/REPAIR_PUBLIC_SECURITY_HEADERS_ON_VPS.sh
  sudo bash code/ops/REPAIR_PUBLIC_SECURITY_HEADERS_ON_VPS.sh --apply

Optional environment:
  LUMENCORE_NGINX_CONFIG=/path/to/active/lumatrader.conf
  LUMENCORE_DOMAIN=lumen-core.ai

Inspect-only mode prints the exact proposed diff. Apply mode requires root,
creates a rollback copy, validates Nginx, reloads only after validation, and
requires the local and public review routes to return the bounded policy.
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
      echo "ERROR: configured Nginx file does not exist: $LUMENCORE_NGINX_CONFIG" >&2
      return 1
    }
    readlink -f -- "$LUMENCORE_NGINX_CONFIG"
    return 0
  fi

  local enabled="/etc/nginx/sites-enabled/lumatrader"
  if [[ -L "$enabled" ]]; then
    local target
    target="$(readlink -f -- "$enabled")"
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
    [[ -f "$candidate" ]] && found+=("$(readlink -f -- "$candidate")")
  done
  mapfile -t found < <(printf '%s\n' "${found[@]}" | sort -u)
  if [[ "${#found[@]}" -eq 1 ]]; then
    printf '%s\n' "${found[0]}"
    return 0
  fi
  if [[ "${#found[@]}" -eq 0 ]]; then
    echo "ERROR: no lumatrader Nginx config found" >&2
  else
    echo "ERROR: multiple Nginx configs found; set LUMENCORE_NGINX_CONFIG" >&2
    printf '  %s\n' "${found[@]}" >&2
  fi
  return 1
}

header_value() {
  local name="$1"
  local file="$2"
  awk -v wanted="$name" '
    BEGIN { IGNORECASE=1 }
    {
      line=$0
      sub(/\r$/, "", line)
      split(line, pair, ":")
      if (tolower(pair[1]) == tolower(wanted)) {
        sub(/^[^:]*:[[:space:]]*/, "", line)
        print line
        exit
      }
    }
  ' "$file"
}

verify_policy() {
  local label="$1"
  local url="$2"
  local resolve_arg="${3:-}"
  local headers body status
  headers="$(mktemp)"
  body="$(mktemp)"
  VERIFY_TEMPS+=("$headers" "$body")
  local curl_args=(
    --silent --show-error --max-time 20 --noproxy '*'
    --dump-header "$headers" --output "$body"
    --write-out '%{http_code}'
  )
  if [[ -n "$resolve_arg" ]]; then
    curl_args+=(--resolve "$resolve_arg")
  fi
  status="$(curl "${curl_args[@]}" "$url")"
  [[ "$status" == "200" ]] || {
    echo "ERROR: ${label} returned HTTP ${status:-000}" >&2
    return 1
  }

  local xcto xfo referrer hsts csp permissions
  xcto="$(header_value X-Content-Type-Options "$headers")"
  xfo="$(header_value X-Frame-Options "$headers")"
  referrer="$(header_value Referrer-Policy "$headers")"
  hsts="$(header_value Strict-Transport-Security "$headers")"
  csp="$(header_value Content-Security-Policy "$headers")"
  permissions="$(header_value Permissions-Policy "$headers")"
  if [[ "$xcto" != "nosniff" \
     || "$xfo" != "DENY" \
     || "$referrer" != "strict-origin-when-cross-origin" \
     || "$hsts" != "max-age=31536000" \
     || "$csp" != *"default-src 'self'"* \
     || "$csp" != *"frame-ancestors 'none'"* \
     || "$csp" != *"object-src 'none'"* \
     || "$permissions" != *"camera=()"* \
     || "$permissions" != *"payment=()"* ]]; then
    echo "WAIT: ${label} has not converged on the bounded policy" >&2
    printf '  X-Content-Type-Options=%q\n' "$xcto" >&2
    printf '  X-Frame-Options=%q\n' "$xfo" >&2
    printf '  Referrer-Policy=%q\n' "$referrer" >&2
    printf '  Strict-Transport-Security=%q\n' "$hsts" >&2
    printf '  Content-Security-Policy=%q\n' "$csp" >&2
    printf '  Permissions-Policy=%q\n' "$permissions" >&2
    return 1
  fi
  echo "OK: ${label} HTTP 200 with bounded public security policy"
}

verify_with_retry() {
  local label="$1"
  local url="$2"
  local resolve_arg="$3"
  local attempts="$4"
  local delay="$5"
  local attempt
  for attempt in $(seq 1 "$attempts"); do
    if verify_policy "${label} attempt ${attempt}/${attempts}" "${url}-${attempt}" "$resolve_arg"; then
      return 0
    fi
    if [[ "$attempt" -lt "$attempts" ]]; then
      sleep "$delay"
    fi
  done
  echo "ERROR: ${label} did not converge after ${attempts} attempts" >&2
  return 1
}

CONFIG="$(detect_config)"
[[ -f "$REPAIR_TOOL" ]] || { echo "ERROR: repair tool not found: $REPAIR_TOOL" >&2; exit 3; }
command -v python3 >/dev/null 2>&1 || { echo "ERROR: python3 is required" >&2; exit 4; }

echo "Nginx config: $CONFIG"
if [[ "$APPLY" != true ]]; then
  python3 "$REPAIR_TOOL" --config "$CONFIG" --show-diff
  exit $?
fi

[[ "${EUID}" -eq 0 ]] || { echo "ERROR: --apply must run as root" >&2; exit 5; }
for command_name in nginx systemctl curl awk mktemp readlink sort; do
  command -v "$command_name" >/dev/null 2>&1 || {
    echo "ERROR: ${command_name} is required" >&2
    exit 6
  }
done

STAMP="$(date -u +%Y%m%dT%H%M%SZ)"
ROLLBACK="${CONFIG}.deploy-rollback.${STAMP}"
cp -a -- "$CONFIG" "$ROLLBACK"
echo "Rollback copy: $ROLLBACK"

rollback() {
  local rc="${1:-1}"
  if [[ "$REPAIR_COMPLETE" != true && -f "$ROLLBACK" ]]; then
    echo "Rolling back Nginx configuration..." >&2
    cp -a -- "$ROLLBACK" "$CONFIG"
    if nginx -t; then systemctl reload nginx || true; fi
  fi
  exit "$rc"
}

VERIFY_TEMPS=()
cleanup() {
  if [[ "${#VERIFY_TEMPS[@]}" -gt 0 ]]; then
    rm -f -- "${VERIFY_TEMPS[@]}"
  fi
}
trap 'rc=$?; cleanup; echo "ERROR: security-header repair stopped on line $LINENO" >&2; rollback "$rc"' ERR
trap 'cleanup; echo "Repair interrupted." >&2; rollback 130' INT TERM

python3 "$REPAIR_TOOL" --config "$CONFIG" --show-diff --apply
nginx -t
systemctl reload nginx
echo "Nginx reloaded after a successful configuration test."

ROUTES=(
  "/"
  "/proof_to_pilot.html"
  "/external_review.html"
  "/evidence/"
  "/build_week/prooflock_console/"
  "/health"
  "/api/public/status"
)
for route in "${ROUTES[@]}"; do
  verify_with_retry \
    "local ${route}" \
    "https://${DOMAIN}${route}?security=${STAMP}" \
    "${DOMAIN}:443:127.0.0.1" \
    10 \
    1
done
for route in "${ROUTES[@]}"; do
  verify_with_retry \
    "public ${route}" \
    "https://${DOMAIN}${route}?security=${STAMP}" \
    "" \
    10 \
    2
done

REPAIR_COMPLETE=true
trap - ERR INT TERM
cleanup
echo "OK: all canonical public review routes preserve the bounded security policy."
