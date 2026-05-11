from __future__ import annotations

import argparse
import hashlib
import json
import math
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
import urllib.error
import urllib.request
import warnings

import numpy as np
import pandas as pd

try:
    import polars as pl
except Exception:
    pl = None

try:
    import duckdb
except Exception:
    duckdb = None

try:
    import orjson
except Exception:
    orjson = None

warnings.filterwarnings("ignore", category=UserWarning, message=".*Could not infer format.*")
warnings.filterwarnings("ignore", category=UserWarning, message=".*CSV malformed.*")
warnings.filterwarnings("ignore", category=RuntimeWarning, message=".*invalid value encountered in cast.*")


TIME_CANDIDATES = [
    "date",
    "datetime",
    "timestamp",
    "time",
    "period",
    "observation_date",
    "month",
    "year",
]

VALUE_PRIORITY = [
    "close",
    "adj_close",
    "adj close",
    "price",
    "last",
    "settle",
    "mid",
    "bid",
    "ask",
    "open",
    "high",
    "low",
    "volume",
    "value",
    "nav",
    "signal",
]

CAPITAL_SCENARIOS = [1_000_000, 10_000_000, 100_000_000, 1_000_000_000]

TEXT_ENCODINGS = ("utf-8", "utf-8-sig", "cp1252", "latin-1")
SUPPORTED_EXTENSIONS = {
    ".csv",
    ".tsv",
    ".txt",
    ".json",
    ".jsonl",
    ".ndjson",
    ".parquet",
    ".feather",
    ".xlsx",
    ".xls",
}
DEFAULT_SOURCE_DIRS = [
    "clean_data",
    "data",
    "live_data",
    "INSTITUTIONAL_STACK_V2/data",
]
EXCLUDED_DIR_NAMES = {
    ".git",
    "node_modules",
    "site-packages",
    "__pycache__",
    "venv",
    ".venv",
    "venv3.11",
    "out",
    "output",
}


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def annualized_sharpe(returns: pd.Series, periods_per_year: int = 252) -> float:
    r = returns.replace([np.inf, -np.inf], np.nan).dropna()
    if len(r) < 2:
        return float("nan")
    std = float(r.std())
    if std == 0.0:
        return float("nan")
    return float((r.mean() / std) * math.sqrt(periods_per_year))


def win_rate(returns: pd.Series) -> float:
    r = returns.replace([np.inf, -np.inf], np.nan).dropna()
    trades = r[r != 0.0]
    if len(trades) == 0:
        return float("nan")
    return float((trades > 0).mean())


def cagr_from_returns(returns: pd.Series, periods_per_year: int = 252) -> float:
    r = returns.replace([np.inf, -np.inf], np.nan).dropna()
    if len(r) < 2:
        return float("nan")
    eq = (1.0 + r).cumprod()
    if (eq <= 0).any():
        return float("nan")
    years = len(eq) / float(periods_per_year)
    if years <= 0 or float(eq.iloc[0]) <= 0:
        return float("nan")
    return float((float(eq.iloc[-1]) / float(eq.iloc[0])) ** (1.0 / years) - 1.0)


def max_drawdown(returns: pd.Series) -> float:
    r = returns.replace([np.inf, -np.inf], np.nan).dropna()
    if len(r) < 2:
        return float("nan")
    eq = (1.0 + r).cumprod()
    dd = eq / eq.cummax() - 1.0
    return float(dd.min())


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def fast_json_loads(payload: str) -> tuple[Any, str]:
    if orjson is not None:
        try:
            return orjson.loads(payload), "orjson"
        except Exception:
            pass
    return json.loads(payload), "json"


def normalize_extensions(raw_extensions: str) -> set[str]:
    parts = [p.strip().lower() for p in str(raw_extensions).split(",") if p.strip()]
    if not parts:
        return set(SUPPORTED_EXTENSIONS)

    normalized: set[str] = set()
    for ext in parts:
        normalized.add(ext if ext.startswith(".") else f".{ext}")
    return normalized


def resolve_source_dirs(root: Path, stack_root: Path, raw_dirs: list[str] | None) -> list[Path]:
    tokens = list(raw_dirs) if raw_dirs else list(DEFAULT_SOURCE_DIRS)
    resolved: list[Path] = []
    seen: set[str] = set()

    for token in tokens:
        candidate = Path(token)
        if not candidate.is_absolute():
            if token.startswith("stack:"):
                candidate = stack_root / token.split(":", 1)[1]
            else:
                candidate = root / token

        key = str(candidate.resolve(strict=False)).lower()
        if key in seen:
            continue
        seen.add(key)
        resolved.append(candidate)

    return resolved


def discover_dataset_files(source_dirs: list[Path], allowed_ext: set[str]) -> list[Path]:
    files: list[Path] = []
    seen: set[str] = set()

    for base in source_dirs:
        if not base.exists() or not base.is_dir():
            continue

        for path in base.rglob("*"):
            if not path.is_file():
                continue
            if path.name.startswith("~$"):
                continue
            if path.suffix.lower() not in allowed_ext:
                continue

            parts_lower = {part.lower() for part in path.parts}
            if parts_lower.intersection(EXCLUDED_DIR_NAMES):
                continue

            key = str(path.resolve(strict=False)).lower()
            if key in seen:
                continue
            seen.add(key)
            files.append(path)

    return sorted(files)


def try_read_delimited_with_polars(path: Path, forced_sep: str | None = None) -> pd.DataFrame | None:
    if pl is None:
        return None

    separators = [forced_sep] if forced_sep is not None else [",", "\t", ";", "|"]
    for separator in separators:
        try:
            frame = pl.read_csv(
                path,
                separator=separator,
                infer_schema_length=4096,
                ignore_errors=True,
                null_values=["", "null", "None", "NA", "NaN"],
            )
            if forced_sep is None and frame.width == 1:
                continue
            return frame.to_pandas()
        except Exception:
            continue

    return None


