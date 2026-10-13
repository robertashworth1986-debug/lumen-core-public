from dataclasses import dataclass
import math

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
        if not math.isfinite(max_daily_loss_usd) or max_daily_loss_usd <= 0:
            raise ValueError("max_daily_loss_usd must be finite and positive")
        if not math.isfinite(max_heat) or not 0 < max_heat <= 1:
            raise ValueError("max_heat must be a finite fraction in (0, 1]")
        self.max_daily_loss_usd = max_daily_loss_usd
        self.max_heat = max_heat

    def allow(self, s: RiskState) -> tuple:
        reasons = []
        # Unknown or malformed account state cannot authorize risk. NaN otherwise
        # passes every ordered comparison below and used to return allow=True.
        numeric = (s.day_pnl_usd, s.open_risk_usd, s.portfolio_heat,
                   self.max_daily_loss_usd, self.max_heat)
        try:
            valid_numbers = all(not isinstance(v, bool) and math.isfinite(v) for v in numeric)
            valid_counts = all(type(v) is int and v >= 0 for v in (s.open_positions, s.max_open_positions))
            valid_flags = all(type(v) is bool for v in (s.symbol_cooldown_active, s.live_mode, s.kill_switch))
            valid_ranges = s.open_risk_usd >= 0 and 0 <= s.portfolio_heat <= 1 and self.max_daily_loss_usd > 0 and 0 < self.max_heat <= 1
        except (TypeError, ValueError):
            return (False, ["invalid_risk_state"])
        if not (valid_numbers and valid_counts and valid_flags and valid_ranges):
            return (False, ["invalid_risk_state"])
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
