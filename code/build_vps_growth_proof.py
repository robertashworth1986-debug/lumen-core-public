from __future__ import annotations

import base64
import hashlib
import hmac
import json
import math
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional
from urllib.parse import urlencode

try:
    import requests
except Exception:
    requests = None

ROOT = Path(__file__).resolve().parents[1]
OUT_EXEC = ROOT / "out" / "execution"
DASH = ROOT / "dashboard"

EVENT_SOURCES = [
    ROOT / "execution_events.jsonl",
    OUT_EXEC / "execution_events.jsonl",
    ROOT / "out" / "execution_events.jsonl",
]

TRADE_LOG_SOURCES = [
    OUT_EXEC / "trade_log.json",
    ROOT / "trade_log.json",
]

LEDGER_SOURCES = [
    OUT_EXEC / "live_trade_ledger.jsonl",
    ROOT / "out" / "execution" / "live_trade_ledger.jsonl",
]

BALANCE_SOURCES = [
    OUT_EXEC / "live_balance_snapshot.json",
    OUT_EXEC / "micro_kraken_balance.json",
]

HEARTBEAT_SOURCES = [
    OUT_EXEC / "live_executor_heartbeat.json",
    OUT_EXEC / "live_engine_heartbeat.json",
]

KRAKEN_KEY_SOURCES = [
    ROOT / "config" / "luma_live_keys.env",
    ROOT / "config" / "live_keys.env",
    ROOT / "config" / "keys.env",
    ROOT / "code" / "execution" / "config" / "luma_live_keys.env",
    ROOT / "code" / "execution" / "config" / "live_keys.env",
]

MAX_RECON_TXIDS = 20

OUTPUT_JSON = OUT_EXEC / "vps_growth_proof.json"
OUTPUT_MD = OUT_EXEC / "vps_growth_proof.md"
OUTPUT_HASH = OUT_EXEC / "vps_growth_proof_sha256.json"
OUTPUT_HISTORY = OUT_EXEC / "vps_growth_proof_history.jsonl"
OUTPUT_DASH_JSON = DASH / "data" / "vps_growth_proof.json"
CONTROLLER_STATUS_JSON = OUT_EXEC / "vps_growth_controller_status.json"
OUTPUT_DASH_CONTROLLER_JSON = DASH / "data" / "vps_growth_controller_status.json"


def now_utc() -> str:
    return datetime.now(timezone.utc).isoformat()


def parse_dt(value: Any) -> Optional[datetime]:
    if value is None:
        return None
    raw = str(value).strip()
    if not raw:
        return None
    try:
        cleaned = raw.replace("Z", "+00:00")
        dt = datetime.fromisoformat(cleaned)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.astimezone(timezone.utc)
    except Exception:
        return None