def try_read_delimited_with_duckdb(path: Path, forced_sep: str | None = None) -> pd.DataFrame | None:
    if duckdb is None:
        return None

    separators = [forced_sep] if forced_sep is not None else [",", "\t", ";", "|"]
    path_sql = str(path).replace("'", "''")

    for separator in separators:
        sep_sql = str(separator).replace("'", "''")
        sql = (
            "SELECT * FROM read_csv_auto("
            f"'{path_sql}', delim='{sep_sql}', header=true, sample_size=8192, ignore_errors=true"
            ")"
        )
        try:
            conn = duckdb.connect(database=":memory:")
            try:
                frame = conn.execute(sql).fetch_df()
            finally:
                conn.close()

            if forced_sep is None and len(frame.columns) == 1:
                continue
            return frame
        except Exception:
            continue

    return None


def safe_read_delimited(path: Path, forced_sep: str | None = None) -> tuple[pd.DataFrame, str]:
    polars_df = try_read_delimited_with_polars(path, forced_sep=forced_sep)
    if polars_df is not None:
        return polars_df, "polars_csv"

    duckdb_df = try_read_delimited_with_duckdb(path, forced_sep=forced_sep)
    if duckdb_df is not None:
        return duckdb_df, "duckdb_csv"

    attempts: list[dict[str, Any]] = []
    if forced_sep is None:
        attempts.extend(
            [
                {"sep": ",", "engine": "c"},
                {"sep": "\t", "engine": "c"},
                {"sep": ";", "engine": "c"},
                {"sep": "|", "engine": "c"},
                {"sep": None, "engine": "python"},
            ]
        )
    else:
        attempts.append({"sep": forced_sep, "engine": "c"})
        attempts.append({"sep": forced_sep, "engine": "python"})

    for enc in TEXT_ENCODINGS:
        for attempt in attempts:
            kwargs: dict[str, Any] = {
                "encoding": enc,
                "low_memory": False,
                "sep": attempt["sep"],
            }
            if attempt["engine"] == "python":
                kwargs["engine"] = "python"
            try:
                df = pd.read_csv(path, **kwargs)
                if isinstance(df, pd.DataFrame):
                    if forced_sep is None and attempt["sep"] in {",", "\t", ";", "|"} and len(df.columns) == 1:
                        continue
                    return df, "pandas_csv"
            except Exception:
                continue

    raise ValueError(f"Failed reading delimited file: {path}")


def safe_read_json(path: Path) -> tuple[pd.DataFrame, str]:
    for enc in TEXT_ENCODINGS:
        try:
            text = path.read_text(encoding=enc)
        except Exception:
            continue

        stripped = text.strip()
        if not stripped:
            return pd.DataFrame()

        try:
            payload, parser_name = fast_json_loads(stripped)
        except Exception:
            continue

        if isinstance(payload, list):
            if not payload:
                return pd.DataFrame(), parser_name
            if all(isinstance(item, dict) for item in payload):
                return pd.json_normalize(payload, sep="_"), parser_name
            return pd.DataFrame({"value": payload}), parser_name

        if isinstance(payload, dict):
            try:
                frame = pd.DataFrame(payload)
                if isinstance(frame, pd.DataFrame) and not frame.empty:
                    return frame, parser_name
            except Exception:
                pass
            return pd.json_normalize([payload], sep="_"), parser_name

        return pd.DataFrame({"value": [payload]}), parser_name

    raise ValueError(f"Failed reading json: {path}")


def safe_read_json_lines(path: Path) -> tuple[pd.DataFrame, str]:
    if pl is not None:
        try:
            frame = pl.read_ndjson(path)
            return frame.to_pandas(), "polars_ndjson"
        except Exception:
            pass

    for enc in TEXT_ENCODINGS:
        try:
            text = path.read_text(encoding=enc)
        except Exception:
            continue

        rows: list[Any] = []
        valid = True
        for line in text.splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                row_payload, _ = fast_json_loads(line)
                rows.append(row_payload)
            except Exception:
                valid = False
                break

        if not valid:
            continue
        if not rows:
            return pd.DataFrame(), "json_lines"

        if all(isinstance(item, dict) for item in rows):
            return pd.json_normalize(rows, sep="_"), "json_lines"
        return pd.DataFrame({"value": rows}), "json_lines"

    raise ValueError(f"Failed reading json lines: {path}")


def safe_read_frame(path: Path) -> tuple[pd.DataFrame, str]:
    ext = path.suffix.lower()
    if ext == ".csv":
        return safe_read_delimited(path, forced_sep=None)
    if ext == ".tsv":
        return safe_read_delimited(path, forced_sep="\t")
    if ext == ".txt":
        return safe_read_delimited(path, forced_sep=None)
    if ext == ".json":
        return safe_read_json(path)
    if ext in {".jsonl", ".ndjson"}:
        return safe_read_json_lines(path)
    if ext == ".parquet":
        if pl is not None:
            try:
                return pl.read_parquet(path).to_pandas(), "polars_parquet"
            except Exception:
                pass
        return pd.read_parquet(path), "pandas_parquet"
    if ext == ".feather":
        if pl is not None:
            try:
                return pl.read_ipc(path).to_pandas(), "polars_feather"
            except Exception:
                pass
        return pd.read_feather(path), "pandas_feather"
    if ext in {".xlsx", ".xls"}:
        try:
            return pd.read_excel(path, sheet_name=0, engine="calamine"), "pandas_excel_calamine"
        except Exception:
            return pd.read_excel(path, sheet_name=0), "pandas_excel"
    raise ValueError(f"Unsupported extension: {ext}")


