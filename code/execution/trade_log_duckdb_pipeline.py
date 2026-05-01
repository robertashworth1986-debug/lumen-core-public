import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List

import duckdb
import polars as pl

try:
    import msgspec
except Exception:
    msgspec = None


ROOT = Path(r"c:/LumaTrader/INSTITUTIONAL_STACK_V2")
TRADE_LOG_DEFAULT = ROOT / "out" / "execution" / "trade_log.json"
OUT_DIR_DEFAULT = ROOT / "out" / "execution" / "analytics"
PARQUET_DEFAULT = OUT_DIR_DEFAULT / "trade_log.parquet"
KPI_JSON_DEFAULT = OUT_DIR_DEFAULT / "investor_kpi_duckdb.json"
KPI_MD_DEFAULT = OUT_DIR_DEFAULT / "investor_kpi_duckdb.md"
DB_DEFAULT = OUT_DIR_DEFAULT / "luma_analytics.duckdb"
LIVE_LEDGER_JSONL_DEFAULT = ROOT / "out" / "execution" / "live_trade_ledger.jsonl"
PAPER_LEDGER_JSONL_DEFAULT = ROOT / "out" / "execution" / "multi_exchange_trade_ledger.jsonl"
LIVE_EXECUTOR_HEARTBEAT_DEFAULT = ROOT / "out" / "execution" / "live_executor_heartbeat.json"
LIVE_ENGINE_HEARTBEAT_DEFAULT = ROOT / "out" / "execution" / "live_engine_heartbeat.json"
PAPER_TICKER_STATUS_DEFAULT = ROOT / "out" / "execution" / "multi_exchange_paper_ticker_status.json"
KPI_SCHEMA_VERSION = "1.2.0"
RUNTIME_STATUS_SCHEMA_VERSION = "1.0.0"
LEDGER_SCHEMA_EXPECTED = "1.1.0"


def load_trade_log(path: Path) -> List[Dict[str, Any]]:
    if not path.exists():
        return []
    raw = path.read_bytes()
    payload: Any
    if msgspec is not None:
        payload = msgspec.json.decode(raw)
    else:
        payload = json.loads(raw.decode("utf-8"))
    if isinstance(payload, list):
        return [row for row in payload if isinstance(row, dict)]
    return []


def load_json(path: Path, default: Any) -> Any:
    try:
        if not path.exists():
            return default
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return default


def load_trade_jsonl(path: Path) -> List[Dict[str, Any]]:
    if not path.exists():
        return []
    out: List[Dict[str, Any]] = []
    try:
        for raw in path.read_text(encoding="utf-8", errors="ignore").splitlines():
            line = raw.strip()
            if not line:
                continue
            try:
                row = json.loads(line)
            except Exception:
                continue
            if isinstance(row, dict):
                out.append(row)
    except Exception:
        return []
    return out


