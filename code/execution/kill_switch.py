import json
from dataclasses import dataclass

@dataclass
class KillInput:
    day_pnl_usd: float
    rejected_orders: int
    avg_slip_bps: float
    api_healthy: bool
    max_daily_loss_usd: float
    max_avg_slip_bps: float

class KillSwitch:
    def __init__(self, runtime_control_path: str):
        self.runtime_control_path = runtime_control_path

    def evaluate(self, x: KillInput) -> tuple:
        reasons = []
        if not x.api_healthy:
            reasons.append("api_unhealthy")
        if x.day_pnl_usd <= -x.max_daily_loss_usd:
            reasons.append("daily_loss_limit")
        if x.rejected_orders >= 3:
            reasons.append("too_many_rejections")
        if x.avg_slip_bps >= x.max_avg_slip_bps:
            reasons.append("slippage_breach")
        return (len(reasons) > 0, reasons)

    def trip(self, reasons: list) -> None:
        with open(self.runtime_control_path, "r", encoding="utf-8") as f:
            rt = json.load(f)
        rt["kill_switch"] = True
        rt["allow_live_orders"] = False
        rt["mode"] = "paper"
        rt["kill_reasons"] = reasons
        with open(self.runtime_control_path, "w", encoding="utf-8") as f:
            json.dump(rt, f, indent=2)
