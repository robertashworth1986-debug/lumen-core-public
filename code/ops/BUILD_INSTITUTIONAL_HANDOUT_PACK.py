from __future__ import annotations

import csv
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.error import URLError
from urllib.request import urlopen


ROOT = Path(r"C:\LumaTrader\INSTITUTIONAL_STACK_V2")
ROOT_PARENT = ROOT.parent
OUT_DIR = ROOT / "out" / "ops" / "institutional_handout"

STARTUP_HEALTH = ROOT / "out" / "execution" / "startup_boot_health_latest.json"
DASH_HEALTH = ROOT / "out" / "execution" / "institutional_crypto_dashboard_health_latest.json"
GRANT_LANES = ROOT / "out" / "ops" / "grant_submit_lanes" / "grant_submit_lanes_latest.json"
FIT_PACK = ROOT / "out" / "ops" / "grant_submit_fit_pack" / "grant_submit_fit_pack_latest.json"
NOBEL_EXEC = ROOT / "out" / "INSTITUTIONAL_REVIEW_BUNDLE" / "nobel_tier_executive_summary.json"


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def now_tag() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def load_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    for enc in ("utf-8", "utf-8-sig", "utf-16", "utf-16-le", "utf-16-be", "ascii"):
        try:
            payload = json.loads(path.read_text(encoding=enc))
            return payload if isinstance(payload, dict) else {}
        except Exception:
            continue
    return {}


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def write_text(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content.rstrip("\r\n") + "\n", encoding="utf-8")


def money(value: Any) -> str:
    try:
        return f"${float(value):,.2f}"
    except Exception:
        return "$0.00"


def bool_text(value: Any) -> str:
    return "YES" if bool(value) else "NO"


def latest_parity_file() -> Path | None:
    ops_root = ROOT_PARENT / "out" / "ops"
    if not ops_root.exists():
        return None
    candidates = sorted(ops_root.glob("**/dashboard_mirror_parity_audit.csv"), key=lambda p: p.stat().st_mtime)
    return candidates[-1] if candidates else None


def parity_summary(parity_csv: Path | None) -> dict[str, Any]:
    if parity_csv is None or not parity_csv.exists():
        return {"drift": None, "missing": None, "abswin": None, "csv_path": ""}

    drift = 0
    missing = 0
    abswin = 0
    try:
        with parity_csv.open("r", encoding="utf-8", errors="ignore", newline="") as handle:
            reader = csv.DictReader(handle)
            for row in reader:
                same = str(row.get("same") or row.get("is_same") or "").strip().lower()
                if same in ("false", "0", "no"):
                    drift += 1

                left = str(row.get("left_exists") or row.get("root_exists") or "").strip().lower()
                right = str(row.get("right_exists") or row.get("mirror_exists") or "").strip().lower()
                if (left in ("false", "0", "no")) or (right in ("false", "0", "no")):
                    missing += 1

                has_abs = str(row.get("has_absolute_windows_path") or row.get("abs_windows_path") or "").strip().lower()
                if has_abs in ("true", "1", "yes"):
                    abswin += 1
    except Exception:
        return {"drift": None, "missing": None, "abswin": None, "csv_path": str(parity_csv)}

    return {
        "drift": drift,
        "missing": missing,
        "abswin": abswin,
        "csv_path": str(parity_csv),
    }


def probe_dashboard_http(url: str, timeout_seconds: float = 4.0) -> dict[str, Any]:
    try:
        with urlopen(url, timeout=timeout_seconds) as resp:
            code = int(getattr(resp, "status", 0) or 0)
            return {
                "ok": code == 200,
                "status_code": code,
                "error": "",
            }
    except URLError as exc:
        return {
            "ok": False,
            "status_code": None,
            "error": str(exc),
        }
    except Exception as exc:
        return {
            "ok": False,
            "status_code": None,
            "error": str(exc),
        }


