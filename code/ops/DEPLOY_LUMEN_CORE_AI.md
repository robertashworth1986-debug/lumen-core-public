# Deploy lumen-core.ai on VPS (Windows)

## Recommended Path
- Best current path: a fresh Windows VPS with a public IPv4 address.
- Do not use the old Oracle/Linux guide for this stack unless you are ready to refactor Windows-rooted paths across the codebase.
- Assume the old Hetzner box is gone if the account is delinquent; replace it and repoint DNS.

## Fastest Path: One Command
From `C:\LumaTrader\INSTITUTIONAL_STACK_V2\code` on the new VPS:

```powershell
powershell -ExecutionPolicy Bypass -File .\ops\RUN_FRESH_WINDOWS_VPS_ONE_CLICK.ps1 -Domain lumen-core.ai -FastFirstBoot
```

This command:
- installs Python/venv prerequisites,
- runs public-stack bootstrap,
- opens firewall ports 80/443,
- installs and starts Caddy,
- starts dashboard + LamaScout,
- installs startup tasks,
- and skips reconnect/elite optimizer for a faster initial go-live.

After DNS and HTTPS are stable, run full optimization:

```powershell
powershell -ExecutionPolicy Bypass -File .\RUN_ELITE_STACK_OPTIMIZER.ps1
```

## 0) Put the stack on the VPS
- Copy this whole folder to the VPS at `C:\LumaTrader\INSTITUTIONAL_STACK_V2`.
- Keep that exact path. Many scripts still assume it.

## 0.5) Install Python/venv dependencies on the new VPS
Run PowerShell from `C:\LumaTrader\INSTITUTIONAL_STACK_V2\code`:

```powershell
powershell -ExecutionPolicy Bypass -File .\ops\INSTALL_PUBLIC_STACK_PREREQS.ps1
```

This creates `code\.venv` and installs the Python packages needed by the dashboard and LamaScout API.

## 1) DNS
- In your domain DNS provider, create an `A` record:
- Host: `@`
- Value: `<your_new_vps_public_ip>`
- TTL: `300`

## 2) Open firewall ports on VPS
Run PowerShell as admin:

```powershell
New-NetFirewallRule -DisplayName "LumenCore HTTP" -Direction Inbound -Protocol TCP -LocalPort 80 -Action Allow
New-NetFirewallRule -DisplayName "LumenCore HTTPS" -Direction Inbound -Protocol TCP -LocalPort 443 -Action Allow
```

## 3) Launch internal apps
From `C:\LumaTrader\INSTITUTIONAL_STACK_V2\code`:

```powershell
powershell -ExecutionPolicy Bypass -File .\ops\RUN_PUBLIC_STACK.ps1 -RunReconnect -RunEliteOptimizer
```

This starts:
- Institutional dashboard on `127.0.0.1:5016`
- LamaScout API on `127.0.0.1:8000`

### One-shot bootstrap (recommended)
If you want a single command that sets firewall + installs Caddy + writes Caddyfile + starts stack:

```powershell
powershell -ExecutionPolicy Bypass -File .\ops\BOOTSTRAP_PUBLIC_VPS.ps1 -Domain lumen-core.ai -RunReconnect -RunEliteOptimizer -InstallScheduledTasks
```

This must be run in an elevated (Administrator) PowerShell.

Suggested fresh-host order:
1. Copy stack to `C:\LumaTrader\INSTITUTIONAL_STACK_V2`
2. Run `RUN_FRESH_WINDOWS_VPS_ONE_CLICK.ps1`
3. Point the DNS A record to the new public IP
4. Wait for HTTPS issuance, then test the site

## 4) Install Caddy reverse proxy
- Download Caddy for Windows from caddyserver.com
- Put `caddy.exe` in `C:\caddy\`
- Copy `ops\Caddyfile.lumen-core.ai` to `C:\caddy\Caddyfile`

Run Caddy:

```powershell
cd C:\caddy
.\caddy.exe run --config .\Caddyfile
```

Caddy will auto-provision HTTPS for `lumen-core.ai`.

## 5) Persist services across reboot
Use Windows Task Scheduler or NSSM:
- Service 1: `RUN_PUBLIC_STACK.ps1`
- Service 2: `caddy.exe run --config C:\caddy\Caddyfile`

## 6) Verify public endpoints
- `https://lumen-core.ai`
- `https://lumen-core.ai/ui`
- `https://lumen-core.ai/health`

## 7) Investor-safe public mode
Keep these values in config:
- `mode = paper`
- `allow_live_orders = false`

Publish only paper + audit evidence until live TXID runbooks are approved.

## 8) Zero-cost source expansion (high value)
Prioritize free/public sources first:
- FRED, BLS, BEA, Census, NOAA, NASA, USGS, EIA
- MusicBrainz, Wikipedia, Google Trends
- Public status feeds (ISO/RTO grid status pages, outage bulletins where available)

## 9) Weekly credibility loop
- Run elite optimizer daily
- Publish latest scorecard + evidence pack weekly
- Track 4 headline KPIs: realized ROI, max drawdown, walk-forward sharpe, measured $/hr

This gives investors a consistent proof cadence before adding expensive APIs.
