from dataclasses import dataclass
import math

@dataclass
class LiquiditySnapshot:
    bid: float
    ask: float
    bid_size: float
    ask_size: float
    est_sweep_cost_bps: float
    quote_update_rate: float

@dataclass
class LiquidityDecision:
    pass_trade: bool
    score: float
    max_notional_usd: float
    reasons: list

class LiquidityGuard:
    def evaluate_kpis(self, context=None):
        """Stub for compatibility. Returns empty dict."""
        return {}

    def assess(self, snap: LiquiditySnapshot) -> LiquidityDecision:
        reasons = []
        values = (snap.bid, snap.ask, snap.bid_size, snap.ask_size,
                  snap.est_sweep_cost_bps, snap.quote_update_rate)
        try:
            valid = all(not isinstance(v, bool) and math.isfinite(v) for v in values)
            valid = valid and snap.bid > 0 and snap.ask >= snap.bid
            valid = valid and snap.bid_size > 0 and snap.ask_size > 0
            valid = valid and snap.est_sweep_cost_bps >= 0 and snap.quote_update_rate >= 0
        except (TypeError, ValueError):
            valid = False
        if not valid:
            return LiquidityDecision(False, 0.0, 0.0, ["invalid_liquidity_snapshot"])
        mid = (snap.bid + snap.ask) / 2
        spread_bps = ((snap.ask - snap.bid) / max(mid, 1e-9)) * 10000
        score = 1.0

        if spread_bps > 8:
            score -= 0.35
            reasons.append("wide_spread")
        if min(snap.bid_size, snap.ask_size) < 0.01:
            score -= 0.25
            reasons.append("thin_top_book")
        if snap.est_sweep_cost_bps > 12:
            score -= 0.25
            reasons.append("high_sweep_cost")
        if snap.quote_update_rate > 20:
            score -= 0.10
            reasons.append("unstable_quotes")

        score = max(0.0, min(1.0, score))
        return LiquidityDecision(
            pass_trade=score >= 0.45,
            score=float(score),
            max_notional_usd=float(2000 * score),
            reasons=reasons
        )