def build_payload() -> dict[str, Any]:
    startup = load_json(STARTUP_HEALTH)
    dash_health = load_json(DASH_HEALTH)
    lanes = load_json(GRANT_LANES)
    fit = load_json(FIT_PACK)
    nobel = load_json(NOBEL_EXEC)
    parity = parity_summary(latest_parity_file())

    dashboard_url = str(dash_health.get("dashboard_url") or "http://127.0.0.1:5016")
    live_dash = probe_dashboard_http(dashboard_url)
    file_dash_healthy = bool(dash_health.get("healthy", False))
    file_dash_http_ok = bool(dash_health.get("http_ok", False))
    effective_dash_ok = file_dash_healthy or bool(live_dash.get("ok", False))

    patent_anchor = nobel.get("patent_anchor", {}) if isinstance(nobel, dict) else {}
    valuation = nobel.get("valuation_positioning_bands", []) if isinstance(nobel, dict) else []
    headline = nobel.get("headline", {}) if isinstance(nobel, dict) else {}

    services = startup.get("services", []) if isinstance(startup.get("services"), list) else []

    return {
        "generated_utc": now_iso(),
        "scope": "institutional_handout_pack",
        "readiness": {
            "startup_all_healthy": bool(startup.get("all_healthy", False)),
            "dashboard_http_healthy": effective_dash_ok,
            "dashboard_http_ok": file_dash_http_ok or bool(live_dash.get("ok", False)),
            "dashboard_file_healthy": file_dash_healthy,
            "dashboard_live_probe_ok": bool(live_dash.get("ok", False)),
            "dashboard_live_probe_status_code": live_dash.get("status_code"),
            "parity_drift": parity.get("drift"),
            "parity_missing": parity.get("missing"),
            "parity_abs_windows_paths": parity.get("abswin"),
        },
        "grant_submit": {
            "matched_lanes": ((lanes.get("totals") or {}).get("matched_tickets", 0) if isinstance(lanes, dict) else 0),
            "skip_lanes": ((lanes.get("totals") or {}).get("skip_tickets", 0) if isinstance(lanes, dict) else 0),
            "federal_lanes": ((lanes.get("totals") or {}).get("federal_tickets", 0) if isinstance(lanes, dict) else 0),
            "fit_likely": ((fit.get("summary") or {}).get("fit_likely", 0) if isinstance(fit, dict) else 0),
            "manual_check": ((fit.get("summary") or {}).get("manual_check", 0) if isinstance(fit, dict) else 0),
        },
        "patent_anchor": {
            "uspto_application": str(patent_anchor.get("uspto_application") or ""),
            "patent_center_reference": str(patent_anchor.get("patent_center_reference") or ""),
            "confirmation_number": str(patent_anchor.get("confirmation_number") or ""),
            "receipt_timestamp_et": str(patent_anchor.get("receipt_timestamp_et") or ""),
            "title": str(patent_anchor.get("title") or ""),
        },
        "valuation_positioning_bands": valuation if isinstance(valuation, list) else [],
        "economic_headline": {
            "projected_failure_cost_usd": float(headline.get("projected_failure_cost_usd", 0.0) or 0.0),
            "estimated_avoided_cost_usd": float(headline.get("estimated_avoided_cost_usd", 0.0) or 0.0),
            "prevented_pct": float(headline.get("prevented_pct", 0.0) or 0.0),
            "sims_run": int(headline.get("sims_run", 0) or 0),
        },
        "service_rows": services,
        "evidence_paths": {
            "startup_health": str(STARTUP_HEALTH),
            "dashboard_health": str(DASH_HEALTH),
            "parity_csv": str(parity.get("csv_path") or ""),
            "grant_submit_lanes": str(GRANT_LANES),
            "grant_submit_fit_pack": str(FIT_PACK),
            "nobel_exec_summary": str(NOBEL_EXEC),
        },
    }


