import argparse
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List

import numpy as np
try:
    import empyrical as ep
except Exception:
    ep = None

try:
    import orjson
except Exception:
    orjson = None


ROOT = Path(r"c:/LumaTrader/INSTITUTIONAL_STACK_V2")
TRADE_LOG_DEFAULT = ROOT / "out" / "execution" / "trade_log.json"
OUT_JSON_DEFAULT = ROOT / "out" / "execution" / "investor_performance_report.json"
OUT_MD_DEFAULT = ROOT / "out" / "execution" / "investor_performance_report.md"


def load_json(path: Path) -> Any:
    if not path.exists():
        return []
    raw = path.read_bytes()
    if orjson is not None:
        return orjson.loads(raw)
    import json
    return json.loads(raw.decode("utf-8"))


def dump_json(path: Path, payload: Dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if orjson is not None:
        path.write_bytes(orjson.dumps(payload, option=orjson.OPT_INDENT_2))
        return
    import json
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def closed_rows(rows: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    out: List[Dict[str, Any]] = []
    for row in rows:
        if not isinstance(row, dict):
            continue
        if str(row.get("status", "")).upper() != "CLOSED":
            continue
        out.append(row)
    return out


def as_float(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except Exception:
        return float(default)


def _native_max_drawdown(returns: np.ndarray) -> float:
    if returns.size == 0:
        return 0.0
    equity = np.cumprod(1.0 + returns)
    running_max = np.maximum.accumulate(equity)
    drawdowns = (equity / np.maximum(running_max, 1e-12)) - 1.0
    return float(np.min(drawdowns)) if drawdowns.size else 0.0


def _native_sharpe(returns: np.ndarray, annualization: float = 365.0) -> float:
    if returns.size < 2:
        return 0.0
    mean = float(np.mean(returns))
    std = float(np.std(returns, ddof=1))
    if abs(std) <= 1e-12:
        return 0.0
    return float((mean / std) * np.sqrt(annualization))


def _native_sortino(returns: np.ndarray, annualization: float = 365.0) -> float:
    if returns.size < 2:
        return 0.0
    mean = float(np.mean(returns))
    downside = returns[returns < 0.0]
    if downside.size < 1:
        return 0.0
    downside_std = float(np.std(downside, ddof=1)) if downside.size > 1 else abs(float(downside[0]))
    if abs(downside_std) <= 1e-12:
        return 0.0
    return float((mean / downside_std) * np.sqrt(annualization))


def _native_calmar(returns: np.ndarray) -> float:
    if returns.size == 0:
        return 0.0
    cumulative = float(np.prod(1.0 + returns) - 1.0)
    max_dd = abs(_native_max_drawdown(returns))
    if max_dd <= 1e-12:
        return 0.0
    return float(cumulative / max_dd)


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate investor-grade performance summary from trade log.")
    parser.add_argument("--trade-log", default=str(TRADE_LOG_DEFAULT))
    parser.add_argument("--out-json", default=str(OUT_JSON_DEFAULT))
    parser.add_argument("--out-md", default=str(OUT_MD_DEFAULT))
    args = parser.parse_args()

    rows = load_json(Path(args.trade_log))
    rows = closed_rows(rows if isinstance(rows, list) else [])

    net_pct = np.array([as_float(r.get("net_pnl_pct", 0.0)) for r in rows], dtype=float)
    gross_pct = np.array([as_float(r.get("pnl_pct", 0.0)) for r in rows], dtype=float)
    fee_usd = np.array([as_float(r.get("round_trip_fee_usd", 0.0)) for r in rows], dtype=float)
    size_usd = np.array([max(1e-9, as_float(r.get("size_usd", 0.0), 1e-9)) for r in rows], dtype=float)

    net_returns = net_pct / 100.0

    if net_returns.size >= 2 and ep is not None:
        sharpe = float(ep.sharpe_ratio(net_returns, annualization=365.0) or 0.0)
        sortino = float(ep.sortino_ratio(net_returns, annualization=365.0) or 0.0)
        calmar = float(ep.calmar_ratio(net_returns) or 0.0)
        max_dd = float(ep.max_drawdown(net_returns) or 0.0)
    elif net_returns.size >= 2:
        sharpe = _native_sharpe(net_returns, annualization=365.0)
        sortino = _native_sortino(net_returns, annualization=365.0)
        calmar = _native_calmar(net_returns)
        max_dd = _native_max_drawdown(net_returns)
    else:
        sharpe = 0.0
        sortino = 0.0
        calmar = 0.0
        max_dd = 0.0

    win_rate = float((net_pct > 0.0).mean() * 100.0) if net_pct.size else 0.0
    avg_net = float(net_pct.mean()) if net_pct.size else 0.0
    median_net = float(np.median(net_pct)) if net_pct.size else 0.0
    total_net_pct = float(net_pct.sum()) if net_pct.size else 0.0
    total_fees_usd = float(fee_usd.sum()) if fee_usd.size else 0.0
    fee_drag_pct_avg = float(np.mean((fee_usd / size_usd) * 100.0)) if fee_usd.size else 0.0

    closed_trades = int(net_pct.size)
    if closed_trades >= 100:
        sample_quality_tier = "institutional"
        sample_confidence_note = "High confidence sample size for investor-facing performance claims."
    elif closed_trades >= 25:
        sample_quality_tier = "pilot"
        sample_confidence_note = "Moderate confidence; suitable for pilot-stage performance discussion."
    elif closed_trades >= 10:
        sample_quality_tier = "limited"
        sample_confidence_note = "Limited confidence; metrics are directional only."
    else:
        sample_quality_tier = "insufficient"
        sample_confidence_note = "Insufficient sample size for strong performance claims; continue accumulating live trades."

    payload = {
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "closed_trades": closed_trades,
        "sample_quality_tier": sample_quality_tier,
        "sample_confidence_note": sample_confidence_note,
        "win_rate_pct": round(win_rate, 3),
        "avg_net_pnl_pct": round(avg_net, 6),
        "median_net_pnl_pct": round(median_net, 6),
        "total_net_pnl_pct": round(total_net_pct, 6),
        "total_round_trip_fees_usd": round(total_fees_usd, 6),
        "avg_fee_drag_pct_per_trade": round(fee_drag_pct_avg, 6),
        "sharpe": round(sharpe, 6),
        "sortino": round(sortino, 6),
        "calmar": round(calmar, 6),
        "max_drawdown": round(max_dd, 6),
        "source_trade_log": str(Path(args.trade_log)),
    }

    md = f"""# Investor Performance Report\n\n- Generated: {payload['timestamp_utc']}\n- Closed trades: {payload['closed_trades']}\n- Sample quality tier: {payload['sample_quality_tier']}\n- Confidence note: {payload['sample_confidence_note']}\n- Win rate: {payload['win_rate_pct']}%\n- Avg net P&L per trade: {payload['avg_net_pnl_pct']}%\n- Median net P&L per trade: {payload['median_net_pnl_pct']}%\n- Total net P&L (% sum): {payload['total_net_pnl_pct']}%\n- Total round-trip fees: ${payload['total_round_trip_fees_usd']}\n- Avg fee drag per trade: {payload['avg_fee_drag_pct_per_trade']}%\n- Sharpe: {payload['sharpe']}\n- Sortino: {payload['sortino']}\n- Calmar: {payload['calmar']}\n- Max Drawdown: {payload['max_drawdown']}\n"""

    dump_json(Path(args.out_json), payload)
    Path(args.out_md).write_text(md, encoding="utf-8")

    print("investor performance report generated")
    print(f"closed_trades={payload['closed_trades']}")
    print(f"out_json={args.out_json}")
    print(f"out_md={args.out_md}")


if __name__ == "__main__":
    main()
