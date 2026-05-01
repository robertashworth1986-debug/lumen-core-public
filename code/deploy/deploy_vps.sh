#!/bin/bash
# ============================================================
#  LumaTrader VPS Deployment Script
#  Run once on a fresh Ubuntu/Debian VPS to set up the portal
#
#  Usage:
#    chmod +x deploy_vps.sh
#    sudo ./deploy_vps.sh
# ============================================================
set -e

DOMAIN="yourdomain.com"           # ← replace with your domain
DASHBOARD_SRC="/opt/lumatrader/dashboard"
WWW_ROOT="/var/www/lumatrader"
NGINX_SITE="/etc/nginx/sites-available/lumatrader"

echo "==> Installing nginx..."
apt-get update -qq
apt-get install -y nginx certbot python3-certbot-nginx

echo "==> Creating web root at $WWW_ROOT"
mkdir -p "$WWW_ROOT"

echo "==> Copying portal landing page..."
cp "$DASHBOARD_SRC/index.html"                  "$WWW_ROOT/index.html"
cp "$DASHBOARD_SRC/institutional_crypto_paper_dashboard.html" \
   "$WWW_ROOT/trading.html" 2>/dev/null || true
cp "$DASHBOARD_SRC/lamascout_dashboard.html"    "$WWW_ROOT/scout.html"   2>/dev/null || true
cp "$DASHBOARD_SRC/infra_audit_dashboard.html"  "$WWW_ROOT/audit.html"   2>/dev/null || true

echo "==> Installing nginx config..."
cp "$(dirname "$0")/nginx/lumatrader.conf" "$NGINX_SITE"
sed -i "s/yourdomain.com/$DOMAIN/g" "$NGINX_SITE"
ln -sf "$NGINX_SITE" /etc/nginx/sites-enabled/lumatrader
rm -f /etc/nginx/sites-enabled/default

echo "==> Testing nginx config..."
nginx -t

echo "==> Reloading nginx..."
systemctl reload nginx

echo ""
echo "==> Portal live at http://$DOMAIN"
echo ""
echo "Next: run certbot for HTTPS:"
echo "  sudo certbot --nginx -d $DOMAIN -d www.$DOMAIN"
echo ""
echo "After certbot, update /etc/nginx/sites-available/lumatrader"
echo "and uncomment the HTTPS listen + SSL certificate lines."
echo ""
echo "Start all three Panel services on the VPS:"
echo "  python -m panel serve .../lamascout_dashboard.py     --port 5017 --address 127.0.0.1 &"
echo "  python -m panel serve .../build_institutional_crypto_paper_dashboard.py --port 5016 --address 127.0.0.1 &"
echo "  uvicorn execution.sector_opp_gain_server:app         --port 7700 --host 127.0.0.1 &"
