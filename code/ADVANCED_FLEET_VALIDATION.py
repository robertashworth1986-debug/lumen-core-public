from __future__ import annotations

import csv
import json
import os
import re
import zipfile
from datetime import datetime, timezone
from pathlib import Path

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


ROOT = Path(
    os.environ.get("LUMA_STACK_ROOT", str(Path(__file__).resolve().parent.parent))
).expanduser().resolve()
OUT = ROOT / "out"
DASH = Path(
    os.environ.get("LUMA_DASHBOARD_DIR", str(ROOT / "dashboard"))
).expanduser().resolve()

SECTOR_MATRIX = OUT / "sector_economic_impact_matrix.json"
OPP_GAIN = OUT / "opportunity_gain_matrix_updated.json"
ROLLING_PERF = OUT / "rolling_performance.json"
REPORT_JSON = OUT / "advanced_fleet_validation.json"
REPORT_HTML = DASH / "advanced_fleet_validation.html"
DATA_DIR = Path(
    os.environ.get("LUMA_LOCAL_DATA_DIR", str(ROOT.parent / "data"))
).expanduser().resolve()
DEFAULT_EXTRA_DATA_DIRS = [Path.home() / "iCloudDrive" / "EIA reports_", Path.home() / "Downloads"]
_TEMP_DATA_DIR = os.environ.get("TEMP") or os.environ.get("TMP")
if _TEMP_DATA_DIR:
    DEFAULT_EXTRA_DATA_DIRS.append(Path(_TEMP_DATA_DIR))

MAX_TEXT_SAMPLE_BYTES = 2_000_000
LOCAL_SOURCE_SPECS = [
    {"sector": "rates", "file": "fred_DGS10.csv", "label": "FRED DGS10"},
    {"sector": "labor", "file": "fred_UNRATE.csv", "label": "FRED UNRATE"},
    {"sector": "macro", "file": "fred_CPIAUCSL.csv", "label": "FRED CPIAUCSL"},
    {"sector": "market_data", "file": "kraken_live.csv", "label": "Kraken live ticker"},
    {"sector": "market_data", "file": "kraken_live_5000.csv", "label": "Kraken OHLC 5000"},
    {"sector": "energy", "file": "Daily_U.S._nuclear_capacity_outage.csv", "label": "EIA nuclear daily outage"},
    {"sector": "energy", "file": "Daily_U.S._nuclear_capacity_outage (1).csv", "label": "EIA nuclear daily outage copy"},
    {"sector": "energy", "file": "Nuclear_Plant_Outages_for_3_6_2026.csv", "label": "EIA plant outage snapshot"},
    {"sector": "energy", "file": "Net_generation_for_all_sectors (1).csv", "label": "EIA net generation all sectors"},
    {"sector": "energy", "file": "Net_generation_United_States_all_sectors_annual (1).csv", "label": "EIA US net generation annual copy"},
    {"sector": "energy", "file": "Net_generation_United_States_all_sectors_annual.csv", "label": "EIA US net generation annual"},
    {"sector": "energy", "file": "Net_generation_United_States_all_sectors_monthly.csv", "label": "EIA US net generation monthly"},
    {"sector": "energy", "file": "Net_generation_United_States_all_sectors_monthly (1).csv", "label": "EIA US net generation monthly copy"},
    {"sector": "energy", "file": "Net_generation_for_all_sectors.csv", "label": "EIA net generation all sectors iCloud"},
    {"sector": "energy", "file": "MER_T09_04.csv", "label": "EIA MER table 9.4"},
    {"sector": "energy", "file": "table1.csv", "label": "EIA petroleum table 1"},
    {"sector": "energy", "file": "table14.csv", "label": "EIA petroleum table 14"},
    {"sector": "power_grid", "file": "930-data-export.csv", "label": "EIA 930 demand sample"},
    {"sector": "power_grid", "file": "930-data-export (1).csv", "label": "EIA 930 demand sample 1"},
    {"sector": "power_grid", "file": "930-data-export (2).csv", "label": "EIA 930 demand sample 2"},
    {"sector": "power_grid", "file": "930-data-export.json", "label": "EIA 930 demand JSON"},
    {"sector": "power_grid", "file": "930-data-export (1).json", "label": "EIA 930 demand JSON 1"},
    {"sector": "power_grid", "file": "930-data-export (2).json", "label": "EIA 930 demand JSON 2"},
    {"sector": "energy", "file": "COAL.txt", "label": "EIA coal JSONL"},
    {"sector": "power_grid", "file": "EBA.txt", "label": "EIA bulk electric JSONL"},
    {"sector": "power_grid", "file": "text.txt", "label": "EIA bulk electric extracted text"},
    {"sector": "power_grid", "file": "EBA.zip", "label": "EIA bulk electric archive"},
    {"sector": "energy", "file": "ELEC.zip", "label": "EIA electricity archive"},
    {"sector": "energy", "file": "COAL.zip", "label": "EIA coal archive"},
    {"sector": "energy", "file": "NUC_STATUS.zip", "label": "EIA nuclear status archive"},
    {"sector": "energy", "file": "NG.zip", "label": "EIA natural gas archive"},
    {"sector": "energy", "file": "PET.zip", "label": "EIA petroleum archive"},
    {"sector": "energy", "file": "EMISS.zip", "label": "EIA emissions archive"},
    {"sector": "energy", "file": "TOTAL.zip", "label": "EIA total energy archive"},
    {"sector": "energy", "file": "SEDS.zip", "label": "EIA state energy archive"},
    {"sector": "energy", "file": "INTL.zip", "label": "EIA international archive"},
    {"sector": "energy", "file": "eia8602024.zip", "label": "EIA 860 generator archive"},
    {"sector": "energy", "file": "aeotab_18.xlsx", "label": "EIA AEO table 18"},
    {"sector": "energy", "file": "aeotab_19.xlsx", "label": "EIA AEO table 19"},
    {"sector": "energy", "file": "Table1_1.xlsx", "label": "EIA table 1.1 workbook"},
]
CSV_HEADER_HINTS = {
    "date",
    "time",
    "timestamp",
    "month",
    "year",
    "day",
    "plant",
    "region code",
    "msn",
    "stub_1",
    "description",
}


