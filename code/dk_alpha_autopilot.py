"""
DraftKings +EV Alpha Autopilot — Institutional Maximum Build
============================================================
Active tiers (all lazy-imported from code/.venv):
  Tier-0  requests, json, csv            (always)
  Tier-1  numpy, pandas                  (feature engineering)
  Tier-2  sklearn                        (RobustScaler, IsolationForest)
  Tier-3  lightgbm, xgboost             (ML ensemble edge ranker)
  Tier-4  shap                           (explainability, top-10)
  Tier-5  scipy                          (bootstrap CI, log-utility Kelly)
  Tier-6  pypfopt                        (Efficient Frontier allocation)
  Tier-7  quantstats                     (Sharpe/Sortino/Calmar/Omega/MaxDD)
  Tier-8  yfinance                       (VIX macro regime)
  Tier-9  openai                         (GPT-4o-mini narrative, key-gated)
  Tier-10 colorama                       (coloured terminal)
"""
from __future__ import annotations

import argparse
import csv
import importlib
import json
import math
import os
import subprocess
import sys
import time
import warnings
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import requests

warnings.filterwarnings("ignore")

# ── Paths ─────────────────────────────────────────────────────────────────────
ROOT       = Path(r"C:\LumaTrader\INSTITUTIONAL_STACK_V2")
CODE_DIR   = ROOT / "code"
SPORTS_DIR = ROOT / "sports_data"
OUT_DIR    = ROOT / "out" / "sports_intelligence"
ENV_FILE   = CODE_DIR / "execution" / "config" / "luma_live_keys.env"

API_BASE        = "https://api.the-odds-api.com/v4"
MARKET_PRIMARY  = "h2h,spreads,totals"
MARKET_FALLBACK = "h2h"

ALPHA_BOARD_JSON    = OUT_DIR / "_dk_alpha_board.json"
ALPHA_BOARD_CSV     = OUT_DIR / "_dk_alpha_board.csv"
LONGSHOT_BOARD_JSON = OUT_DIR / "_dk_longshot_board.json"
MARKET_CATALOG_JSON = OUT_DIR / "_dk_market_catalog.json"
LOOP_STATE_JSON     = OUT_DIR / "_dk_alpha_alert_state.json"
ADVANCED_STACK_JSON = OUT_DIR / "_dk_advanced_stack_report.json"
SHAP_REPORT_JSON    = OUT_DIR / "_dk_shap_report.json"
NARRATIVE_JSON      = OUT_DIR / "_dk_narratives.json"
MACRO_JSON          = OUT_DIR / "_dk_macro_regime.json"

RICH_VENV_PYTHON = CODE_DIR / ".venv" / "Scripts" / "python.exe"
REEXEC_FLAG_ENV  = "DK_ALPHA_AUTOPILOT_REEXEC"


# ── Terminal colours ──────────────────────────────────────────────────────────
def _colorama_init() -> None:
    try:
        importlib.import_module("colorama").init(autoreset=True)
    except Exception:
        pass


def _c(code: str, text: str) -> str:
    try:
        clr   = importlib.import_module("colorama")
        Fore  = clr.Fore
        Style = clr.Style
        pfx   = {
            "gold":  Fore.YELLOW  + Style.BRIGHT,
            "teal":  Fore.CYAN    + Style.BRIGHT,
            "green": Fore.GREEN   + Style.BRIGHT,
            "red":   Fore.RED     + Style.BRIGHT,
            "dim":   Style.DIM,
        }.get(code, "")
        return pfx + text + Style.RESET_ALL
    except Exception:
        return text


# ── Args ──────────────────────────────────────────────────────────────────────
@dataclass
class Args:
    regions:           str
    sports:            str
    min_edge:          float
    horizon_hours:     float
    bankroll:          float
    kelly_frac:        float
    max_bet:           float
    top_n:             int
    longshot_min_dk:   float
    longshot_min_edge: float
    no_fetch:          bool
    no_flowform:       bool
    no_ml:             bool
    no_openai:         bool
    no_macro:          bool
    loop:              bool
    interval_sec:      int
    iterations:        int
    alert_min_edge:    float
    openai_model:      str = field(default="gpt-4o-mini")


# ── Venv re-exec ──────────────────────────────────────────────────────────────
def maybe_reexec_to_richer_env() -> None:
    if os.getenv(REEXEC_FLAG_ENV) == "1":
        return
    if not RICH_VENV_PYTHON.exists():
        return
    current = Path(sys.executable).resolve()
    target  = RICH_VENV_PYTHON.resolve()
    if current == target:
        return
    env = os.environ.copy()
    env[REEXEC_FLAG_ENV] = "1"
    raise SystemExit(subprocess.run([str(target), str(Path(__file__).resolve()), *sys.argv[1:]], env=env).returncode)


# ── Stack detection ───────────────────────────────────────────────────────────
STACK_CHECKS: dict[str, str] = {
    "numpy":                            "numpy",
    "pandas":                           "pandas",
    "sklearn":                          "scikit-learn",
    "scipy":                            "scipy",
    "pypfopt":                          "PyPortfolioOpt",
    "quantstats":                       "quantstats",
    "lightgbm":                         "lightgbm",
    "xgboost":                          "xgboost",
    "shap":                             "shap",
    "openai":                           "openai",
    "fredapi":                          "fredapi",
    "yfinance":                         "yfinance",
    "alpaca":                           "alpaca-py",
    "prometheus_fastapi_instrumentator":"prometheus-fastapi-instrumentator",
    "zmq":                              "pyzmq",
    "colorama":                         "colorama",
}


def detect_advanced_stack() -> dict[str, Any]:
    modules: dict[str, dict[str, Any]] = {}
    for mod_name, pkg_name in STACK_CHECKS.items():
        try:
            mod = importlib.import_module(mod_name)
            modules[mod_name] = {"installed": True,  "package": pkg_name, "version": getattr(mod, "__version__", "?")}
        except Exception as exc:
            modules[mod_name] = {"installed": False, "package": pkg_name, "error": str(exc)}
    installed_count = sum(1 for m in modules.values() if m.get("installed"))
    return {
        "generated_utc":     now_utc(),
        "python_executable": str(Path(sys.executable).resolve()),
        "installed_count":   installed_count,
        "total_checked":     len(modules),
        "modules":           modules,
    }


def _has(stack: dict[str, Any], *names: str) -> bool:
    mods = stack.get("modules", {})
    return all(bool(mods.get(n, {}).get("installed")) for n in names)


# ── Utilities ─────────────────────────────────────────────────────────────────
def now_utc() -> str:
    return datetime.now(timezone.utc).isoformat()


