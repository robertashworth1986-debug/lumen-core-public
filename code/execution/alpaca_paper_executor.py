import argparse
import json
import math
import os
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import requests

from execution.adaptive_regime_router import route_equity_signal


ROOT = Path(r"C:\LumaTrader\INSTITUTIONAL_STACK_V2")
CONFIG = ROOT / "config"
OUT = ROOT / "out"
EXEC_OUT = OUT / "execution"

ENV_FILE = CONFIG / "luma_live_keys.env"
RUNTIME_FILE = CONFIG / "runtime_control.json"
PAPER_RUNTIME_FILE = CONFIG / "paper_trader_runtime.json"
SELECTION_FILE = EXEC_OUT / "institutional_live_selection.json"

STATE_FILE = OUT / "paper_trade_state.json"
LEDGER_FILE = OUT / "paper_trade_ledger.jsonl"
STATUS_FILE = EXEC_OUT / "alpaca_paper_status.json"
ADAPTIVE_UNIVERSE_FILE = OUT / "adaptive_universe.json"
INSTITUTIONAL_DAILY_REPORT_SCRIPT = ROOT / "code" / "institutional_daily_report.py"
INVESTOR_EVIDENCE_PACK_SCRIPT = ROOT / "code" / "build_investor_evidence_pack.py"


def now_utc() -> str:
    return datetime.now(timezone.utc).isoformat()


def load_json(path: Path, default):
    try:
        if path.exists():
            return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        pass
    return default


def save_json(path: Path, payload) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def append_jsonl(path: Path, payload) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(payload, ensure_ascii=True) + "\n")


def _pick_first(*values):
    for value in values:
        if value is None:
            continue
        text = str(value).strip()
        if text:
            return text
    return ""


def load_api_keys() -> dict:
    keys = {}
    if ENV_FILE.exists():
        for raw in ENV_FILE.read_text(encoding="utf-8", errors="ignore").splitlines():
            line = raw.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, value = line.split("=", 1)
            keys[key.strip()] = value.strip()

    return {
        "ALPACA_API_KEY": _pick_first(
            os.environ.get("ALPACA_API_KEY"),
            os.environ.get("APCA_API_KEY_ID"),
            os.environ.get("ALPACA_KEY"),
            keys.get("ALPACA_API_KEY"),
            keys.get("APCA_API_KEY_ID"),
            keys.get("ALPACA_KEY"),
        ),
        "ALPACA_API_SECRET": _pick_first(
            os.environ.get("ALPACA_API_SECRET"),
            os.environ.get("APCA_API_SECRET_KEY"),
            os.environ.get("ALPACA_SECRET"),
            keys.get("ALPACA_API_SECRET"),
            keys.get("APCA_API_SECRET_KEY"),
            keys.get("ALPACA_SECRET"),
        ),
        "ALPACA_PAPER_BASE_URL": _pick_first(
            os.environ.get("ALPACA_PAPER_BASE_URL"),
            os.environ.get("ALPACA_BASE_URL"),
            os.environ.get("ALPACA_TRADING_BASE_URL"),
            keys.get("ALPACA_PAPER_BASE_URL"),
            keys.get("ALPACA_BASE_URL"),
            keys.get("ALPACA_TRADING_BASE_URL"),
        ),
        "ALPACA_DATA_BASE_URL": _pick_first(
            os.environ.get("ALPACA_DATA_BASE_URL"),
            os.environ.get("ALPACA_DATA_BASEURL"),
            keys.get("ALPACA_DATA_BASE_URL"),
            keys.get("ALPACA_DATA_BASEURL"),
        ),
    }


class AlpacaPaperClient:
    def __init__(
        self,
        api_key: str,
        api_secret: str,
        trading_base: str | None = None,
        data_base: str | None = None,
    ):
        self.api_key = api_key or ""
        self.api_secret = api_secret or ""
        self.trading_base = str(trading_base).strip().rstrip("/") or "https://paper-api.alpaca.markets"
        self.data_base = str(data_base).strip().rstrip("/") or "https://data.alpaca.markets"
        self.session = requests.Session()
        self.session.headers.update(
            {
                "APCA-API-KEY-ID": self.api_key,
                "APCA-API-SECRET-KEY": self.api_secret,
            }
        )
        self.max_retries = 3

    def is_configured(self) -> bool:
        return bool(self.api_key and self.api_secret)

    def _request_json(self, method: str, url: str, *, params=None, payload: dict | None = None) -> dict:
        last_error = None
        for attempt in range(1, self.max_retries + 1):
            try:
                response = self.session.request(method, url, params=params, json=payload, timeout=20)
                response.raise_for_status()
                if response.text.strip():
                    return response.json()
                return {"status": "ok"}
            except requests.exceptions.RequestException as exc:
                last_error = exc
                if attempt < self.max_retries:
                    time.sleep(min(2 * attempt, 5))
                    continue
                raise
        if last_error:
            raise last_error
        return {}

    def _get(self, url: str, params=None) -> dict:
        return self._request_json("GET", url, params=params)

    def _post(self, url: str, payload: dict) -> dict:
        return self._request_json("POST", url, payload=payload)

    def _delete(self, url: str) -> dict:
        return self._request_json("DELETE", url)

    def get_account(self) -> dict:
        return self._get(f"{self.trading_base}/v2/account")

    def list_positions(self) -> list[dict]:
        return self._get(f"{self.trading_base}/v2/positions")

    def get_snapshots(self, symbols: list[str]) -> dict:
        if not symbols:
            return {}
        payload = self._get(
            f"{self.data_base}/v2/stocks/snapshots",
            params={"symbols": ",".join(symbols)},
        )
        return payload or {}

    def get_clock(self) -> dict:
        return self._get(f"{self.trading_base}/v2/clock")

    def submit_buy(
        self,
        symbol: str,
        notional_usd: float,
        *,
        limit_price: float | None = None,
        extended_hours: bool = False,
    ) -> dict:
        # Alpaca extended-hours orders must be limit orders.
        if extended_hours and limit_price and limit_price > 0:
            qty = round(float(notional_usd) / float(limit_price), 6)
            payload = {
                "symbol": symbol,
                "side": "buy",
                "type": "limit",
                "time_in_force": "day",
                "qty": qty,
                "limit_price": round(float(limit_price), 2),
                "extended_hours": True,
            }
        else:
            payload = {
                "symbol": symbol,
                "side": "buy",
                "type": "market",
                "time_in_force": "day",
                "notional": round(float(notional_usd), 2),
            }
        return self._post(f"{self.trading_base}/v2/orders", payload)

    def close_position(self, symbol: str) -> dict:
        return self._delete(f"{self.trading_base}/v2/positions/{symbol}")

    def list_open_orders(self) -> list[dict]:
        payload = self._get(
            f"{self.trading_base}/v2/orders",
            params={"status": "open", "direction": "desc", "limit": 500},
        )
        return payload if isinstance(payload, list) else []

    def cancel_order(self, order_id: str) -> dict:
        return self._delete(f"{self.trading_base}/v2/orders/{order_id}")