def now_utc() -> str:
    return datetime.now(timezone.utc).isoformat()


def read_json(path: Path, default):
    try:
        if path.exists():
            return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        pass
    return default


def configured_data_roots() -> list[Path]:
    roots = [DATA_DIR]
    env_roots = os.environ.get("LUMA_EXTRA_DATA_DIRS", "")
    for raw in env_roots.split(os.pathsep):
        if raw.strip():
            roots.append(Path(raw.strip()).expanduser())
    roots.extend(DEFAULT_EXTRA_DATA_DIRS)

    unique: list[Path] = []
    seen = set()
    for root in roots:
        try:
            resolved = root.resolve()
        except Exception:
            resolved = root
        key = str(resolved).lower()
        if key not in seen:
            seen.add(key)
            unique.append(resolved)
    return unique


def _normalize_data_roots(data_roots=None) -> list[Path]:
    if data_roots is None:
        return configured_data_roots()
    if isinstance(data_roots, (str, Path)):
        return [Path(data_roots).expanduser().resolve()]
    return [Path(root).expanduser().resolve() for root in data_roots]


def _looks_like_csv_header(row: list[str]) -> bool:
    joined = " ".join(cell.strip().lower() for cell in row if cell.strip())
    return any(hint in joined for hint in CSV_HEADER_HINTS)


def _count_csv_data_rows(path: Path) -> int:
    header_seen = False
    rows = 0
    with path.open("r", encoding="utf-8-sig", errors="ignore", newline="") as handle:
        reader = csv.reader(handle)
        for row in reader:
            if not any(cell.strip() for cell in row):
                continue
            if not header_seen:
                if len(row) >= 2 and _looks_like_csv_header(row):
                    header_seen = True
                continue
            if len(row) >= 2 and any(cell.strip() for cell in row):
                rows += 1
    return rows

def _sample_jsonl_data_markers(path: Path) -> int:
    with path.open("rb") as handle:
        chunk = handle.read(MAX_TEXT_SAMPLE_BYTES)
    # EIA JSONL rows encode data points as ["20260305T07","0"] or ["2024",3.29].
    markers = re.findall(rb'(?:\["|"period"\s*:\s*"|"timestamp"\s*:\s*"|")(?:19|20)\d{2}', chunk)
    return len(markers)


def _count_xlsx_rows(path: Path) -> int:
    rows = 0
    with zipfile.ZipFile(path) as workbook:
        for name in workbook.namelist():
            if not name.startswith("xl/worksheets/sheet") or not name.endswith(".xml"):
                continue
            data = workbook.read(name)
            rows += len(re.findall(rb"<row\b", data))
    return max(0, rows - 1)


def _count_zip_members(path: Path) -> int:
    with zipfile.ZipFile(path) as archive:
        return sum(1 for member in archive.infolist() if not member.is_dir())


