from __future__ import annotations

import csv
import hashlib
import json
import os
import re
import shutil
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(r"C:\LumaTrader\INSTITUTIONAL_STACK_V2")
OUT = ROOT / "out"
OPS_OUT = OUT / "ops"
SECTOR_OUT = OUT / "sector_energy"

DATA_DOMAIN = "sector_energy_evidence"

DATA_ROOT_CANDIDATES = [
    Path(r"C:\Data sets"),
    ROOT / "data",
    ROOT.parent / "data",
]

DATASET_FILES = {
    "eia930_ba_snapshot": "930-data-export (1).csv",
    "eia930_us48_hourly": "930-data-export (2).csv",
    "eia930_us48_single": "930-data-export.csv",
    "nuclear_daily_outage_a": "Daily_U.S._nuclear_capacity_outage.csv",
    "nuclear_daily_outage_b": "Daily_U.S._nuclear_capacity_outage (1).csv",
    "nuclear_plant_snapshot": "Nuclear_Plant_Outages_for_3_6_2026.csv",
    "net_generation_annual": "Net_generation_United_States_all_sectors_annual (1).csv",
    "net_generation_by_source": "Net_generation_for_all_sectors (1).csv",
    "mer_t09_04": "MER_T09_04.csv",
    "table1": "table1.csv",
    "table14": "table14.csv",
}

TRADER_PROTECTED_PATHS = [
    OUT / "execution" / "trader_alpha_lane",
    OUT / "execution" / "gen_all_ranked.csv",
    OUT / "execution" / "institutional_topn.csv",
    OUT / "execution" / "gen_champion.json",
    OUT / "execution" / "live_key_routing_summary.json",
    OUT / "execution" / "filtered_proof.json",
]

FROZEN_PROTECTED_PATHS = [
    OUT / "frozen_delta_ledger.jsonl",
    OUT / "infra_frozen_deltas.jsonl",
]


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def utc_stamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def normalize_path(p: Path) -> str:
    return str(p.resolve()).replace("\\", "/").lower()


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def select_data_root() -> Path:
    env_override = str(os.environ.get("LUMA_DATA_ROOT", "") or "").strip()
    if env_override:
        override_path = Path(env_override)
        if override_path.exists() and override_path.is_dir():
            return override_path

    ranked: list[tuple[int, float, Path]] = []
    dataset_names = list(DATASET_FILES.values())

    for candidate in DATA_ROOT_CANDIDATES:
        if not candidate.exists() or not candidate.is_dir():
            continue

        present_paths = [candidate / name for name in dataset_names if (candidate / name).exists()]
        coverage_count = len(present_paths)
        latest_mtime = max((p.stat().st_mtime for p in present_paths), default=0.0)
        ranked.append((coverage_count, latest_mtime, candidate))

    if ranked:
        ranked.sort(key=lambda item: (item[0], item[1]), reverse=True)
        return ranked[0][2]

    for candidate in DATA_ROOT_CANDIDATES:
        if candidate.exists() and candidate.is_dir():
            return candidate

    raise FileNotFoundError("No dataset root found. Checked C:/Data sets and stack data folders.")


def parse_timestamp_series(series: pd.Series) -> pd.Series:
    s = series.astype(str).str.strip()
    normalized = (
        s.str.replace("a.m.", "AM", regex=False)
        .str.replace("p.m.", "PM", regex=False)
        .str.replace(" EST", "", regex=False)
        .str.replace(" EDT", "", regex=False)
        .str.replace("UTC", "", regex=False)
    )
    return pd.to_datetime(normalized, errors="coerce")


def to_number(series: pd.Series) -> pd.Series:
    cleaned = (
        series.astype(str)
        .str.strip()
        .str.replace(",", "", regex=False)
        .str.replace("%", "", regex=False)
        .str.replace("$", "", regex=False)
    )
    cleaned = cleaned.replace({"": np.nan, "nan": np.nan, "None": np.nan})
    return pd.to_numeric(cleaned, errors="coerce")


def read_csv_any(path: Path, skiprows: int = 0) -> tuple[pd.DataFrame, str]:
    encodings = ("utf-8", "utf-8-sig", "cp1252", "latin-1", "utf-16")
    last_err = None
    for enc in encodings:
        try:
            df = pd.read_csv(
                path,
                skiprows=skiprows,
                dtype=str,
                encoding=enc,
                engine="python",
                on_bad_lines="skip",
            )
            return df, enc
        except Exception as exc:
            last_err = exc
    raise RuntimeError(f"Failed to read {path} as CSV: {last_err}")