def write_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2), encoding="utf-8")


def load_json_safe(path: Path) -> Any:
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None


def load_env_file() -> None:
    if not ENV_FILE.exists():
        return
    for line in ENV_FILE.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        key = key.strip(); value = value.strip()
        if key and not os.getenv(key):
            os.environ[key] = value


def get_api_key() -> str:
    for k in ("THEODDS_API_KEY", "ODDS_API_KEY", "SPORTS_ODDS_API_KEY"):
        v = (os.getenv(k) or "").strip()
        if v:
            return v
    return ""


def http_get(url: str, params: dict[str, Any]) -> Any:
    resp = requests.get(url, params=params, timeout=45)
    resp.raise_for_status()
    return resp.json()


# ── Odds core ─────────────────────────────────────────────────────────────────
def no_vig_fair_nway(prices: list[float], idx: int) -> float:
    implied = [1.0 / p for p in prices]
    total   = sum(implied)
    return 1.0 / (implied[idx] / total)


def to_american(d: float) -> str:
    if d >= 2.0:
        return f"+{int(round((d - 1.0) * 100))}"
    return f"-{int(round(100.0 / (d - 1.0)))}"


def kelly_variants(dk_price: float, fair_price: float, bankroll: float, max_bet: float) -> dict[str, float]:
    """Full / Half / Quarter / Growth-Optimal Kelly variants."""
    b = dk_price - 1.0
    p = min(1.0, max(0.0, 1.0 / fair_price))
    q = 1.0 - p
    zero = {k: 0.0 for k in ("full_f","half_f","quarter_f","go_f",
                               "full_stake","half_stake","quarter_stake","go_stake")}
    if b <= 0:
        return zero
    full_f = max(0.0, (b * p - q) / b)
    # Growth-optimal: penalise by variance of the bet (log-utility second derivative)
    variance = p * q * (b + 1.0) ** 2
    go_f     = max(0.0, full_f / (1.0 + variance * 0.5))
    return {
        "full_f":        round(full_f,           6),
        "half_f":        round(full_f * 0.5,     6),
        "quarter_f":     round(full_f * 0.25,    6),
        "go_f":          round(go_f,             6),
        "full_stake":    round(min(max_bet, bankroll * full_f),         2),
        "half_stake":    round(min(max_bet, bankroll * full_f * 0.5),   2),
        "quarter_stake": round(min(max_bet, bankroll * full_f * 0.25),  2),
        "go_stake":      round(min(max_bet, bankroll * go_f),           2),
    }


def ev_metrics(dk_price: float, fair_price: float, stake: float) -> dict[str, float]:
    p_win  = min(1.0, max(0.0, 1.0 / fair_price))
    payoff = dk_price - 1.0
    ev     = stake * (p_win * payoff - (1.0 - p_win))
    roi    = ev / stake if stake > 0 else 0.0
    try:
        log_growth = p_win * math.log(1.0 + stake * payoff) + (1.0 - p_win) * math.log(max(1e-9, 1.0 - stake))
    except Exception:
        log_growth = 0.0
    return {"ev_dollars": round(ev, 4), "ev_roi": round(roi, 4), "log_growth_rate": round(log_growth, 6)}


# ── Multi-book consensus ───────────────────────────────────────────────────────
def consensus_fair_price(
    all_books: dict[str, dict[str, dict[str, float]]],
    group_key: str,
    pick: str,
    min_books: int = 2,
) -> tuple[float | None, int]:
    """No-vig fair price as median across all available books."""
    fair_prices: list[float] = []
    for bk_markets in all_books.values():
        bk_group = bk_markets.get(group_key, {})
        if pick not in bk_group:
            continue
        names  = list(bk_group.keys())
        prices = list(bk_group.values())
        if len(prices) < 2:
            continue
        try:
            idx  = names.index(pick)
            fair = no_vig_fair_nway(prices, idx)
            if 1.0 < fair < 1000.0:
                fair_prices.append(fair)
        except Exception:
            continue
    if len(fair_prices) < min_books:
        return None, len(fair_prices)
    import statistics
    return round(statistics.median(fair_prices), 6), len(fair_prices)