def profile_local_source(data_dir: Path, spec: dict) -> dict:
    path = data_dir / spec["file"]
    profile = {
        "sector": spec["sector"],
        "file": spec["file"],
        "label": spec.get("label", spec["file"]),
        "root": str(data_dir),
        "exists": path.exists(),
        "bytes": 0,
        "measured_rows": 0,
        "measurement_mode": "missing",
    }
    if not path.exists():
        return profile

    size = path.stat().st_size
    profile["bytes"] = int(size)
    suffix = path.suffix.lower()
    try:
        if suffix == ".csv":
            profile["measured_rows"] = int(_count_csv_data_rows(path))
            profile["measurement_mode"] = "csv_rows"
        elif suffix in {".txt", ".json"}:
            profile["measured_rows"] = int(_sample_jsonl_data_markers(path))
            profile["measurement_mode"] = "text_sampled_time_markers"
        elif suffix == ".xlsx":
            profile["measured_rows"] = int(_count_xlsx_rows(path))
            profile["measurement_mode"] = "xlsx_sheet_rows"
        elif suffix == ".zip":
            profile["measured_rows"] = int(_count_zip_members(path))
            profile["measurement_mode"] = "zip_member_count"
        else:
            profile["measurement_mode"] = "file_present_unparsed"
    except Exception as exc:
        profile["measurement_mode"] = f"profiling_error:{type(exc).__name__}"
    return profile


def build_local_evidence(data_roots=None) -> dict:
    by_sector: dict[str, dict] = {}
    roots = _normalize_data_roots(data_roots)
    for root in roots:
        for spec in LOCAL_SOURCE_SPECS:
            profile = profile_local_source(root, spec)
            sector = spec["sector"]
            pack = by_sector.setdefault(
                sector,
                {
                    "source_count": 0,
                    "measured_rows": 0,
                    "bytes": 0,
                    "source_files": [],
                    "measurement_modes": [],
                    "data_roots": [],
                    "local_evidence_score": 0.0,
                },
            )
            if not profile["exists"]:
                continue
            pack["source_count"] += 1
            pack["measured_rows"] += int(profile.get("measured_rows", 0))
            pack["bytes"] += int(profile.get("bytes", 0))
            pack["source_files"].append(profile)
            pack["measurement_modes"].append(profile.get("measurement_mode", "unknown"))
            pack["data_roots"].append(str(root))

    for pack in by_sector.values():
        row_score = np.log10(max(1, float(pack["measured_rows"]))) * 1.8
        source_score = min(float(pack["source_count"]) * 0.9, 4.5)
        byte_score = min(np.log10(max(1, float(pack["bytes"]))) * 0.25, 2.0)
        pack["local_evidence_score"] = round(min(12.0, row_score + source_score + byte_score), 4)
        pack["measurement_modes"] = sorted(set(pack["measurement_modes"]))
        pack["data_roots"] = sorted(set(pack["data_roots"]))
    return by_sector


def to_records(sector_matrix: dict, opp_gain: dict, local_evidence: dict | None = None):
    impact = sector_matrix.get("sectors", {})
    gains = opp_gain.get("sectors", {})
    local_evidence = local_evidence or {}
    rows = []
    for sector, d in impact.items():
        g = gains.get(sector, {})
        evidence = local_evidence.get(sector, {})
        rows.append(
            {
                "sector": sector,
                "outage_count": float(d.get("outage_count", 0)),
                "total_loss_usd": float(d.get("total_loss_usd", 0.0)),
                "recoverable_annual_usd": float(d.get("recoverable_annual_usd", 0.0)),
                "baseline_annual_loss_usd": float(g.get("baseline_annual_loss_usd", 0.0)),
                "avg_savings_pct": float(g.get("avg_savings_pct", 0.0)),
                "annual_recoverable_usd": float(g.get("annual_recoverable_usd", 0.0)),
                "sharpe_improvement": float(g.get("sharpe_improvement", 0.0)),
                "local_source_count": float(evidence.get("source_count", 0)),
                "local_measured_rows": float(evidence.get("measured_rows", 0)),
                "local_evidence_score": float(evidence.get("local_evidence_score", 0.0)),
                "local_source_files": [p.get("file", "") for p in evidence.get("source_files", [])],
                "local_measurement_modes": evidence.get("measurement_modes", []),
            }
        )
    return rows


