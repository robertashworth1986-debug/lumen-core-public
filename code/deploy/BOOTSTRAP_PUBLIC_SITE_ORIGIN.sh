#!/usr/bin/env bash
set -Eeuo pipefail

# Provider-neutral bootstrap for one fresh Ubuntu public origin.  It is
# noninteractive and suitable for cloud-init shell user data when the reviewed
# nginx configuration is written to the instance first.  It does not create or
# buy infrastructure, change DNS, request a certificate, clone Git, or install
# any gateway/trading runtime.

umask 027

readonly REQUIRED_APPROVAL="BOOTSTRAP_PUBLIC_SITE_CANDIDATE"
readonly DASHBOARD_ROOT="/opt/lumencore/dashboard"
readonly ROLLBACK_ROOT="/opt/lumencore/rollbacks"
readonly BOOTSTRAP_ROLLBACK_ROOT="$ROLLBACK_ROOT/origin-bootstrap"
readonly PUBLIC_RELEASE_ROLLBACK_ROOT="$ROLLBACK_ROOT/public-site"
readonly RECEIPT_ROOT="/opt/lumencore/receipts/origin-bootstrap"
readonly ACME_WEBROOT="/var/lib/letsencrypt"
readonly CERTIFICATE_ROOT="/etc/letsencrypt/live/lumen-core.ai"

approval=""
nginx_config=""
nginx_config_sha256=""
source_commit=""

die() {
  printf 'ERROR: %s\n' "$*" >&2
  return 1
}

usage() {
  cat >&2 <<'EOF'
Usage: BOOTSTRAP_PUBLIC_SITE_ORIGIN.sh \
  --approval BOOTSTRAP_PUBLIC_SITE_CANDIDATE \
  --nginx-config PATH \
  --nginx-config-sha256 SHA256 \
  --source-commit FULL_SHA

The script installs an HTTP-only health/ACME configuration until the reviewed
certificate files exist.  It never issues a certificate.  Re-run it after the
separately authorized certificate is installed to activate canonical HTTPS.
EOF
  return 2
}