def melt_metrics(
    df: pd.DataFrame,
    dataset: str,
    source_path: Path,
    period_col: str,
    region_col: str,
    metrics: dict[str, tuple[str, str]],
) -> pd.DataFrame:
    frames = []
    for raw_col, (metric_name, unit) in metrics.items():
        if raw_col not in df.columns:
            continue
        part = pd.DataFrame(
            {
                "data_domain": DATA_DOMAIN,
                "dataset": dataset,
                "series": metric_name,
                "region": df[region_col].astype(str),
                "metric": metric_name,
                "period_utc": df[period_col],
                "value": to_number(df[raw_col]),
                "unit": unit,
                "basis": "MEASURED",
                "source_path": str(source_path),
            }
        )
        frames.append(part)
    if not frames:
        return pd.DataFrame(columns=[
            "data_domain",
            "dataset",
            "series",
            "region",
            "metric",
            "period_utc",
            "value",
            "unit",
            "basis",
            "source_path",
        ])
    out = pd.concat(frames, ignore_index=True)
    out = out.dropna(subset=["period_utc", "value"]).reset_index(drop=True)
    return out


def build_us48_hourly(path: Path) -> tuple[pd.DataFrame, pd.DataFrame, dict]:
    df, enc = read_csv_any(path, skiprows=0)
    if "Timestamp (Hour Ending)" not in df.columns:
        raise RuntimeError(f"Missing Timestamp (Hour Ending) in {path}")

    df = df.copy()
    df["period_utc"] = parse_timestamp_series(df["Timestamp (Hour Ending)"])
    df["region"] = df.get("Region Code", "US48").fillna("US48")

    metrics = {
        "Demand (MWh)": ("demand_mwh", "mwh"),
        "Demand Forecast (MWh)": ("demand_forecast_mwh", "mwh"),
        "Net Generation (MWh)": ("net_generation_mwh", "mwh"),
        "Total Interchange (MWh)": ("total_interchange_mwh", "mwh"),
    }
    fact = melt_metrics(
        df=df,
        dataset="eia930_us48_hourly",
        source_path=path,
        period_col="period_utc",
        region_col="region",
        metrics=metrics,
    )

    raw = pd.DataFrame(
        {
            "period_utc": df["period_utc"],
            "region": df["region"],
            "demand_mwh": to_number(df.get("Demand (MWh)", pd.Series(dtype=float))),
            "demand_forecast_mwh": to_number(df.get("Demand Forecast (MWh)", pd.Series(dtype=float))),
            "net_generation_mwh": to_number(df.get("Net Generation (MWh)", pd.Series(dtype=float))),
            "total_interchange_mwh": to_number(df.get("Total Interchange (MWh)", pd.Series(dtype=float))),
        }
    ).dropna(subset=["period_utc"]).reset_index(drop=True)

    profile = {
        "dataset": "eia930_us48_hourly",
        "source_path": str(path),
        "encoding": enc,
        "rows": int(len(df.index)),
        "fact_rows": int(len(fact.index)),
    }
    return fact, raw, profile


def build_ba_snapshot(path: Path) -> tuple[pd.DataFrame, dict]:
    df, enc = read_csv_any(path, skiprows=0)
    if "Selected Hour Timestamp (Hour Ending)" not in df.columns:
        raise RuntimeError(f"Missing Selected Hour Timestamp (Hour Ending) in {path}")

    df = df.copy()
    df["period_utc"] = parse_timestamp_series(df["Selected Hour Timestamp (Hour Ending)"])
    df["region"] = df.get("Region Code", "unknown").fillna("unknown")

    metrics = {
        "Selected Hour Demand (MWh)": ("selected_hour_demand_mwh", "mwh"),
        "Prior Hour Demand (MWh)": ("prior_hour_demand_mwh", "mwh"),
        "Percent Change from Prior Hour": ("demand_change_pct", "pct"),
    }
    fact = melt_metrics(
        df=df,
        dataset="eia930_ba_snapshot",
        source_path=path,
        period_col="period_utc",
        region_col="region",
        metrics=metrics,
    )

    profile = {
        "dataset": "eia930_ba_snapshot",
        "source_path": str(path),
        "encoding": enc,
        "rows": int(len(df.index)),
        "fact_rows": int(len(fact.index)),
    }
    return fact, profile