def looks_like_epoch_values(series: pd.Series) -> bool:
    numeric = pd.to_numeric(series, errors="coerce")
    valid = numeric.dropna()
    if valid.empty:
        return False
    return float(valid.abs().median()) >= 1e8


def looks_like_datetime_strings(series: pd.Series) -> bool:
    sample = series.dropna().astype(str).str.strip()
    if sample.empty:
        return False
    sample = sample.head(200)

    separators = sample.str.contains(r"[-/:T]", regex=True, na=False)
    alpha_month = sample.str.contains(r"[A-Za-z]{3}", regex=True, na=False)
    ratio = float((separators | alpha_month).mean())
    return ratio >= 0.35


def parse_datetime_series(series: pd.Series, col_name: str = "") -> pd.Series:
    numeric = pd.to_numeric(series, errors="coerce")
    numeric_ratio = float(numeric.notna().mean())
    name_time_like = is_time_like_name(str(col_name))

    empty_dt = pd.Series(pd.NaT, index=series.index, dtype="datetime64[ns, UTC]")

    if numeric_ratio >= 0.8:
        if not name_time_like and not looks_like_epoch_values(series):
            return empty_dt

        parsed_best = empty_dt
        best_ratio = 0.0
    else:
        if not name_time_like and not looks_like_datetime_strings(series):
            return empty_dt

        parsed_best = pd.to_datetime(series, errors="coerce", utc=True)
        best_ratio = float(parsed_best.notna().mean())

    for unit in ("s", "ms", "us", "ns"):
        try:
            parsed = pd.to_datetime(numeric, unit=unit, errors="coerce", utc=True)
        except Exception:
            continue

        ratio = float(parsed.notna().mean())
        if ratio < best_ratio:
            continue

        valid = parsed.dropna()
        if valid.empty:
            continue
        median_year = float(valid.dt.year.median())
        if median_year < 1960 or median_year > 2105:
            continue

        best_ratio = ratio
        parsed_best = parsed

    return parsed_best


def detect_time_column(df: pd.DataFrame) -> str | None:
    lower_to_col = {str(c).strip().lower(): str(c).strip() for c in df.columns}
    for candidate in TIME_CANDIDATES:
        if candidate in lower_to_col:
            return lower_to_col[candidate]

    sample = df.head(5000)
    best_col: str | None = None
    best_ratio = 0.0
    for col in sample.columns:
        col_name = str(col)
        series = sample[col]
        if pd.api.types.is_numeric_dtype(series):
            if not is_time_like_name(col_name) and not looks_like_epoch_values(series):
                continue
        try:
            parsed = parse_datetime_series(series, col_name=col_name)
            ratio = float(parsed.notna().mean())
        except Exception:
            ratio = 0.0
        if ratio > best_ratio:
            best_ratio = ratio
            best_col = col_name

    if best_col is not None and best_ratio >= 0.75:
        return best_col
    return None


def is_time_like_name(name: str) -> bool:
    low = name.strip().lower()
    tokens = ["date", "time", "timestamp", "datetime", "period", "_dt", "year", "month"]
    return any(token in low for token in tokens)


def prioritized_value_columns(df: pd.DataFrame, time_col: str, min_rows: int) -> list[str]:
    candidates: list[str] = []
    for col in df.columns:
        col_name = str(col)
        if col_name == time_col:
            continue
        if is_time_like_name(col_name):
            continue
        numeric = pd.to_numeric(df[col_name], errors="coerce")
        if int(numeric.notna().sum()) >= min_rows:
            idx = np.arange(len(numeric), dtype=float)
            vals = numeric.ffill().bfill().to_numpy(dtype=float)
            if len(vals) > 10 and np.isfinite(vals).all():
                idx_center = idx - float(idx.mean())
                val_center = vals - float(np.mean(vals))
                idx_norm = float(np.sqrt(np.sum(idx_center * idx_center)))
                val_abs_max = float(np.max(np.abs(val_center)))
                if val_abs_max > 0.0:
                    val_norm = float(np.sqrt(np.sum((val_center / val_abs_max) ** 2)) * val_abs_max)
                else:
                    val_norm = 0.0
                if idx_norm > 0.0 and val_norm > 0.0:
                    corr = float(np.sum(idx_center * val_center) / (idx_norm * val_norm))
                    if abs(corr) > 0.9999:
                        continue
            candidates.append(col_name)

    if not candidates:
        return []

    def _score(col_name: str) -> tuple[int, int]:
        low = col_name.lower()
        for idx, token in enumerate(VALUE_PRIORITY):
            if token in low:
                return (0, idx)
        return (1, len(low))

    return sorted(candidates, key=_score)


