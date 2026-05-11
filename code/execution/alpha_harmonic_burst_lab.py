from __future__ import annotations

import argparse
import csv
import json
import math
import os
import sqlite3
import statistics
import time
import urllib.error
import urllib.parse
import urllib.request
from concurrent.futures import ProcessPoolExecutor, ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Tuple


ROOT = Path(__file__).resolve().parents[2]
WORKSPACE_ROOT = ROOT.parent
OUT_DIR = ROOT / "out" / "execution"
REGISTRY_FILE = ROOT / "config" / "live_source_registry.json"
TRADE_LOG_FILE = OUT_DIR / "trade_log.json"
DATA_DIR = WORKSPACE_ROOT / "clean_data"

KEY_FILES = [
    ROOT / "config" / "luma_live_keys.env",
    ROOT / "code" / "execution" / "config" / "luma_live_keys.env",
]

SUMMARY_FILE = OUT_DIR / "alpha_burst_lab_summary.json"
CONSTRAINT_FILE = OUT_DIR / "live_api_constraint_probe.json"
DB_FILE = OUT_DIR / "alpha_burst_lab.db"
REPORT_FILE = OUT_DIR / "alpha_burst_lab_report.md"


def now_utc() -> str:
    return datetime.now(timezone.utc).isoformat()


def read_json(path: Path, default: Any) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return default


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(f"{path.name}.tmp")
    tmp.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    os.replace(tmp, path)


def parse_env_files(paths: Iterable[Path]) -> Dict[str, str]:
    env_map: Dict[str, str] = {}
    for path in paths:
        if not path.exists():
            continue
        try:
            for raw_line in path.read_text(encoding="utf-8", errors="ignore").splitlines():
                line = raw_line.strip()
                if not line or line.startswith("#") or "=" not in line:
                    continue
                key, value = line.split("=", 1)
                k = key.strip()
                v = value.strip().strip('"').strip("'")
                if k and v:
                    env_map[k] = v
        except Exception:
            continue
    return env_map


def parse_env_names(env_field: str) -> List[str]:
    return [x.strip() for x in str(env_field or "").split(",") if x.strip()]


def probe_request(url: str, headers: Optional[Dict[str, str]] = None, timeout_sec: float = 8.0) -> Dict[str, Any]:
    started = time.perf_counter()
    req = urllib.request.Request(url, headers=headers or {})
    try:
        with urllib.request.urlopen(req, timeout=timeout_sec) as resp:
            body = resp.read(280)
            elapsed_ms = (time.perf_counter() - started) * 1000.0
            return {
                "probe_ok": True,
                "http_status": int(getattr(resp, "status", 200) or 200),
                "latency_ms": round(elapsed_ms, 2),
                "sample": body.decode(errors="ignore"),
                "error": "",
            }
    except urllib.error.HTTPError as exc:
        elapsed_ms = (time.perf_counter() - started) * 1000.0
        body = b""
        try:
            body = exc.read(280)
        except Exception:
            body = b""
        return {
            "probe_ok": False,
            "http_status": int(exc.code),
            "latency_ms": round(elapsed_ms, 2),
            "sample": body.decode(errors="ignore"),
            "error": f"HTTP {exc.code}",
        }
    except Exception as exc:
        elapsed_ms = (time.perf_counter() - started) * 1000.0
        return {
            "probe_ok": False,
            "http_status": None,
            "latency_ms": round(elapsed_ms, 2),
            "sample": "",
            "error": str(exc),
        }


