from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(r"C:\LumaTrader\INSTITUTIONAL_STACK_V2")
OUT = ROOT / "out"
EXEC = OUT / "execution"
DASH = ROOT / "dashboard"

BREADTH_FILE = OUT / "approved_source_breadth_registry.json"
SCORECARD_FILE = EXEC / "institutional_metrics_scorecard.json"
KPI_FILE = EXEC / "kpi_summary.json"
EVIDENCE_DIR = OUT / "evidence_pack"

PAGE_HTML = DASH / "investor_breadth_credibility.html"
PAGE_JSON = EXEC / "investor_breadth_credibility.json"


def now_utc() -> str:
    return datetime.now(timezone.utc).isoformat()


def load_json(path: Path, default: Any) -> Any:
    try:
        if path.exists():
            return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        pass
    return default


def as_float(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except Exception:
        return float(default)


def latest_evidence_pack() -> str:
    if not EVIDENCE_DIR.exists():
        return "n/a"
    zips = sorted(EVIDENCE_DIR.glob("institutional_evidence_pack_*.zip"), key=lambda p: p.stat().st_mtime, reverse=True)
    return str(zips[0]) if zips else "n/a"


def build_payload() -> dict[str, Any]:
    breadth = load_json(BREADTH_FILE, {})
    scorecard = load_json(SCORECARD_FILE, {})
    kpi = load_json(KPI_FILE, {})

    sectors = breadth.get("sectors", []) if isinstance(breadth, dict) else []
    top_sectors = sorted(
        [s for s in sectors if isinstance(s, dict)],
        key=lambda row: int(row.get("combined_sources", 0)),
        reverse=True,
    )[:10]

    payload = {
        "generated_utc": now_utc(),
        "readiness_tier": str(kpi.get("readiness_tier", scorecard.get("readiness_tier", "UNKNOWN"))),
        "readiness_score": as_float(kpi.get("readiness_score", scorecard.get("readiness_score", 0.0))),
        "key_backed_enabled_sources": int(breadth.get("key_backed_enabled_sources", 0)),
        "open_access_approved_sources": int(breadth.get("open_access_approved_sources", 0)),
        "combined_approved_sources": int(breadth.get("combined_approved_sources", 0)),
        "sector_count": int(breadth.get("sector_count", 0)),
        "measured_total_hour_usd": as_float(kpi.get("measured_total_hour_usd", 0.0)),
        "rolling_total_hour_usd": as_float(kpi.get("rolling_total_hour_usd", 0.0)),
        "realized_roi_pct": as_float(kpi.get("realized_roi_pct", 0.0)),
        "win_rate_pct": as_float(kpi.get("win_rate_pct", 0.0)),
        "top_test_sharpe": as_float(kpi.get("top_test_sharpe", 0.0)),
        "top_walkforward_sharpe_mean": as_float(kpi.get("top_walkforward_sharpe_mean", 0.0)),
        "top_institutional_score": as_float(kpi.get("top_institutional_score", 0.0)),
        "evidence_pack": latest_evidence_pack(),
        "top_sectors": top_sectors,
    }
    return payload


def render_html(payload: dict[str, Any]) -> str:
    rows = "\n".join(
        [
            "<tr>"
            f"<td>{row.get('sector', 'n/a')}</td>"
            f"<td>{int(row.get('key_backed_sources', 0))}</td>"
            f"<td>{int(row.get('open_access_sources', 0))}</td>"
            f"<td>{int(row.get('combined_sources', 0))}</td>"
            "</tr>"
            for row in payload.get("top_sectors", [])
        ]
    )
    if not rows:
        rows = "<tr><td colspan='4'>No sector breadth rows available.</td></tr>"

    return f"""<!doctype html>
<html lang=\"en\">
<head>
<meta charset=\"utf-8\" />
<meta name=\"viewport\" content=\"width=device-width, initial-scale=1\" />
<title>Investor Breadth & Credibility</title>
<style>
:root {{
  --bg:#071018;
  --panel:#102131;
  --ink:#e8f1fa;
  --muted:#a7bacf;
  --accent:#49dcb1;
  --line:#2a3d52;
}}
body {{
  margin:0;
  font-family: "Segoe UI", "Helvetica Neue", sans-serif;
  color:var(--ink);
  background: radial-gradient(900px 500px at 10% -10%, #1b3349 0%, transparent 60%), var(--bg);
}}
.container {{max-width:1200px;margin:24px auto;padding:0 16px;}}
.grid {{display:grid;grid-template-columns:repeat(4,minmax(150px,1fr));gap:12px;}}
.card {{background:var(--panel);border:1px solid var(--line);border-radius:12px;padding:14px;}}
.label {{font-size:12px;color:var(--muted);text-transform:uppercase;letter-spacing:.5px;}}
.value {{font-size:26px;font-weight:700;margin-top:6px;}}
table {{width:100%;border-collapse:collapse;background:var(--panel);border:1px solid var(--line);border-radius:12px;overflow:hidden;}}
th,td {{padding:10px;border-bottom:1px solid var(--line);text-align:left;}}
th {{font-size:12px;color:var(--muted);text-transform:uppercase;letter-spacing:.5px;}}
.small {{color:var(--muted);font-size:12px;}}
@media (max-width:900px) {{.grid{{grid-template-columns:repeat(2,minmax(140px,1fr));}}}}
</style>
</head>
<body>
<div class=\"container\">
  <h1>Investor Breadth & Credibility Surface</h1>
  <p class=\"small\">Generated UTC: {payload['generated_utc']}</p>

  <div class=\"grid\">
    <div class=\"card\"><div class=\"label\">Readiness</div><div class=\"value\">{payload['readiness_tier']} ({payload['readiness_score']:.2f})</div></div>
    <div class=\"card\"><div class=\"label\">Combined Approved Sources</div><div class=\"value\">{payload['combined_approved_sources']}</div></div>
    <div class=\"card\"><div class=\"label\">Open-Access Sources</div><div class=\"value\">{payload['open_access_approved_sources']}</div></div>
    <div class=\"card\"><div class=\"label\">Measured $/hr</div><div class=\"value\">${payload['measured_total_hour_usd']:,.0f}</div></div>
  </div>

  <h2>Top Sector Breadth</h2>
  <table>
    <thead><tr><th>Sector</th><th>Key-backed</th><th>Open-access</th><th>Combined</th></tr></thead>
    <tbody>{rows}</tbody>
  </table>

  <h2>Credibility KPIs</h2>
  <div class=\"grid\">
    <div class=\"card\"><div class=\"label\">Rolling $/hr</div><div class=\"value\">${payload['rolling_total_hour_usd']:,.0f}</div></div>
    <div class=\"card\"><div class=\"label\">Realized ROI %</div><div class=\"value\">{payload['realized_roi_pct']:.2f}%</div></div>
    <div class=\"card\"><div class=\"label\">Win Rate %</div><div class=\"value\">{payload['win_rate_pct']:.2f}%</div></div>
    <div class=\"card\"><div class=\"label\">Walk-forward Sharpe</div><div class=\"value\">{payload['top_walkforward_sharpe_mean']:.2f}</div></div>
  </div>

  <p class=\"small\">Latest evidence pack: {payload['evidence_pack']}</p>
</div>
</body>
</html>
"""


def main() -> int:
    EXEC.mkdir(parents=True, exist_ok=True)
    DASH.mkdir(parents=True, exist_ok=True)

    payload = build_payload()
    PAGE_JSON.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    PAGE_HTML.write_text(render_html(payload), encoding="utf-8")

    print("INVESTOR BREADTH PAGE WRITTEN")
    print(PAGE_JSON)
    print(PAGE_HTML)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
