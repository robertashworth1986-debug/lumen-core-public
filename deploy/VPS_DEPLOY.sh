#!/bin/bash
# =============================================================================
# LUMEN-CORE.AI — Full Stack VPS Deployment
# Target: Oracle Cloud Ubuntu instance-20260423-0118
# Public IP: 157.151.148.234
# Domain: lumen-core.ai
# =============================================================================
set -e

DOMAIN="lumen-core.ai"
APP_DOMAIN="app.${DOMAIN}"
RESEARCH_DOMAIN="research.${DOMAIN}"
STACK_ROOT="/opt/lumencore"
STACK_USER="lumencore"
PY_VERSION="3.11"
DASHBOARD_PORT=5016
API_PORT=8000
LAMASCOUT_API_PORT=8001
INTEL_API_PORT=7700

PKG_MGR=""
PY_BIN=""

detect_pkg_manager() {
    if command -v apt-get >/dev/null 2>&1; then
        PKG_MGR="apt"
    elif command -v dnf >/dev/null 2>&1; then
        PKG_MGR="dnf"
    elif command -v yum >/dev/null 2>&1; then
        PKG_MGR="yum"
    else
        echo "ERROR: unsupported Linux distro (apt/dnf/yum not found)."
        exit 1
    fi
}

resolve_python_bin() {
    if command -v "python${PY_VERSION}" >/dev/null 2>&1; then
        PY_BIN="python${PY_VERSION}"
    elif command -v python3 >/dev/null 2>&1; then
        PY_BIN="python3"
    else
        echo "ERROR: python3 not found after package installation."
        exit 1
    fi
}

install_system_packages() {
    case "${PKG_MGR}" in
        apt)
            apt-get update -y
            apt-get install -y \
                python${PY_VERSION} python${PY_VERSION}-venv python3-pip \
                nginx certbot python3-certbot-nginx \
                git curl wget unzip htop tmux screen \
                build-essential libssl-dev libffi-dev \
                postgresql-client \
                supervisor \
                ufw
            ;;
        dnf)
            dnf -y install epel-release || true
            dnf -y install \
                python3 python3-pip python3-devel \
                nginx \
                git curl wget unzip tmux \
                gcc gcc-c++ make openssl-devel libffi-devel \
                postgresql \
                firewalld

            for pkg in python3-virtualenv certbot python3-certbot-nginx htop screen supervisor; do
                dnf -y install "$pkg" || echo "      Optional package unavailable on this host: $pkg"
            done
            ;;
        yum)
            yum -y install epel-release || true
            yum -y install \
                python3 python3-pip python3-devel \
                nginx \
                git curl wget unzip tmux \
                gcc gcc-c++ make openssl-devel libffi-devel \
                postgresql \
                firewalld

            for pkg in python3-virtualenv certbot python3-certbot-nginx htop screen supervisor; do
                yum -y install "$pkg" || echo "      Optional package unavailable on this host: $pkg"
            done
            ;;
    esac
}

echo "======================================================"
echo " LUMEN-CORE.AI VPS DEPLOYMENT — $(date -u)"
echo "======================================================"

# ------------------------------------------------------------------------------
# 1. SYSTEM PACKAGES
# ------------------------------------------------------------------------------
echo "[1/9] Installing system packages..."
detect_pkg_manager
echo "      Package manager: ${PKG_MGR}"
install_system_packages
resolve_python_bin
echo "      Python runtime: ${PY_BIN}"

# ------------------------------------------------------------------------------
# 2. FIREWALL
# ------------------------------------------------------------------------------
echo "[2/9] Configuring firewall..."
if command -v ufw >/dev/null 2>&1; then
    ufw allow OpenSSH || true
    ufw allow 'Nginx Full' || true
    ufw allow 443/tcp || true
    ufw allow 80/tcp || true
    ufw --force enable || true
elif command -v firewall-cmd >/dev/null 2>&1; then
    systemctl enable --now firewalld || true
    firewall-cmd --permanent --add-service=ssh || true
    firewall-cmd --permanent --add-service=http || true
    firewall-cmd --permanent --add-service=https || true
    firewall-cmd --reload || true
else
    echo "      Firewall tool not found; skipping automated firewall config."
fi

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
${PY_BIN} -m venv ${STACK_ROOT}/.venv || {
    ${PY_BIN} -m pip install --user virtualenv
    ${PY_BIN} -m virtualenv ${STACK_ROOT}/.venv
}
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
echo "      scp -r C:/LumaTrader/INSTITUTIONAL_STACK_V2/code/* <vps-user>@157.151.148.234:${STACK_ROOT}/code/"
echo "      scp -r C:/LumaTrader/INSTITUTIONAL_STACK_V2/LamaScout/* <vps-user>@157.151.148.234:${STACK_ROOT}/LamaScout/"
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

# --- Cross-Sector Opportunity Intel API ---
cat > /etc/systemd/system/luma-intel-api.service << EOF
[Unit]
Description=Luma Cross-Sector Opportunity Intel API
After=network.target

