import os
import sys
import json
import time
import random
import hmac
import hashlib
import base64
import requests

from pathlib import Path
from urllib.parse import urlencode
from datetime import datetime, timezone
from typing import Optional

import requests

# Add paths
sys.path.insert(0, r"C:\LumaTrader\INSTITUTIONAL_STACK_V2\code\execution")

from signal_gate import EvolutionarySignalGate, GateInput
from portfolio_brain import PortfolioBrain, Position
from liquidity_guard import LiquidityGuard, LiquiditySnapshot
from risk_kernel import RiskKernel, RiskState
from sizing_engine import SizingEngine, SizeInput
from order_router import OrderRouter, RouteIntent
from shadow_runner import ShadowRunner, ShadowFill
from trade_ledger import TradeLedger
from audit_chain import AuditChain

try:
    from regime_engine import InstitutionalRegimeEngine
except Exception:
    InstitutionalRegimeEngine = None


ROOT = Path(r"C:\LumaTrader\INSTITUTIONAL_STACK_V2")
CONFIG = ROOT / "config"
OUT = ROOT / "out" / "execution"
DASH = ROOT / "dashboard"
LIVE_TRADE_LOG_FILE = OUT / "live_trade_log.json"
LIVE_SHADOW_LEDGER_FILE = OUT / "live_shadow_fills.csv"
LIVE_TRADE_LEDGER_CSV_FILE = OUT / "live_trade_ledger.csv"
LIVE_TRADE_LEDGER_JSONL_FILE = OUT / "live_trade_ledger.jsonl"
LIVE_AUDIT_CHAIN_FILE = OUT / "live_execution_audit_chain.jsonl"
LIVE_HEARTBEAT_FILE = OUT / "live_executor_heartbeat.json"
LIVE_HEARTBEAT_SCHEMA_VERSION = "1.0.0"
ROLLING_CAPITAL_BEST_MULTI_FILE = Path(r"C:/LumaTrader/rolling_capital/rolling_capital_best_multi.json")

OUT.mkdir(parents=True, exist_ok=True)
DASH.mkdir(parents=True, exist_ok=True)


def load_json(path: Path, default):
    try:
        if path.exists():
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
    except Exception:
        pass
    return default


def load_api_keys() -> dict:
    keys = {}
    env_file = CONFIG / "luma_live_keys.env"
    if not env_file.exists():
        return keys
    for line in env_file.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, v = line.split("=", 1)
        keys[k.strip()] = v.strip()
    return keys


def load_institutional_live_selection() -> dict:
    return load_json(
        OUT / "institutional_live_selection.json",
        {"flow": "fallback", "strategy": "harmonic_blend", "edge_multiplier": 1.0, "institutional_score": 0.0},
    )


def _resolve_urgency(edge_score: float, spread_bps: float, direction: str) -> str:
    del direction
    if edge_score >= 0.75 and spread_bps <= 8.0:
        return "aggressive"
    if edge_score >= 0.45 and spread_bps <= 20.0:
        return "normal"
    return "passive"


def _preferred_live_symbol() -> Optional[str]:
    payload = load_json(ROLLING_CAPITAL_BEST_MULTI_FILE, {})
    raw_symbol = str(payload.get("symbol", "")).upper().strip()
    if not raw_symbol:
        return None
    base_symbol = raw_symbol.split("/")[0].strip()
    return base_symbol or None


def _write_live_heartbeat(payload: dict) -> None:
    try:
        payload = dict(payload)
        payload.setdefault("schema_version", LIVE_HEARTBEAT_SCHEMA_VERSION)
        payload.setdefault("timestamp_utc", datetime.now(timezone.utc).isoformat())
        LIVE_HEARTBEAT_FILE.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    except Exception:
        pass


SYMBOL_REGISTRY = {
    "BTC": {"exchange": "kraken", "pair": "XBTUSD", "min_order": 0.0001},
    "ETH": {"exchange": "kraken", "pair": "ETHUSD", "min_order": 0.001},
    "SOL": {"exchange": "kraken", "pair": "SOLUSD", "min_order": 0.01},
    "XRP": {"exchange": "kraken", "pair": "XRPUSD", "min_order": 1.0},
}