def extract_series_from_file(
    path: Path,
    min_rows: int,
    min_span_years: float,
    max_cols_per_file: int,
    max_file_bytes: int,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    inventory_rows: list[dict[str, Any]] = []
    series_payloads: list[dict[str, Any]] = []
    file_type = path.suffix.lower().lstrip(".")

    try:
        file_bytes = int(path.stat().st_size)
    except Exception:
        file_bytes = 0

    if max_file_bytes > 0 and file_bytes > max_file_bytes:
        inventory_rows.append(
            {
                "file_path": str(path),
                "file_type": file_type,
                "read_engine": "skipped_large",
                "series_name": "",
                "column": "",
                "rows": 0,
                "start_utc": "",
                "end_utc": "",
                "span_years": 0.0,
                "time_source": "none",
                "backtest_ready": False,
                "reason": f"file_too_large:{file_bytes}",
            }
        )
        return inventory_rows, series_payloads

    try:
        df, read_engine = safe_read_frame(path)
    except Exception as ex:
        inventory_rows.append(
            {
                "file_path": str(path),
                "file_type": file_type,
                "read_engine": "read_error",
                "series_name": "",
                "column": "",
                "rows": 0,
                "start_utc": "",
                "end_utc": "",
                "span_years": 0.0,
                "backtest_ready": False,
                "reason": f"read_error:{ex}",
            }
        )
        return inventory_rows, series_payloads

    if df.empty:
        inventory_rows.append(
            {
                "file_path": str(path),
                "file_type": file_type,
                "read_engine": read_engine,
                "series_name": "",
                "column": "",
                "rows": 0,
                "start_utc": "",
                "end_utc": "",
                "span_years": 0.0,
                "backtest_ready": False,
                "reason": "empty_file",
            }
        )
        return inventory_rows, series_payloads

    df.columns = [str(c).strip() for c in df.columns]
    time_col = detect_time_column(df)
    time_source = "observed"

    if not time_col:
        value_cols = prioritized_value_columns(df, time_col="", min_rows=min_rows)
        if not value_cols:
            inventory_rows.append(
                {
                    "file_path": str(path),
                    "file_type": file_type,
                    "read_engine": read_engine,
                    "series_name": "",
                    "column": "",
                    "rows": int(len(df)),
                    "start_utc": "",
                    "end_utc": "",
                    "span_years": 0.0,
                    "time_source": "none",
                    "backtest_ready": False,
                    "reason": "no_time_column_and_no_numeric",
                }
            )
            return inventory_rows, series_payloads
        synthetic_dt = pd.date_range(start="2000-01-01", periods=len(df), freq="D", tz="UTC")
        df = df.assign(_dt=synthetic_dt)
        time_source = "synthetic"
    else:
        dt = parse_datetime_series(df[time_col], col_name=time_col)
        df = df.assign(_dt=dt)
        df = df[df["_dt"].notna()].copy()
        if looks_like_epoch_values(df[time_col]):
            time_source = "epoch"

    if df.empty:
        inventory_rows.append(
            {
                "file_path": str(path),
                "file_type": file_type,
                "read_engine": read_engine,
                "series_name": "",
                "column": "",
                "rows": 0,
                "start_utc": "",
                "end_utc": "",
                "span_years": 0.0,
                "time_source": time_source,
                "backtest_ready": False,
                "reason": "no_valid_datetime_rows",
            }
        )
        return inventory_rows, series_payloads

    value_cols = prioritized_value_columns(df, time_col=time_col, min_rows=min_rows)
    if not value_cols:
        inventory_rows.append(
            {
                "file_path": str(path),
                "file_type": file_type,
                "read_engine": read_engine,
                "series_name": "",
                "column": "",
                "rows": int(len(df)),
                "start_utc": "",
                "end_utc": "",
                "span_years": 0.0,
                "backtest_ready": False,
                "reason": "no_numeric_column",
            }
        )
        return inventory_rows, series_payloads

    for col in value_cols[:max_cols_per_file]:
        sub = pd.DataFrame(
            {
                "dt": df["_dt"],
                "value": pd.to_numeric(df[col], errors="coerce"),
            }
        ).dropna(subset=["dt", "value"])

        if sub.empty:
            inventory_rows.append(
                {
                    "file_path": str(path),
                    "file_type": file_type,
                    "read_engine": read_engine,
                    "series_name": f"{path.stem}__{col}",
                    "column": col,
                    "rows": 0,
                    "start_utc": "",
                    "end_utc": "",
                    "span_years": 0.0,
                    "time_source": time_source,
                    "backtest_ready": False,
                    "reason": "no_valid_numeric_rows",
                }
            )
            continue

        sub = sub.sort_values("dt").drop_duplicates(subset=["dt"], keep="last")
        rows = int(len(sub))
        start_ts = sub["dt"].iloc[0]
        end_ts = sub["dt"].iloc[-1]
        span_days = max(0, int((end_ts - start_ts).days))
        span_years = span_days / 365.25

        reasons: list[str] = []
        if rows < min_rows:
            reasons.append("rows_below_threshold")
        if span_years < min_span_years:
            reasons.append("span_below_threshold")

        ready = len(reasons) == 0
        reason_text = "ready" if ready else ";".join(reasons)

        series_name = f"{path.stem}__{col}".replace(" ", "_")
        inventory_rows.append(
            {
                "file_path": str(path),
                "file_type": file_type,
                "read_engine": read_engine,
                "series_name": series_name,
                "column": col,
                "rows": rows,
                "start_utc": start_ts.isoformat(),
                "end_utc": end_ts.isoformat(),
                "span_years": round(span_years, 3),
                "time_source": time_source,
                "backtest_ready": ready,
                "reason": reason_text,
            }
        )

        if ready:
            fingerprint = hashlib.sha1(
                pd.util.hash_pandas_object(sub.set_index("dt")["value"], index=True).values.tobytes()
            ).hexdigest()
            series_payloads.append(
                {
                    "series_name": series_name,
                    "file_path": str(path),
                    "file_type": file_type,
                    "read_engine": read_engine,
                    "column": col,
                    "rows": rows,
                    "span_years": span_years,
                    "time_source": time_source,
                    "fingerprint": fingerprint,
                    "values": sub.set_index("dt")["value"].astype(float),
                }
            )

    return inventory_rows, series_payloads


def walk_forward_backtest(
    values: pd.Series,
    train_bars: int,
    test_bars: int,
    cost_bps: float,
    windows: list[int],
) -> dict[str, float] | None:
    px = values.sort_index().astype(float)
    prev = px.shift(1).abs().clip(lower=1e-9)
    ret = ((px - px.shift(1)) / prev).replace([np.inf, -np.inf], np.nan)
    ret = ret.clip(-0.99, 0.99).dropna()

    total_bars = len(ret)
    dynamic_train = min(train_bars, int(total_bars * 0.65))
    dynamic_test = min(test_bars, int(total_bars * 0.20))
    dynamic_train = max(120, dynamic_train)
    dynamic_test = max(30, dynamic_test)

    if dynamic_train + dynamic_test + 10 > total_bars:
        dynamic_train = max(60, int(total_bars * 0.55))
        dynamic_test = max(20, int(total_bars * 0.20))

    if dynamic_train + dynamic_test + 10 > total_bars:
        return None

    strat_chunks: list[pd.Series] = []
    base_chunks: list[pd.Series] = []
    pos_chunks: list[pd.Series] = []
    chosen_windows: list[int] = []

    for start in range(0, len(ret) - dynamic_train - dynamic_test + 1, dynamic_test):
        train = ret.iloc[start : start + dynamic_train]
        test = ret.iloc[start + dynamic_train : start + dynamic_train + dynamic_test]

        best_window: int | None = None
        best_sharpe = float("-inf")

        for w in windows:
            pos = np.sign(train.rolling(w).mean()).shift(1).fillna(0.0)
            turnover = pos.diff().abs().fillna(0.0)
            strat = (pos * train) - (turnover * (cost_bps / 10000.0))
            sh = annualized_sharpe(strat)
            if np.isfinite(sh) and sh > best_sharpe:
                best_sharpe = sh
                best_window = w

        if best_window is None:
            continue

        past = ret.iloc[: start + dynamic_train + dynamic_test]
        pos_full = np.sign(past.rolling(best_window).mean()).shift(1).fillna(0.0)
        pos_test = pos_full.iloc[start + dynamic_train : start + dynamic_train + dynamic_test]
        turnover_test = pos_test.diff().abs().fillna(0.0)
        strat_test = (pos_test * test) - (turnover_test * (cost_bps / 10000.0))

        strat_chunks.append(strat_test)
        base_chunks.append(test)
        pos_chunks.append(pos_test)
        chosen_windows.append(best_window)

    if not strat_chunks:
        return None

    strat_ret = pd.concat(strat_chunks).sort_index()
    base_ret = pd.concat(base_chunks).sort_index()
    pos_all = pd.concat(pos_chunks).sort_index()

    edge = strat_ret - base_ret
    result = {
        "bars_tested": int(len(strat_ret)),
        "windows_used": int(len(chosen_windows)),
        "train_bars_used": int(dynamic_train),
        "test_bars_used": int(dynamic_test),
        "median_window": float(np.median(chosen_windows)) if chosen_windows else float("nan"),
        "strategy_sharpe": annualized_sharpe(strat_ret),
        "baseline_sharpe": annualized_sharpe(base_ret),
        "sharpe_delta": annualized_sharpe(strat_ret) - annualized_sharpe(base_ret),
        "strategy_cagr": cagr_from_returns(strat_ret),
        "baseline_cagr": cagr_from_returns(base_ret),
        "cagr_delta": cagr_from_returns(strat_ret) - cagr_from_returns(base_ret),
        "strategy_max_dd": max_drawdown(strat_ret),
        "baseline_max_dd": max_drawdown(base_ret),
        "drawdown_delta": max_drawdown(base_ret) - max_drawdown(strat_ret),
        "strategy_win_rate": win_rate(strat_ret),
        "baseline_win_rate": win_rate(base_ret),
        "edge_bps_per_bar": float(edge.mean() * 10000.0),
        "exposure": float((pos_all != 0.0).mean()),
    }
    return result


def load_missing_catalog_entries(catalog_path: Path, include_stale_clean_paths: bool) -> pd.DataFrame:
    if not catalog_path.exists():
        return pd.DataFrame()

    try:
        df = pd.read_csv(catalog_path, low_memory=False)
    except Exception:
        return pd.DataFrame()

    if df.empty:
        return pd.DataFrame()

    status = df.get("status", pd.Series([""] * len(df))).astype(str).str.lower().fillna("")
    clean_path = df.get("clean_path", pd.Series([""] * len(df))).astype(str).fillna("")

    def _exists(value: str) -> bool:
        value = value.strip()
        return bool(value) and Path(value).exists()

    clean_exists = clean_path.apply(_exists)
    reason = df.get("reason", pd.Series([""] * len(df))).astype(str).fillna("")

    missing_mask = status != "cleaned"
    if include_stale_clean_paths:
        missing_mask = missing_mask | ((status == "cleaned") & (~clean_exists))
    missing = df.loc[missing_mask].copy()
    if missing.empty:
        return missing

    missing["clean_path_exists"] = clean_exists[missing_mask].values
    missing["status_normalized"] = status[missing_mask].values
    missing["reason_normalized"] = reason[missing_mask].values
    return missing


def build_opportunity_table(results_df: pd.DataFrame) -> pd.DataFrame:
    positive = results_df[results_df["cagr_delta"] > 0.0].copy()
    median_edge = float(positive["cagr_delta"].median()) if not positive.empty else 0.0
    q75_edge = float(positive["cagr_delta"].quantile(0.75)) if not positive.empty else 0.0
    conservative_edge = min(max(median_edge, 0.0), 0.10)

    rows: list[dict[str, Any]] = []
    for capital in CAPITAL_SCENARIOS:
        rows.append(
            {
                "capital_usd": float(capital),
                "gain_if_0p1pct_edge_usd": float(capital * 0.001),
                "gain_if_conservative_edge_usd": float(capital * conservative_edge),
                "gain_if_median_cagr_delta_usd": float(capital * median_edge),
                "gain_if_q75_cagr_delta_usd": float(capital * q75_edge),
                "conservative_edge_rate": conservative_edge,
                "median_cagr_delta": median_edge,
                "q75_cagr_delta": q75_edge,
            }
        )

    return pd.DataFrame(rows)


def post_json(url: str, payload: dict[str, Any]) -> tuple[bool, str]:
    body = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=body,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=10) as response:
            data = response.read().decode("utf-8", errors="ignore")
            return True, f"HTTP {response.status}: {data[:240]}"
    except urllib.error.HTTPError as ex:
        detail = ex.read().decode("utf-8", errors="ignore")
        return False, f"HTTP {ex.code}: {detail[:240]}"
    except Exception as ex:
        return False, str(ex)


