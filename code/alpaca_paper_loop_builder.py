from __future__ import annotations

from pathlib import Path
import os
import json
import hashlib
import math
import statistics
import subprocess
import sys
import tempfile
from datetime import datetime, timezone

import requests

STACK = Path(
    os.environ.get("LUMA_STACK_ROOT", str(Path(__file__).resolve().parent.parent))
).expanduser().resolve()
ROOT = STACK.parent
CODE  = STACK / "code"
CFG   = STACK / "config"
OUT   = STACK / "out"
DASH = Path(
    os.environ.get("LUMA_DASHBOARD_DIR", str(STACK / "dashboard"))
).expanduser().resolve()

for p in [CODE, CFG, OUT, DASH]:
    p.mkdir(parents=True, exist_ok=True)

from execution.append_lock import exclusive_append_lock

CFG_FILE    = CFG / "paper_trader_runtime.json"
ENV_FILE    = CFG / "luma_live_keys.env"
LEDGER_FILE = OUT / "paper_trade_ledger.jsonl"
REAL_LEDGER_FILE = OUT / "paper_trade_real_api_ledger.jsonl"
COLLECTOR_STATE_FILE = OUT / "execution" / "alpaca_activity_collector_state.json"
COLLECTOR_LOCK_FILE = OUT / "execution" / "alpaca_activity_collector.lock"
RUNTIME_FILE= OUT / "paper_trade_runtime.json"
HASH_FILE   = OUT / "paper_trade_chain_of_custody_sha256.json"
EVIDENCE_REPORT_FILE = OUT / "investor_evidence_report.json"
HTML_FILE   = DASH / "alpaca_paper_live_dashboard.html"
RECONCILIATION_SCRIPT = CODE / "ops" / "BUILD_PAPER_LEDGER_RECONCILIATION.py"

def now():
    return datetime.now(timezone.utc).isoformat()

def sha256_file(path: Path):
    if not path.exists():
        return ""
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1024*1024), b""):
            h.update(chunk)
    return h.hexdigest()

def write_json(path, obj):
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, tmp_name = tempfile.mkstemp(prefix=f".{path.name}.", suffix=".tmp", dir=path.parent)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8", newline="\n") as handle:
            json.dump(obj, handle, indent=2, ensure_ascii=True)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(tmp_name, path)
    finally:
        try:
            Path(tmp_name).unlink()
        except FileNotFoundError:
            pass

def append_jsonl(path, obj):
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "a", encoding="utf-8") as f:
        f.write(json.dumps(obj, ensure_ascii=True, separators=(",", ":")) + "\n")
        f.flush()
        os.fsync(f.fileno())


def fill_id_sha256(fill_id: str) -> str:
    return hashlib.sha256(str(fill_id).encode("utf-8")).hexdigest()


def load_fill_id_hashes(path: Path) -> set[str]:
    hashes: set[str] = set()
    if not path.exists():
        return hashes
    try:
        with path.open("r", encoding="utf-8", errors="replace") as handle:
            for raw_line in handle:
                try:
                    row = json.loads(raw_line)
                except json.JSONDecodeError:
                    continue
                if not isinstance(row, dict):
                    continue
                fill_id = str(row.get("fill_id") or "").strip()
                if fill_id:
                    hashes.add(fill_id_sha256(fill_id))
    except OSError:
        return set()
    return hashes


def load_json(path: Path, default):
    if not path.exists():
        return default
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
        return payload
    except Exception:
        return default


def load_jsonl(path: Path, limit: int = 5000) -> list:
    if not path.exists():
        return []
    rows = []
    try:
        lines = path.read_text(encoding="utf-8", errors="ignore").splitlines()
        for line in lines[-max(1, int(limit)):]:
            try:
                payload = json.loads(line)
                if isinstance(payload, dict):
                    rows.append(payload)
            except Exception:
                continue
    except Exception:
        return []
    return rows


def _to_float(value, default: float = 0.0) -> float:
    try:
        return float(value)
    except Exception:
        return float(default)


def _parse_iso_utc(ts: str):
    text = str(ts or "").strip()
    if not text:
        return None
    try:
        return datetime.fromisoformat(text.replace("Z", "+00:00"))
    except Exception:
        return None


