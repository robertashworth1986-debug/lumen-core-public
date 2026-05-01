from dataclasses import dataclass

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
