# VPS Domain and Dashboard Recovery

Date: 2026-06-19

## Findings

- `lumen-core.ai` resolves to `157.151.148.234`.
- Public HTTPS is reachable through nginx.
- `/`, `/health`, `/api/snapshot`, `/kraken_execution_dashboard.html`,
  `/mission_control.html`, `/quant_lab.html`, `/grants.html`, `/forecast.html`,
  and `/evidence/` returned HTTP 200.
- `/api/live_status.json`, `/api/federal_brief.json`,
  `/api/evidence_summary.json`, `/api/executor_heartbeat.json`, and
  `/agent_approval_hub.html` returned 404 before the local compatibility patch.
- `/health` reported `status=degraded` because artifact heartbeats were stale.
- SSH initially connected, then became unreachable on port 22.
- The VPS root filesystem reported 100% usage with only about 20 KB free.
- The largest observed file was
  `/opt/lumencore/out/execution/multi_exchange_paper_ticker_ledger.jsonl`
  at about 9.8 GB.

## 2026-06-19 Recheck

- `GET /health` and `GET /api/snapshot` returned HTTP 200.
- `/api/live_status.json`, `/api/federal_brief.json`,
  `/api/evidence_summary.json`, `/api/executor_heartbeat.json`, and
  `/agent_approval_hub.html` still returned 404 because the compatibility
  patch was not yet deployed.
- Port 22 was reachable again, but the local `lumen-vps` identity and the
  earlier `ssh-key-2026-04-23.key` identity were rejected with public-key
  authentication failure.
- Deployment remains blocked until a valid SSH user/key or provider console
  shell is available.

## Local Repairs Added

- `code/luma_experience_gateway.py` now exposes compatibility feeds for the
  legacy JSON endpoints expected by dashboards and GitHub cards.
- `dashboard/agent_approval_hub.html` was restored from archive to the public
  dashboard surface.
- `code/multi_exchange_paper_ticker.py` now bounds the noisy cycle-status JSONL
  ledger with an environment-configurable cap:
  - `LUMA_PAPER_TICKER_LEDGER_MAX_BYTES`, default 64 MB.
  - `LUMA_PAPER_TICKER_LEDGER_TAIL_BYTES`, default 8 MB.

## Recovery Commands

Run only after SSH is reachable. These commands preserve a recent compressed
tail of the runaway ledger, then truncate the oversized source file so the
running services can write heartbeats again.

```bash
sudo journalctl --vacuum-size=50M
sudo find /var/log/lumencore -type f -size +20M -name "*.log" -exec truncate -s 0 {} \;

LEDGER=/opt/lumencore/out/execution/multi_exchange_paper_ticker_ledger.jsonl
STAMP=$(date -u +%Y%m%dT%H%M%SZ)
sudo mkdir -p /opt/lumencore/out/archive/runtime_recovery_$STAMP
sudo tail -n 200000 "$LEDGER" | gzip -9 | sudo tee \
  /opt/lumencore/out/archive/runtime_recovery_$STAMP/multi_exchange_paper_ticker_ledger_tail.jsonl.gz >/dev/null
sudo truncate -s 0 "$LEDGER"
df -h /
```

Then deploy or restart after free space is visible:

```bash
sudo systemctl restart luma-gateway luma-dashboard-refresh luma-paper-ticker luma-symbol-awareness luma-kraken-history
curl -fsS http://127.0.0.1:8787/health
curl -fsS http://127.0.0.1:8787/api/snapshot
```

## Claim Boundary

These checks verify public endpoint reachability and local remediation logic.
They do not prove that all live artifact producers are fresh until the VPS disk
is recovered, services are restarted, and `/health` reports fresh artifacts.
