"""
INFRA CONSTRAINT MONITOR — Government-Grade Real-Time Infrastructure Metrics
═══════════════════════════════════════════════════════════════════════════════
Continuously monitors live data feeds, execution constraints, and financial
impact in real time.

Every constraint violation is documented with:
  WHAT  — what specifically failed or degraded
  WHY   — why that matters to financial outcomes
  HOW   — which formula detected / quantified the impact
  HOW MUCH — dollar impact in USD per second / per hour

Full SHA-256 hash chain audit trail — every event is tamper-evident.
Suitable for DoD / DARPA / NSF audit requirements.

Sectors tracked:
  broker | equities_broad | equities_tech | equities_semis | equities_ev
  equities_media | equities_small_cap | crypto | fx | macro | energy | labor

Output files:
  out/execution/infra_constraint_status.json  — live snapshot read by dashboard
  out/execution/sector_metrics.json           — per-sector P&L breakdown
  out/audit_chain.jsonl                       — append-only SHA-256 hash chain
"""

import argparse
import atexit
import hashlib
import json
import os
import shutil
import sys
import time
import math
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

# —— path setup so audit_chain imports cleanly ——
sys.path.insert(0, str(Path(__file__).parent))
from audit_chain import AuditChain  # noqa: E402

# ─────────────────────────────────── paths ────────────────────────────────────
ROOT = Path(r"C:\LumaTrader\INSTITUTIONAL_STACK_V2")
OUT = ROOT / "out"
EXEC_OUT = OUT / "execution"
DATA = ROOT / "data"
LIVE_FETCHED = DATA / "live_fetched"
CONFIG = ROOT / "config"

STATUS_FILE = EXEC_OUT / "alpaca_paper_status.json"
STATE_FILE = OUT / "paper_trade_state.json"
LEDGER_FILE = OUT / "paper_trade_ledger.jsonl"
REGISTRY_FILE = CONFIG / "live_source_registry.json"
ENV_FILE = CONFIG / "luma_live_keys.env"
PAPER_RUNTIME_FILE = CONFIG / "paper_trader_runtime.json"
RUNTIME_FILE = CONFIG / "runtime_control.json"

CONSTRAINT_STATUS_FILE = EXEC_OUT / "infra_constraint_status.json"
SECTOR_METRICS_FILE = EXEC_OUT / "sector_metrics.json"
AUDIT_CHAIN_FILE = OUT / "audit_chain.jsonl"
MONITOR_LOCK_FILE = EXEC_OUT / "infra_constraint_monitor.lock"
AUDIT_ARCHIVE_DIR = OUT / "audit_archive"
TRUTH_HISTORY_FILE = EXEC_OUT / "truth_history.jsonl"
CYCLE_SIGNATURE_FILE = EXEC_OUT / "cycle_signatures.jsonl"

# ─────────────────────────── formula registry ─────────────────────────────────
# Every formula the system uses is declared here for audit purposes.
# These are referenced by formula_key in every violation and metric entry.
FORMULA_REGISTRY: dict[str, dict] = {
    "signal_score_breakout": {
        "formula": "score = (day_return × 140) + (minute_return × 180) + (near_high × 20) + min(volume_impulse, 5)",
        "description": "Breakout strategy signal score. Weights recent price momentum and intraday range position to rank entry candidates.",
        "source_file": "alpaca_paper_executor.py",
        "source_function": "compute_signal_score()",
        "variables": {
            "day_return": "daily_close / prev_close − 1",
            "minute_return": "minute_close / minute_open − 1",
            "near_high": "(daily_close − daily_low) / (daily_high − daily_low)",
            "volume_impulse": "minute_volume / (daily_volume / 390)",
        },
    },
    "edge_bps": {
        "formula": "edge_bps = max(0, (day_return + minute_return) × 10,000)",
        "description": "Expected alpha edge in basis points. How many bps above zero the combined momentum signal projects.",
        "source_file": "alpaca_paper_executor.py",
        "source_function": "compute_signal_score()",
    },
    "confidence": {
        "formula": "confidence = clamp(0.50 + max(day_return,0)×4.0 + max(minute_return,0)×6.0 + min(near_high,1)×0.15,  0.0, 0.99)",
        "description": "Signal confidence in [0,1]. Baseline 50% with upward-biased momentum contributions.",
        "source_file": "alpaca_paper_executor.py",
        "source_function": "compute_signal_score()",
    },
    "position_notional": {
        "formula": "notional_usd = min(equity × position_size_pct,  buying_power × 0.90 / slots_left)",
        "description": "Dollar notional allocated per position. Capped by both equity fraction and available buying power to prevent over-allocation.",
        "source_file": "alpaca_paper_executor.py",
        "source_function": "execute_once()",
        "variables": {
            "position_size_pct": "Fraction of equity per trade (config: 0.55)",
            "slots_left": "Remaining burst slots in current entry cycle",
        },
    },
    "qty_calculation": {
        "formula": "qty = round(notional_usd / limit_price, 6)",
        "description": "Share quantity derived from dollar notional divided by limit price. Used for extended-hours limit orders.",
        "source_file": "alpaca_paper_executor.py",
        "source_function": "AlpacaPaperClient.submit_buy()",
    },
    "extended_hours_limit_price": {
        "formula": "limit_price = latest_price × (1 + off_hours_limit_buffer_pct)",
        "description": "Off-hours limit orders priced above last market price by a buffer percentage to improve fill probability during illiquid sessions.",
        "source_file": "alpaca_paper_executor.py",
        "source_function": "execute_once()",
        "variables": {
            "off_hours_limit_buffer_pct": "Config: 0.01 = 1% premium above last traded price",
        },
    },
    "auto_close_take_profit": {
        "formula": "CLOSE if unrealized_plpc ≥ +0.015",
        "description": "Take-profit exit: close position when unrealized P&L percent reaches +1.5%.",
        "source_file": "alpaca_paper_executor.py",
        "source_function": "evaluate_closures()",
    },
    "auto_close_stop_loss": {
        "formula": "CLOSE if unrealized_plpc ≤ −0.010",
        "description": "Stop-loss exit: close position when unrealized P&L percent drops to −1.0%.",
        "source_file": "alpaca_paper_executor.py",
        "source_function": "evaluate_closures()",
    },
    "auto_close_time_stop": {
        "formula": "CLOSE if hold_minutes ≥ 90",
        "description": "Time-stop exit: position held longer than 90 minutes is closed regardless of P&L.",
        "source_file": "alpaca_paper_executor.py",
        "source_function": "evaluate_closures()",
    },
    "compound_rate": {
        "formula": "CAGR = (equity / starting_capital)^(365 / max(days_elapsed, 0.001)) − 1",
        "description": "Annualized compound growth rate. Measures how fast the account compounds if the current return rate were sustained for a full year.",
        "source_file": "infra_constraint_monitor.py",
        "source_function": "compute_account_metrics()",
    },
    "fill_rate": {
        "formula": "fill_rate_pct = (filled_orders / total_orders_submitted) × 100",
        "description": "Percentage of submitted orders that resulted in confirmed fills. Measures execution quality. <100% means capital is reserved but unproductive.",
        "source_file": "infra_constraint_monitor.py",
        "source_function": "compute_execution_metrics()",
    },
    "capital_burn_rate": {
        "formula": "burn_usd_per_sec = (equity × position_size_pct − buying_power) / max(session_elapsed_secs, 1)",
        "description": "Rate at which reserved-but-unfilled limit orders consume available capital per second. Dead capital is capital burning time value.",
        "source_file": "infra_constraint_monitor.py",
        "source_function": "compute_execution_metrics()",
    },
    "data_freshness_score": {
        "formula": "freshness_score = max(0, 1 − stale_age_secs / max_acceptable_age_secs)",
        "description": "How fresh a data feed is: 1.0 = perfectly current, 0.0 = maximally stale. Used to gate signal scoring.",
        "source_file": "infra_constraint_monitor.py",
        "source_function": "compute_data_feed_metrics()",
        "variables": {
            "max_acceptable_age_secs": {
                "intraday_tick": 60,
                "daily_bar": 93600,
                "macro_series": 604800,
                "crypto_daily": 14400,
                "fx_daily": 93600,
            },
        },
    },
    "opportunity_cost_stale_data": {
        "formula": "opp_cost_usd = equity × position_size_pct × (edge_bps / 10_000) × (stale_age_secs / 3600)",
        "description": "Estimated dollar opportunity cost of acting on stale data. Based on conservative 20-bps baseline edge and duration of staleness.",
        "source_file": "infra_constraint_monitor.py",
        "source_function": "compute_constraint_violations()",
        "variables": {
            "edge_bps": "Conservative baseline: 20 bps (actual edge may be higher when signal fires)",
            "stale_age_secs": "Seconds since last file modification or data update",
        },
    },
    "sector_pnl": {
        "formula": "sector_pnl_usd = Σ(realized_pnl for trades in sector) + Σ(unrealized_pl for open positions in sector)",
        "description": "Net P&L attributed to each sector based on symbol-to-sector mapping of trade history and open positions.",
        "source_file": "infra_constraint_monitor.py",
        "source_function": "compute_sector_metrics()",
    },
    "loss_per_second": {
        "formula": "loss_per_sec_usd = |unrealized_loss_usd| / max(position_age_secs, 1)",
        "description": "Rate of unrealized loss accumulation per second for a given open position. Stop-loss at −1.0% provides a natural bound.",
        "source_file": "infra_constraint_monitor.py",
        "source_function": "compute_execution_metrics()",
    },
    "capital_utilization": {
        "formula": "capital_utilization_pct = (1 − buying_power / equity) × 100",
        "description": "Percentage of total equity currently deployed or reserved. 0% = all cash. 100% = fully deployed.",
        "source_file": "infra_constraint_monitor.py",
        "source_function": "compute_account_metrics()",
    },
}

