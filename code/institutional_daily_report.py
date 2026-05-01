import hashlib
import json
import os
from datetime import datetime, timezone
from pathlib import Path

import requests

ROOT = Path(r"C:\LumaTrader\INSTITUTIONAL_STACK_V2")
OUT = ROOT / "out"
EXEC_OUT = OUT / "execution"
CONFIG = ROOT / "config"

INVESTOR_EVIDENCE_FILE = OUT / "investor_evidence_report.json"
STATUS_FILE = EXEC_OUT / "alpaca_paper_status.json"
STATE_FILE = OUT / "paper_trade_state.json"
LEDGER_FILE = OUT / "paper_trade_ledger.jsonl"

REPORT_JSON = OUT / "institutional_daily_report.json"
REPORT_CSV = OUT / "institutional_daily_report.csv"
REPORT_HASH = OUT / "institutional_daily_report_sha256.json"


def now_utc() -> str:
    return datetime.now(timezone.utc).isoformat()


def load_json(path: Path, default):
    try:
        if path.exists():
            return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        pass
    return default


def load_jsonl(path: Path) -> list[dict]:
    rows = []
    if not path.exists():
        return rows
    try:
        with path.open("r", encoding="utf-8", errors="ignore") as handle:
            for line in handle:
                line = line.strip()
                if not line:
                    continue
                try:
                    payload = json.loads(line)
                    if isinstance(payload, dict):
                        rows.append(payload)
                except Exception:
                    continue
    except Exception:
        return []
    return rows


def parse_iso_ts(raw: str) -> float:
    text = str(raw or "").strip()
    if not text:
        return 0.0
    text = text.replace("Z", "+00:00")
    try:
        return datetime.fromisoformat(text).timestamp()
    except Exception:
        return 0.0


def load_api_keys() -> tuple[str, str]:
    env = {}
    env_file = CONFIG / "luma_live_keys.env"
    if env_file.exists():
        for raw in env_file.read_text(encoding="utf-8", errors="ignore").splitlines():
            line = raw.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            k, v = line.split("=", 1)
            env[k.strip()] = v.strip()

    key = (
        os.environ.get("ALPACA_API_KEY")
        or os.environ.get("APCA_API_KEY_ID")
        or env.get("ALPACA_API_KEY")
        or env.get("APCA_API_KEY_ID")
        or ""
    )
    secret = (
        os.environ.get("ALPACA_API_SECRET")
        or os.environ.get("APCA_API_SECRET_KEY")
        or env.get("ALPACA_API_SECRET")
        or env.get("APCA_API_SECRET_KEY")
        or ""
    )
    return str(key), str(secret)


def fetch_spy_change_pct() -> float | None:
    key, secret = load_api_keys()
    if not key or not secret:
        return None

    url = "https://data.alpaca.markets/v2/stocks/snapshots"
    headers = {
        "APCA-API-KEY-ID": key,
        "APCA-API-SECRET-KEY": secret,
    }
    try:
        resp = requests.get(url, params={"symbols": "SPY"}, headers=headers, timeout=10)
        resp.raise_for_status()
        payload = resp.json() or {}
        snap = (payload.get("snapshots") or {}).get("SPY") or {}
        daily = snap.get("dailyBar") or {}
        prev = snap.get("prevDailyBar") or {}
        close = float(daily.get("c") or 0.0)
        prev_close = float(prev.get("c") or 0.0)
        if close <= 0 or prev_close <= 0:
            return None
        return ((close / prev_close) - 1.0) * 100.0
    except Exception:
        return None