def build_daily_nuclear_outage(path: Path) -> tuple[pd.DataFrame, pd.DataFrame, dict]:
    df, enc = read_csv_any(path, skiprows=4)
    if "Day" not in df.columns:
        raise RuntimeError(f"Missing Day column in {path}")

    df = df.copy()
    df["period_utc"] = pd.to_datetime(df["Day"], errors="coerce")
    df["region"] = "US"

    metrics = {
        "2026 gigawatts (GW)": ("nuclear_outage_2026_gw", "gw"),
        "2025 gigawatts (GW)": ("nuclear_outage_2025_gw", "gw"),
        "2021-2025 Range Low  gigawatts (GW)": ("nuclear_outage_range_low_gw", "gw"),
        "2021-2025 Range High  gigawatts (GW)": ("nuclear_outage_range_high_gw", "gw"),
    }
    fact = melt_metrics(
        df=df,
        dataset="nuclear_daily_outage",
        source_path=path,
        period_col="period_utc",
        region_col="region",
        metrics=metrics,
    )

    raw = pd.DataFrame(
        {
            "period_utc": df["period_utc"],
            "outage_2026_gw": to_number(df.get("2026 gigawatts (GW)", pd.Series(dtype=float))),
            "outage_2025_gw": to_number(df.get("2025 gigawatts (GW)", pd.Series(dtype=float))),
            "range_low_gw": to_number(df.get("2021-2025 Range Low  gigawatts (GW)", pd.Series(dtype=float))),
            "range_high_gw": to_number(df.get("2021-2025 Range High  gigawatts (GW)", pd.Series(dtype=float))),
        }
    ).dropna(subset=["period_utc"]).reset_index(drop=True)

    profile = {
        "dataset": "nuclear_daily_outage",
        "source_path": str(path),
        "encoding": enc,
        "rows": int(len(df.index)),
        "fact_rows": int(len(fact.index)),
    }
    return fact, raw, profile


def extract_date_from_filename(filename: str) -> pd.Timestamp | None:
    m = re.search(r"(\d{1,2})_(\d{1,2})_(\d{4})", filename)
    if not m:
        return None
    month, day, year = m.groups()
    try:
        return pd.Timestamp(year=int(year), month=int(month), day=int(day))
    except Exception:
        return None


def build_plant_outage(path: Path) -> tuple[pd.DataFrame, pd.DataFrame, dict]:
    df, enc = read_csv_any(path, skiprows=4)
    snapshot_date = extract_date_from_filename(path.name)
    if snapshot_date is None:
        snapshot_date = pd.Timestamp.utcnow().normalize()

    df = df.copy()
    df["period_utc"] = snapshot_date
    df["region"] = "US"
    df["plant"] = df.get("Plant Name", "unknown").fillna("unknown")

    metrics = {
        "Plant Output": ("plant_output_pct", "pct"),
        "Outage Amount (MW)": ("plant_outage_mw", "mw"),
        "Capacity (MW)": ("plant_capacity_mw", "mw"),
        "Operating Units": ("plant_operating_units", "count"),
    }
    fact = []
    for raw_col, (metric_name, unit) in metrics.items():
        if raw_col not in df.columns:
            continue
        part = pd.DataFrame(
            {
                "data_domain": DATA_DOMAIN,
                "dataset": "nuclear_plant_snapshot",
                "series": df["plant"].astype(str),
                "region": df["region"],
                "metric": metric_name,
                "period_utc": df["period_utc"],
                "value": to_number(df[raw_col]),
                "unit": unit,
                "basis": "MEASURED",
                "source_path": str(path),
            }
        )
        fact.append(part)
    fact_df = pd.concat(fact, ignore_index=True) if fact else pd.DataFrame()
    if not fact_df.empty:
        fact_df = fact_df.dropna(subset=["value"]).reset_index(drop=True)

    raw = pd.DataFrame(
        {
            "period_utc": df["period_utc"],
            "plant": df["plant"],
            "plant_output_pct": to_number(df.get("Plant Output", pd.Series(dtype=float))),
            "plant_outage_mw": to_number(df.get("Outage Amount (MW)", pd.Series(dtype=float))),
            "plant_capacity_mw": to_number(df.get("Capacity (MW)", pd.Series(dtype=float))),
        }
    ).dropna(subset=["plant_outage_mw", "plant_capacity_mw"], how="all")

    profile = {
        "dataset": "nuclear_plant_snapshot",
        "source_path": str(path),
        "encoding": enc,
        "rows": int(len(df.index)),
        "fact_rows": int(len(fact_df.index)) if not fact_df.empty else 0,
    }
    return fact_df, raw, profile


def build_generation_annual(path: Path) -> tuple[pd.DataFrame, pd.DataFrame, dict]:
    df, enc = read_csv_any(path, skiprows=4)
    if "Year" not in df.columns:
        raise RuntimeError(f"Missing Year column in {path}")

    value_col = next((c for c in df.columns if "all fuels" in str(c).lower()), None)
    if value_col is None:
        raise RuntimeError(f"Missing all fuels value column in {path}")

    parsed_year = pd.to_datetime(df["Year"].astype(str), format="%Y", errors="coerce")
    values = to_number(df[value_col])

    fact = pd.DataFrame(
        {
            "data_domain": DATA_DOMAIN,
            "dataset": "net_generation_annual",
            "series": "all_fuels_utility_scale",
            "region": "US",
            "metric": "net_generation_mwh",
            "period_utc": parsed_year,
            "value": values,
            "unit": "thousand_mwh",
            "basis": "MEASURED",
            "source_path": str(path),
        }
    ).dropna(subset=["period_utc", "value"])

    raw = pd.DataFrame({"period_utc": parsed_year, "value": values}).dropna(subset=["period_utc", "value"])

    profile = {
        "dataset": "net_generation_annual",
        "source_path": str(path),
        "encoding": enc,
        "rows": int(len(df.index)),
        "fact_rows": int(len(fact.index)),
    }
    return fact, raw, profile


