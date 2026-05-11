#!/bin/bash
# =============================================================================
# LUMEN-CORE.AI — Full Stack VPS Deployment
# Target: Oracle Cloud Ubuntu instance-20260423-0118
# Public IP: 157.151.148.234
# Domain: lumen-core.ai
# =============================================================================
set -e

DOMAIN="lumen-core.ai"
STACK_ROOT="/opt/lumencore"
STACK_USER="lumencore"
PY_VERSION="3.11"
DASHBOARD_PORT=5016
API_PORT=8000
LAMASCOUT_API_PORT=8001

echo "======================================================"
echo " LUMEN-CORE.AI VPS DEPLOYMENT — $(date -u)"
echo "======================================================"

# ------------------------------------------------------------------------------
# 1. SYSTEM PACKAGES
# ------------------------------------------------------------------------------
echo "[1/9] Installing system packages..."
apt-get update -y
apt-get install -y \
    python${PY_VERSION} python${PY_VERSION}-venv python3-pip \
    nginx certbot python3-certbot-nginx \
    git curl wget unzip htop tmux screen \
    build-essential libssl-dev libffi-dev \
    postgresql-client \
    supervisor \
    ufw

# ------------------------------------------------------------------------------
# 2. FIREWALL
# ------------------------------------------------------------------------------
echo "[2/9] Configuring firewall..."
ufw allow OpenSSH
ufw allow 'Nginx Full'
ufw allow 443/tcp
ufw allow 80/tcp
ufw --force enable

# ------------------------------------------------------------------------------
# 3. CREATE STACK USER + DIRECTORIES
# ------------------------------------------------------------------------------
echo "[3/9] Creating stack user and directories..."
id -u ${STACK_USER} &>/dev/null || useradd -m -s /bin/bash ${STACK_USER}
mkdir -p ${STACK_ROOT}/{code,LamaScout,config,out,logs,dashboard}
mkdir -p ${STACK_ROOT}/out/execution
mkdir -p ${STACK_ROOT}/LamaScout/out
mkdir -p /var/log/lumencore

# ------------------------------------------------------------------------------
# 4. PYTHON VENV + PACKAGES
# ------------------------------------------------------------------------------
echo "[4/9] Creating Python virtual environment..."
python${PY_VERSION} -m venv ${STACK_ROOT}/.venv
source ${STACK_ROOT}/.venv/bin/activate

pip install --upgrade pip setuptools wheel

echo "[4/9] Installing base trading stack packages (203 packages)..."
pip install \
    aiodns aiohappyeyeballs aiohttp aiosignal aiosqlite alembic altair \
    amplitude-analytics annotated-types anyio apprise arch asgi-lifespan asyncpg \
    attrs beartype bleach bokeh cachetools ccxt certifi cffi charset-normalizer \
    clarabel click cloudpickle colorama colorlog contourpy coolname cronsim \
    cryptography cvxpy cycler cyclopts dateparser defusedxml docker \
    docstring-parser docutils duckdb et-xmlfile exceptiongroup fakeredis \
    fastapi fonttools fpdf2 frozenlist fsspec \
    google-api-python-client google-auth google-auth-httplib2 \
    google-auth-oauthlib googleapis-common-protos graphviz greenlet griffe \
    httpcore httpx humanize humanfriendly ijson importlib-metadata \
    jinja2 joblib jsonschema kaleido loguru \
    markdown markupsafe matplotlib numpy openpyxl optuna \
    packaging pandas panel paramiko patsy pillow plotly polars \
    prefect psutil psycopg pyarrow pydantic pydantic-settings \
    PyYAML pyzmq requests rich \
    scikit-learn scipy seaborn setuptools six \
    sniffio spotipy SQLAlchemy statsmodels \
    tenacity tqdm typer \
    uvicorn websocket-client websockets \
    pytrends newsapi-python python-dotenv \
    streamlit dash

echo "[4/9] Installing LamaScout extras..."
pip install \
    spotipy pytrends newsapi-python prefect TikTokApi \
    river polars altair panel duckdb optuna

deactivate