def build_probe_spec(source: str, env_map: Dict[str, str]) -> Optional[Dict[str, Any]]:
    src = source.upper().strip()

    if src == "ALPHAVANTAGE" and env_map.get("ALPHAVANTAGE_API_KEY"):
        key = urllib.parse.quote_plus(env_map["ALPHAVANTAGE_API_KEY"])
        return {"url": f"https://www.alphavantage.co/query?function=GLOBAL_QUOTE&symbol=AAPL&apikey={key}", "headers": {}}

    if src == "FINNHUB" and env_map.get("FINNHUB_API_KEY"):
        key = urllib.parse.quote_plus(env_map["FINNHUB_API_KEY"])
        return {"url": f"https://finnhub.io/api/v1/quote?symbol=AAPL&token={key}", "headers": {}}

    if src == "TWELVE_DATA" and env_map.get("TWELVE_DATA_API_KEY"):
        key = urllib.parse.quote_plus(env_map["TWELVE_DATA_API_KEY"])
        return {"url": f"https://api.twelvedata.com/time_series?symbol=AAPL&interval=1h&outputsize=2&apikey={key}", "headers": {}}

    if src == "FRED" and env_map.get("FRED_API_KEY"):
        key = urllib.parse.quote_plus(env_map["FRED_API_KEY"])
        return {
            "url": "https://api.stlouisfed.org/fred/series/observations?series_id=DGS10&file_type=json&limit=2&api_key=" + key,
            "headers": {},
        }

    if src == "ALPACA" and env_map.get("ALPACA_API_KEY") and env_map.get("ALPACA_API_SECRET"):
        return {
            "url": "https://data.alpaca.markets/v2/stocks/AAPL/bars/latest",
            "headers": {
                "APCA-API-KEY-ID": env_map["ALPACA_API_KEY"],
                "APCA-API-SECRET-KEY": env_map["ALPACA_API_SECRET"],
            },
        }

    if src == "KRAKEN":
        return {"url": "https://api.kraken.com/0/public/Ticker?pair=XBTUSD", "headers": {}}

    if src == "NREL" and env_map.get("NREL_API_KEY"):
        key = urllib.parse.quote_plus(env_map["NREL_API_KEY"])
        return {
            "url": f"https://developer.nrel.gov/api/alt-fuel-stations/v1/nearest.json?api_key={key}&location=80202&limit=1",
            "headers": {},
        }

    if src == "NASA" and env_map.get("NASA_API_KEY"):
        key = urllib.parse.quote_plus(env_map["NASA_API_KEY"])
        return {"url": f"https://api.nasa.gov/planetary/apod?api_key={key}", "headers": {}}

    if src == "NOAA_NCEI" and env_map.get("NOAA_API_TOKEN"):
        return {
            "url": "https://www.ncei.noaa.gov/cdo-web/api/v2/datasets?limit=1",
            "headers": {"token": env_map["NOAA_API_TOKEN"]},
        }

    if src == "BLS" and env_map.get("BLS_API_KEY"):
        key = urllib.parse.quote_plus(env_map["BLS_API_KEY"])
        return {
            "url": f"https://api.bls.gov/publicAPI/v2/timeseries/data/LNS14000000?registrationkey={key}",
            "headers": {},
        }

    if src == "BEA" and env_map.get("BEA_API_KEY"):
        key = urllib.parse.quote_plus(env_map["BEA_API_KEY"])
        return {
            "url": f"https://apps.bea.gov/api/data/?UserID={key}&method=GETDATASETLIST&ResultFormat=json",
            "headers": {},
        }

    if src == "MASSIVE" and env_map.get("MASSIVE_API_KEY"):
        key = urllib.parse.quote_plus(env_map["MASSIVE_API_KEY"])
        return {
            "url": f"https://api.polygon.io/v2/aggs/ticker/AAPL/range/1/day/2025-01-02/2025-01-03?adjusted=true&sort=asc&limit=2&apiKey={key}",
            "headers": {},
        }

    return None