def parse_iso_ts(raw: str) -> float:
    if not raw:
        return 0.0
    try:
        return datetime.fromisoformat(str(raw).replace("Z", "+00:00")).timestamp()
    except Exception:
        return 0.0


def _iso_or_none(raw) -> str | None:
    text = str(raw or "").strip()
    return text if text else None


def compute_signal_score(snapshot: dict, selection: dict) -> dict:
    minute_bar = snapshot.get("minuteBar") or {}
    daily_bar = snapshot.get("dailyBar") or {}
    prev_daily_bar = snapshot.get("prevDailyBar") or {}
    latest_trade = snapshot.get("latestTrade") or {}

    price = float(latest_trade.get("p") or minute_bar.get("c") or daily_bar.get("c") or 0.0)
    minute_open = float(minute_bar.get("o") or price or 0.0)
    minute_close = float(minute_bar.get("c") or price or 0.0)
    daily_close = float(daily_bar.get("c") or price or 0.0)
    daily_high = float(daily_bar.get("h") or daily_close or 0.0)
    daily_low = float(daily_bar.get("l") or daily_close or 0.0)
    prev_close = float(prev_daily_bar.get("c") or daily_close or 0.0)
    minute_volume = float(minute_bar.get("v") or 0.0)
    daily_volume = float(daily_bar.get("v") or 0.0)

    if price <= 0 or prev_close <= 0:
        return {"score": -1e9, "price": 0.0, "confidence": 0.0, "edge_bps": 0.0}

    minute_return = (minute_close / max(minute_open, 1e-9)) - 1.0 if minute_open > 0 else 0.0
    day_return = (daily_close / max(prev_close, 1e-9)) - 1.0
    intraday_range = max(daily_high - daily_low, 1e-9)
    near_high = (daily_close - daily_low) / intraday_range
    volume_impulse = minute_volume / max(daily_volume / 390.0, 1.0)

    router = route_equity_signal(
        day_return=day_return,
        minute_return=minute_return,
        near_high=near_high,
        volume_impulse=volume_impulse,
    )

    strategy = str(selection.get("strategy", "breakout_donchian")).lower()
    if router.get("preferred_family") == "mean_reversion":
        raw_score = (
            max(-day_return, 0.0) * 170.0
            + max(minute_return, 0.0) * 140.0
            + max(0.60 - near_high, 0.0) * 28.0
            + min(volume_impulse, 5.0) * 1.5
        )
    elif "breakout" in strategy:
        raw_score = (day_return * 140.0) + (minute_return * 180.0) + (near_high * 20.0) + min(volume_impulse, 5.0)
    elif "regime" in strategy:
        raw_score = (day_return * 110.0) + (minute_return * 140.0) + (near_high * 15.0)
    else:
        raw_score = (day_return * 100.0) + (minute_return * 100.0) + (near_high * 10.0)

    if router.get("preferred_family") == "mean_reversion":
        edge_bps = max(0.0, ((-day_return * 0.65) + max(minute_return, 0.0)) * 10000.0)
        confidence = max(
            0.0,
            min(
                0.99,
                (0.48 + max(-day_return, 0.0) * 3.4 + max(minute_return, 0.0) * 5.5 + max(0.65 - near_high, 0.0) * 0.25)
                * float(router.get("confidence_multiplier", 1.0)),
            ),
        )
    else:
        edge_bps = max(0.0, (day_return + minute_return) * 10000.0)
        confidence = max(
            0.0,
            min(
                0.99,
                (0.50 + max(day_return, 0.0) * 4.0 + max(minute_return, 0.0) * 6.0 + min(near_high, 1.0) * 0.15)
                * float(router.get("confidence_multiplier", 1.0)),
            ),
        )
    return {
        "score": float(raw_score),
        "price": float(price),
        "confidence": float(confidence),
        "edge_bps": float(edge_bps),
        "day_return": float(day_return),
        "minute_return": float(minute_return),
        "near_high": float(near_high),
        "volume_impulse": float(volume_impulse),
        "signal_family": str(router.get("preferred_family", "neutral")),
        "regime_state": str(router.get("state", "neutral")),
        "regime_rationale": str(router.get("rationale", "")),
        "family_confidence": float(router.get("family_confidence", 0.5)),
    }