def safe_float(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except Exception:
        return default


def read_json(path: Path, default: Any) -> Any:
    try:
        if path.exists():
            return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        pass
    return default


def pick_first_existing(paths: Iterable[Path]) -> Optional[Path]:
    for p in paths:
        if p.exists():
            return p
    return None


def unique_ordered(values: Iterable[Any]) -> List[str]:
    out: List[str] = []
    seen: set[str] = set()
    for raw in values:
        token = str(raw).strip()
        if not token or token in seen:
            continue
        seen.add(token)
        out.append(token)
    return out


def load_jsonl_rows(paths: Iterable[Path]) -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []
    seen: set[str] = set()
    for path in paths:
        if not path.exists():
            continue
        for line in path.read_text(encoding="utf-8", errors="ignore").splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                row = json.loads(line)
            except Exception:
                continue
            if not isinstance(row, dict):
                continue
            try:
                key = json.dumps(row, sort_keys=True)
            except Exception:
                key = str(row)
            if key in seen:
                continue
            seen.add(key)
            rows.append(row)
    rows.sort(key=lambda x: str(x.get("timestamp") or x.get("logged_utc") or x.get("timestamp_utc") or ""))
    return rows


def load_events(paths: Iterable[Path]) -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []
    seen: set[str] = set()
    for path in paths:
        if not path.exists():
            continue
        for line in path.read_text(encoding="utf-8", errors="ignore").splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                row = json.loads(line)
            except Exception:
                continue
            if not isinstance(row, dict):
                continue
            try:
                key = json.dumps(row, sort_keys=True)
            except Exception:
                key = str(row)
            if key in seen:
                continue
            seen.add(key)
            rows.append(row)
    rows.sort(key=lambda x: str(x.get("ts") or x.get("timestamp_utc") or x.get("timestamp") or ""))
    return rows


def extract_txids(row: Dict[str, Any]) -> List[str]:
    raw = row.get("txid")
    if raw is None:
        vr = row.get("validation_result")
        if isinstance(vr, dict):
            raw = vr.get("txid")
    if raw is None:
        return []
    if isinstance(raw, list):
        return [str(x).strip() for x in raw if str(x).strip()]
    return [str(raw).strip()] if str(raw).strip() else []


def summarize_events(events: List[Dict[str, Any]]) -> Dict[str, Any]:
    submit_total = 0
    validate_only = 0
    live_submits = 0
    txids: List[str] = []
    recent_24h_live_submit = 0
    recent_7d_live_submit = 0

    now = datetime.now(timezone.utc)
    cutoff_24h = now.timestamp() - 86400
    cutoff_7d = now.timestamp() - (7 * 86400)

    for row in events:
        event_name = str(row.get("event") or row.get("event_type") or "").strip().lower()
        if event_name not in {"submit_order", "submit_order_validate_only"}:
            continue

        submit_total += 1
        validate = row.get("validate")
        is_validate = str(validate).lower() == "true" or validate is True or event_name == "submit_order_validate_only"
        if is_validate:
            validate_only += 1

        event_txids = extract_txids(row)
        if event_txids and not is_validate:
            live_submits += 1
            txids.extend(event_txids)
            ts = parse_dt(row.get("ts") or row.get("timestamp_utc") or row.get("timestamp"))
            if ts is not None:
                ts_unix = ts.timestamp()
                if ts_unix >= cutoff_24h:
                    recent_24h_live_submit += 1
                if ts_unix >= cutoff_7d:
                    recent_7d_live_submit += 1

    txids_unique: List[str] = []
    seen: set[str] = set()
    for tx in txids:
        if tx in seen:
            continue
        seen.add(tx)
        txids_unique.append(tx)

    return {
        "submit_total": submit_total,
        "submit_validate_only": validate_only,
        "submit_live": live_submits,
        "txid_count": len(txids_unique),
        "txids": txids_unique,
        "recent_24h_live_submit": recent_24h_live_submit,
        "recent_7d_live_submit": recent_7d_live_submit,
    }


def summarize_live_trade_ledger(rows: List[Dict[str, Any]]) -> Dict[str, Any]:
    if not rows:
        return {
            "rows_total": 0,
            "txid_count": 0,
            "txids": [],
            "latest_txid": None,
            "latest_timestamp_utc": None,
            "status_counts": {},
            "source_count": sum(1 for p in LEDGER_SOURCES if p.exists()),
        }

    txids: List[str] = []
    status_counts: Dict[str, int] = {}
    latest_dt: Optional[datetime] = None
    latest_txid: Optional[str] = None

    for row in rows:
        if not isinstance(row, dict):
            continue

        txid = str(row.get("txid") or "").strip()
        if txid:
            txids.append(txid)

        status = str(row.get("status") or "unknown").strip().upper() or "UNKNOWN"
        status_counts[status] = status_counts.get(status, 0) + 1

        ts = parse_dt(row.get("timestamp") or row.get("logged_utc") or row.get("timestamp_utc"))
        if ts is not None and (latest_dt is None or ts > latest_dt):
            latest_dt = ts
            latest_txid = txid or latest_txid

    txids_unique = unique_ordered(txids)

    return {
        "rows_total": len(rows),
        "txid_count": len(txids_unique),
        "txids": txids_unique,
        "latest_txid": latest_txid,
        "latest_timestamp_utc": latest_dt.isoformat() if latest_dt else None,
        "status_counts": status_counts,
        "source_count": sum(1 for p in LEDGER_SOURCES if p.exists()),
    }


def load_kraken_keys() -> Dict[str, Any]:
    for path in KRAKEN_KEY_SOURCES:
        if not path.exists():
            continue

        key = ""
        secret = ""
        for line in path.read_text(encoding="utf-8", errors="ignore").splitlines():
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            k, v = line.split("=", 1)
            k = k.strip().upper()
            v = v.strip()
            if k == "KRAKEN_API_KEY":
                key = v
            elif k == "KRAKEN_API_SECRET":
                secret = v

        if key and secret:
            return {
                "api_key": key,
                "api_secret": secret,
                "source": str(path),
            }

    return {
        "api_key": "",
        "api_secret": "",
        "source": None,
    }


def kraken_sign(api_secret: str, urlpath: str, data: Dict[str, Any]) -> str:
    postdata = urlencode(data)
    encoded = (str(data.get("nonce", "")) + postdata).encode()
    message = urlpath.encode() + hashlib.sha256(encoded).digest()
    mac = hmac.new(base64.b64decode(api_secret), message, hashlib.sha512)
    return base64.b64encode(mac.digest()).decode()


def kraken_query_orders(txids: List[str], api_key: str, api_secret: str) -> Dict[str, Any]:
    if requests is None:
        return {"result": {}, "errors": ["requests_unavailable"]}

    endpoint = "/0/private/QueryOrders"
    nonce_seed = max(time.time_ns(), 1)
    result_rows: Dict[str, Any] = {}
    errors: List[str] = []

    chunks = [txids[i : i + MAX_RECON_TXIDS] for i in range(0, len(txids), MAX_RECON_TXIDS)]
    session = requests.Session()

    for chunk in chunks:
        for attempt in range(2):
            nonce_seed = max(time.time_ns(), nonce_seed + 1)
            data = {
                "nonce": str(nonce_seed),
                "txid": ",".join(chunk),
                "trades": True,
            }
            headers = {
                "API-Key": api_key,
                "API-Sign": kraken_sign(api_secret, endpoint, data),
            }

            payload: Dict[str, Any]
            try:
                response = session.post("https://api.kraken.com" + endpoint, data=data, headers=headers, timeout=20)
                response.raise_for_status()
                payload = response.json()
            except Exception as exc:
                errors.append(f"query_exception:{exc}")
                payload = {}

            err_list = payload.get("error") if isinstance(payload, dict) else []
            if err_list:
                if any("Invalid nonce" in str(e) for e in err_list) and attempt == 0:
                    nonce_seed += 10_000_000_000
                    time.sleep(0.25)
                    continue
                errors.extend(str(e) for e in err_list)

            result = payload.get("result") if isinstance(payload, dict) else {}
            if isinstance(result, dict):
                result_rows.update(result)
            break

    return {
        "result": result_rows,
        "errors": unique_ordered(errors),
    }


def summarize_kraken_fill_reconciliation(txids: List[str]) -> Dict[str, Any]:
    txids_unique = unique_ordered(txids)
    summary: Dict[str, Any] = {
        "query_enabled": False,
        "query_source": None,
        "txids_considered": len(txids_unique),
        "txids_queried": 0,
        "queried_txids": [],
        "status_counts": {},
        "closed_count": 0,
        "open_count": 0,
        "canceled_count": 0,
        "expired_count": 0,
        "pending_count": 0,
        "fully_filled_count": 0,
        "partially_filled_count": 0,
        "unfilled_count": 0,
        "fill_sync_pct": 0.0,
        "total_cost_usd": 0.0,
        "total_fee_usd": 0.0,
        "last_closed_utc": None,
        "query_errors": [],
        "sample": [],
    }

    if not txids_unique:
        summary["query_errors"] = ["no_txids"]
        return summary

    if requests is None:
        summary["query_errors"] = ["requests_unavailable"]
        return summary

    keys = load_kraken_keys()
    api_key = str(keys.get("api_key") or "")
    api_secret = str(keys.get("api_secret") or "")
    if not api_key or not api_secret:
        summary["query_errors"] = ["missing_kraken_keys"]
        return summary

    target_txids = txids_unique[-MAX_RECON_TXIDS:]
    summary["query_enabled"] = True
    summary["query_source"] = keys.get("source")
    summary["txids_queried"] = len(target_txids)
    summary["queried_txids"] = target_txids

    response = kraken_query_orders(target_txids, api_key=api_key, api_secret=api_secret)
    result_rows = response.get("result") if isinstance(response, dict) else {}
    if not isinstance(result_rows, dict):
        result_rows = {}
    query_errors = response.get("errors") if isinstance(response, dict) else []
    if isinstance(query_errors, list):
        summary["query_errors"] = unique_ordered(query_errors)

    latest_closed_dt: Optional[datetime] = None
    status_counts: Dict[str, int] = {}
    samples: List[Dict[str, Any]] = []

    for txid in target_txids:
        info = result_rows.get(txid)
        status = "unknown"
        vol = 0.0
        vol_exec = 0.0
        cost = 0.0
        fee = 0.0
        trades_count = 0

        if isinstance(info, dict):
            status = str(info.get("status") or "unknown").strip().lower()
            vol = safe_float(info.get("vol"), 0.0)
            vol_exec = safe_float(info.get("vol_exec"), 0.0)
            cost = safe_float(info.get("cost"), 0.0)
            fee = safe_float(info.get("fee"), 0.0)

            trades = info.get("trades")
            trades_count = len(trades) if isinstance(trades, list) else 0

            if status == "closed":
                summary["closed_count"] += 1
                close_unix = safe_float(info.get("closetm"), 0.0)
                if close_unix > 0.0:
                    try:
                        close_dt = datetime.fromtimestamp(close_unix, tz=timezone.utc)
                        if latest_closed_dt is None or close_dt > latest_closed_dt:
                            latest_closed_dt = close_dt
                    except Exception:
                        pass
            elif status == "open":
                summary["open_count"] += 1
            elif status in {"canceled", "cancelled"}:
                summary["canceled_count"] += 1
            elif status == "expired":
                summary["expired_count"] += 1
            else:
                summary["pending_count"] += 1

            if vol_exec <= 0.0:
                summary["unfilled_count"] += 1
            elif vol > 0.0 and (vol_exec + 1e-12) < vol:
                summary["partially_filled_count"] += 1
            else:
                summary["fully_filled_count"] += 1

            summary["total_cost_usd"] += cost
            summary["total_fee_usd"] += fee
        else:
            summary["pending_count"] += 1
            summary["unfilled_count"] += 1

        status_counts[status] = status_counts.get(status, 0) + 1
        samples.append(
            {
                "txid": txid,
                "status": status,
                "vol": round(vol, 8),
                "vol_exec": round(vol_exec, 8),
                "cost_usd": round(cost, 6),
                "fee_usd": round(fee, 6),
                "trades_count": trades_count,
            }
        )

    summary["status_counts"] = status_counts
    summary["fill_sync_pct"] = round(
        (summary["closed_count"] / summary["txids_queried"] * 100.0) if summary["txids_queried"] else 0.0,
        2,
    )
    summary["total_cost_usd"] = round(summary["total_cost_usd"], 6)
    summary["total_fee_usd"] = round(summary["total_fee_usd"], 6)
    summary["last_closed_utc"] = latest_closed_dt.isoformat() if latest_closed_dt else None
    summary["sample"] = samples[-8:]
    return summary


def summarize_trade_log(rows: List[Dict[str, Any]]) -> Dict[str, Any]:
    if not rows:
        return {
            "rows_total": 0,
            "closed_live_count": 0,
            "win_count": 0,
            "loss_count": 0,
            "win_rate_pct": 0.0,
            "realized_net_usd": 0.0,
            "fees_usd": 0.0,
            "gross_notional_usd": 0.0,
            "avg_net_per_trade_usd": 0.0,
            "avg_net_pct_per_trade": 0.0,
            "max_drawdown_pct": 0.0,
            "profit_factor": 0.0,
            "trades_per_day": 0.0,
            "last_trade_utc": None,
        }

    closed_live: List[Dict[str, Any]] = []
    for row in rows:
        if not isinstance(row, dict):
            continue
        if str(row.get("status", "")).upper() != "CLOSED":
            continue
        mode = str(row.get("execution_mode", "")).upper()
        if mode and mode != "LIVE":
            continue
        exchange = str(row.get("exchange", "")).lower()
        if exchange and exchange != "kraken":
            continue
        closed_live.append(row)

    if not closed_live:
        return {
            "rows_total": len(rows),
            "closed_live_count": 0,
            "win_count": 0,
            "loss_count": 0,
            "win_rate_pct": 0.0,
            "realized_net_usd": 0.0,
            "fees_usd": 0.0,
            "gross_notional_usd": 0.0,
            "avg_net_per_trade_usd": 0.0,
            "avg_net_pct_per_trade": 0.0,
            "max_drawdown_pct": 0.0,
            "profit_factor": 0.0,
            "trades_per_day": 0.0,
            "last_trade_utc": None,
        }

    closed_live.sort(key=lambda x: str(x.get("timestamp") or ""))

    realized_net = sum(safe_float(r.get("net_pnl"), 0.0) for r in closed_live)
    fees = sum(safe_float(r.get("round_trip_fee_usd"), 0.0) for r in closed_live)
    gross_notional = sum(safe_float(r.get("size_usd"), 0.0) for r in closed_live)

    win_count = sum(1 for r in closed_live if safe_float(r.get("net_pnl"), 0.0) > 0)
    loss_count = sum(1 for r in closed_live if safe_float(r.get("net_pnl"), 0.0) < 0)
    win_rate = (win_count / len(closed_live)) * 100.0 if closed_live else 0.0

    net_values = [safe_float(r.get("net_pnl"), 0.0) for r in closed_live]
    pct_values = [safe_float(r.get("net_pnl_pct"), 0.0) for r in closed_live]

    positives = sum(v for v in net_values if v > 0)
    negatives = abs(sum(v for v in net_values if v < 0))
    profit_factor = (positives / negatives) if negatives > 1e-12 else (10.0 if positives > 0 else 0.0)

    equity = 1.0
    peak = 1.0
    max_dd = 0.0
    for p in pct_values:
        equity *= 1.0 + (p / 100.0)
        peak = max(peak, equity)
        if peak > 0:
            max_dd = max(max_dd, (peak - equity) / peak)

    day_buckets: Dict[str, int] = {}
    last_trade_ts: Optional[datetime] = None
    for row in closed_live:
        dt = parse_dt(row.get("timestamp"))
        if dt is None:
            continue
        last_trade_ts = dt
        key = dt.date().isoformat()
        day_buckets[key] = day_buckets.get(key, 0) + 1

    unique_days = len(day_buckets)
    trades_per_day = (len(closed_live) / unique_days) if unique_days else 0.0

    return {
        "rows_total": len(rows),
        "closed_live_count": len(closed_live),
        "win_count": win_count,
        "loss_count": loss_count,
        "win_rate_pct": round(win_rate, 2),
        "realized_net_usd": round(realized_net, 4),
        "fees_usd": round(fees, 4),
        "gross_notional_usd": round(gross_notional, 4),
        "avg_net_per_trade_usd": round(realized_net / len(closed_live), 6),
        "avg_net_pct_per_trade": round(sum(pct_values) / len(pct_values), 6),
        "max_drawdown_pct": round(max_dd * 100.0, 4),
        "profit_factor": round(profit_factor, 4),
        "trades_per_day": round(trades_per_day, 4),
        "last_trade_utc": last_trade_ts.isoformat() if last_trade_ts else None,
    }


def summarize_balance(paths: Iterable[Path]) -> Dict[str, Any]:
    for path in paths:
        payload = read_json(path, None)
        if not isinstance(payload, dict) or not payload:
            continue

        if "portfolio_est_total_usd" in payload:
            return {
                "source": str(path),
                "portfolio_est_total_usd": safe_float(payload.get("portfolio_est_total_usd"), 0.0),
                "usd_liquid": safe_float(payload.get("usd_balance_max"), 0.0),
                "timestamp_utc": payload.get("timestamp_utc"),
            }

        if "usd_balance" in payload:
            return {
                "source": str(path),
                "portfolio_est_total_usd": safe_float(payload.get("usd_balance"), 0.0),
                "usd_liquid": safe_float(payload.get("usd_balance"), 0.0),
                "timestamp_utc": payload.get("timestamp") or payload.get("timestamp_utc"),
            }

    return {
        "source": None,
        "portfolio_est_total_usd": 0.0,
        "usd_liquid": 0.0,
        "timestamp_utc": None,
    }


def summarize_heartbeat(paths: Iterable[Path]) -> Dict[str, Any]:
    best: Dict[str, Any] = {
        "source": None,
        "status": "unknown",
        "timestamp_utc": None,
        "age_minutes": None,
        "fresh": False,
        "reason": "missing",
    }

    now = datetime.now(timezone.utc)
    for path in paths:
        payload = read_json(path, None)
        if not isinstance(payload, dict) or not payload:
            continue

        status = str(payload.get("status") or "unknown")
        ts = parse_dt(payload.get("timestamp_utc") or payload.get("generated_utc") or payload.get("timestamp"))
        age_minutes = None
        fresh = False
        if ts is not None:
            age_minutes = (now - ts).total_seconds() / 60.0
            fresh = age_minutes <= 20.0

        candidate = {
            "source": str(path),
            "status": status,
            "timestamp_utc": ts.isoformat() if ts else payload.get("timestamp_utc") or payload.get("timestamp"),
            "age_minutes": round(age_minutes, 2) if age_minutes is not None else None,
            "fresh": fresh,
            "reason": payload.get("reason") or payload.get("error") or "",
        }

        if best["source"] is None:
            best = candidate
            continue

        # Prefer fresher heartbeats.
        prev_age = best.get("age_minutes")
        cur_age = candidate.get("age_minutes")
        if prev_age is None and cur_age is not None:
            best = candidate
        elif isinstance(prev_age, (int, float)) and isinstance(cur_age, (int, float)) and cur_age < prev_age:
            best = candidate

    return best


def build_projections(capital_usd: float, avg_net_pct_trade: float, trades_per_day: float) -> Dict[str, Any]:
    if capital_usd <= 0 or trades_per_day <= 0:
        return {
            "daily_edge_base_pct": 0.0,
            "scenarios": {},
            "note": "Insufficient capital or trade-frequency data for projection.",
        }

    daily_edge = (avg_net_pct_trade / 100.0) * trades_per_day
    # Keep projections bounded to avoid unrealistic blowups.
    daily_edge = max(-0.03, min(0.03, daily_edge))

    scenario_rates = {
        "conservative": daily_edge * 0.45,
        "base": daily_edge * 0.75,
        "aggressive": daily_edge * 1.10,
    }

    scenarios: Dict[str, Dict[str, float]] = {}
    for name, rate in scenario_rates.items():
        r = max(-0.05, min(0.05, rate))
        eq_30 = capital_usd * math.pow(1.0 + r, 30)
        eq_90 = capital_usd * math.pow(1.0 + r, 90)
        scenarios[name] = {
            "daily_rate_pct": round(r * 100.0, 4),
            "equity_30d_usd": round(eq_30, 2),
            "equity_90d_usd": round(eq_90, 2),
        }

    return {
        "daily_edge_base_pct": round(daily_edge * 100.0, 4),
        "scenarios": scenarios,
        "note": "Projection is expectancy-based and capped for realism; it is not a guarantee.",
    }


def compute_integrity_score(
    events: Dict[str, Any],
    trades: Dict[str, Any],
    heartbeat: Dict[str, Any],
    ledger: Dict[str, Any],
    reconciliation: Dict[str, Any],
) -> Dict[str, Any]:
    score = 0.0

    txid_score = min(35.0, events.get("txid_count", 0) * 2.5)
    submit_score = min(16.0, events.get("submit_live", 0) * 1.1)
    trade_depth = min(16.0, trades.get("closed_live_count", 0) * 0.4)
    ledger_score = min(8.0, ledger.get("txid_count", 0) * 1.0)
    heartbeat_score = 15.0 if heartbeat.get("fresh") else 4.0
    pnl_track_score = 6.0 if trades.get("rows_total", 0) > 0 else 0.0
    recon_sync = safe_float(reconciliation.get("fill_sync_pct"), 0.0)
    reconciliation_score = min(19.0, max(0.0, recon_sync * 0.19))

    score = txid_score + submit_score + trade_depth + ledger_score + heartbeat_score + pnl_track_score + reconciliation_score
    score = min(100.0, score)

    return {
        "score_0_100": round(score, 2),
        "components": {
            "txid_evidence": round(txid_score, 2),
            "live_submit_depth": round(submit_score, 2),
            "trade_log_depth": round(trade_depth, 2),
            "ledger_depth": round(ledger_score, 2),
            "heartbeat_freshness": round(heartbeat_score, 2),
            "pnl_tracking": round(pnl_track_score, 2),
            "exchange_reconciliation": round(reconciliation_score, 2),
        },
    }


def write_markdown(payload: Dict[str, Any]) -> None:
    events = payload.get("kraken_execution_evidence", {})
    ledger = payload.get("live_ledger_evidence", {})
    recon = payload.get("kraken_fill_reconciliation", {})
    trades = payload.get("live_trade_performance", {})
    capital = payload.get("capital_state", {})
    score = payload.get("integrity_score", {})
    proj = payload.get("compounding_projection", {})
    scenarios = proj.get("scenarios", {})
    ctrl = payload.get("growth_controller_status", {})
    guard = ctrl.get("guard", {}) if isinstance(ctrl, dict) else {}
    reasons = guard.get("reasons", []) if isinstance(guard, dict) else []
    query_errors = recon.get("query_errors") if isinstance(recon, dict) else []
    if not isinstance(query_errors, list):
        query_errors = []

    lines = [
        "# VPS Kraken Growth Proof",
        "",
        f"Generated UTC: {payload.get('generated_utc')}",
        "",
        "## Evidence",
        f"- Live submit events: {events.get('submit_live', 0)}",
        f"- TXID count: {events.get('txid_count', 0)}",
        f"- Live submits (24h): {events.get('recent_24h_live_submit', 0)}",
        f"- Live submits (7d): {events.get('recent_7d_live_submit', 0)}",
        f"- Ledger TXID count: {ledger.get('txid_count', 0)}",
        f"- Ledger latest TXID: {ledger.get('latest_txid')}",
        "",
        "## Exchange Reconciliation",
        f"- TXIDs queried: {recon.get('txids_queried', 0)}",
        f"- Closed count: {recon.get('closed_count', 0)}",
        f"- Fully filled count: {recon.get('fully_filled_count', 0)}",
        f"- Partially filled count: {recon.get('partially_filled_count', 0)}",
        f"- Fill sync pct: {recon.get('fill_sync_pct', 0.0)}%",
        f"- Reconciliation errors: {', '.join(str(x) for x in query_errors) if query_errors else 'none'}",
        "",
        "## Performance",
        f"- Closed live trades: {trades.get('closed_live_count', 0)}",
        f"- Realized net USD: {trades.get('realized_net_usd', 0.0)}",
        f"- Win rate: {trades.get('win_rate_pct', 0.0)}%",
        f"- Avg net per trade USD: {trades.get('avg_net_per_trade_usd', 0.0)}",
        f"- Avg net pct per trade: {trades.get('avg_net_pct_per_trade', 0.0)}%",
        f"- Max drawdown: {trades.get('max_drawdown_pct', 0.0)}%",
        "",
        "## Capital",
        f"- Estimated portfolio USD: {capital.get('portfolio_est_total_usd', 0.0)}",
        f"- Liquid USD: {capital.get('usd_liquid', 0.0)}",
        f"- Snapshot source: {capital.get('source')}",
        "",
        "## Integrity Score",
        f"- Score (0-100): {score.get('score_0_100', 0.0)}",
        "",
        "## Controller Guard",
        f"- Mode: {ctrl.get('mode', 'UNKNOWN') if isinstance(ctrl, dict) else 'UNKNOWN'}",
        f"- Allow live: {guard.get('allow_live', False) if isinstance(guard, dict) else False}",
        f"- Heartbeat: {guard.get('heartbeat_source', 'n/a')} / {guard.get('heartbeat_status', 'n/a')} / {guard.get('heartbeat_age_minutes', 'n/a')} min",
        f"- Reasons: {', '.join(str(x) for x in reasons) if reasons else 'none'}",
        "",
        "## Projection",
    ]

    for name in ("conservative", "base", "aggressive"):
        row = scenarios.get(name)
        if not isinstance(row, dict):
            continue
        lines.append(
            f"- {name.title()}: daily {row.get('daily_rate_pct', 0.0)}% | 30d ${row.get('equity_30d_usd', 0.0)} | 90d ${row.get('equity_90d_usd', 0.0)}"
        )

    lines.extend([
        "",
        "## Guardrail",
        "- This report is evidence and control telemetry, not a guarantee of returns.",
        "- Live trading must remain risk-capped and supervisor-controlled.",
    ])

    OUTPUT_MD.write_text("\n".join(lines) + "\n", encoding="utf-8")


def write_hash_manifest() -> None:
    artifacts = [OUTPUT_JSON, OUTPUT_MD, OUTPUT_DASH_JSON]
    if OUTPUT_DASH_CONTROLLER_JSON.exists():
        artifacts.append(OUTPUT_DASH_CONTROLLER_JSON)
    rows = []
    for path in artifacts:
        data = path.read_bytes()
        rows.append(
            {
                "path": str(path),
                "sha256": hashlib.sha256(data).hexdigest(),
                "bytes": len(data),
            }
        )

    OUTPUT_HASH.write_text(json.dumps({"generated_utc": now_utc(), "artifacts": rows}, indent=2), encoding="utf-8")


def append_history(payload: Dict[str, Any]) -> None:
    events = payload.get("kraken_execution_evidence", {})
    ledger = payload.get("live_ledger_evidence", {})
    recon = payload.get("kraken_fill_reconciliation", {})
    trades = payload.get("live_trade_performance", {})
    score = payload.get("integrity_score", {})
    cap = payload.get("capital_state", {})

    row = {
        "generated_utc": payload.get("generated_utc"),
        "score_0_100": score.get("score_0_100", 0.0),
        "txid_count": events.get("txid_count", 0),
        "ledger_txid_count": ledger.get("txid_count", 0),
        "live_submit_7d": events.get("recent_7d_live_submit", 0),
        "closed_reconciled_count": recon.get("closed_count", 0),
        "fill_sync_pct": recon.get("fill_sync_pct", 0.0),
        "closed_live_count": trades.get("closed_live_count", 0),
        "realized_net_usd": trades.get("realized_net_usd", 0.0),
        "win_rate_pct": trades.get("win_rate_pct", 0.0),
        "portfolio_est_total_usd": cap.get("portfolio_est_total_usd", 0.0),
    }

    with OUTPUT_HISTORY.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(row, sort_keys=True) + "\n")


