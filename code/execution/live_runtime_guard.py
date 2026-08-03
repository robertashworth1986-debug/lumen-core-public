import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Tuple


class LiveRuntimeGuard:
    """Central runtime control checks for paper/live execution safety."""

    def __init__(self, root: Path):
        self.root = Path(root)
        self.config = self.root / "config"
        self.runtime_file = self.config / "runtime_control.json"
        self.paper_file = self.config / "paper_trader_runtime.json"

    def load(self) -> Dict:
        defaults = {
            "mode": "paper",
            "allow_live_orders": False,
            "paper_enabled": True,
            "futures_mode": False,
            "leverage_multiplier": 1.0,
            "kill_switch": True,
            "max_daily_loss_usd": 100.0,
            "max_open_positions": 5,
            "max_portfolio_heat": 0.10,
            "loop_seconds": 5,
            "max_position_usd": 50.0,
            "min_position_usd": 5.0,
            "reserve_usd": 15.0,
            "base_risk_fraction": 0.20,
            "pyramid_reinvestment_multiplier": 1.15,
            "max_consecutive_order_failures": 8,
            "order_failure_cooldown_sec": 30,
            "gate_override_enabled": False,
            "gate_override_min_confidence": 0.60,
            "gate_override_min_edge_bps": 12.0,
            "auto_convert_collateral": False,
            "collateral_sell_fraction": 0.10,
            "collateral_convert_cooldown_sec": 120,
            "fallback_buying_power_usd": 0.0,
            "symbol_skip_cooldown_sec": 45,
            "ticker_fail_cooldown_sec": 5,
            "min_order_cooldown_sec": 60,
            "capital_aware_ranking_enabled": True,
            "capital_aware_scan_size": 6,
            "pounce_edge_bps_bonus": 4.0,
        }
        if not self.runtime_file.exists():
            return defaults
        try:
            cfg = json.loads(self.runtime_file.read_text(encoding="utf-8"))
            out = defaults.copy()
            out.update(cfg if isinstance(cfg, dict) else {})
            return self._normalize(out)
        except Exception:
            return defaults

    @staticmethod
    def _clamp_float(value, low: float, high: float, default: float) -> float:
        try:
            v = float(value)
        except Exception:
            return float(default)
        return max(low, min(high, v))

    @staticmethod
    def _coerce_int(value, low: int, high: int, default: int) -> int:
        try:
            v = int(value)
        except Exception:
            return int(default)
        return max(low, min(high, v))

    @staticmethod
    def _coerce_bool(value, default: bool = False) -> bool:
        if isinstance(value, bool):
            return value
        if isinstance(value, str):
            return value.strip().lower() in {"1", "true", "yes", "on"}
        if isinstance(value, (int, float)):
            return value != 0
        return default

    def _normalize(self, runtime: Dict) -> Dict:
        mode = str(runtime.get("mode", "paper")).strip().lower()
        if mode not in {"paper", "live"}:
            mode = "paper"

        normalized = {
            "mode": mode,
            "allow_live_orders": self._coerce_bool(runtime.get("allow_live_orders", False), False),
            "paper_enabled": self._coerce_bool(runtime.get("paper_enabled", True), True),
            "futures_mode": self._coerce_bool(runtime.get("futures_mode", False), False),
            "leverage_multiplier": self._clamp_float(runtime.get("leverage_multiplier", 1.0), 1.0, 5.0, 1.0),
            "kill_switch": self._coerce_bool(runtime.get("kill_switch", True), True),
            "max_daily_loss_usd": self._clamp_float(runtime.get("max_daily_loss_usd", 100.0), 1.0, 1_000_000.0, 100.0),
            "max_open_positions": self._coerce_int(runtime.get("max_open_positions", 5), 1, 200, 5),
            "max_portfolio_heat": self._clamp_float(runtime.get("max_portfolio_heat", 0.10), 0.01, 1.00, 0.10),
            "loop_seconds": self._clamp_float(runtime.get("loop_seconds", 5), 0.25, 60.0, 5.0),
            "max_position_usd": self._clamp_float(runtime.get("max_position_usd", 50.0), 1.0, 1_000_000.0, 50.0),
            "min_position_usd": self._clamp_float(runtime.get("min_position_usd", 5.0), 0.5, 100_000.0, 5.0),
            "reserve_usd": self._clamp_float(runtime.get("reserve_usd", 15.0), 0.0, 1_000_000.0, 15.0),
            "base_risk_fraction": self._clamp_float(runtime.get("base_risk_fraction", 0.20), 0.01, 1.00, 0.20),
            "pyramid_reinvestment_multiplier": self._clamp_float(runtime.get("pyramid_reinvestment_multiplier", 1.15), 0.50, 5.00, 1.15),
            "max_consecutive_order_failures": self._coerce_int(runtime.get("max_consecutive_order_failures", 8), 1, 500, 8),
            "order_failure_cooldown_sec": self._clamp_float(runtime.get("order_failure_cooldown_sec", 30), 1.0, 3_600.0, 30.0),
            "gate_override_enabled": self._coerce_bool(runtime.get("gate_override_enabled", False), False),
            "gate_override_min_confidence": self._clamp_float(runtime.get("gate_override_min_confidence", 0.60), 0.0, 1.0, 0.60),
            "gate_override_min_edge_bps": self._clamp_float(runtime.get("gate_override_min_edge_bps", 12.0), 0.0, 10_000.0, 12.0),
            "auto_convert_collateral": self._coerce_bool(runtime.get("auto_convert_collateral", False), False),
            "collateral_sell_fraction": self._clamp_float(runtime.get("collateral_sell_fraction", 0.10), 0.01, 0.50, 0.10),
            "collateral_convert_cooldown_sec": self._clamp_float(runtime.get("collateral_convert_cooldown_sec", 120), 5.0, 3600.0, 120.0),
            "fallback_buying_power_usd": self._clamp_float(runtime.get("fallback_buying_power_usd", 0.0), 0.0, 10_000_000.0, 0.0),
            "symbol_skip_cooldown_sec": self._clamp_float(runtime.get("symbol_skip_cooldown_sec", 45), 5.0, 3600.0, 45.0),
            "ticker_fail_cooldown_sec": self._clamp_float(runtime.get("ticker_fail_cooldown_sec", 5), 1.0, 300.0, 5.0),
            "min_order_cooldown_sec": self._clamp_float(runtime.get("min_order_cooldown_sec", 60), 5.0, 3600.0, 60.0),
            "capital_aware_ranking_enabled": self._coerce_bool(runtime.get("capital_aware_ranking_enabled", True), True),
            "capital_aware_scan_size": self._coerce_int(runtime.get("capital_aware_scan_size", 1000), 1, 10000, 1000),
            "pounce_edge_bps_bonus": self._clamp_float(runtime.get("pounce_edge_bps_bonus", 4.0), 0.0, 50.0, 4.0),
        }

        for key, value in runtime.items():
            if key not in normalized:
                normalized[key] = value

        # Keep min_position <= max_position regardless of user config order.
        if normalized["min_position_usd"] > normalized["max_position_usd"]:
            normalized["min_position_usd"] = normalized["max_position_usd"]

        # Asset conversion is never a paper-mode convenience. It remains
        # unavailable until the runtime is fully and explicitly live-armed.
        fully_live_armed = (
            normalized["mode"] == "live"
            and normalized["allow_live_orders"]
            and not normalized["paper_enabled"]
            and not normalized["kill_switch"]
        )
        if not fully_live_armed:
            normalized["auto_convert_collateral"] = False

        return normalized

    def can_place_live_order(self, runtime: Dict, realized_pnl_total: float, portfolio_heat: float, open_positions: int) -> Tuple[bool, str]:
        if bool(runtime.get("kill_switch", False)):
            return False, "kill_switch_enabled"

        mode = str(runtime.get("mode", "paper")).lower()
        allow_live = bool(runtime.get("allow_live_orders", False))

        if mode != "live" or not allow_live:
            return False, "live_orders_not_armed"

        # Prevent conflicting modes from passing by mistake.
        if bool(runtime.get("paper_enabled", False)):
            return False, "paper_mode_conflict"

        max_daily_loss = float(runtime.get("max_daily_loss_usd", 100.0) or 100.0)
        if realized_pnl_total <= -abs(max_daily_loss):
            return False, "max_daily_loss_reached"

        max_heat = float(runtime.get("max_portfolio_heat", 0.10) or 0.10)
        if portfolio_heat > max_heat:
            return False, "portfolio_heat_limit"

        max_open = int(runtime.get("max_open_positions", 5) or 5)
        if open_positions >= max_open:
            return False, "max_open_positions_reached"

        return True, "live_orders_armed"

    @staticmethod
    def now_utc() -> str:
        return datetime.now(timezone.utc).isoformat()