def load_unified_rows(trade_log_path: Path, live_ledger_path: Path, paper_ledger_path: Path) -> List[Dict[str, Any]]:
    rows = load_trade_log(trade_log_path)
    if rows:
        return rows

    unified: List[Dict[str, Any]] = []
    for row in load_trade_jsonl(live_ledger_path):
        unified.append(
            {
                "timestamp": row.get("timestamp") or row.get("logged_utc") or "",
                "txid": row.get("txid", ""),
                "exchange": "kraken",
                "symbol": row.get("symbol", ""),
                "pair": row.get("pair", ""),
                "direction": row.get("direction", ""),
                "side": row.get("side", ""),
                "status": row.get("status", ""),
                "execution_mode": row.get("execution_mode", ""),
                "close_reason": row.get("close_reason", ""),
                "gate_score": row.get("gate_score", 0.0),
                "entry_price": row.get("entry_price", 0.0),
                "exit_price": row.get("exit_price", 0.0),
                "qty": row.get("qty", 0.0),
                "size_usd": row.get("size_usd", 0.0),
                "pnl": row.get("pnl", row.get("net_pnl", 0.0)),
                "pnl_pct": row.get("pnl_pct", row.get("net_pnl_pct", 0.0)),
                "net_pnl": row.get("net_pnl", row.get("pnl", 0.0)),
                "net_pnl_pct": row.get("net_pnl_pct", row.get("pnl_pct", 0.0)),
                "round_trip_fee_usd": row.get("round_trip_fee_usd", 0.0),
                "hold_seconds_actual": row.get("hold_seconds_actual", 0.0),
                "tp_net_bps": row.get("tp_net_bps", 0.0),
                "sl_net_bps": row.get("sl_net_bps", 0.0),
            }
        )

    for row in load_trade_jsonl(paper_ledger_path):
        unified.append(
            {
                "timestamp": row.get("timestamp") or row.get("logged_utc") or "",
                "txid": row.get("txid", ""),
                "exchange": row.get("exchange", "binanceus_paper"),
                "symbol": row.get("symbol", ""),
                "pair": row.get("pair", ""),
                "direction": row.get("direction", ""),
                "side": row.get("side", ""),
                "status": row.get("status", ""),
                "execution_mode": row.get("execution_mode", ""),
                "close_reason": row.get("close_reason", ""),
                "gate_score": row.get("gate_score", 0.0),
                "entry_price": row.get("entry_price", 0.0),
                "exit_price": row.get("exit_price", 0.0),
                "qty": row.get("qty", 0.0),
                "size_usd": row.get("size_usd", 0.0),
                "pnl": row.get("pnl", row.get("net_pnl", 0.0)),
                "pnl_pct": row.get("pnl_pct", row.get("net_pnl_pct", 0.0)),
                "net_pnl": row.get("net_pnl", row.get("pnl", 0.0)),
                "net_pnl_pct": row.get("net_pnl_pct", row.get("pnl_pct", 0.0)),
                "round_trip_fee_usd": row.get("round_trip_fee_usd", 0.0),
                "hold_seconds_actual": row.get("hold_seconds_actual", 0.0),
                "tp_net_bps": row.get("tp_net_bps", 0.0),
                "sl_net_bps": row.get("sl_net_bps", 0.0),
            }
        )

    return unified


def normalize_rows(rows: List[Dict[str, Any]]) -> pl.DataFrame:
    normalized: List[Dict[str, Any]] = []
    for row in rows:
        normalized.append(
            {
                "timestamp": str(row.get("timestamp", "")),
                "txid": str(row.get("txid", "")),
                "exchange": str(row.get("exchange", "")),
                "symbol": str(row.get("symbol", "")),
                "pair": str(row.get("pair", "")),
                "direction": str(row.get("direction", "")),
                "side": str(row.get("side", "")),
                "status": str(row.get("status", "")),
                "execution_mode": str(row.get("execution_mode", "")),
                "close_reason": str(row.get("close_reason", "")),
                "gate_score": float(row.get("gate_score", 0.0) or 0.0),
                "entry_price": float(row.get("entry_price", 0.0) or 0.0),
                "exit_price": float(row.get("exit_price", 0.0) or 0.0),
                "qty": float(row.get("qty", 0.0) or 0.0),
                "size_usd": float(row.get("size_usd", 0.0) or 0.0),
                "pnl": float(row.get("pnl", 0.0) or 0.0),
                "pnl_pct": float(row.get("pnl_pct", 0.0) or 0.0),
                "net_pnl": float(row.get("net_pnl", 0.0) or 0.0),
                "net_pnl_pct": float(row.get("net_pnl_pct", 0.0) or 0.0),
                "round_trip_fee_usd": float(row.get("round_trip_fee_usd", 0.0) or 0.0),
                "hold_seconds_actual": float(row.get("hold_seconds_actual", 0.0) or 0.0),
                "tp_net_bps": float(row.get("tp_net_bps", 0.0) or 0.0),
                "sl_net_bps": float(row.get("sl_net_bps", 0.0) or 0.0),
            }
        )
    if not normalized:
        return pl.DataFrame(
            {
                "timestamp": [],
                "txid": [],
                "exchange": [],
                "symbol": [],
                "pair": [],
                "direction": [],
                "side": [],
                "status": [],
                "execution_mode": [],
                "close_reason": [],
                "gate_score": [],
                "entry_price": [],
                "exit_price": [],
                "qty": [],
                "size_usd": [],
                "pnl": [],
                "pnl_pct": [],
                "net_pnl": [],
                "net_pnl_pct": [],
                "round_trip_fee_usd": [],
                "hold_seconds_actual": [],
                "tp_net_bps": [],
                "sl_net_bps": [],
            }
        )
    return pl.DataFrame(normalized)