def main() -> int:
    parser = argparse.ArgumentParser(description="Investor-grade dataset/backtest proof sweep")
    parser.add_argument("--root", default=r"C:\LumaTrader")
    parser.add_argument("--stack-root", default=r"C:\LumaTrader\INSTITUTIONAL_STACK_V2")
    parser.add_argument(
        "--source-dirs",
        nargs="*",
        default=None,
        help="Relative/absolute dataset directories. Supports stack: prefix for stack-root paths.",
    )
    parser.add_argument(
        "--extensions",
        default="csv,tsv,txt,json,jsonl,ndjson,parquet,feather,xlsx,xls",
        help="Comma-separated file extensions to include.",
    )
    parser.add_argument("--min-rows", type=int, default=252)
    parser.add_argument("--min-span-years", type=float, default=1.0)
    parser.add_argument("--max-cols-per-file", type=int, default=2)
    parser.add_argument("--max-file-mb", type=int, default=512)
    parser.add_argument("--max-files", type=int, default=0)
    parser.add_argument("--max-series", type=int, default=0)
    parser.add_argument("--train-bars", type=int, default=756)
    parser.add_argument("--test-bars", type=int, default=126)
    parser.add_argument("--cost-bps", type=float, default=5.0)
    parser.add_argument("--include-stale-clean-paths", action="store_true")
    parser.add_argument("--push-nodered", action="store_true")
    parser.add_argument("--nodered-base", default="http://127.0.0.1:8787")
    args = parser.parse_args()

    root = Path(args.root)
    stack_root = Path(args.stack_root)
    clean_dir = root / "clean_data"
    catalog_path = clean_dir / "dataset_catalog.csv"
    source_dirs = resolve_source_dirs(root=root, stack_root=stack_root, raw_dirs=args.source_dirs)
    allowed_extensions = normalize_extensions(args.extensions)
    max_file_bytes = int(max(0, args.max_file_mb) * 1024 * 1024)

    stamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    out_dir = root / "out" / "ops" / f"investor_proof_sweep_{stamp}"
    out_dir.mkdir(parents=True, exist_ok=True)

    dataset_files = discover_dataset_files(source_dirs=source_dirs, allowed_ext=allowed_extensions)
    if args.max_files and args.max_files > 0:
        dataset_files = dataset_files[: int(args.max_files)]
    if not dataset_files:
        discovered = [str(p) for p in source_dirs]
        raise SystemExit(
            "No dataset files found for configured scan roots. "
            f"roots={discovered}, extensions={sorted(allowed_extensions)}"
        )

    print(f"[SWEEP] scanning dataset files: {len(dataset_files)}")
    inventory_rows: list[dict[str, Any]] = []
    series_payloads: list[dict[str, Any]] = []

    for idx, file_path in enumerate(dataset_files, start=1):
        inv_rows, payloads = extract_series_from_file(
            file_path,
            min_rows=args.min_rows,
            min_span_years=args.min_span_years,
            max_cols_per_file=args.max_cols_per_file,
            max_file_bytes=max_file_bytes,
        )
        inventory_rows.extend(inv_rows)
        series_payloads.extend(payloads)
        if idx % 100 == 0:
            print(f"[SWEEP] scanned {idx}/{len(dataset_files)} files")

    file_type_counts_raw = pd.Series(
        [path.suffix.lower().lstrip(".") for path in dataset_files],
        dtype="string",
    ).value_counts()
    file_type_counts = {str(k): int(v) for k, v in file_type_counts_raw.items()}

    inventory_df = pd.DataFrame(inventory_rows)
    read_engine_counts_raw = inventory_df.get("read_engine", pd.Series(dtype="string")).astype(str).value_counts()
    read_engine_counts = {str(k): int(v) for k, v in read_engine_counts_raw.items() if str(k)}
    inventory_csv = out_dir / "dataset_inventory.csv"
    inventory_df.to_csv(inventory_csv, index=False)

    ready = [s for s in series_payloads if s["rows"] >= args.min_rows and s["span_years"] >= args.min_span_years]
    ready = sorted(ready, key=lambda x: (x["span_years"], x["rows"]), reverse=True)
    dedup_ready: dict[str, dict[str, Any]] = {}
    for payload in ready:
        key = str(payload.get("fingerprint", ""))
        if not key:
            key = f"{payload['series_name']}::{payload['rows']}"
        if key not in dedup_ready:
            dedup_ready[key] = payload
            continue
        incumbent = dedup_ready[key]
        if (payload["span_years"], payload["rows"]) > (incumbent["span_years"], incumbent["rows"]):
            dedup_ready[key] = payload
    ready = list(dedup_ready.values())
    ready = sorted(ready, key=lambda x: (x["span_years"], x["rows"]), reverse=True)
    if args.max_series > 0:
        ready = ready[: args.max_series]

    print(f"[SWEEP] backtest-ready series: {len(ready)}")

    results_rows: list[dict[str, Any]] = []
    windows = [5, 10, 20, 63, 126]

    for idx, payload in enumerate(ready, start=1):
        metrics = walk_forward_backtest(
            payload["values"],
            train_bars=args.train_bars,
            test_bars=args.test_bars,
            cost_bps=args.cost_bps,
            windows=windows,
        )
        if metrics is None:
            continue

        row = {
            "series_name": payload["series_name"],
            "file_path": payload["file_path"],
            "column": payload["column"],
            "rows": payload["rows"],
            "span_years": round(float(payload["span_years"]), 3),
            **metrics,
        }
        results_rows.append(row)

        if idx % 100 == 0:
            print(f"[SWEEP] backtested {idx}/{len(ready)} series")

    results_df = pd.DataFrame(results_rows)
    if results_df.empty:
        raise SystemExit("No backtest results produced. Consider lowering thresholds.")

    results_df = results_df.sort_values("sharpe_delta", ascending=False).reset_index(drop=True)
    backtest_csv = out_dir / "walkforward_results.csv"
    top20_csv = out_dir / "walkforward_top20.csv"
    bottom20_csv = out_dir / "walkforward_bottom20.csv"
    results_df.to_csv(backtest_csv, index=False)
    results_df.head(20).to_csv(top20_csv, index=False)
    results_df.tail(20).to_csv(bottom20_csv, index=False)

    missing_catalog = load_missing_catalog_entries(
        catalog_path,
        include_stale_clean_paths=bool(args.include_stale_clean_paths),
    )
    missing_catalog_csv = out_dir / "missing_catalog_entries.csv"
    if missing_catalog.empty:
        pd.DataFrame(columns=["status", "reason", "source_path", "clean_path", "clean_path_exists"]).to_csv(
            missing_catalog_csv, index=False
        )
    else:
        missing_catalog.to_csv(missing_catalog_csv, index=False)

    long_horizon_count = int((inventory_df.get("span_years", pd.Series(dtype=float)) >= 20.0).sum())
    large_file_skip_count = int(
        inventory_df.get("reason", pd.Series(dtype="string")).astype(str).str.startswith("file_too_large").sum()
    )
    positive_sharpe_count = int((results_df["sharpe_delta"] > 0.0).sum())
    positive_cagr_count = int((results_df["cagr_delta"] > 0.0).sum())

    best_row = results_df.iloc[0].to_dict()

    opportunity_df = build_opportunity_table(results_df)
    opportunity_csv = out_dir / "opportunity_scale_table.csv"
    opportunity_df.to_csv(opportunity_csv, index=False)

    positive_ratio = float(positive_sharpe_count / max(1, len(results_df)))
    unity_payload = {
        "generated_utc": utc_now(),
        "scene": "core",
        "cue": "institutional_signal" if positive_ratio >= 0.55 else "focused_scan",
        "intensity": max(0.35, min(0.98, positive_ratio)),
        "detail": {
            "series_backtested": int(len(results_df)),
            "positive_sharpe_ratio": round(positive_ratio, 4),
            "best_series": str(best_row.get("series_name", "")),
            "best_sharpe_delta": float(best_row.get("sharpe_delta", 0.0)),
        },
    }

    nodered_payload = {
        "type": "investor_proof_sweep",
        "generated_utc": utc_now(),
        "summary": {
            "dataset_files_scanned": int(len(dataset_files)),
            "dataset_file_types": file_type_counts,
            "reader_engines": read_engine_counts,
            "inventory_rows": int(len(inventory_df)),
            "backtested_series": int(len(results_df)),
            "positive_sharpe_count": positive_sharpe_count,
            "positive_cagr_count": positive_cagr_count,
            "long_horizon_series_count": long_horizon_count,
            "large_file_skip_count": large_file_skip_count,
            "missing_catalog_entries": int(len(missing_catalog)),
        },
        "top_series": results_df.head(10)[
            [
                "series_name",
                "sharpe_delta",
                "cagr_delta",
                "drawdown_delta",
                "edge_bps_per_bar",
            ]
        ].to_dict(orient="records"),
    }

    unity_payload_json = out_dir / "unity_edge_payload.json"
    nodered_payload_json = out_dir / "nodered_payload.json"
    unity_payload_json.write_text(json.dumps(unity_payload, indent=2), encoding="utf-8")
    nodered_payload_json.write_text(json.dumps(nodered_payload, indent=2), encoding="utf-8")

    nodered_push = {"attempted": bool(args.push_nodered), "ingest": "not_attempted", "scene": "not_attempted"}
    if args.push_nodered:
        ingest_ok, ingest_msg = post_json(f"{args.nodered_base}/api/nodered/ingest", nodered_payload)
        scene_ok, scene_msg = post_json(f"{args.nodered_base}/api/scene/cue", unity_payload)
        nodered_push = {
            "attempted": True,
            "ingest": "ok" if ingest_ok else "failed",
            "ingest_detail": ingest_msg,
            "scene": "ok" if scene_ok else "failed",
            "scene_detail": scene_msg,
            "base_url": args.nodered_base,
        }

    summary = {
        "generated_utc": utc_now(),
        "scope": {
            "root": str(root),
            "stack_root": str(stack_root),
            "clean_dir": str(clean_dir),
            "catalog_path": str(catalog_path),
            "source_dirs": [str(p) for p in source_dirs],
        },
        "parameters": {
            "extensions": sorted(allowed_extensions),
            "min_rows": args.min_rows,
            "min_span_years": args.min_span_years,
            "max_cols_per_file": args.max_cols_per_file,
            "max_file_mb": args.max_file_mb,
            "max_files": args.max_files,
            "max_series": args.max_series,
            "train_bars": args.train_bars,
            "test_bars": args.test_bars,
            "cost_bps": args.cost_bps,
        },
        "coverage": {
            "dataset_files_scanned": int(len(dataset_files)),
            "dataset_file_types": file_type_counts,
            "reader_engines": read_engine_counts,
            "dataset_inventory_rows": int(len(inventory_df)),
            "backtest_ready_series": int(len(ready)),
            "backtested_series": int(len(results_df)),
            "long_horizon_series_count_20y": long_horizon_count,
            "large_file_skip_count": large_file_skip_count,
            "missing_catalog_entries": int(len(missing_catalog)),
        },
        "results": {
            "positive_sharpe_count": positive_sharpe_count,
            "positive_cagr_count": positive_cagr_count,
            "median_sharpe_delta": float(results_df["sharpe_delta"].median()),
            "median_cagr_delta": float(results_df["cagr_delta"].median()),
            "best_series": {
                "series_name": best_row.get("series_name"),
                "sharpe_delta": float(best_row.get("sharpe_delta", 0.0)),
                "cagr_delta": float(best_row.get("cagr_delta", 0.0)),
                "drawdown_delta": float(best_row.get("drawdown_delta", 0.0)),
            },
        },
        "node_red_unity": nodered_push,
        "artifacts": {
            "dataset_inventory_csv": str(inventory_csv),
            "walkforward_results_csv": str(backtest_csv),
            "walkforward_top20_csv": str(top20_csv),
            "walkforward_bottom20_csv": str(bottom20_csv),
            "missing_catalog_entries_csv": str(missing_catalog_csv),
            "opportunity_scale_table_csv": str(opportunity_csv),
            "nodered_payload_json": str(nodered_payload_json),
            "unity_edge_payload_json": str(unity_payload_json),
        },
    }

    summary_json = out_dir / "proof_summary.json"
    summary_json.write_text(json.dumps(summary, indent=2), encoding="utf-8")

    md_lines = [
        "# Investor Proof Sweep",
        "",
        f"Generated UTC: {summary['generated_utc']}",
        "",
        "## Coverage",
        "",
        f"- Dataset files scanned: {summary['coverage']['dataset_files_scanned']}",
        f"- Dataset file types: {summary['coverage']['dataset_file_types']}",
        f"- Reader engines used: {summary['coverage']['reader_engines']}",
        f"- Dataset inventory rows: {summary['coverage']['dataset_inventory_rows']}",
        f"- Backtest-ready series: {summary['coverage']['backtest_ready_series']}",
        f"- Backtested series: {summary['coverage']['backtested_series']}",
        f"- Long-horizon series (>=20y): {summary['coverage']['long_horizon_series_count_20y']}",
        f"- Large files skipped by guardrail: {summary['coverage']['large_file_skip_count']}",
        f"- Missing catalog entries: {summary['coverage']['missing_catalog_entries']}",
        "",
        "## Results",
        "",
        f"- Positive Sharpe delta count: {summary['results']['positive_sharpe_count']}",
        f"- Positive CAGR delta count: {summary['results']['positive_cagr_count']}",
        f"- Median Sharpe delta: {summary['results']['median_sharpe_delta']:.4f}",
        f"- Median CAGR delta: {summary['results']['median_cagr_delta']:.6f}",
        f"- Best series: {summary['results']['best_series']['series_name']}",
        f"- Best Sharpe delta: {summary['results']['best_series']['sharpe_delta']:.4f}",
        f"- Best CAGR delta: {summary['results']['best_series']['cagr_delta']:.6f}",
        f"- Best drawdown delta: {summary['results']['best_series']['drawdown_delta']:.6f}",
        "",
        "## Node-RED and Unity",
        "",
        f"- Push attempted: {summary['node_red_unity'].get('attempted', False)}",
        f"- Ingest status: {summary['node_red_unity'].get('ingest', 'not_attempted')}",
        f"- Scene cue status: {summary['node_red_unity'].get('scene', 'not_attempted')}",
        "",
        "## Artifact Paths",
        "",
    ]

    for key, value in summary["artifacts"].items():
        md_lines.append(f"- {key}: {value}")

    summary_md = out_dir / "proof_summary.md"
    summary_md.write_text("\n".join(md_lines) + "\n", encoding="utf-8")

    hash_manifest_rows = []
    artifact_files = [
        inventory_csv,
        backtest_csv,
        top20_csv,
        bottom20_csv,
        missing_catalog_csv,
        opportunity_csv,
        nodered_payload_json,
        unity_payload_json,
        summary_json,
        summary_md,
    ]
    for path in artifact_files:
        hash_manifest_rows.append(
            {
                "path": str(path),
                "bytes": int(path.stat().st_size),
                "sha256": sha256_file(path),
            }
        )

    hash_manifest = {
        "generated_utc": utc_now(),
        "artifact_count": len(hash_manifest_rows),
        "artifacts": hash_manifest_rows,
    }
    hash_manifest_json = out_dir / "artifact_hash_manifest.json"
    hash_manifest_json.write_text(json.dumps(hash_manifest, indent=2), encoding="utf-8")

    print("[SWEEP] complete")
    print(f"[SWEEP] output: {out_dir}")
    print(f"[SWEEP] backtested series: {len(results_df)}")
    print(f"[SWEEP] long-horizon series >=20y: {long_horizon_count}")
    print(f"[SWEEP] missing catalog entries: {len(missing_catalog)}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
