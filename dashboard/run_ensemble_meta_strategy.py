"""Offline past-only ensemble research. No broker or execution authority.

Legacy vector strategies may normalize their complete input. Only a prior
rolling window reaches each strategy; its last signal weights the next price
transition. Reporting blocks never change decisions. Additive unitless scores
are not compounded or realized PnL.
"""
from __future__ import annotations

import argparse
import csv
from functools import lru_cache
import hashlib
import io
import json
import math
from pathlib import Path
import platform
import sys
import types

import numpy as np
import pandas as pd

STACK_ROOT = Path(__file__).resolve().parents[1]
RUNNER_SOURCE_SHA256 = hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
SCHEMA = "lumencore.ensemble_past_only_research.v2"
STRATEGY_MODULES = (
    "hybrid_harmonic_strategies", "hybrid_harmonic_algorithms", "novel_harmonic_layers"
)
MAX_INPUT_BYTES = 32 * 1024 * 1024
MAX_INPUT_ROWS = 10000
RESULT_COLUMNS = ["start", "end", "result", "bars", "gross_result", "estimated_cost", "buy_hold_result", "cash_result"]


def canonical_json(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False)


def digest(data):
    return hashlib.sha256(data).hexdigest()


def _read_bounded(path):
    with Path(path).open("rb") as handle:
        content = handle.read(MAX_INPUT_BYTES + 1)
    if len(content) > MAX_INPUT_BYTES:
        raise ValueError("Input exceeds the 32 MiB research limit")
    return content


def _valid_prices(df):
    if not isinstance(df, pd.DataFrame) or list(df.columns).count("close") != 1:
        raise ValueError("An explicit, unique close column is required")
    if len(df) == 0 or len(df) > MAX_INPUT_ROWS:
        raise ValueError("Input must contain 1..10000 ordered rows")
    if not df.index.is_unique or not df.index.is_monotonic_increasing:
        raise ValueError("Input index must be unique and increasing")
    numeric = pd.to_numeric(df["close"], errors="raise")
    if pd.api.types.is_bool_dtype(numeric.dtype) or np.iscomplexobj(numeric):
        raise ValueError("Prices must be real numbers, not booleans or complex values")
    values = numeric.to_numpy(dtype=float)
    if not np.isfinite(values).all() or (values <= 0).any():
        raise ValueError("Prices must all be finite and positive; no filling is permitted")
    return values


def _parse_data(content, *, price_column="close", timestamp_column=None):
    text = content.decode("utf-8-sig")
    if "\x00" in text:
        raise ValueError("CSV cannot contain NUL bytes")
    reader = csv.reader(io.StringIO(text, newline=""), strict=True)
    try:
        header = next(reader, [])
        records = []
        for row in reader:
            if len(row) != len(header):
                raise ValueError("Every CSV record must match the header width; blank records are not dropped")
            records.append(row)
            if len(records) > MAX_INPUT_ROWS:
                raise ValueError("Input exceeds the 10000-row research limit")
    except csv.Error as exc:
        raise ValueError("Malformed CSV quoting") from exc
    if not header or len(header) != len(set(header)) or any(not item.strip() for item in header):
        raise ValueError("CSV requires unique, nonempty column names")
    if price_column not in header:
        raise ValueError("The explicitly selected price column is absent")
    # Construct from the checked records: pandas inference can silently drop
    # blank records, infer an index from surplus fields or coerce True to 1.
    df = pd.DataFrame(records, columns=header)
    if price_column != "close":
        if "close" in df.columns:
            raise ValueError("Selected price column conflicts with an existing close column")
        df = df.rename(columns={price_column: "close"})
    if timestamp_column is not None:
        if timestamp_column not in df or timestamp_column == "close":
            raise ValueError("A separate timestamp column is required")
        timestamps = pd.to_datetime(df[timestamp_column], utc=True, errors="raise")
        if timestamps.isna().any():
            raise ValueError("Timestamps cannot be missing")
        df = df.set_index(pd.DatetimeIndex(timestamps))
    df["close"] = _valid_prices(df)
    return df


def load_data(path, *, price_column="close", timestamp_column=None):
    """Read explicitly selected prices; no numeric fallback or interpolation."""
    return _parse_data(_read_bounded(path), price_column=price_column, timestamp_column=timestamp_column)


@lru_cache(maxsize=1)
def _strategy_modules():
    modules = []
    for name in STRATEGY_MODULES:
        path = STACK_ROOT / "code" / (name + ".py")
        source = path.read_bytes()
        # Only three named canonical files. Ignore data/code, sys.path,
        # ordinary module caches and stale bytecode; bind the executed bytes.
        module = types.ModuleType("_lumencore_ensemble_" + name)
        module.__file__ = str(path)
        exec(compile(source, str(path), "exec"), module.__dict__)
        modules.append((module, digest(source)))
    return tuple(modules)