# ------------------------------------------------------------------------------
# 5. UPLOAD / CLONE CODE
# ------------------------------------------------------------------------------
echo "[5/9] Code directory ready at ${STACK_ROOT}"
echo "      --> rsync or scp your stack from your Windows machine:"
echo ""
echo "      # From Windows PowerShell (run once after this script finishes):"
echo "      scp -r C:/LumaTrader/INSTITUTIONAL_STACK_V2/code/* ubuntu@157.151.148.234:${STACK_ROOT}/code/"
echo "      scp -r C:/LumaTrader/INSTITUTIONAL_STACK_V2/LamaScout/* ubuntu@157.151.148.234:${STACK_ROOT}/LamaScout/"
echo ""

chown -R ${STACK_USER}:${STACK_USER} ${STACK_ROOT}
chown -R ${STACK_USER}:${STACK_USER} /var/log/lumencore

# ------------------------------------------------------------------------------
# 6. SYSTEMD SERVICES
# ------------------------------------------------------------------------------
echo "[6/9] Installing systemd services..."

# --- LamaScout API service ---
cat > /etc/systemd/system/lamascout-api.service << 'EOF'
[Unit]
Description=LamaScout Artist Intelligence API
After=network.target

[Service]
Type=simple
User=lumencore
WorkingDirectory=/opt/lumencore/LamaScout
Environment="PATH=/opt/lumencore/.venv/bin"
ExecStart=/opt/lumencore/.venv/bin/python -m uvicorn src.dashboard_api:app --host 0.0.0.0 --port 8001 --workers 2
Restart=always
RestartSec=10
StandardOutput=append:/var/log/lumencore/lamascout-api.log
StandardError=append:/var/log/lumencore/lamascout-api.log

[Install]
WantedBy=multi-user.target
EOF

# --- LamaScout Continuous Scouting Loop ---
cat > /etc/systemd/system/lamascout-loop.service << 'EOF'
[Unit]
Description=LamaScout Continuous Artist Scouting Pipeline
After=network.target

[Service]
Type=simple
User=lumencore
WorkingDirectory=/opt/lumencore/LamaScout
Environment="PATH=/opt/lumencore/.venv/bin"
ExecStart=/opt/lumencore/.venv/bin/python -m src.pipeline --loop --interval 1800
Restart=always
RestartSec=30
StandardOutput=append:/var/log/lumencore/lamascout-loop.log
StandardError=append:/var/log/lumencore/lamascout-loop.log

[Install]
WantedBy=multi-user.target
EOF

# --- Institutional Crypto Dashboard (Panel serve) ---
cat > /etc/systemd/system/luma-dashboard.service << 'EOF'
[Unit]
Description=LumaCore Institutional Crypto Dashboard
After=network.target

[Service]
Type=simple
User=lumencore
WorkingDirectory=/opt/lumencore/code
Environment="PATH=/opt/lumencore/.venv/bin"
ExecStart=/opt/lumencore/.venv/bin/python /opt/lumencore/code/execution/build_institutional_crypto_paper_dashboard.py --mode serve --host 127.0.0.1 --port 5016
Restart=always
RestartSec=15
StandardOutput=append:/var/log/lumencore/dashboard.log
StandardError=append:/var/log/lumencore/dashboard.log

[Install]
WantedBy=multi-user.target
EOF

# --- Paper Ticker Engine ---
cat > /etc/systemd/system/luma-paper-ticker.service << 'EOF'
[Unit]
Description=LumaCore Multi-Exchange Paper Ticker
After=network.target

[Service]
Type=simple
User=lumencore
WorkingDirectory=/opt/lumencore/code
Environment="PATH=/opt/lumencore/.venv/bin"
ExecStart=/opt/lumencore/.venv/bin/python /opt/lumencore/code/multi_exchange_paper_ticker.py --profile apex --seed-capital 250000
Restart=always
RestartSec=20
StandardOutput=append:/var/log/lumencore/paper-ticker.log
StandardError=append:/var/log/lumencore/paper-ticker.log

[Install]
WantedBy=multi-user.target
EOF

systemctl daemon-reload
systemctl enable lamascout-api lamascout-loop luma-dashboard luma-paper-ticker

echo "[6/9] Services installed and enabled."

# ------------------------------------------------------------------------------
# 7. NGINX REVERSE PROXY
# ------------------------------------------------------------------------------
echo "[7/9] Configuring nginx for lumen-core.ai..."