def build_investor_evidence_report(state: dict, runtime_payload: dict) -> dict:
    rows = load_jsonl(REAL_LEDGER_FILE, limit=10000)
    snapshots = [r for r in rows if str(r.get("event_type", "")).lower() == "account_snapshot"]
    fills = [r for r in rows if str(r.get("event_type", "")).lower() == "alpaca_fill"]

    equities = [_to_float(r.get("equity_usd", 0.0), 0.0) for r in snapshots]
    returns_pct = []
    for i in range(1, len(equities)):
        prev_eq = max(equities[i - 1], 1e-9)
        curr_eq = equities[i]
        returns_pct.append(((curr_eq - prev_eq) / prev_eq) * 100.0)

    win_periods = sum(1 for value in returns_pct if value > 0)
    loss_periods = sum(1 for value in returns_pct if value < 0)
    flat_periods = sum(1 for value in returns_pct if abs(value) <= 1e-12)
    sampled_periods = len(returns_pct)
    win_rate_pct = ((win_periods / sampled_periods) * 100.0) if sampled_periods else 0.0

    sharpe_proxy = 0.0
    annualized_sharpe_proxy = 0.0
    sample_interval_sec = None
    if sampled_periods >= 2:
        stdev = statistics.pstdev(returns_pct)
        if stdev > 1e-12:
            mean_ret = statistics.mean(returns_pct)
            sharpe_proxy = mean_ret / stdev
            ts_values = [_parse_iso_utc(s.get("timestamp")) for s in snapshots]
            ts_values = [x for x in ts_values if x is not None]
            deltas = []
            for i in range(1, len(ts_values)):
                delta = (ts_values[i] - ts_values[i - 1]).total_seconds()
                if delta > 0:
                    deltas.append(delta)
            if deltas:
                sample_interval_sec = statistics.median(deltas)
                annual_factor = math.sqrt((365.0 * 24.0 * 3600.0) / max(sample_interval_sec, 1.0))
                annualized_sharpe_proxy = sharpe_proxy * annual_factor

    max_drawdown_pct = 0.0
    if equities:
        peak = equities[0]
        for eq in equities:
            if eq > peak:
                peak = eq
            dd_pct = ((peak - eq) / max(peak, 1e-9)) * 100.0
            if dd_pct > max_drawdown_pct:
                max_drawdown_pct = dd_pct

    symbols = sorted({str(r.get("symbol", "")).strip().upper() for r in fills if str(r.get("symbol", "")).strip()})
    side_buy = sum(1 for r in fills if str(r.get("side", "")).lower() == "buy")
    side_sell = sum(1 for r in fills if str(r.get("side", "")).lower() == "sell")

    starting_capital = _to_float(state.get("starting_capital_usd", 100000.0), 100000.0)
    latest_equity = _to_float(state.get("equity_usd", starting_capital), starting_capital)
    paper_profit = _to_float(state.get("paper_profit_usd", latest_equity - starting_capital), latest_equity - starting_capital)
    return_pct_total = ((latest_equity - starting_capital) / max(starting_capital, 1e-9)) * 100.0

    report = {
        "generated_utc": now(),
        "source": "alpaca_paper_real_api",
        "evidence_mode": str(runtime_payload.get("evidence_mode", "unknown") or "unknown"),
        "runtime_error": str(runtime_payload.get("runtime_error", "") or ""),
        "capital": {
            "starting_capital_usd": round(starting_capital, 4),
            "latest_equity_usd": round(latest_equity, 4),
            "paper_profit_usd": round(paper_profit, 4),
            "return_pct_total": round(return_pct_total, 6),
        },
        "fills": {
            "count": int(len(fills)),
            "symbols": symbols,
            "buy_count": int(side_buy),
            "sell_count": int(side_sell),
        },
        "equity_path": {
            "snapshot_count": int(len(snapshots)),
            "sampled_period_returns": int(sampled_periods),
            "win_periods": int(win_periods),
            "loss_periods": int(loss_periods),
            "flat_periods": int(flat_periods),
            "win_rate_pct": round(win_rate_pct, 6),
            "sharpe_proxy": round(sharpe_proxy, 6),
            "annualized_sharpe_proxy": round(annualized_sharpe_proxy, 6),
            "max_drawdown_pct": round(max_drawdown_pct, 6),
            "median_sample_interval_sec": None if sample_interval_sec is None else round(sample_interval_sec, 6),
        },
        "files": {
            "real_ledger": str(REAL_LEDGER_FILE),
            "state": str(COLLECTOR_STATE_FILE),
            "runtime": str(RUNTIME_FILE),
        },
    }
    return report

def load_cfg():
    if CFG_FILE.exists():
        payload = load_json(CFG_FILE, {})
        if isinstance(payload, dict):
            return payload
    cfg = {
        "starting_capital_usd": 100000.0,
        "loop_seconds": 300,
        "symbols": ["SPY","QQQ","NVDA","MSFT","AAPL","AMD","TSLA","META"],
        "paper_enabled": True,
        "alpaca_evidence_mode": "real_api",
        "alpaca_activity_page_size": 100,
    }
    write_json(CFG_FILE, cfg)
    return cfg