def main() -> None:
    OUT_EXEC.mkdir(parents=True, exist_ok=True)
    DASH.mkdir(parents=True, exist_ok=True)
    OUTPUT_DASH_JSON.parent.mkdir(parents=True, exist_ok=True)

    events = load_events(EVENT_SOURCES)
    event_summary = summarize_events(events)

    ledger_rows = load_jsonl_rows(LEDGER_SOURCES)
    ledger_summary = summarize_live_trade_ledger(ledger_rows)

    combined_txids = unique_ordered(
        list(event_summary.get("txids", [])) + list(ledger_summary.get("txids", []))
    )
    event_summary["txid_count_event_stream"] = event_summary.get("txid_count", 0)
    event_summary["txid_count_ledger_stream"] = ledger_summary.get("txid_count", 0)
    event_summary["txid_count"] = len(combined_txids)
    event_summary["txids"] = combined_txids

    reconciliation_summary = summarize_kraken_fill_reconciliation(combined_txids)

    trade_log_path = pick_first_existing(TRADE_LOG_SOURCES)
    trade_rows = read_json(trade_log_path, []) if trade_log_path else []
    if not isinstance(trade_rows, list):
        trade_rows = []
    trade_summary = summarize_trade_log(trade_rows)

    balance_summary = summarize_balance(BALANCE_SOURCES)
    heartbeat_summary = summarize_heartbeat(HEARTBEAT_SOURCES)
    controller_status = read_json(CONTROLLER_STATUS_JSON, {})
    if not isinstance(controller_status, dict):
        controller_status = {}

    capital_usd = safe_float(balance_summary.get("portfolio_est_total_usd"), 0.0)
    projections = build_projections(
        capital_usd=capital_usd,
        avg_net_pct_trade=safe_float(trade_summary.get("avg_net_pct_per_trade"), 0.0),
        trades_per_day=safe_float(trade_summary.get("trades_per_day"), 0.0),
    )

    integrity = compute_integrity_score(
        event_summary,
        trade_summary,
        heartbeat_summary,
        ledger_summary,
        reconciliation_summary,
    )

    payload: Dict[str, Any] = {
        "generated_utc": now_utc(),
        "schema": "vps_growth_proof_v2",
        "objective": "VPS-side live Kraken execution evidence with exchange-reconciled fill truth, growth telemetry, and compounding-proof instrumentation.",
        "kraken_execution_evidence": {
            **event_summary,
            "event_source_count": sum(1 for p in EVENT_SOURCES if p.exists()),
        },
        "live_ledger_evidence": ledger_summary,
        "kraken_fill_reconciliation": reconciliation_summary,
        "live_trade_performance": {
            **trade_summary,
            "trade_log_source": str(trade_log_path) if trade_log_path else None,
        },
        "capital_state": balance_summary,
        "runtime_heartbeat": heartbeat_summary,
        "growth_controller_status": controller_status,
        "compounding_projection": projections,
        "integrity_score": integrity,
        "guardrail": "Evidence telemetry only. No guarantee of profit. Keep live-trade controls and risk caps active.",
    }

    OUTPUT_JSON.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    OUTPUT_DASH_JSON.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    if controller_status:
        OUTPUT_DASH_CONTROLLER_JSON.write_text(json.dumps(controller_status, indent=2), encoding="utf-8")
    write_markdown(payload)
    write_hash_manifest()
    append_history(payload)

    print(str(OUTPUT_JSON))
    print(str(OUTPUT_MD))
    print(str(OUTPUT_HASH))
    print(str(OUTPUT_HISTORY))
    print(str(OUTPUT_DASH_JSON))


if __name__ == "__main__":
    main()