while (($#)); do
  case "$1" in
    --approval)
      (($# >= 2)) || usage
      approval="$2"
      shift 2
      ;;
    --nginx-config)
      (($# >= 2)) || usage
      nginx_config="$2"
      shift 2
      ;;
    --nginx-config-sha256)
      (($# >= 2)) || usage
      nginx_config_sha256="$2"
      shift 2
      ;;
    --source-commit)
      (($# >= 2)) || usage
      source_commit="$2"
      shift 2
      ;;
    *)
      usage
      ;;
  esac
done

[[ "$approval" == "$REQUIRED_APPROVAL" ]] || die "explicit candidate bootstrap approval is required"
[[ "$EUID" -eq 0 ]] || die "candidate bootstrap must run as root"
[[ "$source_commit" =~ ^[0-9a-f]{40}$ ]] || die "source commit must be a full lowercase SHA-1"
[[ "$nginx_config_sha256" =~ ^[0-9a-f]{64}$ ]] || die "nginx config SHA-256 is invalid"
[[ "$nginx_config" == /* ]] || die "nginx config path must be absolute"
[[ -f "$nginx_config" && ! -L "$nginx_config" ]] || die "nginx config must be a regular non-symlink file"

for command_name in sha256sum stat install date mktemp realpath; do
  command -v "$command_name" >/dev/null 2>&1 || die "missing bootstrap prerequisite: $command_name"
done

actual_config_sha256="$(sha256sum -- "$nginx_config")"
actual_config_sha256="${actual_config_sha256%% *}"
[[ "$actual_config_sha256" == "$nginx_config_sha256" ]] || die "nginx config does not match the reviewed SHA-256"

# Pin the reviewed bytes in a root-owned file before any long-running package
# operation.  The SSH account must not be able to swap the source after review.
reviewed_config_copy="$(mktemp /tmp/lumencore-reviewed-origin.XXXXXXXX.conf)"
policy_rc_created=0
apt_log=""
trap 'if [[ "$policy_rc_created" -eq 1 ]]; then rm -f -- /usr/sbin/policy-rc.d; fi; if [[ -n "$apt_log" ]]; then rm -f -- "$apt_log"; fi; rm -f -- "$reviewed_config_copy"' EXIT
install -o root -g root -m 0600 -- "$nginx_config" "$reviewed_config_copy"
reviewed_copy_sha256="$(sha256sum -- "$reviewed_config_copy")"
reviewed_copy_sha256="${reviewed_copy_sha256%% *}"
[[ "$reviewed_copy_sha256" == "$nginx_config_sha256" ]] || die "root-owned nginx config copy failed verification"

# Prevent the package post-install hook from exposing Ubuntu's default Nginx
# page before the bounded hold configuration is installed and tested.
if [[ ! -e /usr/sbin/policy-rc.d && ! -L /usr/sbin/policy-rc.d ]]; then
  temporary_policy="$(mktemp /tmp/lumencore-policy-rc.XXXXXXXX)"
  cat > "$temporary_policy" <<'POLICY'
#!/bin/sh
exit 101
POLICY
  install -o root -g root -m 0755 -- "$temporary_policy" /usr/sbin/policy-rc.d
  rm -f -- "$temporary_policy"
  policy_rc_created=1
fi

[[ -r /etc/os-release ]] || die "operating-system identity is unavailable"
# shellcheck disable=SC1091
. /etc/os-release
[[ "${ID:-}" == "ubuntu" ]] || die "candidate origin must run Ubuntu"
case "${VERSION_ID:-}" in
  22.04|24.04) ;;
  *) die "candidate origin requires Ubuntu 22.04 or 24.04 LTS" ;;
esac

export DEBIAN_FRONTEND=noninteractive
apt_log="$(mktemp /tmp/lumencore-origin-apt.XXXXXXXX.log)"
if ! apt-get update -q >"$apt_log" 2>&1; then
  tail -n 80 "$apt_log" >&2 || true
  die "Ubuntu package-index refresh failed"
fi
if ! apt-get install -y --no-install-recommends \
  ca-certificates \
  certbot \
  curl \
  iproute2 \
  nginx \
  openssl \
  python3 \
  python3-certbot-nginx \
  unattended-upgrades >>"$apt_log" 2>&1; then
  tail -n 120 "$apt_log" >&2 || true
  die "bounded origin package installation failed"
fi
rm -f -- "$apt_log"
apt_log=""
if [[ "$policy_rc_created" -eq 1 ]]; then
  rm -f -- /usr/sbin/policy-rc.d
  policy_rc_created=0
fi

for command_name in curl nginx openssl python3 ss systemctl timeout; do
  command -v "$command_name" >/dev/null 2>&1 || die "missing installed prerequisite: $command_name"
done

install -d -o root -g root -m 0755 -- \
  /opt/lumencore \
  "$DASHBOARD_ROOT" \
  "$ACME_WEBROOT" \
  "$ACME_WEBROOT/.well-known" \
  "$ACME_WEBROOT/.well-known/acme-challenge"
install -d -o root -g root -m 0750 -- \
  "$ROLLBACK_ROOT" \
  "$BOOTSTRAP_ROLLBACK_ROOT" \
  "$PUBLIC_RELEASE_ROLLBACK_ROOT" \
  /opt/lumencore/receipts \
  "$RECEIPT_ROOT"

timestamp="$(date -u +%Y%m%dT%H%M%SZ)"
rollback_dir="$BOOTSTRAP_ROLLBACK_ROOT/${timestamp}-${source_commit:0:12}"
[[ ! -e "$rollback_dir" ]] || die "timestamped origin-bootstrap rollback directory already exists"
install -d -o root -g root -m 0700 -- "$rollback_dir"

if [[ -d /etc/nginx/sites-available && -d /etc/nginx/sites-enabled ]]; then
  nginx_target="/etc/nginx/sites-available/lumencore-public-origin"
  nginx_enabled="/etc/nginx/sites-enabled/lumencore-public-origin"
  nginx_default="/etc/nginx/sites-enabled/default"
else
  nginx_target="/etc/nginx/conf.d/lumencore-public-origin.conf"
  nginx_enabled=""
  nginx_default="/etc/nginx/conf.d/default.conf"
fi

[[ ! -L "$nginx_target" ]] || die "nginx target may not be a symbolic link"
if [[ -n "$nginx_enabled" && -e "$nginx_enabled" && ! -L "$nginx_enabled" ]]; then
  die "nginx enabled target must be absent or a symbolic link"
fi

target_existed=0
enabled_existed=0
default_existed=0
if [[ -e "$nginx_target" ]]; then
  [[ -f "$nginx_target" ]] || die "nginx target has an unsupported type"
  cp -a -- "$nginx_target" "$rollback_dir/nginx-target"
  target_existed=1
fi
if [[ -n "$nginx_enabled" && -L "$nginx_enabled" ]]; then
  cp -a -- "$nginx_enabled" "$rollback_dir/nginx-enabled"
  enabled_existed=1
fi
if [[ -e "$nginx_default" || -L "$nginx_default" ]]; then
  cp -a -- "$nginx_default" "$rollback_dir/nginx-default"
  default_existed=1
fi

temporary_config="$(mktemp /tmp/lumencore-public-origin.XXXXXXXX.conf)"
configuration_started=0

cleanup() {
  if [[ "$policy_rc_created" -eq 1 ]]; then
    rm -f -- /usr/sbin/policy-rc.d
    policy_rc_created=0
  fi
  if [[ -n "$reviewed_config_copy" && "$reviewed_config_copy" == /tmp/lumencore-reviewed-origin.*.conf ]]; then
    rm -f -- "$reviewed_config_copy"
  fi
  if [[ -n "$temporary_config" && "$temporary_config" == /tmp/lumencore-public-origin.*.conf ]]; then
    rm -f -- "$temporary_config"
  fi
}

rollback_on_error() {
  local exit_code=$?
  trap - ERR
  set +e
  if [[ "$configuration_started" -eq 1 ]]; then
    rm -f -- "$nginx_target"
    if [[ "$target_existed" -eq 1 ]]; then
      cp -a -- "$rollback_dir/nginx-target" "$nginx_target"
    fi
    if [[ -n "$nginx_enabled" ]]; then
      rm -f -- "$nginx_enabled"
      if [[ "$enabled_existed" -eq 1 ]]; then
        cp -a -- "$rollback_dir/nginx-enabled" "$nginx_enabled"
      fi
    fi
    rm -f -- "$nginx_default"
    if [[ "$default_existed" -eq 1 ]]; then
      cp -a -- "$rollback_dir/nginx-default" "$nginx_default"
    fi
    if nginx -t >/dev/null 2>&1; then
      systemctl reload nginx >/dev/null 2>&1 || true
      printf 'ORIGIN_BOOTSTRAP_ROLLBACK_APPLIED=%s\n' "$rollback_dir" >&2
    else
      printf 'ORIGIN_BOOTSTRAP_ROLLBACK_REQUIRES_REVIEW=%s\n' "$rollback_dir" >&2
    fi
  fi
  cleanup
  exit "$exit_code"
}

trap cleanup EXIT
trap rollback_on_error ERR

tls_ready=true
for certificate_link in \
  "$CERTIFICATE_ROOT/fullchain.pem" \
  "$CERTIFICATE_ROOT/privkey.pem"; do
  if [[ ! -f "$certificate_link" || ! -r "$certificate_link" ]]; then
    tls_ready=false
    continue
  fi
  certificate_target="$(realpath -e -- "$certificate_link" 2>/dev/null || true)"
  if [[ "$certificate_target" != /etc/letsencrypt/archive/lumen-core.ai/* ]]; then
    tls_ready=false
  fi
done
for required_tls_support in \
  /etc/letsencrypt/options-ssl-nginx.conf \
  /etc/letsencrypt/ssl-dhparams.pem; do
  if [[ ! -f "$required_tls_support" || -L "$required_tls_support" ]]; then
    tls_ready=false
  fi
done

if [[ "$tls_ready" == "true" ]]; then
  install -o root -g root -m 0644 -- "$reviewed_config_copy" "$temporary_config"
  installed_mode="canonical_https"
else
  cat > "$temporary_config" <<'NGINX'
# Safe first-boot listener.  It exposes only ACME and a bounded health marker.
server {
    listen 80 default_server;
    listen [::]:80 default_server;
    server_name lumen-core.ai www.lumen-core.ai app.lumen-core.ai research.lumen-core.ai;
    server_tokens off;

    location ^~ /.well-known/acme-challenge/ {
        root /var/lib/letsencrypt;
        default_type text/plain;
        limit_except GET HEAD { deny all; }
        try_files $uri =404;
    }

    location = /nginx-health {
        default_type application/json;
        access_log off;
        limit_except GET HEAD { deny all; }
        return 200 '{"status":"ok","platform":"nginx","surface":"bounded-public-origin","tls":"pending"}';
    }

    location / {
        add_header Retry-After "300" always;
        limit_except GET HEAD { deny all; }
        return 503;
    }
}
NGINX
  chmod 0644 "$temporary_config"
  installed_mode="http_acme_hold"
fi

configuration_started=1
install -o root -g root -m 0644 -- "$temporary_config" "$nginx_target"
if [[ -n "$nginx_enabled" ]]; then
  rm -f -- "$nginx_enabled"
  ln -s -- "$nginx_target" "$nginx_enabled"
fi
rm -f -- "$nginx_default"

nginx -t
if systemctl is-active --quiet nginx; then
  systemctl reload nginx
else
  systemctl enable --now nginx
fi
systemctl is-active --quiet nginx

if systemctl list-unit-files --type=timer --no-legend 2>/dev/null | grep -q '^certbot\.timer'; then
  systemctl enable --now certbot.timer
fi
if systemctl list-unit-files --type=service --no-legend 2>/dev/null | grep -q '^unattended-upgrades\.service'; then
  systemctl enable --now unattended-upgrades.service || true
fi

health_body="$(curl --fail --silent --show-error \
  --connect-timeout 5 --max-time 15 \
  -H 'Host: lumen-core.ai' \
  http://127.0.0.1/nginx-health)"
python3 - "$health_body" <<'PY'
import json
import sys

payload = json.loads(sys.argv[1])
if payload.get("status") != "ok" or payload.get("surface") != "bounded-public-origin":
    raise SystemExit("ERROR: bounded nginx health contract is invalid")
PY

if [[ "$tls_ready" == "true" ]]; then
  curl --fail --silent --show-error \
    --noproxy lumen-core.ai \
    --resolve lumen-core.ai:443:127.0.0.1 \
    --connect-timeout 5 --max-time 15 \
    https://lumen-core.ai/nginx-health >/dev/null
  for certificate_name in lumen-core.ai www.lumen-core.ai app.lumen-core.ai research.lumen-core.ai; do
    timeout 15 openssl s_client \
      -connect 127.0.0.1:443 \
      -servername "$certificate_name" \
      -verify_hostname "$certificate_name" \
      -verify_return_error \
      -brief </dev/null >/dev/null
  done
fi

receipt="$RECEIPT_ROOT/${timestamp}-${source_commit:0:12}.json"
python3 - \
  "$receipt" \
  "$timestamp" \
  "$source_commit" \
  "$nginx_config_sha256" \
  "$nginx_target" \
  "$rollback_dir" \
  "$installed_mode" \
  "$tls_ready" \
  "${VERSION_ID}" <<'PY'
from datetime import datetime, timezone
import json
from pathlib import Path
import sys

(
    receipt_path,
    timestamp,
    source_commit,
    config_sha256,
    nginx_target,
    rollback_dir,
    installed_mode,
    tls_ready,
    ubuntu_version,
) = sys.argv[1:]
payload = {
    "checked_at_utc": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
    "installed_mode": installed_mode,
    "nginx_config_sha256": config_sha256,
    "nginx_target": nginx_target,
    "rollback_directory": rollback_dir,
    "schema": "lumencore.public_origin_bootstrap_receipt.v1",
    "source_commit": source_commit,
    "timestamp": timestamp,
    "tls_ready": tls_ready == "true",
    "ubuntu_version": ubuntu_version,
}
rendered = json.dumps(payload, indent=2, sort_keys=True, ensure_ascii=True) + "\n"
Path(receipt_path).write_text(rendered, encoding="utf-8", newline="\n")
print(rendered, end="")
PY
chmod 0640 "$receipt"

configuration_started=0
printf 'PUBLIC_ORIGIN_BOOTSTRAP_OK\n'
printf 'PUBLIC_ORIGIN_TLS_READY=%s\n' "$tls_ready"
printf 'PUBLIC_ORIGIN_BOOTSTRAP_RECEIPT=%s\n' "$receipt"
printf 'PUBLIC_ORIGIN_BOOTSTRAP_ROLLBACK=%s\n' "$rollback_dir"
