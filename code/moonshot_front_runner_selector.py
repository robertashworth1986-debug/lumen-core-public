import json
import math
import os
from datetime import datetime, timezone

OUT_DIR = os.path.join("C:\\LumaTrader\\INSTITUTIONAL_STACK_V2\\code", "out", "execution")
HORIZON_PATH = os.path.join(OUT_DIR, "moonshot_horizon_performance.json")
LATEST_PATH = os.path.join(OUT_DIR, "moonshot_dual_scan_latest.json")
OUT_PATH = os.path.join(OUT_DIR, "moonshot_front_runner_decision.json")

H_WEIGHTS = {
    "5m": 0.05,
    "15m": 0.08,
    "30m": 0.10,
    "1h": 0.12,
    "3h": 0.15,
    "8h": 0.15,
    "1d": 0.15,
    "1w": 0.10,
    "1m": 0.10,
}


def load_json(path, default):
    if not os.path.exists(path):
        return default
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def safe_float(v, default=0.0):
    try:
        if v is None:
            return default
        return float(v)
    except Exception:
        return default


def reliability(samples: int) -> float:
    # Saturates toward 1.0 as we collect more samples.
    return min(1.0, max(0.0, samples / 80.0))


def horizon_score(exchange_summary: dict) -> dict:
    weighted = 0.0
    weight_used = 0.0
    sample_total = 0

    for h, w in H_WEIGHTS.items():
        hs = exchange_summary.get(h, {})
        med_ret = hs.get("median_ret")
        samples = int(hs.get("samples", 0) or 0)
        if med_ret is None:
            continue
        r = reliability(samples)
        weighted += w * safe_float(med_ret) * r
        weight_used += w
        sample_total += samples

    normalized = (weighted / weight_used) if weight_used > 0 else 0.0
    return {
        "horizon_weighted_score": normalized,
        "horizon_samples_total": sample_total,
        "horizon_weight_used": weight_used,
    }


def quality_signal(top_targets: list) -> dict:
    if not top_targets:
        return {"avg_quality": 0.0, "target_count": 0, "quality_score": 0.0}

    qs = [safe_float(t.get("quality_score"), 0.0) for t in top_targets]
    avg_q = sum(qs) / len(qs)
    cnt = len(top_targets)

    # 0..1 quality signal from quality score plus count depth.
    q_norm = max(0.0, min(1.0, avg_q / 100.0))
    c_norm = max(0.0, min(1.0, math.log10(cnt + 1) / math.log10(16)))
    score = 0.7 * q_norm + 0.3 * c_norm

    return {
        "avg_quality": avg_q,
        "target_count": cnt,
        "quality_score": score,
    }


def blended_score(horizon_part: dict, quality_part: dict) -> float:
    # Horizon returns drive most of decision; quality/coverage acts as tie-break pressure.
    # Scale horizon into ~[-1,1] like quality score.
    h = horizon_part["horizon_weighted_score"] * 8.0
    q = quality_part["quality_score"]
    return 0.75 * h + 0.25 * q


def main():
    horizon = load_json(HORIZON_PATH, {})
    latest = load_json(LATEST_PATH, {})

    ex_summary = horizon.get("exchange_horizon_summary", {})
    kr_h = horizon_score(ex_summary.get("kraken", {}))
    bn_h = horizon_score(ex_summary.get("binanceus", {}))

    kr_latest = latest.get("kraken", {})
    bn_latest = latest.get("binanceus", {})
    kr_q = quality_signal(kr_latest.get("top_targets", []))
    bn_q = quality_signal(bn_latest.get("top_targets", []))

    kr_score = blended_score(kr_h, kr_q)
    bn_score = blended_score(bn_h, bn_q)

    # Conservative decision rule: require margin, else run dual.
    margin = kr_score - bn_score
    if margin > 0.06:
        decision = "kraken"
    elif margin < -0.06:
        decision = "binanceus"
    else:
        decision = "dual"

    out = {
        "generated_utc": datetime.now(timezone.utc).isoformat(),
        "inputs": {
            "horizon_path": HORIZON_PATH,
            "latest_scan_path": LATEST_PATH,
        },
        "scores": {
            "kraken": {
                **kr_h,
                **kr_q,
                "blended_score": kr_score,
            },
            "binanceus": {
                **bn_h,
                **bn_q,
                "blended_score": bn_score,
            },
        },
        "decision": {
            "front_runner": decision,
            "score_margin_kr_minus_bn": margin,
            "rationale": "Horizon-weighted realized returns + current target quality/coverage.",
        },
    }

    with open(OUT_PATH, "w", encoding="utf-8") as f:
        json.dump(out, f, indent=2)

    print("FRONT_RUNNER_DONE")
    print(f"decision={decision} margin={margin:.5f} out={OUT_PATH}")


if __name__ == "__main__":
    main()
