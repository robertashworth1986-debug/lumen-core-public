import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List


SITE_ROOT = Path(__file__).resolve().parents[1]
STACK_ROOT = SITE_ROOT.parent
CONFIG_DIR = STACK_ROOT / "config"
OUT_DIR = STACK_ROOT / "out"
EXEC_DIR = OUT_DIR / "execution"

PUBLIC_DIR = SITE_ROOT / "public"
DATA_DIR = PUBLIC_DIR / "data"


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _read_json(path: Path, default: Any) -> Any:
    if not path.exists():
        return default
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return default


def _read_jsonl(path: Path, limit: int = 100) -> List[Dict[str, Any]]:
    if not path.exists():
        return []
    rows: List[Dict[str, Any]] = []
    try:
        lines = path.read_text(encoding="utf-8", errors="ignore").splitlines()
        for line in lines[-limit:]:
            line = line.strip()
            if not line:
                continue
            try:
                rows.append(json.loads(line))
            except Exception:
                continue
    except Exception:
        return []
    return rows


def _write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def _safe_runtime(runtime_cfg: Dict[str, Any]) -> Dict[str, Any]:
    allowed_keys = {
        "mode",
        "paper_enabled",
        "allow_live_orders",
        "kill_switch",
        "futures_mode",
        "leverage_multiplier",
        "max_open_positions",
        "max_drawdown_pct",
        "max_daily_loss_usd",
        "max_portfolio_heat",
        "max_position_usd",
        "min_position_usd",
        "reserve_usd",
        "base_risk_fraction",
        "capital_aware_ranking_enabled",
        "capital_aware_scan_size",
    }
    return {k: runtime_cfg.get(k) for k in sorted(allowed_keys) if k in runtime_cfg}


def _build_index_html() -> str:
    return """<!doctype html>
<html lang=\"en\">
<head>
  <meta charset=\"utf-8\" />
  <meta name=\"viewport\" content=\"width=device-width, initial-scale=1\" />
  <title>LUMENCORE • Runtime Status</title>
  <style>
    :root { color-scheme: dark; }
    body { margin: 0; font-family: Inter, Segoe UI, Arial, sans-serif; background: #0b1020; color: #e6ecff; }
    .wrap { max-width: 1040px; margin: 0 auto; padding: 24px; }
    h1 { margin: 0 0 8px; font-size: 1.8rem; }
    .muted { color: #a9b4d0; }
    .grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(230px, 1fr)); gap: 12px; margin-top: 16px; }
    .card { background: #141b33; border: 1px solid #273157; border-radius: 12px; padding: 14px; }
    .k { color: #8da3ff; font-size: .85rem; text-transform: uppercase; letter-spacing: .05em; }
    .v { font-size: 1.2rem; margin-top: 6px; font-weight: 700; }
    table { width: 100%; border-collapse: collapse; margin-top: 14px; }
    th, td { text-align: left; padding: 8px; border-bottom: 1px solid #273157; font-size: .92rem; }
    code { background: #1c2547; padding: 2px 6px; border-radius: 6px; }
  </style>
</head>
<body>
  <div class=\"wrap\">
    <h1>LUMENCORE Runtime Dashboard</h1>
    <div class=\"muted\" id=\"buildAt\">Loading build metadata...</div>

    <div class=\"grid\" id=\"cards\"></div>

    <h2>Recent Trades</h2>
    <table>
      <thead><tr><th>Timestamp</th><th>Symbol</th><th>Side</th><th>Status</th><th>P&L</th></tr></thead>
      <tbody id=\"trades\"></tbody>
    </table>

    <h2>Recent Audit Events</h2>
    <table>
      <thead><tr><th>Time</th><th>Event</th><th>Symbol</th><th>Details</th></tr></thead>
      <tbody id=\"audit\"></tbody>
    </table>
  </div>

  <script>
    async function getJSON(path) {
      const res = await fetch(path, { cache: 'no-store' });
      if (!res.ok) throw new Error('Failed: ' + path);
      return await res.json();
    }

    function card(k, v) {
      return `<div class=\"card\"><div class=\"k\">${k}</div><div class=\"v\">${v}</div></div>`;
    }

    (async () => {
      try {
        const [health, runtime, profile, portfolio, trades, audit, build] = await Promise.all([
          getJSON('./data/health.json'),
          getJSON('./data/runtime.json'),
          getJSON('./data/profile.json'),
          getJSON('./data/portfolio.json'),
          getJSON('./data/trades_recent.json'),
          getJSON('./data/audit_recent.json'),
          getJSON('./data/build_info.json'),
        ]);

        document.getElementById('buildAt').innerHTML = `Generated: <code>${build.generated_utc}</code> • Source: <code>${build.stack_root}</code>`;

        const cards = [];
        cards.push(card('Runtime Mode', runtime.mode ?? 'unknown'));
        cards.push(card('Live Orders', String(runtime.allow_live_orders)));
        cards.push(card('Kill Switch', String(runtime.kill_switch)));
        cards.push(card('Active Profile', profile.active_profile ?? 'unknown'));
        cards.push(card('Current Equity', `$${(portfolio.current_equity ?? 0).toFixed(2)}`));
        cards.push(card('Realized P&L', `$${(portfolio.realized_pnl_total ?? 0).toFixed(2)}`));
        cards.push(card('Recent Trades', String((trades.items ?? []).length)));
        cards.push(card('Recent Events', String((audit.items ?? []).length)));
        document.getElementById('cards').innerHTML = cards.join('');

        const tradeRows = (trades.items ?? []).slice(0, 20).map(t => {
          return `<tr>
            <td>${t.timestamp ?? '-'}</td>
            <td>${t.symbol ?? '-'}</td>
            <td>${t.side ?? '-'}</td>
            <td>${t.status ?? '-'}</td>
            <td>${(t.pnl ?? 0).toFixed ? t.pnl.toFixed(2) : (t.pnl ?? '-')}</td>
          </tr>`;
        }).join('');
        document.getElementById('trades').innerHTML = tradeRows || '<tr><td colspan="5">No trades found.</td></tr>';

        const auditRows = (audit.items ?? []).slice(0, 20).reverse().map(e => {
          const payload = e.payload || {};
          return `<tr>
            <td>${e.event_time_utc ?? '-'}</td>
            <td>${e.event_type ?? '-'}</td>
            <td>${payload.symbol ?? '-'}</td>
            <td>${JSON.stringify(payload).slice(0, 120)}</td>
          </tr>`;
        }).join('');
        document.getElementById('audit').innerHTML = auditRows || '<tr><td colspan="4">No audit events found.</td></tr>';
      } catch (err) {
        document.body.insertAdjacentHTML('beforeend', `<pre style=\"color:#ff8a8a;padding:16px\">${err}</pre>`);
      }
    })();
  </script>
</body>
</html>
"""


