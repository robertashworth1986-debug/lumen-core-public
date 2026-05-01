from dataclasses import dataclass
from typing import Dict, List


@dataclass
class Position:
    symbol: str
    side: str
    entry_price: float
    current_price: float
    qty: float
    entry_time_utc: str
    flowform: str = "unknown"
    algo: str = "unknown"
    strategy: str = "unknown"
    order_id: str = ""
    status: str = "OPEN"
    exit_price: float = 0.0
    exit_time_utc: str = ""
    pnl: float = 0.0


class PortfolioBrain:
    def __init__(self, initial_capital: float = 0.0):
        self.positions: List[Position] = []
        self.initial_capital = float(initial_capital)
        self.current_equity = float(initial_capital)
        self.realized_pnl_total = 0.0
        self.max_drawdown = 0.0
        self.total_trades = 0
        self._wins = 0
        self._equity_peak = float(initial_capital)

    def add(self, position: Dict):
        # Backward-compatible helper for older call sites using dicts.
        if isinstance(position, dict):
            px = float(position.get("entry_price", 0.0) or 0.0)
            qty = float(position.get("qty", 0.0) or 0.0)
            side = str(position.get("side", "long"))
            p = Position(
                symbol=str(position.get("symbol", "UNKNOWN")),
                side=side,
                entry_price=px,
                current_price=px,
                qty=qty,
                entry_time_utc=str(position.get("entry_time_utc", "")),
                order_id=str(position.get("order_id", "")),
                status=str(position.get("status", "OPEN")),
            )
            self.positions.append(p)

    def add_position(self, position: Position):
        self.positions.append(position)

    def get_open_positions(self) -> List[Position]:
        return [p for p in self.positions if str(p.status).upper() == "OPEN"]

    def exposure(self) -> float:
        total = 0.0
        for p in self.get_open_positions():
            total += abs(float(p.current_price) * float(p.qty))
        return float(total)

    def correlated(self, symbol: str) -> bool:
        return any(p.symbol == symbol for p in self.get_open_positions())

    def close_position(self, symbol: str, exit_price: float, exit_time_utc: str):
        for p in reversed(self.positions):
            if p.symbol == symbol and str(p.status).upper() == "OPEN":
                p.exit_price = float(exit_price)
                p.exit_time_utc = exit_time_utc
                p.current_price = float(exit_price)
                if str(p.side).lower() == "long":
                    pnl = (p.exit_price - p.entry_price) * p.qty
                else:
                    pnl = (p.entry_price - p.exit_price) * p.qty
                p.pnl = float(pnl)
                p.status = "CLOSED"

                self.realized_pnl_total += float(pnl)
                self.current_equity = self.initial_capital + self.realized_pnl_total
                self.total_trades += 1
                if pnl > 0:
                    self._wins += 1

                self._equity_peak = max(self._equity_peak, self.current_equity)
                if self._equity_peak > 0:
                    dd = (self.current_equity / self._equity_peak) - 1.0
                    self.max_drawdown = min(self.max_drawdown, dd)
                return

    def win_rate(self) -> float:
        if self.total_trades == 0:
            return 0.0
        return float((self._wins / self.total_trades) * 100.0)

    def get_summary(self) -> Dict:
        return {
            "initial_capital": float(self.initial_capital),
            "current_equity": float(self.current_equity),
            "realized_pnl_total": float(self.realized_pnl_total),
            "max_drawdown": float(self.max_drawdown),
            "total_trades": int(self.total_trades),
            "win_rate_pct": float(self.win_rate()),
            "open_positions": int(len(self.get_open_positions())),
            "exposure_usd": float(self.exposure()),
        }
