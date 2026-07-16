#!/usr/bin/env python3
"""Read-only LumenCore execution orchestrator.

The historical multi-exchange implementation is preserved in
execution_orchestrator_legacy.py. This canonical process samples only public
Kraken market data, writes a fail-closed heartbeat, and maintains a SHA-256
linked audit ledger. It never loads exchange credentials.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import signal
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable

import requests

ROOT = Path(os.environ.get("LUMA_STACK_ROOT", r"C:\LumaTrader\INSTITUTIONAL_STACK_V2")).expanduser()
OUT = ROOT / "out" / "execution"
HEARTBEAT_FILE = OUT / "live_engine_heartbeat.json"
SNAPSHOT_FILE = OUT / "live_data_no_orders_snapshot.json"
AUDIT_LEDGER_FILE = OUT / "live_data_no_orders_audit.jsonl"
PUBLIC_TICKER_URL = "https://api.kraken.com/0/public/Ticker"
PROMOTION_STAGE = "live_data_no_orders"
ORDER_SAFETY_POLICY = "validate_only_fail_closed"
DEFAULT_PAIRS = ("XBTUSD", "ETHUSD", "SOLUSD")
_STOP = False


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def canonical_json(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True, default=str)


def sha256_payload(value: Any) -> str:
    return hashlib.sha256(canonical_json(value).encode("utf-8")).hexdigest()


def atomic_write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + ".tmp")
    temporary.write_text(json.dumps(value, indent=2, ensure_ascii=True), encoding="utf-8")
    os.replace(temporary, path)


def normalize_pairs(values: Iterable[str]) -> list[str]:
    pairs: list[str] = []
    seen: set[str] = set()
    for raw in values:
        for part in str(raw or "").split(","):
            pair = part.strip().upper().replace("/", "")
            if pair and pair not in seen:
                seen.add(pair)
                pairs.append(pair)
    return pairs


def fetch_public_ticker(session: requests.Session, pair: str, timeout_seconds: float = 10.0) -> dict[str, Any]:
    response = session.get(PUBLIC_TICKER_URL, params={"pair": pair}, timeout=max(1.0, timeout_seconds))
    response.raise_for_status()
    body = response.json()
    if not isinstance(body, dict) or body.get("error"):
        raise RuntimeError(f"Kraken public ticker error: {body.get('error') if isinstance(body, dict) else 'invalid body'}")
    result = body.get("result")
    if not isinstance(result, dict) or not result:
        raise RuntimeError("Kraken public ticker result missing")
    resolved_pair, ticker = next(iter(result.items()))
    if not isinstance(ticker, dict):
        raise RuntimeError("Kraken public ticker payload missing")

    def number(key: str, index: int = 0) -> float | None:
        value = ticker.get(key)
        if isinstance(value, list):
            if index >= len(value):
                return None
            value = value[index]
        try:
            return float(value)
        except (TypeError, ValueError):
            return None

    return {
        "requested_pair": pair,
        "resolved_pair": str(resolved_pair),
        "last": number("c"),
        "bid": number("b"),
        "ask": number("a"),
        "volume_24h": number("v", 1),
    }


def build_read_only_snapshot(
    session: requests.Session,
    pairs: Iterable[str],
    *,
    timeout_seconds: float = 10.0,
) -> dict[str, Any]:
    normalized = normalize_pairs(pairs)
    markets: list[dict[str, Any]] = []
    healthy = 0
    for pair in normalized:
        try:
            markets.append({"pair": pair, "ok": True, "ticker": fetch_public_ticker(session, pair, timeout_seconds)})
            healthy += 1
        except Exception as exc:
            markets.append({"pair": pair, "ok": False, "error_type": type(exc).__name__, "error": str(exc)[:240]})
    return {
        "timestamp_utc": utc_now(),
        "status": PROMOTION_STAGE if healthy == len(normalized) else "degraded_read_only",
        "reason": "authenticated order submission disabled by promotion stage",
        "mode": "read_only",
        "promotion_stage": PROMOTION_STAGE,
        "order_safety_policy": ORDER_SAFETY_POLICY,
        "public_market_data_only": True,
        "credentials_loaded": False,
        "allow_live_orders": False,
        "kill_switch": True,
        "pair_count": len(normalized),
        "healthy_pair_count": healthy,
        "markets": markets,
    }


def _previous_hash(path: Path) -> str:
    if not path.exists():
        return "0" * 64
    try:
        for raw in reversed(path.read_text(encoding="utf-8", errors="replace").splitlines()):
            if raw.strip():
                value = str(json.loads(raw).get("record_sha256", ""))
                return value if len(value) == 64 else "0" * 64
    except Exception:
        pass
    return "0" * 64


def persist_snapshot(
    snapshot: dict[str, Any],
    *,
    heartbeat_path: Path = HEARTBEAT_FILE,
    snapshot_path: Path = SNAPSHOT_FILE,
    ledger_path: Path = AUDIT_LEDGER_FILE,
) -> dict[str, Any]:
    persisted = dict(snapshot)
    persisted["snapshot_sha256"] = sha256_payload(snapshot)
    healthy_markets = [item for item in persisted["markets"] if item.get("ok")]
    selected = healthy_markets[0]["pair"] if healthy_markets else ""
    heartbeat = {
        "timestamp_utc": persisted["timestamp_utc"],
        "status": "running" if persisted["healthy_pair_count"] else "degraded",
        "reason": PROMOTION_STAGE,
        "mode": "read_only",
        "promotion_stage": PROMOTION_STAGE,
        "order_safety_policy": ORDER_SAFETY_POLICY,
        "public_market_data_only": True,
        "credentials_loaded": False,
        "allow_live_orders": False,
        "kill_switch": True,
        "selected_symbol": selected,
        "symbol_source": "public_read_only_pair_list",
        "universe_candidate_count": persisted["pair_count"],
        "healthy_pair_count": persisted["healthy_pair_count"],
        "pair_count": persisted["pair_count"],
        "snapshot_sha256": persisted["snapshot_sha256"],
    }
    record = {
        "timestamp_utc": utc_now(),
        "event": "read_only_market_snapshot",
        "promotion_stage": PROMOTION_STAGE,
        "previous_sha256": _previous_hash(ledger_path),
        "payload": {
            "snapshot_sha256": persisted["snapshot_sha256"],
            "healthy_pair_count": persisted["healthy_pair_count"],
            "pair_count": persisted["pair_count"],
        },
    }
    record["record_sha256"] = sha256_payload(record)
    atomic_write_json(snapshot_path, persisted)
    atomic_write_json(heartbeat_path, heartbeat)
    ledger_path.parent.mkdir(parents=True, exist_ok=True)
    with ledger_path.open("a", encoding="utf-8") as handle:
        handle.write(canonical_json(record) + "\n")
    return {"snapshot": persisted, "heartbeat": heartbeat, "ledger_record": record}


def _stop(_signum: int, _frame: Any) -> None:
    global _STOP
    _STOP = True


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="LumenCore public-market monitor; live execution disabled")
    parser.add_argument("--pair", action="append", default=[])
    parser.add_argument("--interval-sec", type=float, default=15.0)
    parser.add_argument("--timeout-sec", type=float, default=10.0)
    parser.add_argument("--once", action="store_true")
    parser.add_argument("--max-cycles", type=int, default=None)
    args = parser.parse_args(argv)

    env_pairs = os.environ.get("LUMA_READ_ONLY_PAIRS", "")
    pairs = normalize_pairs(args.pair or ([env_pairs] if env_pairs else DEFAULT_PAIRS)) or list(DEFAULT_PAIRS)
    signal.signal(signal.SIGINT, _stop)
    if hasattr(signal, "SIGTERM"):
        signal.signal(signal.SIGTERM, _stop)

    print("LUMENCORE EXECUTION ORCHESTRATOR | LIVE DATA | NO ORDERS", flush=True)
    session = requests.Session()
    cycles = 0
    global _STOP
    _STOP = False
    while not _STOP:
        result = persist_snapshot(build_read_only_snapshot(session, pairs, timeout_seconds=args.timeout_sec))
        cycles += 1
        print(canonical_json({
            "cycle": cycles,
            "status": result["snapshot"]["status"],
            "healthy_pairs": result["snapshot"]["healthy_pair_count"],
            "pair_count": result["snapshot"]["pair_count"],
            "snapshot_sha256": result["snapshot"]["snapshot_sha256"],
        }), flush=True)
        if args.once or (args.max_cycles is not None and cycles >= args.max_cycles):
            break
        time.sleep(max(1.0, args.interval_sec))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