def main() -> None:
    runtime_cfg = _read_json(CONFIG_DIR / "runtime_control.json", {})
    execution_runtime = _read_json(OUT_DIR / "execution_runtime.json", {})
    profile_state = _read_json(EXEC_DIR / "adaptive_profile_state.json", {})
    portfolio_summary = _read_json(EXEC_DIR / "portfolio_summary.json", {})
    trade_log = _read_json(EXEC_DIR / "trade_log.json", [])
    audit_recent = _read_jsonl(EXEC_DIR / "execution_audit_chain.jsonl", limit=200)

    trade_items = trade_log[-100:] if isinstance(trade_log, list) else []
    latest_trade = trade_items[-1] if trade_items else {}
    latest_event = audit_recent[-1] if audit_recent else {}

    health = {
        "generated_utc": _utc_now(),
        "runtime_mode": runtime_cfg.get("mode", execution_runtime.get("runtime_mode", "unknown")),
        "allow_live_orders": bool(runtime_cfg.get("allow_live_orders", False)),
        "kill_switch": bool(runtime_cfg.get("kill_switch", execution_runtime.get("kill_switch", False))),
        "active_profile": profile_state.get("active_profile", "unknown"),
        "trade_count_recent": len(trade_items),
        "audit_event_count_recent": len(audit_recent),
        "latest_trade": latest_trade,
        "latest_event": latest_event,
    }

    runtime_payload = _safe_runtime(runtime_cfg)
    runtime_payload["execution_runtime"] = execution_runtime

    DATA_DIR.mkdir(parents=True, exist_ok=True)
    _write_json(DATA_DIR / "health.json", health)
    _write_json(DATA_DIR / "runtime.json", runtime_payload)
    _write_json(DATA_DIR / "profile.json", profile_state)
    _write_json(DATA_DIR / "portfolio.json", portfolio_summary)
    _write_json(DATA_DIR / "trades_recent.json", {"items": trade_items})
    _write_json(DATA_DIR / "audit_recent.json", {"items": audit_recent})
    _write_json(
        DATA_DIR / "build_info.json",
        {
            "generated_utc": _utc_now(),
            "site_root": str(SITE_ROOT),
            "stack_root": str(STACK_ROOT),
            "source_paths": {
                "runtime_control": str(CONFIG_DIR / "runtime_control.json"),
                "execution_runtime": str(OUT_DIR / "execution_runtime.json"),
                "profile_state": str(EXEC_DIR / "adaptive_profile_state.json"),
                "portfolio_summary": str(EXEC_DIR / "portfolio_summary.json"),
                "trade_log": str(EXEC_DIR / "trade_log.json"),
                "execution_audit_chain": str(EXEC_DIR / "execution_audit_chain.jsonl"),
            },
        },
    )

    PUBLIC_DIR.mkdir(parents=True, exist_ok=True)
    (PUBLIC_DIR / "index.html").write_text(_build_index_html(), encoding="utf-8")

    print("✅ LUMENCORE site bundle built")
    print(f"   Public dir: {PUBLIC_DIR}")
    print(f"   Data dir:   {DATA_DIR}")


if __name__ == "__main__":
    main()