cat > /etc/nginx/sites-available/lumen-core.ai << 'EOF'
# =============================================================================
# lumen-core.ai — Nginx Reverse Proxy
# =============================================================================

# Redirect HTTP -> HTTPS
server {
    listen 80;
    server_name lumen-core.ai www.lumen-core.ai;
    return 301 https://$host$request_uri;
}

server {
    listen 443 ssl http2;
    server_name lumen-core.ai www.lumen-core.ai;

    # SSL — filled in by certbot
    ssl_certificate     /etc/letsencrypt/live/lumen-core.ai/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/lumen-core.ai/privkey.pem;
    include             /etc/letsencrypt/options-ssl-nginx.conf;
    ssl_dhparam         /etc/letsencrypt/ssl-dhparams.pem;

    # Security headers
    add_header Strict-Transport-Security "max-age=63072000; includeSubDomains; preload" always;
    add_header X-Frame-Options SAMEORIGIN always;
    add_header X-Content-Type-Options nosniff always;
    add_header Referrer-Policy no-referrer-when-downgrade always;

    # --- Institutional Crypto Dashboard ---
    location /dashboard/ {
        proxy_pass         http://127.0.0.1:5016/;
        proxy_http_version 1.1;
        proxy_set_header   Upgrade $http_upgrade;
        proxy_set_header   Connection "upgrade";
        proxy_set_header   Host $host;
        proxy_set_header   X-Real-IP $remote_addr;
        proxy_read_timeout 86400;
    }

    # --- LamaScout Artist Intelligence API ---
    location /api/scout/ {
        proxy_pass         http://127.0.0.1:8001/;
        proxy_http_version 1.1;
        proxy_set_header   Host $host;
        proxy_set_header   X-Real-IP $remote_addr;
    }

    # --- Trading Stack API (if enabled) ---
    location /api/trading/ {
        proxy_pass         http://127.0.0.1:8000/;
        proxy_http_version 1.1;
        proxy_set_header   Host $host;
        proxy_set_header   X-Real-IP $remote_addr;
    }

    # --- Static out/ directory (proof packs, reports) ---
    location /proof/ {
        alias /opt/lumencore/out/;
        autoindex on;
        autoindex_exact_size off;
        autoindex_localtime on;
    }

    # --- Root serves a status page ---
    location / {
        return 200 '{"status":"LUMEN-CORE ONLINE","domain":"lumen-core.ai","stack":"INSTITUTIONAL_STACK_V2"}';
        add_header Content-Type application/json;
    }
}
EOF

ln -sf /etc/nginx/sites-available/lumen-core.ai /etc/nginx/sites-enabled/lumen-core.ai
rm -f /etc/nginx/sites-enabled/default
nginx -t && systemctl reload nginx

# ------------------------------------------------------------------------------
# 8. SSL CERTIFICATE (Let's Encrypt)
# ------------------------------------------------------------------------------
echo "[8/9] Obtaining SSL certificate for lumen-core.ai..."
echo "      NOTE: DNS must be pointed to 157.151.148.234 BEFORE this runs."
echo ""
echo "      Run this command after DNS propagates:"
echo "      certbot --nginx -d lumen-core.ai -d www.lumen-core.ai --non-interactive --agree-tos -m admin@lumen-core.ai"
echo ""
echo "      Auto-renewal is already configured by certbot's systemd timer."

# ------------------------------------------------------------------------------
# 9. DONE
# ------------------------------------------------------------------------------
echo ""
echo "======================================================"
echo " DEPLOYMENT COMPLETE"
echo " lumen-core.ai → 157.151.148.234"
echo ""
echo " Services:"
echo "   lamascout-api    → https://lumen-core.ai/api/scout/"
echo "   dashboard        → https://lumen-core.ai/dashboard/"
echo "   proof artifacts  → https://lumen-core.ai/proof/"
echo ""
echo " Next steps:"
echo "   1. Point DNS A record: lumen-core.ai → 157.151.148.234"
echo "   2. SCP your code from Windows (commands shown in step 5 above)"
echo "   3. Run certbot for SSL"
echo "   4. systemctl start luma-paper-ticker lamascout-loop"
echo "   5. systemctl start lamascout-api luma-dashboard"
echo "======================================================"