def compute_kpis(db_path: Path, parquet_path: Path) -> Dict[str, Any]:
    con = duckdb.connect(str(db_path))
    con.execute("CREATE OR REPLACE TABLE trade_log AS SELECT * FROM read_parquet(?)", [str(parquet_path)])

    closed = con.execute(
        """
        SELECT
          COUNT(*) AS n,
          COALESCE(SUM(net_pnl_pct), 0.0) AS total_net_pnl_pct,
          COALESCE(AVG(net_pnl_pct), 0.0) AS avg_net_pnl_pct,
          COALESCE(MEDIAN(net_pnl_pct), 0.0) AS median_net_pnl_pct,
          COALESCE(SUM(round_trip_fee_usd), 0.0) AS total_fees_usd,
          COALESCE(AVG(CASE WHEN size_usd > 0 THEN (round_trip_fee_usd/size_usd)*100.0 ELSE 0.0 END), 0.0) AS avg_fee_drag_pct,
          COALESCE(AVG(CASE WHEN net_pnl_pct > 0 THEN 1.0 ELSE 0.0 END)*100.0, 0.0) AS win_rate_pct,
          COALESCE(AVG(gate_score), 0.0) AS avg_gate_score,
          COALESCE(AVG(hold_seconds_actual), 0.0) AS avg_hold_seconds
        FROM trade_log
        WHERE UPPER(status) = 'CLOSED'
        """
    ).fetchone()

    n = int(closed[0] or 0)
    total_net_pnl_pct = float(closed[1] or 0.0)
    avg_net_pnl_pct = float(closed[2] or 0.0)
    median_net_pnl_pct = float(closed[3] or 0.0)
    total_fees_usd = float(closed[4] or 0.0)
    avg_fee_drag_pct = float(closed[5] or 0.0)
    win_rate_pct = float(closed[6] or 0.0)
    avg_gate_score = float(closed[7] or 0.0)
    avg_hold_seconds = float(closed[8] or 0.0)

    std_net = con.execute(
        "SELECT COALESCE(STDDEV_SAMP(net_pnl_pct), 0.0) FROM trade_log WHERE UPPER(status)='CLOSED'"
    ).fetchone()[0]
    std_net = float(std_net or 0.0)

    sharpe_proxy = 0.0
    if n >= 2 and abs(std_net) > 1e-12:
        sharpe_proxy = (avg_net_pnl_pct / std_net) * (365.0 ** 0.5)

    downside_std = con.execute(
        """
        SELECT COALESCE(STDDEV_SAMP(CASE WHEN net_pnl_pct < 0 THEN net_pnl_pct END), 0.0)
        FROM trade_log
        WHERE UPPER(status)='CLOSED'
        """
    ).fetchone()[0]
    downside_std = float(downside_std or 0.0)
    sortino_proxy = 0.0
    if n >= 2 and abs(downside_std) > 1e-12:
        sortino_proxy = (avg_net_pnl_pct / downside_std) * (365.0 ** 0.5)

    rows = con.execute(
        """
        SELECT net_pnl_pct
        FROM trade_log
        WHERE UPPER(status)='CLOSED'
        ORDER BY timestamp
        """
    ).fetchall()
    equity = 1.0
    peak = 1.0
    max_drawdown = 0.0
    for (value,) in rows:
        ret = float(value or 0.0) / 100.0
        equity *= (1.0 + ret)
        if equity > peak:
            peak = equity
        dd = (equity / peak) - 1.0
        if dd < max_drawdown:
            max_drawdown = dd

    if n >= 100:
        sample_quality_tier = "institutional"
        sample_confidence_note = "High confidence sample size for investor-facing KPI use."
    elif n >= 25:
        sample_quality_tier = "pilot"
        sample_confidence_note = "Moderate confidence; suitable for pilot performance narrative."
    elif n >= 10:
        sample_quality_tier = "limited"
        sample_confidence_note = "Directional only; continue accumulating live observations."
    else:
        sample_quality_tier = "insufficient"
        sample_confidence_note = "Too few closed trades for robust KPI interpretation."

    result = {
        "schema_version": KPI_SCHEMA_VERSION,
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "closed_trades": n,
        "sample_quality_tier": sample_quality_tier,
        "sample_confidence_note": sample_confidence_note,
        "total_net_pnl_pct": round(total_net_pnl_pct, 6),
        "avg_net_pnl_pct": round(avg_net_pnl_pct, 6),
        "median_net_pnl_pct": round(median_net_pnl_pct, 6),
        "total_round_trip_fees_usd": round(total_fees_usd, 6),
        "avg_fee_drag_pct_per_trade": round(avg_fee_drag_pct, 6),
        "win_rate_pct": round(win_rate_pct, 6),
        "avg_gate_score": round(avg_gate_score, 6),
        "avg_hold_seconds": round(avg_hold_seconds, 6),
        "sharpe_proxy": round(float(sharpe_proxy), 6),
        "sortino_proxy": round(float(sortino_proxy), 6),
        "max_drawdown": round(float(max_drawdown), 6),
        "data_sources": {
            "parquet": str(parquet_path),
            "duckdb": str(db_path),
        },
    }
    con.close()
    return result


