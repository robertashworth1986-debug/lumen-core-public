import json
import os
from datetime import datetime, timezone

OUT_DIR = os.path.join("C:\\LumaTrader\\INSTITUTIONAL_STACK_V2\\code", "out", "execution")
DECISION_PATH = os.path.join(OUT_DIR, "moonshot_front_runner_decision.json")
POLICY_PATH = os.path.join(OUT_DIR, "moonshot_allocation_policy.json")
OUT_PATH = os.path.join(OUT_DIR, "moonshot_allocation_plan.json")


def load_json(path, default):
    if not os.path.exists(path):
        return default
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def pick_split(policy: dict, decision_name: str, margin: float):
    splits = policy.get("splits", {})
    margin_gate = float(policy.get("decision_margin_for_full_shift", 0.12))

    if decision_name in {"kraken", "binanceus"} and abs(margin) < margin_gate:
        decision_name = "dual"

    if decision_name in splits:
        split = splits[decision_name]
    else:
        split = policy.get("fallback_if_missing_decision", {"kraken_pct": 50, "binanceus_pct": 50})

    return decision_name, int(split.get("kraken_pct", 0)), int(split.get("binanceus_pct", 0)), margin_gate


def main():
    decision = load_json(DECISION_PATH, {})
    policy = load_json(POLICY_PATH, {})

    chosen = decision.get("decision", {}).get("front_runner", "dual")
    margin = float(decision.get("decision", {}).get("score_margin_kr_minus_bn", 0.0) or 0.0)

    selected_mode, kr_pct, bn_pct, gate = pick_split(policy, chosen, margin)

    capital = float(policy.get("base_capital_usd", 500.0))
    max_risk_pct = float(policy.get("max_total_risk_pct", 1.0))

    out = {
        "generated_utc": datetime.now(timezone.utc).isoformat(),
        "inputs": {
            "decision_path": DECISION_PATH,
            "policy_path": POLICY_PATH,
        },
        "selected_mode": selected_mode,
        "decision_margin_kr_minus_bn": margin,
        "decision_margin_for_full_shift": gate,
        "allocation_pct": {
            "kraken": kr_pct,
            "binanceus": bn_pct,
        },
        "capital_plan_usd": {
            "total": capital,
            "kraken": round(capital * kr_pct / 100.0, 2),
            "binanceus": round(capital * bn_pct / 100.0, 2),
        },
        "risk_plan": {
            "max_total_risk_pct": max_risk_pct,
            "kraken_risk_cap_pct": round(max_risk_pct * kr_pct / 100.0, 4),
            "binanceus_risk_cap_pct": round(max_risk_pct * bn_pct / 100.0, 4),
        },
        "notes": [
            "Routing plan only. Execution module should still enforce per-trade risk and stop rules.",
            "When score margin is small, policy forces dual mode to avoid overfitting/noise shifts."
        ],
    }

    with open(OUT_PATH, "w", encoding="utf-8") as f:
        json.dump(out, f, indent=2)

    print("ALLOCATION_ROUTER_DONE")
    print(f"mode={selected_mode} kraken={kr_pct}% binanceus={bn_pct}% out={OUT_PATH}")


if __name__ == "__main__":
    main()
