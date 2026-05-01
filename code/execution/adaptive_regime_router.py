from __future__ import annotations

from typing import Any


def _f(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except Exception:
        return float(default)


def _clamp(value: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, value))


def route_equity_signal(
    *,
    day_return: float,
    minute_return: float,
    near_high: float,
    volume_impulse: float,
    momentum_breadth: float = 0.5,
) -> dict[str, Any]:
    trend_strength = (
        max(day_return, 0.0) * 140.0
        + max(minute_return, 0.0) * 180.0
        + max(near_high, 0.0) * 18.0
        + min(max(volume_impulse, 0.0), 5.0) * 2.5
    )
    reversal_strength = (
        max(-day_return, 0.0) * 160.0
        + max(minute_return, 0.0) * 120.0
        + max(0.55 - near_high, 0.0) * 32.0
        + min(max(volume_impulse, 0.0), 5.0) * 2.0
    )

    state = "neutral"
    preferred_family = "neutral"
    heat_multiplier = 0.88
    confidence_multiplier = 0.92
    rationale = "Tape is mixed; keep entries selective."

    if trend_strength >= reversal_strength + 0.60 and day_return >= 0.0 and near_high >= 0.58:
        state = "trend"
        preferred_family = "breakout"
        heat_multiplier = 1.05 if momentum_breadth >= 0.35 else 0.96
        confidence_multiplier = 1.06 if momentum_breadth >= 0.35 else 0.98
        rationale = "Positive breadth and high-location strength favor continuation entries."
    elif reversal_strength > trend_strength and day_return <= 0.01 and minute_return >= -0.0015:
        state = "reversal"
        preferred_family = "mean_reversion"
        heat_multiplier = 0.94
        confidence_multiplier = 1.02
        rationale = "Oversold dislocation with stabilization favors controlled snapback entries."

    family_gap = abs(trend_strength - reversal_strength)
    family_confidence = _clamp(0.50 + family_gap / 24.0, 0.50, 0.98)

    return {
        "state": state,
        "preferred_family": preferred_family,
        "trend_strength": round(trend_strength, 6),
        "reversal_strength": round(reversal_strength, 6),
        "family_confidence": round(family_confidence, 6),
        "heat_multiplier": round(heat_multiplier, 6),
        "confidence_multiplier": round(confidence_multiplier, 6),
        "rationale": rationale,
    }


def route_crypto_signal(
    *,
    pct24: float,
    r2: float,
    r4: float,
    near_high: float,
    dislocation_score: float,
    breadth_pos_pct24: float = 0.5,
    realized_vol_pct: float = 0.0,
) -> dict[str, Any]:
    breakout_strength = (
        max(pct24, 0.0) * 18.0
        + max(r2, 0.0) * 120.0
        + max(r4, 0.0) * 80.0
        + max(near_high, 0.0) * 12.0
        + max(breadth_pos_pct24 - 0.5, 0.0) * 40.0
    )
    reversion_strength = (
        max(dislocation_score, 0.0) * 1.35
        + max(-pct24, 0.0) * 14.0
        + max(0.55 - near_high, 0.0) * 18.0
        + max(r2, 0.0) * 40.0
    )

    state = "balanced"
    preferred_family = "balanced"
    heat_multiplier = 1.0
    risk_multiplier = 1.0
    rationale = "Breadth and dispersion are balanced across crypto sleeves."

    if realized_vol_pct >= 0.035 and breadth_pos_pct24 <= 0.45:
        state = "stress_reversal"
        preferred_family = "dislocation"
        heat_multiplier = 0.82
        risk_multiplier = 1.18
        rationale = "High volatility and weak breadth favor dislocation entries over momentum chasing."
    elif breakout_strength >= reversion_strength and breadth_pos_pct24 >= 0.55 and near_high >= 0.58:
        state = "expansion"
        preferred_family = "breakout"
        heat_multiplier = 1.06
        risk_multiplier = 0.92
        rationale = "Broad participation and trend persistence support breakout allocation."
    elif reversion_strength > breakout_strength:
        state = "reversion"
        preferred_family = "dislocation"
        heat_multiplier = 0.90
        risk_multiplier = 1.08
        rationale = "Dislocation intensity outweighs breakout quality; snapback sleeve gets priority."

    family_gap = abs(breakout_strength - reversion_strength)
    family_confidence = _clamp(0.48 + family_gap / 30.0, 0.48, 0.98)

    return {
        "state": state,
        "preferred_family": preferred_family,
        "breakout_strength": round(breakout_strength, 6),
        "reversion_strength": round(reversion_strength, 6),
        "family_confidence": round(family_confidence, 6),
        "heat_multiplier": round(heat_multiplier, 6),
        "risk_multiplier": round(risk_multiplier, 6),
        "rationale": rationale,
    }


def route_sports_signal(
    *,
    signal_type: str,
    edge_pct: float,
    ev_pct: float | None,
    change_pct: float = 0.0,
    softness_score: float = 0.5,
) -> dict[str, Any]:
    signal_type = str(signal_type or "").lower()
    ev_value = _f(ev_pct, 0.0)
    edge_value = _f(edge_pct, 0.0)
    move_value = _f(change_pct, 0.0)

    momentum_strength = 0.0
    reversion_strength = 0.0

    if signal_type == "arbitrage":
        momentum_strength = edge_value * 1.40
        rationale = "Cross-book dislocation is immediately executable and should be prioritized."
    elif signal_type == "line_gap":
        momentum_strength = edge_value * 0.65 + move_value * 0.55
        reversion_strength = edge_value * 0.55 + max(softness_score - 0.45, 0.0) * 18.0
        rationale = "Line dispersion can resolve through follow-through or soft-book snapback."
    else:
        momentum_strength = max(ev_value, 0.0) * 0.75 + edge_value * 0.35
        reversion_strength = max(ev_value, 0.0) * 0.95 + max(softness_score - 0.40, 0.0) * 16.0
        rationale = "Positive EV value bets are best treated as controlled price reversion."

    preferred_family = "neutral"
    state = "balanced"
    if signal_type == "arbitrage" or momentum_strength >= reversion_strength + 0.50:
        preferred_family = "momentum_capture"
        state = "execution_window"
    elif reversion_strength > momentum_strength:
        preferred_family = "mean_reversion"
        state = "price_reversion"

    family_gap = abs(momentum_strength - reversion_strength)
    family_confidence = _clamp(0.52 + family_gap / 20.0, 0.52, 0.99)

    return {
        "state": state,
        "preferred_family": preferred_family,
        "momentum_strength": round(momentum_strength, 6),
        "reversion_strength": round(reversion_strength, 6),
        "family_confidence": round(family_confidence, 6),
        "softness_score": round(_clamp(_f(softness_score, 0.5), 0.0, 1.0), 6),
        "rationale": rationale,
    }