def evaluate_provider_constraint(row: Dict[str, Any], env_map: Dict[str, str]) -> Dict[str, Any]:
    source = str(row.get("source", "UNKNOWN"))
    sector = str(row.get("sector", "unknown"))
    env_names = parse_env_names(str(row.get("env", "")))
    measured_rows = int(row.get("rows", 0) or 0)
    enabled = bool(row.get("enabled", False))

    key_present = all(env_map.get(name, "").strip() for name in env_names) if env_names else False
    probe_spec = build_probe_spec(source, env_map) if key_present else None

    if not enabled or not key_present:
        return {
            "source": source,
            "sector": sector,
            "enabled": enabled,
            "env_names": env_names,
            "key_present": key_present,
            "probe_supported": probe_spec is not None,
            "probe_ok": False,
            "http_status": None,
            "latency_ms": None,
            "measured_rows": measured_rows,
            "constraint_level": "CRITICAL",
            "constraint_reason": "missing_or_disabled_keys",
        }

    if probe_spec is None:
        level = "MEDIUM" if measured_rows > 0 else "HIGH"
        return {
            "source": source,
            "sector": sector,
            "enabled": enabled,
            "env_names": env_names,
            "key_present": key_present,
            "probe_supported": False,
            "probe_ok": False,
            "http_status": None,
            "latency_ms": None,
            "measured_rows": measured_rows,
            "constraint_level": level,
            "constraint_reason": "no_probe_mapping",
        }

    result = probe_request(probe_spec["url"], probe_spec.get("headers", {}), timeout_sec=8.0)
    level = "LOW"
    reason = "healthy"

    if not result["probe_ok"]:
        level = "HIGH"
        reason = "probe_failed"
    elif measured_rows == 0:
        level = "MEDIUM"
        reason = "live_probe_ok_but_no_measured_rows"
    elif result["latency_ms"] is not None and float(result["latency_ms"]) > 2200:
        level = "MEDIUM"
        reason = "high_latency"

    return {
        "source": source,
        "sector": sector,
        "enabled": enabled,
        "env_names": env_names,
        "key_present": key_present,
        "probe_supported": True,
        "probe_ok": bool(result["probe_ok"]),
        "http_status": result["http_status"],
        "latency_ms": result["latency_ms"],
        "measured_rows": measured_rows,
        "constraint_level": level,
        "constraint_reason": reason,
        "probe_error": result["error"],
    }


def load_trade_returns(trade_log_path: Path, cap: int = 40000) -> List[float]:
    rows = read_json(trade_log_path, [])
    out: List[float] = []
    if not isinstance(rows, list):
        return out

    for row in rows:
        if not isinstance(row, dict):
            continue
        if str(row.get("status", "")).upper() != "CLOSED":
            continue
        val = row.get("net_pnl_pct")
        if val is None:
            val = row.get("pnl_pct")
        try:
            out.append(float(val) / 100.0)
        except Exception:
            continue
        if len(out) >= cap:
            break
    return out


def sniff_close_column(headers: List[str]) -> Optional[str]:
    candidates = ["close", "Close", "adj_close", "Adj Close", "price", "Price", "last", "Last"]
    hset = set(headers)
    for key in candidates:
        if key in hset:
            return key
    return headers[0] if headers else None


def prices_to_returns(prices: List[float]) -> List[float]:
    if len(prices) < 3:
        return []
    rets: List[float] = []
    prev = prices[0]
    for price in prices[1:]:
        if prev > 0 and price > 0:
            rets.append((price - prev) / prev)
        prev = price
    return rets


def load_csv_return_series(data_dir: Path, max_files: int = 18, max_len: int = 6000) -> Dict[str, List[float]]:
    series: Dict[str, List[float]] = {}
    if not data_dir.exists():
        return series

    patterns = ["alpaca_*.csv", "av_fx_*.csv", "close__*.csv"]
    files: List[Path] = []
    for pattern in patterns:
        files.extend(sorted(data_dir.glob(pattern)))

    picked: List[Path] = []
    seen = set()
    for path in files:
        key = str(path.resolve()).lower()
        if key in seen:
            continue
        seen.add(key)
        picked.append(path)
        if len(picked) >= max_files:
            break

    for path in picked:
        prices: List[float] = []
        try:
            with path.open("r", encoding="utf-8", errors="ignore", newline="") as f:
                reader = csv.DictReader(f)
                if not reader.fieldnames:
                    continue
                col = sniff_close_column(list(reader.fieldnames))
                if not col:
                    continue
                for row in reader:
                    try:
                        prices.append(float(str(row.get(col, "")).strip()))
                    except Exception:
                        continue
                    if len(prices) >= max_len + 1:
                        break
        except Exception:
            continue

        returns = prices_to_returns(prices)
        if len(returns) >= 120:
            series[path.stem] = returns[-max_len:]

    return series


def rolling_mean(values: List[float], window: int) -> List[float]:
    n = len(values)
    out = [0.0] * n
    if window <= 1:
        return list(values)
    acc = 0.0
    for i, v in enumerate(values):
        acc += v
        if i >= window:
            acc -= values[i - window]
        count = min(i + 1, window)
        out[i] = acc / float(count)
    return out


