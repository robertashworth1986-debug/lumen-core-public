from __future__ import annotations

import argparse
import csv
import json
import statistics
import time
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def now_tag() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def parse_ts(value: Any) -> datetime | None:
    if not isinstance(value, str):
        return None
    text = value.strip()
    if not text:
        return None
    if text.endswith("Z"):
        text = text[:-1] + "+00:00"
    try:
        parsed = datetime.fromisoformat(text)
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def load_json(path: Path) -> Any:
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    if not path.exists():
        return records
    with path.open("r", encoding="utf-8", errors="ignore") as handle:
        for raw in handle:
            line = raw.strip()
            if not line:
                continue
            try:
                item = json.loads(line)
            except json.JSONDecodeError:
                continue
            if isinstance(item, dict):
                records.append(item)
    return records


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if not rows:
        path.write_text("", encoding="utf-8")
        return
    fieldnames = list(rows[0].keys())
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def number_stats(values: list[float]) -> dict[str, float | int | None]:
    if not values:
        return {"count": 0, "min": None, "max": None, "avg": None, "median": None}
    return {
        "count": len(values),
        "min": round(min(values), 6),
        "max": round(max(values), 6),
        "avg": round(sum(values) / len(values), 6),
        "median": round(statistics.median(values), 6),
    }


def counter_dict(counter: Counter[str]) -> dict[str, int]:
    return {key: int(value) for key, value in sorted(counter.items(), key=lambda kv: (-kv[1], kv[0]))}


def choose_timestamp(record: dict[str, Any], keys: list[str]) -> datetime | None:
    for key in keys:
        parsed = parse_ts(record.get(key))
        if parsed is not None:
            return parsed
    return None


def within_window(ts: datetime | None, start_utc: datetime, end_utc: datetime) -> bool:
    if ts is None:
        return False
    return start_utc <= ts <= end_utc


def collect_heartbeat_samples(
    heartbeat_path: Path,
    duration_sec: int,
    sample_interval_sec: float,
    verbose_progress: bool,
) -> tuple[list[dict[str, Any]], int, datetime, datetime]:
    samples: list[dict[str, Any]] = []
    seen_timestamps: set[str] = set()
    poll_iterations = 0
    window_start_utc = datetime.now(timezone.utc)

    while True:
        poll_iterations += 1
        payload = load_json(heartbeat_path)
        if isinstance(payload, dict):
            hb_timestamp = payload.get("timestamp_utc")
            if isinstance(hb_timestamp, str) and hb_timestamp and hb_timestamp not in seen_timestamps:
                seen_timestamps.add(hb_timestamp)
                reason_codes = payload.get("edge_proof_bootstrap_reason_codes", [])
                if isinstance(reason_codes, str):
                    reason_codes = [reason_codes]
                if not isinstance(reason_codes, list):
                    reason_codes = []
                reason_codes = [str(item) for item in reason_codes if str(item).strip()]

                sample = {
                    "timestamp_utc": hb_timestamp,
                    "status": str(payload.get("status", "")),
                    "reason": str(payload.get("reason", "")),
                    "symbol_source": str(payload.get("symbol_source", "")),
                    "selected_symbol": str(payload.get("selected_symbol", "")),
                    "selected_bootstrap_ready": bool(payload.get("selected_bootstrap_ready", False)),
                    "bootstrap_candidate_count": payload.get("bootstrap_candidate_count"),
                    "selected_spread_bps": payload.get("selected_spread_bps"),
                    "selected_momentum_pct": payload.get("selected_momentum_pct"),
                    "selected_hybrid_score": payload.get("selected_hybrid_score"),
                    "gate_expected_edge_bps": payload.get("gate_expected_edge_bps"),
                    "gate_composite_score": payload.get("gate_composite_score"),
                    "edge_proof_bootstrap_reason_codes": reason_codes,
                }
                samples.append(sample)
                if verbose_progress:
                    print(
                        "SAMPLE"
                        f" idx={len(samples)}"
                        f" ts={sample.get('timestamp_utc', '')}"
                        f" status={sample.get('status', '')}"
                        f" reason={sample.get('reason', '')}"
                        f" symbol={sample.get('selected_symbol', '')}"
                    )

        elapsed_sec = (datetime.now(timezone.utc) - window_start_utc).total_seconds()
        if elapsed_sec >= float(duration_sec):
            break

        if sample_interval_sec > 0:
            time.sleep(sample_interval_sec)

    window_end_utc = datetime.now(timezone.utc)
    if verbose_progress:
        print(
            "WINDOW_COMPLETE"
            f" polls={poll_iterations}"
            f" samples={len(samples)}"
            f" start={window_start_utc.isoformat()}"
            f" end={window_end_utc.isoformat()}"
        )
    return samples, poll_iterations, window_start_utc, window_end_utc