def choose_candidate(symbols: list[str], snapshots: dict, selection: dict, held_symbols: set[str]):
    ranked = []
    for symbol in symbols:
        snapshot = snapshots.get(symbol) or {}
        score = compute_signal_score(snapshot, selection)
        if score["price"] <= 0:
            continue
        score["symbol"] = symbol
        score["held"] = symbol in held_symbols
        ranked.append(score)

    # Adaptive entry strictness: demand higher quality setups when broad momentum is weak.
    tradable_ranked = [item for item in ranked if not item.get("held")]
    if tradable_ranked:
        strong_count = sum(
            1
            for item in tradable_ranked
            if item.get("day_return", 0.0) >= 0.005 and item.get("near_high", 0.0) >= 0.65
        )
        momentum_breadth = strong_count / max(len(tradable_ranked), 1)
    else:
        momentum_breadth = 0.0

    for item in ranked:
        router = route_equity_signal(
            day_return=float(item.get("day_return", 0.0) or 0.0),
            minute_return=float(item.get("minute_return", 0.0) or 0.0),
            near_high=float(item.get("near_high", 0.0) or 0.0),
            volume_impulse=float(item.get("volume_impulse", 0.0) or 0.0),
            momentum_breadth=momentum_breadth,
        )
        item["signal_family"] = str(router.get("preferred_family", item.get("signal_family", "neutral")))
        item["regime_state"] = str(router.get("state", item.get("regime_state", "neutral")))
        item["family_confidence"] = float(router.get("family_confidence", item.get("family_confidence", 0.5)))

    min_score = 7.0 if momentum_breadth < 0.35 else 5.0
    min_edge_bps = 80.0 if momentum_breadth < 0.35 else 50.0

    ranked.sort(key=lambda item: (item["held"], -item["score"], -item["edge_bps"], -item["confidence"]))
    for item in ranked:
        is_breakout = item.get("signal_family") == "breakout"
        is_reversion = item.get("signal_family") == "mean_reversion"
        if (
            not item["held"]
            and item["score"] > min_score
            and item.get("edge_bps", 0.0) >= min_edge_bps
            and (
                (
                    is_breakout
                    and item.get("day_return", 0.0) >= 0.005
                    and item.get("near_high", 0.0) >= 0.65
                    and item.get("minute_return", 0.0) >= -0.0005
                )
                or (
                    is_reversion
                    and item.get("day_return", 0.0) <= -0.004
                    and item.get("near_high", 0.0) <= 0.45
                    and item.get("minute_return", 0.0) >= -0.001
                    and item.get("family_confidence", 0.0) >= 0.55
                )
            )
        ):
            return item, ranked
    return (ranked[0] if ranked else None), ranked


def _normalize_symbols(raw_symbols: list[str]) -> list[str]:
    out = []
    seen = set()
    for raw in raw_symbols:
        sym = str(raw or "").upper().strip()
        if not sym:
            continue
        if sym in seen:
            continue
        seen.add(sym)
        out.append(sym)
    return out


def resolve_symbols_for_scan(client: AlpacaPaperClient, paper_runtime: dict) -> tuple[list[str], str, int]:
    configured = _normalize_symbols(paper_runtime.get("symbols", []) or [])
    symbol_mode = str(paper_runtime.get("symbol_mode", "ADAPTIVE_UNIVERSE") or "ADAPTIVE_UNIVERSE").upper()
    scan_limit = max(10, int(paper_runtime.get("snapshot_scan_limit", 300) or 300))

    if configured:
        return configured[:scan_limit], "paper_runtime.symbols", len(configured)

    if symbol_mode in {"ADAPTIVE_UNIVERSE", "UNIVERSE", "AUTO"}:
        adaptive_path = Path(str(paper_runtime.get("adaptive_universe_file", ADAPTIVE_UNIVERSE_FILE)))
        adaptive = load_json(adaptive_path, {})
        adaptive_symbols = _normalize_symbols(adaptive.get("symbols", []) if isinstance(adaptive, dict) else [])
        if adaptive_symbols:
            return adaptive_symbols[:scan_limit], "adaptive_universe_file", len(adaptive_symbols)

    # Fallback: discover active tradable Alpaca US equities when upstream universe is empty.
    assets = client._get(
        f"{client.trading_base}/v2/assets",
        params={"status": "active", "asset_class": "us_equity"},
    )
    discovered = []
    if isinstance(assets, list):
        for row in assets:
            if not isinstance(row, dict):
                continue
            if not bool(row.get("tradable", False)):
                continue
            if not bool(row.get("fractionable", False)):
                continue
            sym = str(row.get("symbol", "")).upper().strip()
            if not sym:
                continue
            discovered.append(sym)
    discovered = _normalize_symbols(discovered)
    return discovered[:scan_limit], "alpaca_assets_fallback", len(discovered)


def resolve_entry_notional_policy(paper_runtime: dict, equity: float, buying_power: float, cash: float) -> dict:
    micro_balance_threshold_usd = float(paper_runtime.get("micro_balance_threshold_usd", 50.0) or 50.0)
    micro_min_notional_usd = float(paper_runtime.get("micro_min_notional_usd", 5.0) or 5.0)
    standard_min_notional_usd = float(paper_runtime.get("standard_min_notional_usd", 100.0) or 100.0)

    effective_balance = max(float(equity or 0.0), float(buying_power or 0.0) * 0.5, float(cash or 0.0))
    micro_balance_mode = effective_balance > 0 and effective_balance <= micro_balance_threshold_usd
    minimum_entry_notional_usd = micro_min_notional_usd if micro_balance_mode else standard_min_notional_usd

    minimum_entry_notional_usd = max(1.0, minimum_entry_notional_usd)
    return {
        "micro_balance_mode": bool(micro_balance_mode),
        "micro_balance_threshold_usd": micro_balance_threshold_usd,
        "minimum_entry_notional_usd": float(minimum_entry_notional_usd),
        "micro_min_notional_usd": micro_min_notional_usd,
        "standard_min_notional_usd": standard_min_notional_usd,
        "effective_balance_usd": float(effective_balance),
    }


def _clamp(value: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, value))


def compute_dynamic_position_pct(pick: dict, paper_runtime: dict, base_position_size_pct: float) -> float:
    min_position_size_pct = float(paper_runtime.get("min_position_size_pct", max(0.02, base_position_size_pct * 0.5)) or 0.02)
    max_position_size_pct = float(paper_runtime.get("max_position_size_pct", base_position_size_pct) or base_position_size_pct)
    max_position_size_pct = max(min_position_size_pct, max_position_size_pct)

    confidence = float(pick.get("confidence", 0.0) or 0.0)
    edge_bps = float(pick.get("edge_bps", 0.0) or 0.0)
    near_high = float(pick.get("near_high", 0.0) or 0.0)
    minute_return = float(pick.get("minute_return", 0.0) or 0.0)

    conf_norm = _clamp((confidence - 0.55) / 0.40, 0.0, 1.0)
    edge_norm = _clamp((edge_bps - 80.0) / 1120.0, 0.0, 1.0)
    high_norm = _clamp((near_high - 0.60) / 0.40, 0.0, 1.0)

    quality_score = (0.45 * conf_norm) + (0.35 * edge_norm) + (0.20 * high_norm)
    quality_multiplier = 0.65 + (0.70 * quality_score)

    if minute_return < 0:
        quality_multiplier *= 0.92

    target_pct = _clamp(base_position_size_pct * quality_multiplier, min_position_size_pct, max_position_size_pct)
    return float(target_pct)


