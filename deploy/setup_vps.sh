#!/bin/bash
# Run on Oracle VPS as opc user. Idempotent — safe to run multiple times.
set -euo pipefail

echo "=== [1/7] Installing Caddy ==="
if ! command -v caddy >/dev/null 2>&1; then
  sudo dnf install -y 'dnf-command(copr)'
  sudo dnf copr enable -y @caddy/caddy
  sudo dnf install -y caddy
else
  echo "Caddy already installed: $(caddy version | head -1)"
fi

echo "=== [2/7] Creating /var/www/lumen-core ==="
sudo mkdir -p /var/www/lumen-core
sudo chown -R opc:opc /var/www/lumen-core

echo "=== [3/7] Installing landing page ==="
sudo cp /tmp/lumen_index.html /var/www/lumen-core/index.html
sudo chmod 644 /var/www/lumen-core/index.html

echo "=== [4/7] Installing Caddyfile ==="
sudo cp /tmp/Caddyfile /etc/caddy/Caddyfile
sudo chown root:caddy /etc/caddy/Caddyfile
sudo chmod 644 /etc/caddy/Caddyfile

echo "=== [5/7] Opening firewall ports 80 + 443 ==="
sudo firewall-cmd --permanent --add-service=http  || true
sudo firewall-cmd --permanent --add-service=https || true
sudo firewall-cmd --reload
sudo firewall-cmd --list-services

echo "=== [6/7] Opening Oracle iptables (Oracle Linux uses iptables INPUT chain too) ==="
# Oracle Linux ships with iptables rules that block 80/443 even when firewalld allows them.
# Insert allow rules at the top of INPUT chain idempotently.
if ! sudo iptables -C INPUT -p tcp --dport 80 -j ACCEPT 2>/dev/null; then
  sudo iptables -I INPUT 6 -p tcp --dport 80  -j ACCEPT
fi
if ! sudo iptables -C INPUT -p tcp --dport 443 -j ACCEPT 2>/dev/null; then
  sudo iptables -I INPUT 6 -p tcp --dport 443 -j ACCEPT
fi
sudo bash -c 'iptables-save > /etc/sysconfig/iptables' || true

echo "=== [7/7] Restarting Caddy ==="
sudo systemctl enable caddy
sudo systemctl restart caddy
sleep 2
sudo systemctl status caddy --no-pager | head -15

echo
echo "=== DONE ==="
echo "Site root: /var/www/lumen-core"
echo "Caddyfile: /etc/caddy/Caddyfile"
echo
echo "Public IP: $(curl -s ifconfig.me)"
echo "Local probe (will be 200 OK once Caddy comes up):"
curl -sI -o /dev/null -w "  http://localhost  -> HTTP %{http_code}\n" http://localhost/ || true
echo
echo "NOTE: Oracle Cloud also has a Network Security List in the console."
echo "If https://lumen-core.ai still fails after DNS propagates, you'll need to"
echo "add ingress rules for ports 80 and 443 in the Oracle Cloud console:"
echo "  Networking > Virtual Cloud Networks > [your VCN] > Security Lists > Default"
echo "  Add Ingress: Source 0.0.0.0/0, TCP, Destination Port 80"
echo "  Add Ingress: Source 0.0.0.0/0, TCP, Destination Port 443"
