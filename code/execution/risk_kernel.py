from dataclasses import dataclass

@dataclass
class RiskState:
    day_pnl_usd: float
    open_risk_usd: float
    portfolio_heat: float
    symbol_cooldown_active: bool
    open_positions: int
    max_open_positions: int
    live_mode: bool
    kill_switch: bool

class RiskKernel:
    def __init__(self, max_daily_loss_usd: float = 20.0, max_heat: float = 0.02):
        self.max_daily_loss_usd = max_daily_loss_usd
        self.max_heat = max_heat

    def allow(self, s: RiskState) -> tuple:
        reasons = []
        if s.kill_switch:
            reasons.append("kill_switch_on")
        if s.day_pnl_usd <= -self.max_daily_loss_usd:
            reasons.append("daily_loss_limit_hit")
        if s.portfolio_heat > self.max_heat:
            reasons.append("portfolio_heat_too_high")
        if s.symbol_cooldown_active:
            reasons.append("symbol_cooldown")
        if s.open_positions >= s.max_open_positions:
            reasons.append("max_positions_reached")
        return (len(reasons) == 0, reasons)