def load_env_keys() -> dict:
    keys = {}
    if not ENV_FILE.exists():
        return keys
    try:
        for line in ENV_FILE.read_text(encoding="utf-8", errors="ignore").splitlines():
            row = str(line or "").strip()
            if not row or row.startswith("#") or "=" not in row:
                continue
            k, v = row.split("=", 1)
            keys[k.strip()] = v.strip()
    except Exception:
        return {}
    return keys


def _pick_first(*values):
    for value in values:
        text = str(value or "").strip()
        if text:
            return text
    return ""


def resolve_alpaca_credentials(cfg: dict) -> dict:
    env_file_keys = load_env_keys()
    api_key = _pick_first(
        os.environ.get("ALPACA_API_KEY"),
        os.environ.get("APCA_API_KEY_ID"),
        env_file_keys.get("ALPACA_API_KEY"),
        env_file_keys.get("APCA_API_KEY_ID"),
    )
    api_secret = _pick_first(
        os.environ.get("ALPACA_API_SECRET"),
        os.environ.get("APCA_API_SECRET_KEY"),
        env_file_keys.get("ALPACA_API_SECRET"),
        env_file_keys.get("APCA_API_SECRET_KEY"),
    )
    base_url = _pick_first(
        cfg.get("alpaca_base_url"),
        os.environ.get("ALPACA_PAPER_BASE_URL"),
        os.environ.get("ALPACA_BASE_URL"),
        os.environ.get("ALPACA_TRADING_BASE_URL"),
        env_file_keys.get("ALPACA_BASE_URL"),
        env_file_keys.get("ALPACA_TRADING_BASE_URL"),
        "https://paper-api.alpaca.markets",
    ).rstrip("/")
    return {
        "api_key": api_key,
        "api_secret": api_secret,
        "base_url": base_url,
    }


def alpaca_get(session: requests.Session, base_url: str, endpoint: str, params: dict | None = None) -> tuple[bool, object]:
    try:
        response = session.get(f"{base_url}{endpoint}", params=params or {}, timeout=20)
        if response.status_code >= 400:
            return False, {
                "status_code": response.status_code,
                "body": response.text[:800],
            }
        return True, response.json()
    except Exception as exc:
        return False, {
            "error": str(exc),
        }

cfg = load_cfg()
state_raw = load_json(COLLECTOR_STATE_FILE, {})
state = state_raw if isinstance(state_raw, dict) else {}

starting_capital = float(cfg.get("starting_capital_usd", 100000.0) or 100000.0)
state.setdefault("generated_utc", now())
state.setdefault("starting_capital_usd", starting_capital)
state.setdefault("equity_usd", float(state.get("starting_capital_usd", starting_capital) or starting_capital))
state.setdefault("cash_usd", float(state.get("equity_usd", starting_capital) or starting_capital))
state.setdefault("paper_profit_usd", 0.0)
state.setdefault("trade_count", 0)
state.setdefault("win_count", 0)
state.setdefault("loss_count", 0)
state.setdefault("last_symbol", None)
state.setdefault("last_side", None)
state.setdefault("seen_fill_id_sha256", [])

credentials = resolve_alpaca_credentials(cfg)
api_key = credentials["api_key"]
api_secret = credentials["api_secret"]
base_url = credentials["base_url"]
paper_enabled = bool(cfg.get("paper_enabled", True))

runtime_error = ""
account_payload = {}
fills_payload = []
new_fills = []

