import json
import os
from datetime import datetime, timezone

OUT_DIR = os.path.join("C:\\LumaTrader\\INSTITUTIONAL_STACK_V2\\code", "out", "execution")
LATEST_PATH = os.path.join(OUT_DIR, "moonshot_dual_scan_latest.json")
ALLOCATION_PATH = os.path.join(OUT_DIR, "moonshot_allocation_plan.json")
OUT_PATH = os.path.join(OUT_DIR, "moonshot_execution_handoff.json")


def load_json(path, default):
    if not os.path.exists(path):
        return default
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def safe_float(v, default=0.0):
    try:
        return float(v)
    except Exception:
        return default


def allocate_for_exchange(targets, capital_usd, portfolio_capital_usd, risk_cap_pct, top_n=8):
    if not targets or capital_usd <= 0:
        return []

    ranked = sorted(
        targets,
        key=lambda x: (
            safe_float(x.get("quality_score"), 0.0),
            safe_float(x.get("discount_from_high"), 0.0),
            safe_float(x.get("turnover_24h_usd"), 0.0),
        ),
        reverse=True,
    )[:top_n]

    total_quality = sum(max(0.01, safe_float(t.get("quality_score"), 0.0)) for t in ranked)
    total_risk_pct = max(0.0, risk_cap_pct)

    out = []
    for t in ranked:
        q = max(0.01, safe_float(t.get("quality_score"), 0.0))
        w = q / total_quality if total_quality > 0 else 1.0 / len(ranked)

        alloc_usd = capital_usd * w
        risk_pct = total_risk_pct * w
        stop_pct = 0.03  # fixed default stop budget for now

        if stop_pct > 0:
            # Risk model: quantity so max stop loss ~= allocated risk budget.
            max_risk_usd = portfolio_capital_usd * risk_pct
            notional_usd = max_risk_usd / stop_pct if max_risk_usd > 0 else 0.0
            order_notional_usd = min(alloc_usd, notional_usd)
        else:
            order_notional_usd = alloc_usd

        out.append(
            {
                "exchange": t.get("exchange"),
                "symbol": t.get("symbol"),
                "quality_score": round(q, 4),
                "discount_from_high": round(safe_float(t.get("discount_from_high"), 0.0), 6),
                "turnover_24h_usd": round(safe_float(t.get("turnover_24h_usd"), 0.0), 2),
                "entry_price_snapshot": safe_float(t.get("price"), 0.0),
                "weight": round(w, 6),
                "capital_allocation_usd": round(alloc_usd, 2),
                "risk_cap_pct_of_portfolio": round(risk_pct, 6),
                "stop_loss_pct": stop_pct,
                "max_order_notional_usd": round(order_notional_usd, 2),
                "status": "approved",
            }
        )

    return out


def main():
    latest = load_json(LATEST_PATH, {})
    plan = load_json(ALLOCATION_PATH, {})

    cap = plan.get("capital_plan_usd", {})
    risk = plan.get("risk_plan", {})

    kr_cap = safe_float(cap.get("kraken", 0.0))
    bn_cap = safe_float(cap.get("binanceus", 0.0))
    total_cap = safe_float(cap.get("total", kr_cap + bn_cap))
    kr_risk = safe_float(risk.get("kraken_risk_cap_pct", 0.0)) / 100.0
    bn_risk = safe_float(risk.get("binanceus_risk_cap_pct", 0.0)) / 100.0

    kr_targets = latest.get("kraken", {}).get("top_targets", [])
    bn_targets = latest.get("binanceus", {}).get("top_targets", [])

    kr_orders = allocate_for_exchange(kr_targets, kr_cap, total_cap, kr_risk, top_n=8)
    bn_orders = allocate_for_exchange(bn_targets, bn_cap, total_cap, bn_risk, top_n=8)

    all_orders = kr_orders + bn_orders
    all_orders.sort(key=lambda x: x["capital_allocation_usd"], reverse=True)

    out = {
        "generated_utc": datetime.now(timezone.utc).isoformat(),
        "inputs": {
            "latest_scan": LATEST_PATH,
            "allocation_plan": ALLOCATION_PATH,
        },
        "execution_mode": plan.get("selected_mode", "dual"),
        "order_count": len(all_orders),
        "orders": all_orders,
        "notes": [
            "This is an execution handoff plan. Final live execution must enforce exchange min notional, fees, and slippage guards.",
            "Per-order notional is capped by both allocation and risk-based stop-loss budget.",
        ],
    }

    with open(OUT_PATH, "w", encoding="utf-8") as f:
        json.dump(out, f, indent=2)

    print("EXECUTION_HANDOFF_DONE")
    print(f"orders={len(all_orders)} out={OUT_PATH}")


if __name__ == "__main__":
    main()