[Service]
Type=simple
User=lumencore
WorkingDirectory=/opt/lumencore/code
Environment="PATH=/opt/lumencore/.venv/bin"
ExecStart=/opt/lumencore/.venv/bin/python -m uvicorn execution.sector_opp_gain_server:app --host 127.0.0.1 --port ${INTEL_API_PORT}
Restart=always
RestartSec=10
StandardOutput=append:/var/log/lumencore/sector-intel.log
StandardError=append:/var/log/lumencore/sector-intel.log

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
systemctl enable lamascout-api lamascout-loop luma-dashboard luma-paper-ticker luma-intel-api

echo "[6/9] Services installed and enabled."

# ------------------------------------------------------------------------------
# 7. NGINX REVERSE PROXY
# ------------------------------------------------------------------------------
echo "[7/9] Configuring nginx for lumen-core.ai..."

mkdir -p /var/www/html
mkdir -p /opt/lumencore/dashboard
systemctl enable --now nginx || true

cat > /etc/nginx/conf.d/lumatrader.conf << 'EOF'
upstream trading_dashboard { server 127.0.0.1:5016; keepalive 32; }
upstream intel_api { server 127.0.0.1:7700; keepalive 32; }
upstream scout_dashboard { server 127.0.0.1:5017; keepalive 32; }
upstream lamascout_api { server 127.0.0.1:8001; keepalive 32; }
upstream luma_gateway { server 127.0.0.1:8787; keepalive 64; }

server {
    listen 80;
    server_name yourdomain.com www.yourdomain.com app.yourdomain.com research.yourdomain.com;
    return 301 https://$host$request_uri;
}

server {
    listen 443 ssl;
    server_name yourdomain.com www.yourdomain.com;

    ssl_certificate     /etc/letsencrypt/live/yourdomain.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/yourdomain.com/privkey.pem;
    include /etc/letsencrypt/options-ssl-nginx.conf;
    ssl_dhparam /etc/letsencrypt/ssl-dhparams.pem;

    location /api/scout/ {
        proxy_pass         http://lamascout_api/;
        proxy_http_version 1.1;
        proxy_set_header   Host              $host;
        proxy_set_header   X-Real-IP         $remote_addr;
        proxy_set_header   X-Forwarded-For   $proxy_add_x_forwarded_for;
        proxy_set_header   X-Forwarded-Proto $scheme;
    }

    location /api/ {
        proxy_pass         http://luma_gateway;
        proxy_http_version 1.1;
        proxy_set_header   Host              $host;
        proxy_set_header   X-Real-IP         $remote_addr;
        proxy_set_header   X-Forwarded-For   $proxy_add_x_forwarded_for;
        proxy_set_header   X-Forwarded-Proto $scheme;
    }

    location /auth/ {
        proxy_pass         http://luma_gateway;
        proxy_http_version 1.1;
        proxy_set_header   Host              $host;
        proxy_set_header   X-Real-IP         $remote_addr;
        proxy_set_header   X-Forwarded-For   $proxy_add_x_forwarded_for;
        proxy_set_header   X-Forwarded-Proto $scheme;
    }

    location /ws/live {
        proxy_pass         http://luma_gateway;
        proxy_http_version 1.1;
        proxy_set_header   Upgrade           $http_upgrade;
        proxy_set_header   Connection        "upgrade";
        proxy_set_header   Host              $host;
        proxy_set_header   X-Real-IP         $remote_addr;
        proxy_set_header   X-Forwarded-For   $proxy_add_x_forwarded_for;
        proxy_set_header   X-Forwarded-Proto $scheme;
        proxy_read_timeout 86400s;
    }

    location = /dashboard {
        return 302 /quant_lab.html;
    }

    location = /dashboard/ {
        return 302 /quant_lab.html;
    }

    location /trading {
        rewrite ^/trading(/.*)$ $1 break;
        proxy_pass         http://trading_dashboard;
        proxy_http_version 1.1;
        proxy_set_header   Host              $host;
        proxy_set_header   X-Real-IP         $remote_addr;
        proxy_set_header   X-Forwarded-For   $proxy_add_x_forwarded_for;
        proxy_set_header   X-Forwarded-Proto $scheme;
        proxy_read_timeout 86400s;
    }

    location /scout {
        rewrite ^/scout(/.*)$ $1 break;
        proxy_pass         http://scout_dashboard;
        proxy_http_version 1.1;
        proxy_set_header   Host              $host;
        proxy_set_header   X-Real-IP         $remote_addr;
        proxy_set_header   X-Forwarded-For   $proxy_add_x_forwarded_for;
        proxy_set_header   X-Forwarded-Proto $scheme;
        proxy_read_timeout 86400s;
    }

    location /intel {
        rewrite ^/intel(/.*)$ $1 break;
        proxy_pass         http://intel_api;
        proxy_http_version 1.1;
        proxy_set_header   Host              $host;
        proxy_set_header   X-Real-IP         $remote_addr;
        proxy_set_header   X-Forwarded-For   $proxy_add_x_forwarded_for;
        proxy_set_header   X-Forwarded-Proto $scheme;
    }

    # Public proof access is curated. Do not expose /opt/lumencore/out as a
    # browsable directory; reviewers should enter through proof_to_pilot.html
    # and hash-verified /data/*.json feeds.
    location = /proof/ {
        return 302 /proof_to_pilot.html;
    }

    location /proof/ {
        return 404;
    }

    location = /evidence/runs {
        return 404;
    }

    location ^~ /evidence/runs/ {
        return 404;
    }

    location /evidence/ {
        alias /opt/lumencore/dashboard/evidence/;
        try_files $uri $uri/ =404;
    }

    # Grant application packets include operator-only form fields. Reviewer-safe
    # grant feeds are published under /data and /dashboard/data instead.
    location ^~ /out/grants/ {
        return 404;
    }

    location /out/ {
        proxy_pass         http://luma_gateway;
        proxy_http_version 1.1;
        proxy_set_header   Host              $host;
        proxy_set_header   X-Real-IP         $remote_addr;
        proxy_set_header   X-Forwarded-For   $proxy_add_x_forwarded_for;
        proxy_set_header   X-Forwarded-Proto $scheme;
    }

    location ~ ^/INSTITUTIONAL_STACK_V2/out/(.*)$ {
        return 302 /out/$1;
    }

    location = /data/sector_energy_evidence_pipeline_latest.json {
        return 302 /out/ops/sector_energy_evidence_pipeline_latest.json;
    }

    location = /data/sector_energy_investor_bridge_latest.json {
        return 302 /out/sector_energy/sector_energy_investor_bridge_latest.json;
    }

    location = /INSTITUTIONAL_STACK_V2/dashboard/data/sector_energy_evidence_pipeline_latest.json {
        return 302 /out/ops/sector_energy_evidence_pipeline_latest.json;
    }

    location = /INSTITUTIONAL_STACK_V2/dashboard/data/sector_energy_investor_bridge_latest.json {
        return 302 /out/sector_energy/sector_energy_investor_bridge_latest.json;
    }

    location / {
        root /opt/lumencore/dashboard;
        index mission_control.html index.html;
        try_files $uri $uri/ @gateway_fallback;
    }

    location @gateway_fallback {
        proxy_pass         http://luma_gateway;
        proxy_http_version 1.1;
        proxy_set_header   Host              $host;
        proxy_set_header   X-Real-IP         $remote_addr;
        proxy_set_header   X-Forwarded-For   $proxy_add_x_forwarded_for;
        proxy_set_header   X-Forwarded-Proto $scheme;
    }
}