def rolling_std(values: List[float], window: int) -> List[float]:
    n = len(values)
    out = [0.0] * n
    if window <= 1:
        return out
    for i in range(n):
        start = max(0, i - window + 1)
        segment = values[start : i + 1]
        if len(segment) <= 1:
            out[i] = 0.0
        else:
            out[i] = statistics.pstdev(segment)
    return out


def normalize(values: List[float]) -> List[float]:
    if not values:
        return []
    denom = sum(abs(v) for v in values) / float(len(values))
    if denom <= 1e-12:
        return [0.0] * len(values)
    return [v / denom for v in values]


def clamp(values: List[float], lo: float, hi: float) -> List[float]:
    return [max(lo, min(hi, v)) for v in values]


def harmonic_phase_coherence(returns: List[float]) -> List[float]:
    fast = rolling_mean(returns, 5)
    mid = rolling_mean(returns, 13)
    slow = rolling_mean(returns, 34)
    signal = []
    for a, b, c in zip(fast, mid, slow):
        v = (math.copysign(1.0, a - b) if a != b else 0.0)
        v += (math.copysign(1.0, b - c) if b != c else 0.0)
        v += (math.copysign(1.0, a - c) if a != c else 0.0)
        signal.append(v / 3.0)
    return clamp(normalize(signal), -1.0, 1.0)


def harmonic_envelope(returns: List[float]) -> List[float]:
    mu = rolling_mean(returns, 20)
    sd = rolling_std(returns, 20)
    tilt = rolling_mean(returns, 5)
    out: List[float] = []
    for r, m, s, t in zip(returns, mu, sd, tilt):
        z = 0.0 if s <= 1e-12 else (r - m) / s
        env = math.exp(-0.5 * z * z)
        out.append(env * (1.0 if t >= 0 else -1.0))
    return clamp(normalize(out), -3.0, 3.0)


def harmonic_resonance_cluster(returns: List[float]) -> List[float]:
    mom = rolling_mean(returns, 8)
    mean21 = rolling_mean(returns, 21)
    rev = [-(r - m) for r, m in zip(returns, mean21)]
    vol = [-x for x in rolling_std(returns, 8)]
    combo = [(a + b + c) / 3.0 for a, b, c in zip(normalize(mom), normalize(rev), normalize(vol))]
    return clamp(normalize(combo), -3.0, 3.0)


def harmonic_geometry_consensus(returns: List[float]) -> List[float]:
    a = normalize(rolling_mean(returns, 5))
    b = normalize([math.sin(x) for x in rolling_mean(returns, 8)])
    c = normalize([math.cos(x) for x in rolling_mean(returns, 13)])
    d = normalize([math.tanh(x) for x in rolling_mean(returns, 21)])
    out: List[float] = []
    for x1, x2, x3, x4 in zip(a, b, c, d):
        s = 0.0
        s += 1.0 if x1 > 0 else -1.0 if x1 < 0 else 0.0
        s += 1.0 if x2 > 0 else -1.0 if x2 < 0 else 0.0
        s += 1.0 if x3 > 0 else -1.0 if x3 < 0 else 0.0
        s += 1.0 if x4 > 0 else -1.0 if x4 < 0 else 0.0
        out.append(s / 4.0)
    return clamp(normalize(out), -1.0, 1.0)


ALGO_MAP = {
    "phase_coherence": harmonic_phase_coherence,
    "harmonic_envelope": harmonic_envelope,
    "resonance_cluster": harmonic_resonance_cluster,
    "geometry_consensus": harmonic_geometry_consensus,
}