def build_generation_by_source(path: Path) -> tuple[pd.DataFrame, dict]:
    df, enc = read_csv_any(path, skiprows=4)
    year_cols = [c for c in df.columns if str(c).isdigit()]
    if not year_cols:
        raise RuntimeError(f"No year columns found in {path}")

    label_col = "description" if "description" in df.columns else df.columns[0]
    unit_col = "units" if "units" in df.columns else None

    long_df = df.melt(id_vars=[label_col] + ([unit_col] if unit_col else []), value_vars=year_cols, var_name="year", value_name="value")
    long_df["period_utc"] = pd.to_datetime(long_df["year"].astype(str), format="%Y", errors="coerce")

    fact = pd.DataFrame(
        {
            "data_domain": DATA_DOMAIN,
            "dataset": "net_generation_by_source",
            "series": long_df[label_col].astype(str).str.strip(),
            "region": "US",
            "metric": "net_generation_mwh",
            "period_utc": long_df["period_utc"],
            "value": to_number(long_df["value"]),
            "unit": long_df[unit_col].astype(str) if unit_col else "reported_units_unknown",
            "basis": "MEASURED",
            "source_path": str(path),
        }
    ).dropna(subset=["period_utc", "value"])

    profile = {
        "dataset": "net_generation_by_source",
        "source_path": str(path),
        "encoding": enc,
        "rows": int(len(df.index)),
        "fact_rows": int(len(fact.index)),
    }
    return fact, profile


def build_mer(path: Path) -> tuple[pd.DataFrame, dict]:
    df, enc = read_csv_any(path, skiprows=0)
    if "YYYYMM" not in df.columns or "Value" not in df.columns:
        raise RuntimeError(f"Missing YYYYMM/Value columns in {path}")

    period = pd.to_datetime(df["YYYYMM"].astype(str), format="%Y%m", errors="coerce")
    series = df.get("MSN", "unknown").astype(str)
    if "Description" in df.columns:
        series = series + " | " + df["Description"].astype(str)

    fact = pd.DataFrame(
        {
            "data_domain": DATA_DOMAIN,
            "dataset": "mer_t09_04",
            "series": series,
            "region": "US",
            "metric": "mer_value",
            "period_utc": period,
            "value": to_number(df["Value"]),
            "unit": df.get("Unit", "reported_units_unknown").astype(str) if "Unit" in df.columns else "reported_units_unknown",
            "basis": "MEASURED",
            "source_path": str(path),
        }
    ).dropna(subset=["period_utc", "value"])

    profile = {
        "dataset": "mer_t09_04",
        "source_path": str(path),
        "encoding": enc,
        "rows": int(len(df.index)),
        "fact_rows": int(len(fact.index)),
    }
    return fact, profile


def parse_short_date(label: str) -> pd.Timestamp | None:
    try:
        return pd.to_datetime(label, format="%m/%d/%y", errors="coerce")
    except Exception:
        return None


def build_table1(path: Path) -> tuple[pd.DataFrame, dict]:
    df, enc = read_csv_any(path, skiprows=0)
    if "STUB_1" not in df.columns:
        raise RuntimeError(f"Missing STUB_1 in {path}")

    date_cols = [c for c in df.columns if parse_short_date(str(c)) is not None]
    if not date_cols:
        return pd.DataFrame(), {
            "dataset": "table1",
            "source_path": str(path),
            "encoding": enc,
            "rows": int(len(df.index)),
            "fact_rows": 0,
        }

    long_df = df.melt(id_vars=["STUB_1"], value_vars=date_cols, var_name="period_label", value_name="value")
    long_df["period_utc"] = pd.to_datetime(long_df["period_label"], format="%m/%d/%y", errors="coerce")

    fact = pd.DataFrame(
        {
            "data_domain": DATA_DOMAIN,
            "dataset": "table1",
            "series": long_df["STUB_1"].astype(str),
            "region": "US",
            "metric": "inventory_snapshot_value",
            "period_utc": long_df["period_utc"],
            "value": to_number(long_df["value"]),
            "unit": "reported_units_unknown",
            "basis": "MEASURED",
            "source_path": str(path),
        }
    ).dropna(subset=["period_utc", "value"])

    profile = {
        "dataset": "table1",
        "source_path": str(path),
        "encoding": enc,
        "rows": int(len(df.index)),
        "fact_rows": int(len(fact.index)),
    }
    return fact, profile


