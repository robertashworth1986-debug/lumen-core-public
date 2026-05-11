from __future__ import annotations

import argparse
import hashlib
import json
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
from sklearn.linear_model import LinearRegression, Ridge
from sklearn.metrics import mean_absolute_error, mean_squared_error
from sklearn.neural_network import MLPRegressor
from sklearn.preprocessing import StandardScaler

try:
    import matplotlib.pyplot as plt
    from matplotlib.backends.backend_pdf import PdfPages
except Exception:
    plt = None
    PdfPages = None


ROOT = Path(r"c:/LumaTrader/INSTITUTIONAL_STACK_V2")
DEFAULT_OUTPUT_ROOT = ROOT / "out" / "execution" / "harmonic_backprop_proofpack"
DEFAULT_LEDGER = ROOT / "out" / "frozen_delta_ledger.jsonl"

PREFERRED_VALUE_COLUMNS = [
    "value",
    "close",
    "clo",
    "generation",
    "price",
    "target",
    "y",
]

PREFERRED_DATE_COLUMNS = [
    "date",
    "datetime",
    "timestamp",
    "time",
    "period",
    "month",
]


@dataclass
class SeriesPayload:
    source_path: Path
    source_sha256: str
    value_col: str
    date_col: str | None
    frame: pd.DataFrame
    rows_total: int
    rows_valid: int


def now_utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def now_utc_compact() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def read_last_nonempty_json_line(path: Path) -> dict[str, Any] | None:
    if not path.exists():
        return None
    lines = path.read_text(encoding="utf-8", errors="ignore").splitlines()
    for line in reversed(lines):
        if not line.strip():
            continue
        try:
            return json.loads(line)
        except Exception:
            return None
    return None


def detect_date_col(df: pd.DataFrame, requested: str) -> str | None:
    cols = list(df.columns)
    if requested and requested in cols:
        return requested

    lowered = {c: str(c).strip().lower() for c in cols}
    for pref in PREFERRED_DATE_COLUMNS:
        for col, low in lowered.items():
            if low == pref:
                return col
    for pref in PREFERRED_DATE_COLUMNS:
        for col, low in lowered.items():
            if pref in low:
                return col
    return None


def detect_value_col(df: pd.DataFrame, requested: str) -> str:
    cols = list(df.columns)
    if requested and requested in cols:
        return requested

    numeric_candidate_scores: list[tuple[float, str]] = []
    for col in cols:
        as_num = pd.to_numeric(df[col], errors="coerce")
        usable = float(as_num.notna().mean())
        if usable >= 0.35:
            numeric_candidate_scores.append((usable, col))

    lowered = {c: str(c).strip().lower() for c in cols}
    for pref in PREFERRED_VALUE_COLUMNS:
        for col, low in lowered.items():
            if low == pref and any(c == col for _, c in numeric_candidate_scores):
                return col
    for pref in PREFERRED_VALUE_COLUMNS:
        for col, low in lowered.items():
            if pref in low and any(c == col for _, c in numeric_candidate_scores):
                return col

    if numeric_candidate_scores:
        numeric_candidate_scores.sort(reverse=True)
        return numeric_candidate_scores[0][1]

    if cols:
        return cols[0]
    raise ValueError("input CSV has no columns")


def load_series(csv_path: Path, value_col: str, date_col: str) -> SeriesPayload:
    if not csv_path.exists():
        raise FileNotFoundError(f"CSV not found: {csv_path}")

    df = pd.read_csv(csv_path)
    if df.empty:
        raise ValueError("input CSV is empty")

    total_rows = len(df)
    chosen_value = detect_value_col(df, value_col)
    chosen_date = detect_date_col(df, date_col)

    clean = pd.DataFrame()
    clean["value"] = pd.to_numeric(df[chosen_value], errors="coerce")

    parsed_dates = None
    if chosen_date is not None:
        parsed_dates = pd.to_datetime(df[chosen_date], errors="coerce", utc=True)
        good_ratio = float(parsed_dates.notna().mean())
        if good_ratio < 0.30:
            parsed_dates = None
            chosen_date = None

    if parsed_dates is not None:
        clean["ts"] = parsed_dates
        clean = clean.dropna(subset=["ts", "value"]).sort_values("ts").reset_index(drop=True)
    else:
        clean = clean.dropna(subset=["value"]).reset_index(drop=True)
        clean["ts"] = pd.date_range(
            start="2000-01-01",
            periods=len(clean),
            freq="D",
            tz="UTC",
        )

    if len(clean) < 60:
        raise ValueError(f"not enough valid rows after cleaning: {len(clean)} (need at least 60)")

    return SeriesPayload(
        source_path=csv_path,
        source_sha256=sha256_file(csv_path),
        value_col=chosen_value,
        date_col=chosen_date,
        frame=clean,
        rows_total=total_rows,
        rows_valid=len(clean),
    )


