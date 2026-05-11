from __future__ import annotations

import argparse
import json
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Set

ROOT = Path(r"C:\LumaTrader\INSTITUTIONAL_STACK_V2")
EXEC_OUT = ROOT / "out" / "execution"
KEY_REPORT_FILE = EXEC_OUT / "api_key_registry_report.json"
OUT_FILE = EXEC_OUT / "lane_integrity_report.json"


def now_utc() -> str:
    return datetime.now(timezone.utc).isoformat()


def load_json(path: Path, default: Any) -> Any:
    try:
        if path.exists():
            return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        pass
    return default


def atomic_write_json(path: Path, payload: Dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    tmp.replace(path)


def classify_lanes(row: Dict[str, Any]) -> Set[str]:
    key = str(row.get("key", "")).upper()
    purpose = str(row.get("purpose", "")).lower()
    used_by = " ".join(str(x).lower() for x in (row.get("used_by") or []))
    blob = f"{key} {purpose} {used_by}"

    lanes: Set[str] = set()

    if any(token in blob for token in ["ALPACA", "KRAKEN", "BINANCE", "TRAD", "EXECUTOR", "ORDER"]):
        lanes.add("trading_execution")
    if any(token in blob for token in ["SYMBOL", "UNIVERSE", "REGISTRY", "FINNHUB", "ALPHAVANTAGE", "TWELVE_DATA"]):
        lanes.add("symbols_market_data")
    if any(token in blob for token in ["FRED", "EIA", "NOAA", "CENSUS", "BEA", "BLS", "NASA", "NREL", "AQS", "USGS"]):
        lanes.add("gov_infra_data")
    if any(token in blob for token in ["OPENAI", "AZURE_OPENAI", "EXPLAINER", "GUIDE"]):
        lanes.add("ai_explainer")
    if any(token in blob for token in ["WEBHOOK", "PAYOUT", "TOKEN", "AUTH_BEARER"]):
        lanes.add("payouts_webhooks")
    if any(token in blob for token in ["PROOF", "AUDIT", "CHAIN", "DELTA", "CUSTODY"]):
        lanes.add("proof_audit")

    # If no lane detected, keep in a catch-all lane for manual classification.
    if not lanes:
        lanes.add("unassigned")

    return lanes


def build_report() -> Dict[str, Any]:
    report = load_json(KEY_REPORT_FILE, {})
    rows = report.get("rows", []) if isinstance(report, dict) else []

    lane_counts: Dict[str, int] = {}
    lane_present_counts: Dict[str, int] = {}
    lane_missing_counts: Dict[str, int] = {}

    crossings: List[Dict[str, Any]] = []
    unassigned: List[str] = []

    for row in rows:
        if not isinstance(row, dict):
            continue
        lanes = sorted(classify_lanes(row))
        present = bool(row.get("present", False))
        key = str(row.get("key", ""))

        for lane in lanes:
            lane_counts[lane] = lane_counts.get(lane, 0) + 1
            if present:
                lane_present_counts[lane] = lane_present_counts.get(lane, 0) + 1
            else:
                lane_missing_counts[lane] = lane_missing_counts.get(lane, 0) + 1

        if len(lanes) > 1 and key:
            crossings.append(
                {
                    "key": key,
                    "lanes": lanes,
                    "present": present,
                    "purpose": row.get("purpose", ""),
                }
            )

        if lanes == ["unassigned"] and key:
            unassigned.append(key)

    total_keys = int(report.get("total_keys", len(rows) or 0)) if isinstance(report, dict) else len(rows)
    present_keys = int(report.get("present_keys", 0)) if isinstance(report, dict) else 0
    coverage_pct = float(report.get("coverage_pct", 0.0)) if isinstance(report, dict) else 0.0

    critical_keys = [
        "ALPACA_API_KEY",
        "ALPACA_API_SECRET",
        "KRAKEN_API_KEY",
        "KRAKEN_API_SECRET",
        "EIA_API_KEY",
        "FRED_API_KEY",
        "OPENAI_API_KEY",
    ]
    critical_missing = []
    row_map = {str(r.get("key", "")): r for r in rows if isinstance(r, dict)}
    for key in critical_keys:
        rec = row_map.get(key, {})
        if not bool(rec.get("present", False)):
            critical_missing.append(key)

    status = "green"
    if critical_missing or len(crossings) >= 10:
        status = "red"
    elif len(crossings) > 0 or coverage_pct < 55.0:
        status = "yellow"

    return {
        "generated_utc": now_utc(),
        "schema": "lane_integrity_report_v1",
        "status": status,
        "summary": {
            "total_keys": total_keys,
            "present_keys": present_keys,
            "coverage_pct": round(coverage_pct, 2),
            "cross_lane_key_count": len(crossings),
            "critical_missing_count": len(critical_missing),
            "unassigned_key_count": len(unassigned),
        },
        "lane_counts": lane_counts,
        "lane_present_counts": lane_present_counts,
        "lane_missing_counts": lane_missing_counts,
        "critical_missing": critical_missing,
        "crossings_top": crossings[:25],
        "unassigned_top": sorted(unassigned)[:25],
        "inputs": {
            "api_key_registry_report": str(KEY_REPORT_FILE),
        },
    }


def run_once() -> Dict[str, Any]:
    payload = build_report()
    atomic_write_json(OUT_FILE, payload)
    return payload


def main(argv: List[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Lane integrity guard")
    parser.add_argument("--loop", action="store_true", help="Run continuously")
    parser.add_argument("--interval", type=int, default=30, help="Loop interval in seconds")
    args = parser.parse_args(argv)

    if not args.loop:
        payload = run_once()
        print(json.dumps(payload, indent=2))
        return 0

    interval = max(10, int(args.interval))
    while True:
        payload = run_once()
        s = payload.get("summary", {})
        print(
            f"[{payload.get('generated_utc')}] status={payload.get('status')} "
            f"cross={s.get('cross_lane_key_count', 0)} "
            f"critical_missing={s.get('critical_missing_count', 0)} "
            f"coverage={s.get('coverage_pct', 0.0):.2f}%"
        )
        time.sleep(interval)


if __name__ == "__main__":
    raise SystemExit(main())