def bar_metrics(returns: List[float]) -> Dict[str, float]:
    if not returns:
        return {
            "total_return_pct": 0.0,
            "mean_bar_return": 0.0,
            "volatility": 0.0,
            "sharpe": 0.0,
            "max_drawdown_pct": 0.0,
        }

    equity = 1.0
    peak = 1.0
    max_dd = 0.0
    for r in returns:
        equity *= 1.0 + r
        peak = max(peak, equity)
        if peak > 0:
            max_dd = max(max_dd, (peak - equity) / peak)

    mean_r = sum(returns) / float(len(returns))
    vol = statistics.pstdev(returns) if len(returns) > 1 else 0.0
    sharpe = (mean_r / vol) * math.sqrt(252.0) if vol > 1e-12 else 0.0

    return {
        "total_return_pct": (equity - 1.0) * 100.0,
        "mean_bar_return": mean_r,
        "volatility": vol,
        "sharpe": sharpe,
        "max_drawdown_pct": max_dd * 100.0,
    }


def backtest_signal(returns: List[float], signal: List[float], entry: float, exit_: float, hold_max: int) -> Dict[str, Any]:
    if not returns or not signal or len(returns) != len(signal):
        m = bar_metrics([])
        return {
            **m,
            "win_rate": 0.0,
            "trades": 0,
            "avg_trade_return_pct": 0.0,
            "edge_bps": 0.0,
        }

    position = False
    hold = 0
    strategy_returns: List[float] = []
    trade_returns: List[float] = []
    trade_equity = 1.0

    for r, s in zip(returns, signal):
        if not position and s >= entry:
            position = True
            hold = 0
            trade_equity = 1.0

        bar_r = r if position else 0.0
        strategy_returns.append(bar_r)

        if position:
            hold += 1
            trade_equity *= 1.0 + r
            if s <= exit_ or hold >= hold_max:
                trade_returns.append((trade_equity - 1.0) * 100.0)
                position = False

    if position:
        trade_returns.append((trade_equity - 1.0) * 100.0)

    m = bar_metrics(strategy_returns)
    wins = sum(1 for x in trade_returns if x > 0)
    trades = len(trade_returns)
    win_rate = (wins / float(trades)) if trades else 0.0
    avg_trade = (sum(trade_returns) / float(trades)) if trades else 0.0

    return {
        **m,
        "win_rate": win_rate,
        "trades": trades,
        "avg_trade_return_pct": avg_trade,
        "edge_bps": m["mean_bar_return"] * 10000.0,
    }


def evaluate_series_algo(payload: Dict[str, Any]) -> List[Dict[str, Any]]:
    series_name = payload["series_name"]
    algo_name = payload["algo_name"]
    returns = payload["returns"]
    signal = payload["signal"]
    entries = payload["entries"]
    exits = payload["exits"]
    holds = payload["holds"]
    baseline = payload["baseline"]
    baseline_edge_bps = float(baseline.get("mean_bar_return", 0.0)) * 10000.0

    out: List[Dict[str, Any]] = []
    for entry in entries:
        for exit_ in exits:
            if exit_ >= entry:
                continue
            for hold_max in holds:
                metrics = backtest_signal(returns, signal, entry, exit_, hold_max)
                score = (
                    (metrics["total_return_pct"] * 1.7)
                    + (metrics["sharpe"] * 9.0)
                    + (metrics["win_rate"] * 28.0)
                    - (metrics["max_drawdown_pct"] * 0.9)
                )

                out.append(
                    {
                        "series": series_name,
                        "algo": algo_name,
                        "entry_threshold": float(entry),
                        "exit_threshold": float(exit_),
                        "hold_max": int(hold_max),
                        "trades": int(metrics["trades"]),
                        "win_rate": float(metrics["win_rate"]),
                        "avg_trade_return_pct": float(metrics["avg_trade_return_pct"]),
                        "total_return_pct": float(metrics["total_return_pct"]),
                        "sharpe": float(metrics["sharpe"]),
                        "max_drawdown_pct": float(metrics["max_drawdown_pct"]),
                        "mean_bar_return": float(metrics["mean_bar_return"]),
                        "volatility": float(metrics["volatility"]),
                        "edge_bps": float(metrics["edge_bps"]),
                        "score": float(score),
                        "baseline_return_pct": float(baseline["total_return_pct"]),
                        "baseline_drawdown_pct": float(baseline["max_drawdown_pct"]),
                        "baseline_volatility": float(baseline["volatility"]),
                        "baseline_edge_bps": float(baseline_edge_bps),
                    }
                )
    return out