def evaluate_closures(positions: list[dict], tracked_positions: dict, now_ts: float, paper_runtime: dict | None = None):
    cfg = paper_runtime or {}
    take_profit_pct = float(cfg.get("take_profit_pct", 0.020) or 0.020)
    hard_stop_pct = float(cfg.get("hard_stop_pct", -0.0035) or -0.0035)
    max_hold_minutes = float(cfg.get("max_hold_minutes", 45.0) or 45.0)
    trailing_trigger_pct = float(cfg.get("trailing_trigger_pct", 0.010) or 0.010)
    trailing_drawdown_pct = float(cfg.get("trailing_drawdown_pct", 0.0040) or 0.0040)
    failed_winner_trigger_pct = float(cfg.get("failed_winner_trigger_pct", 0.006) or 0.006)
    failed_winner_floor_pct = float(cfg.get("failed_winner_floor_pct", -0.0005) or -0.0005)

    to_close = []
    for pos in positions:
        symbol = str(pos.get("symbol", "")).upper()
        uplpc = float(pos.get("unrealized_plpc") or 0.0)
        tracked = tracked_positions.setdefault(symbol, {})
        opened_at = str(tracked.get("opened_at", ""))
        max_uplpc = float(tracked.get("max_uplpc", uplpc))
        max_uplpc = max(max_uplpc, uplpc)
        tracked["max_uplpc"] = max_uplpc

        hold_minutes = 0.0
        if opened_at:
            try:
                opened_ts = datetime.fromisoformat(opened_at.replace("Z", "+00:00")).timestamp()
                hold_minutes = max(0.0, (now_ts - opened_ts) / 60.0)
            except Exception:
                hold_minutes = 0.0

        trail_drawdown = max_uplpc - uplpc
        hit_take_profit = uplpc >= take_profit_pct
        hit_hard_stop = uplpc <= hard_stop_pct
        hit_time_stop = hold_minutes >= max_hold_minutes
        # If a winner gives back too much, lock gains rather than waiting for full mean reversion.
        hit_trailing_stop = max_uplpc >= trailing_trigger_pct and trail_drawdown >= trailing_drawdown_pct
        # If a once-strong winner turns negative after at least +1%, cut quickly.
        hit_failed_winner = max_uplpc >= failed_winner_trigger_pct and uplpc <= failed_winner_floor_pct

        if hit_take_profit or hit_hard_stop or hit_time_stop or hit_trailing_stop or hit_failed_winner:
            to_close.append(
                {
                    "symbol": symbol,
                    "uplpc": uplpc,
                    "hold_minutes": hold_minutes,
                    "max_uplpc": max_uplpc,
                    "trail_drawdown": trail_drawdown,
                    "close_reason": (
                        "take_profit"
                        if hit_take_profit
                        else "hard_stop"
                        if hit_hard_stop
                        else "trailing_stop"
                        if hit_trailing_stop
                        else "failed_winner"
                        if hit_failed_winner
                        else "time_stop"
                    ),
                }
            )
    return to_close


def cleanup_stale_open_orders(client: AlpacaPaperClient, tracked_positions: dict, stale_seconds: float, now_ts: float):
    open_orders = client.list_open_orders()
    pending_symbols = set()
    canceled = []
    cancellable_statuses = {"new", "accepted", "pending_new", "accepted_for_bidding"}

    for order in open_orders:
        symbol = str(order.get("symbol", "")).upper()
        if symbol:
            pending_symbols.add(symbol)

        if stale_seconds <= 0:
            continue

        status = str(order.get("status", "")).lower()
        if status not in cancellable_statuses:
            continue

        order_id = str(order.get("id", ""))
        submitted_at = parse_iso_ts(order.get("submitted_at") or order.get("created_at"))
        if not order_id or submitted_at <= 0:
            continue

        age_seconds = max(0.0, now_ts - submitted_at)
        if age_seconds < stale_seconds:
            continue

        result = client.cancel_order(order_id)
        canceled.append(
            {
                "id": order_id,
                "symbol": symbol,
                "status": status,
                "age_seconds": round(age_seconds, 2),
                "result": result,
            }
        )
        pending_symbols.discard(symbol)
        tracked_positions.pop(symbol, None)

    return pending_symbols, canceled


def build_status_payload(
    account: dict,
    runtime: dict,
    paper_runtime: dict,
    selection: dict,
    positions: list[dict],
    candidate,
    ranked,
    note: str,
    open_orders: list[dict],
    execution_meta: dict | None = None,
):
    equity = float(account.get("equity") or 0.0)
    cash = float(account.get("cash") or 0.0)
    buying_power = float(account.get("buying_power") or 0.0)
    return {
        "generated_utc": now_utc(),
        "mode": "ALPACA_PAPER",
        "kraken_armed": bool(runtime.get("mode") == "live" and runtime.get("allow_live_orders")),
        "paper_enabled": bool(runtime.get("paper_enabled")),
        "allow_live_orders": bool(runtime.get("allow_live_orders")),
        "account": {
            "equity": equity,
            "cash": cash,
            "buying_power": buying_power,
        },
        "runtime": paper_runtime,
        "selection": selection,
        "positions": positions,
        "open_orders": open_orders[:25],
        "open_orders_count": len(open_orders),
        "open_unfilled_orders_count": sum(
            1
            for o in open_orders
            if float(o.get("filled_qty") or 0.0) <= 0
        ),
        "top_candidate": candidate,
        "top_ranked": ranked[:8],
        "status_note": note,
        "execution_meta": execution_meta or {},
    }