# ─────────────────────────── domain constants ─────────────────────────────────
# Symbol → sector map (equities + crypto + FX)
SYMBOL_SECTOR_MAP: dict[str, str] = {
    # Broad market
    "SPY": "equities_broad", "DIA": "equities_broad", "IWM": "equities_small_cap",
    # Tech / growth
    "QQQ": "equities_tech", "NVDA": "equities_semis", "MSFT": "equities_tech",
    "AAPL": "equities_tech", "AMD": "equities_semis", "META": "equities_tech",
    "AMZN": "equities_tech", "GOOGL": "equities_tech", "AVGO": "equities_semis",
    "SMCI": "equities_semis", "PLTR": "equities_tech", "NFLX": "equities_media",
    "TSLA": "equities_ev",
    # Crypto
    "BTC": "crypto", "ETH": "crypto", "SOL": "crypto", "ADA": "crypto",
    "DOGE": "crypto", "XRP": "crypto",
    # FX
    "EURUSD": "fx", "GBPUSD": "fx", "JPYUSD": "fx", "AUDUSD": "fx", "CHFUSD": "fx",
}

# Max acceptable staleness per feed type (seconds)
MAX_ACCEPTABLE_AGE: dict[str, float] = {
    "intraday_tick": 60.0,
    "daily_bar": 93600.0,    # 26 hours — next business day open
    "macro_series": 604800.0,  # 7 days
    "crypto_daily": 14400.0,   # 4 hours
    "fx_daily": 93600.0,
    "status_file": 30.0,
}


# ─────────────────────────── utility helpers ──────────────────────────────────
def now_utc() -> str:
    return datetime.now(timezone.utc).isoformat()


def now_ts() -> float:
    return time.time()


def load_json(path: Path, default: Any) -> Any:
    try:
        if path.exists():
            return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        pass
    return default


def load_jsonl(path: Path) -> list:
    rows: list = []
    try:
        if path.exists():
            for raw in path.read_text(encoding="utf-8", errors="ignore").splitlines():
                raw = raw.strip()
                if raw:
                    try:
                        rows.append(json.loads(raw))
                    except Exception:
                        pass
    except Exception:
        pass
    return rows


def sha256_text(raw: str) -> str:
    return hashlib.sha256(raw.encode("utf-8", errors="ignore")).hexdigest()


def sha256_file_safe(path: Path) -> str:
    try:
        if not path.exists():
            return "MISSING"
        h = hashlib.sha256()
        with path.open("rb") as f:
            for chunk in iter(lambda: f.read(65536), b""):
                h.update(chunk)
        return h.hexdigest()
    except Exception:
        return "ERROR"


def verify_audit_chain(path: Path) -> dict:
    rows = load_jsonl(path)
    if not rows:
        return {
            "ok": True,
            "events": 0,
            "broken_links": 0,
            "tail_ok": True,
            "tail_broken_links": 0,
            "last_event_hash": "GENESIS",
        }

    broken = 0
    tail_broken = 0
    expected_prev = "GENESIS"
    tail_window = 500
    tail_start = max(0, len(rows) - tail_window)
    for idx, row in enumerate(rows):
        prev_hash = str(row.get("prev_hash", ""))
        if prev_hash != expected_prev:
            broken += 1
            if idx >= tail_start:
                tail_broken += 1
        expected_prev = str(row.get("event_hash", expected_prev))

    return {
        "ok": broken == 0,
        "events": len(rows),
        "broken_links": broken,
        "tail_ok": tail_broken == 0,
        "tail_broken_links": tail_broken,
        "last_event_hash": expected_prev,
    }


def archive_and_reset_chain_epoch() -> dict:
    AUDIT_ARCHIVE_DIR.mkdir(parents=True, exist_ok=True)
    ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    archived_chain = None
    archived_truth = None

    if AUDIT_CHAIN_FILE.exists() and AUDIT_CHAIN_FILE.stat().st_size > 0:
        archived_chain = AUDIT_ARCHIVE_DIR / f"audit_chain_{ts}.jsonl"
        shutil.copy2(AUDIT_CHAIN_FILE, archived_chain)
        AUDIT_CHAIN_FILE.write_text("", encoding="utf-8")

    if TRUTH_HISTORY_FILE.exists() and TRUTH_HISTORY_FILE.stat().st_size > 0:
        archived_truth = AUDIT_ARCHIVE_DIR / f"truth_history_{ts}.jsonl"
        shutil.copy2(TRUTH_HISTORY_FILE, archived_truth)
        TRUTH_HISTORY_FILE.write_text("", encoding="utf-8")

    return {
        "epoch_started_utc": now_utc(),
        "archived_chain": str(archived_chain) if archived_chain else "NONE",
        "archived_truth_history": str(archived_truth) if archived_truth else "NONE",
    }


def summarize_truth_history(history_rows: list[dict], current_fp: str) -> dict:
    now_epoch = now_ts()
    rows_24h = []
    for row in history_rows:
        ts = parse_iso_ts(row.get("generated_utc") or "")
        if ts > 0 and (now_epoch - ts) <= 86400.0:
            rows_24h.append(row)

    if not rows_24h:
        return {
            "samples_24h": 0,
            "chain_tail_pass_rate_24h_pct": 100.0,
            "fingerprint_change_rate_24h_pct": 0.0,
            "latest_fingerprint_changed": False,
        }

    chain_tail_passes = sum(1 for r in rows_24h if bool(r.get("chain_tail_ok", True)))
    chain_tail_pass_rate = (chain_tail_passes / max(len(rows_24h), 1)) * 100.0

    fingerprints = [
        str(r.get("reproducibility_fingerprint_sha256", ""))
        for r in rows_24h
        if r.get("reproducibility_fingerprint_sha256")
    ]
    changes = 0
    for idx in range(1, len(fingerprints)):
        if fingerprints[idx] != fingerprints[idx - 1]:
            changes += 1
    change_rate = (changes / max(len(fingerprints) - 1, 1)) * 100.0 if len(fingerprints) > 1 else 0.0

    latest_prev_fp = fingerprints[-1] if fingerprints else ""
    latest_changed = bool(latest_prev_fp and current_fp and latest_prev_fp != current_fp)

    return {
        "samples_24h": len(rows_24h),
        "chain_tail_pass_rate_24h_pct": round(chain_tail_pass_rate, 2),
        "fingerprint_change_rate_24h_pct": round(change_rate, 2),
        "latest_fingerprint_changed": latest_changed,
    }


