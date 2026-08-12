#!/bin/bash
# ============================================================
#  LumaTrader VPS Deployment Script
#  Run once on a fresh Ubuntu/Debian VPS to set up the portal
#
#  Usage:
#    chmod +x deploy_vps.sh
#    sudo ./deploy_vps.sh [domain]
# ============================================================
set -euo pipefail

DOMAIN="${LUMA_DOMAIN:-${1:-lumen-core.ai}}"
if [[ -n "${LUMA_SERVICE_USER:-}" ]]; then
   SERVICE_USER="$LUMA_SERVICE_USER"
elif id -u lumencore >/dev/null 2>&1; then
   SERVICE_USER="lumencore"
else
   SERVICE_USER="${SUDO_USER:-opc}"
fi
if ! id -u "$SERVICE_USER" >/dev/null 2>&1; then
   echo "ERROR: required non-root service account does not exist: $SERVICE_USER" >&2
   exit 8
fi
if [[ "$(id -u "$SERVICE_USER")" -eq 0 ]]; then
   echo "ERROR: refusing to run LumenCore application services as root" >&2
   exit 9
fi
SERVICE_GROUP="$(id -gn "$SERVICE_USER" 2>/dev/null || echo "$SERVICE_USER")"

WWW_ROOT="/var/www/lumatrader"
if [[ -d "/etc/nginx/sites-available" ]]; then
   NGINX_SITE="/etc/nginx/sites-available/lumatrader"
else
   NGINX_SITE="/etc/nginx/conf.d/lumatrader.conf"
fi

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
chmod +x "$SCRIPT_DIR/verify_dashboard_endpoints.sh"

ROOT_DIR="$(cd "$SCRIPT_DIR/../.." && pwd)"
SOURCE_CANDIDATES=(
   "$ROOT_DIR/dashboard"
   "/opt/lumatrader/dashboard"
   "/opt/lumatrader/INSTITUTIONAL_STACK_V2/dashboard"
)

DASHBOARD_SRC=""
for cand in "${SOURCE_CANDIDATES[@]}"; do
   if [[ -f "$cand/index.html" ]]; then
      DASHBOARD_SRC="$cand"
      break
   fi
done

if [[ -z "$DASHBOARD_SRC" ]]; then
   echo "ERROR: could not locate dashboard source directory." >&2
   echo "Checked:" >&2
   for cand in "${SOURCE_CANDIDATES[@]}"; do
      echo "  - $cand" >&2
   done
   exit 2
fi

echo "==> Using dashboard source: $DASHBOARD_SRC"

STACK_ROOT="$(cd "$DASHBOARD_SRC/.." && pwd)"
CODE_CANDIDATES=(
   "$STACK_ROOT/code"
   "/opt/lumatrader/code"
   "/opt/lumatrader/INSTITUTIONAL_STACK_V2/code"
)

CODE_DIR=""
for cand in "${CODE_CANDIDATES[@]}"; do
   if [[ -f "$cand/luma_experience_gateway.py" ]]; then
      CODE_DIR="$cand"
      break
   fi
done

if [[ -z "$CODE_DIR" ]]; then
   echo "ERROR: could not locate code directory with luma_experience_gateway.py" >&2
   exit 6
fi

PYTHON_CANDIDATES=(
   "$STACK_ROOT/venv3.11/bin/python"
   "$STACK_ROOT/.venv/bin/python"
   "/opt/lumatrader/venv3.11/bin/python"
   "/opt/lumatrader/.venv/bin/python"
   "$(command -v python3 || true)"
)

PYTHON_BIN=""
for py in "${PYTHON_CANDIDATES[@]}"; do
   if [[ -n "$py" && -x "$py" ]]; then
      PYTHON_BIN="$py"
      break
   fi
done

if [[ -z "$PYTHON_BIN" ]]; then
   echo "ERROR: no Python runtime found for gateway service." >&2
   exit 7
fi

echo "==> Using code dir: $CODE_DIR"
echo "==> Using Python: $PYTHON_BIN"
echo "==> Using domain: $DOMAIN"
echo "==> Service user: $SERVICE_USER:$SERVICE_GROUP"

