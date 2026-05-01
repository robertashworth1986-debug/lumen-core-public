from __future__ import annotations

from typing import Any, Dict, List

from execution.adaptive_regime_router import route_crypto_signal

try:
    from arch import arch_model
except Exception:
    arch_model = None

try:
    from river import stats as river_stats
except Exception:
    river_stats = None


def _f(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except Exception:
        return float(default)


def _returns(prices: List[float]) -> List[float]:
    out: List[float] = []
    for idx in range(1, len(prices)):
        p0 = _f(prices[idx - 1], 0.0)
        p1 = _f(prices[idx], 0.0)
        if p0 > 0.0 and p1 > 0.0:
            out.append((p1 / p0) - 1.0)
    return out


def infer_market_regime(
    history: Dict[str, List[float]],
    hybrid_ranked: List[Dict[str, Any]],
    breadth_pos_pct24: float,
    prior_state: Dict[str, Any] | None = None,
) -> Dict[str, Any]:
    btc_prices = history.get("BTCUSDT") or history.get("BTCUSD") or []
    btc_returns = _returns(btc_prices if isinstance(btc_prices, list) else [])

    realized_vol = sum(abs(value) for value in btc_returns) / len(btc_returns) if btc_returns else 0.0
    arch_vol = None
    if arch_model is not None and len(btc_returns) >= 16:
        try:
            model = arch_model([value * 100.0 for value in btc_returns], p=1, q=1, mean="zero", vol="GARCH", dist="normal")
            fit = model.fit(disp="off")
            arch_vol = abs(float(fit.conditional_volatility.iloc[-1])) / 100.0
        except Exception:
            arch_vol = None

    online_mean = 0.0
    online_vol = 0.0
    if river_stats is not None and btc_returns:
        mean_est = river_stats.Mean()
        var_est = river_stats.Var()
        for value in btc_returns:
            mean_est.update(value)
            var_est.update(value)
        online_mean = float(mean_est.get() or 0.0)
        variance = float(var_est.get() or 0.0)
        online_vol = variance ** 0.5 if variance > 0.0 else 0.0

    breadth = _f(breadth_pos_pct24, 0.5)
    top_edge = max(_f(hybrid_ranked[0].get("hybrid_score"), 0.0), 0.0) if hybrid_ranked else 0.0
    top_slice = [_f(item.get("hybrid_score"), 0.0) for item in hybrid_ranked[:10]]
    median_edge = sorted(top_slice)[len(top_slice) // 2] if top_slice else 0.0
    vol_proxy = max(realized_vol, _f(arch_vol, 0.0), online_vol)

    router_votes = {"breakout": 0.0, "dislocation": 0.0}
    router_conf_sum = 0.0
    for item in hybrid_ranked[:12]:
        routed = route_crypto_signal(
            pct24=_f(item.get("pct24"), 0.0),
            r2=_f(item.get("r2"), 0.0),
            r4=_f(item.get("r4"), 0.0),
            near_high=_f(item.get("near_high"), 0.0),
            dislocation_score=_f(item.get("dislocation_score"), 0.0),
            breadth_pos_pct24=breadth,
            realized_vol_pct=vol_proxy,
        )
        family = str(routed.get("preferred_family", "balanced"))
        conf = _f(routed.get("family_confidence"), 0.5)
        router_conf_sum += conf
        if family == "breakout":
            router_votes["breakout"] += conf
        elif family == "dislocation":
            router_votes["dislocation"] += conf

    regime = "balanced"
    heat_multiplier = 1.0
    risk_aversion_multiplier = 1.0
    confidence_multiplier = 1.0
    rationale = "Breadth and volatility are in the middle regime."
    if vol_proxy >= 0.035 or breadth <= 0.40:
        regime = "defensive"
        heat_multiplier = 0.72
        risk_aversion_multiplier = 1.35
        confidence_multiplier = 0.85
        rationale = "Elevated realized volatility or narrow breadth triggered defensive capital discipline."
    elif breadth >= 0.62 and top_edge >= max(median_edge, 0.45):
        regime = "expansion"
        heat_multiplier = 1.05
        risk_aversion_multiplier = 0.88
        confidence_multiplier = 1.10
        rationale = "Broad positive participation and strong top-edge conditions support controlled expansion."

    preferred_family = "balanced"
    if router_votes["breakout"] > router_votes["dislocation"]:
        preferred_family = "breakout"
    elif router_votes["dislocation"] > router_votes["breakout"]:
        preferred_family = "dislocation"

    if preferred_family == "dislocation" and regime == "expansion":
        regime = "reversion"
        heat_multiplier = min(heat_multiplier, 0.92)
        risk_aversion_multiplier = max(risk_aversion_multiplier, 1.05)
        confidence_multiplier = min(confidence_multiplier, 0.98)
        rationale = "Shared router detected stronger dislocation conditions than continuation despite broad tape strength."

    return {
        "regime": regime,
        "breadth_pos_pct24": round(breadth, 6),
        "realized_vol_pct": round(realized_vol, 6),
        "arch_vol_pct": round(_f(arch_vol, 0.0), 6),
        "online_mean_return": round(online_mean, 6),
        "online_vol_pct": round(online_vol, 6),
        "top_edge": round(top_edge, 6),
        "median_edge": round(median_edge, 6),
        "heat_multiplier": round(heat_multiplier, 6),
        "risk_aversion_multiplier": round(risk_aversion_multiplier, 6),
        "confidence_multiplier": round(confidence_multiplier, 6),
        "preferred_family": preferred_family,
        "family_confidence": round(router_conf_sum / max(min(len(hybrid_ranked[:12]), 12), 1), 6),
        "router_votes": {
            "breakout": round(router_votes["breakout"], 6),
            "dislocation": round(router_votes["dislocation"], 6),
        },
        "rationale": rationale,
        "prior_regime": str((prior_state or {}).get("regime", "n/a")),
    }