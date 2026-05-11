#!/usr/bin/env bash
set -euo pipefail

usage() {
  cat <<'EOF'
Usage:
  sudo ./bootstrap_vps_lumatrader.sh \
    --repo-url <git_repo_url> \
    --domain <your_domain> \
    [--branch <git_branch>] \
    [--target-dir </opt/lumatrader>] \
    [--service-user <linux_user>] \
    [--strict]

Options:
  --repo-url         Git repository URL to clone/update (required)
  --domain           Public domain for nginx/certbot wiring (required)
  --branch           Git branch to deploy (default: main)
  --target-dir       Local checkout directory (default: /opt/lumatrader)
  --service-user     Service account for systemd units (default: sudo user)
  --strict           Enables strict premium/coherence gates
  --strict-premium   Override strict premium gate (0 or 1)
  --strict-coherence Override strict coherence gate (0 or 1)
  --help             Show this help
EOF
}

if [[ "${EUID:-$(id -u)}" -ne 0 ]]; then
  echo "ERROR: run as root (use sudo)." >&2
  exit 1
fi

REPO_URL=""
DOMAIN=""
BRANCH="main"
TARGET_DIR="/opt/lumatrader"
SERVICE_USER="${SUDO_USER:-$(id -un)}"
STRICT_PREMIUM="0"
STRICT_COHERENCE="0"

while [[ $# -gt 0 ]]; do
  case "$1" in
    --repo-url)
      REPO_URL="${2:-}"
      shift 2
      ;;
    --domain)
      DOMAIN="${2:-}"
      shift 2
      ;;
    --branch)
      BRANCH="${2:-}"
      shift 2
      ;;
    --target-dir)
      TARGET_DIR="${2:-}"
      shift 2
      ;;
    --service-user)
      SERVICE_USER="${2:-}"
      shift 2
      ;;
    --strict)
      STRICT_PREMIUM="1"
      STRICT_COHERENCE="1"
      shift
      ;;
    --strict-premium)
      STRICT_PREMIUM="${2:-0}"
      shift 2
      ;;
    --strict-coherence)
      STRICT_COHERENCE="${2:-0}"
      shift 2
      ;;
    --help|-h)
      usage
      exit 0
      ;;
    *)
      echo "ERROR: unknown argument $1" >&2
      usage
      exit 2
      ;;
  esac
done

if [[ -z "$REPO_URL" || -z "$DOMAIN" ]]; then
  echo "ERROR: --repo-url and --domain are required." >&2
  usage
  exit 2
fi

install_packages() {
  if command -v apt-get >/dev/null 2>&1; then
    apt-get update -y
    apt-get install -y git curl ca-certificates
    return
  fi
  if command -v dnf >/dev/null 2>&1; then
    dnf install -y git curl ca-certificates
    return
  fi
  if command -v yum >/dev/null 2>&1; then
    yum install -y git curl ca-certificates
    return
  fi
  echo "ERROR: no supported package manager found (apt-get/dnf/yum)." >&2
  exit 3
}

echo "==> Installing bootstrap dependencies"
install_packages

echo "==> Preparing checkout at $TARGET_DIR"
mkdir -p "$(dirname "$TARGET_DIR")"

if [[ -d "$TARGET_DIR/.git" ]]; then
  echo "==> Updating existing repository"
  git -C "$TARGET_DIR" fetch --all --prune
  git -C "$TARGET_DIR" checkout "$BRANCH"
  git -C "$TARGET_DIR" pull --ff-only origin "$BRANCH"
else
  echo "==> Cloning repository"
  git clone --branch "$BRANCH" "$REPO_URL" "$TARGET_DIR"
fi

DEPLOY_SCRIPT="$TARGET_DIR/INSTITUTIONAL_STACK_V2/code/deploy/deploy_vps.sh"
if [[ ! -f "$DEPLOY_SCRIPT" ]]; then
  echo "ERROR: deploy script not found at $DEPLOY_SCRIPT" >&2
  exit 4
fi

chmod +x "$DEPLOY_SCRIPT"

echo "==> Launching deploy script"
LUMA_DOMAIN="$DOMAIN" \
LUMA_SERVICE_USER="$SERVICE_USER" \
LUMA_STRICT_PREMIUM_STACK="$STRICT_PREMIUM" \
LUMA_STRICT_COHERENCE_BUILD="$STRICT_COHERENCE" \
"$DEPLOY_SCRIPT" "$DOMAIN"

echo
echo "==> Bootstrap complete"
echo "Domain: $DOMAIN"
echo "Checkout: $TARGET_DIR"
echo "Branch: $BRANCH"
echo
echo "Recommended checks:"
echo "  systemctl status luma-gateway luma-dashboard-refresh luma-node-red luma-nodered-flow-sync --no-pager"
echo "  curl -sS http://127.0.0.1/api/snapshot"
echo "  certbot --nginx -d $DOMAIN -d www.$DOMAIN"
