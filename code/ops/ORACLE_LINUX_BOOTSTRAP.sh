#!/usr/bin/env bash
# ============================================================
# ORACLE_LINUX_BOOTSTRAP.sh
# Run once on Oracle Linux after stack is uploaded.
# Usage:  bash ORACLE_LINUX_BOOTSTRAP.sh [DOMAIN]
# Example: bash ORACLE_LINUX_BOOTSTRAP.sh lumen-core.ai
# ============================================================
set -e

DOMAIN="${1:-lumen-core.ai}"
INSTALL_ROOT="/opt/lumatrader"
STACK="$INSTALL_ROOT/INSTITUTIONAL_STACK_V2"
CODE="$STACK/code"
VENV="$CODE/.venv"
PY="$VENV/bin/python3"

echo "=================================================="
echo " LumaTrader Oracle Linux Bootstrap"
echo " Install root : $INSTALL_ROOT"
echo " Domain       : $DOMAIN"
echo " Date         : $(date -u)"
echo "=================================================="

# ── 1. System packages ────────────────────────────────────
echo "[1/8] Installing system packages..."
sudo dnf install -y python3 python3-pip python3-venv git curl wget unzip \
    gcc gcc-c++ make openssl-devel bzip2-devel libffi-devel 2>/dev/null || \
sudo apt-get install -y python3 python3-pip python3-venv git curl wget unzip \
    build-essential libssl-dev libffi-dev 2>/dev/null || true

# ── 2. Move stack into place ──────────────────────────────
echo "[2/8] Setting up install path..."
sudo mkdir -p "$INSTALL_ROOT"
sudo chown -R "$(whoami)":"$(whoami)" "$INSTALL_ROOT"

# If uploaded as zip
if [ -f ~/INSTITUTIONAL_STACK_V2.zip ]; then
    echo "  Found zip, extracting to $INSTALL_ROOT ..."
    unzip -q ~/INSTITUTIONAL_STACK_V2.zip -d "$INSTALL_ROOT"
elif [ -d ~/INSTITUTIONAL_STACK_V2 ]; then
    echo "  Found directory, moving to $INSTALL_ROOT ..."
    mv ~/INSTITUTIONAL_STACK_V2 "$STACK"
else
    echo "  Stack already at $STACK (or nothing to move)"
fi

# ── 3. Patch ALL hardcoded Windows paths in Python files ─────
echo "[3/8] Patching Windows paths in all .py files..."
python3 - <<'PATCHEOF'
import os, sys

STACK_ROOT = "/opt/lumatrader/INSTITUTIONAL_STACK_V2"
CODE_ROOT  = os.path.join(STACK_ROOT, "code")

WIN_ROOTS = [
    r"C:\LumaTrader\INSTITUTIONAL_STACK_V2",
    r"C:/LumaTrader/INSTITUTIONAL_STACK_V2",
    "C:\\\\LumaTrader\\\\INSTITUTIONAL_STACK_V2",
]
SYSPATH_WIN = [
    r"C:\LumaTrader\INSTITUTIONAL_STACK_V2\code",
    r"C:/LumaTrader/INSTITUTIONAL_STACK_V2/code",
    r"C:\LumaTrader\INSTITUTIONAL_STACK_V2\code\execution",
    r"C:/LumaTrader/INSTITUTIONAL_STACK_V2/code/execution",
]

patched = 0
for dirpath, dirs, files in os.walk(CODE_ROOT):
    # skip venv
    dirs[:] = [d for d in dirs if d not in (".venv", "venv", "__pycache__")]
    for fname in files:
        if not fname.endswith(".py"):
            continue
        fpath = os.path.join(dirpath, fname)
        try:
            with open(fpath, "r", encoding="utf-8", errors="ignore") as fh:
                content = fh.read()
            new = content
            for win in WIN_ROOTS:
                new = new.replace(win, STACK_ROOT)
            for win in SYSPATH_WIN:
                new = new.replace(win, win.replace("C:\\LumaTrader\\INSTITUTIONAL_STACK_V2", STACK_ROOT)
                                          .replace("C:/LumaTrader/INSTITUTIONAL_STACK_V2", STACK_ROOT)
                                          .replace("\\", "/"))
            # Fix Scripts\python.exe → bin/python3
            new = new.replace(".venv\\Scripts\\python.exe", ".venv/bin/python3")
            new = new.replace(".venv/Scripts/python.exe", ".venv/bin/python3")
            if new != content:
                with open(fpath, "w", encoding="utf-8") as fh:
                    fh.write(new)
                patched += 1
        except Exception as e:
            print(f"  SKIP {fpath}: {e}")

print(f"  Patched {patched} files.")
PATCHEOF

