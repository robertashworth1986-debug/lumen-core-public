from __future__ import annotations

import argparse
import json
import time
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(r"C:\LumaTrader\INSTITUTIONAL_STACK_V2")
OUT_EXEC = ROOT / "out" / "execution"
DASH = ROOT / "dashboard"

OPPORTUNITY_BRIEF = OUT_EXEC / "institutional_opportunity_executive_brief.json"
LANE_ALERTS = OUT_EXEC / "institutional_sector_lane_alerts_latest.json"
REPORT = OUT_EXEC / "institutional_crypto_paper_report.json"
RECONNECT = OUT_EXEC / "institutional_reconnect_status_latest.json"
WALLBOARD = DASH / "investor_wallboard.html"
TALK_TRACK = OUT_EXEC / "investor_talk_track.md"
HEARTBEAT = OUT_EXEC / "investor_wallboard_heartbeat.json"


def now_utc() -> str:
    return datetime.now(timezone.utc).isoformat()


def read_json(path: Path, default):
    try:
        if path.exists():
            return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        pass
    return default


def fnum(value, default: float = 0.0) -> float:
    try:
        return float(value)
    except Exception:
        return float(default)


def usd(value: float) -> str:
    return f"${value:,.0f}"


def pct(value: float) -> str:
    return f"{value * 100.0:,.2f}%"