def build_report() -> dict:
    evidence = load_json(INVESTOR_EVIDENCE_FILE, {})
    status = load_json(STATUS_FILE, {})
    state = load_json(STATE_FILE, {})
    ledger = load_jsonl(LEDGER_FILE)

    capital = evidence.get("capital") or {}
    account = status.get("account") or {}
    execution_meta = status.get("execution_meta") or {}

    equity = float(account.get("equity") or state.get("equity_usd") or 0.0)
    start_capital = float(capital.get("starting_capital_usd") or 100000.0)
    pnl_total = equity - start_capital
    return_total_pct = (pnl_total / start_capital * 100.0) if start_capital > 0 else 0.0

    fills = evidence.get("fills") or {}
    eq_path = evidence.get("equity_path") or {}

    now_ts = datetime.now(timezone.utc).timestamp()
    recent_60m = [
        row
        for row in ledger
        if now_ts - parse_iso_ts(row.get("timestamp", "")) <= 3600
    ]

    opens_60m = [row for row in recent_60m if str(row.get("action", "")).lower() == "open"]
    closes_60m = [row for row in recent_60m if str(row.get("action", "")).lower() == "close"]

    gross_notional_60m = 0.0
    for row in recent_60m:
        notional = float(row.get("notional_usd") or 0.0)
        if notional > 0:
            gross_notional_60m += notional

    spy_change_pct = fetch_spy_change_pct()
    excess_vs_spy_pct = None
    if spy_change_pct is not None:
        excess_vs_spy_pct = return_total_pct - spy_change_pct

    report = {
        "generated_utc": now_utc(),
        "as_of_status_utc": status.get("generated_utc", ""),
        "account": {
            "starting_capital_usd": start_capital,
            "equity_usd": round(equity, 2),
            "pnl_total_usd": round(pnl_total, 2),
            "return_total_pct": round(return_total_pct, 4),
            "open_positions": int(len(status.get("positions") or [])),
            "cash_usd": float(account.get("cash") or 0.0),
            "buying_power_usd": float(account.get("buying_power") or 0.0),
        },
        "risk": {
            "max_drawdown_pct": float(eq_path.get("max_drawdown_pct") or 0.0),
            "drawdown_from_peak_pct": float(execution_meta.get("drawdown_from_peak_pct") or 0.0),
            "risk_off_mode": bool(execution_meta.get("risk_off_mode", False)),
            "entry_pause_active": bool(execution_meta.get("entry_pause_active", False)),
            "entry_pause_until_ts": float(execution_meta.get("entry_pause_until_ts") or 0.0),
        },
        "performance": {
            "fills_count": int(fills.get("count") or 0),
            "buy_count": int(fills.get("buy_count") or 0),
            "sell_count": int(fills.get("sell_count") or 0),
            "win_rate_pct": float(eq_path.get("win_rate_pct") or 0.0),
            "sharpe_proxy": float(eq_path.get("sharpe_proxy") or 0.0),
            "annualized_sharpe_proxy": float(eq_path.get("annualized_sharpe_proxy") or 0.0),
        },
        "execution_flow_60m": {
            "events": int(len(recent_60m)),
            "opens": int(len(opens_60m)),
            "closes": int(len(closes_60m)),
            "gross_notional_usd": round(gross_notional_60m, 2),
        },
        "selection": {
            "status_note": str(status.get("status_note") or ""),
            "top_candidate_symbol": (status.get("top_candidate") or {}).get("symbol"),
            "top_candidate_score": float(((status.get("top_candidate") or {}).get("score") or 0.0)),
            "top_candidate_edge_bps": float(((status.get("top_candidate") or {}).get("edge_bps") or 0.0)),
            "scan_limit": int(execution_meta.get("snapshot_scan_limit") or 0),
            "universe_total": int(execution_meta.get("symbol_universe_total") or 0),
        },
        "benchmark": {
            "spy_day_change_pct": None if spy_change_pct is None else round(spy_change_pct, 4),
            "excess_return_vs_spy_pct": None if excess_vs_spy_pct is None else round(excess_vs_spy_pct, 4),
        },
        "artifacts": {
            "status_file": str(STATUS_FILE),
            "state_file": str(STATE_FILE),
            "evidence_file": str(INVESTOR_EVIDENCE_FILE),
            "ledger_file": str(LEDGER_FILE),
        },
    }
    return report


def write_report(report: dict) -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    REPORT_JSON.write_text(json.dumps(report, indent=2), encoding="utf-8")

    csv_lines = [
        "generated_utc,equity_usd,pnl_total_usd,return_total_pct,open_positions,drawdown_from_peak_pct,risk_off_mode,entry_pause_active,fills_count,win_rate_pct,sharpe_proxy,events_60m,opens_60m,closes_60m,gross_notional_60m,spy_day_change_pct,excess_return_vs_spy_pct",
        (
            f"{report.get('generated_utc','')},"
            f"{report['account']['equity_usd']},"
            f"{report['account']['pnl_total_usd']},"
            f"{report['account']['return_total_pct']},"
            f"{report['account']['open_positions']},"
            f"{report['risk']['drawdown_from_peak_pct']},"
            f"{str(report['risk']['risk_off_mode']).lower()},"
            f"{str(report['risk']['entry_pause_active']).lower()},"
            f"{report['performance']['fills_count']},"
            f"{report['performance']['win_rate_pct']},"
            f"{report['performance']['sharpe_proxy']},"
            f"{report['execution_flow_60m']['events']},"
            f"{report['execution_flow_60m']['opens']},"
            f"{report['execution_flow_60m']['closes']},"
            f"{report['execution_flow_60m']['gross_notional_usd']},"
            f"{'' if report['benchmark']['spy_day_change_pct'] is None else report['benchmark']['spy_day_change_pct']},"
            f"{'' if report['benchmark']['excess_return_vs_spy_pct'] is None else report['benchmark']['excess_return_vs_spy_pct']}"
        ),
    ]
    REPORT_CSV.write_text("\n".join(csv_lines) + "\n", encoding="utf-8")

    hash_payload = {
        "generated_utc": now_utc(),
        "files": {},
    }
    for path in [REPORT_JSON, REPORT_CSV]:
        digest = hashlib.sha256(path.read_bytes()).hexdigest()
        hash_payload["files"][str(path)] = {
            "sha256": digest,
            "bytes": path.stat().st_size,
        }
    REPORT_HASH.write_text(json.dumps(hash_payload, indent=2), encoding="utf-8")


def main() -> None:
    report = build_report()
    write_report(report)
    print("INSTITUTIONAL DAILY REPORT WRITTEN")
    print(REPORT_JSON)
    print(REPORT_CSV)
    print(REPORT_HASH)


if __name__ == "__main__":
    main()