def compute_with_polars(records):
    if not records:
        return None

    if pl is not None:
        df = pl.DataFrame(records)
        df = df.with_columns(
            [
                pl.when(pl.col("total_loss_usd") > 0)
                .then(pl.col("annual_recoverable_usd") / pl.col("total_loss_usd"))
                .otherwise(0.0)
                .alias("recovery_efficiency"),
                (
                    pl.col("sharpe_improvement") * 0.55
                    + pl.col("avg_savings_pct") * 100.0 * 0.30
                    + pl.col("outage_count") * 0.15
                    + pl.col("local_evidence_score") * 0.35
                ).alias("institutional_score"),
            ]
        )
        frame_rows = df.to_dicts()
        top = (
            df.sort("institutional_score", descending=True)
            .select(
                [
                    "sector",
                    "institutional_score",
                    "annual_recoverable_usd",
                    "sharpe_improvement",
                    "avg_savings_pct",
                    "local_measured_rows",
                    "local_source_count",
                    "local_evidence_score",
                    "local_source_files",
                    "local_measurement_modes",
                ]
            )
            .head(10)
            .to_dicts()
        )
    else:
        df = pd.DataFrame.from_records(records)
        if df.empty:
            return None
        df["recovery_efficiency"] = np.where(
            df["total_loss_usd"] > 0,
            df["annual_recoverable_usd"] / df["total_loss_usd"],
            0.0,
        )
        df["institutional_score"] = (
            df["sharpe_improvement"] * 0.55
            + df["avg_savings_pct"] * 100.0 * 0.30
            + df["outage_count"] * 0.15
            + df["local_evidence_score"] * 0.35
        )
        frame_rows = df.to_dict(orient="records")
        top = (
            df.sort_values("institutional_score", ascending=False)[
                [
                    "sector",
                    "institutional_score",
                    "annual_recoverable_usd",
                    "sharpe_improvement",
                    "avg_savings_pct",
                    "local_measured_rows",
                    "local_source_count",
                    "local_evidence_score",
                    "local_source_files",
                    "local_measurement_modes",
                ]
            ]
            .head(10)
            .to_dict(orient="records")
        )

    score_rows = [{"sector": row.get("sector", ""), "institutional_score": row.get("institutional_score", 0.0)} for row in frame_rows]
    score_vals = np.array([float(r.get("institutional_score", 0.0)) for r in score_rows], dtype=float)
    mu = float(score_vals.mean()) if score_vals.size else 0.0
    sd = float(score_vals.std()) if score_vals.size else 0.0
    if sd <= 1e-12:
        z_vals = np.zeros_like(score_vals)
    else:
        z_vals = (score_vals - mu) / sd

    anomalies = []
    for row, z in zip(score_rows, z_vals.tolist()):
        if abs(z) > 1.5:
            anomalies.append({"sector": row.get("sector", ""), "score_z": float(z)})

    return {
        "top_sectors": top,
        "anomalies": anomalies,
        "sector_frame": frame_rows,
    }


def compute_with_duckdb(records):
    if duckdb is None or not records:
        return None
    con = duckdb.connect(database=":memory:")
    pdf = pd.DataFrame.from_records(records)
    con.register("sector_data", pdf)
    q = """
    SELECT
      sector,
      annual_recoverable_usd,
      sharpe_improvement,
      avg_savings_pct,
      outage_count,
      local_measured_rows,
      local_source_count,
      local_evidence_score,
      (0.55 * sharpe_improvement + 30.0 * avg_savings_pct + 0.15 * outage_count + 0.35 * local_evidence_score) AS tactical_score
    FROM sector_data
    ORDER BY tactical_score DESC
    LIMIT 10
    """
    out = con.execute(q).fetchdf().to_dict(orient="records")
    con.close()
    return out