class KrakenClient:
    def __init__(self, api_key: str, api_secret: str):
        self.api_key = api_key or ""
        self.api_secret = api_secret or ""
        self.base_url = "https://api.kraken.com"
        self.session = requests.Session()

    def _sign(self, urlpath: str, data: dict) -> str:
        nonce = data["nonce"]
        postdata = urlencode(data)
        encoded = (str(nonce) + postdata).encode()
        message = urlpath.encode() + hashlib.sha256(encoded).digest()
        mac = hmac.new(base64.b64decode(self.api_secret), message, hashlib.sha512)
        return base64.b64encode(mac.digest()).decode()

    def _private(self, endpoint: str, data: dict) -> dict:
        data = dict(data or {})
        data["nonce"] = str(int(time.time() * 1000))
        headers = {
            "API-Key": self.api_key,
            "API-Sign": self._sign(endpoint, data),
        }
        r = self.session.post(self.base_url + endpoint, data=data, headers=headers, timeout=15)
        r.raise_for_status()
        payload = r.json()
        if payload.get("error"):
            return {"error": payload["error"]}
        return payload.get("result", {})

    def get_account_balance(self) -> float:
        if not self.api_key or not self.api_secret:
            return 0.0
        try:
            result = self._private("/0/private/Balance", {})
            if "error" in result:
                return 0.0
            return float(result.get("ZUSD", 0.0))
        except Exception:
            return 0.0

    def send_order(self, pair: str, side: str, qty: float, price: float = None, order_type: str = "limit") -> dict:
        if not self.api_key or not self.api_secret:
            return {"error": "missing kraken credentials"}
        data = {
            "pair": pair,
            "type": side.lower(),
            "ordertype": "limit" if order_type == "limit" else "market",
            "volume": f"{qty:.8f}",
        }
        if order_type == "limit" and price is not None:
            data["price"] = f"{price:.8f}"
        try:
            return self._private("/0/private/AddOrder", data)
        except Exception as e:
            return {"error": str(e)}

    def get_ticker(self, pair: str):
        try:
            r = self.session.get(self.base_url + "/0/public/Ticker", params={"pair": pair}, timeout=10)
            r.raise_for_status()
            payload = r.json()
            if payload.get("error"):
                return None
            result = payload.get("result", {})
            if not result:
                return None
            key = next(iter(result.keys()))
            t = result[key]
            return {
                "bid": float(t["b"][0]),
                "ask": float(t["a"][0]),
                "last": float(t["c"][0]),
                "pair": key,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }
        except Exception:
            return None


class MultiExchangeRouter:
    def __init__(self, api_keys: dict):
        self.kraken = KrakenClient(api_keys.get("KRAKEN_API_KEY", ""), api_keys.get("KRAKEN_API_SECRET", ""))

    def get_symbol_config(self, symbol: str):
        return SYMBOL_REGISTRY.get(symbol.upper())

    def get_ticker(self, symbol: str):
        cfg = self.get_symbol_config(symbol)
        if not cfg:
            return None
        return self.kraken.get_ticker(cfg["pair"])

    def get_balance(self):
        return self.kraken.get_account_balance()

    def place_order(self, symbol: str, side: str, qty: float, limit_price: float = None):
        cfg = self.get_symbol_config(symbol)
        if not cfg:
            return {"error": f"unknown symbol {symbol}"}
        return self.kraken.send_order(cfg["pair"], side, qty, limit_price, "limit" if limit_price else "market")