def render_markdown(payload: dict[str, Any]) -> str:
    readiness = payload.get("readiness", {}) if isinstance(payload, dict) else {}
    grants = payload.get("grant_submit", {}) if isinstance(payload, dict) else {}
    patent = payload.get("patent_anchor", {}) if isinstance(payload, dict) else {}
    valuation = payload.get("valuation_positioning_bands", []) if isinstance(payload, dict) else []
    econ = payload.get("economic_headline", {}) if isinstance(payload, dict) else {}
    rows = payload.get("service_rows", []) if isinstance(payload, dict) else []
    paths = payload.get("evidence_paths", {}) if isinstance(payload, dict) else {}

    lines: list[str] = []
    lines.append("# Institutional Handout Pack")
    lines.append("")
    lines.append(f"Generated UTC: {payload.get('generated_utc', '')}")
    lines.append("")
    lines.append("## Readiness Snapshot")
    lines.append(f"- Startup all healthy: {bool_text(readiness.get('startup_all_healthy'))}")
    lines.append(f"- Dashboard HTTP healthy: {bool_text(readiness.get('dashboard_http_healthy'))}")
    lines.append(f"- Dashboard file healthy: {bool_text(readiness.get('dashboard_file_healthy'))}")
    lines.append(f"- Dashboard live probe healthy: {bool_text(readiness.get('dashboard_live_probe_ok'))}")
    lines.append(f"- Dashboard live probe status code: {readiness.get('dashboard_live_probe_status_code')}")
    lines.append(f"- Parity drift count: {readiness.get('parity_drift')}")
    lines.append(f"- Parity missing count: {readiness.get('parity_missing')}")
    lines.append(f"- Absolute Windows paths: {readiness.get('parity_abs_windows_paths')}")
    lines.append("")
    lines.append("## Grant Submission Readiness")
    lines.append(f"- Matched lanes: {grants.get('matched_lanes', 0)}")
    lines.append(f"- Federal lanes: {grants.get('federal_lanes', 0)}")
    lines.append(f"- Skip lanes: {grants.get('skip_lanes', 0)}")
    lines.append(f"- Fit likely opportunities: {grants.get('fit_likely', 0)}")
    lines.append(f"- Manual-check opportunities: {grants.get('manual_check', 0)}")
    lines.append("")
    lines.append("## Patent and Valuation Anchor")
    lines.append(f"- USPTO application: {patent.get('uspto_application', '')}")
    lines.append(f"- Patent Center reference: {patent.get('patent_center_reference', '')}")
    lines.append(f"- Confirmation number: {patent.get('confirmation_number', '')}")
    lines.append(f"- Receipt timestamp (ET): {patent.get('receipt_timestamp_et', '')}")
    lines.append(f"- Filing title: {patent.get('title', '')}")
    for item in valuation if isinstance(valuation, list) else []:
        lines.append(f"- Valuation band: {item}")
    lines.append("")
    lines.append("## Economic Impact Headline")
    lines.append(f"- Projected failure cost: {money(econ.get('projected_failure_cost_usd', 0.0))}")
    lines.append(f"- Estimated avoided cost: {money(econ.get('estimated_avoided_cost_usd', 0.0))}")
    lines.append(f"- Prevention rate: {float(econ.get('prevented_pct', 0.0) or 0.0):.4f}%")
    lines.append(f"- Optimization simulations run: {int(econ.get('sims_run', 0) or 0)}")
    lines.append("")
    lines.append("## Service State")
    for row in rows if isinstance(rows, list) else []:
        if not isinstance(row, dict):
            continue
        lines.append(
            f"- {row.get('Service', '')}: running={bool_text(row.get('Running'))}, process_count={row.get('ProcessCount', 0)}"
        )
    lines.append("")
    lines.append("## Evidence Paths")
    for key, value in paths.items() if isinstance(paths, dict) else []:
        lines.append(f"- {key}: {value}")

    return "\n".join(lines).rstrip() + "\n"