if paper_enabled and api_key and api_secret:
    session = requests.Session()
    session.headers.update(
        {
            "APCA-API-KEY-ID": api_key,
            "APCA-API-SECRET-KEY": api_secret,
        }
    )

    account_ok, account_data = alpaca_get(session, base_url, "/v2/account")
    if account_ok and isinstance(account_data, dict):
        account_payload = account_data
    else:
        runtime_error = f"account_fetch_failed:{account_data}"

    page_size = int(cfg.get("alpaca_activity_page_size", 100) or 100)
    fill_endpoints = [
        ("/v2/account/activities", {"activity_types": "FILL", "direction": "desc", "page_size": page_size}),
        ("/v2/account/activities/FILL", {"direction": "desc", "page_size": page_size}),
    ]
    fill_err = None
    for endpoint, params in fill_endpoints:
        ok, payload = alpaca_get(session, base_url, endpoint, params)
        if ok and isinstance(payload, list):
            fills_payload = payload
            fill_err = None
            break
        fill_err = payload
    if fill_err and not fills_payload:
        runtime_error = runtime_error or f"fill_fetch_failed:{fill_err}"

    # One coordinator lock makes the read-dedupe-append checkpoint atomic
    # across duplicate launchers. Raw fill identifiers remain only in the
    # private ledgers; the checkpoint stores one-way hashes.
    with exclusive_append_lock(
        COLLECTOR_LOCK_FILE,
        timeout_seconds=10.0,
        stale_after_seconds=60.0,
    ):
        local_seen = load_fill_id_hashes(LEDGER_FILE)
        real_seen = load_fill_id_hashes(REAL_LEDGER_FILE)
        persisted_seen = {
            str(value).strip()
            for value in (state.get("seen_fill_id_sha256") or [])
            if str(value).strip()
        }
        all_seen = local_seen | real_seen | persisted_seen

        for fill in reversed(fills_payload):
            if not isinstance(fill, dict):
                continue
            fill_id = str(fill.get("id", "") or fill.get("activity_id", "") or "").strip()
            if not fill_id:
                continue
            fill_hash = fill_id_sha256(fill_id)
            qty = float(fill.get("qty", 0.0) or 0.0)
            price = float(fill.get("price", 0.0) or 0.0)
            side = str(fill.get("side", "") or "").lower()
            event = {
                "timestamp": str(fill.get("transaction_time", fill.get("date", now()))),
                "event_type": "alpaca_fill",
                "mode": "ALPACA_PAPER",
                "fill_id": fill_id,
                "symbol": str(fill.get("symbol", "") or ""),
                "side": side,
                "qty": qty,
                "price": price,
                "net_amount_usd": qty * price,
                "order_id": str(fill.get("order_id", "") or ""),
                "source": "alpaca_api",
            }
            appended = False
            if fill_hash not in local_seen:
                append_jsonl(LEDGER_FILE, event)
                local_seen.add(fill_hash)
                appended = True
            if fill_hash not in real_seen:
                append_jsonl(REAL_LEDGER_FILE, event)
                real_seen.add(fill_hash)
                appended = True
            if appended:
                new_fills.append(event)
            all_seen.add(fill_hash)

        if account_payload:
            equity = float(account_payload.get("equity", state.get("equity_usd", starting_capital)) or starting_capital)
            cash = float(account_payload.get("cash", state.get("cash_usd", equity)) or equity)
            state["equity_usd"] = round(equity, 2)
            state["cash_usd"] = round(cash, 2)
            state["paper_profit_usd"] = round(equity - float(state.get("starting_capital_usd", starting_capital) or starting_capital), 2)

        if new_fills:
            latest = new_fills[-1]
            state["last_symbol"] = latest.get("symbol")
            state["last_side"] = latest.get("side")

        state["trade_count"] = int(len(all_seen))
        state["seen_fill_id_sha256"] = sorted(all_seen)[-5000:]

        snapshot_event = {
            "timestamp": now(),
            "event_type": "account_snapshot",
            "mode": "ALPACA_PAPER",
            "source": "alpaca_api",
            "equity_usd": float(state.get("equity_usd", 0.0) or 0.0),
            "cash_usd": float(state.get("cash_usd", 0.0) or 0.0),
            "paper_profit_usd": float(state.get("paper_profit_usd", 0.0) or 0.0),
            "trade_count": int(state.get("trade_count", 0) or 0),
        }
        append_jsonl(REAL_LEDGER_FILE, snapshot_event)
else:
    runtime_error = "alpaca_credentials_missing_or_paper_disabled"

write_json(COLLECTOR_STATE_FILE, state)

reconciliation_status = "NOT_RUN"
if RECONCILIATION_SCRIPT.exists():
    try:
        reconciliation_proc = subprocess.run(
            [sys.executable, str(RECONCILIATION_SCRIPT)],
            cwd=str(CODE),
            capture_output=True,
            text=True,
            timeout=180,
            check=False,
        )
        reconciliation_status = "PASS" if reconciliation_proc.returncode == 0 else "FAIL"
    except (OSError, subprocess.SubprocessError):
        reconciliation_status = "FAIL"