# ── 4. Create Python venv ─────────────────────────────────
echo "[4/8] Creating Python virtual environment..."
python3 -m venv "$VENV"
"$VENV/bin/pip" install --upgrade pip setuptools wheel -q

# ── 5. Install Python requirements ───────────────────────
echo "[5/8] Installing Python packages (this takes ~2 min)..."
if [ -f "$STACK/LamaScout/requirements.txt" ]; then
    "$VENV/bin/pip" install -r "$STACK/LamaScout/requirements.txt" -q
fi
if [ -f "$STACK/LamaScout/requirements-extra.txt" ]; then
    "$VENV/bin/pip" install -r "$STACK/LamaScout/requirements-extra.txt" -q
fi
# Trading stack extras
"$VENV/bin/pip" install panel plotly pandas numpy requests alpaca-trade-api \
    scipy osqp cvxpy scikit-learn websocket-client aiohttp uvicorn fastapi \
    python-dotenv pyyaml rich loguru -q 2>/dev/null || true

# ── 6. Firewall + open ports ──────────────────────────────
echo "[6/8] Opening firewall ports 80 and 443..."
sudo firewall-cmd --permanent --add-port=80/tcp  2>/dev/null || true
sudo firewall-cmd --permanent --add-port=443/tcp 2>/dev/null || true
sudo firewall-cmd --permanent --add-port=5016/tcp 2>/dev/null || true
sudo firewall-cmd --permanent --add-port=8000/tcp 2>/dev/null || true
sudo firewall-cmd --reload 2>/dev/null || true
# Ubuntu fallback
sudo ufw allow 80  2>/dev/null || true
sudo ufw allow 443 2>/dev/null || true
sudo ufw allow 5016 2>/dev/null || true
sudo ufw allow 8000 2>/dev/null || true

# ── 7. Install Caddy (reverse proxy) ─────────────────────
echo "[7/8] Installing Caddy..."
if ! command -v caddy &>/dev/null; then
    curl -fsSL https://caddyserver.com/api/download?os=linux&arch=amd64 -o /tmp/caddy
    sudo mv /tmp/caddy /usr/local/bin/caddy
    sudo chmod +x /usr/local/bin/caddy
fi

cat > /tmp/Caddyfile <<CADDY
$DOMAIN {
    reverse_proxy /api/* localhost:8000
    reverse_proxy localhost:5016
}
CADDY
sudo mkdir -p /etc/caddy
sudo cp /tmp/Caddyfile /etc/caddy/Caddyfile

# Caddy systemd unit
sudo tee /etc/systemd/system/caddy.service > /dev/null <<'UNIT'
[Unit]
Description=Caddy Web Server
After=network.target

[Service]
ExecStart=/usr/local/bin/caddy run --config /etc/caddy/Caddyfile
Restart=on-failure

[Install]
WantedBy=multi-user.target
UNIT

sudo systemctl daemon-reload
sudo systemctl enable caddy
sudo systemctl restart caddy

# ── 8. Create systemd services for dashboard + LamaScout ─
echo "[8/8] Creating systemd services..."

# Dashboard
sudo tee /etc/systemd/system/lumatrader-dashboard.service > /dev/null <<UNIT
[Unit]
Description=LumaTrader Institutional Dashboard
After=network.target

[Service]
WorkingDirectory=$CODE
ExecStart=$PY $CODE/execution/build_institutional_crypto_paper_dashboard.py --mode serve --host 127.0.0.1 --port 5016
Restart=always
RestartSec=10
Environment=PYTHONUNBUFFERED=1

[Install]
WantedBy=multi-user.target
UNIT

# LamaScout API
sudo tee /etc/systemd/system/lamascout.service > /dev/null <<UNIT
[Unit]
Description=LamaScout API
After=network.target

[Service]
WorkingDirectory=$STACK/LamaScout
ExecStart=$PY -m uvicorn src.dashboard_api:app --host 127.0.0.1 --port 8000
Restart=always
RestartSec=10
Environment=PYTHONUNBUFFERED=1

[Install]
WantedBy=multi-user.target
UNIT

sudo systemctl daemon-reload
sudo systemctl enable lumatrader-dashboard lamascout
sudo systemctl start lumatrader-dashboard lamascout

echo ""
echo "=================================================="
echo " Bootstrap complete!"
echo ""
echo " Dashboard : http://$DOMAIN  (or http://$(curl -s ifconfig.me))"
echo " LamaScout : http://$DOMAIN/api/..."
echo ""
echo " Next steps:"
echo "   1. Point $DOMAIN A record to: $(curl -s ifconfig.me)"
echo "   2. Check services: systemctl status lumatrader-dashboard lamascout caddy"
echo "   3. View logs:      journalctl -u lumatrader-dashboard -f"
echo "=================================================="