REFRESH_SCRIPT="$CODE_DIR/dashboard_unified_refresh.py"
NODE_RED_FLOW_FILE="$CODE_DIR/node_red/flows_luma_bidirectional.json"
NODE_RED_ENSURE_SCRIPT="$CODE_DIR/ENSURE_NODERED_LUMA_FLOWS.py"
COHERENCE_BUILDER="$STACK_ROOT/code/build_gov_grade_coherence_report.py"
COMMAND_FABRIC_ENSURE="$CODE_DIR/ops/ensure_dashboard_command_fabric.py"
STRICT_COHERENCE_BUILD="${LUMA_STRICT_COHERENCE_BUILD:-0}"
STRICT_PREMIUM_STACK="${LUMA_STRICT_PREMIUM_STACK:-0}"

REQUIRED_PAGES=(
   "index.html"
   "operator_home.html"
   "mission_control.html"
   "grants.html"
   "quant_lab.html"
   "kraken_execution_dashboard.html"
   "forecast.html"
   "explain.html"
   "anomalies.html"
   "lab.html"
   "lumascout.html"
)

if [[ -f "$COMMAND_FABRIC_ENSURE" ]]; then
   echo "==> Ensuring canonical dashboard command fabric..."
   "$PYTHON_BIN" "$COMMAND_FABRIC_ENSURE" \
      --dashboard-root "$DASHBOARD_SRC" \
      --strict
fi

for page in "${REQUIRED_PAGES[@]}"; do
   if [[ ! -f "$DASHBOARD_SRC/$page" ]]; then
      echo "ERROR: required page missing from dashboard source: $page" >&2
      exit 3
   fi
done

echo "==> Verifying dashboard endpoint hygiene..."
"$SCRIPT_DIR/verify_dashboard_endpoints.sh" "$DASHBOARD_SRC"

if command -v apt-get >/dev/null 2>&1; then
   PKG_MGR="apt"
   PKG_UPDATE_CMD=(apt-get update -qq)
   PKG_INSTALL_CMD=(apt-get install -y)
elif command -v dnf >/dev/null 2>&1; then
   PKG_MGR="dnf"
   PKG_UPDATE_CMD=(dnf makecache -q)
   PKG_INSTALL_CMD=(dnf install -y)
elif command -v yum >/dev/null 2>&1; then
   PKG_MGR="yum"
   PKG_UPDATE_CMD=(yum makecache -q)
   PKG_INSTALL_CMD=(yum install -y)
else
   echo "ERROR: no supported package manager found (apt-get/dnf/yum)." >&2
   exit 10
fi

echo "==> Installing system packages via $PKG_MGR..."
"${PKG_UPDATE_CMD[@]}"
"${PKG_INSTALL_CMD[@]}" nginx rsync curl git
"${PKG_INSTALL_CMD[@]}" nodejs npm >/dev/null 2>&1 || true

if command -v dnf >/dev/null 2>&1; then
   NODE_MAJOR="$(node -v 2>/dev/null | sed -E 's/^v([0-9]+).*/\1/' || true)"
   if [[ -z "$NODE_MAJOR" || "$NODE_MAJOR" -lt 18 ]]; then
      echo "==> Upgrading Node.js stream to v20 for Node-RED compatibility..."
      dnf -y module reset nodejs >/dev/null 2>&1 || true
      dnf -y module enable nodejs:20 >/dev/null 2>&1 || true
      dnf -y install nodejs npm >/dev/null 2>&1 || true
   fi
fi

if ! command -v certbot >/dev/null 2>&1; then
   "${PKG_INSTALL_CMD[@]}" certbot >/dev/null 2>&1 || true
   "${PKG_INSTALL_CMD[@]}" python3-certbot >/dev/null 2>&1 || true
fi

# Optional on some distros/repos.
"${PKG_INSTALL_CMD[@]}" python3-certbot-nginx >/dev/null 2>&1 || true

if command -v certbot >/dev/null 2>&1; then
   echo "==> Certbot detected: $(command -v certbot)"
else
   echo "==> WARNING: certbot not installed from repo; HTTPS certificate step may require manual install."
fi