class RobustLiveExecutor:
    def __init__(self, api_keys: dict):
        self.router = MultiExchangeRouter(api_keys)
        self.signal_gate = EvolutionarySignalGate()
        self.portfolio = PortfolioBrain(initial_capital=219.0)
        self.liquidity_guard = LiquidityGuard()
        self.risk_kernel = RiskKernel()
        self.sizing_engine = SizingEngine()
        self.order_router = OrderRouter()
        self.shadow_runner = ShadowRunner()
        self.trade_ledger = TradeLedger(str(LIVE_TRADE_LEDGER_CSV_FILE), str(LIVE_TRADE_LEDGER_JSONL_FILE))
        self.audit_chain = AuditChain(LIVE_AUDIT_CHAIN_FILE)

        self.regime_engine = InstitutionalRegimeEngine() if InstitutionalRegimeEngine else None
        self.live_selection = load_institutional_live_selection()
        self.edge_multiplier = float(self.live_selection.get("edge_multiplier", 1.0))

        self.pyramid_level = 1
        self.consecutive_losses = 0
        self.trade_log = []

    def _strategy_regime_conflict(self, strategy: str, regime_name: str) -> bool:
        # hard-block matrix
        disallow = {
            "mean_revert": {"trend", "expansion"},
            "breakout": {"chop", "squeeze"},
            "trend": {"chop"},
        }
        blocked = disallow.get(strategy, set())
        return regime_name in blocked

    def _liquidity_score(self, liq_decision) -> float:
        try:
            tier = getattr(liq_decision, "liquidity_tier", None)
            if hasattr(tier, "value"):
                return max(0.0, min(1.0, float(tier.value) / 10.0))
        except Exception:
            pass
        return 0.8

    def get_decision_engine_input(self, symbol: str) -> Optional[GateInput]:
        ticker = self.router.get_ticker(symbol)
        if not ticker:
            return None

        regime_name = "normal"
        if self.regime_engine:
            try:
                r = self.regime_engine.classify(symbol)
                regime_name = getattr(r, "name", "normal")
            except Exception:
                pass

        strategy = self.live_selection.get("strategy", "harmonic_blend")
        if self._strategy_regime_conflict(strategy, regime_name):
            return None  # hard block

        vol_pct = random.uniform(0.5, 3.0)
        hist_wr = self.portfolio.win_rate() / 100 if getattr(self.portfolio, "total_trades", 0) > 0 else 0.5
        expected_edge_bps = random.uniform(5, 30) * self.edge_multiplier

        return GateInput(
            regime=f"{regime_name}|flow={self.live_selection.get('flow')}|strategy={strategy}",
            regime_confidence=random.uniform(0.6, 0.95),
            alignment_score=random.uniform(0.6, 0.95),
            liquidity_score=0.85,
            signal_decay_score=0.2,
            cross_confirm_score=random.uniform(0.6, 0.95),
            expected_edge_bps=expected_edge_bps,
            direction_hint=random.choice([0.0, 1.0]),
            volatility_pct=vol_pct,
            correlation_to_portfolio=0.1,
            market_regime="normal",
            sector_heat=0.05,
            historical_win_rate=hist_wr,
            monte_carlo_edge=0.0,
            live_data_freshness=0.95,
        )

    def execute_trade_cycle(self, symbol: str):
        now = datetime.now(timezone.utc)
        print(f"[{now.strftime('%H:%M:%S')}] cycle {symbol}")

        gate_input = self.get_decision_engine_input(symbol)
        if not gate_input:
            _write_live_heartbeat({"status": "blocked", "reason": "regime_or_data", "symbol": symbol})
            print("  blocked: regime/selection conflict or no data")
            return

        gate_decision = self.signal_gate.decide(gate_input)
        if not gate_decision.armed:
            _write_live_heartbeat({"status": "blocked", "reason": "gate_not_armed", "symbol": symbol})
            print("  blocked: gate not armed")
            return

        ticker = self.router.get_ticker(symbol)
        if not ticker:
            _write_live_heartbeat({"status": "blocked", "reason": "missing_ticker", "symbol": symbol})
            print("  blocked: no ticker")
            return

        bid, ask, last = ticker["bid"], ticker["ask"], ticker["last"]
        mid = max((bid + ask) / 2.0, 1e-9)
        spread_bps = abs((ask - bid) / mid) * 10000.0

        liq = self.liquidity_guard.assess(
            LiquiditySnapshot(
                bid=bid, ask=ask, bid_size=1.0, ask_size=1.0,
                est_sweep_cost_bps=5.0, quote_update_rate=2.0, volume_24h=30_000_000,
                volatility_pct=gate_input.volatility_pct
            )
        )
        if not liq.pass_trade:
            _write_live_heartbeat({"status": "blocked", "reason": "liquidity", "symbol": symbol})
            print("  blocked: liquidity")
            return

        risk = self.risk_kernel.allow(
            RiskState(
                day_pnl_usd=self.portfolio.realized_pnl_total,
                open_risk_usd=self.portfolio.exposure(),
                portfolio_heat=self.portfolio.exposure() / max(self.portfolio.current_equity, 1),
                symbol_cooldown_active=False,
                open_positions=len(self.portfolio.get_open_positions()),
                max_open_positions=5,
                live_mode=True,
                kill_switch=False,
                drawdown_pct=self.portfolio.max_drawdown * 100,
                max_consecutive_losses=self.consecutive_losses,
                sector_heat={"crypto": 0.1},
            )
        )
        if not risk.allowed:
            _write_live_heartbeat({"status": "blocked", "reason": "risk", "symbol": symbol, "risk_reasons": list(getattr(risk, "reasons", []) or [])})
            print("  blocked: risk")
            return

        usd_balance = self.router.get_balance()
        direction = gate_decision.direction
        stop_price = last * (0.98 if direction == "long" else 1.02)
        urgency = _resolve_urgency(float(gate_decision.composite_score), spread_bps, direction)
        fee_bps = float(self.live_selection.get("fee_bps", 10.0) or 10.0)
        slippage_bps = float(self.live_selection.get("slippage_bps", max(spread_bps * 0.6, 8.0)) or max(spread_bps * 0.6, 8.0))
        drawdown_pct = max(float(getattr(self.portfolio, "max_drawdown", 0.0) or 0.0), 0.0)
        size_decision = self.sizing_engine.size(
            SizeInput(
                equity_usd=usd_balance,
                entry_price=last,
                stop_price=stop_price,
                realized_vol=max(0.0001, gate_input.volatility_pct / 100.0),
                edge_score=float(gate_decision.composite_score),
                portfolio_heat=self.portfolio.exposure() / max(self.portfolio.current_equity, 1),
                liquidity_score=self._liquidity_score(liq),
                fee_bps=fee_bps,
                slippage_bps=slippage_bps,
                urgency=urgency,
                dislocation_score=max(float(gate_decision.composite_score) - 0.40, 0.0),
                drawdown_pct=drawdown_pct,
                reserve_usd=float(self.live_selection.get("reserve_usd", 0.0) or 0.0),
                max_notional_usd=float(self.live_selection.get("max_notional_usd", 0.0) or 0.0),
            )
        )

        qty = float(size_decision.qty)
        notional_usd = float(getattr(size_decision, "notional_usd", 0.0))
        risk_usd = float(getattr(size_decision, "risk_usd", 0.0))
        if qty <= 0:
            _write_live_heartbeat({"status": "blocked", "reason": "sizing_zero", "symbol": symbol, "urgency": urgency})
            print("  blocked: sizing qty=0")
            return

        cfg = self.router.get_symbol_config(symbol)
        if qty < float(cfg["min_order"]):
            _write_live_heartbeat({"status": "blocked", "reason": "min_order", "symbol": symbol, "qty": qty, "min_order": float(cfg["min_order"])})
            print("  blocked: min_order")
            return

        side = "buy" if direction == "long" else "sell"
        route_intent = RouteIntent(
            symbol=symbol,
            side=side,
            qty=qty,
            urgency=urgency,
            entry_price=last,
            stop_price=stop_price,
            take_profit=(last * (1.02 if direction == "long" else 0.98)),
            reduce_only=False,
        )
        order_template = self.order_router.build_primary(route_intent, validate_only=False)
        close_template = self.order_router.build_close_template(route_intent)
        shadow_fill_px, shadow_slip_bps = self.shadow_runner.simulate_fill(bid, ask, side, urgency)
        self.shadow_runner.append_ledger(
            str(LIVE_SHADOW_LEDGER_FILE),
            ShadowFill(
                ts_utc=now.isoformat(),
                symbol=symbol,
                side=side,
                qty=qty,
                est_fill=shadow_fill_px,
                slip_bps=shadow_slip_bps,
                mode="live_shadow",
            ),
        )

        limit_price = None
        if order_template.get("order_type") == "limit":
            limit_price = float(order_template.get("limit_price") or last)
        result = self.router.place_order(symbol, side, qty, limit_price)
        if "error" in result:
            _write_live_heartbeat({"status": "error", "reason": "order_failed", "symbol": symbol, "side": side, "error": str(result.get("error"))})
            print(f"  order failed: {result['error']}")
            return

        txid = result.get("txid", ["unknown"])
        txid = txid[0] if isinstance(txid, list) else str(txid)

        self.portfolio.add_position(
            Position(
                symbol=f"{symbol}/USD",
                side=direction,
                entry_price=last,
                current_price=last,
                qty=qty,
                entry_time_utc=now.isoformat(),
                flowform=self.live_selection.get("flow", "fallback"),
                algo="echo_stack",
                strategy=self.live_selection.get("strategy", "harmonic_blend"),
                order_id=txid,
                status="OPEN",
            )
        )

        ledger_hash = self.trade_ledger.append(
            {
                "timestamp": now.isoformat(),
                "txid": txid,
                "symbol": symbol,
                "pair": cfg["pair"],
                "direction": direction,
                "side": side,
                "status": "PLACED",
                "execution_mode": urgency,
                "gate_score": round(float(gate_decision.composite_score), 6),
                "entry_price": round(float(last), 6),
                "qty": round(qty, 10),
                "size_usd": round(notional_usd, 6),
                "risk_usd": round(risk_usd, 6),
                "round_trip_fee_usd": 0.0,
                "tp_net_bps": round((((float(route_intent.take_profit or last) / max(float(last), 1e-9)) - 1.0) * 10000.0), 6),
                "sl_net_bps": round((((float(route_intent.stop_price or last) / max(float(last), 1e-9)) - 1.0) * 10000.0), 6),
            }
        )
        audit_row = self.audit_chain.append(
            "live_order_placed",
            {
                "symbol": symbol,
                "pair": cfg["pair"],
                "side": side,
                "direction": direction,
                "urgency": urgency,
                "gate_score": round(float(gate_decision.composite_score), 6),
                "txid": txid,
                "ledger_hash": ledger_hash,
            },
        )

        self.trade_log.append(
            {
                "timestamp": now.isoformat(),
                "txid": txid,
                "symbol": symbol,
                "pair": cfg["pair"],
                "direction": direction,
                "side": side,
                "entry_price": last,
                "qty": qty,
                "size_usd": notional_usd,
                "risk_usd": risk_usd,
                "flow": self.live_selection.get("flow"),
                "strategy": self.live_selection.get("strategy"),
                "edge_multiplier": self.edge_multiplier,
                "urgency": urgency,
                "spread_bps": round(spread_bps, 6),
                "shadow_fill": {"est_fill": round(shadow_fill_px, 6), "slip_bps": round(shadow_slip_bps, 6)},
                "order_template": order_template,
                "close_template": close_template,
                "ledger_hash": ledger_hash,
                "audit_hash": audit_row.get("event_hash"),
                "status": "PLACED",
            }
        )

        with open(LIVE_TRADE_LOG_FILE, "w", encoding="utf-8") as f:
            json.dump(self.trade_log, f, indent=2)

        _write_live_heartbeat(
            {
                "status": "ok",
                "symbol": symbol,
                "pair": cfg["pair"],
                "side": side,
                "txid": txid,
                "urgency": urgency,
                "spread_bps": round(spread_bps, 6),
                "size_usd": round(notional_usd, 6),
                "risk_usd": round(risk_usd, 6),
                "edge_score": round(float(gate_decision.composite_score), 6),
                "portfolio_heat": round(self.portfolio.exposure() / max(self.portfolio.current_equity, 1), 6),
            }
        )

        print(f"  placed txid={txid}")

    def run_institutional_execution_loop(self):
        print("starting live loop")
        while True:
            try:
                symbol = _preferred_live_symbol()
                if not symbol or symbol not in SYMBOL_REGISTRY:
                    symbol = random.choice(list(SYMBOL_REGISTRY.keys()))
                self.execute_trade_cycle(symbol)
                time.sleep(30)
            except KeyboardInterrupt:
                print("stopped")
                break
            except Exception as e:
                _write_live_heartbeat(
                    {
                        "status": "error",
                        "reason": "loop_exception",
                        "symbol": symbol if "symbol" in locals() else "",
                        "error": str(e),
                    }
                )
                print(f"loop error: {e}")
                time.sleep(5)


if __name__ == "__main__":
    api_keys = load_api_keys()
    executor = RobustLiveExecutor(api_keys)
    executor.run_institutional_execution_loop()