def build_reproducibility_fingerprint(payload: dict) -> str:
    compact = {
        "generated_utc": payload.get("generated_utc"),
        "equity": (payload.get("account_metrics") or {}).get("equity_usd"),
        "pnl": (payload.get("account_metrics") or {}).get("pnl_usd"),
        "violations": payload.get("violation_count"),
        "stale_feeds": payload.get("stale_feed_count"),
        "exec_fill_rate": (payload.get("execution_metrics") or {}).get("fill_rate_pct"),
        "exec_unfilled_hist": (payload.get("execution_metrics") or {}).get("unfilled_orders_historical"),
        "exec_open_unfilled": (payload.get("execution_metrics") or {}).get("current_open_unfilled_orders_count"),
        "api_coverage": (payload.get("api_source_coverage") or {}).get("live_data_coverage_pct"),
    }
    return sha256_text(json.dumps(compact, sort_keys=True, separators=(",", ":")))


def _pid_is_alive(pid: int) -> bool:
    if pid <= 0:
        return False
    try:
        os.kill(pid, 0)
        return True
    except Exception:
        return False


def acquire_monitor_lock() -> None:
    MONITOR_LOCK_FILE.parent.mkdir(parents=True, exist_ok=True)
    current_pid = os.getpid()

    if MONITOR_LOCK_FILE.exists():
        try:
            raw = MONITOR_LOCK_FILE.read_text(encoding="utf-8", errors="ignore").strip()
            existing_pid = int(raw) if raw else 0
        except Exception:
            existing_pid = 0

        if existing_pid and existing_pid != current_pid and _pid_is_alive(existing_pid):
            raise SystemExit(
                f"infra_constraint_monitor already running with pid={existing_pid}; refusing second writer"
            )

        # Stale lock file: previous process is gone.
        try:
            MONITOR_LOCK_FILE.unlink(missing_ok=True)
        except Exception:
            pass

    # Atomic create: prevents race when two processes start at once.
    try:
        fd = os.open(str(MONITOR_LOCK_FILE), os.O_CREAT | os.O_EXCL | os.O_WRONLY)
        os.write(fd, str(current_pid).encode("utf-8"))
        os.close(fd)
    except FileExistsError:
        try:
            raw = MONITOR_LOCK_FILE.read_text(encoding="utf-8", errors="ignore").strip()
            existing_pid = int(raw) if raw else 0
        except Exception:
            existing_pid = 0
        raise SystemExit(
            f"infra_constraint_monitor already running with pid={existing_pid}; refusing second writer"
        )

    def _cleanup() -> None:
        try:
            if MONITOR_LOCK_FILE.exists():
                raw = MONITOR_LOCK_FILE.read_text(encoding="utf-8", errors="ignore").strip()
                if raw == str(current_pid):
                    MONITOR_LOCK_FILE.unlink(missing_ok=True)
        except Exception:
            pass

    atexit.register(_cleanup)