echo "==> Ensuring gateway Python dependencies..."
"$PYTHON_BIN" -m pip install --upgrade pip wheel setuptools >/tmp/luma_pip_bootstrap.log 2>&1 || {
   echo "ERROR: failed to bootstrap pip tooling" >&2
   tail -n 80 /tmp/luma_pip_bootstrap.log >&2 || true
   exit 8
}
"$PYTHON_BIN" -m pip install \
   fastapi "uvicorn[standard]" pandas numpy requests pydantic \
   python-multipart aiofiles websockets prometheus-client \
   prometheus-fastapi-instrumentator >/tmp/luma_gateway_deps.log 2>&1 || {
   echo "ERROR: failed to install gateway dependencies" >&2
   tail -n 120 /tmp/luma_gateway_deps.log >&2 || true
   exit 9
}

echo "==> Ensuring premium stack Python dependencies..."
PREMIUM_PACKAGES=(
   scikit-learn
   scipy
   PyPortfolioOpt
   quantstats
   lightgbm
   xgboost
   shap
   openai
   fredapi
   yfinance
   alpaca-py
   pyzmq
   colorama
   reportlab
)
if "$PYTHON_BIN" -m pip install "${PREMIUM_PACKAGES[@]}" >/tmp/luma_premium_deps.log 2>&1; then
   echo "  PASS premium stack dependencies refreshed"
else
   echo "WARNING: premium stack dependency install failed." >&2
   tail -n 120 /tmp/luma_premium_deps.log >&2 || true
   if [[ "$STRICT_PREMIUM_STACK" == "1" ]]; then
      echo "ERROR: strict premium stack mode enabled; aborting deploy." >&2
      exit 12
   fi
   echo "WARNING: continuing deploy with partial premium stack." >&2
fi

if "$PYTHON_BIN" - <<'PY' >/tmp/luma_premium_probe.log 2>&1
import importlib.util
modules = [
    "sklearn",
    "scipy",
    "pypfopt",
    "quantstats",
    "lightgbm",
    "xgboost",
    "shap",
    "openai",
    "fredapi",
    "yfinance",
    "alpaca",
    "zmq",
    "colorama",
]
missing = [m for m in modules if importlib.util.find_spec(m) is None]
if missing:
    raise SystemExit("missing_modules=" + ",".join(missing))
print("premium_probe=ok")
PY
then
   echo "  PASS premium module probe"
else
   echo "WARNING: premium module probe failed." >&2
   cat /tmp/luma_premium_probe.log >&2 || true
   if [[ "$STRICT_PREMIUM_STACK" == "1" ]]; then
      echo "ERROR: strict premium stack mode enabled; aborting deploy." >&2
      exit 13
   fi
fi

if [[ -f "$COHERENCE_BUILDER" ]]; then
   echo "==> Building gov-grade coherence artifacts..."
   if "$PYTHON_BIN" "$COHERENCE_BUILDER" >/tmp/luma_coherence_build.log 2>&1; then
      echo "  PASS coherence artifacts refreshed"
      tail -n 8 /tmp/luma_coherence_build.log || true
   else
      echo "WARNING: coherence artifact build failed." >&2
      tail -n 120 /tmp/luma_coherence_build.log >&2 || true
      if [[ "$STRICT_COHERENCE_BUILD" == "1" ]]; then
         echo "ERROR: strict coherence build mode enabled; aborting deploy." >&2
         exit 11
      fi
      echo "WARNING: continuing deploy with existing coherence artifacts." >&2
   fi
else
   echo "==> Coherence builder not found at $COHERENCE_BUILDER; skipping coherence refresh."
fi

NODE_RED_BIN="$(command -v node-red || true)"
if [[ -z "$NODE_RED_BIN" && -x "$(command -v npm || true)" ]]; then
   echo "==> Installing Node-RED via npm..."
   npm install -g --unsafe-perm node-red >/tmp/luma_nodered_install.log 2>&1 || true
   NODE_RED_BIN="$(command -v node-red || true)"
fi
if [[ -z "$NODE_RED_BIN" && -x "/usr/local/bin/node-red" ]]; then
   NODE_RED_BIN="/usr/local/bin/node-red"
fi
if [[ -n "$NODE_RED_BIN" ]]; then
   echo "==> Node-RED detected: $NODE_RED_BIN"