runtime_payload = {
    "generated_utc": now(),
    "paper_enabled": paper_enabled,
    "evidence_mode": "real_api",
    "alpaca_key_present": bool(api_key),
    "alpaca_secret_present": bool(api_secret),
    "alpaca_base_url": base_url,
    "equity_usd": float(state.get("equity_usd", 0.0) or 0.0),
    "paper_profit_usd": float(state.get("paper_profit_usd", 0.0) or 0.0),
    "trade_count": int(state.get("trade_count", 0) or 0),
    "wins": int(state.get("win_count", 0) or 0),
    "losses": int(state.get("loss_count", 0) or 0),
    "last_symbol": state.get("last_symbol"),
    "last_side": state.get("last_side"),
    "new_fill_events": int(len(new_fills)),
    "ledger_reconciliation_status": reconciliation_status,
    "runtime_error": runtime_error,
}
write_json(RUNTIME_FILE, runtime_payload)

evidence_report = build_investor_evidence_report(state, runtime_payload)
write_json(EVIDENCE_REPORT_FILE, evidence_report)

write_json(HASH_FILE, {
    "generated_utc": now(),
    "files": [
        {"path": str(LEDGER_FILE), "sha256": sha256_file(LEDGER_FILE)},
        {"path": str(REAL_LEDGER_FILE), "sha256": sha256_file(REAL_LEDGER_FILE) if REAL_LEDGER_FILE.exists() else ""},
        {"path": str(COLLECTOR_STATE_FILE), "sha256": sha256_file(COLLECTOR_STATE_FILE)},
        {"path": str(RUNTIME_FILE), "sha256": sha256_file(RUNTIME_FILE)},
        {"path": str(EVIDENCE_REPORT_FILE), "sha256": sha256_file(EVIDENCE_REPORT_FILE) if EVIDENCE_REPORT_FILE.exists() else ""}
    ]
})

runtime = load_json(RUNTIME_FILE, {})
html = f"""<!doctype html>
<html>
<head>
<meta charset="utf-8">
<title>LumenCore Alpaca Paper Live Dashboard</title>
<style>
body{{font-family:Segoe UI,Arial,sans-serif;background:#0b1020;color:#eaf2ff;margin:0;padding:24px}}
.grid{{display:grid;grid-template-columns:repeat(4,1fr);gap:14px}}
.card{{background:#121a30;border:1px solid #233155;border-radius:16px;padding:16px}}
.label{{font-size:12px;color:#8ea4c8;text-transform:uppercase;letter-spacing:.08em}}
.value{{font-size:28px;font-weight:700;margin-top:8px}}
.sub{{margin-top:8px;color:#bed0ea}}
</style>
</head>
<body>
<h1>LumenCore — Alpaca Paper Live Dashboard</h1>
<p class="sub">Real Alpaca paper evidence collector (account + fill activity), with chain-of-custody hashes.</p>
<div class="grid">
    <div class="card"><div class="label">Evidence mode</div><div class="value">{runtime.get("evidence_mode", "unknown")}</div></div>
  <div class="card"><div class="label">Starting capital</div><div class="value">${state["starting_capital_usd"]:,.2f}</div></div>
  <div class="card"><div class="label">Current equity</div><div class="value">${state["equity_usd"]:,.2f}</div></div>
  <div class="card"><div class="label">Paper profit</div><div class="value">${state["paper_profit_usd"]:,.2f}</div></div>
    <div class="card"><div class="label">Sharpe proxy</div><div class="value">{evidence_report.get("equity_path",{}).get("sharpe_proxy",0.0)}</div></div>
  <div class="card"><div class="label">Trades</div><div class="value">{state["trade_count"]}</div></div>
  <div class="card"><div class="label">Wins</div><div class="value">{state["win_count"]}</div></div>
  <div class="card"><div class="label">Losses</div><div class="value">{state["loss_count"]}</div></div>
  <div class="card"><div class="label">Last symbol</div><div class="value">{state["last_symbol"]}</div></div>
  <div class="card"><div class="label">Last side</div><div class="value">{state["last_side"]}</div></div>
    <div class="card"><div class="label">New fills (last run)</div><div class="value">{runtime.get("new_fill_events", 0)}</div></div>
</div>
<p class="sub" style="margin-top:18px">Runtime error: {runtime.get("runtime_error", "")}</p>
<p class="sub" style="margin-top:18px">Proof files: paper_trade_real_api_ledger.jsonl, investor_evidence_report.json, alpaca_activity_collector_state.json, paper_trade_runtime.json, paper_trade_chain_of_custody_sha256.json</p>
</body>
</html>
"""
HTML_FILE.write_text(html, encoding="utf-8")

print("WROTE:", LEDGER_FILE)
print("WROTE:", COLLECTOR_STATE_FILE)
print("WROTE:", RUNTIME_FILE)
print("WROTE:", HASH_FILE)
print("WROTE:", HTML_FILE)