def strategy_payloads(
    series_map: Dict[str, List[float]],
    entries: List[float],
    exits: List[float],
    holds: List[int],
) -> List[Dict[str, Any]]:
    payloads: List[Dict[str, Any]] = []
    for series_name, returns in series_map.items():
        if len(returns) < 120:
            continue
        baseline = bar_metrics(returns)
        for algo_name, algo_fn in ALGO_MAP.items():
            signal = algo_fn(returns)
            payloads.append(
                {
                    "series_name": series_name,
                    "algo_name": algo_name,
                    "returns": returns,
                    "signal": signal,
                    "entries": entries,
                    "exits": exits,
                    "holds": holds,
                    "baseline": baseline,
                }
            )
    return payloads


def setup_db(path: Path) -> sqlite3.Connection:
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(path)
    cur = conn.cursor()
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS api_constraints (
            generated_utc TEXT,
            source TEXT,
            sector TEXT,
            key_present INTEGER,
            probe_supported INTEGER,
            probe_ok INTEGER,
            http_status INTEGER,
            latency_ms REAL,
            measured_rows INTEGER,
            constraint_level TEXT,
            constraint_reason TEXT
        )
        """
    )
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS strategy_trials (
            generated_utc TEXT,
            series TEXT,
            algo TEXT,
            entry_threshold REAL,
            exit_threshold REAL,
            hold_max INTEGER,
            trades INTEGER,
            win_rate REAL,
            avg_trade_return_pct REAL,
            total_return_pct REAL,
            sharpe REAL,
            max_drawdown_pct REAL,
            mean_bar_return REAL,
            volatility REAL,
            edge_bps REAL,
            score REAL,
            baseline_return_pct REAL,
            baseline_drawdown_pct REAL,
            baseline_volatility REAL
        )
        """
    )
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS run_summary (
            generated_utc TEXT,
            series_count INTEGER,
            trial_count INTEGER,
            critical_constraints INTEGER,
            high_constraints INTEGER,
            edge_uplift_bps REAL,
            drawdown_saved_pct REAL,
            volatility_reduction_pct REAL,
            note TEXT
        )
        """
    )
    conn.commit()
    return conn


def insert_constraints(conn: sqlite3.Connection, generated_utc: str, rows: List[Dict[str, Any]]) -> None:
    cur = conn.cursor()
    cur.executemany(
        """
        INSERT INTO api_constraints (
            generated_utc, source, sector, key_present, probe_supported, probe_ok,
            http_status, latency_ms, measured_rows, constraint_level, constraint_reason
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        [
            (
                generated_utc,
                row.get("source"),
                row.get("sector"),
                1 if row.get("key_present") else 0,
                1 if row.get("probe_supported") else 0,
                1 if row.get("probe_ok") else 0,
                row.get("http_status"),
                row.get("latency_ms"),
                row.get("measured_rows"),
                row.get("constraint_level"),
                row.get("constraint_reason"),
            )
            for row in rows
        ],
    )
    conn.commit()


