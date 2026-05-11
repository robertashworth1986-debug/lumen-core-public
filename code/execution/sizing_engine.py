from dataclasses import dataclass


@dataclass
class SizeInput:
    equity_usd: float
    entry_price: float
    stop_price: float
    realized_vol: float
    edge_score: float
    portfolio_heat: float
    liquidity_score: float = 1.0
    fee_bps: float = 10.0
    slippage_bps: float = 8.0
    urgency: str = "normal"
    dislocation_score: float = 0.0
    drawdown_pct: float = 0.0
    reserve_usd: float = 0.0
    max_notional_usd: float = 0.0


@dataclass
class SizeDecision:
    qty: float
    notional_usd: float
    risk_usd: float
    leverage_hint: float


class SizingEngine:
    def __init__(
        self,
        max_risk_pct: float = 0.0035,
        max_heat: float = 0.02,
        vol_target: float = 0.15,
        max_risk_pct_floor: float = 0.0005,
        max_risk_pct_ceiling: float = 0.02,
    ):
        self.max_risk_pct = max_risk_pct
        self.max_heat = max_heat
        self.vol_target = vol_target
        self.max_risk_pct_floor = max_risk_pct_floor
        self.max_risk_pct_ceiling = max_risk_pct_ceiling

    @staticmethod
    def _urgency_penalty(urgency: str) -> float:
        u = str(urgency or "normal").lower().strip()
        if u == "ultra_aggressive":
            return 1.16
        if u == "aggressive":
            return 1.08
        if u == "passive":
            return 0.92
        return 1.0

    @staticmethod
    def _friction_penalty(fee_bps: float, slippage_bps: float) -> float:
        total_bps = max(float(fee_bps), 0.0) + max(float(slippage_bps), 0.0)
        # 0 bps -> 1.0 ; 100 bps -> 0.5
        return max(0.50, 1.0 - (total_bps / 200.0))

    @staticmethod
    def _drawdown_throttle(drawdown_pct: float) -> float:
        dd = max(float(drawdown_pct), 0.0)
        if dd >= 0.35:
            return 0.20
        if dd >= 0.25:
            return 0.35
        if dd >= 0.15:
            return 0.60
        if dd >= 0.08:
            return 0.80
        return 1.0

    def size(self, x: SizeInput) -> SizeDecision:
        equity = max(float(x.equity_usd), 0.0)
        entry = max(float(x.entry_price), 1e-9)
        stop = max(float(x.stop_price), 1e-9)

        stop_dist = abs(entry - stop)
        if stop_dist <= 1e-9 or equity <= 0:
            return SizeDecision(qty=0.0, notional_usd=0.0, risk_usd=0.0, leverage_hint=1.0)

        # Base risk budget with hard floor/ceiling to avoid runaway sizing.
        risk_pct = min(max(self.max_risk_pct, self.max_risk_pct_floor), self.max_risk_pct_ceiling)
        risk_usd = equity * risk_pct

        # heat haircut
        heat_ratio = min(max(x.portfolio_heat / max(self.max_heat, 1e-9), 0.0), 2.0)
        heat_haircut = max(0.15, 1.0 - 0.5 * heat_ratio)

        # liquidity haircut
        liq = min(max(float(x.liquidity_score), 0.0), 1.0)
        liq_haircut = max(0.15, liq)

        # edge boost
        edge = min(max(float(x.edge_score), 0.0), 1.0)
        edge_boost = 0.35 + (1.40 * edge)  # ~0.35 to 1.75

        # Dislocation boost only applies when edge is already decent.
        dislocation = min(max(float(x.dislocation_score), 0.0), 1.0)
        dislocation_boost = 1.0 + (0.25 * dislocation if edge >= 0.40 else 0.0)

        # vol scaling
        rv = max(float(x.realized_vol), 1e-6)
        vol_scale = min(max(self.vol_target / rv, 0.25), 2.0)

        friction_penalty = self._friction_penalty(float(x.fee_bps), float(x.slippage_bps))
        urgency_penalty = self._urgency_penalty(x.urgency)
        drawdown_throttle = self._drawdown_throttle(float(x.drawdown_pct))

        adj_risk = risk_usd * heat_haircut * liq_haircut * edge_boost * dislocation_boost * vol_scale
        adj_risk *= friction_penalty * urgency_penalty * drawdown_throttle
        qty = max(adj_risk / stop_dist, 0.0)
        notional = qty * entry

        # Respect reserve and optional hard notional cap.
        reserve = max(float(x.reserve_usd), 0.0)
        affordable = max(equity - reserve, 0.0)
        if affordable <= 0.0:
            return SizeDecision(qty=0.0, notional_usd=0.0, risk_usd=0.0, leverage_hint=1.0)

        cap = max(float(x.max_notional_usd), 0.0)
        if cap > 0.0:
            affordable = min(affordable, cap)

        if notional > affordable:
            scale = affordable / max(notional, 1e-9)
            qty *= scale
            notional = affordable
            adj_risk *= scale

        leverage_hint = min(max(vol_scale, 0.5), 3.0)
        return SizeDecision(qty=qty, notional_usd=notional, risk_usd=adj_risk, leverage_hint=leverage_hint)