def run_periodic_artifacts(paper_runtime: dict, state: dict, now_ts: float) -> tuple[float, float, list[str]]:
    report_refresh_minutes = max(0.5, float(paper_runtime.get("report_refresh_minutes", 5.0) or 5.0))
    evidence_pack_refresh_minutes = max(1.0, float(paper_runtime.get("evidence_pack_refresh_minutes", 30.0) or 30.0))

    last_report_ts = float(state.get("last_report_refresh_ts", 0.0) or 0.0)
    last_pack_ts = float(state.get("last_evidence_pack_refresh_ts", 0.0) or 0.0)
    notes: list[str] = []

    if INSTITUTIONAL_DAILY_REPORT_SCRIPT.exists() and (now_ts - last_report_ts) >= (report_refresh_minutes * 60.0):
        try:
            subprocess.run([sys.executable, str(INSTITUTIONAL_DAILY_REPORT_SCRIPT)], cwd=str(ROOT / "code"), check=False)
            last_report_ts = now_ts
            notes.append("report_refresh=ok")
        except Exception as exc:
            notes.append(f"report_refresh_error={type(exc).__name__}")

    if INVESTOR_EVIDENCE_PACK_SCRIPT.exists() and (now_ts - last_pack_ts) >= (evidence_pack_refresh_minutes * 60.0):
        try:
            subprocess.run([sys.executable, str(INVESTOR_EVIDENCE_PACK_SCRIPT)], cwd=str(ROOT / "code"), check=False)
            last_pack_ts = now_ts
            notes.append("evidence_pack_refresh=ok")
        except Exception as exc:
            notes.append(f"evidence_pack_refresh_error={type(exc).__name__}")

    return last_report_ts, last_pack_ts, notes