def make_samples_csv_rows(samples: list[dict[str, Any]]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for sample in samples:
        rows.append(
            {
                "timestamp_utc": sample.get("timestamp_utc", ""),
                "status": sample.get("status", ""),
                "reason": sample.get("reason", ""),
                "symbol_source": sample.get("symbol_source", ""),
                "selected_symbol": sample.get("selected_symbol", ""),
                "selected_bootstrap_ready": bool(sample.get("selected_bootstrap_ready", False)),
                "bootstrap_candidate_count": sample.get("bootstrap_candidate_count"),
                "selected_spread_bps": sample.get("selected_spread_bps"),
                "selected_momentum_pct": sample.get("selected_momentum_pct"),
                "selected_hybrid_score": sample.get("selected_hybrid_score"),
                "gate_expected_edge_bps": sample.get("gate_expected_edge_bps"),
                "gate_composite_score": sample.get("gate_composite_score"),
                "edge_proof_bootstrap_reason_codes": "|".join(
                    [str(x) for x in sample.get("edge_proof_bootstrap_reason_codes", []) if str(x).strip()]
                ),
            }
        )
    return rows


def make_trade_window_csv_rows(trades_window: list[dict[str, Any]]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for trade in trades_window:
        rows.append(
            {
                "timestamp": trade.get("timestamp", ""),
                "logged_utc": trade.get("logged_utc", ""),
                "txid": trade.get("txid", ""),
                "symbol": trade.get("symbol", ""),
                "pair": trade.get("pair", ""),
                "status": trade.get("status", ""),
                "size_usd": trade.get("size_usd", ""),
                "gate_score": trade.get("gate_score", ""),
                "entry_price": trade.get("entry_price", ""),
                "qty": trade.get("qty", ""),
                "quote_lane": trade.get("quote_lane", ""),
            }
        )
    return rows


def safe_ratio(numerator: int, denominator: int) -> float | None:
    if denominator <= 0:
        return None
    return round(float(numerator) / float(denominator), 6)


def write_markdown(path: Path, payload: dict[str, Any]) -> None:
    summary = payload.get("summary", {})
    dist = payload.get("heartbeat_distribution", {})
    metrics = payload.get("metrics", {})
    trades = payload.get("trades_window", {})
    guardrails = payload.get("runtime_guardrails", {})
    constraints = payload.get("constraint_decisions", [])

    lines: list[str] = []
    lines.append("# Bootstrap Hit-Rate Baseline")
    lines.append("")
    lines.append(f"Generated UTC: {payload.get('generated_utc', '')}")
    lines.append(
        f"Window UTC: {payload.get('scope', {}).get('window_start_utc', '')} -> {payload.get('scope', {}).get('window_end_utc', '')}"
    )
    lines.append("")

    lines.append("## Summary")
    lines.append(f"- Heartbeat samples: {summary.get('heartbeat_samples', 0)}")
    lines.append(f"- Bootstrap-ready samples: {summary.get('bootstrap_ready_samples', 0)}")
    lines.append(f"- Bootstrap-ready pct: {summary.get('bootstrap_ready_pct', 0.0)}")
    lines.append(f"- Trades placed in window: {summary.get('trades_placed_window', 0)}")
    lines.append(f"- Traded symbols in window: {summary.get('traded_symbols', [])}")
    lines.append(f"- Dominant status: {summary.get('dominant_status', '')}")
    lines.append(f"- Dominant blocker reason: {summary.get('dominant_reason', '')}")
    lines.append(f"- Dominant bootstrap blocker: {summary.get('dominant_bootstrap_reason', '')}")
    lines.append("")

    lines.append("## Runtime Guardrails")
    lines.append(f"- allow_live_orders: {guardrails.get('allow_live_orders', False)}")
    lines.append(f"- kill_switch: {guardrails.get('kill_switch', True)}")
    lines.append(
        f"- bootstrap_max_entries_per_hour: {guardrails.get('edge_proof_bootstrap_max_entries_per_hour', '')}"
    )
    lines.append(
        f"- bootstrap_min_gate_score: {guardrails.get('edge_proof_bootstrap_min_gate_score', '')}"
    )
    lines.append(
        f"- bootstrap_min_expected_edge_bps: {guardrails.get('edge_proof_bootstrap_min_expected_edge_bps', '')}"
    )
    lines.append(
        f"- bootstrap_min_hybrid_score: {guardrails.get('edge_proof_bootstrap_min_hybrid_score', '')}"
    )
    lines.append(
        f"- bootstrap_min_momentum_pct: {guardrails.get('edge_proof_bootstrap_min_momentum_pct', '')}"
    )
    lines.append(
        f"- bootstrap_max_spread_bps: {guardrails.get('edge_proof_bootstrap_max_spread_bps', '')}"
    )
    lines.append("")

    lines.append("## Heartbeat Distributions")
    lines.append(f"- status_counts: {dist.get('status_counts', {})}")
    lines.append(f"- reason_counts: {dist.get('reason_counts', {})}")
    lines.append(f"- symbol_source_counts: {dist.get('symbol_source_counts', {})}")
    lines.append(f"- bootstrap_reason_code_counts: {dist.get('bootstrap_reason_code_counts', {})}")
    lines.append("")

    lines.append("## Metric Stats")
    lines.append(f"- bootstrap_candidate_stats: {metrics.get('bootstrap_candidate_stats', {})}")
    lines.append(f"- spread_bps_stats: {metrics.get('spread_bps_stats', {})}")
    lines.append(f"- momentum_pct_stats: {metrics.get('momentum_pct_stats', {})}")
    lines.append(f"- hybrid_score_stats: {metrics.get('hybrid_score_stats', {})}")
    lines.append(f"- gate_expected_edge_bps_stats: {metrics.get('gate_expected_edge_bps_stats', {})}")
    lines.append("")

    lines.append("## Trade Window")
    lines.append(f"- placed_count: {trades.get('placed_count', 0)}")
    lines.append(f"- total_size_usd: {trades.get('total_size_usd', 0.0)}")
    lines.append(f"- symbol_counts: {trades.get('symbol_counts', {})}")
    lines.append(f"- first_trade_delay_sec: {trades.get('first_trade_delay_sec', None)}")
    lines.append(f"- txids: {trades.get('txids', [])}")
    lines.append("")

    lines.append("## Constraint Decisions")
    if isinstance(constraints, list) and constraints:
        for item in constraints:
            lines.append(f"- {item}")
    else:
        lines.append("- none")

    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Capture bootstrap hit-rate baseline from live heartbeat and trade window telemetry."
    )
    parser.add_argument(
        "--stack-root",
        default=str(Path(__file__).resolve().parents[2]),
        help="Path to INSTITUTIONAL_STACK_V2 root",
    )
    parser.add_argument("--duration-sec", type=int, default=180, help="Sampling window length in seconds")
    parser.add_argument(
        "--sample-interval-sec",
        type=float,
        default=5.0,
        help="Heartbeat polling interval in seconds",
    )
    parser.add_argument(
        "--window-start-utc",
        default="",
        help="Optional explicit UTC timestamp for trade/log window start (ISO-8601).",
    )
    parser.add_argument(
        "--verbose-progress",
        action="store_true",
        help="Emit per-sample progress lines during capture.",
    )
    args = parser.parse_args()

    stack_root = Path(args.stack_root).resolve()
    heartbeat_path = stack_root / "out" / "execution" / "live_executor_heartbeat.json"
    queue_path = stack_root / "out" / "execution" / "live_operator_approval_queue.json"
    runtime_control_path = stack_root / "config" / "runtime_control.json"
    trade_ledger_path = stack_root / "out" / "execution" / "live_trade_ledger.jsonl"
    trade_log_path = stack_root / "out" / "execution" / "live_trade_log.json"

    samples, poll_iterations, window_start_utc, window_end_utc = collect_heartbeat_samples(
        heartbeat_path=heartbeat_path,
        duration_sec=max(args.duration_sec, 1),
        sample_interval_sec=max(args.sample_interval_sec, 0.2),
        verbose_progress=bool(args.verbose_progress),
    )

    trade_window_start_utc = window_start_utc
    if str(args.window_start_utc or "").strip():
        parsed_trade_start = parse_ts(args.window_start_utc)
        if parsed_trade_start is None:
            raise SystemExit(f"Invalid --window-start-utc value: {args.window_start_utc}")
        trade_window_start_utc = parsed_trade_start

    status_counts = Counter(str(sample.get("status", "") or "unknown") for sample in samples)
    reason_counts = Counter(str(sample.get("reason", "") or "none") for sample in samples)
    symbol_source_counts = Counter(str(sample.get("symbol_source", "") or "unknown") for sample in samples)

    bootstrap_reason_code_counts: Counter[str] = Counter()
    for sample in samples:
        for reason_code in sample.get("edge_proof_bootstrap_reason_codes", []) or []:
            bootstrap_reason_code_counts[str(reason_code)] += 1

    bootstrap_ready_samples = sum(1 for sample in samples if bool(sample.get("selected_bootstrap_ready", False)))

    bootstrap_candidate_values = [
        float(sample.get("bootstrap_candidate_count"))
        for sample in samples
        if isinstance(sample.get("bootstrap_candidate_count"), (int, float))
    ]
    spread_values = [
        float(sample.get("selected_spread_bps"))
        for sample in samples
        if isinstance(sample.get("selected_spread_bps"), (int, float))
    ]
    momentum_values = [
        float(sample.get("selected_momentum_pct"))
        for sample in samples
        if isinstance(sample.get("selected_momentum_pct"), (int, float))
    ]
    hybrid_score_values = [
        float(sample.get("selected_hybrid_score"))
        for sample in samples
        if isinstance(sample.get("selected_hybrid_score"), (int, float))
    ]
    gate_edge_values = [
        float(sample.get("gate_expected_edge_bps"))
        for sample in samples
        if isinstance(sample.get("gate_expected_edge_bps"), (int, float))
    ]
    gate_composite_values = [
        float(sample.get("gate_composite_score"))
        for sample in samples
        if isinstance(sample.get("gate_composite_score"), (int, float))
    ]

    trade_ledger_records = load_jsonl(trade_ledger_path)
    trades_window: list[dict[str, Any]] = []
    for record in trade_ledger_records:
        record_ts = choose_timestamp(record, ["timestamp", "logged_utc", "timestamp_utc"])
        if within_window(record_ts, trade_window_start_utc, window_end_utc):
            trades_window.append(record)

    trade_window_status_counts = Counter(str(row.get("status", "") or "unknown") for row in trades_window)
    trade_symbol_counts = Counter(str(row.get("symbol", "") or "unknown") for row in trades_window)
    trade_txids = [str(row.get("txid", "")) for row in trades_window if str(row.get("txid", "")).strip()]
    placed_count = sum(1 for row in trades_window if str(row.get("status", "")).upper() == "PLACED")
    total_size_usd = round(
        sum(float(row.get("size_usd", 0.0) or 0.0) for row in trades_window if isinstance(row.get("size_usd"), (int, float))),
        6,
    )

    first_trade_delay_sec = None
    first_trade_timestamp_utc = None
    if trades_window:
        ts_values: list[datetime] = []
        for row in trades_window:
            row_ts = choose_timestamp(row, ["timestamp", "logged_utc", "timestamp_utc"])
            if row_ts is not None:
                ts_values.append(row_ts)
        if ts_values:
            first_ts = min(ts_values)
            first_trade_timestamp_utc = first_ts.isoformat()
            first_trade_delay_sec = round((first_ts - trade_window_start_utc).total_seconds(), 3)

    trade_log_payload = load_json(trade_log_path)
    trade_log_rows = trade_log_payload if isinstance(trade_log_payload, list) else []
    trade_log_window: list[dict[str, Any]] = []
    for row in trade_log_rows:
        if not isinstance(row, dict):
            continue
        row_ts = choose_timestamp(row, ["timestamp", "logged_utc", "timestamp_utc"])
        if within_window(row_ts, trade_window_start_utc, window_end_utc):
            trade_log_window.append(row)

    trade_log_status_counts = Counter(str(row.get("status", "") or "unknown") for row in trade_log_window)
    edge_proof_armed_count = 0
    hard_safety_bypass_count = 0
    for row in trade_log_window:
        edge_proof = row.get("edge_proof", {})
        if isinstance(edge_proof, dict) and bool(edge_proof.get("armed", False)):
            edge_proof_armed_count += 1
        if bool(row.get("hard_safety_bypass_applied", False)):
            hard_safety_bypass_count += 1

    runtime_control = load_json(runtime_control_path)
    if not isinstance(runtime_control, dict):
        runtime_control = {}

    runtime_guardrails = {
        "allow_live_orders": bool(runtime_control.get("allow_live_orders", False)),
        "kill_switch": bool(runtime_control.get("kill_switch", True)),
        "edge_proof_bootstrap_enabled": bool(runtime_control.get("edge_proof_bootstrap_enabled", False)),
        "edge_proof_bootstrap_max_entries_per_hour": runtime_control.get(
            "edge_proof_bootstrap_max_entries_per_hour", None
        ),
        "edge_proof_bootstrap_min_gate_score": runtime_control.get("edge_proof_bootstrap_min_gate_score", None),
        "edge_proof_bootstrap_min_expected_edge_bps": runtime_control.get(
            "edge_proof_bootstrap_min_expected_edge_bps", None
        ),
        "edge_proof_bootstrap_min_hybrid_score": runtime_control.get("edge_proof_bootstrap_min_hybrid_score", None),
        "edge_proof_bootstrap_min_momentum_pct": runtime_control.get("edge_proof_bootstrap_min_momentum_pct", None),
        "edge_proof_bootstrap_max_spread_bps": runtime_control.get("edge_proof_bootstrap_max_spread_bps", None),
        "edge_proof_bootstrap_hybrid_edge_scale": runtime_control.get("edge_proof_bootstrap_hybrid_edge_scale", None),
    }

    queue_snapshot = load_json(queue_path)
    queue_tickets: list[dict[str, Any]] = []
    if isinstance(queue_snapshot, dict):
        raw_tickets = queue_snapshot.get("tickets", [])
        if isinstance(raw_tickets, list):
            queue_tickets = [row for row in raw_tickets if isinstance(row, dict)]

    queue_top_symbols = [str(row.get("symbol", "")) for row in queue_tickets[:5] if str(row.get("symbol", "")).strip()]

    dominant_status = status_counts.most_common(1)[0][0] if status_counts else ""
    dominant_reason = reason_counts.most_common(1)[0][0] if reason_counts else ""
    dominant_bootstrap_reason = (
        bootstrap_reason_code_counts.most_common(1)[0][0] if bootstrap_reason_code_counts else ""
    )

    constraints: list[str] = []
    if runtime_guardrails.get("allow_live_orders", False):
        constraints.append("live_orders_enabled=true for supervised live execution")
    else:
        constraints.append("live_orders_enabled=false; conversion intentionally blocked")

    max_entries_per_hour = runtime_guardrails.get("edge_proof_bootstrap_max_entries_per_hour")
    if isinstance(max_entries_per_hour, (int, float)):
        constraints.append(f"bootstrap_max_entries_per_hour={max_entries_per_hour}")

    if dominant_bootstrap_reason:
        constraints.append(f"dominant_bootstrap_reason={dominant_bootstrap_reason}")

    if dominant_reason:
        constraints.append(f"dominant_cycle_reason={dominant_reason}")

    payload: dict[str, Any] = {
        "schema_version": "luma_bootstrap_hitrate_baseline_v1",
        "generated_utc": now_iso(),
        "scope": {
            "stack_root": str(stack_root),
            "window_start_utc": window_start_utc.isoformat(),
            "window_end_utc": window_end_utc.isoformat(),
            "trade_window_start_utc": trade_window_start_utc.isoformat(),
            "duration_sec": int(max(args.duration_sec, 1)),
            "sample_interval_sec": float(max(args.sample_interval_sec, 0.2)),
            "poll_iterations": int(poll_iterations),
            "paths": {
                "heartbeat": str(heartbeat_path),
                "trade_ledger": str(trade_ledger_path),
                "trade_log": str(trade_log_path),
                "runtime_control": str(runtime_control_path),
                "operator_queue": str(queue_path),
            },
        },
        "runtime_guardrails": runtime_guardrails,
        "queue_snapshot": {
            "ticket_count": int(len(queue_tickets)),
            "top_symbols": queue_top_symbols,
            "queue_generated_utc": queue_snapshot.get("generated_utc") if isinstance(queue_snapshot, dict) else None,
        },
        "summary": {
            "heartbeat_samples": int(len(samples)),
            "bootstrap_ready_samples": int(bootstrap_ready_samples),
            "bootstrap_ready_pct": round((float(bootstrap_ready_samples) / float(len(samples)) * 100.0), 3)
            if samples
            else 0.0,
            "trades_placed_window": int(placed_count),
            "traded_symbols_count": int(len(trade_symbol_counts)),
            "traded_symbols": [key for key, _ in trade_symbol_counts.most_common()],
            "bootstrap_ready_to_placed_proxy_ratio": safe_ratio(placed_count, bootstrap_ready_samples),
            "dominant_status": dominant_status,
            "dominant_reason": dominant_reason,
            "dominant_bootstrap_reason": dominant_bootstrap_reason,
        },
        "heartbeat_distribution": {
            "status_counts": counter_dict(status_counts),
            "reason_counts": counter_dict(reason_counts),
            "symbol_source_counts": counter_dict(symbol_source_counts),
            "bootstrap_reason_code_counts": counter_dict(bootstrap_reason_code_counts),
        },
        "metrics": {
            "bootstrap_candidate_stats": number_stats(bootstrap_candidate_values),
            "spread_bps_stats": number_stats(spread_values),
            "momentum_pct_stats": number_stats(momentum_values),
            "hybrid_score_stats": number_stats(hybrid_score_values),
            "gate_expected_edge_bps_stats": number_stats(gate_edge_values),
            "gate_composite_score_stats": number_stats(gate_composite_values),
        },
        "trades_window": {
            "placed_count": int(placed_count),
            "status_counts": counter_dict(trade_window_status_counts),
            "symbol_counts": counter_dict(trade_symbol_counts),
            "txids": trade_txids,
            "total_size_usd": total_size_usd,
            "first_trade_timestamp_utc": first_trade_timestamp_utc,
            "first_trade_delay_sec": first_trade_delay_sec,
            "records": trades_window,
        },
        "trade_log_window": {
            "row_count": int(len(trade_log_window)),
            "status_counts": counter_dict(trade_log_status_counts),
            "edge_proof_armed_count": int(edge_proof_armed_count),
            "hard_safety_bypass_count": int(hard_safety_bypass_count),
        },
        "heartbeat_samples": samples,
        "constraint_decisions": constraints,
    }

    out_dir = stack_root / "out" / "ops" / "bootstrap_hitrate"
    tag = now_tag()
    json_path = out_dir / f"bootstrap_hitrate_baseline_{tag}.json"
    samples_csv_path = out_dir / f"bootstrap_hitrate_samples_{tag}.csv"
    trade_window_csv_path = out_dir / f"bootstrap_hitrate_trades_{tag}.csv"
    md_path = out_dir / f"bootstrap_hitrate_baseline_{tag}.md"

    write_json(json_path, payload)
    write_csv(samples_csv_path, make_samples_csv_rows(samples))
    write_csv(trade_window_csv_path, make_trade_window_csv_rows(trades_window))
    write_markdown(md_path, payload)

    latest_json = out_dir / "bootstrap_hitrate_baseline_latest.json"
    latest_samples_csv = out_dir / "bootstrap_hitrate_samples_latest.csv"
    latest_trades_csv = out_dir / "bootstrap_hitrate_trades_latest.csv"
    latest_md = out_dir / "bootstrap_hitrate_baseline_latest.md"

    write_json(latest_json, payload)
    latest_samples_csv.write_text(samples_csv_path.read_text(encoding="utf-8"), encoding="utf-8")
    latest_trades_csv.write_text(trade_window_csv_path.read_text(encoding="utf-8"), encoding="utf-8")
    latest_md.write_text(md_path.read_text(encoding="utf-8"), encoding="utf-8")

    manifest = {
        "generated_utc": payload.get("generated_utc"),
        "summary": payload.get("summary"),
        "artifacts": {
            "json": str(json_path),
            "samples_csv": str(samples_csv_path),
            "trades_csv": str(trade_window_csv_path),
            "markdown": str(md_path),
            "latest_json": str(latest_json),
            "latest_samples_csv": str(latest_samples_csv),
            "latest_trades_csv": str(latest_trades_csv),
            "latest_markdown": str(latest_md),
        },
    }

    manifest_path = out_dir / f"bootstrap_hitrate_manifest_{tag}.json"
    write_json(manifest_path, manifest)
    print(json.dumps({**manifest, "manifest": str(manifest_path)}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