# ── Line-movement detection ────────────────────────────────────────────────────
def detect_line_movement(current_rows: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    prev = load_json_safe(ALPHA_BOARD_JSON)
    if not isinstance(prev, dict):
        return {}
    prev_cache = {r["alert_id"]: float(r.get("dk_price_decimal", 0.0)) for r in prev.get("rows", []) if "alert_id" in r}
    movements: dict[str, dict[str, Any]] = {}
    for row in current_rows:
        aid    = row.get("alert_id", "")
        cur_dk = float(row.get("dk_price_decimal", 0.0))
        if aid in prev_cache and prev_cache[aid] > 0:
            delta      = cur_dk - prev_cache[aid]
            pct_change = delta / prev_cache[aid] * 100.0
            movements[aid] = {
                "prev_dk":     round(prev_cache[aid], 4),
                "current_dk":  round(cur_dk, 4),
                "delta":       round(delta, 4),
                "pct_change":  round(pct_change, 4),
                "sharp_signal": pct_change < -1.0,   # line shortening = sharp action
            }
    return movements


# ── Macro regime (VIX via yfinance) ───────────────────────────────────────────
def fetch_macro_regime(stack: dict[str, Any], args: Args) -> dict[str, Any]:
    base = {"regime": "unknown", "vix": None, "spy_5d_pct": None,
            "regime_mult": 1.0, "generated_utc": now_utc()}
    if args.no_macro or not _has(stack, "yfinance"):
        return base
    try:
        yf       = importlib.import_module("yfinance")
        vix_data = yf.download("^VIX", period="5d", interval="1d", progress=False, auto_adjust=True)
        vix      = float(vix_data["Close"].iloc[-1]) if not vix_data.empty else 20.0
        spy_data = yf.download("SPY",  period="10d", interval="1d", progress=False, auto_adjust=True)
        spy_mom  = float((spy_data["Close"].iloc[-1] / spy_data["Close"].iloc[-5] - 1.0) * 100.0) \
                   if len(spy_data) >= 5 else 0.0
        regime      = "calm" if vix < 15 else ("normal" if vix < 25 else ("elevated" if vix < 35 else "crisis"))
        regime_mult = {"calm": 1.0, "normal": 1.0, "elevated": 0.75, "crisis": 0.5}[regime]
        result = {"generated_utc": now_utc(), "vix": round(vix, 2),
                  "spy_5d_pct": round(spy_mom, 4), "regime": regime, "regime_mult": regime_mult}
        write_json(MACRO_JSON, result)
        return result
    except Exception as exc:
        return {**base, "error": str(exc)}


# ── FlowForm integration ───────────────────────────────────────────────────────
def load_flowform_signals() -> list[dict[str, Any]]:
    flow_path = OUT_DIR / "_flowform_ranked.json"
    if not flow_path.exists():
        return []
    try:
        payload = json.loads(flow_path.read_text(encoding="utf-8"))
    except Exception:
        return []
    signals = payload.get("signals", []) if isinstance(payload, dict) else []
    return [s for s in signals if isinstance(s, dict)]


def flowform_match(row: dict[str, Any], flow_signals: list[dict[str, Any]]) -> dict[str, Any]:
    sport_key = row.get("sport_key", "")
    home      = row.get("home_team", "")
    away      = row.get("away_team", "")
    market    = row.get("market", "")
    matches   = [
        s for s in flow_signals
        if s.get("sport_key") == sport_key
        and str(s.get("home_team", "")) == home
        and str(s.get("away_team", "")) == away
        and str(s.get("market", "")) == market
    ]
    if not matches:
        return {"flowform_count": 0, "flowform_best_score": 0.0,
                "flowform_best_hhs": 0.0, "flowform_signal_types": []}
    return {
        "flowform_count":        len(matches),
        "flowform_best_score":   round(max(float(m.get("score",  0.0) or 0.0) for m in matches), 4),
        "flowform_best_hhs":     round(max(float((m.get("flowform", {}) or {}).get("hybrid_harmonic_score", 0.0) or 0.0) for m in matches), 4),
        "flowform_signal_types": sorted({str(m.get("signal_type", "")) for m in matches if m.get("signal_type")}),
    }


# ── scipy bootstrap CI ────────────────────────────────────────────────────────
def edge_confidence_interval(
    dk_price: float, fair_price: float,
    stack: dict[str, Any], n_bootstrap: int = 500,
) -> dict[str, float]:
    if not _has(stack, "scipy", "numpy"):
        return {"edge_ci_lo": 0.0, "edge_ci_hi": 0.0}
    try:
        np    = importlib.import_module("numpy")
        rng   = np.random.default_rng(42)
        p_hat = min(1.0, max(0.0, 1.0 / fair_price))
        samples = rng.binomial(1, p_hat, size=(n_bootstrap, 100)).mean(axis=1)
        edges   = (dk_price * samples - 1.0) * 100.0
        return {
            "edge_ci_lo": round(float(np.percentile(edges, 2.5)),  3),
            "edge_ci_hi": round(float(np.percentile(edges, 97.5)), 3),
        }
    except Exception:
        return {"edge_ci_lo": 0.0, "edge_ci_hi": 0.0}


# ── Fetch universe ─────────────────────────────────────────────────────────────
def list_active_sports(api_key: str) -> list[str]:
    payload = http_get(f"{API_BASE}/sports", {"apiKey": api_key})
    out = [str(item["key"]).strip() for item in payload
           if isinstance(item, dict) and item.get("active") and item.get("key")]
    return sorted(out)


def fetch_sport_events(api_key: str, sport_key: str, regions: str, markets: str) -> list[dict[str, Any]]:
    payload = http_get(f"{API_BASE}/sports/{sport_key}/odds",
                       {"apiKey": api_key, "regions": regions, "markets": markets,
                        "oddsFormat": "decimal", "dateFormat": "iso"})
    return [x for x in payload if isinstance(x, dict)] if isinstance(payload, list) else []


def fetch_universe(api_key: str, args: Args) -> dict[str, Any]:
    SPORTS_DIR.mkdir(parents=True, exist_ok=True)
    sports   = list_active_sports(api_key) if args.sports.strip().lower() == "all" \
               else [s.strip() for s in args.sports.split(",") if s.strip()]
    manifest: dict[str, Any] = {"generated_utc": now_utc(), "regions": args.regions,
                                 "sports_requested": len(sports), "sports": {}}
    for sport_key in sports:
        event_rows: list[dict[str, Any]] = []
        used_markets = MARKET_PRIMARY
        try:
            event_rows = fetch_sport_events(api_key, sport_key, args.regions, MARKET_PRIMARY)
        except requests.HTTPError:
            try:
                used_markets = MARKET_FALLBACK
                event_rows   = fetch_sport_events(api_key, sport_key, args.regions, MARKET_FALLBACK)
            except Exception as exc:
                manifest["sports"][sport_key] = {"ok": False, "events": 0, "error": str(exc)}
                continue
        except Exception as exc:
            manifest["sports"][sport_key] = {"ok": False, "events": 0, "error": str(exc)}
            continue
        out_path = SPORTS_DIR / f"{sport_key}_allbooks_live_odds.json"
        write_json(out_path, event_rows)
        manifest["sports"][sport_key] = {"ok": True, "events": len(event_rows),
                                         "markets_used": used_markets, "path": str(out_path)}
    write_json(SPORTS_DIR / "allbooks_manifest.json", manifest)
    return manifest


# ── Market catalog ─────────────────────────────────────────────────────────────
def build_market_catalog() -> dict[str, Any]:
    catalog: dict[str, Any] = {"generated_utc": now_utc(), "sports": {}, "global_markets": {}}
    for path in sorted(SPORTS_DIR.glob("*_allbooks_live_odds.json")):
        sport_key    = path.name.replace("_allbooks_live_odds.json", "")
        per_market: dict[str, int] = {}
        total_events = 0
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            continue
        if not isinstance(data, list):
            continue
        for ev in data:
            if not isinstance(ev, dict):
                continue
            total_events += 1
            for bm in ev.get("bookmakers", []):
                if not isinstance(bm, dict) or bm.get("key") != "draftkings":
                    continue
                for market in bm.get("markets", []):
                    if not isinstance(market, dict):
                        continue
                    mk = str(market.get("key", "")).strip()
                    if not mk:
                        continue
                    per_market[mk]                = per_market.get(mk, 0) + 1
                    catalog["global_markets"][mk] = catalog["global_markets"].get(mk, 0) + 1
        catalog["sports"][sport_key] = {
            "events":     total_events,
            "dk_markets": dict(sorted(per_market.items(), key=lambda kv: (-kv[1], kv[0]))),
        }
    catalog["global_markets"] = dict(sorted(catalog["global_markets"].items(), key=lambda kv: (-kv[1], kv[0])))
    write_json(MARKET_CATALOG_JSON, catalog)
    return catalog


# ── Core alpha row builder ─────────────────────────────────────────────────────
def build_alpha_rows(args: Args, stack: dict[str, Any]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    now          = datetime.now(timezone.utc)
    flow_signals = load_flowform_signals()

    for path in sorted(SPORTS_DIR.glob("*_allbooks_live_odds.json")):
        sport_key = path.name.replace("_allbooks_live_odds.json", "")
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            continue
        if not isinstance(data, list):
            continue

        for ev in data:
            if not isinstance(ev, dict):
                continue
            commence_time = str(ev.get("commence_time", ""))
            if not commence_time:
                continue
            try:
                start_dt = datetime.fromisoformat(commence_time.replace("Z", "+00:00"))
            except Exception:
                continue
            hours_to_start = (start_dt - now).total_seconds() / 3600.0
            if hours_to_start <= 0:
                continue
            if args.horizon_hours > 0 and hours_to_start > args.horizon_hours:
                continue

            home_team = str(ev.get("home_team", ""))
            away_team = str(ev.get("away_team", ""))
            game      = f"{away_team} @ {home_team}".strip()

            # Build full all-books price tree
            all_books: dict[str, dict[str, dict[str, float]]] = {}
            for bm in ev.get("bookmakers", []):
                if not isinstance(bm, dict):
                    continue
                bk = str(bm.get("key", ""))
                if not bk:
                    continue
                all_books[bk] = {}
                for market in bm.get("markets", []):
                    if not isinstance(market, dict):
                        continue
                    mk = str(market.get("key", ""))
                    if mk not in ("h2h", "spreads", "totals"):
                        continue
                    for outcome in market.get("outcomes", []):
                        if not isinstance(outcome, dict):
                            continue
                        name  = str(outcome.get("name", ""))
                        price = outcome.get("price")
                        point = outcome.get("point", "")
                        if not name or not isinstance(price, (int, float)):
                            continue
                        gk = f"{mk}::{point}"
                        all_books[bk].setdefault(gk, {})[name] = float(price)

            dk  = all_books.get("draftkings", {})
            pin = all_books.get("pinnacle",   {})
            if not dk or not pin:
                continue

            for group_key, pin_map in pin.items():
                if group_key not in dk or len(pin_map) < 2:
                    continue
                dk_map     = dk[group_key]
                names      = list(pin_map.keys())
                pin_prices = [pin_map[n] for n in names]
                pin_fair   = {n: no_vig_fair_nway(pin_prices, i) for i, n in enumerate(names)}
                market_key, point = group_key.split("::", 1)

                for pick, dk_price in dk_map.items():
                    fair_price_pin = pin_fair.get(pick)
                    if fair_price_pin is None:
                        continue

                    # Multi-book consensus (median no-vig, ≥3 books preferred)
                    consensus_fp, n_books = consensus_fair_price(all_books, group_key, pick, min_books=2)
                    fair_price = consensus_fp if (consensus_fp and n_books >= 3) else fair_price_pin

                    edge_pct = (dk_price / fair_price - 1.0) * 100.0
                    if edge_pct < args.min_edge:
                        continue

                    kv    = kelly_variants(dk_price, fair_price, args.bankroll, args.max_bet)
                    stake = kv["quarter_stake"]
                    evm   = ev_metrics(dk_price, fair_price, stake)

                    row: dict[str, Any] = {
                        "sport_key":            sport_key,
                        "home_team":            home_team,
                        "away_team":            away_team,
                        "game":                 game,
                        "market":               market_key,
                        "pick":                 pick,
                        "point":                point,
                        "dk_price_decimal":     round(dk_price, 4),
                        "dk_price_american":    to_american(dk_price),
                        "fair_price_decimal":   round(fair_price, 4),
                        "fair_price_pin":       round(fair_price_pin, 4),
                        "fair_price_consensus": round(consensus_fp, 4) if consensus_fp else None,
                        "n_books_consensus":    n_books,
                        "edge_pct":             round(edge_pct, 4),
                        "hours_to_start":       round(hours_to_start, 3),
                        "commence_time":        commence_time,
                        # Kelly variants
                        "kelly_full_f":         kv["full_f"],
                        "kelly_half_f":         kv["half_f"],
                        "kelly_quarter_f":      kv["quarter_f"],
                        "kelly_go_f":           kv["go_f"],
                        "kelly_stake":          kv["quarter_stake"],
                        "kelly_half_stake":     kv["half_stake"],
                        "kelly_go_stake":       kv["go_stake"],
                        "stake_cap":            args.max_bet,
                        "stake_return_if_win":  round(stake * dk_price, 2),
                        "stake_profit_if_win":  round(stake * (dk_price - 1.0), 2),
                        # EV
                        "ev_dollars":           evm["ev_dollars"],
                        "ev_roi":               evm["ev_roi"],
                        "log_growth_rate":      evm["log_growth_rate"],
                        # Placeholders — filled by downstream layers
                        "optimized_stake":      kv["quarter_stake"],
                        "optimized_weight":     None,
                        "ml_edge_score":        0.0,
                        "ml_confidence":        0.0,
                        "shap_top_feature":     None,
                        "shap_top_value":       None,
                        "line_moved":           False,
                        "line_delta":           0.0,
                        "sharp_money_signal":   False,
                        "alpha_score":          0.0,
                        "alpha_score_v2":       0.0,
                        "edge_ci_lo":           0.0,
                        "edge_ci_hi":           0.0,
                        "narrative":            None,
                    }
                    row.update(flowform_match(row, flow_signals))
                    row["alpha_score"] = round(
                        row["edge_pct"] * 2.0
                        + row["flowform_best_hhs"] * 0.25
                        + row["flowform_count"]   * 1.0, 4,
                    )
                    row["alert_id"] = "|".join([
                        row["sport_key"], row["game"], row["market"],
                        row["pick"], str(row["point"]), f"{row['dk_price_decimal']:.4f}",
                    ])
                    rows.append(row)

    rows.sort(key=lambda r: (r["alpha_score"], r["edge_pct"]), reverse=True)
    return rows


# ── ML Ensemble (LightGBM + XGBoost + SHAP) ───────────────────────────────────
_SPORT_ENCODER:  dict[str, int] = {}
_MARKET_ENCODER: dict[str, int] = {}
_FEATURE_NAMES = [
    "edge_pct", "log_dk_price", "hours_to_start", "time_weight",
    "kelly_go_pct", "flowform_hhs", "flowform_count", "n_books_consensus",
    "sport_id", "market_id",
]


def _build_feature_matrix(rows: list[dict[str, Any]], horizon: float) -> Any:
    np = importlib.import_module("numpy")
    X  = []
    for r in rows:
        sport_id  = _SPORT_ENCODER.setdefault(r.get("sport_key", ""), len(_SPORT_ENCODER))
        market_id = _MARKET_ENCODER.setdefault(r.get("market", ""), len(_MARKET_ENCODER))
        hours     = float(r.get("hours_to_start", 1.0))
        time_w    = max(0.0, 1.0 - hours / max(horizon, 1.0))
        X.append([
            float(r.get("edge_pct", 0.0)),
            np.log1p(float(r.get("dk_price_decimal", 2.0))),
            hours, time_w,
            float(r.get("kelly_go_f", 0.0)) * 100.0,
            float(r.get("flowform_best_hhs", 0.0)),
            float(r.get("flowform_count", 0)),
            float(r.get("n_books_consensus", 1)),
            float(sport_id), float(market_id),
        ])
    return np.array(X, dtype=np.float32)


def _build_target(rows: list[dict[str, Any]], horizon: float) -> Any:
    np = importlib.import_module("numpy")
    y = []
    for r in rows:
        edge = float(r.get("edge_pct", 0.0))
        tw   = max(0.0, 1.0 - float(r.get("hours_to_start", 1.0)) / max(horizon, 1.0))
        ff   = float(r.get("flowform_best_hhs", 0.0))
        y.append(edge * (1.0 + tw) * (1.0 + ff * 0.1))
    return np.array(y, dtype=np.float32)


def apply_ml_ensemble(
    rows: list[dict[str, Any]], args: Args, stack: dict[str, Any],
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    report: dict[str, Any] = {"lgbm": False, "xgb": False, "shap": False}
    if args.no_ml or len(rows) < 4 or not _has(stack, "numpy", "lightgbm", "xgboost"):
        return rows, report
    try:
        np  = importlib.import_module("numpy")
        lgb = importlib.import_module("lightgbm")
        xgb = importlib.import_module("xgboost")

        X = _build_feature_matrix(rows, args.horizon_hours)
        y = _build_target(rows, args.horizon_hours)

        # ── LightGBM ──────────────────────────────────────────────────────────
        lgb_ds    = lgb.Dataset(X, label=y, feature_name=_FEATURE_NAMES, free_raw_data=False)
        lgb_model = lgb.train(
            {"objective": "regression", "metric": "rmse", "num_leaves": 15,
             "max_depth": 4, "learning_rate": 0.08, "min_child_samples": 2,
             "subsample": 0.8, "colsample_bytree": 0.8, "verbose": -1, "force_col_wise": True},
            lgb_ds, num_boost_round=200, valid_sets=[lgb_ds],
            callbacks=[lgb.early_stopping(20, verbose=False), lgb.log_evaluation(-1)],
        )
        lgb_preds = lgb_model.predict(X)
        report["lgbm"] = True

        # ── XGBoost ───────────────────────────────────────────────────────────
        xgb_dm    = xgb.DMatrix(X, label=y, feature_names=_FEATURE_NAMES)
        xgb_model = xgb.train(
            {"objective": "reg:squarederror", "eval_metric": "rmse", "max_depth": 4,
             "eta": 0.08, "subsample": 0.8, "colsample_bytree": 0.8,
             "min_child_weight": 1, "verbosity": 0},
            xgb_dm, num_boost_round=200,
            evals=[(xgb_dm, "train")], verbose_eval=False, early_stopping_rounds=20,
        )
        xgb_preds = xgb_model.predict(xgb_dm)
        report["xgb"] = True

        # ── Ensemble average → normalised confidence ──────────────────────────
        ensemble  = (lgb_preds + xgb_preds) / 2.0
        e_min, e_max = ensemble.min(), ensemble.max()
        confidence   = (ensemble - e_min) / (e_max - e_min) if e_max > e_min else np.zeros_like(ensemble)
        for i, row in enumerate(rows):
            row["ml_edge_score"] = round(float(ensemble[i]),   4)
            row["ml_confidence"] = round(float(confidence[i]), 4)

        # ── SHAP explainability (top-10) ──────────────────────────────────────
        if _has(stack, "shap"):
            try:
                shap      = importlib.import_module("shap")
                n_explain = min(10, len(rows))
                explainer = shap.TreeExplainer(lgb_model)
                shap_vals = explainer.shap_values(X[:n_explain])
                if isinstance(shap_vals, list):
                    shap_vals = shap_vals[0]
                shap_report: list[dict[str, Any]] = []
                for i in range(n_explain):
                    abs_sv     = np.abs(shap_vals[i])
                    top_feat_i = int(np.argmax(abs_sv))
                    rows[i]["shap_top_feature"] = _FEATURE_NAMES[top_feat_i]
                    rows[i]["shap_top_value"]   = round(float(shap_vals[i][top_feat_i]), 4)
                    shap_report.append({
                        "pick": rows[i].get("pick"), "game": rows[i].get("game"),
                        "shap_summary": {fn: round(float(shap_vals[i][fi]), 4)
                                         for fi, fn in enumerate(_FEATURE_NAMES)},
                    })
                write_json(SHAP_REPORT_JSON, {"generated_utc": now_utc(),
                                               "n_explained": n_explain, "picks": shap_report})
                report["shap"] = True
            except Exception as exc:
                report["shap_error"] = str(exc)
    except Exception as exc:
        report["error"] = str(exc)
    return rows, report


# ── sklearn layer: RobustScaler + IsolationForest ─────────────────────────────
def apply_sklearn_layer(
    rows: list[dict[str, Any]], args: Args, stack: dict[str, Any],
) -> tuple[list[dict[str, Any]], bool]:
    if not _has(stack, "numpy", "pandas", "sklearn") or not rows:
        return rows, False
    try:
        np  = importlib.import_module("numpy")
        pd  = importlib.import_module("pandas")
        pp  = importlib.import_module("sklearn.preprocessing")
        ens = importlib.import_module("sklearn.ensemble")

        df      = pd.DataFrame(rows)
        horizon = max(args.horizon_hours, 1.0)
        df["time_weight"] = np.clip(1.0 - (df["hours_to_start"] / horizon), 0.0, 1.0)
        df["edge_scaled"] = pp.RobustScaler().fit_transform(df[["edge_pct"]].values).ravel()

        feat_cols = [c for c in ["edge_pct", "hours_to_start", "dk_price_decimal", "kelly_go_f"] if c in df.columns]
        if len(feat_cols) >= 2 and len(df) >= 4:
            iso_scores = ens.IsolationForest(contamination=0.1, random_state=42, n_estimators=100) \
                            .fit_predict(df[feat_cols].fillna(0.0))
            df["isolation_flag"] = (iso_scores == -1).astype(float)
        else:
            df["isolation_flag"] = 0.0

        df["alpha_score"] = (
            df["alpha_score"]
            + df["edge_scaled"]    * 2.5
            + df["time_weight"]    * 1.5
            + df["isolation_flag"] * 1.0
        ).round(4)
        rows = df.sort_values(["alpha_score", "edge_pct"], ascending=False).to_dict("records")
        return rows, True
    except Exception:
        return rows, False


# ── PyPortfolioOpt Efficient Frontier allocation ───────────────────────────────
def apply_pypfopt(
    rows: list[dict[str, Any]], args: Args, stack: dict[str, Any],
) -> tuple[list[dict[str, Any]], bool]:
    if not _has(stack, "numpy", "pypfopt") or not rows:
        return rows, False
    try:
        np = importlib.import_module("numpy")
        EfficientFrontier = importlib.import_module("pypfopt.efficient_frontier").EfficientFrontier
        candidates = [r for r in rows if float(r.get("edge_pct", 0.0)) > 0.0]
        n = min(25, len(candidates))
        if n < 2:
            return rows, False
        top = candidates[:n]
        mu  = np.array([float(r["edge_pct"]) / 100.0 for r in top], dtype=float)
        var = []
        for r in top:
            p_win  = min(1.0, max(0.0, 1.0 / float(r["fair_price_decimal"])))
            payoff = float(r["dk_price_decimal"]) - 1.0
            exp_r  = p_win * payoff - (1.0 - p_win)
            v      = p_win * (payoff - exp_r) ** 2 + (1.0 - p_win) * (-1.0 - exp_r) ** 2
            var.append(max(v, 1e-6))
        ef = EfficientFrontier(mu, np.diag(np.array(var)), weight_bounds=(0.0, 1.0))
        ef.max_sharpe(risk_free_rate=0.0)
        weights = ef.clean_weights()
        if sum(float(w) for w in weights.values()) > 0:
            for idx, row in enumerate(top):
                w = float(weights.get(idx, 0.0))
                row["optimized_stake"]  = round(min(args.max_bet, args.bankroll * w), 2)
                row["optimized_weight"] = round(w, 6)
        return rows, True
    except Exception:
        return rows, False


# ── QuantStats expanded snapshot ──────────────────────────────────────────────
def quantstats_snapshot(rows: list[dict[str, Any]], stack: dict[str, Any]) -> dict[str, Any]:
    if not _has(stack, "quantstats", "pandas") or not rows:
        return {}
    try:
        pd = importlib.import_module("pandas")
        qs = importlib.import_module("quantstats")

        expected_rets = [
            min(1.0, max(0.0, 1.0 / float(r["fair_price_decimal"]))) * (float(r["dk_price_decimal"]) - 1.0)
            - (1.0 - min(1.0, max(0.0, 1.0 / float(r["fair_price_decimal"]))))
            for r in rows
        ]
        ser = pd.Series(expected_rets)
        cum = pd.Series((1.0 + ser).cumprod().values)

        def _safe(fn, *a, **kw):
            try:
                v = fn(*a, **kw)
                return round(float(v), 6) if v is not None else None
            except Exception:
                return None

        return {
            "sample_size": len(ser),
            "sharpe":      _safe(qs.stats.sharpe,       ser, rf=0.0),
            "sortino":     _safe(qs.stats.sortino,      ser, rf=0.0),
            "volatility":  _safe(qs.stats.volatility,   ser),
            "skewness":    _safe(qs.stats.skew,         ser),
            "kurtosis":    _safe(qs.stats.kurtosis,     ser),
            "calmar":      _safe(qs.stats.calmar,       cum),
            "omega":       _safe(qs.stats.omega,        ser, rf=0.0),
            "max_dd":      _safe(qs.stats.max_drawdown, cum),
        }
    except Exception:
        return {}


# ── OpenAI narrative generation ────────────────────────────────────────────────
def generate_narratives(rows: list[dict[str, Any]], args: Args, stack: dict[str, Any]) -> None:
    if args.no_openai or not _has(stack, "openai"):
        return
    openai_key = (os.getenv("OPENAI_API_KEY") or "").strip()
    if not openai_key:
        return
    try:
        openai = importlib.import_module("openai")
        client = openai.OpenAI(api_key=openai_key)
        top_rows = [r for r in rows if r.get("edge_pct", 0.0) > 0.0][:5]
        if not top_rows:
            return
        picks_summary = "\n".join([
            f"- {r['pick']} ({r['game']}, {r['market']}, DK={r['dk_price_american']}, "
            f"Edge={r['edge_pct']:.2f}%, EV=${r.get('ev_dollars',0):.2f}, "
            f"Books={r.get('n_books_consensus',1)}, ML={r.get('ml_edge_score',0):.2f})"
            for r in top_rows
        ])
        resp   = client.chat.completions.create(
            model=args.openai_model,
            messages=[{"role": "user", "content":
                "You are an elite sports betting analyst. "
                "For each pick below write ONE sharp sentence explaining the edge. "
                "Respond as JSON {\"pick_name\": \"sentence\"}\n\n" + picks_summary}],
            max_tokens=400, temperature=0.3,
        )
        text   = resp.choices[0].message.content or ""
        start  = text.find("{")
        end    = text.rfind("}") + 1
        parsed: dict[str, str] = {}
        if start >= 0 and end > start:
            parsed = json.loads(text[start:end])
        narratives: dict[str, str] = {}
        for r in top_rows:
            pick_name = r.get("pick", "")
            for k, v in parsed.items():
                if pick_name.lower() in k.lower() or k.lower() in pick_name.lower():
                    r["narrative"] = str(v)
                    narratives[r.get("alert_id", "")] = str(v)
                    break
        write_json(NARRATIVE_JSON, {"generated_utc": now_utc(),
                                    "model": args.openai_model, "narratives": narratives})
    except Exception as exc:
        write_json(NARRATIVE_JSON, {"error": str(exc), "generated_utc": now_utc()})


# ── Composite alpha_score_v2 ───────────────────────────────────────────────────
def compute_alpha_v2(
    rows: list[dict[str, Any]], macro: dict[str, Any], args: Args,
) -> list[dict[str, Any]]:
    regime_mult = float(macro.get("regime_mult", 1.0))
    horizon     = max(args.horizon_hours, 1.0)
    ml_scores   = [float(r.get("ml_edge_score", 0.0)) for r in rows]
    ml_min      = min(ml_scores) if ml_scores else 0.0
    ml_range    = (max(ml_scores) - ml_min) if len(ml_scores) > 1 and max(ml_scores) > ml_min else 1.0
    for row in rows:
        ml_norm = ((float(row.get("ml_edge_score", 0.0)) - ml_min) / ml_range) * 10.0
        row["alpha_score_v2"] = round((
            float(row.get("edge_pct",            0.0)) * 3.0
            + ml_norm                                  * 1.5
            + float(row.get("flowform_best_hhs", 0.0)) * 0.5
            + float(row.get("flowform_count",    0))   * 0.3
            + max(0.0, 1.0 - row.get("hours_to_start", 0.0) / horizon) * 1.0
            + float(row.get("optimized_weight") or 0.0) * 5.0
            + float(row.get("n_books_consensus", 1))   * 0.2
            + max(0.0, float(row.get("edge_ci_lo", 0.0))) * 0.5
            + (2.0 if row.get("sharp_money_signal") else 0.0)
        ) * regime_mult, 4)
        row["regime_applied"] = macro.get("regime", "unknown")
        row["regime_mult"]    = regime_mult
    rows.sort(key=lambda r: (r["alpha_score_v2"], r["edge_pct"]), reverse=True)
    return rows


# ── CSV writer ────────────────────────────────────────────────────────────────
def write_csv(rows: list[dict[str, Any]], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if not rows:
        path.write_text("", encoding="utf-8")
        return
    fieldnames = list(rows[0].keys())
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


# ── FlowForm subprocess ────────────────────────────────────────────────────────
def run_flowform_layer() -> None:
    subprocess.run(
        [str(Path(os.getenv("PYTHON_EXECUTABLE", "") or sys.executable)),
         str(CODE_DIR / "sports_intelligence_layer.py")], check=False,
    )


# ── Loop state ────────────────────────────────────────────────────────────────
def load_previous_state() -> dict[str, Any]:
    try:
        payload = json.loads(LOOP_STATE_JSON.read_text(encoding="utf-8"))
        return payload if isinstance(payload, dict) else {"last_alert_ids": []}
    except Exception:
        return {"last_alert_ids": []}


def save_state(alert_ids: list[str]) -> None:
    write_json(LOOP_STATE_JSON, {"saved_utc": now_utc(), "last_alert_ids": sorted(set(alert_ids))})


# ── Terminal print ────────────────────────────────────────────────────────────
def print_top_rows(rows: list[dict[str, Any]], title: str, top_n: int) -> None:
    print("\n" + _c("gold", title))
    if not rows:
        print(_c("dim", "  (none)"))
        return
    for idx, row in enumerate(rows[:top_n], start=1):
        pt        = "(" + str(row["point"]) + ")" if str(row.get("point", "")) else ""
        sh        = _c("red", " ⚡SHARP") if row.get("sharp_money_signal") else ""
        ci        = " CI[{:.1f},{:.1f}]".format(row.get("edge_ci_lo", 0), row.get("edge_ci_hi", 0))
        shap_feat = row.get("shap_top_feature")
        shap_note = (" [shap:{}={:+.3f}]".format(shap_feat, row.get("shap_top_value", 0))
                     if shap_feat else "")
        edge_str  = _c("green", "{:>6.2f}%".format(row["edge_pct"]))
        v2_str    = _c("teal",  "{:>7.2f}".format(row["alpha_score_v2"]))
        ml_str    = _c("dim",   "ML={:>5.2f}".format(row.get("ml_edge_score", 0)))
        go_stake  = row.get("kelly_go_stake", row["kelly_stake"])
        line1 = "  {:>2}. [{}] [v2={}] [{}]{} {} | {} | {} {} {}".format(
            idx, edge_str, v2_str, ml_str, sh,
            row["sport_key"], row["game"], row["market"], row["pick"], pt,
        )
        line2 = " | DK={} ({:.3f}) | K${:.2f} Go${:.2f} | EV${:.3f}{}{} | T-{:.2f}h".format(
            row["dk_price_american"], row["dk_price_decimal"],
            row["kelly_stake"], go_stake,
            row.get("ev_dollars", 0), ci, shap_note, row["hours_to_start"],
        )
        print(line1 + line2)
        if row.get("narrative"):
            print(_c("dim", "       ↳ " + row["narrative"]))


# ── Main run_once ──────────────────────────────────────────────────────────────
def run_once(args: Args, api_key: str) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    if not args.no_fetch:
        manifest = fetch_universe(api_key, args)
        ok_count = sum(1 for x in manifest["sports"].values() if isinstance(x, dict) and x.get("ok"))
        print(_c("teal", f"\u2193 Fetched sports: ok={ok_count}/{manifest['sports_requested']}"))

    if not args.no_flowform:
        run_flowform_layer()

    catalog = build_market_catalog()
    print(_c("dim", f"  Market catalog: {len(catalog['global_markets'])} DK markets"))

    stack = detect_advanced_stack()
    print(_c("teal", f"  Premium stack: {stack.get('installed_count',0)}/{stack.get('total_checked',0)} modules"))

    # 1. Core rows
    rows = build_alpha_rows(args, stack)
    print(_c("gold", f"  Raw alpha rows: {len(rows)}"))

    # 2. Line movement
    movements = detect_line_movement(rows)
    for row in rows:
        mv = movements.get(row.get("alert_id", ""))
        if mv:
            row["line_moved"]       = True
            row["line_delta"]       = mv.get("delta", 0.0)
            row["sharp_money_signal"] = bool(mv.get("sharp_signal", False))

    # 3. scipy CI
    if _has(stack, "scipy", "numpy"):
        for row in rows:
            row.update(edge_confidence_interval(
                row["dk_price_decimal"], row["fair_price_decimal"], stack, n_bootstrap=500))

    # 4. sklearn
    rows, sklearn_ok = apply_sklearn_layer(rows, args, stack)

    # 5. ML ensemble (LightGBM + XGBoost + SHAP)
    rows, ml_report  = apply_ml_ensemble(rows, args, stack)

    # 6. PyPortfolioOpt
    rows, popt_ok    = apply_pypfopt(rows, args, stack)

    # 7. QuantStats
    qs_snap = quantstats_snapshot(rows, stack)

    # 8. VIX macro regime
    macro = fetch_macro_regime(stack, args)
    print(_c("dim", f"  Macro: VIX={macro.get('vix','?')} regime={macro.get('regime','?')} mult={macro.get('regime_mult','?')}"))

    # 9. Composite score v2
    rows = compute_alpha_v2(rows, macro, args)

    # 10. OpenAI narratives (non-blocking, last)
    generate_narratives(rows, args, stack)

    # Longshots
    longshots = [r for r in rows
                 if r["dk_price_decimal"] >= args.longshot_min_dk and r["edge_pct"] >= args.longshot_min_edge]

    # Write artifacts
    top_row = rows[0] if rows else {}
    write_json(ALPHA_BOARD_JSON, {
        "generated_utc": now_utc(), "regions": args.regions,
        "min_edge": args.min_edge, "horizon_hours": args.horizon_hours,
        "bankroll": args.bankroll, "kelly_fraction": args.kelly_frac, "max_bet": args.max_bet,
        "count": len(rows), "macro": macro, "quantstats": qs_snap,
        "line_movements": len(movements),
        "sharp_signals": sum(1 for r in rows if r.get("sharp_money_signal")),
        "ml_report": ml_report,
        "advanced_stack": {
            "installed_count": stack.get("installed_count"),
            "total_checked":   stack.get("total_checked"),
            "sklearn":  sklearn_ok, "pypfopt": popt_ok,
            "ml_lgbm":  bool(ml_report.get("lgbm")),
            "ml_xgb":   bool(ml_report.get("xgb")),
            "shap":     bool(ml_report.get("shap")),
        },
        "top_pick": {
            "pick": top_row.get("pick"), "game": top_row.get("game"),
            "edge_pct": top_row.get("edge_pct"), "alpha_score_v2": top_row.get("alpha_score_v2"),
            "ml_edge_score": top_row.get("ml_edge_score"),
        } if top_row else {},
        "rows": rows,
    })
    write_json(LONGSHOT_BOARD_JSON, {
        "generated_utc": now_utc(),
        "longshot_min_dk": args.longshot_min_dk, "longshot_min_edge": args.longshot_min_edge,
        "count": len(longshots), "rows": longshots,
    })
    write_json(ADVANCED_STACK_JSON, {
        **stack, "ml_report": ml_report, "quantstats": qs_snap,
        "alpha_rows": len(rows), "longshot_rows": len(longshots),
        "sharp_signals": sum(1 for r in rows if r.get("sharp_money_signal")),
    })
    write_csv(rows, ALPHA_BOARD_CSV)

    print(_c("gold", "  Stack features: ") +
          f"sklearn={sklearn_ok} lgbm={ml_report.get('lgbm',False)} "
          f"xgb={ml_report.get('xgb',False)} shap={ml_report.get('shap',False)} "
          f"pypfopt={popt_ok} qs.sharpe={qs_snap.get('sharpe','?')}")
    print_top_rows(rows,      "\u2550\u2550\u2550 Alpha Board (\u03b1-score v2, ML+consensus+regime)", args.top_n)
    print_top_rows(longshots, "\u2550\u2550\u2550 Longshot Board", min(args.top_n, len(longshots)) if longshots else 0)
    return rows, longshots


# ── Loop ──────────────────────────────────────────────────────────────────────
def run_loop(args: Args, api_key: str) -> int:
    iteration = 0
    while True:
        iteration += 1
        print(_c("teal", f"\n{'='*60}\n  Loop #{iteration} @ {now_utc()}\n{'='*60}"))
        rows, _ = run_once(args, api_key)
        state       = load_previous_state()
        prev_ids    = set(state.get("last_alert_ids", []))
        current_ids = {r["alert_id"] for r in rows
                       if r["edge_pct"] >= args.alert_min_edge and r["hours_to_start"] > 0}
        new_ids = current_ids - prev_ids
        if new_ids:
            new_rows = [r for r in rows if r["alert_id"] in new_ids]
            print(_c("red", f"\n  \u26a1 ALERT: {len(new_ids)} NEW alpha (edge \u2265 {args.alert_min_edge:.2f}%)"))
            print_top_rows(new_rows, "New Alpha Alerts", min(args.top_n, len(new_rows)))
        else:
            print(_c("dim", "\n  No new alerts above threshold."))
        save_state(list(current_ids))
        if args.iterations > 0 and iteration >= args.iterations:
            print("Loop completed."); return 0
        time.sleep(max(5, args.interval_sec))


# ── Argument parsing ──────────────────────────────────────────────────────────
def parse_args() -> Args:
    parser = argparse.ArgumentParser(
        description="DraftKings +EV Alpha Autopilot — Institutional Maximum Build",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument("--regions",            default="us,uk,eu")
    parser.add_argument("--sports",             default="all")
    parser.add_argument("--min-edge",           type=float, default=1.0)
    parser.add_argument("--horizon-hours",      type=float, default=72.0)
    parser.add_argument("--bankroll",           type=float, default=150.0)
    parser.add_argument("--kelly-frac",         type=float, default=0.25)
    parser.add_argument("--max-bet",            type=float, default=25.0)
    parser.add_argument("--top-n",              type=int,   default=15)
    parser.add_argument("--longshot-min-dk",    type=float, default=4.0)
    parser.add_argument("--longshot-min-edge",  type=float, default=2.0)
    parser.add_argument("--no-fetch",           action="store_true")
    parser.add_argument("--no-flowform",        action="store_true")
    parser.add_argument("--no-ml",              action="store_true")
    parser.add_argument("--no-openai",          action="store_true")
    parser.add_argument("--no-macro",           action="store_true")
    parser.add_argument("--loop",               action="store_true")
    parser.add_argument("--interval-sec",       type=int,   default=300)
    parser.add_argument("--iterations",         type=int,   default=0)
    parser.add_argument("--alert-min-edge",     type=float, default=5.0)
    parser.add_argument("--openai-model",       default="gpt-4o-mini")
    ns = parser.parse_args()
    return Args(
        regions=ns.regions, sports=ns.sports, min_edge=ns.min_edge,
        horizon_hours=ns.horizon_hours, bankroll=ns.bankroll,
        kelly_frac=ns.kelly_frac, max_bet=ns.max_bet, top_n=ns.top_n,
        longshot_min_dk=ns.longshot_min_dk, longshot_min_edge=ns.longshot_min_edge,
        no_fetch=ns.no_fetch, no_flowform=ns.no_flowform, no_ml=ns.no_ml,
        no_openai=ns.no_openai, no_macro=ns.no_macro,
        loop=ns.loop, interval_sec=ns.interval_sec, iterations=ns.iterations,
        alert_min_edge=ns.alert_min_edge, openai_model=ns.openai_model,
    )


# ── Entry point ───────────────────────────────────────────────────────────────
def main() -> int:
    _colorama_init()
    maybe_reexec_to_richer_env()
    load_env_file()
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    args    = parse_args()
    api_key = get_api_key()
    if not api_key and not args.no_fetch:
        print(_c("red", "ERROR: Missing odds API key (THEODDS_API_KEY / ODDS_API_KEY / SPORTS_ODDS_API_KEY)."))
        return 2
    if args.loop:
        return run_loop(args, api_key)
    run_once(args, api_key)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
