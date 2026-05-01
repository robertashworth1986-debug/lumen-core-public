from __future__ import annotations

import json
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


ROOT = Path(r"C:\LumaTrader\INSTITUTIONAL_STACK_V2")
OUT = ROOT / "out"
DASH = Path(r"C:\LumaTrader\dashboard")

SECTOR_MATRIX = OUT / "sector_economic_impact_matrix.json"
OPP_GAIN = OUT / "opportunity_gain_matrix_updated.json"
ROLLING_PERF = OUT / "rolling_performance.json"
REPORT_JSON = OUT / "advanced_fleet_validation.json"
REPORT_HTML = DASH / "advanced_fleet_validation.html"


def now_utc() -> str:
    return datetime.now(timezone.utc).isoformat()


def read_json(path: Path, default):
    try:
        if path.exists():
            return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        pass
    return default


def to_records(sector_matrix: dict, opp_gain: dict):
    impact = sector_matrix.get("sectors", {})
    gains = opp_gain.get("sectors", {})
    rows = []
    for sector, d in impact.items():
        g = gains.get(sector, {})
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
            }
        )
    return rows


def compute_with_polars(records):
    if pl is None or not records:
        return None
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
            ).alias("institutional_score"),
        ]
    )

    top = (
        df.sort("institutional_score", descending=True)
        .select(["sector", "institutional_score", "annual_recoverable_usd", "sharpe_improvement", "avg_savings_pct"])
        .head(10)
        .to_dicts()
    )

    score_rows = df.select(["sector", "institutional_score"]).to_dicts()
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
        "sector_frame": df.to_dicts(),
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
      (0.55 * sharpe_improvement + 30.0 * avg_savings_pct + 0.15 * outage_count) AS tactical_score
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
      <thead><tr><th>Sector</th><th>Institutional Score</th><th>Recoverable Annual</th><th>Sharpe</th><th>Savings</th></tr></thead>
      <tbody>{''.join(rows)}</tbody>
    </table>
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

    records = to_records(sector_matrix, opp_gain)
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