else
   echo "==> WARNING: Node-RED is not installed; Node-RED auto-service will be skipped."
fi

echo "==> Creating web root at $WWW_ROOT"
mkdir -p "$WWW_ROOT"

echo "==> Syncing dashboard web assets to $WWW_ROOT ..."
rsync -av --delete \
   --exclude '*.py' \
   --exclude '*.pyc' \
   --exclude '*.ps1' \
   --exclude '__pycache__/' \
   --exclude '.venv/' \
   --exclude 'node_modules/' \
   "$DASHBOARD_SRC/" "$WWW_ROOT/"

# Compatibility aliases expected by some entrypoints.
cp "$DASHBOARD_SRC/institutional_crypto_paper_dashboard.html" "$WWW_ROOT/trading.html" 2>/dev/null || true
cp "$DASHBOARD_SRC/lumascout_dashboard.html" "$WWW_ROOT/scout.html" 2>/dev/null || true
cp "$DASHBOARD_SRC/infra_audit_dashboard.html" "$WWW_ROOT/audit.html" 2>/dev/null || true

# The gateway creates a singleton lock below the stack root. Prepare only that
# bounded runtime directory for the non-root service account; source remains
# root/operator-owned and output ownership is handled separately below.
install -d -o "$SERVICE_USER" -g "$SERVICE_GROUP" -m 0750 "$STACK_ROOT/run"

GATEWAY_SERVICE="/etc/systemd/system/luma-gateway.service"
echo "==> Installing gateway service: $GATEWAY_SERVICE"
cat > "$GATEWAY_SERVICE" <<EOF
[Unit]
Description=Luma Experience Gateway (FastAPI)
After=network.target
StartLimitIntervalSec=300
StartLimitBurst=10

[Service]
Type=simple
User=$SERVICE_USER
Group=$SERVICE_GROUP
WorkingDirectory=$CODE_DIR
ExecStart=$PYTHON_BIN -m uvicorn luma_experience_gateway:app --app-dir $CODE_DIR --host 127.0.0.1 --port 8787
Restart=on-failure
RestartSec=3
UMask=0027
NoNewPrivileges=true
PrivateTmp=true
Environment=PYTHONUNBUFFERED=1
Environment=LUMA_STACK_ROOT=$STACK_ROOT
Environment=LUMA_DASHBOARD_DIR=$DASHBOARD_SRC

[Install]
WantedBy=multi-user.target
EOF

echo "==> Starting gateway service..."
systemctl daemon-reload
systemctl enable --now luma-gateway
systemctl restart luma-gateway

echo "==> Checking gateway health..."
gateway_ready=0
for attempt in $(seq 1 30); do
   if curl -fsS "http://127.0.0.1:8787/health" >/tmp/luma_gateway_health.json; then
      gateway_ready=1
      break
   fi
   sleep 1
done
if [[ "$gateway_ready" != "1" ]]; then
   echo "ERROR: gateway health check failed on 127.0.0.1:8787" >&2
   systemctl --no-pager --full status luma-gateway || true
   journalctl -u luma-gateway -n 80 --no-pager || true
   exit 5
fi
echo "  PASS gateway health"

DASH_REFRESH_SERVICE="/etc/systemd/system/luma-dashboard-refresh.service"
if [[ -f "$REFRESH_SCRIPT" ]]; then
   echo "==> Installing dashboard refresh service: $DASH_REFRESH_SERVICE"
   cat > "$DASH_REFRESH_SERVICE" <<EOF
[Unit]
Description=Luma Unified Dashboard Refresh Loop
After=network.target luma-gateway.service
Requires=luma-gateway.service
StartLimitIntervalSec=300
StartLimitBurst=5

[Service]
Type=simple
User=$SERVICE_USER
Group=$SERVICE_GROUP
WorkingDirectory=$CODE_DIR
ExecStart=$PYTHON_BIN $REFRESH_SCRIPT --loop
Restart=on-failure
RestartSec=5
UMask=0027
NoNewPrivileges=true
PrivateTmp=true
Environment=PYTHONUNBUFFERED=1
Environment=LUMA_STACK_ROOT=$STACK_ROOT
Environment=LUMA_DASHBOARD_DIR=$DASHBOARD_SRC