def execute_once(client: AlpacaPaperClient, runtime: dict, paper_runtime: dict, selection: dict, args) -> dict:
    account = client.get_account()
    positions = client.list_positions()
    state = load_json(STATE_FILE, {})
    tracked_positions = dict(state.get("tracked_positions", {}))
    recent_exits = dict(state.get("recent_exits", {}))
    recent_close_events = list(state.get("recent_close_events", []))
    entry_pause_until_ts = float(state.get("entry_pause_until_ts", 0.0) or 0.0)
    reentry_cooldown_minutes = float(paper_runtime.get("reentry_cooldown_minutes", 10.0) or 10.0)
    reentry_cooldown_seconds = max(0.0, reentry_cooldown_minutes * 60.0)
    symbols, symbols_source, universe_total_count = resolve_symbols_for_scan(client, paper_runtime)
    snapshots = client.get_snapshots(symbols)

    now_ts = time.time()
    utc_weekday = datetime.now(timezone.utc).weekday()
    weekend_closed = utc_weekday >= 5
    closures = evaluate_closures(positions, tracked_positions, now_ts, paper_runtime)
    note_parts = []

    if closures and not args.status_only and not args.no_orders:
        for item in closures:
            result = client.close_position(item["symbol"])
            append_jsonl(
                LEDGER_FILE,
                {
                    "timestamp": now_utc(),
                    "mode": "ALPACA_PAPER",
                    "action": "close",
                    "symbol": item["symbol"],
                    "uplpc": item["uplpc"],
                    "max_uplpc": item.get("max_uplpc", item["uplpc"]),
                    "trail_drawdown": item.get("trail_drawdown", 0.0),
                    "close_reason": item.get("close_reason", "rule"),
                    "hold_minutes": item["hold_minutes"],
                    "result": result,
                    "note": "Auto-close on adaptive profit protection rules",
                },
            )
            tracked_positions.pop(item["symbol"], None)
            recent_exits[item["symbol"]] = now_utc()
            recent_close_events.append(
                {
                    "ts": now_ts,
                    "symbol": item["symbol"],
                    "uplpc": float(item.get("uplpc", 0.0) or 0.0),
                    "reason": item.get("close_reason", "rule"),
                }
            )
        note_parts.append(f"closed={len(closures)}")

    recent_close_events = [
        event
        for event in recent_close_events
        if now_ts - float(event.get("ts", 0.0) or 0.0) <= 6 * 3600
    ]
    if len(recent_close_events) > 80:
        recent_close_events = recent_close_events[-80:]

    if now_ts >= entry_pause_until_ts:
        loss_streak_window_trades = max(2, int(paper_runtime.get("loss_streak_window_trades", 4) or 4))
        loss_streak_uplpc_threshold = float(paper_runtime.get("loss_streak_uplpc_threshold", -0.0005) or -0.0005)
        loss_streak_pause_minutes = max(1.0, float(paper_runtime.get("loss_streak_pause_minutes", 8.0) or 8.0))
        tail = recent_close_events[-loss_streak_window_trades:]
        if len(tail) == loss_streak_window_trades and all(
            float(event.get("uplpc", 0.0) or 0.0) <= loss_streak_uplpc_threshold for event in tail
        ):
            entry_pause_until_ts = now_ts + (loss_streak_pause_minutes * 60.0)
            note_parts.append(f"entry_pause_triggered={loss_streak_window_trades}_losses")

    entry_pause_active = now_ts < entry_pause_until_ts
    if entry_pause_active:
        remaining_pause_sec = max(0, int(entry_pause_until_ts - now_ts))
        note_parts.append(f"entry_pause_active={remaining_pause_sec}s")

    stale_open_order_minutes = float(paper_runtime.get("stale_open_order_minutes", 5.0) or 5.0)
    stale_open_order_seconds = max(0.0, stale_open_order_minutes * 60.0)
    pending_order_symbols = set()
    canceled_open_orders = []
    if not args.status_only and not args.no_orders:
        pending_order_symbols, canceled_open_orders = cleanup_stale_open_orders(
            client,
            tracked_positions,
            stale_open_order_seconds,
            now_ts,
        )

        # On weekends, equity market orders cannot fill. Cancel all open orders
        # immediately to avoid dead capital and runaway unfilled counts.
        if weekend_closed:
            open_orders = client.list_open_orders()
            for order in open_orders:
                order_id = str(order.get("id", ""))
                if not order_id:
                    continue
                symbol = str(order.get("symbol", "")).upper()
                status = str(order.get("status", "")).lower()
                if status in {"filled", "canceled", "expired", "rejected"}:
                    continue
                result = client.cancel_order(order_id)
                canceled_open_orders.append(
                    {
                        "id": order_id,
                        "symbol": symbol,
                        "status": status,
                        "age_seconds": 0.0,
                        "result": result,
                    }
                )
                tracked_positions.pop(symbol, None)
            pending_order_symbols = set()

        if canceled_open_orders:
            append_jsonl(
                LEDGER_FILE,
                {
                    "timestamp": now_utc(),
                    "mode": "ALPACA_PAPER",
                    "action": "cancel_open_orders",
                    "count": len(canceled_open_orders),
                    "orders": canceled_open_orders,
                    "note": "Auto-cancel open paper orders to release buying power (stale/weekend)",
                },
            )
            note_parts.append(f"canceled_open_orders={len(canceled_open_orders)}")

    positions = client.list_positions()
    account = client.get_account()
    clock = client.get_clock()
    market_open = bool(clock.get("is_open"))
    next_open_utc = _iso_or_none(clock.get("next_open"))
    next_close_utc = _iso_or_none(clock.get("next_close"))
    allow_off_hours_orders = bool(paper_runtime.get("allow_off_hours_orders", False))
    equity = float(account.get("equity") or 0.0)
    buying_power = float(account.get("buying_power") or 0.0)
    cash = float(account.get("cash") or 0.0)
    prior_equity_peak_usd = float(state.get("equity_peak_usd", equity) or equity)
    equity_peak_usd = max(prior_equity_peak_usd, equity)
    drawdown_from_peak_pct = ((equity / max(equity_peak_usd, 1e-9)) - 1.0) if equity_peak_usd > 0 else 0.0
    risk_off_drawdown_pct = float(paper_runtime.get("risk_off_drawdown_pct", -0.015) or -0.015)
    risk_off_position_scale = float(paper_runtime.get("risk_off_position_scale", 0.60) or 0.60)
    risk_off_burst_entries = max(1, int(paper_runtime.get("risk_off_burst_entries", 1) or 1))
    risk_off_mode = drawdown_from_peak_pct <= risk_off_drawdown_pct
    max_positions = int(paper_runtime.get("max_positions", 8) or 8)
    position_size_pct = float(paper_runtime.get("position_size_pct", 0.35) or 0.35)
    min_entry_price = float(paper_runtime.get("min_entry_price", 3.0) or 3.0)
    off_hours_limit_buffer_pct = float(paper_runtime.get("off_hours_limit_buffer_pct", 0.005) or 0.0)

    if len(positions) > max_positions and not args.status_only and not args.no_orders:
        trim_count = len(positions) - max_positions
        weakest = sorted(positions, key=lambda p: float(p.get("unrealized_plpc") or 0.0))[:trim_count]
        for pos in weakest:
            symbol = str(pos.get("symbol", "")).upper()
            uplpc = float(pos.get("unrealized_plpc") or 0.0)
            result = client.close_position(symbol)
            append_jsonl(
                LEDGER_FILE,
                {
                    "timestamp": now_utc(),
                    "mode": "ALPACA_PAPER",
                    "action": "close",
                    "symbol": symbol,
                    "uplpc": uplpc,
                    "close_reason": "portfolio_cap_trim",
                    "result": result,
                    "note": "Auto-close weakest names to honor max_positions cap",
                },
            )
            tracked_positions.pop(symbol, None)
            recent_exits[symbol] = now_utc()

        positions = client.list_positions()
        account = client.get_account()
        equity = float(account.get("equity") or 0.0)
        buying_power = float(account.get("buying_power") or 0.0)
        cash = float(account.get("cash") or 0.0)
        note_parts.append(f"cap_trim={trim_count}")

    held_symbols = {str(pos.get("symbol", "")).upper() for pos in positions}
    entry_policy = resolve_entry_notional_policy(paper_runtime, equity, buying_power, cash)

    # Keep tracked positions aligned with reality: either truly held or currently pending.
    tracked_positions = {
        symbol: payload
        for symbol, payload in tracked_positions.items()
        if str(symbol).upper() in held_symbols or str(symbol).upper() in pending_order_symbols
    }

    tracked_symbols = {str(sym).upper() for sym in tracked_positions.keys()}
    cooldown_symbols = set()
    if reentry_cooldown_seconds > 0:
        for sym, ts in list(recent_exits.items()):
            last_exit_ts = parse_iso_ts(ts)
            if last_exit_ts <= 0:
                recent_exits.pop(sym, None)
                continue
            age_seconds = max(0.0, now_ts - last_exit_ts)
            if age_seconds <= reentry_cooldown_seconds:
                cooldown_symbols.add(str(sym).upper())
            elif age_seconds > 6 * 3600:
                recent_exits.pop(sym, None)

    blocked_symbols = held_symbols | tracked_symbols | pending_order_symbols | cooldown_symbols
    candidate, ranked = choose_candidate(symbols, snapshots, selection, blocked_symbols)
    # Capacity should only count live/pending exposure, not cooldown-excluded symbols.
    effective_open_count = len(held_symbols | tracked_symbols | pending_order_symbols)

    order_results = []
    can_submit_orders = (market_open or allow_off_hours_orders) and not weekend_closed and not entry_pause_active

    if candidate and effective_open_count < max_positions and can_submit_orders and not args.status_only and not args.no_orders:
        remaining_slots = max(1, max_positions - effective_open_count)
        burst_entries = max(1, int(paper_runtime.get("burst_entries_per_cycle", 1) or 1))
        if risk_off_mode:
            burst_entries = min(burst_entries, risk_off_burst_entries)

        min_entry_score = float(paper_runtime.get("min_entry_score", 7.0) or 7.0)
        min_entry_edge_bps = float(paper_runtime.get("min_entry_edge_bps", 100.0) or 100.0)
        min_entry_day_return = float(paper_runtime.get("min_entry_day_return", 0.006) or 0.006)
        min_entry_near_high = float(paper_runtime.get("min_entry_near_high", 0.72) or 0.72)
        min_entry_confidence = float(paper_runtime.get("min_entry_confidence", 0.70) or 0.70)
        min_entry_minute_return = float(paper_runtime.get("min_entry_minute_return", -0.0002) or -0.0002)
        max_entry_day_return = float(paper_runtime.get("max_entry_day_return", 0.22) or 0.22)
        min_entry_volume_impulse = float(paper_runtime.get("min_entry_volume_impulse", 0.25) or 0.25)

        if risk_off_mode:
            min_entry_score += 2.0
            min_entry_edge_bps += 60.0
            min_entry_day_return += 0.004
            min_entry_near_high += 0.05
            min_entry_confidence = max(min_entry_confidence, 0.80)
            min_entry_minute_return = max(min_entry_minute_return, 0.0)

        orderable_ranked = [
            item
            for item in ranked
            if not item.get("held")
            and item.get("price", 0.0) >= min_entry_price
            and item.get("score", 0.0) >= min_entry_score
            and item.get("edge_bps", 0.0) >= min_entry_edge_bps
            and item.get("day_return", 0.0) >= min_entry_day_return
            and item.get("day_return", 0.0) <= max_entry_day_return
            and item.get("near_high", 0.0) >= min_entry_near_high
            and item.get("confidence", 0.0) >= min_entry_confidence
            and item.get("minute_return", 0.0) >= min_entry_minute_return
            and item.get("volume_impulse", 0.0) >= min_entry_volume_impulse
        ]
        to_open = min(remaining_slots, burst_entries, len(orderable_ranked))
        allocated_notional = 0.0
        opened_symbols = []

        # Open multiple top-ranked names in one cycle to accelerate compounding in paper mode.
        for idx, pick in enumerate(orderable_ranked[:to_open]):
            dynamic_position_pct = compute_dynamic_position_pct(pick, paper_runtime, position_size_pct)
            if risk_off_mode:
                dynamic_position_pct *= max(0.25, min(1.0, risk_off_position_scale))
            target_notional = equity * dynamic_position_pct
            remaining_bp_budget = (buying_power * 0.90) - allocated_notional
            minimum_entry_notional_usd = float(entry_policy.get("minimum_entry_notional_usd", 100.0) or 100.0)
            if remaining_bp_budget < minimum_entry_notional_usd:
                break
            slots_left = max(1, to_open - idx)
            capped_notional = min(target_notional, remaining_bp_budget / slots_left)
            notional = round(max(minimum_entry_notional_usd, capped_notional), 2)

            use_extended_hours_limit = bool(allow_off_hours_orders and not market_open)
            base_price = float(pick.get("price") or 0.0)
            limit_price = base_price
            if use_extended_hours_limit and base_price > 0:
                limit_price = base_price * (1.0 + max(0.0, off_hours_limit_buffer_pct))

            order_result = client.submit_buy(
                pick["symbol"],
                notional,
                limit_price=limit_price,
                extended_hours=use_extended_hours_limit,
            )
            order_results.append(
                {
                    "symbol": pick["symbol"],
                    "notional_usd": notional,
                    "result": order_result,
                }
            )
            tracked_positions[pick["symbol"]] = {
                "opened_at": now_utc(),
                "planned_notional": notional,
                "planned_position_size_pct": dynamic_position_pct,
                "score": pick["score"],
                "confidence": pick.get("confidence", 0.0),
                "edge_bps": pick.get("edge_bps", 0.0),
                "day_return": pick.get("day_return", 0.0),
                "max_uplpc": 0.0,
            }
            append_jsonl(
                LEDGER_FILE,
                {
                    "timestamp": now_utc(),
                    "mode": "ALPACA_PAPER",
                    "action": "open",
                    "symbol": pick["symbol"],
                    "notional_usd": notional,
                    "position_size_pct": dynamic_position_pct,
                    "score": pick["score"],
                    "edge_bps": pick["edge_bps"],
                    "confidence": pick["confidence"],
                    "result": order_result,
                    "note": "Adaptive quality-weighted burst entry",
                },
            )
            allocated_notional += notional
            opened_symbols.append(pick["symbol"])

        if opened_symbols:
            note_parts.append(f"opened={','.join(opened_symbols)}")
        else:
            note_parts.append("opened=none")
    elif candidate:
        note_parts.append(f"candidate={candidate['symbol']}")
        if weekend_closed:
            note_parts.append("market=weekend_closed")
            if bool(entry_policy.get("micro_balance_mode", False)):
                note_parts.append("weekend_micro_mode=crypto_route_recommended")
        elif not market_open and not allow_off_hours_orders:
            note_parts.append("market=closed")
            if next_open_utc:
                note_parts.append(f"alpaca_next_open={next_open_utc}")
    else:
        note_parts.append("candidate=none")

    if risk_off_mode:
        note_parts.append(f"risk_off=drawdown_{round(drawdown_from_peak_pct * 100.0, 2)}pct")

    positions = client.list_positions()
    account = client.get_account()
    equity = float(account.get("equity") or 0.0)
    cash = float(account.get("cash") or 0.0)
    open_orders = client.list_open_orders()

    last_report_refresh_ts, last_evidence_pack_refresh_ts, artifact_notes = run_periodic_artifacts(paper_runtime, state, now_ts)
    note_parts.extend(artifact_notes)

    state_payload = {
        "generated_utc": now_utc(),
        "mode": "paper",
        "paper_enabled": True,
        "allow_live_orders": False,
        "selection_source": paper_runtime.get("selection_source", "engine_logic"),
        "symbol_mode": paper_runtime.get("symbol_mode", "ADAPTIVE_UNIVERSE"),
        "runtime_symbol": runtime.get("symbol", "UNIVERSE"),
        "symbols_source": symbols_source,
        "symbol_count": len(symbols),
        "symbol_universe_total": int(universe_total_count),
        "symbols_preview": symbols[:25],
        "pnl_usd": round(equity - float(paper_runtime.get("starting_capital_usd", 100000.0) or 100000.0), 2),
        "equity_usd": equity,
        "equity_peak_usd": equity_peak_usd,
        "drawdown_from_peak_pct": drawdown_from_peak_pct,
        "cash_usd": cash,
        "open_positions": positions,
        "tracked_positions": tracked_positions,
        "recent_exits": recent_exits,
        "recent_close_events": recent_close_events,
        "entry_pause_until_ts": entry_pause_until_ts,
        "last_report_refresh_ts": last_report_refresh_ts,
        "last_evidence_pack_refresh_ts": last_evidence_pack_refresh_ts,
        "status": "READY" if candidate else "WAITING_FOR_CANDIDATE",
        "top_candidate": candidate,
        "top_ranked": ranked[:8],
        "market_open": bool(market_open),
        "alpaca_clock": {
            "is_open": bool(market_open),
            "next_open_utc": next_open_utc,
            "next_close_utc": next_close_utc,
            "timestamp_utc": _iso_or_none(clock.get("timestamp")),
        },
        "weekend_closed": bool(weekend_closed),
        "can_submit_orders": bool(can_submit_orders),
        "risk_off_mode": bool(risk_off_mode),
        "risk_off_drawdown_pct": risk_off_drawdown_pct,
        "risk_off_position_scale": risk_off_position_scale,
        "entry_pause_active": bool(entry_pause_active),
        "reentry_cooldown_minutes": reentry_cooldown_minutes,
        "cooldown_symbols_count": len(cooldown_symbols),
        "micro_balance_mode": bool(entry_policy.get("micro_balance_mode", False)),
        "minimum_entry_notional_usd": float(entry_policy.get("minimum_entry_notional_usd", 100.0) or 100.0),
    }
    save_json(STATE_FILE, state_payload)

    status_payload = build_status_payload(
        account=account,
        runtime=runtime,
        paper_runtime=paper_runtime,
        selection=selection,
        positions=positions,
        candidate=candidate,
        ranked=ranked,
        note=", ".join(note_parts),
        open_orders=open_orders,
        execution_meta={
            "market_open": bool(market_open),
            "alpaca_next_open_utc": next_open_utc,
            "alpaca_next_close_utc": next_close_utc,
            "weekend_closed": bool(weekend_closed),
            "can_submit_orders": bool(can_submit_orders),
            "allow_off_hours_orders": bool(allow_off_hours_orders),
            "micro_balance_mode": bool(entry_policy.get("micro_balance_mode", False)),
            "minimum_entry_notional_usd": float(entry_policy.get("minimum_entry_notional_usd", 100.0) or 100.0),
            "effective_balance_usd": float(entry_policy.get("effective_balance_usd", 0.0) or 0.0),
            "micro_balance_threshold_usd": float(entry_policy.get("micro_balance_threshold_usd", 50.0) or 50.0),
            "equity_peak_usd": float(equity_peak_usd),
            "drawdown_from_peak_pct": float(drawdown_from_peak_pct),
            "risk_off_mode": bool(risk_off_mode),
            "risk_off_drawdown_pct": float(risk_off_drawdown_pct),
            "entry_pause_active": bool(entry_pause_active),
            "entry_pause_until_ts": float(entry_pause_until_ts),
            "min_entry_price": float(min_entry_price),
            "last_report_refresh_ts": float(last_report_refresh_ts),
            "last_evidence_pack_refresh_ts": float(last_evidence_pack_refresh_ts),
            "weekend_route_hint": "kraken_crypto_micro" if weekend_closed else "alpaca_equities",
            "symbols_source": symbols_source,
            "symbol_universe_total": int(universe_total_count),
            "snapshot_scan_limit": len(symbols),
            "reentry_cooldown_minutes": reentry_cooldown_minutes,
            "cooldown_symbols_count": len(cooldown_symbols),
        },
    )
    if order_results:
        status_payload["last_order_result"] = order_results[-1]["result"]
        status_payload["last_order_results"] = order_results
    save_json(STATUS_FILE, status_payload)
    return status_payload