def _coerce_signal(raw_signal, index):
    if isinstance(raw_signal, pd.Series) and not raw_signal.index.equals(index):
        raise ValueError("Signal index must exactly match the supplied historical rows")
    values = np.asarray(raw_signal, dtype=float)
    if values.ndim != 1 or len(values) != len(index) or not np.isfinite(values).all():
        raise ValueError("Signal must be a finite vector matching every supplied historical row")
    return pd.Series(values, index=index, dtype=float)


def ensemble_signals(df):
    _valid_prices(df)
    hhs, hha, nhl = (item[0] for item in _strategy_modules())
    builders = [
        hhs.strat_phase_follow, hhs.strat_resonance_revert,
        hhs.strat_interference_breakout, hhs.strat_nodal_compression_release,
        hhs.strat_frequency_drift_guard, hhs.strat_curvature_reversal,
        hhs.strat_harmonic_consensus, hha.algo_phase_coherence,
        hha.algo_resonance_cluster, hha.algo_multi_timescale_interference,
        hha.algo_harmonic_envelope, nhl.algo_echo_stack,
        nhl.algo_resonant_pressure, nhl.algo_phase_lattice, nhl.algo_vortex_memory,
    ]
    signals = []
    for builder in builders:
        try:
            raw = builder(df["close"].copy())
            signals.append(_coerce_signal(raw, df.index).to_numpy())
        except Exception as exc:
            raise ValueError(f"Strategy {builder.__name__} did not produce a valid signal") from exc
    return pd.Series(np.mean(np.column_stack(signals), axis=1), index=df.index, name="ensemble_signal")


def auto_tune(df, signal_func):
    raise NotImplementedError("No validated tuning contract exists; use separate development data")


def _positive_integer(value, name):
    if isinstance(value, bool) or not isinstance(value, (int, np.integer)) or not 1 <= value <= MAX_INPUT_ROWS:
        raise ValueError(f"{name} must be an integer from 1 to 10000")


def _cost_bps(value, name):
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value) or not 0 <= value <= 10000:
        raise ValueError(f"{name} must be finite and between 0 and 10000")


def evaluate_rows(df, signal_func, *, window=250, fee_bps=0.0, slippage_bps=0.0):
    """Target i uses only rows [i-window, i); initial diagnostic weight is flat.

    Costs are a linear one-way turnover assumption. Final weight is not
    liquidated. Financing, impact, fills, borrow and taxes are outside scope.
    """
    values = _valid_prices(df)
    _positive_integer(window, "window")
    _cost_bps(fee_bps, "fee_bps")
    _cost_bps(slippage_bps, "slippage_bps")
    if len(df) <= window:
        raise ValueError("At least window + 1 rows are needed for an evaluated transition")
    rows = []
    previous_weight = 0.0
    for i in range(window, len(df)):
        history = df.iloc[i - window:i].copy(deep=True)
        signal = _coerce_signal(signal_func(history), history.index)
        raw = float(signal.iloc[-1])
        weight = float(np.clip(raw, -1.0, 1.0))
        turnover = abs(weight - previous_weight)
        fee = turnover * fee_bps / 10000.0
        slippage = turnover * slippage_bps / 10000.0
        change = float(values[i] / values[i - 1] - 1.0)
        gross = weight * change
        baseline_cost = (fee_bps + slippage_bps) / 10000.0 if i == window else 0.0
        rows.append({
            "target_position": i, "decision_row": str(df.index[i - 1]), "target_row": str(df.index[i]),
            "previous_price": float(values[i - 1]), "target_price": float(values[i]),
            "raw_signal": raw, "weight": weight, "turnover": turnover,
            "price_return": change, "gross_score": gross, "fee_cost": fee,
            "slippage_cost": slippage, "net_score": gross - fee - slippage,
            "buy_hold_score": change - baseline_cost, "cash_score": 0.0,
        })
        previous_weight = weight
    result = pd.DataFrame(rows)
    if not np.isfinite(result.select_dtypes(include=[np.number]).to_numpy()).all():
        raise ValueError("Evaluation produced a nonfinite score")
    return result


def summarize_rows(rows, *, step=50):
    _positive_integer(step, "step")
    blocks = []
    for i in range(0, len(rows), step):
        part = rows.iloc[i:i + step]
        blocks.append({
            "start": part["target_row"].iloc[0], "end": part["target_row"].iloc[-1],
            "result": float(part["net_score"].sum()), "bars": len(part),
            "gross_result": float(part["gross_score"].sum()),
            "estimated_cost": float((part["fee_cost"] + part["slippage_cost"]).sum()),
            "buy_hold_result": float(part["buy_hold_score"].sum()), "cash_result": 0.0,
        })
    return pd.DataFrame(blocks, columns=RESULT_COLUMNS)


