from dataclasses import dataclass
from typing import Optional, Literal

@dataclass
class RouteIntent:
    symbol: str
    side: str
    qty: float
    urgency: Literal["passive","normal","aggressive"]
    entry_price: Optional[float]
    stop_price: Optional[float]
    take_profit: Optional[float]
    reduce_only: bool = False

class OrderRouter:
    def build_primary(self, x: RouteIntent, validate_only: bool = True) -> dict:
        if x.urgency == "passive":
            return {
                "order_type": "limit",
                "symbol": x.symbol,
                "side": x.side,
                "order_qty": x.qty,
                "limit_price": x.entry_price,
                "time_in_force": "gtc",
                "post_only": True,
                "reduce_only": x.reduce_only,
                "validate": validate_only
            }
        if x.urgency == "normal":
            return {
                "order_type": "limit",
                "symbol": x.symbol,
                "side": x.side,
                "order_qty": x.qty,
                "limit_price": x.entry_price,
                "time_in_force": "ioc",
                "reduce_only": x.reduce_only,
                "validate": validate_only
            }
        return {
            "order_type": "market",
            "symbol": x.symbol,
            "side": x.side,
            "order_qty": x.qty,
            "reduce_only": x.reduce_only,
            "validate": validate_only
        }

    def build_close_template(self, x: RouteIntent) -> Optional[dict]:
        if x.stop_price is None and x.take_profit is None:
            return None
        out = {}
        if x.stop_price is not None:
            out["stop"] = {"order_type": "stop-loss", "trigger_price": x.stop_price}
        if x.take_profit is not None:
            out["take_profit"] = {"order_type": "take-profit", "trigger_price": x.take_profit}
        return out