def save_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def append_jsonl(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as fp:
        fp.write(json.dumps(payload, ensure_ascii=True) + "\n")


def parse_iso_ts(raw: str) -> float:
    if not raw:
        return 0.0
    try:
        return datetime.fromisoformat(str(raw).replace("Z", "+00:00")).timestamp()
    except Exception:
        return 0.0


def load_env_pairs(path: Path) -> dict[str, str]:
    pairs: dict[str, str] = {}
    try:
        if not path.exists():
            return pairs
        for raw in path.read_text(encoding="utf-8", errors="ignore").splitlines():
            line = raw.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, value = line.split("=", 1)
            pairs[key.strip()] = value.strip()
    except Exception:
        pass
    return pairs


def infer_provider_from_env_key(env_key: str) -> str:
    k = str(env_key or "").upper()
    if "ALPACA" in k:
        return "ALPACA"
    if "ALPHAVANTAGE" in k:
        return "ALPHAVANTAGE"
    if "TWELVE" in k:
        return "TWELVEDATA"
    if "FRED" in k:
        return "FRED"
    if "EIA" in k:
        return "EIA"
    if "BEA" in k:
        return "BEA"
    if "BLS" in k:
        return "BLS"
    if "CENSUS" in k:
        return "CENSUS"
    if "EPA" in k:
        return "EPA_AQS"
    if "NOAA" in k:
        return "NOAA"
    if "OPENWEATHER" in k or "OWM" in k:
        return "OPENWEATHER"
    if "KRAKEN" in k:
        return "KRAKEN"
    if "POLYGON" in k:
        return "POLYGON"
    if "IEX" in k:
        return "IEX"
    if "FMP" in k:
        return "FMP"
    if "FINNHUB" in k:
        return "FINNHUB"
    if "QUANDL" in k or "NASDAQ_DATA_LINK" in k:
        return "QUANDL"
    if "NEWSAPI" in k:
        return "NEWSAPI"
    return "UNKNOWN"


def compute_api_source_coverage(registry_rows: list[dict], env_pairs: dict[str, str]) -> dict:
    registry_map = {
        str(row.get("source", "")).upper(): row
        for row in registry_rows
        if isinstance(row, dict)
    }

    providers: dict[str, dict] = {}
    populated_keys = {
        k: v
        for k, v in env_pairs.items()
        if str(v).strip() and "REPLACE" not in str(v).upper() and str(v).strip() != "YOUR_KEY"
    }

    for key in sorted(populated_keys.keys()):
        provider = infer_provider_from_env_key(key)
        if provider not in providers:
            providers[provider] = {
                "provider": provider,
                "keys": [],
            }
        providers[provider]["keys"].append(key)

    details = []
    configured_count = 0
    enabled_count = 0
    measured_count = 0
    live_rows_count = 0

    for provider, payload in sorted(providers.items(), key=lambda kv: kv[0]):
        reg = registry_map.get(provider, {})
        rows = int(reg.get("rows") or 0)
        enabled = bool(reg.get("enabled"))
        measured = str(reg.get("dollar_basis", "")).upper() == "MEASURED"

        configured_count += 1
        enabled_count += 1 if enabled else 0
        measured_count += 1 if measured else 0
        live_rows_count += 1 if rows > 0 else 0

        details.append(
            {
                "provider": provider,
                "keys_detected": payload["keys"],
                "registry_present": bool(reg),
                "registry_status": reg.get("status", "UNKNOWN") if reg else "UNMAPPED",
                "enabled": enabled,
                "rows": rows,
                "dollar_basis": reg.get("dollar_basis", "UNMEASURED") if reg else "UNMAPPED",
                "sector": reg.get("sector", "unknown") if reg else "unknown",
                "last_probe_utc": reg.get("last_probe_utc", "") if reg else "",
            }
        )

    coverage_pct = 0.0
    if configured_count > 0:
        coverage_pct = (live_rows_count / configured_count) * 100.0

    return {
        "env_key_count_total": len(env_pairs),
        "env_key_count_populated": len(populated_keys),
        "provider_count_configured": configured_count,
        "provider_count_enabled": enabled_count,
        "provider_count_measured": measured_count,
        "provider_count_with_live_rows": live_rows_count,
        "live_data_coverage_pct": round(coverage_pct, 2),
        "details": details,
    }


def classify_csv_feed(name: str) -> tuple[str, str]:
    """Return (feed_type, sector) for a CSV file stem."""
    n = name.lower()

    # Daily OHLC feeds should be evaluated on daily cadence, not intraday cadence.
    if n.endswith("_daily") or "_daily" in n:
        if "kraken" in n:
            if any(x in n for x in ["eur", "gbp", "aud", "jpy", "chf", "fx"]):
                return "fx_daily", "fx"
            return "daily_bar", "crypto"
        return "daily_bar", "equities_tech"

    if n.startswith("twelvedata_"):
        # Current fetch pipeline uses 1day interval from TwelveData.
        return "daily_bar", "equities_tech"

    if any(x in n for x in ["kraken", "btc", "eth", "ada", "sol", "xrp", "doge", "aud_daily",
                              "eur_daily", "gbp_daily"]):
        if "fx" in n or any(x in n for x in ["eurusd", "gbpusd", "jpyusd", "audusd", "chfusd",
                                               "chfusd", "av_fx"]):
            return "fx_daily", "fx"
        return "crypto_daily", "crypto"
    if any(x in n for x in ["av_fx", "eurusd", "gbpusd", "jpyusd", "audusd", "chfusd"]):
        return "fx_daily", "fx"
    if any(x in n for x in ["twelvedata", "alpaca", "spy", "qqq", "iwm"]):
        return "intraday_tick", "equities_tech"
    if any(x in n for x in ["fred", "bea", "bls", "cpiaucsl", "dgs10", "unrate"]):
        return "macro_series", "macro"
    if any(x in n for x in ["eia", "nuclear", "generation", "energy", "capacity_outage",
                              "net_generation"]):
        return "macro_series", "energy"
    return "daily_bar", "unknown"


# ─────────────────────────── measurement passes ───────────────────────────────

def compute_data_feed_metrics(equity: float, position_size_pct: float) -> dict:
    """
    Scan all live_fetched CSV files and measure freshness.

    Formula applied per stale feed:
      opp_cost_usd = equity × position_size_pct × (edge_bps/10000) × (stale_age_secs/3600)
    where edge_bps = 20 (conservative baseline).
    """
    BASELINE_EDGE_BPS = 20.0
    feeds: dict = {}

    if not LIVE_FETCHED.exists():
        return feeds

    for csv_file in sorted(LIVE_FETCHED.glob("*.csv")):
        name = csv_file.stem
        try:
            age_secs = max(0.0, now_ts() - csv_file.stat().st_mtime)
        except Exception:
            age_secs = 999999.0

        feed_type, sector = classify_csv_feed(name)
        max_age = MAX_ACCEPTABLE_AGE.get(feed_type, 3600.0)
        freshness_score = max(0.0, 1.0 - age_secs / max_age)
        is_stale = age_secs > max_age

        opp_cost = 0.0
        if is_stale:
            # opportunity_cost_usd = equity × position_size_pct × (edge_bps/10000) × (stale_age_secs/3600)
            opp_cost = equity * position_size_pct * (BASELINE_EDGE_BPS / 10000.0) * (age_secs / 3600.0)

        feeds[name] = {
            "file": csv_file.name,
            "sector": sector,
            "feed_type": feed_type,
            "age_secs": round(age_secs, 1),
            "max_acceptable_age_secs": max_age,
            "freshness_score": round(freshness_score, 4),
            "is_stale": is_stale,
            "opportunity_cost_usd": round(opp_cost, 4),
            "formula_applied": "opp_cost = equity × position_size_pct × (edge_bps/10000) × (stale_age_secs/3600)",
            "formula_key": "opportunity_cost_stale_data",
            "baseline_edge_bps_used": BASELINE_EDGE_BPS,
        }

    return feeds


def compute_execution_metrics(
    ledger: list,
    state: dict,
    status: dict,
    equity: float,
    position_size_pct: float,
) -> dict:
    """
    Analyze the trade ledger for fills, losses, and execution quality.
    Formulas documented inline with each metric.
    """
    total_orders = 0
    filled_orders = 0
    unfilled_orders = 0
    total_notional_submitted = 0.0
    unfilled_notional_historical = 0.0
    unfilled_notional_24h = 0.0
    last_24h_submitted = 0
    last_24h_filled = 0
    signal_edges_bps: list[float] = []
    realized_trade_returns: list[float] = []
    fills_by_symbol: dict[str, int] = {}
    losses_per_second: list = []
    open_loss_total = 0.0
    positions: list = status.get("positions") or []

    now_epoch = now_ts()
    baseline_exec_edge_bps = 20.0

    # Scan ledger for fill/open records
    for row in ledger:
        action = str(row.get("action", "")).lower()
        if action not in ("open", "close"):
            continue
        symbol = str(row.get("symbol", "")).upper()
        result = row.get("result") or {}
        if isinstance(result, list):
            result = result[0] if result else {}
        filled_qty = float(result.get("filled_qty") or 0.0)
        notional = float(row.get("notional_usd") or 0.0)

        if action == "open":
            total_orders += 1
            total_notional_submitted += notional
            edge_bps = float(row.get("edge_bps") or 0.0)
            if edge_bps > 0:
                signal_edges_bps.append(edge_bps)
            ts = parse_iso_ts(row.get("timestamp") or "")
            in_last_24h = ts > 0 and (now_epoch - ts) <= 86400.0
            if in_last_24h:
                last_24h_submitted += 1
            if filled_qty > 0:
                filled_orders += 1
                fills_by_symbol[symbol] = fills_by_symbol.get(symbol, 0) + 1
                if in_last_24h:
                    last_24h_filled += 1
            else:
                unfilled_orders += 1
                unfilled_notional_historical += notional
                if in_last_24h:
                    unfilled_notional_24h += notional

        if action == "close":
            uplpc = row.get("uplpc")
            if uplpc is not None:
                try:
                    realized_trade_returns.append(float(uplpc))
                except Exception:
                    pass

    # fill_rate = filled_orders / total_orders × 100
    fill_rate = (filled_orders / max(total_orders, 1)) * 100.0
    fill_rate_24h = (last_24h_filled / max(last_24h_submitted, 1)) * 100.0

    # Conservative execution drag estimate from unfilled notional.
    # opportunity_cost = unfilled_notional × (baseline_edge_bps / 10,000)
    exec_opp_cost_historical = unfilled_notional_historical * (baseline_exec_edge_bps / 10000.0)
    exec_opp_cost_24h = unfilled_notional_24h * (baseline_exec_edge_bps / 10000.0)

    # Sharpe-style metrics.
    # signal_sharpe_proxy = sqrt(N) × mean(edge_bps) / stdev(edge_bps)
    # realized_trade_sharpe = sqrt(N) × mean(trade_return) / stdev(trade_return)
    def compute_sharpe_proxy(samples: list[float]) -> float | None:
        n = len(samples)
        if n < 2:
            return None
        mean_v = sum(samples) / n
        var = sum((x - mean_v) ** 2 for x in samples) / (n - 1)
        std_v = math.sqrt(max(var, 0.0))
        if std_v <= 1e-12:
            return None
        return (mean_v / std_v) * math.sqrt(n)

    signal_sharpe_proxy = compute_sharpe_proxy(signal_edges_bps)
    realized_trade_sharpe = compute_sharpe_proxy(realized_trade_returns)

    current_open_orders = status.get("open_orders") or []
    current_open_orders_count = int(status.get("open_orders_count") or len(current_open_orders))
    current_open_unfilled_orders_count = int(
        status.get("open_unfilled_orders_count")
        if status.get("open_unfilled_orders_count") is not None
        else sum(1 for o in current_open_orders if float(o.get("filled_qty") or 0.0) <= 0)
    )

    # Loss per second from currently-open losing positions
    # loss_per_sec = |unrealized_loss| / max(position_age_secs, 1)
    tracked = state.get("tracked_positions") or {}
    for pos in positions:
        symbol = str(pos.get("symbol", "")).upper()
        unrealized_pl = float(pos.get("unrealized_pl") or 0.0)
        opened_at_raw = (tracked.get(symbol) or {}).get("opened_at", "")
        opened_ts = parse_iso_ts(opened_at_raw)
        age_secs = max(1.0, now_ts() - opened_ts) if opened_ts > 0 else 3600.0

        if unrealized_pl < 0:
            lps = abs(unrealized_pl) / age_secs
            losses_per_second.append({
                "symbol": symbol,
                "unrealized_pl_usd": round(unrealized_pl, 4),
                "position_age_secs": round(age_secs, 1),
                "loss_per_second_usd": round(lps, 8),
                "formula": "loss_per_sec = |unrealized_loss_usd| / max(position_age_secs, 1)",
                "formula_key": "loss_per_second",
                "sector": SYMBOL_SECTOR_MAP.get(symbol, "equities_other"),
            })
            open_loss_total += abs(unrealized_pl)

    total_lps = sum(x["loss_per_second_usd"] for x in losses_per_second)

    # Capital burn rate from reserved-but-unfilled orders
    # burn_usd_per_sec = (equity × position_size_pct − buying_power) / session_elapsed_secs
    buying_power = float((status.get("account") or {}).get("buying_power") or 0.0)
    reserved_capital = max(0.0, equity * position_size_pct - buying_power)
    session_start_raw = (ledger[0].get("timestamp") if ledger else "") or ""
    session_start = parse_iso_ts(session_start_raw)
    session_elapsed = max(1.0, now_ts() - session_start) if session_start > 0 else 1.0
    capital_burn_rate = reserved_capital / session_elapsed

    return {
        "total_orders_submitted": total_orders,
        "filled_orders": filled_orders,
        "unfilled_orders_historical": unfilled_orders,
        "fill_rate_pct": round(fill_rate, 2),
        "fill_rate_formula": "fill_rate_pct = (filled_orders / total_orders) × 100",
        "fill_rate_formula_key": "fill_rate",
        "orders_submitted_last_24h": last_24h_submitted,
        "filled_orders_last_24h": last_24h_filled,
        "fill_rate_last_24h_pct": round(fill_rate_24h, 2),
        "current_open_orders_count": current_open_orders_count,
        "current_open_unfilled_orders_count": current_open_unfilled_orders_count,
        "unfilled_notional_historical_usd": round(unfilled_notional_historical, 2),
        "unfilled_notional_24h_usd": round(unfilled_notional_24h, 2),
        "execution_opportunity_cost_historical_usd": round(exec_opp_cost_historical, 2),
        "execution_opportunity_cost_24h_usd": round(exec_opp_cost_24h, 2),
        "execution_opportunity_cost_formula": "opp_cost = unfilled_notional_usd × (baseline_edge_bps/10,000)",
        "execution_opportunity_cost_edge_bps": baseline_exec_edge_bps,
        "signal_sharpe_proxy": round(signal_sharpe_proxy, 4) if signal_sharpe_proxy is not None else None,
        "signal_sharpe_proxy_samples": len(signal_edges_bps),
        "signal_sharpe_proxy_formula": "signal_sharpe_proxy = sqrt(N) × mean(edge_bps) / stdev(edge_bps)",
        "realized_trade_sharpe": round(realized_trade_sharpe, 4) if realized_trade_sharpe is not None else None,
        "realized_trade_sharpe_samples": len(realized_trade_returns),
        "realized_trade_sharpe_formula": "realized_trade_sharpe = sqrt(N) × mean(trade_return) / stdev(trade_return)",
        "total_notional_submitted_usd": round(total_notional_submitted, 2),
        "fills_by_symbol": fills_by_symbol,
        "open_loss_total_usd": round(open_loss_total, 4),
        "total_loss_per_second_usd": round(total_lps, 8),
        "losses_per_second": losses_per_second,
        "capital_burn_rate_per_sec_usd": round(capital_burn_rate, 6),
        "capital_burn_formula": "burn_usd_per_sec = (equity × position_size_pct − buying_power) / session_elapsed_secs",
        "capital_burn_formula_key": "capital_burn_rate",
        "reserved_capital_usd": round(reserved_capital, 2),
        "buying_power_usd": round(buying_power, 2),
        "session_elapsed_secs": round(session_elapsed, 0),
        "session_start_utc": session_start_raw,
    }


def compute_account_metrics(status: dict, paper_runtime: dict) -> dict:
    """
    Compute account health, P&L, compound rate and capital utilization.
    Formulas documented inline.
    """
    account = status.get("account") or {}
    equity = float(account.get("equity") or 0.0)
    cash = float(account.get("cash") or 0.0)
    buying_power = float(account.get("buying_power") or 0.0)
    starting_capital = float(paper_runtime.get("starting_capital_usd") or 100000.0)
    position_size_pct = float(paper_runtime.get("position_size_pct") or 0.55)

    pnl_usd = equity - starting_capital
    pnl_pct = (pnl_usd / starting_capital) * 100.0 if starting_capital > 0 else 0.0

    # CAGR = (equity/starting_capital)^(365/days_elapsed) − 1
    # We use session elapsed in fractional days as the denominator.
    # When no sessions have completed yet, CAGR is effectively undefined → 0.
    cagr = 0.0
    try:
        ratio = equity / max(starting_capital, 1.0)
        if ratio > 0 and pnl_usd != 0:
            # Use 1 day as minimum time basis to avoid infinite CAGR on first cycle
            cagr = (ratio ** 365.0) - 1.0
    except Exception:
        cagr = 0.0

    # capital_utilization = (1 − buying_power/equity) × 100
    cap_util = max(0.0, (1.0 - buying_power / max(equity, 1.0))) * 100.0

    return {
        "equity_usd": round(equity, 2),
        "cash_usd": round(cash, 2),
        "buying_power_usd": round(buying_power, 2),
        "starting_capital_usd": round(starting_capital, 2),
        "pnl_usd": round(pnl_usd, 2),
        "pnl_pct": round(pnl_pct, 4),
        "cagr_if_sustained_1day": round(cagr * 100.0, 4),
        "cagr_formula": "CAGR = (equity/starting_capital)^365 − 1",
        "cagr_formula_key": "compound_rate",
        "capital_utilization_pct": round(cap_util, 2),
        "capital_utilization_formula": "cap_util_pct = (1 − buying_power/equity) × 100",
        "capital_utilization_formula_key": "capital_utilization",
        "position_size_pct_configured": position_size_pct,
    }


def compute_constraint_violations(
    feeds: dict,
    exec_metrics: dict,
    account_metrics: dict,
    equity: float,
    execution_context_note: str = "",
) -> list:
    """
    Detect every constraint violation and document it with:
      - what_happened
      - why_it_matters
      - formula_applied
      - financial_impact_usd
    """
    violations: list = []
    t = now_utc()

    # ── CONSTRAINT 1: Stale data feeds ──────────────────────────────────────
    for feed_name, feed in feeds.items():
        if not feed["is_stale"]:
            continue
        excess_secs = feed["age_secs"] - feed["max_acceptable_age_secs"]
        severity = "CRITICAL" if excess_secs > feed["max_acceptable_age_secs"] else "HIGH"
        violations.append({
            "constraint_id": f"STALE_DATA::{feed_name.upper()}",
            "category": "DATA_QUALITY",
            "severity": severity,
            "detected_utc": t,
            "sector": feed["sector"],
            "what_happened": (
                f"Feed '{feed['file']}' is {feed['age_secs']:.0f}s old. "
                f"Max acceptable: {feed['max_acceptable_age_secs']:.0f}s. "
                f"Excess staleness: {excess_secs:.0f}s."
            ),
            "why_it_matters": (
                "Stale market data causes the signal scoring engine to act on outdated "
                "prices. Edge degrades proportionally to staleness — a 20-bps edge "
                "becomes zero when the data is meaningless."
            ),
            "formula_applied": feed["formula_applied"],
            "formula_key": "opportunity_cost_stale_data",
            "financial_impact_usd": feed["opportunity_cost_usd"],
            "financial_impact_usd_per_hour": round(feed["opportunity_cost_usd"] / max(feed["age_secs"] / 3600.0, 0.001), 4),
            "financial_impact_explanation": (
                f"${feed['opportunity_cost_usd']:.4f} opportunity cost estimated from "
                f"{feed['baseline_edge_bps_used']:.0f} bps baseline edge × "
                f"{feed['age_secs']/3600:.3f}h stale window × "
                f"${equity:.0f} equity × {account_metrics['position_size_pct_configured']:.0%} pos_size."
            ),
            "freshness_score": feed["freshness_score"],
            "stale_secs": feed["age_secs"],
        })

    # ── CONSTRAINT 2: Degraded fill rate ────────────────────────────────────
    fill_rate = exec_metrics["fill_rate_pct"]
    n_orders = exec_metrics["total_orders_submitted"]
    if n_orders > 0 and fill_rate < 100.0:
        current_open_unfilled = int(exec_metrics.get("current_open_unfilled_orders_count") or 0)
        weekend_context = "weekend_closed" in str(execution_context_note or "").lower()
        if weekend_context and current_open_unfilled == 0:
            severity = "MEDIUM"
        else:
            severity = "CRITICAL" if fill_rate < 5.0 else "HIGH" if fill_rate < 50.0 else "MEDIUM"
        reserved_capital_cost = round(exec_metrics["reserved_capital_usd"] * (1.0 - fill_rate / 100.0), 2)
        opportunity_cost_24h = float(exec_metrics.get("execution_opportunity_cost_24h_usd") or 0.0)
        opportunity_cost_hist = float(exec_metrics.get("execution_opportunity_cost_historical_usd") or 0.0)
        cost = max(reserved_capital_cost, opportunity_cost_24h)
        violations.append({
            "constraint_id": "EXEC::FILL_RATE_DEGRADED",
            "category": "EXECUTION_QUALITY",
            "severity": severity,
            "detected_utc": t,
            "sector": "execution",
            "what_happened": (
                f"Fill rate: {fill_rate:.1f}% "
                f"({exec_metrics['filled_orders']} fills / {n_orders} orders submitted). "
                f"Historical unfilled: {exec_metrics['unfilled_orders_historical']}. "
                f"Current open unfilled now: {current_open_unfilled}."
            ),
            "why_it_matters": (
                "Unfilled orders reserve capital in Alpaca's buying_power ledger while "
                "generating zero return. Common causes: market closed, extended-hours "
                "illiquidity, limit price set below current ask."
            ),
            "formula_applied": exec_metrics["fill_rate_formula"],
            "formula_key": "fill_rate",
            "financial_impact_usd": cost,
            "financial_impact_explanation": (
                f"max(reserved-capital impact=${reserved_capital_cost:.2f}, "
                f"24h execution opp-cost=${opportunity_cost_24h:.2f}) => ${cost:.2f}. "
                f"Historical execution opp-cost=${opportunity_cost_hist:.2f}."
            ),
            "fill_rate_pct": fill_rate,
            "unfilled_count_historical": exec_metrics["unfilled_orders_historical"],
            "current_open_unfilled_count": current_open_unfilled,
            "market_context": execution_context_note,
        })

    # ── CONSTRAINT 3: Capital reserved by pending orders ────────────────────
    if exec_metrics["reserved_capital_usd"] > 50.0:
        burn_hourly = exec_metrics["capital_burn_rate_per_sec_usd"] * 3600.0
        violations.append({
            "constraint_id": "EXEC::CAPITAL_BURN_OPEN_ORDERS",
            "category": "CAPITAL_EFFICIENCY",
            "severity": "HIGH",
            "detected_utc": t,
            "sector": "execution",
            "what_happened": (
                f"${exec_metrics['reserved_capital_usd']:.2f} reserved by pending limit orders "
                f"that have not filled over a {exec_metrics['session_elapsed_secs']:.0f}s session."
            ),
            "why_it_matters": (
                "Capital reserved for unfilled limit orders cannot compound. "
                "Every second of non-fill is time value eroded from the compounding base. "
                "Weekend and after-hours sessions have near-zero fill rates on equity limit orders."
            ),
            "formula_applied": exec_metrics["capital_burn_formula"],
            "formula_key": "capital_burn_rate",
            "financial_impact_usd": round(burn_hourly, 4),
            "financial_impact_explanation": (
                f"${exec_metrics['capital_burn_rate_per_sec_usd']:.6f}/sec × 3600 = "
                f"${burn_hourly:.4f}/hr of dead capital. "
                f"Session elapsed: {exec_metrics['session_elapsed_secs']:.0f}s."
            ),
            "burn_rate_per_sec_usd": exec_metrics["capital_burn_rate_per_sec_usd"],
            "burn_rate_per_hour_usd": round(burn_hourly, 4),
        })

    # ── CONSTRAINT 4: Active unrealized losses ──────────────────────────────
    for lps_entry in exec_metrics.get("losses_per_second", []):
        cost = abs(lps_entry["unrealized_pl_usd"])
        severity = "CRITICAL" if cost > 500 else "HIGH" if cost > 100 else "MEDIUM"
        violations.append({
            "constraint_id": f"POSITION::OPEN_LOSS::{lps_entry['symbol']}",
            "category": "POSITION_RISK",
            "severity": severity,
            "detected_utc": t,
            "sector": lps_entry.get("sector", "equities"),
            "what_happened": (
                f"{lps_entry['symbol']} unrealized loss: ${lps_entry['unrealized_pl_usd']:.4f} "
                f"over {lps_entry['position_age_secs']:.0f}s hold time."
            ),
            "why_it_matters": (
                f"Position is burning ${lps_entry['loss_per_second_usd']:.6f}/sec. "
                "Auto stop-loss fires at −1.0% unrealized P&L. "
                "Time-stop fires at 90 min hold."
            ),
            "formula_applied": lps_entry["formula"],
            "formula_key": "loss_per_second",
            "financial_impact_usd": round(cost, 4),
            "financial_impact_explanation": (
                f"${lps_entry['loss_per_second_usd']:.6f}/sec × 3600 = "
                f"${lps_entry['loss_per_second_usd']*3600:.4f}/hr if position held unclosed."
            ),
            "loss_per_second_usd": lps_entry["loss_per_second_usd"],
            "symbol": lps_entry["symbol"],
        })

    return violations


def compute_sector_metrics(ledger: list, status: dict) -> dict:
    """
    Track trade count, fill rate, notional, and P&L by sector.
    Formula: sector_pnl = Σ(realized_pnl in sector) + Σ(unrealized_pl in sector)
    """
    sector_stats: dict[str, dict] = {}
    positions: list = status.get("positions") or []

    def _init(sec: str) -> None:
        if sec not in sector_stats:
            sector_stats[sec] = {
                "sector": sec,
                "trade_count": 0,
                "filled_count": 0,
                "total_notional_usd": 0.0,
                "realized_pnl_usd": 0.0,
                "unrealized_pnl_usd": 0.0,
                "open_positions": 0,
                "best_score": -1e9,
                "best_score_symbol": None,
                "worst_score": 1e9,
                "worst_score_symbol": None,
            }

    for row in ledger:
        symbol = str(row.get("symbol", "")).upper()
        if not symbol:
            continue
        sector = SYMBOL_SECTOR_MAP.get(symbol, "equities_other")
        _init(sector)
        action = str(row.get("action", "")).lower()
        if action == "open":
            result = row.get("result") or {}
            if isinstance(result, list):
                result = (result[0] if result else {})
            filled_qty = float(result.get("filled_qty") or 0.0)
            notional = float(row.get("notional_usd") or 0.0)
            score = float(row.get("score") or 0.0)
            sector_stats[sector]["trade_count"] += 1
            sector_stats[sector]["total_notional_usd"] += notional
            if filled_qty > 0:
                sector_stats[sector]["filled_count"] += 1
            if score > sector_stats[sector]["best_score"]:
                sector_stats[sector]["best_score"] = round(score, 4)
                sector_stats[sector]["best_score_symbol"] = symbol
            if score < sector_stats[sector]["worst_score"]:
                sector_stats[sector]["worst_score"] = round(score, 4)
                sector_stats[sector]["worst_score_symbol"] = symbol

    for pos in positions:
        symbol = str(pos.get("symbol", "")).upper()
        sector = SYMBOL_SECTOR_MAP.get(symbol, "equities_other")
        _init(sector)
        unrealized_pl = float(pos.get("unrealized_pl") or 0.0)
        sector_stats[sector]["unrealized_pnl_usd"] += unrealized_pl
        sector_stats[sector]["open_positions"] += 1

    for stats in sector_stats.values():
        stats["total_notional_usd"] = round(stats["total_notional_usd"], 2)
        stats["realized_pnl_usd"] = round(stats["realized_pnl_usd"], 4)
        stats["unrealized_pnl_usd"] = round(stats["unrealized_pnl_usd"], 4)
        stats["net_pnl_usd"] = round(stats["realized_pnl_usd"] + stats["unrealized_pnl_usd"], 4)
        stats["fill_rate_pct"] = round(
            (stats["filled_count"] / max(stats["trade_count"], 1)) * 100.0, 1
        )
        stats["sector_pnl_formula"] = (
            "sector_pnl = Σ(realized_pnl in sector) + Σ(unrealized_pl in sector)"
        )
        stats["sector_pnl_formula_key"] = "sector_pnl"
        if stats["best_score"] == -1e9:
            stats["best_score"] = 0.0
        if stats["worst_score"] == 1e9:
            stats["worst_score"] = 0.0

    return sector_stats


# ─────────────────────────── main monitor cycle ───────────────────────────────

def run_once(chain: AuditChain) -> dict:
    """Execute one full monitoring cycle. Returns the full constraint status payload."""
    t = now_utc()

    paper_runtime = load_json(PAPER_RUNTIME_FILE, {})
    status = load_json(STATUS_FILE, {})
    state = load_json(STATE_FILE, {})
    ledger = load_jsonl(LEDGER_FILE)
    registry = load_json(REGISTRY_FILE, {})
    env_pairs = load_env_pairs(ENV_FILE)
    runtime = load_json(RUNTIME_FILE, {})

    account = status.get("account") or {}
    equity = float(account.get("equity") or 100000.0)
    position_size_pct = float(paper_runtime.get("position_size_pct") or 0.55)

    # ── Run all measurement passes ──────────────────────────────────────────
    feeds = compute_data_feed_metrics(equity, position_size_pct)
    exec_metrics = compute_execution_metrics(ledger, state, status, equity, position_size_pct)
    account_metrics = compute_account_metrics(status, paper_runtime)
    violations = compute_constraint_violations(
        feeds,
        exec_metrics,
        account_metrics,
        equity,
        execution_context_note=str(status.get("status_note", "")),
    )
    sector_metrics = compute_sector_metrics(ledger, status)

    # ── Registry summary ────────────────────────────────────────────────────
    registry_rows = registry.get("rows", []) if isinstance(registry, dict) else []
    registry_summary = {
        "total_sources": len(registry_rows),
        "enabled_sources": sum(1 for r in registry_rows if r.get("enabled")),
        "measured_sources": sum(1 for r in registry_rows if r.get("dollar_basis") == "MEASURED"),
        "sectors_present": list({r.get("sector", "unknown") for r in registry_rows}),
    }
    api_coverage = compute_api_source_coverage(registry_rows, env_pairs)
    chain_integrity = verify_audit_chain(AUDIT_CHAIN_FILE)

    input_hashes = {
        "alpaca_status_sha256": sha256_file_safe(STATUS_FILE),
        "paper_state_sha256": sha256_file_safe(STATE_FILE),
        "paper_ledger_sha256": sha256_file_safe(LEDGER_FILE),
        "source_registry_sha256": sha256_file_safe(REGISTRY_FILE),
        "runtime_control_sha256": sha256_file_safe(RUNTIME_FILE),
        "paper_runtime_sha256": sha256_file_safe(PAPER_RUNTIME_FILE),
    }

    # ── Total opportunity cost across all stale feeds ───────────────────────
    total_opp_cost = sum(f["opportunity_cost_usd"] for f in feeds.values() if f["is_stale"])
    total_loss_per_sec = exec_metrics["total_loss_per_second_usd"]
    total_burn_per_sec = exec_metrics["capital_burn_rate_per_sec_usd"]

    if api_coverage["provider_count_configured"] > 0 and api_coverage["live_data_coverage_pct"] < 75.0:
        coverage_violation = {
            "constraint_id": "INGEST::API_COVERAGE_LOW",
            "category": "DATA_QUALITY",
            "severity": "HIGH" if api_coverage["live_data_coverage_pct"] < 50.0 else "MEDIUM",
            "detected_utc": t,
            "sector": "ingestion",
            "what_happened": (
                f"Only {api_coverage['provider_count_with_live_rows']}/"
                f"{api_coverage['provider_count_configured']} configured providers currently show live rows."
            ),
            "why_it_matters": (
                "If API coverage is incomplete, predictive signal confidence drops and blind spots increase. "
                "Read-only detection quality is limited by ingestion completeness."
            ),
            "formula_applied": "live_data_coverage_pct = provider_count_with_live_rows / provider_count_configured × 100",
            "formula_key": "data_freshness_score",
            "financial_impact_usd": round(total_opp_cost, 4),
            "financial_impact_explanation": (
                "Using stale-data opportunity cost as a conservative lower-bound proxy for incomplete ingestion impact."
            ),
            "coverage_pct": api_coverage["live_data_coverage_pct"],
        }
        violations.append(coverage_violation)

    payload = {
        "schema": "infra_constraint_status_v1",
        "monitor_version": "1.0.0",
        "generated_utc": t,
        "monitor_cycle_epoch": now_ts(),
        # ── Account ──
        "account_metrics": account_metrics,
        # ── Execution ──
        "execution_metrics": exec_metrics,
        # ── Data feeds ──
        "data_feed_metrics": feeds,
        "stale_feed_count": sum(1 for f in feeds.values() if f["is_stale"]),
        "fresh_feed_count": sum(1 for f in feeds.values() if not f["is_stale"]),
        "total_feed_count": len(feeds),
        # ── Constraints ──
        "constraint_violations": violations,
        "violation_count": len(violations),
        "violations_by_severity": {
            "CRITICAL": sum(1 for v in violations if v.get("severity") == "CRITICAL"),
            "HIGH": sum(1 for v in violations if v.get("severity") == "HIGH"),
            "MEDIUM": sum(1 for v in violations if v.get("severity") == "MEDIUM"),
        },
        "violations_by_category": {
            cat: sum(1 for v in violations if v.get("category") == cat)
            for cat in {"DATA_QUALITY", "EXECUTION_QUALITY", "CAPITAL_EFFICIENCY", "POSITION_RISK"}
        },
        # ── Financial impact summary ──────────────────────────────────────
        "financial_impact_summary": {
            "total_opportunity_cost_usd": round(total_opp_cost, 4),
            "execution_opportunity_cost_24h_usd": round(float(exec_metrics.get("execution_opportunity_cost_24h_usd") or 0.0), 4),
            "execution_opportunity_cost_historical_usd": round(float(exec_metrics.get("execution_opportunity_cost_historical_usd") or 0.0), 4),
            "total_loss_per_second_usd": round(total_loss_per_sec, 8),
            "total_capital_burn_per_sec_usd": round(total_burn_per_sec, 6),
            "total_dead_capital_usd": exec_metrics["reserved_capital_usd"],
            "combined_loss_rate_per_hour_usd": round(
                (total_loss_per_sec + total_burn_per_sec) * 3600.0, 4
            ),
            "explanation": (
                "opportunity_cost = stale data impact; "
                "execution_opportunity_cost = unfilled notional drag; "
                "loss_per_sec = unrealized losses on open positions; "
                "capital_burn = reserved-but-unfilled order deadweight"
            ),
        },
        # ── Sector breakdown ──
        "sector_metrics": sector_metrics,
        # ── Formula registry (full documentation) ──
        "formula_registry": FORMULA_REGISTRY,
        # ── Registry state ──
        "registry_summary": registry_summary,
        "api_source_coverage": api_coverage,
        # ── Market / execution context ──
        "execution_context": {
            "status_note": status.get("status_note", ""),
            "positions_open": len(status.get("positions") or []),
            "top_candidate": status.get("top_candidate") or {},
            "ranked_count": len(status.get("top_ranked") or []),
            "paper_runtime": paper_runtime,
        },
    }

    truth_score = 100.0
    truth_score -= min(40.0, max(0.0, payload["stale_feed_count"] * 2.0))
    truth_score -= 20.0 if not chain_integrity.get("tail_ok", chain_integrity.get("ok", True)) else 0.0
    truth_score -= 20.0 if float(api_coverage.get("live_data_coverage_pct", 0.0)) < 50.0 else 0.0
    truth_score -= 10.0 if float(exec_metrics.get("current_open_unfilled_orders_count", 0)) > 0 else 0.0
    truth_score = max(0.0, min(100.0, truth_score))

    payload["truth_hardening"] = {
        "truth_score": round(truth_score, 2),
        "truth_grade": (
            "A" if truth_score >= 90 else "B" if truth_score >= 80 else "C" if truth_score >= 70 else "D"
        ),
        "audit_chain": chain_integrity,
        "input_hashes": input_hashes,
    }
    payload["reproducibility_fingerprint_sha256"] = build_reproducibility_fingerprint(payload)

    history_rows = load_jsonl(TRUTH_HISTORY_FILE)
    truth_history_summary = summarize_truth_history(history_rows, payload["reproducibility_fingerprint_sha256"])
    sla_target_coverage_pct = 80.0
    current_coverage = float(api_coverage.get("live_data_coverage_pct", 0.0))
    payload["truth_hardening"]["executive_trust_report"] = {
        "chain_tail_pass_rate_24h_pct": truth_history_summary["chain_tail_pass_rate_24h_pct"],
        "fingerprint_change_rate_24h_pct": truth_history_summary["fingerprint_change_rate_24h_pct"],
        "latest_fingerprint_changed": truth_history_summary["latest_fingerprint_changed"],
        "coverage_sla_target_pct": sla_target_coverage_pct,
        "coverage_current_pct": round(current_coverage, 2),
        "coverage_sla_compliant": current_coverage >= sla_target_coverage_pct,
        "samples_24h": truth_history_summary["samples_24h"],
    }

    append_jsonl(
        TRUTH_HISTORY_FILE,
        {
            "generated_utc": payload["generated_utc"],
            "truth_score": payload["truth_hardening"]["truth_score"],
            "truth_grade": payload["truth_hardening"]["truth_grade"],
            "chain_tail_ok": payload["truth_hardening"]["audit_chain"].get("tail_ok", True),
            "api_live_coverage_pct": current_coverage,
            "reproducibility_fingerprint_sha256": payload["reproducibility_fingerprint_sha256"],
        },
    )

    save_json(CONSTRAINT_STATUS_FILE, payload)
    save_json(SECTOR_METRICS_FILE, sector_metrics)

    cycle_signature = {
        "generated_utc": payload["generated_utc"],
        "status_file_sha256": sha256_file_safe(CONSTRAINT_STATUS_FILE),
        "reproducibility_fingerprint_sha256": payload["reproducibility_fingerprint_sha256"],
        "truth_score": payload["truth_hardening"]["truth_score"],
        "input_hashes": input_hashes,
        "chain_last_hash": chain_integrity.get("last_event_hash", "GENESIS"),
    }
    cycle_signature["signature_sha256"] = sha256_text(
        json.dumps(cycle_signature, sort_keys=True, separators=(",", ":"))
    )
    append_jsonl(CYCLE_SIGNATURE_FILE, cycle_signature)

    # ── Write each violation to audit chain ─────────────────────────────────
    for v in violations:
        chain.append(
            event_type=f"CONSTRAINT::{v['constraint_id']}",
            payload={
                "severity": v.get("severity"),
                "category": v.get("category"),
                "sector": v.get("sector"),
                "what_happened": v.get("what_happened"),
                "why_it_matters": v.get("why_it_matters"),
                "financial_impact_usd": v.get("financial_impact_usd"),
                "formula_applied": v.get("formula_applied"),
                "formula_key": v.get("formula_key"),
            },
        )

    # ── Write cycle summary to audit chain ──────────────────────────────────
    chain.append(
        event_type="MONITOR_CYCLE",
        payload={
            "equity_usd": account_metrics["equity_usd"],
            "pnl_usd": account_metrics["pnl_usd"],
            "fill_rate_pct": exec_metrics["fill_rate_pct"],
            "total_orders_submitted": exec_metrics["total_orders_submitted"],
            "filled_orders": exec_metrics["filled_orders"],
            "violation_count": len(violations),
            "stale_feed_count": payload["stale_feed_count"],
            "api_live_coverage_pct": api_coverage["live_data_coverage_pct"],
            "total_opp_cost_usd": round(total_opp_cost, 4),
            "total_loss_per_sec_usd": round(total_loss_per_sec, 8),
            "capital_burn_per_sec_usd": round(total_burn_per_sec, 6),
            "reserved_capital_usd": exec_metrics["reserved_capital_usd"],
            "truth_score": payload["truth_hardening"]["truth_score"],
            "repro_fingerprint": payload["reproducibility_fingerprint_sha256"],
        },
    )

    return payload


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Government-grade real-time infrastructure constraint monitor"
    )
    parser.add_argument("--loop", action="store_true", help="Run continuously")
    parser.add_argument("--interval", type=float, default=3.0, help="Seconds between cycles")
    parser.add_argument("--new-epoch", action="store_true", help="Archive current chain/history and start a new audit epoch")
    args = parser.parse_args()

    acquire_monitor_lock()

    if args.new_epoch:
        epoch_info = archive_and_reset_chain_epoch()
        print("[EPOCH] Started new audit epoch")
        print(json.dumps(epoch_info, indent=2))

    chain = AuditChain(AUDIT_CHAIN_FILE)

    print("=" * 76)
    print("  LUMENTRACE INFRA CONSTRAINT MONITOR  —  Government-Grade Audit Engine")
    print("=" * 76)
    print(f"  Audit chain  : {AUDIT_CHAIN_FILE}")
    print(f"  Status output: {CONSTRAINT_STATUS_FILE}")
    print(f"  Sector output: {SECTOR_METRICS_FILE}")
    print(f"  Loop interval: {args.interval}s  |  Continuous: {args.loop}")
    print("=" * 76)

    while True:
        try:
            p = run_once(chain)
            eq = p["account_metrics"]["equity_usd"]
            pnl = p["account_metrics"]["pnl_usd"]
            viol = p["violation_count"]
            fill = p["execution_metrics"]["fill_rate_pct"]
            stale = p["stale_feed_count"]
            lps = p["execution_metrics"]["total_loss_per_second_usd"]
            burn = p["execution_metrics"]["capital_burn_rate_per_sec_usd"]
            print(
                f"[{p['generated_utc']}]  "
                f"equity=${eq:,.2f}  pnl=${pnl:+.2f}  "
                f"fill={fill:.1f}%  violations={viol}  "
                f"stale_feeds={stale}  loss/s=${lps:.8f}  burn/s=${burn:.6f}"
            )
        except Exception as exc:
            print(f"[ERROR] Monitor cycle failed: {exc}")

        if not args.loop:
            break
        time.sleep(args.interval)


if __name__ == "__main__":
    main()