def split_series(y: np.ndarray, test_frac: float, min_test: int) -> tuple[np.ndarray, np.ndarray]:
    n = len(y)
    n_test = max(min_test, int(round(n * test_frac)))
    n_test = min(n_test, max(12, n // 2))
    n_train = n - n_test
    if n_train < 48:
        n_test = max(12, n - 48)
        n_train = n - n_test
    if n_train < 32 or n_test < 8:
        raise ValueError(f"series too short after split: n={n}, train={n_train}, test={n_test}")
    return y[:n_train], y[n_train:]


def harmonic_features(t: np.ndarray, periods: list[float]) -> np.ndarray:
    cols = [np.ones_like(t, dtype=float), t.astype(float)]
    for period in periods:
        if period <= 1:
            continue
        cols.append(np.sin(2.0 * np.pi * t / period))
        cols.append(np.cos(2.0 * np.pi * t / period))
    return np.column_stack(cols)


def model_naive(y_train: np.ndarray, n_test: int) -> np.ndarray:
    return np.full(n_test, y_train[-1], dtype=float)


def model_linear_trend(y_train: np.ndarray, n_test: int) -> np.ndarray:
    n = len(y_train)
    x_train = np.arange(n, dtype=float).reshape(-1, 1)
    model = LinearRegression().fit(x_train, y_train)
    x_test = np.arange(n, n + n_test, dtype=float).reshape(-1, 1)
    return model.predict(x_test)


def model_harmonic_fixed12(y_train: np.ndarray, n_test: int) -> np.ndarray:
    n = len(y_train)
    t_train = np.arange(n, dtype=float)
    t_test = np.arange(n, n + n_test, dtype=float)
    x_train = harmonic_features(t_train, [12.0])
    x_test = harmonic_features(t_test, [12.0])
    model = Ridge(alpha=1.0).fit(x_train, y_train)
    return model.predict(x_test)


def model_harmonic_search(y_train: np.ndarray, n_test: int, top_k: int = 3) -> np.ndarray:
    n = len(y_train)
    centered = y_train - np.mean(y_train)
    fft = np.fft.rfft(centered)
    power = np.abs(fft) ** 2
    freqs = np.fft.rfftfreq(n, d=1.0)

    # Ignore DC and ultra-low frequencies that overfit trend rather than seasonal structure.
    mask = freqs > (1.0 / max(n, 4))
    periods: list[float] = []
    if mask.any():
        ranked = np.argsort(power[mask])[::-1][:top_k]
        picked = freqs[mask][ranked]
        periods = [max(2.0, 1.0 / f) for f in picked if f > 0]
    if not periods:
        periods = [12.0]

    t_train = np.arange(n, dtype=float)
    t_test = np.arange(n, n + n_test, dtype=float)
    x_train = harmonic_features(t_train, periods)
    x_test = harmonic_features(t_test, periods)
    model = Ridge(alpha=1.0).fit(x_train, y_train)
    return model.predict(x_test)


def model_mlp_untuned(y_train: np.ndarray, n_test: int) -> np.ndarray:
    n = len(y_train)
    x_train = np.arange(n, dtype=float).reshape(-1, 1)
    x_test = np.arange(n, n + n_test, dtype=float).reshape(-1, 1)
    model = MLPRegressor(
        hidden_layer_sizes=(10,),
        learning_rate_init=0.001,
        max_iter=200,
        random_state=7,
        n_iter_no_change=200,
    )
    model.fit(x_train, y_train)
    return model.predict(x_test)


def make_lag_features(y: np.ndarray, n_lags: int) -> tuple[np.ndarray, np.ndarray]:
    xs = []
    ys = []
    for idx in range(n_lags, len(y)):
        xs.append(y[idx - n_lags:idx])
        ys.append(y[idx])
    return np.array(xs), np.array(ys)


def model_mlp_tuned(y_train: np.ndarray, n_test: int, n_lags: int = 24) -> np.ndarray:
    if len(y_train) <= n_lags + 8:
        return model_naive(y_train, n_test)

    x_train, y_supervised = make_lag_features(y_train, n_lags=n_lags)
    sx = StandardScaler().fit(x_train)
    sy = StandardScaler().fit(y_supervised.reshape(-1, 1))

    x_scaled = sx.transform(x_train)
    y_scaled = sy.transform(y_supervised.reshape(-1, 1)).ravel()

    model = MLPRegressor(
        hidden_layer_sizes=(64, 32, 16),
        learning_rate_init=0.003,
        max_iter=2000,
        early_stopping=True,
        validation_fraction=0.12,
        n_iter_no_change=25,
        random_state=7,
    )
    model.fit(x_scaled, y_scaled)

    history = list(y_train[-n_lags:])
    preds = []
    for _ in range(n_test):
        xin = np.array(history[-n_lags:], dtype=float).reshape(1, -1)
        xin_scaled = sx.transform(xin)
        yhat_scaled = model.predict(xin_scaled)
        yhat = sy.inverse_transform(yhat_scaled.reshape(-1, 1)).ravel()[0]
        preds.append(float(yhat))
        history.append(float(yhat))
    return np.array(preds, dtype=float)


MODELS: dict[str, Any] = {
    "a_naive": model_naive,
    "b_linear_trend": model_linear_trend,
    "c_harmonic_fixed12": model_harmonic_fixed12,
    "d_harmonic_search": model_harmonic_search,
    "e_mlp_untuned": model_mlp_untuned,
    "f_mlp_tuned": model_mlp_tuned,
}


def evaluate_models(y_train: np.ndarray, y_test: np.ndarray) -> tuple[pd.DataFrame, pd.DataFrame]:
    rows: list[dict[str, Any]] = []
    pred_map: dict[str, np.ndarray] = {}

    for model_name, model_fn in MODELS.items():
        try:
            preds = model_fn(y_train, len(y_test))
            preds = np.asarray(preds, dtype=float)
            if len(preds) != len(y_test):
                raise ValueError(f"prediction length mismatch {len(preds)} != {len(y_test)}")

            rmse = float(np.sqrt(mean_squared_error(y_test, preds)))
            mae = float(mean_absolute_error(y_test, preds))
            denom = np.clip(np.abs(y_test), 1e-9, None)
            mape = float(np.mean(np.abs((y_test - preds) / denom)) * 100.0)

            rows.append(
                {
                    "model": model_name,
                    "rmse": rmse,
                    "mae": mae,
                    "mape_pct": mape,
                }
            )
            pred_map[model_name] = preds
        except Exception as exc:
            rows.append(
                {
                    "model": model_name,
                    "rmse": np.nan,
                    "mae": np.nan,
                    "mape_pct": np.nan,
                    "error": str(exc),
                }
            )

    metrics = pd.DataFrame(rows).sort_values("rmse", na_position="last").reset_index(drop=True)

    holdout = pd.DataFrame({"actual": y_test})
    for model_name in MODELS.keys():
        if model_name in pred_map:
            holdout[f"pred_{model_name}"] = pred_map[model_name]

    return metrics, holdout


def build_findings(metrics: pd.DataFrame) -> list[str]:
    valid = metrics.dropna(subset=["rmse"]).copy()
    if valid.empty:
        return ["No model produced a valid score."]

    winner = valid.iloc[0]
    lookup = {r["model"]: float(r["rmse"]) for _, r in valid.iterrows()}

    findings = [
        f"Winner by RMSE: {winner['model']} ({winner['rmse']:.6f})",
    ]

    if "c_harmonic_fixed12" in lookup and "e_mlp_untuned" in lookup:
        v6_gap = lookup["e_mlp_untuned"] - lookup["c_harmonic_fixed12"]
        findings.append(
            f"V6-style matchup (harmonic_fixed12 vs mlp_untuned): gap={v6_gap:+.6f} RMSE (positive favors harmonic)."
        )

    if "d_harmonic_search" in lookup and "f_mlp_tuned" in lookup:
        fair_gap = lookup["f_mlp_tuned"] - lookup["d_harmonic_search"]
        findings.append(
            f"Fair matchup (harmonic_search vs mlp_tuned): gap={fair_gap:+.6f} RMSE (positive favors harmonic_search)."
        )

    findings.append(
        "Interpretation: fixed period Fourier terms can dominate when seasonality is known in advance, while tuned MLP often improves on non-periodic dynamics."
    )
    return findings


def generate_plots(
    run_dir: Path,
    ts_test: pd.Series,
    holdout: pd.DataFrame,
    metrics: pd.DataFrame,
) -> list[Path]:
    artifacts: list[Path] = []
    if plt is None:
        return artifacts

    plot_png = run_dir / "holdout_predictions.png"
    fig, ax = plt.subplots(figsize=(11, 5))
    ax.plot(ts_test, holdout["actual"], label="actual", linewidth=2.0)
    for col in holdout.columns:
        if col.startswith("pred_"):
            ax.plot(ts_test, holdout[col], label=col.replace("pred_", ""), linewidth=1.1)
    ax.set_title("Holdout Forecast Comparison")
    ax.set_ylabel("value")
    ax.legend(loc="best", fontsize=8)
    fig.tight_layout()
    fig.savefig(plot_png, dpi=150)
    plt.close(fig)
    artifacts.append(plot_png)

    rmse_png = run_dir / "rmse_rank.png"
    valid = metrics.dropna(subset=["rmse"]).copy()
    fig2, ax2 = plt.subplots(figsize=(9, 4.8))
    ax2.bar(valid["model"], valid["rmse"], color="#57a0ff")
    ax2.set_title("RMSE by Model (lower is better)")
    ax2.set_ylabel("rmse")
    ax2.tick_params(axis="x", labelrotation=20)
    fig2.tight_layout()
    fig2.savefig(rmse_png, dpi=150)
    plt.close(fig2)
    artifacts.append(rmse_png)

    if PdfPages is not None:
        pdf_path = run_dir / "report.pdf"
        with PdfPages(pdf_path) as pdf:
            fig3, ax3 = plt.subplots(figsize=(11, 5))
            ax3.plot(ts_test, holdout["actual"], label="actual", linewidth=2.0)
            for col in holdout.columns:
                if col.startswith("pred_"):
                    ax3.plot(ts_test, holdout[col], label=col.replace("pred_", ""), linewidth=1.1)
            ax3.set_title("Holdout Forecast Comparison")
            ax3.legend(loc="best", fontsize=8)
            fig3.tight_layout()
            pdf.savefig(fig3)
            plt.close(fig3)

            fig4, ax4 = plt.subplots(figsize=(9, 4.8))
            ax4.bar(valid["model"], valid["rmse"], color="#57a0ff")
            ax4.set_title("RMSE by Model")
            ax4.tick_params(axis="x", labelrotation=20)
            fig4.tight_layout()
            pdf.savefig(fig4)
            plt.close(fig4)
        artifacts.append(pdf_path)

    return artifacts


def append_ledger(
    ledger_path: Path,
    run_id: str,
    manifest_path: Path,
    summary_path: Path,
    files_count: int,
    input_path: Path,
    input_sha256: str,
) -> dict[str, Any]:
    prev = read_last_nonempty_json_line(ledger_path)
    prev_hash = prev.get("entry_sha256") if isinstance(prev, dict) else None

    row = {
        "run_utc": now_utc(),
        "test_name": "harmonic_backprop_proofpack",
        "run_id": run_id,
        "manifest_sha256": sha256_file(manifest_path),
        "summary_sha256": sha256_file(summary_path),
        "prev_entry_sha256": prev_hash,
        "files_count": int(files_count),
        "input_path": str(input_path),
        "input_sha256": input_sha256,
    }

    to_hash = json.dumps(row, sort_keys=True).encode("utf-8")
    row["entry_sha256"] = hashlib.sha256(to_hash).hexdigest()

    ledger_path.parent.mkdir(parents=True, exist_ok=True)
    with ledger_path.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(row) + "\n")
    return row


def run(args: argparse.Namespace) -> dict[str, Any]:
    input_path = Path(args.input_csv).resolve()
    payload = load_series(input_path, value_col=args.value_col, date_col=args.date_col)

    y = payload.frame["value"].to_numpy(dtype=float)
    y_train, y_test = split_series(y, test_frac=args.test_frac, min_test=args.min_test)

    metrics, holdout = evaluate_models(y_train, y_test)

    n_train = len(y_train)
    ts_test = payload.frame["ts"].iloc[n_train:].reset_index(drop=True)
    run_id = now_utc_compact() + (f"_{args.run_tag}" if args.run_tag else "")

    output_root = Path(args.output_root)
    run_dir = output_root / run_id
    run_dir.mkdir(parents=True, exist_ok=True)

    cleaned_csv = run_dir / "cleaned_input.csv"
    payload.frame.to_csv(cleaned_csv, index=False)

    holdout_out = holdout.copy()
    holdout_out.insert(0, "ts", ts_test.astype(str))
    holdout_csv = run_dir / "holdout_predictions.csv"
    holdout_out.to_csv(holdout_csv, index=False)

    metrics_csv = run_dir / "metrics.csv"
    metrics.to_csv(metrics_csv, index=False)

    pivot = metrics[["model", "rmse"]].set_index("model").T
    pivot_csv = run_dir / "metrics_pivot.csv"
    pivot.to_csv(pivot_csv)

    findings = build_findings(metrics)
    findings_txt = run_dir / "findings.txt"
    findings_txt.write_text("\n".join(findings) + "\n", encoding="utf-8")

    summary = {
        "run_id": run_id,
        "generated_utc": now_utc(),
        "test_name": "harmonic_backprop_proofpack",
        "input": {
            "path": str(payload.source_path),
            "sha256": payload.source_sha256,
            "value_col": payload.value_col,
            "date_col": payload.date_col,
            "rows_total": payload.rows_total,
            "rows_valid": payload.rows_valid,
        },
        "split": {
            "n_train": len(y_train),
            "n_test": len(y_test),
            "test_frac": float(args.test_frac),
        },
        "winner": metrics.iloc[0].to_dict() if not metrics.empty else {},
        "ranked_models": metrics.to_dict(orient="records"),
        "findings": findings,
    }

    summary_path = run_dir / "summary.json"
    summary_path.write_text(json.dumps(summary, indent=2), encoding="utf-8")

    plot_artifacts = generate_plots(run_dir, ts_test=ts_test, holdout=holdout, metrics=metrics)

    files_for_manifest = [
        cleaned_csv,
        holdout_csv,
        metrics_csv,
        pivot_csv,
        findings_txt,
        summary_path,
    ] + plot_artifacts

    manifest = {
        "run_id": run_id,
        "generated_utc": now_utc(),
        "files": {
            str(path.relative_to(run_dir)): sha256_file(path)
            for path in files_for_manifest
            if path.exists()
        },
    }

    manifest_path = run_dir / "manifest.sha256.json"
    manifest_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")

    latest_pointer = {
        "generated_utc": now_utc(),
        "run_id": run_id,
        "run_dir": str(run_dir),
        "summary_path": str(summary_path),
        "manifest_path": str(manifest_path),
        "input_path": str(payload.source_path),
        "input_sha256": payload.source_sha256,
    }
    latest_path = output_root / "latest.json"
    latest_path.write_text(json.dumps(latest_pointer, indent=2), encoding="utf-8")

    ledger_entry = append_ledger(
        ledger_path=Path(args.ledger),
        run_id=run_id,
        manifest_path=manifest_path,
        summary_path=summary_path,
        files_count=len(manifest["files"]),
        input_path=payload.source_path,
        input_sha256=payload.source_sha256,
    )

    result = {
        "run_id": run_id,
        "run_dir": str(run_dir),
        "winner": summary["winner"],
        "ledger_entry_sha256": ledger_entry.get("entry_sha256"),
        "manifest_sha256": sha256_file(manifest_path),
    }

    if not args.quiet:
        print("=== harmonic_backprop_proofpack ===")
        print(f"run_id={result['run_id']}")
        print(f"input={payload.source_path}")
        print(f"rows_valid={payload.rows_valid} train={len(y_train)} test={len(y_test)}")
        print(f"winner={summary['winner']}")
        print(f"run_dir={result['run_dir']}")
        print(f"ledger_entry_sha256={result['ledger_entry_sha256']}")

    return result


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run stack-native harmonic vs backprop benchmark and emit hash-verifiable proof artifacts."
    )
    parser.add_argument("--input-csv", required=True, help="Path to input CSV")
    parser.add_argument("--value-col", default="", help="Optional numeric target column name")
    parser.add_argument("--date-col", default="", help="Optional date/timestamp column name")
    parser.add_argument("--output-root", default=str(DEFAULT_OUTPUT_ROOT), help="Directory for run artifacts")
    parser.add_argument("--ledger", default=str(DEFAULT_LEDGER), help="JSONL ledger file path")
    parser.add_argument("--test-frac", type=float, default=0.2, help="Holdout fraction (default: 0.2)")
    parser.add_argument("--min-test", type=int, default=12, help="Minimum holdout rows (default: 12)")
    parser.add_argument("--run-tag", default="", help="Optional run tag suffix")
    parser.add_argument("--quiet", action="store_true", help="Suppress console summary")
    return parser.parse_args()


if __name__ == "__main__":
    run(parse_args())