def build_html(report: dict) -> str:
    rows = []
    for r in report.get("top_sectors", []):
        rows.append(
            "<tr>"
            f"<td>{r.get('sector','')}</td>"
            f"<td>{float(r.get('institutional_score',0.0)):.2f}</td>"
            f"<td>${float(r.get('annual_recoverable_usd',0.0)):,.0f}</td>"
            f"<td>{float(r.get('sharpe_improvement',0.0)):.2f}</td>"
            f"<td>{float(r.get('avg_savings_pct',0.0))*100.0:.2f}%</td>"
            f"<td>{float(r.get('local_measured_rows',0.0)):,.0f}</td>"
            f"<td>{int(float(r.get('local_source_count',0.0)))}</td>"
            "</tr>"
        )

    anomalies = report.get("anomalies", [])
    anomalies_html = "<br>".join(
        [f"{a.get('sector','')}: z={float(a.get('score_z',0.0)):.2f}" for a in anomalies]
    ) or "None"

    return f"""
<!doctype html>
<html lang='en'>
<head>
<meta charset='utf-8'>
<meta name='viewport' content='width=device-width, initial-scale=1'>
<title>LumenCore Advanced Fleet Validation</title>
<style>
body{{margin:0;padding:24px;background:#081426;color:#e8f2ff;font-family:Segoe UI,Arial,sans-serif;}}
.wrap{{max-width:1300px;margin:0 auto;}}
.card{{background:#0f1d3a;border:1px solid #234477;border-radius:14px;padding:18px;margin-bottom:16px;}}
h1{{margin:0 0 10px 0;font-size:34px;color:#5ff1d2;}}
.grid{{display:grid;grid-template-columns:repeat(auto-fit,minmax(220px,1fr));gap:12px;}}
.k{{font-size:12px;color:#9dc3f1;text-transform:uppercase;}}
.v{{font-size:24px;font-weight:700;margin-top:8px;}}
table{{width:100%;border-collapse:collapse;}}
th,td{{padding:10px;border-bottom:1px solid #24456f;text-align:left;}}
th{{color:#7fffd4;}}
</style>
</head>
<body>
<div class='wrap'>
  <h1>Advanced Fleet Validation</h1>
  <div class='card'>
    <div class='grid'>
      <div><div class='k'>Generated UTC</div><div class='v'>{report.get('generated_utc','')}</div></div>
      <div><div class='k'>Model Stack</div><div class='v'>{report.get('stack','')}</div></div>
      <div><div class='k'>Sectors Scored</div><div class='v'>{report.get('sectors_scored',0)}</div></div>
      <div><div class='k'>Anomaly Count</div><div class='v'>{len(report.get('anomalies',[]))}</div></div>
    </div>
  </div>
  <div class='card'>
    <h3>Top Tactical Sectors</h3>
    <table>
      <thead><tr><th>Sector</th><th>Institutional/Evidence Score</th><th>Recoverable Annual</th><th>Sharpe</th><th>Savings</th><th>Measured Rows</th><th>Local Sources</th></tr></thead>
      <tbody>{''.join(rows)}</tbody>
    </table>
    <p style='color:#9dc3f1;font-size:13px;margin-top:12px;'>Measured rows are local/source-evidence support. Recoverable annual remains tied to the economic model and is not promoted from raw data alone.</p>
  </div>
  <div class='card'>
    <h3>Z-Score Anomaly Signals</h3>
    <div>{anomalies_html}</div>
  </div>
</div>
</body>
</html>
"""


def main() -> dict:
    sector_matrix = read_json(SECTOR_MATRIX, {})
    opp_gain = read_json(OPP_GAIN, {})
    rolling = read_json(ROLLING_PERF, {})
    data_roots = configured_data_roots()
    local_evidence = build_local_evidence(data_roots)

    records = to_records(sector_matrix, opp_gain, local_evidence)
    polars_pack = compute_with_polars(records) or {"top_sectors": [], "anomalies": [], "sector_frame": []}
    duckdb_top = compute_with_duckdb(records) or []

    stack = []
    stack.append("polars" if pl is not None else "polars-missing")
    stack.append("duckdb" if duckdb is not None else "duckdb-missing")
    stack.append("numpy")
    stack.append("pandas")

    report = {
        "generated_utc": now_utc(),
        "stack": ", ".join(stack),
        "sectors_scored": len(records),
        "local_data_dir": str(DATA_DIR),
        "local_data_dirs": [str(root) for root in data_roots],
        "local_evidence_summary": {
            "sectors_with_local_sources": sum(1 for row in local_evidence.values() if row.get("source_count", 0) > 0),
            "total_local_sources": sum(int(row.get("source_count", 0)) for row in local_evidence.values()),
            "total_measured_rows": sum(int(row.get("measured_rows", 0)) for row in local_evidence.values()),
        },
        "local_evidence": local_evidence,
        "top_sectors": polars_pack.get("top_sectors", []),
        "anomalies": polars_pack.get("anomalies", []),
        "duckdb_top": duckdb_top,
        "paper_runtime": {
            "equity": rolling.get("current_equity", 0.0),
            "paper_sharpe": rolling.get("paper_sharpe", 0.0),
            "trades": rolling.get("trades", 0),
            "win_rate_pct": rolling.get("win_rate_pct", 0.0),
        },
    }

    REPORT_JSON.write_text(json.dumps(report, indent=2), encoding="utf-8")
    REPORT_HTML.write_text(build_html(report), encoding="utf-8")
    print(f"[ADVANCED] wrote {REPORT_JSON}")
    print(f"[ADVANCED] wrote {REPORT_HTML}")
    return report


if __name__ == "__main__":
    main()