[Install]
WantedBy=multi-user.target
EOF
   systemctl daemon-reload
   systemctl enable --now luma-dashboard-refresh
   systemctl restart luma-dashboard-refresh
else
   echo "==> WARNING: dashboard refresh script not found at $REFRESH_SCRIPT; skipping auto-refresh service."
fi

mkdir -p "$STACK_ROOT/data/kraken_hourly_history" "$STACK_ROOT/out/ops" "$STACK_ROOT/out/execution"
chown -R "$SERVICE_USER:$SERVICE_GROUP" \
   "$STACK_ROOT/data/kraken_hourly_history" \
   "$STACK_ROOT/out/ops" \
   "$STACK_ROOT/out/execution" || true

PAPER_TICKER_LEDGER="$STACK_ROOT/out/execution/multi_exchange_paper_ticker_ledger.jsonl"
if [[ -e "$PAPER_TICKER_LEDGER" ]]; then
   if [[ ! -f "$PAPER_TICKER_LEDGER" || -L "$PAPER_TICKER_LEDGER" ]]; then
      echo "==> ERROR: paper-ticker ledger is not a regular non-symbolic file." >&2
      exit 1
   fi
   chown --no-dereference "$SERVICE_USER:$SERVICE_GROUP" "$PAPER_TICKER_LEDGER"
   chmod 0640 "$PAPER_TICKER_LEDGER"
else
   install -o "$SERVICE_USER" -g "$SERVICE_GROUP" -m 0640 /dev/null "$PAPER_TICKER_LEDGER"
fi

RUNTIME_PREFLIGHT="$CODE_DIR/ops/assert_runtime_safety.py"
PAPER_TICKER="$CODE_DIR/multi_exchange_paper_ticker.py"
if [[ -f "$RUNTIME_PREFLIGHT" && -f "$PAPER_TICKER" ]]; then
   echo "==> Installing paper-only ticker service..."
   cat > /etc/systemd/system/luma-paper-ticker.service <<EOF
[Unit]
Description=Luma Multi-Exchange Paper Ticker
After=network-online.target
Wants=network-online.target
StartLimitIntervalSec=300
StartLimitBurst=5

[Service]
Type=simple
User=$SERVICE_USER
Group=$SERVICE_GROUP
WorkingDirectory=$CODE_DIR
Environment=PYTHONUNBUFFERED=1
Environment=LUMA_STACK_ROOT=$STACK_ROOT
UMask=0027
ExecStartPre=$PYTHON_BIN $RUNTIME_PREFLIGHT
ExecStart=$PYTHON_BIN $PAPER_TICKER --profile apex --seed-capital 250000
Restart=on-failure
RestartSec=20

[Install]
WantedBy=multi-user.target
EOF
   systemctl daemon-reload
   systemctl enable --now luma-paper-ticker
   systemctl restart luma-paper-ticker
else
   echo "==> WARNING: paper ticker or runtime preflight missing; ticker service not installed."
fi

AWARENESS_SCRIPT="$CODE_DIR/execution/luma_symbol_awareness_daemon.py"
if [[ -f "$AWARENESS_SCRIPT" && -f "$STACK_ROOT/symbol_registry_auto.py" ]]; then
   echo "==> Installing symbol awareness service..."
   cat > /etc/systemd/system/luma-symbol-awareness.service <<EOF
[Unit]
Description=Luma Full-Universe Symbol Awareness (Shadow Only)
After=network-online.target
Wants=network-online.target
StartLimitIntervalSec=300
StartLimitBurst=5

[Service]
Type=simple
User=$SERVICE_USER
Group=$SERVICE_GROUP
WorkingDirectory=$CODE_DIR
Environment=PYTHONUNBUFFERED=1
Environment=LUMA_STACK_ROOT=$STACK_ROOT
Environment=LUMA_HARMONIC_DEBUG=0
UMask=0027
ExecStart=$PYTHON_BIN $AWARENESS_SCRIPT --loop-seconds 1.0 --batch-size 120
Restart=on-failure
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF
   systemctl daemon-reload
   systemctl enable --now luma-symbol-awareness
   systemctl restart luma-symbol-awareness
else
   echo "==> WARNING: awareness script or symbol registry missing; awareness service not installed."