def build_table14(path: Path) -> tuple[pd.DataFrame, dict]:
    df, enc = read_csv_any(path, skiprows=0)
    if "STUB_1" not in df.columns or "STUB_2" not in df.columns:
        raise RuntimeError(f"Missing STUB_1/STUB_2 in {path}")

    month_order = {
        "Jan": 1,
        "Feb": 2,
        "Mar": 3,
        "Apr": 4,
        "May": 5,
        "Jun": 6,
        "Jul": 7,
        "Aug": 8,
        "Sep": 9,
        "Oct": 10,
        "Nov": 11,
        "Dec": 12,
    }

    month_cols = [c for c in df.columns if c in month_order]
    if not month_cols:
        return pd.DataFrame(), {
            "dataset": "table14",
            "source_path": str(path),
            "encoding": enc,
            "rows": int(len(df.index)),
            "fact_rows": 0,
        }

    long_df = df.melt(id_vars=["STUB_1", "STUB_2"], value_vars=month_cols, var_name="month", value_name="value")
    year = pd.to_numeric(long_df["STUB_1"], errors="coerce")
    month_num = long_df["month"].map(month_order)
    long_df["period_utc"] = pd.to_datetime(
        {
            "year": year,
            "month": month_num,
            "day": 1,
        },
        errors="coerce",
    )

    fact = pd.DataFrame(
        {
            "data_domain": DATA_DOMAIN,
            "dataset": "table14",
            "series": long_df["STUB_2"].astype(str),
            "region": "US",
            "metric": "monthly_price_value",
            "period_utc": long_df["period_utc"],
            "value": to_number(long_df["value"]),
            "unit": "reported_units_unknown",
            "basis": "MEASURED",
            "source_path": str(path),
        }
    ).dropna(subset=["period_utc", "value"])

    profile = {
        "dataset": "table14",
        "source_path": str(path),
        "encoding": enc,
        "rows": int(len(df.index)),
        "fact_rows": int(len(fact.index)),
    }
    return fact, profile