def insert_trials(conn: sqlite3.Connection, generated_utc: str, rows: List[Dict[str, Any]]) -> None:
    cur = conn.cursor()
    cur.executemany(
        """
        INSERT INTO strategy_trials (
            generated_utc, series, algo, entry_threshold, exit_threshold, hold_max, trades,
            win_rate, avg_trade_return_pct, total_return_pct, sharpe, max_drawdown_pct,
            mean_bar_return, volatility, edge_bps, score,
            baseline_return_pct, baseline_drawdown_pct, baseline_volatility
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        [
            (
                generated_utc,
                row.get("series"),
                row.get("algo"),
                row.get("entry_threshold"),
                row.get("exit_threshold"),
                row.get("hold_max"),
                row.get("trades"),
                row.get("win_rate"),
                row.get("avg_trade_return_pct"),
                row.get("total_return_pct"),
                row.get("sharpe"),
                row.get("max_drawdown_pct"),
                row.get("mean_bar_return"),
                row.get("volatility"),
                row.get("edge_bps"),
                row.get("score"),
                row.get("baseline_return_pct"),
                row.get("baseline_drawdown_pct"),
                row.get("baseline_volatility"),
            )
            for row in rows
        ],
    )
    conn.commit()


def write_report(path: Path, summary: Dict[str, Any]) -> None:
    lines: List[str] = []
    lines.append("# Alpha Harmonic Burst Lab")
    lines.append("")
    lines.append(f"Generated UTC: {summary.get('generated_utc')}")
    lines.append("")
    lines.append("## Constraint Snapshot")
    lines.append("")
    c = summary.get("constraint_summary", {})
    lines.append(f"- Providers scanned: {c.get('providers_scanned', 0)}")
    lines.append(f"- Critical constraints: {c.get('critical', 0)}")
    lines.append(f"- High constraints: {c.get('high', 0)}")
    lines.append(f"- Healthy probes: {c.get('healthy', 0)}")
    lines.append("")
    lines.append("## Strategy Burst Snapshot")
    lines.append("")
    b = summary.get("burst_summary", {})
    lines.append(f"- Series used: {b.get('series_used', 0)}")
    lines.append(f"- Total strategy trials: {b.get('trial_count', 0)}")
    lines.append(f"- Worker processes: {b.get('workers_used', 0)}")
    lines.append("")
    p = summary.get("proof_of_savings", {})
    lines.append("## Proof of Savings")
    lines.append("")
    lines.append(f"- Edge uplift (bps): {p.get('edge_uplift_bps', 0.0):.2f}")
    lines.append(f"- Drawdown saved (pct points): {p.get('drawdown_saved_pct', 0.0):.2f}")
    lines.append(f"- Volatility reduction (%): {p.get('volatility_reduction_pct', 0.0):.2f}")
    lines.append("")
    lines.append("## Top Strategy")
    lines.append("")
    best = summary.get("best_strategy") or {}
    if best:
        lines.append(f"- Series: {best.get('series')}")
        lines.append(f"- Algo: {best.get('algo')}")
        lines.append(f"- Entry threshold: {best.get('entry_threshold')}")
        lines.append(f"- Exit threshold: {best.get('exit_threshold')}")
        lines.append(f"- Hold max: {best.get('hold_max')}")
        lines.append(f"- Total return (%): {best.get('total_return_pct', 0.0):.2f}")
        lines.append(f"- Sharpe: {best.get('sharpe', 0.0):.3f}")
        lines.append(f"- Max drawdown (%): {best.get('max_drawdown_pct', 0.0):.2f}")
    else:
        lines.append("- No valid strategy candidate.")
    lines.append("")
    lines.append("## Compliance Note")
    lines.append("")
    lines.append("- This output is research and optimization evidence, not a guarantee of profit.")
    lines.append("- Live capital deployment must remain risk-capped and supervised.")

    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description="Run live constraint probing + CPU burst harmonic strategy research.")
    parser.add_argument("--max-series", type=int, default=14, help="Maximum number of external CSV series to include.")
    parser.add_argument("--workers", type=int, default=max(2, (os.cpu_count() or 8) - 1), help="Process workers for burst search.")
    parser.add_argument("--max-top", type=int, default=20, help="Number of top strategies saved in summary output.")
    args = parser.parse_args()

    generated_utc = now_utc()
    env_map = parse_env_files(KEY_FILES)
    registry_data = read_json(REGISTRY_FILE, {"rows": []})
    registry_rows = registry_data.get("rows", []) if isinstance(registry_data, dict) else []

    constraints: List[Dict[str, Any]] = []
    with ThreadPoolExecutor(max_workers=8) as pool:
        futures = [pool.submit(evaluate_provider_constraint, row, env_map) for row in registry_rows if isinstance(row, dict)]
        for future in as_completed(futures):
            try:
                constraints.append(future.result())
            except Exception:
                continue
    constraints.sort(key=lambda x: str(x.get("source", "")))

    trade_returns = load_trade_returns(TRADE_LOG_FILE)
    csv_series = load_csv_return_series(DATA_DIR, max_files=max(1, args.max_series), max_len=6000)
    series_map: Dict[str, List[float]] = {}

    if len(trade_returns) >= 120:
        series_map["trade_log_live"] = trade_returns
    for name, values in csv_series.items():
        if len(values) >= 120:
            series_map[name] = values

    entries = [0.12, 0.2, 0.3, 0.42]
    exits = [-0.28, -0.16, -0.08]
    holds = [12, 20, 34]
    payloads = strategy_payloads(series_map, entries, exits, holds)

    all_trials: List[Dict[str, Any]] = []
    workers_used = max(1, int(args.workers))
    if payloads:
        with ProcessPoolExecutor(max_workers=workers_used) as pool:
            future_map = [pool.submit(evaluate_series_algo, payload) for payload in payloads]
            for future in as_completed(future_map):
                try:
                    all_trials.extend(future.result())
                except Exception:
                    continue

    all_trials.sort(key=lambda x: float(x.get("score", 0.0)), reverse=True)
    top = all_trials[: max(1, int(args.max_top))]
    best = top[0] if top else {}

    proof = {
        "edge_uplift_bps": 0.0,
        "drawdown_saved_pct": 0.0,
        "volatility_reduction_pct": 0.0,
    }
    if best:
        proof["edge_uplift_bps"] = float(best.get("edge_bps", 0.0) - float(best.get("baseline_edge_bps", 0.0)))
        proof["drawdown_saved_pct"] = float(best.get("baseline_drawdown_pct", 0.0) - best.get("max_drawdown_pct", 0.0))
        base_vol = float(best.get("baseline_volatility", 0.0))
        if base_vol > 1e-12:
            proof["volatility_reduction_pct"] = ((base_vol - float(best.get("volatility", 0.0))) / base_vol) * 100.0

    critical = sum(1 for c in constraints if c.get("constraint_level") == "CRITICAL")
    high = sum(1 for c in constraints if c.get("constraint_level") == "HIGH")
    healthy = sum(1 for c in constraints if c.get("constraint_level") == "LOW")

    summary = {
        "generated_utc": generated_utc,
        "schema": "alpha_harmonic_burst_lab_v1",
        "objective": "Find stronger edge candidates, map live API constraints, and publish proof-of-savings research artifacts.",
        "constraint_summary": {
            "providers_scanned": len(constraints),
            "critical": critical,
            "high": high,
            "healthy": healthy,
        },
        "burst_summary": {
            "series_used": len(series_map),
            "trial_count": len(all_trials),
            "workers_used": workers_used,
            "entries": entries,
            "exits": exits,
            "holds": holds,
        },
        "proof_of_savings": {
            "edge_uplift_bps": round(float(proof["edge_uplift_bps"]), 2),
            "drawdown_saved_pct": round(float(proof["drawdown_saved_pct"]), 2),
            "volatility_reduction_pct": round(float(proof["volatility_reduction_pct"]), 2),
        },
        "best_strategy": best,
        "top_strategies": top,
        "database": str(DB_FILE),
        "constraints_file": str(CONSTRAINT_FILE),
        "report_file": str(REPORT_FILE),
        "guardrail": "Research output only. No guarantee of profit. Keep risk controls active.",
    }

    write_json(CONSTRAINT_FILE, {
        "generated_utc": generated_utc,
        "schema": "live_api_constraint_probe_v1",
        "rows": constraints,
    })
    write_json(SUMMARY_FILE, summary)
    write_report(REPORT_FILE, summary)

    conn = setup_db(DB_FILE)
    try:
        insert_constraints(conn, generated_utc, constraints)
        insert_trials(conn, generated_utc, all_trials)
        conn.execute(
            """
            INSERT INTO run_summary (
                generated_utc, series_count, trial_count, critical_constraints, high_constraints,
                edge_uplift_bps, drawdown_saved_pct, volatility_reduction_pct, note
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                generated_utc,
                len(series_map),
                len(all_trials),
                critical,
                high,
                float(summary["proof_of_savings"]["edge_uplift_bps"]),
                float(summary["proof_of_savings"]["drawdown_saved_pct"]),
                float(summary["proof_of_savings"]["volatility_reduction_pct"]),
                summary["guardrail"],
            ),
        )
        conn.commit()
    finally:
        conn.close()

    print("alpha_harmonic_burst_lab complete")
    print(f"constraints={len(constraints)}")
    print(f"series_used={len(series_map)}")
    print(f"trial_count={len(all_trials)}")
    print(f"summary={SUMMARY_FILE}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