def walk_forward(df, signal_func, window=250, step=50, *, fee_bps=0.0, slippage_bps=0.0):
    _positive_integer(step, "step")
    rows = evaluate_rows(df, signal_func, window=window, fee_bps=fee_bps, slippage_bps=slippage_bps)
    return summarize_rows(rows, step=step)


def _source_identities():
    if digest(Path(__file__).read_bytes()) != RUNNER_SOURCE_SHA256:
        raise ValueError("Evaluator source changed after import; start a new process")
    identities = {"dashboard/run_ensemble_meta_strategy.py": RUNNER_SOURCE_SHA256}
    for name, (_, loaded_hash) in zip(STRATEGY_MODULES, _strategy_modules()):
        relative = "code/" + name + ".py"
        if digest((STACK_ROOT / relative).read_bytes()) != loaded_hash:
            raise ValueError("A loaded strategy source changed; start a new process")
        identities[relative] = loaded_hash
    return identities


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--input-kind", choices=("synthetic", "unverified_source"), default="unverified_source",
                        help="Operator declaration; does not independently verify the input source")
    parser.add_argument("--output-dir", type=Path, required=True, help="New directory; never overwrite retained runs")
    parser.add_argument("--price-column", default="close")
    parser.add_argument("--timestamp-column")
    parser.add_argument("--window", type=int, default=250)
    parser.add_argument("--step", type=int, default=50)
    parser.add_argument("--fee-bps", type=float, required=True, help="Explicit one-way fee assumption, including zero")
    parser.add_argument("--slippage-bps", type=float, required=True, help="Explicit one-way slippage assumption, including zero")
    args = parser.parse_args(argv)
    try:
        if args.output_dir.exists():
            raise ValueError("Output directory already exists; retained runs cannot be overwritten")
        content = _read_bounded(args.input)
        df = _parse_data(content, price_column=args.price_column, timestamp_column=args.timestamp_column)
        before = _source_identities()
        rows = evaluate_rows(df, ensemble_signals, window=args.window, fee_bps=args.fee_bps, slippage_bps=args.slippage_bps)
        blocks = summarize_rows(rows, step=args.step)
        if _source_identities() != before or _read_bounded(args.input) != content:
            raise ValueError("Input or evaluator source changed during evaluation")
        config = {"window": args.window, "reporting_step": args.step, "fee_bps": args.fee_bps, "slippage_bps": args.slippage_bps, "price_column": args.price_column, "timestamp_column": args.timestamp_column}
        receipt = {
            "schema": SCHEMA, "evidence_class": "OFFLINE_RESEARCH_DIAGNOSTIC",
            "input": {"name": args.input.name, "kind": args.input_kind, "sha256": digest(content), "bytes": len(content), "rows": len(df)},
            "configuration": config, "code_sha256": before,
            "runtime": {"python": platform.python_version(), "numpy": np.__version__, "pandas": pd.__version__},
            "metric": "additive_unitless_weighted_return_minus_assumed_turnover_cost",
            "chronology": "parsed_timestamp_order_only" if args.timestamp_column else "supplied_row_order_only",
            "independent_source_timing_verified": False, "parameter_selection_verified": False,
            "information_set": "Prior window rows only; final prior-row signal weights next observed transition",
            "position_model": "Flat initial weight; clipped [-1,1]; final weight not liquidated",
            "excluded": ["actual fills", "compounding", "financing", "borrow", "market impact", "taxes", "realized PnL", "independent validation"],
            "execution_authorized": False, "scientific_performance_claim_supported": False,
            "evaluated_transitions": len(rows), "reporting_blocks": len(blocks),
            "net_score_sum": float(rows["net_score"].sum()), "buy_hold_score_sum": float(rows["buy_hold_score"].sum()),
        }
        artifacts = {"ensemble_walkforward_results.csv": blocks.to_csv(index=False, lineterminator="\n").encode(), "ensemble_evaluation_rows.csv": rows.to_csv(index=False, lineterminator="\n").encode()}
        receipt["artifacts"] = {name: {"bytes": len(data), "sha256": digest(data)} for name, data in artifacts.items()}
        receipt["receipt_sha256"] = digest(canonical_json(receipt).encode())
        args.output_dir.mkdir(parents=True, exist_ok=False)
        for name, data in artifacts.items():
            (args.output_dir / name).write_bytes(data)
        # A partial directory has no completion receipt.
        (args.output_dir / "ensemble_run_receipt.json").write_bytes((canonical_json(receipt) + "\n").encode("utf-8"))
    except (ValueError, OSError, UnicodeError, KeyError) as exc:
        print(f"Evaluation rejected: {exc}", file=sys.stderr)
        return 2
    print(f"Wrote {len(rows)} offline research transitions to {args.output_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