def write_heartbeat(mode: str, status: str, refresh_count: int, refresh_seconds: float | None = None, error: str | None = None) -> None:
  payload = {
    "timestamp_utc": now_utc(),
    "mode": mode,
    "status": status,
    "refresh_count": int(refresh_count),
    "refresh_seconds": refresh_seconds,
    "wallboard": str(WALLBOARD),
  }
  if error:
    payload["error"] = error
  OUT_EXEC.mkdir(parents=True, exist_ok=True)
  HEARTBEAT.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def build_wallboard(refresh_seconds: float = 0.0) -> dict:
    brief = read_json(OPPORTUNITY_BRIEF, {})
    alerts = read_json(LANE_ALERTS, {})
    report = read_json(REPORT, {})
    reconnect = read_json(RECONNECT, {})

    rolling_hour = fnum(brief.get("rolling_total_hour_usd", 0.0))
    measured_hour = fnum(brief.get("measured_total_hour_usd", 0.0))
    modeled_only_hour = fnum(brief.get("modeled_only_hour_usd", 0.0))
    top_sector = str(brief.get("top_sector", "n/a"))

    portfolio = report.get("portfolio", {}) if isinstance(report, dict) else {}
    equity = fnum(portfolio.get("equity_usd", 0.0))
    ret = fnum(portfolio.get("return_pct", 0.0))

    crit = int(fnum(alerts.get("critical_count", 0.0)))
    warn = int(fnum(alerts.get("warning_count", 0.0)))

    healthy = bool(reconnect.get("overall_healthy", False)) if isinstance(reconnect, dict) else False
    health_label = "HEALTHY" if healthy else "DEGRADED"

    top_rows = brief.get("top_rows", []) if isinstance(brief, dict) else []
    top_rows = [row for row in top_rows if isinstance(row, dict)][:6]

    row_html = ""
    for row in top_rows:
        row_html += (
            "<div class='row'>"
            f"<div class='sector'>{str(row.get('sector', 'n/a')).upper()}</div>"
            f"<div class='val'>{usd(fnum(row.get('rolling_hour_usd', 0.0)))}/hr</div>"
            f"<div class='lane'>LANE {str(row.get('confidence_lane', 'LOW')).upper()}</div>"
            "</div>"
        )

    refresh_meta = ""
    if refresh_seconds and refresh_seconds > 0:
        refresh_meta = f"<meta http-equiv='refresh' content='{int(max(refresh_seconds, 5.0))}' />"

    html = f"""
<!doctype html>
<html lang='en'>
<head>
  <meta charset='utf-8' />
  <meta name='viewport' content='width=device-width, initial-scale=1' />
  {refresh_meta}
  <title>Investor Wallboard</title>
  <style>
    body {{
      margin: 0;
      font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
      color: #eef6ff;
      background: radial-gradient(circle at 10% 0%, #1d3049 0%, #08101b 48%, #050a12 100%);
    }}
    .wrap {{ padding: 24px 28px; }}
    .title {{ font-size: 64px; font-weight: 800; letter-spacing: 0.4px; margin-bottom: 12px; line-height: 1.05; }}
    .sub {{ font-size: 30px; opacity: 0.95; margin-bottom: 20px; }}
    .grid {{ display: grid; grid-template-columns: repeat(4, minmax(180px, 1fr)); gap: 14px; margin-bottom: 20px; }}
    .card {{ background: rgba(8, 15, 24, 0.88); border: 1px solid rgba(158, 196, 236, 0.28); border-radius: 16px; padding: 14px; }}
    .label {{ font-size: 20px; text-transform: uppercase; letter-spacing: 0.7px; opacity: 0.88; }}
    .value {{ font-size: 56px; font-weight: 800; margin-top: 5px; line-height: 1.05; }}
    .value-sm {{ font-size: 46px; font-weight: 800; margin-top: 5px; line-height: 1.05; }}
    .status-ok {{ color: #67e5c4; }}
    .status-bad {{ color: #ff8d78; }}
    .section-title {{ font-size: 42px; font-weight: 800; margin: 14px 0; }}
    .rows {{ background: rgba(8, 15, 24, 0.88); border: 1px solid rgba(158, 196, 236, 0.28); border-radius: 16px; padding: 10px 14px; }}
    .row {{ display: grid; grid-template-columns: 2fr 1fr 1fr; gap: 12px; padding: 12px 8px; border-bottom: 1px solid rgba(158, 196, 236, 0.18); align-items: center; }}
    .row:last-child {{ border-bottom: none; }}
    .sector {{ font-size: 36px; font-weight: 800; }}
    .val {{ font-size: 32px; font-weight: 800; color: #f1d68a; }}
    .lane {{ font-size: 28px; font-weight: 800; color: #79ded2; }}
    .footer {{ margin-top: 16px; font-size: 22px; opacity: 0.92; }}
    @media (max-width: 1200px) {{
      .grid {{ grid-template-columns: repeat(2, minmax(180px, 1fr)); }}
      .title {{ font-size: 42px; }}
      .value {{ font-size: 36px; }}
      .row {{ grid-template-columns: 1fr; }}
    }}
  </style>
</head>
<body>
  <div class='wrap'>
    <div class='title'>LumaTrader Institutional Value Wallboard</div>
    <div class='sub'>Big-screen investor view: readable, auditable, and focused on measured opportunity.</div>

    <div class='grid'>
      <div class='card'><div class='label'>Rolling Opportunity</div><div class='value'>{usd(rolling_hour)}/hr</div></div>
      <div class='card'><div class='label'>Measured Opportunity</div><div class='value'>{usd(measured_hour)}/hr</div></div>
      <div class='card'><div class='label'>Modeled-Only</div><div class='value'>{usd(modeled_only_hour)}/hr</div></div>
      <div class='card'><div class='label'>Top Sector</div><div class='value-sm'>{top_sector.upper()}</div></div>
      <div class='card'><div class='label'>Portfolio Equity</div><div class='value'>{usd(equity)}</div></div>
      <div class='card'><div class='label'>Return</div><div class='value'>{pct(ret)}</div></div>
      <div class='card'><div class='label'>Lane Alerts</div><div class='value-sm'>C:{crit} / W:{warn}</div></div>
      <div class='card'><div class='label'>System Health</div><div class='value-sm {('status-ok' if healthy else 'status-bad')}'>{health_label}</div></div>
    </div>

    <div class='section-title'>Top Opportunity Lanes</div>
    <div class='rows'>
      {row_html if row_html else '<div class="row"><div class="sector">NO LANE DATA AVAILABLE</div><div class="val">--</div><div class="lane">--</div></div>'}
    </div>

    <div class='footer'>Generated UTC: {now_utc()}</div>
  </div>
</body>
</html>
"""

    DASH.mkdir(parents=True, exist_ok=True)
    WALLBOARD.write_text(html, encoding="utf-8")

    talk_track = [
        "# Investor Talk Track",
        "",
        "## 30-second open",
        f"- This platform is currently surfacing {usd(rolling_hour)}/hour in rolling opportunity, with {usd(measured_hour)}/hour grounded in measured lanes.",
        f"- The top sector right now is {top_sector} and live system health is {health_label}.",
        "- What you are seeing is not a static deck. It is a live decision system with health, continuity, and auditable artifact trails.",
        "",
        "## 60-second proof",
        "- We separate measured value from modeled-only translation so claims remain investor-safe.",
        f"- Current lane alert posture is critical={crit}, warning={warn}.",
        "- Reconnect and continuity are automated, including package inventory, heartbeat checks, and status artifacts.",
        "",
      "## 3-minute Nobel-tier pitch",
      f"- 00:00-00:30 | Mission: We built a government-grade mission control stack that turns live operational drift into pre-failure action, with a current rolling value surface of {usd(rolling_hour)}/hour.",
      f"- 00:30-01:00 | Proof now: Measured lanes already account for {usd(measured_hour)}/hour, top live sector is {top_sector}, and health posture is {health_label}.",
      "- 01:00-01:30 | Investor edge: This is not speculative dashboard theater. It is an operating system with deterministic pipelines, auditable evidence trails, and continuity controls.",
      "- 01:30-02:00 | Defensibility: Lane isolation, hash-linked artifacts, and chain-of-custody reporting create a moat in execution integrity.",
      "- 02:00-02:30 | Capital thesis: Funding scales measured lane coverage, accelerates controlled live transition, and compounds the measured-value share over modeled-only share.",
      "- 02:30-03:00 | Close: Invest in a system that proves value before claiming value, and already runs with institutional-grade monitoring discipline.",
      "",
        "## Business close",
        "- Immediate value: deploy this command center as operational visibility for optimization and risk controls.",
        "- Expansion value: scale measured lanes across additional sectors while preserving audit discipline.",
        "- Funding use: accelerate measured-lane coverage and transition from paper proof to controlled live milestones.",
        "",
        f"Generated UTC: {now_utc()}",
    ]
    OUT_EXEC.mkdir(parents=True, exist_ok=True)
    TALK_TRACK.write_text("\n".join(talk_track) + "\n", encoding="utf-8")

    return {
        "wallboard": str(WALLBOARD),
        "talk_track": str(TALK_TRACK),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Build investor wallboard and talk track")
    parser.add_argument("--mode", choices=["export", "serve"], default="export", help="export once or continuously refresh artifacts")
    parser.add_argument("--refresh-seconds", type=float, default=15.0, help="refresh cadence for serve mode and browser auto-refresh")
    args = parser.parse_args()

    if args.mode == "serve":
        refresh = max(float(args.refresh_seconds), 5.0)
        count = 0
        while True:
            try:
                result = build_wallboard(refresh_seconds=refresh)
                count += 1
                write_heartbeat(mode="serve", status="ok", refresh_count=count, refresh_seconds=refresh)
                print(f"[{now_utc()}] refreshed {result['wallboard']}")
            except Exception as exc:
                count += 1
                write_heartbeat(mode="serve", status="error", refresh_count=count, refresh_seconds=refresh, error=str(exc))
                print(f"[{now_utc()}] refresh error: {exc}")
            time.sleep(refresh)

    result = build_wallboard(refresh_seconds=max(float(args.refresh_seconds), 5.0))
    write_heartbeat(mode="export", status="ok", refresh_count=1, refresh_seconds=max(float(args.refresh_seconds), 5.0))
    print(f"Wrote {result['wallboard']}")
    print(f"Wrote {result['talk_track']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