def build_constraint_ledger(
    us48_hourly: pd.DataFrame,
    daily_outage: pd.DataFrame,
    plant_outage: pd.DataFrame,
    generation_annual: pd.DataFrame,
) -> pd.DataFrame:
    rows: list[dict] = []

    if not us48_hourly.empty:
        h = us48_hourly.sort_values("period_utc").copy()
        demand = h["demand_mwh"]
        forecast = h["demand_forecast_mwh"]
        interchange = h["total_interchange_mwh"]

        abs_error = (demand - forecast).abs()
        error_pct = (abs_error / demand.replace(0, np.nan)) * 100.0
        demand_vol = demand.pct_change().std() * 100.0

        rows.extend(
            [
                {
                    "data_domain": DATA_DOMAIN,
                    "metric_id": "us48_forecast_abs_error_mwh_total",
                    "value": float(abs_error.sum(skipna=True)),
                    "unit": "mwh",
                    "basis": "MEASURED",
                    "window_start_utc": str(h["period_utc"].min()),
                    "window_end_utc": str(h["period_utc"].max()),
                    "source": "eia930_us48_hourly",
                },
                {
                    "data_domain": DATA_DOMAIN,
                    "metric_id": "us48_forecast_error_pct_mean",
                    "value": float(error_pct.mean(skipna=True)),
                    "unit": "pct",
                    "basis": "MEASURED",
                    "window_start_utc": str(h["period_utc"].min()),
                    "window_end_utc": str(h["period_utc"].max()),
                    "source": "eia930_us48_hourly",
                },
                {
                    "data_domain": DATA_DOMAIN,
                    "metric_id": "us48_interchange_abs_mwh_total",
                    "value": float(interchange.abs().sum(skipna=True)),
                    "unit": "mwh",
                    "basis": "MEASURED",
                    "window_start_utc": str(h["period_utc"].min()),
                    "window_end_utc": str(h["period_utc"].max()),
                    "source": "eia930_us48_hourly",
                },
                {
                    "data_domain": DATA_DOMAIN,
                    "metric_id": "us48_demand_volatility_pct_std",
                    "value": float(demand_vol),
                    "unit": "pct",
                    "basis": "MEASURED",
                    "window_start_utc": str(h["period_utc"].min()),
                    "window_end_utc": str(h["period_utc"].max()),
                    "source": "eia930_us48_hourly",
                },
            ]
        )

    if not daily_outage.empty:
        d = daily_outage.copy().sort_values("period_utc")
        outage_series = d["outage_2026_gw"]
        if outage_series.notna().sum() < max(5, int(len(d.index) * 0.2)):
            outage_series = d["outage_2025_gw"]

        rows.extend(
            [
                {
                    "data_domain": DATA_DOMAIN,
                    "metric_id": "nuclear_outage_gw_mean",
                    "value": float(outage_series.mean(skipna=True)),
                    "unit": "gw",
                    "basis": "MEASURED",
                    "window_start_utc": str(d["period_utc"].min()),
                    "window_end_utc": str(d["period_utc"].max()),
                    "source": "nuclear_daily_outage",
                },
                {
                    "data_domain": DATA_DOMAIN,
                    "metric_id": "nuclear_outage_gw_peak",
                    "value": float(outage_series.max(skipna=True)),
                    "unit": "gw",
                    "basis": "MEASURED",
                    "window_start_utc": str(d["period_utc"].min()),
                    "window_end_utc": str(d["period_utc"].max()),
                    "source": "nuclear_daily_outage",
                },
            ]
        )

    if not plant_outage.empty:
        p = plant_outage.copy()
        outage_mw = p["plant_outage_mw"].sum(skipna=True)
        capacity_mw = p["plant_capacity_mw"].sum(skipna=True)
        outage_ratio_pct = (outage_mw / capacity_mw * 100.0) if capacity_mw > 0 else np.nan
        rows.extend(
            [
                {
                    "data_domain": DATA_DOMAIN,
                    "metric_id": "nuclear_plant_outage_mw_total_snapshot",
                    "value": float(outage_mw),
                    "unit": "mw",
                    "basis": "MEASURED",
                    "window_start_utc": str(p["period_utc"].min()),
                    "window_end_utc": str(p["period_utc"].max()),
                    "source": "nuclear_plant_snapshot",
                },
                {
                    "data_domain": DATA_DOMAIN,
                    "metric_id": "nuclear_plant_outage_ratio_pct_snapshot",
                    "value": float(outage_ratio_pct) if np.isfinite(outage_ratio_pct) else np.nan,
                    "unit": "pct",
                    "basis": "MEASURED",
                    "window_start_utc": str(p["period_utc"].min()),
                    "window_end_utc": str(p["period_utc"].max()),
                    "source": "nuclear_plant_snapshot",
                },
            ]
        )

    if not generation_annual.empty:
        g = generation_annual.copy().sort_values("period_utc")
        years = g.set_index(g["period_utc"].dt.year)["value"].to_dict()
        if 2025 in years and 2024 in years and years[2024] not in (0, np.nan):
            yoy_pct = ((years[2025] - years[2024]) / years[2024]) * 100.0
            rows.append(
                {
                    "data_domain": DATA_DOMAIN,
                    "metric_id": "annual_generation_yoy_pct_2025_vs_2024",
                    "value": float(yoy_pct),
                    "unit": "pct",
                    "basis": "MEASURED",
                    "window_start_utc": str(g["period_utc"].min()),
                    "window_end_utc": str(g["period_utc"].max()),
                    "source": "net_generation_annual",
                }
            )

    return pd.DataFrame(rows)


def build_us48_coherence(us48_hourly: pd.DataFrame) -> pd.DataFrame:
    if us48_hourly.empty:
        return pd.DataFrame(columns=[
            "period_utc",
            "region",
            "demand_mwh",
            "demand_forecast_mwh",
            "abs_error_mwh",
            "error_ratio",
            "interchange_ratio",
            "demand_return",
            "demand_volatility_24h",
            "coherence_score",
            "regime",
        ])

    h = us48_hourly.sort_values("period_utc").copy()
    demand = h["demand_mwh"]
    forecast = h["demand_forecast_mwh"]
    interchange = h["total_interchange_mwh"]

    abs_error = (demand - forecast).abs()
    error_ratio = abs_error / demand.replace(0, np.nan)
    interchange_ratio = interchange.abs() / demand.replace(0, np.nan)
    demand_return = demand.pct_change()
    roll_vol = demand_return.rolling(24, min_periods=6).std()

    coherence = 100.0 - (error_ratio * 120.0 + interchange_ratio * 60.0 + roll_vol * 85.0)
    coherence = coherence.clip(lower=0.0, upper=100.0)

    regime = np.where(coherence >= 70.0, "FLOW", np.where(coherence >= 45.0, "STRAIN", "FRACTURE"))

    out = pd.DataFrame(
        {
            "period_utc": h["period_utc"],
            "region": h["region"],
            "demand_mwh": demand,
            "demand_forecast_mwh": forecast,
            "abs_error_mwh": abs_error,
            "error_ratio": error_ratio,
            "interchange_ratio": interchange_ratio,
            "demand_return": demand_return,
            "demand_volatility_24h": roll_vol,
            "coherence_score": coherence,
            "regime": regime,
        }
    )
    return out.dropna(subset=["period_utc"]).reset_index(drop=True)