fi

HISTORY_SCRIPT="$CODE_DIR/ops/collect_kraken_hourly_history.py"
if [[ -f "$HISTORY_SCRIPT" ]]; then
   echo "==> Installing Kraken history service..."
   cat > /etc/systemd/system/luma-kraken-history.service <<EOF
[Unit]
Description=Luma Kraken Hourly History Collector and Timing Rebuild
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
User=$SERVICE_USER
Group=$SERVICE_GROUP
WorkingDirectory=$CODE_DIR
Environment=PYTHONUNBUFFERED=1
Environment=LUMA_STACK_ROOT=$STACK_ROOT
ExecStart=$PYTHON_BIN $HISTORY_SCRIPT --daemon --cycle-sec 21600 --pair-limit 80 --rebuild-timing
Restart=always
RestartSec=30

[Install]
WantedBy=multi-user.target
EOF
   systemctl daemon-reload
   systemctl enable --now luma-kraken-history
   systemctl restart luma-kraken-history
else
   echo "==> WARNING: Kraken history collector missing; history service not installed."
fi

cat > /etc/logrotate.d/lumencore <<'EOF'
/var/log/lumencore/*.log {
    daily
    rotate 7
    size 50M
    compress
    delaycompress
    missingok
    notifempty
    copytruncate
}
EOF

if [[ -n "$NODE_RED_BIN" ]]; then
   NODE_RED_USERDIR="/var/lib/luma-node-red"
   NODE_RED_SERVICE="/etc/systemd/system/luma-node-red.service"
   mkdir -p "$NODE_RED_USERDIR"
   chown -R "$SERVICE_USER:$SERVICE_GROUP" "$NODE_RED_USERDIR" || true

   echo "==> Installing Node-RED service: $NODE_RED_SERVICE"
   cat > "$NODE_RED_SERVICE" <<EOF
[Unit]
Description=Luma Node-RED Automation Bus
After=network.target

[Service]
Type=simple
User=$SERVICE_USER
Group=$SERVICE_GROUP
WorkingDirectory=$CODE_DIR
Environment=HOME=/home/$SERVICE_USER
ExecStart=$NODE_RED_BIN --userDir $NODE_RED_USERDIR --port 1880
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
EOF

   systemctl daemon-reload
   systemctl enable --now luma-node-red

   if [[ -f "$NODE_RED_FLOW_FILE" && -f "$NODE_RED_ENSURE_SCRIPT" ]]; then
      NODE_RED_FLOW_SYNC_SERVICE="/etc/systemd/system/luma-nodered-flow-sync.service"
      echo "==> Installing Node-RED flow sync service: $NODE_RED_FLOW_SYNC_SERVICE"
      cat > "$NODE_RED_FLOW_SYNC_SERVICE" <<EOF
[Unit]
Description=Luma Node-RED Flow Sync
After=luma-node-red.service luma-gateway.service
Requires=luma-node-red.service luma-gateway.service

[Service]
Type=oneshot
WorkingDirectory=$CODE_DIR
ExecStartPre=/bin/sh -c 'for i in \$(seq 1 30); do curl -fsS http://127.0.0.1:1880/ >/dev/null && exit 0; sleep 1; done; exit 1'
ExecStart=$PYTHON_BIN $NODE_RED_ENSURE_SCRIPT --base http://127.0.0.1:1880 --flow-file $NODE_RED_FLOW_FILE --min-nodes 11
RemainAfterExit=yes

[Install]
WantedBy=multi-user.target
EOF
      systemctl daemon-reload
      systemctl enable --now luma-nodered-flow-sync || true
   else
      echo "==> WARNING: Node-RED flow assets not found; skipping flow sync service."
      echo "    missing flow: $NODE_RED_FLOW_FILE"
      echo "    missing helper: $NODE_RED_ENSURE_SCRIPT"
   fi
fi

EDGE_USING_CADDY="0"
if systemctl is-active --quiet caddy; then
   EDGE_USING_CADDY="1"
fi

if [[ "$EDGE_USING_CADDY" == "1" ]]; then
   echo "==> Caddy is active on this host; skipping nginx activation to avoid port conflicts."
else
   echo "==> Installing nginx config..."
   cp "$(dirname "$0")/nginx/lumatrader.conf" "$NGINX_SITE"
   sed -i "s/yourdomain.com/$DOMAIN/g" "$NGINX_SITE"
   if [[ -d "/etc/nginx/sites-enabled" ]]; then
      ln -sf "$NGINX_SITE" /etc/nginx/sites-enabled/lumatrader
      rm -f /etc/nginx/sites-enabled/default
   fi

   echo "==> Testing nginx config..."
   nginx -t

   if systemctl is-active --quiet nginx; then
      echo "==> Reloading nginx..."
      systemctl reload nginx
   else
      echo "==> Starting nginx..."
      systemctl enable --now nginx
   fi
fi

echo "==> Running post-deploy smoke checks..."
for p in "/api/snapshot" "/api/unity/unified-edge" "/health"; do
   code="$(curl -sS -o /dev/null -w "%{http_code}" "http://127.0.0.1:8787$p")"
   if [[ "$code" != "200" ]]; then
      echo "ERROR: direct gateway smoke check failed for $p (HTTP $code)" >&2
      exit 4
   fi
   echo "  PASS gateway $p (HTTP $code)"
done

if [[ "$EDGE_USING_CADDY" == "1" ]]; then
   SMOKE_BASE="http://127.0.0.1:8787"
   SMOKE_PATHS=(
      "/api/snapshot"
      "/api/unity/unified-edge"
      "/health"
   )
   if [[ ! -f "$WWW_ROOT/mission_control.html" ]]; then
      echo "ERROR: mission_control.html missing from $WWW_ROOT" >&2
      exit 4
   fi
else
   SMOKE_BASE="http://127.0.0.1"
   SMOKE_PATHS=(
      "/"
      "/mission_control.html"
      "/api/snapshot"
      "/api/unity/unified-edge"
      "/health"
      "/nginx-health"
   )
fi

for p in "${SMOKE_PATHS[@]}"; do
   code="$(curl -sS -o /dev/null -w "%{http_code}" "$SMOKE_BASE$p")"
   if [[ "$code" != "200" && "$code" != "301" && "$code" != "302" && "$code" != "307" && "$code" != "308" ]]; then
      echo "ERROR: smoke check failed for $p (HTTP $code)" >&2
      exit 4
   fi
   echo "  PASS $p (HTTP $code)"
done

NR_POST_CODE="$(curl -sS -o /dev/null -w "%{http_code}" -X POST "http://127.0.0.1:8787/api/nodered/ingest" -H "Content-Type: application/json" -d '{"source":"deploy_smoke","alive":true}')"
if [[ "$NR_POST_CODE" == "200" ]]; then
   echo "  PASS /api/nodered/ingest (HTTP 200)"
else
   echo "==> WARNING: /api/nodered/ingest returned HTTP $NR_POST_CODE"
fi

echo ""
echo "==> Portal live at http://$DOMAIN"
echo ""
echo "Next: run certbot for HTTPS:"
echo "  sudo certbot --nginx -d $DOMAIN -d www.$DOMAIN -d app.$DOMAIN -d research.$DOMAIN"
echo ""
echo "After certbot, update /etc/nginx/sites-available/lumatrader"
echo "and uncomment the HTTPS listen + SSL certificate lines."
echo ""
echo "Gateway service is managed by systemd:"
echo "  sudo systemctl status luma-gateway"
echo "  sudo journalctl -u luma-gateway -f"
echo "Dashboard refresh loop service:"
echo "  sudo systemctl status luma-dashboard-refresh"
echo "  sudo journalctl -u luma-dashboard-refresh -f"
echo "Node-RED automation bus (if installed):"
echo "  sudo systemctl status luma-node-red"
echo "  sudo systemctl status luma-nodered-flow-sync"
echo ""
echo "Start supporting services on the VPS (if needed):"
echo "  python -m panel serve .../lamascout_dashboard.py     --port 5017 --address 127.0.0.1 &"
echo "  python -m panel serve .../build_institutional_crypto_paper_dashboard.py --port 5016 --address 127.0.0.1 &"
echo "  uvicorn execution.sector_opp_gain_server:app         --port 7700 --host 127.0.0.1 &"