def _safe_float(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except Exception:
        return default


def build_runtime_status(
    kpi: Dict[str, Any],
    live_executor_heartbeat_path: Path,
    live_engine_heartbeat_path: Path,
    paper_ticker_status_path: Path,
    runtime_status_path: Path,
) -> Dict[str, Any]:
    live_executor_hb = load_json(live_executor_heartbeat_path, {})
    live_engine_hb = load_json(live_engine_heartbeat_path, {})
    paper_status = load_json(paper_ticker_status_path, {})

    binance_engine = paper_status.get("binanceus_paper_engine", {}) if isinstance(paper_status, dict) else {}
    paper_state = binance_engine.get("state", {}) if isinstance(binance_engine, dict) else {}

    payload = {
        "schema_version": RUNTIME_STATUS_SCHEMA_VERSION,
        "generated_utc": datetime.now(timezone.utc).isoformat(),
        "kpi": {
            "schema_version": kpi.get("schema_version", KPI_SCHEMA_VERSION),
            "closed_trades": int(kpi.get("closed_trades", 0) or 0),
            "sample_quality_tier": str(kpi.get("sample_quality_tier", "unknown")),
            "total_net_pnl_pct": _safe_float(kpi.get("total_net_pnl_pct", 0.0)),
            "win_rate_pct": _safe_float(kpi.get("win_rate_pct", 0.0)),
            "max_drawdown": _safe_float(kpi.get("max_drawdown", 0.0)),
            "sharpe_proxy": _safe_float(kpi.get("sharpe_proxy", 0.0)),
        },
        "live_lane": {
            "executor_heartbeat_file": str(live_executor_heartbeat_path),
            "engine_heartbeat_file": str(live_engine_heartbeat_path),
            "executor": {
                "status": str(live_executor_hb.get("status", "unknown")),
                "reason": str(live_executor_hb.get("reason", "")),
                "symbol": str(live_executor_hb.get("symbol", "")),
                "timestamp_utc": str(live_executor_hb.get("timestamp_utc", "")),
                "schema_version": str(live_executor_hb.get("schema_version", "unknown")),
            },
            "engine": {
                "status": str(live_engine_hb.get("status", "unknown")),
                "stream_brief": str(live_engine_hb.get("stream_brief", "")),
                "timestamp_utc": str(live_engine_hb.get("timestamp_utc", "")),
                "schema_version": str(live_engine_hb.get("schema_version", "unknown")),
            },
        },
        "paper_lane": {
            "ticker_status_file": str(paper_ticker_status_path),
            "profile": str(paper_status.get("profile", "")),
            "cycle": int(paper_status.get("cycle", 0) or 0),
            "timestamp_utc": str(paper_status.get("timestamp_utc", "")),
            "equity_usd": _safe_float(paper_state.get("equity_usd", 0.0)),
            "cash_usd": _safe_float(paper_state.get("cash_usd", 0.0)),
            "open_positions": int(len(paper_state.get("positions", {}))) if isinstance(paper_state.get("positions", {}), dict) else 0,
        },
        "schema_contract": {
            "ledger_schema_expected": LEDGER_SCHEMA_EXPECTED,
            "kpi_schema": KPI_SCHEMA_VERSION,
            "runtime_status_schema": RUNTIME_STATUS_SCHEMA_VERSION,
        },
    }

    runtime_status_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return payload


def write_outputs(kpi: Dict[str, Any], json_path: Path, md_path: Path) -> None:
    json_path.parent.mkdir(parents=True, exist_ok=True)
    json_path.write_text(json.dumps(kpi, indent=2), encoding="utf-8")

    md = (
        "# LumaCore DuckDB Investor KPI\n\n"
        f"- Generated: {kpi['timestamp_utc']}\n"
        f"- Closed trades: {kpi['closed_trades']}\n"
        f"- Sample quality tier: {kpi['sample_quality_tier']}\n"
        f"- Confidence note: {kpi['sample_confidence_note']}\n"
        f"- Total net P&L (%): {kpi['total_net_pnl_pct']}\n"
        f"- Avg net P&L/trade (%): {kpi['avg_net_pnl_pct']}\n"
        f"- Median net P&L/trade (%): {kpi['median_net_pnl_pct']}\n"
        f"- Win rate (%): {kpi['win_rate_pct']}\n"
        f"- Total round-trip fees (USD): {kpi['total_round_trip_fees_usd']}\n"
        f"- Avg fee drag/trade (%): {kpi['avg_fee_drag_pct_per_trade']}\n"
        f"- Avg gate score: {kpi['avg_gate_score']}\n"
        f"- Avg hold seconds: {kpi['avg_hold_seconds']}\n"
        f"- Sharpe proxy: {kpi['sharpe_proxy']}\n"
        f"- Sortino proxy: {kpi['sortino_proxy']}\n"
        f"- Max drawdown: {kpi['max_drawdown']}\n"
    )
    md_path.write_text(md, encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description="Build Parquet + DuckDB KPI outputs from trade log.")
    parser.add_argument("--trade-log", default=str(TRADE_LOG_DEFAULT))
    parser.add_argument("--live-ledger-jsonl", default=str(LIVE_LEDGER_JSONL_DEFAULT))
    parser.add_argument("--paper-ledger-jsonl", default=str(PAPER_LEDGER_JSONL_DEFAULT))
    parser.add_argument("--live-executor-heartbeat", default=str(LIVE_EXECUTOR_HEARTBEAT_DEFAULT))
    parser.add_argument("--live-engine-heartbeat", default=str(LIVE_ENGINE_HEARTBEAT_DEFAULT))
    parser.add_argument("--paper-ticker-status", default=str(PAPER_TICKER_STATUS_DEFAULT))
    parser.add_argument("--out-dir", default=str(OUT_DIR_DEFAULT))
    args = parser.parse_args()

    trade_log_path = Path(args.trade_log)
    live_ledger_path = Path(args.live_ledger_jsonl)
    paper_ledger_path = Path(args.paper_ledger_jsonl)
    live_executor_heartbeat_path = Path(args.live_executor_heartbeat)
    live_engine_heartbeat_path = Path(args.live_engine_heartbeat)
    paper_ticker_status_path = Path(args.paper_ticker_status)
    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    parquet_path = out_dir / PARQUET_DEFAULT.name
    kpi_json = out_dir / KPI_JSON_DEFAULT.name
    kpi_md = out_dir / KPI_MD_DEFAULT.name
    db_path = out_dir / DB_DEFAULT.name
    runtime_status_json = out_dir / "investor_runtime_status.json"

    rows = load_unified_rows(trade_log_path, live_ledger_path, paper_ledger_path)
    frame = normalize_rows(rows)
    frame.write_parquet(parquet_path)

    kpi = compute_kpis(db_path=db_path, parquet_path=parquet_path)
    write_outputs(kpi, json_path=kpi_json, md_path=kpi_md)
    build_runtime_status(
        kpi=kpi,
        live_executor_heartbeat_path=live_executor_heartbeat_path,
        live_engine_heartbeat_path=live_engine_heartbeat_path,
        paper_ticker_status_path=paper_ticker_status_path,
        runtime_status_path=runtime_status_json,
    )

    print("duckdb pipeline complete")
    print(f"rows={len(rows)}")
    print(f"parquet={parquet_path}")
    print(f"kpi_json={kpi_json}")
    print(f"kpi_md={kpi_md}")
    print(f"runtime_status_json={runtime_status_json}")


if __name__ == "__main__":
    main()