def assert_lane_boundary(write_paths: list[Path]) -> None:
    normalized_writes = [normalize_path(p) for p in write_paths]
    trader_paths = [normalize_path(p) for p in TRADER_PROTECTED_PATHS]
    frozen_paths = [normalize_path(p) for p in FROZEN_PROTECTED_PATHS]

    for w in normalized_writes:
        for t in trader_paths:
            if w == t or w.startswith(t + "/"):
                raise RuntimeError(f"lane boundary violation: sector writer attempted trader path {w}")
        for f in frozen_paths:
            if w == f:
                raise RuntimeError(f"lane boundary violation: sector writer attempted frozen-delta canonical path {w}")


def write_csv(path: Path, df: pd.DataFrame) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(path, index=False)


def write_json(path: Path, obj: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, indent=2), encoding="utf-8")


def main() -> None:
    generated_utc = utc_now()
    run_tag = utc_stamp()
    data_root = select_data_root()

    run_dir = OPS_OUT / f"measured_sector_fact_table_{run_tag}"
    run_dir.mkdir(parents=True, exist_ok=True)
    SECTOR_OUT.mkdir(parents=True, exist_ok=True)

    manifests = []
    fact_frames = []
    profiles = []

    def add_manifest(dataset_key: str, path: Path) -> None:
        if not path.exists():
            manifests.append(
                {
                    "dataset": dataset_key,
                    "path": str(path),
                    "exists": False,
                    "size_bytes": 0,
                    "sha256": None,
                }
            )
            return
        manifests.append(
            {
                "dataset": dataset_key,
                "path": str(path),
                "exists": True,
                "size_bytes": int(path.stat().st_size),
                "sha256": sha256_file(path),
            }
        )

    paths = {k: data_root / v for k, v in DATASET_FILES.items()}
    for key, p in paths.items():
        add_manifest(key, p)

    us48_hourly_raw = pd.DataFrame()
    daily_outage_raw = pd.DataFrame()
    plant_outage_raw = pd.DataFrame()
    generation_annual_raw = pd.DataFrame()

    if paths["eia930_us48_hourly"].exists():
        fact, raw, profile = build_us48_hourly(paths["eia930_us48_hourly"])
        fact_frames.append(fact)
        us48_hourly_raw = raw
        profiles.append(profile)

    if paths["eia930_ba_snapshot"].exists():
        fact, profile = build_ba_snapshot(paths["eia930_ba_snapshot"])
        fact_frames.append(fact)
        profiles.append(profile)

    for daily_key in ("nuclear_daily_outage_a", "nuclear_daily_outage_b"):
        if paths[daily_key].exists():
            fact, raw, profile = build_daily_nuclear_outage(paths[daily_key])
            fact_frames.append(fact)
            daily_outage_raw = raw if daily_outage_raw.empty else daily_outage_raw
            profiles.append(profile)
            break

    if paths["nuclear_plant_snapshot"].exists():
        fact, raw, profile = build_plant_outage(paths["nuclear_plant_snapshot"])
        fact_frames.append(fact)
        plant_outage_raw = raw
        profiles.append(profile)

    if paths["net_generation_annual"].exists():
        fact, raw, profile = build_generation_annual(paths["net_generation_annual"])
        fact_frames.append(fact)
        generation_annual_raw = raw
        profiles.append(profile)

    if paths["net_generation_by_source"].exists():
        fact, profile = build_generation_by_source(paths["net_generation_by_source"])
        fact_frames.append(fact)
        profiles.append(profile)

    if paths["mer_t09_04"].exists():
        fact, profile = build_mer(paths["mer_t09_04"])
        fact_frames.append(fact)
        profiles.append(profile)

    if paths["table1"].exists():
        fact, profile = build_table1(paths["table1"])
        fact_frames.append(fact)
        profiles.append(profile)

    if paths["table14"].exists():
        fact, profile = build_table14(paths["table14"])
        fact_frames.append(fact)
        profiles.append(profile)

    if not fact_frames:
        raise RuntimeError("No fact rows were generated. Check dataset root and file availability.")

    fact_table = pd.concat([f for f in fact_frames if not f.empty], ignore_index=True)
    fact_table["period_utc"] = pd.to_datetime(fact_table["period_utc"], errors="coerce")
    fact_table = fact_table.dropna(subset=["period_utc", "value"]).sort_values(["period_utc", "dataset", "series"]).reset_index(drop=True)

    constraint_ledger = build_constraint_ledger(
        us48_hourly=us48_hourly_raw,
        daily_outage=daily_outage_raw,
        plant_outage=plant_outage_raw,
        generation_annual=generation_annual_raw,
    )

    coherence_df = build_us48_coherence(us48_hourly_raw)

    latest_fact_csv = SECTOR_OUT / "measured_sector_fact_table.csv"
    latest_ledger_csv = SECTOR_OUT / "measured_sector_constraint_ledger.csv"
    latest_coherence_csv = SECTOR_OUT / "us48_coherence_timeseries.csv"
    latest_summary_json = SECTOR_OUT / "measured_sector_summary.json"
    latest_lane_manifest = SECTOR_OUT / "sector_lane_manifest.json"

    run_fact_csv = run_dir / "measured_sector_fact_table.csv"
    run_ledger_csv = run_dir / "measured_sector_constraint_ledger.csv"
    run_coherence_csv = run_dir / "us48_coherence_timeseries.csv"
    run_summary_json = run_dir / "build_summary.json"
    run_manifest_csv = run_dir / "input_file_manifest.csv"
    run_profiles_json = run_dir / "dataset_profiles.json"
    run_summary_md = run_dir / "build_summary.md"

    planned_writes = [
        latest_fact_csv,
        latest_ledger_csv,
        latest_coherence_csv,
        latest_summary_json,
        latest_lane_manifest,
        run_fact_csv,
        run_ledger_csv,
        run_coherence_csv,
        run_summary_json,
        run_manifest_csv,
        run_profiles_json,
        run_summary_md,
    ]
    assert_lane_boundary(planned_writes)

    write_csv(run_fact_csv, fact_table)
    write_csv(run_ledger_csv, constraint_ledger)
    write_csv(run_coherence_csv, coherence_df)

    write_csv(latest_fact_csv, fact_table)
    write_csv(latest_ledger_csv, constraint_ledger)
    write_csv(latest_coherence_csv, coherence_df)

    with run_manifest_csv.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["dataset", "path", "exists", "size_bytes", "sha256"])
        writer.writeheader()
        for row in manifests:
            writer.writerow(row)

    write_json(run_profiles_json, {"generated_utc": generated_utc, "rows": profiles})

    summary = {
        "generated_utc": generated_utc,
        "run_tag": run_tag,
        "data_domain": DATA_DOMAIN,
        "data_root": str(data_root),
        "fact_rows": int(len(fact_table.index)),
        "constraint_rows": int(len(constraint_ledger.index)),
        "coherence_rows": int(len(coherence_df.index)),
        "fact_period_start_utc": str(fact_table["period_utc"].min()) if not fact_table.empty else None,
        "fact_period_end_utc": str(fact_table["period_utc"].max()) if not fact_table.empty else None,
        "datasets_seen": sorted(set(fact_table["dataset"].astype(str).tolist())),
        "dataset_profile_count": len(profiles),
        "run_dir": str(run_dir),
        "latest_outputs": {
            "fact_csv": str(latest_fact_csv),
            "constraint_csv": str(latest_ledger_csv),
            "coherence_csv": str(latest_coherence_csv),
            "summary_json": str(latest_summary_json),
            "lane_manifest": str(latest_lane_manifest),
        },
    }

    lane_manifest = {
        "generated_utc": generated_utc,
        "lane": DATA_DOMAIN,
        "run_tag": run_tag,
        "writes": [str(p) for p in planned_writes],
        "guarded_trader_paths": [str(p) for p in TRADER_PROTECTED_PATHS],
        "guarded_frozen_paths": [str(p) for p in FROZEN_PROTECTED_PATHS],
        "notes": [
            "Measured sector outputs are isolated under out/sector_energy and out/ops run bundle.",
            "No trader execution artifacts are written by this builder.",
            "No frozen-delta canonical ledgers are modified by this builder.",
        ],
    }

    write_json(run_summary_json, summary)
    write_json(latest_summary_json, summary)
    write_json(latest_lane_manifest, lane_manifest)

    md_lines = [
        "# Measured Sector Fact Table Build",
        "",
        f"Generated UTC: {generated_utc}",
        f"Run Tag: {run_tag}",
        f"Data Root: {data_root}",
        "",
        "## Output Counts",
        f"- Fact rows: {summary['fact_rows']}",
        f"- Constraint rows: {summary['constraint_rows']}",
        f"- Coherence rows: {summary['coherence_rows']}",
        "",
        "## Coverage",
        f"- Fact period start: {summary['fact_period_start_utc']}",
        f"- Fact period end: {summary['fact_period_end_utc']}",
        f"- Datasets included: {len(summary['datasets_seen'])}",
        "",
        "## Evidence Paths",
        f"- Run summary: {run_summary_json}",
        f"- Input manifest: {run_manifest_csv}",
        f"- Latest fact table: {latest_fact_csv}",
        f"- Latest lane manifest: {latest_lane_manifest}",
    ]
    run_summary_md.write_text("\n".join(md_lines) + "\n", encoding="utf-8")

    print(str(run_summary_json))
    print(str(latest_fact_csv))
    print(str(latest_lane_manifest))


if __name__ == "__main__":
    main()