def render_html(payload: dict[str, Any]) -> str:
    readiness = payload.get("readiness", {}) if isinstance(payload, dict) else {}
    grants = payload.get("grant_submit", {}) if isinstance(payload, dict) else {}
    patent = payload.get("patent_anchor", {}) if isinstance(payload, dict) else {}
    valuation = payload.get("valuation_positioning_bands", []) if isinstance(payload, dict) else []

    valuation_rows = "".join(f"<li>{v}</li>" for v in (valuation if isinstance(valuation, list) else []))

    return f"""<!doctype html>
<html>
<head>
  <meta charset='utf-8' />
  <meta name='viewport' content='width=device-width, initial-scale=1' />
  <title>Luma Institutional Handout</title>
  <style>
    :root {{ --bg:#071325; --panel:#10233f; --line:#27456f; --txt:#e9f1ff; --muted:#9eb6d8; --accent:#72ffd7; --accent2:#6dc5ff; }}
    body {{ margin:0; background:radial-gradient(circle at 0% 0%, #15355f, transparent 40%), var(--bg); color:var(--txt); font-family:Segoe UI, Arial, sans-serif; }}
    .wrap {{ max-width:1200px; margin:0 auto; padding:24px; }}
    .title {{ font-size:38px; margin:0 0 6px 0; }}
    .sub {{ color:var(--muted); margin-bottom:16px; }}
    .grid {{ display:grid; grid-template-columns:repeat(3,1fr); gap:14px; }}
    .card {{ background:var(--panel); border:1px solid var(--line); border-radius:14px; padding:14px; }}
    .k {{ color:var(--muted); font-size:11px; text-transform:uppercase; letter-spacing:.08em; }}
    .v {{ font-size:28px; color:var(--accent); margin-top:8px; }}
    .v2 {{ font-size:20px; color:var(--accent2); margin-top:8px; }}
    h2 {{ margin:18px 0 8px 0; }}
    ul {{ margin:0; padding-left:18px; }}
    li {{ margin:4px 0; }}
  </style>
</head>
<body>
  <div class='wrap'>
    <h1 class='title'>Institutional Readiness Handout</h1>
    <div class='sub'>Generated UTC: {payload.get('generated_utc', '')}</div>

    <div class='grid'>
      <div class='card'><div class='k'>Startup Healthy</div><div class='v'>{bool_text(readiness.get('startup_all_healthy'))}</div></div>
      <div class='card'><div class='k'>Dashboard Healthy</div><div class='v'>{bool_text(readiness.get('dashboard_http_healthy'))}</div></div>
      <div class='card'><div class='k'>Parity Drift</div><div class='v'>{readiness.get('parity_drift')}</div></div>
    </div>

    <h2>Submission Readiness</h2>
    <div class='grid'>
      <div class='card'><div class='k'>Matched Lanes</div><div class='v2'>{grants.get('matched_lanes', 0)}</div></div>
      <div class='card'><div class='k'>Federal Lanes</div><div class='v2'>{grants.get('federal_lanes', 0)}</div></div>
      <div class='card'><div class='k'>Fit Likely</div><div class='v2'>{grants.get('fit_likely', 0)}</div></div>
    </div>

    <h2>Patent and Valuation Anchor</h2>
    <div class='card'>
      <ul>
        <li>USPTO application: {patent.get('uspto_application', '')}</li>
        <li>Patent Center reference: {patent.get('patent_center_reference', '')}</li>
        <li>Confirmation number: {patent.get('confirmation_number', '')}</li>
        <li>Receipt timestamp: {patent.get('receipt_timestamp_et', '')}</li>
        <li>Title: {patent.get('title', '')}</li>
      </ul>
      <ul>{valuation_rows}</ul>
    </div>
  </div>
</body>
</html>
"""


def main() -> int:
    payload = build_payload()
    tag = now_tag()

    json_ts = OUT_DIR / f"institutional_handout_{tag}.json"
    md_ts = OUT_DIR / f"institutional_handout_{tag}.md"
    html_ts = OUT_DIR / f"institutional_handout_{tag}.html"
    json_latest = OUT_DIR / "institutional_handout_latest.json"
    md_latest = OUT_DIR / "institutional_handout_latest.md"
    html_latest = OUT_DIR / "institutional_handout_latest.html"

    write_json(json_ts, payload)
    write_json(json_latest, payload)
    write_text(md_ts, render_markdown(payload))
    write_text(md_latest, render_markdown(payload))
    write_text(html_ts, render_html(payload))
    write_text(html_latest, render_html(payload))

    print("BUILD_INSTITUTIONAL_HANDOUT_PACK")
    print(f"json={json_latest}")
    print(f"md={md_latest}")
    print(f"html={html_latest}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