def main():
    parser = argparse.ArgumentParser(description="Alpaca paper executor for aggressive compounding demos")
    parser.add_argument("--status-only", action="store_true", help="Fetch account/candidate status without placing or closing orders")
    parser.add_argument("--no-orders", action="store_true", help="Evaluate signals and state without sending Alpaca paper orders")
    parser.add_argument("--loop", action="store_true", help="Run continuously using paper runtime loop_seconds")
    args = parser.parse_args()

    keys = load_api_keys()
    client = AlpacaPaperClient(
        keys.get("ALPACA_API_KEY", ""),
        keys.get("ALPACA_API_SECRET", ""),
        trading_base=keys.get("ALPACA_PAPER_BASE_URL", ""),
        data_base=keys.get("ALPACA_DATA_BASE_URL", ""),
    )
    if not client.is_configured():
        raise SystemExit(
            "Missing ALPACA_API_KEY / ALPACA_API_SECRET in config/luma_live_keys.env or environment. "
            "Supported aliases: APCA_API_KEY_ID, APCA_API_SECRET_KEY, ALPACA_KEY, ALPACA_SECRET."
        )

    runtime = load_json(RUNTIME_FILE, {})
    paper_runtime = load_json(PAPER_RUNTIME_FILE, {})
    selection = load_json(SELECTION_FILE, {})
    loop_seconds = max(1, int(paper_runtime.get("loop_seconds", 5) or 5))

    while True:
        try:
            payload = execute_once(client, runtime, paper_runtime, selection, args)
        except requests.exceptions.RequestException as exc:
            payload = {
                "generated_utc": now_utc(),
                "mode": "ALPACA_PAPER",
                "status": "NETWORK_RETRY_WAIT",
                "error_type": type(exc).__name__,
                "error": str(exc),
            }
            save_json(STATUS_FILE, payload)
        except Exception as exc:
            payload = {
                "generated_utc": now_utc(),
                "mode": "ALPACA_PAPER",
                "status": "ERROR_RETRY_WAIT",
                "error_type": type(exc).__name__,
                "error": str(exc),
            }
            save_json(STATUS_FILE, payload)
        print(json.dumps(payload, indent=2))
        if not args.loop:
            break
        time.sleep(loop_seconds)


if __name__ == "__main__":
    main()