server {
    listen 443 ssl;
    server_name app.yourdomain.com;
    ssl_certificate     /etc/letsencrypt/live/yourdomain.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/yourdomain.com/privkey.pem;
    include /etc/letsencrypt/options-ssl-nginx.conf;
    ssl_dhparam /etc/letsencrypt/ssl-dhparams.pem;
    location / {
        return 302 https://yourdomain.com/investor_command_room.html;
    }
}

server {
    listen 443 ssl;
    server_name research.yourdomain.com;
    ssl_certificate     /etc/letsencrypt/live/yourdomain.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/yourdomain.com/privkey.pem;
    include /etc/letsencrypt/options-ssl-nginx.conf;
    ssl_dhparam /etc/letsencrypt/ssl-dhparams.pem;
    location / {
        return 302 https://yourdomain.com/quant_lab.html;
    }
}
EOF

sed -i "s/yourdomain.com/${DOMAIN}/g" /etc/nginx/conf.d/lumatrader.conf

if [ -d /etc/nginx/sites-enabled ]; then
    rm -f /etc/nginx/sites-enabled/lumen-core.ai || true
    rm -f /etc/nginx/sites-enabled/default || true
fi
rm -f /etc/nginx/conf.d/default.conf || true
rm -f /etc/nginx/conf.d/lumen-core.ai.conf || true

nginx -t && systemctl reload nginx

# ------------------------------------------------------------------------------
# 8. SSL CERTIFICATE (Let's Encrypt)
# ------------------------------------------------------------------------------
echo "[8/9] Obtaining SSL certificate for lumen-core.ai..."
echo "      NOTE: DNS must be pointed to 157.151.148.234 BEFORE this runs."
echo ""
echo "      Run this command after DNS propagates:"
echo "      certbot --nginx -d lumen-core.ai -d www.lumen-core.ai -d app.lumen-core.ai -d research.lumen-core.ai --non-interactive --agree-tos -m admin@lumen-core.ai"
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
echo "   intel api        → https://lumen-core.ai/intel/"
echo "   proof artifacts  → https://lumen-core.ai/proof/"
echo "   investor app     → https://${APP_DOMAIN}/"
echo "   research app     → https://${RESEARCH_DOMAIN}/"
echo ""
echo " Next steps:"
echo "   1. Point DNS A record: lumen-core.ai → 157.151.148.234"
echo "   2. SCP your code from Windows (commands shown in step 5 above)"
echo "   3. Run certbot for SSL"
echo "   4. systemctl start luma-paper-ticker lamascout-loop"
echo "   5. systemctl start lamascout-api luma-dashboard luma-intel-api"
echo "======================================================"
