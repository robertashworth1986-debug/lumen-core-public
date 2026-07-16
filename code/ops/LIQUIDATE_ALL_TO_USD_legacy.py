#!/usr/bin/env python3
import argparse
import json
import math
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import requests

ROOT = Path(r"C:\LumaTrader\INSTITUTIONAL_STACK_V2")
CODE_DIR = ROOT / "code"
OUT_OPS_DIR = ROOT / "out" / "ops"
OUT_EXEC_DIR = ROOT / "out" / "execution"

sys.path.insert(0, str(CODE_DIR))

from kraken_execution import _private_post, arm_deadman_switch, get_balance  # noqa: E402

KRAKEN_PUBLIC_URL = "https://api.kraken.com/0/public/AssetPairs"
USD_QUOTES = {"ZUSD", "USD"}
USDT_QUOTES = {"USDT", "XUSDT", "ZUSDT"}
USD_ASSETS = {"ZUSD", "USD"}
USDT_ASSETS = {"USDT", "XUSDT", "ZUSDT"}
SELL_BUFFER = 0.998


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def ts_compact() -> str:
    return utc_now().strftime("%Y%m%dT%H%M%SZ")


def safe_float(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except Exception:
        return default


def floor_to_decimals(value: float, decimals: int) -> float:
    if decimals <= 0:
        return math.floor(value)
    factor = 10 ** decimals
    return math.floor(value * factor) / factor


def fetch_asset_pairs() -> dict[str, dict[str, Any]]:
    r = requests.get(KRAKEN_PUBLIC_URL, timeout=30)
    r.raise_for_status()
    payload = r.json()
    errs = payload.get("error") or []
    if errs:
        raise RuntimeError("Kraken AssetPairs error: " + "; ".join(str(x) for x in errs))
    result = payload.get("result")
    if not isinstance(result, dict):
        raise RuntimeError("Kraken AssetPairs result missing")
    return result


def pick_pair(
    asset: str,
    all_pairs: dict[str, dict[str, Any]],
    quote_targets: set[str],
) -> dict[str, Any] | None:
    candidates: list[dict[str, Any]] = []
    base_target = str(asset).upper().strip()

    for _, meta in all_pairs.items():
        if not isinstance(meta, dict):
            continue
        base = str(meta.get("base", "")).upper().strip()
        quote = str(meta.get("quote", "")).upper().strip()
        if base != base_target:
            continue
        if quote not in quote_targets:
            continue

        altname = str(meta.get("altname", "")).strip() or str(meta.get("wsname", "")).split("/")[0]
        if not altname:
            continue

        candidates.append(
            {
                "pair": altname,
                "base": base,
                "quote": quote,
                "ordermin": safe_float(meta.get("ordermin", 0.0), 0.0),
                "lot_decimals": int(meta.get("lot_decimals", 8) or 8),
            }
        )

    if not candidates:
        return None

    # Prefer native USD quote first when multiple aliases exist.
    candidates.sort(key=lambda c: (0 if c["quote"] in USD_QUOTES else 1, c["pair"]))
    return candidates[0]


def build_sell_order(amount: float, pair_meta: dict[str, Any]) -> tuple[float, str | None]:
    lot_decimals = int(pair_meta.get("lot_decimals", 8) or 8)
    ordermin = max(safe_float(pair_meta.get("ordermin", 0.0), 0.0), 0.0)
    buffered = max(float(amount) * SELL_BUFFER, 0.0)
    volume = floor_to_decimals(buffered, lot_decimals)
    raw_volume = floor_to_decimals(max(float(amount), 0.0), lot_decimals)

    if volume <= 0.0:
        if raw_volume > 0.0:
            volume = raw_volume
        else:
            return 0.0, "volume_zero_after_rounding"

    # For balances near Kraken minimums, buffered sizing can fall just under ordermin.
    # If the raw rounded size satisfies ordermin, prefer raw size.
    if ordermin > 0.0 and volume + 1e-12 < ordermin and raw_volume + 1e-12 >= ordermin:
        volume = raw_volume

    if ordermin > 0.0 and volume + 1e-12 < ordermin:
        return 0.0, f"below_ordermin({ordermin})"
    return volume, None


def nonzero_balance(balance: dict[str, Any]) -> dict[str, float]:
    out: dict[str, float] = {}
    for k, v in balance.items():
        amount = safe_float(v, 0.0)
        if abs(amount) > 0.0:
            out[str(k).upper()] = amount
    return out


def submit_market_sell(pair: str, volume: float) -> dict[str, Any]:
    payload = {
        "pair": pair,
        "type": "sell",
        "ordertype": "market",
        "volume": f"{float(volume):.8f}",
    }
    return _private_post("/0/private/AddOrder", payload)


def main() -> None:
    parser = argparse.ArgumentParser(description="Liquidate Kraken holdings into USD")
    parser.add_argument("--execute", action="store_true", help="Place live market sell orders")
    parser.add_argument(
        "--include-fiat",
        action="store_true",
        help="Also try converting non-USD fiat balances (default: skip non-USD fiat)",
    )
    args = parser.parse_args()

    OUT_OPS_DIR.mkdir(parents=True, exist_ok=True)
    OUT_EXEC_DIR.mkdir(parents=True, exist_ok=True)

    started = utc_now().isoformat()

    pairs = fetch_asset_pairs()
    start_balance = nonzero_balance(get_balance())

    actions: list[dict[str, Any]] = []
    skipped: list[dict[str, Any]] = []

    # Phase 1: sell each non-USD, non-USDT asset to USD directly when possible, else USDT fallback.
    for asset in sorted(start_balance.keys()):
        amount = max(start_balance.get(asset, 0.0), 0.0)
        if amount <= 0.0:
            continue
        if asset in USD_ASSETS:
            continue

        # Skip non-USD fiat by default (user asked all crypto).
        if (not args.include_fiat) and asset.startswith("Z") and asset not in USD_ASSETS and asset not in USDT_ASSETS:
            skipped.append({"asset": asset, "amount": amount, "reason": "non_usd_fiat_skipped"})
            continue

        if asset in USDT_ASSETS:
            # Converted in phase 2 after collecting any additional USDT from fallback sales.
            continue

        pair_meta = pick_pair(asset, pairs, USD_QUOTES)
        route = "direct_usd"
        if pair_meta is None:
            pair_meta = pick_pair(asset, pairs, USDT_QUOTES)
            route = "via_usdt"

        if pair_meta is None:
            skipped.append({"asset": asset, "amount": amount, "reason": "no_usd_or_usdt_pair"})
            continue

        volume, issue = build_sell_order(amount, pair_meta)
        if issue:
            skipped.append(
                {
                    "asset": asset,
                    "amount": amount,
                    "pair": pair_meta.get("pair"),
                    "reason": issue,
                }
            )
            continue

        action = {
            "asset": asset,
            "amount": amount,
            "pair": pair_meta.get("pair"),
            "route": route,
            "volume": volume,
            "status": "planned",
        }

        if args.execute:
            try:
                result = submit_market_sell(str(pair_meta.get("pair")), float(volume))
                action["status"] = "submitted"
                action["result"] = result
            except Exception as exc:
                action["status"] = "error"
                action["error"] = str(exc)

        actions.append(action)

    # Phase 2: convert any USDT balance to USD.
    if args.execute:
        live_balance = nonzero_balance(get_balance())
    else:
        live_balance = dict(start_balance)

    usdt_total = sum(max(live_balance.get(code, 0.0), 0.0) for code in USDT_ASSETS)
    usdt_asset = next((code for code in USDT_ASSETS if max(live_balance.get(code, 0.0), 0.0) > 0.0), "USDT")
    if usdt_total > 0.0:
        usdt_pair = pick_pair(usdt_asset, pairs, USD_QUOTES)
        if usdt_pair is None:
            skipped.append({"asset": usdt_asset, "amount": usdt_total, "reason": "usdt_usd_pair_missing"})
        else:
            volume, issue = build_sell_order(usdt_total, usdt_pair)
            if issue:
                skipped.append(
                    {
                        "asset": usdt_asset,
                        "amount": usdt_total,
                        "pair": usdt_pair.get("pair"),
                        "reason": issue,
                    }
                )
            else:
                action = {
                    "asset": usdt_asset,
                    "amount": usdt_total,
                    "pair": usdt_pair.get("pair"),
                    "route": "usdt_to_usd",
                    "volume": volume,
                    "status": "planned",
                }
                if args.execute:
                    try:
                        result = submit_market_sell(str(usdt_pair.get("pair")), float(volume))
                        action["status"] = "submitted"
                        action["result"] = result
                    except Exception as exc:
                        action["status"] = "error"
                        action["error"] = str(exc)
                actions.append(action)

    if args.execute:
        try:
            deadman = arm_deadman_switch(60)
        except Exception as exc:
            deadman = {"error": str(exc)}
    else:
        deadman = {"status": "dry_run"}

    end_balance = nonzero_balance(get_balance()) if args.execute else {}

    report = {
        "generated_utc": utc_now().isoformat(),
        "scope": "liquidate_all_to_usd",
        "execute": bool(args.execute),
        "started_utc": started,
        "deadman": deadman,
        "start_balance": start_balance,
        "actions": actions,
        "skipped": skipped,
        "end_balance": end_balance,
        "summary": {
            "planned_count": len(actions),
            "submitted_count": sum(1 for a in actions if a.get("status") == "submitted"),
            "error_count": sum(1 for a in actions if a.get("status") == "error"),
            "skipped_count": len(skipped),
        },
    }

    stamp = ts_compact()
    out_json = OUT_OPS_DIR / f"liquidate_all_to_usd_{stamp}.json"
    latest = OUT_EXEC_DIR / "liquidate_all_to_usd_latest.json"
    out_json.write_text(json.dumps(report, indent=2), encoding="utf-8")
    latest.write_text(json.dumps(report, indent=2), encoding="utf-8")

    print(json.dumps({
        "status": "ok",
        "execute": bool(args.execute),
        "submitted_count": report["summary"]["submitted_count"],
        "error_count": report["summary"]["error_count"],
        "skipped_count": report["summary"]["skipped_count"],
        "out_json": str(out_json),
        "latest": str(latest),
    }, indent=2))


if __name__ == "__main__":
    main()
