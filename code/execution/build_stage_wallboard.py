"""
Stage Mode Wallboard — LumaTrader Institutional
Zero scroll. 6 giant blocks. Readable from back of conference room.
Run once (export) or continuously (serve).
"""
from __future__ import annotations

import argparse
import json
import re
import time
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(r"C:\LumaTrader\INSTITUTIONAL_STACK_V2")
OUT_EXEC = ROOT / "out" / "execution"
DASH = ROOT / "dashboard"

OPPORTUNITY_BRIEF = OUT_EXEC / "institutional_opportunity_executive_brief.json"
LANE_ALERTS       = OUT_EXEC / "institutional_sector_lane_alerts_latest.json"
REPORT            = OUT_EXEC / "institutional_crypto_paper_report.json"
RECONNECT         = OUT_EXEC / "institutional_reconnect_status_latest.json"
DASH_HEARTBEAT    = OUT_EXEC / "institutional_crypto_dashboard_heartbeat.json"
TICKER_STATUS     = OUT_EXEC / "multi_exchange_paper_ticker_status.json"
LIVE_ENGINE_HEARTBEAT = OUT_EXEC / "live_engine_heartbeat.json"
LIVE_KEYS_ENV_CANDIDATES = [
  ROOT / "config" / "luma_live_keys.env",
  ROOT / "code" / "execution" / "config" / "luma_live_keys.env",
]
LIVE_SOURCE_REGISTRY_CANDIDATES = [
  ROOT / "config" / "live_source_registry.json",
  ROOT / "out" / "source_truth_table.json",
]

STAGE_HTML    = DASH / "stage_wallboard.html"
HEARTBEAT     = OUT_EXEC / "stage_wallboard_heartbeat.json"


# ──────────────────────────── helpers ──────────────────────────────────────

def now_utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")


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
    if value >= 1_000_000:
        return f"${value / 1_000_000:.2f}M"
    if value >= 1_000:
        return f"${value:,.0f}"
    return f"${value:.2f}"


def pct(value: float) -> str:
    return f"{(100.0 * value):.1f}%"


def _existing_path(candidates: list[Path]) -> Path | None:
  for path in candidates:
    if path.exists():
      return path
  return None


def load_live_key_coverage() -> tuple[int, int, int, int]:
  env_path = _existing_path(LIVE_KEYS_ENV_CANDIDATES)
  key_var_count = 0
  family_set: set[str] = set()
  enabled_sources = 0
  enabled_sectors = 0

  if env_path is not None:
    suffix_re = re.compile(r"(_API_KEY|_API_SECRET|_KEY|_SECRET|_TOKEN)$")
    try:
      for raw in env_path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
          continue
        name, value = line.split("=", 1)
        name = name.strip()
        value = value.strip()
        if not name or not value:
          continue
        if not any(tag in name for tag in ("KEY", "SECRET", "TOKEN")):
          continue

        key_var_count += 1
        family = suffix_re.sub("", name)
        if family:
          family_set.add(family)
    except Exception:
      pass

  registry_path = _existing_path(LIVE_SOURCE_REGISTRY_CANDIDATES)
  if registry_path is not None:
    payload = read_json(registry_path, {})
    rows = []
    if isinstance(payload, dict):
      if isinstance(payload.get("rows"), list):
        rows = [r for r in payload.get("rows", []) if isinstance(r, dict)]
      elif isinstance(payload.get("sources"), list):
        rows = [r for r in payload.get("sources", []) if isinstance(r, dict)]
    enabled_rows = [
      r for r in rows
      if bool(r.get("enabled", False))
      or str(r.get("status", "")).upper() in ("LIVE_KEY_PRESENT", "ENABLED", "ACTIVE", "OK")
    ]
    enabled_sources = len(enabled_rows)
    enabled_sectors = len({str(r.get("sector", "")).strip().lower() for r in enabled_rows if str(r.get("sector", "")).strip()})

  return (key_var_count, len(family_set), enabled_sources, enabled_sectors)


def write_heartbeat(mode: str, status: str, count: int, refresh_seconds: float | None = None, error: str | None = None) -> None:
    payload = {
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "mode": mode,
        "status": status,
        "refresh_count": int(count),
        "refresh_seconds": refresh_seconds,
        "stage_html": str(STAGE_HTML),
    }
    if error:
        payload["error"] = error
    OUT_EXEC.mkdir(parents=True, exist_ok=True)
    HEARTBEAT.write_text(json.dumps(payload, indent=2), encoding="utf-8")


# ──────────────────────────── core builder ─────────────────────────────────

def build_stage(refresh_seconds: float = 0.0) -> str:
    brief    = read_json(OPPORTUNITY_BRIEF, {})
    alerts   = read_json(LANE_ALERTS, {})
    report   = read_json(REPORT, {})
    reconnect      = read_json(RECONNECT, {})
    dash_heartbeat = read_json(DASH_HEARTBEAT, {})
    ticker_status  = read_json(TICKER_STATUS, {})
    live_engine_heartbeat = read_json(LIVE_ENGINE_HEARTBEAT, {})

    rolling_hour  = fnum(brief.get("rolling_total_hour_usd", 0.0))
    measured_hour = fnum(brief.get("measured_total_hour_usd", 0.0))
    modeled_only_hour = fnum(brief.get("modeled_only_hour_usd", 0.0))
    sectors_count = int(fnum(brief.get("sectors", 0.0)))
    top_sector    = str(brief.get("top_sector", "N/A")).upper().replace("_", " ")
    top_rows = brief.get("top_rows", []) if isinstance(brief, dict) else []
    top_rows_count = len([r for r in top_rows if isinstance(r, dict)])

    key_var_count, key_family_count, enabled_sources, enabled_sectors = load_live_key_coverage()
    measured_share = 0.0
    if rolling_hour > 0:
      measured_share = max(0.0, min(1.0, measured_hour / rolling_hour))

    crit = int(fnum(alerts.get("critical_count", 0.0)))
    warn = int(fnum(alerts.get("warning_count", 0.0)))
    alert_text = "ALL CLEAR" if (crit == 0 and warn == 0) else f"{crit} CRITICAL  {warn} WARNING"
    alert_class = "ok" if (crit == 0 and warn == 0) else "bad"

    # Health: use heartbeat freshness + ticker status as primary signals;
    # fall back to reconnect overall_healthy only if no better signal exists.
    dash_hb_ok = str(dash_heartbeat.get("status", "")).lower() == "ok"
    ticker_ok  = str(ticker_status.get("status", "")).lower() in ("ok", "running", "healthy", "active")
    reconnect_ok = bool(reconnect.get("overall_healthy", False)) if isinstance(reconnect, dict) else False
    # Consider healthy if either direct heartbeat signals are ok OR reconnect says ok
    healthy = dash_hb_ok or ticker_ok or reconnect_ok
    health_text  = "● LIVE & HEALTHY" if healthy else "⚠ DEGRADED"
    health_class = "ok" if healthy else "bad"

    refresh_meta = ""
    if refresh_seconds and refresh_seconds > 0:
        refresh_meta = f"<meta http-equiv='refresh' content='{int(max(refresh_seconds, 5.0))}' />"

    # Decide the ASK block value - use rolling opportunity as the anchor
    ask_line = f"Seeking early institutional partners to scale {usd(rolling_hour)}/hr measured edge."

    qa_1 = f"Q: Is this mostly modeled?  A: No - {usd(measured_hour)}/hr measured vs {usd(modeled_only_hour)}/hr modeled-only ({pct(measured_share)} measured share)."
    qa_2 = f"Q: How broad is live coverage?  A: {sectors_count} sectors tracked, {top_rows_count} active lanes ranked, {enabled_sources} enabled sources across {enabled_sectors} sectors ({key_var_count} key vars)."
    orch_status = str(live_engine_heartbeat.get("status", "unknown") or "unknown").upper()
    orch_stream_brief = str(live_engine_heartbeat.get("stream_brief", "n/a") or "n/a")
    qa_3 = f"Q: Is this operational right now?  A: {health_text.replace('● ', '')}; orchestrator={orch_status}; stream={orch_stream_brief}; lane posture {crit} critical / {warn} warning; top lane {top_sector}."

    html = f"""<!doctype html>
<html lang='en'>
<head>
  <meta charset='utf-8' />
  <meta name='viewport' content='width=device-width, initial-scale=1' />
  {refresh_meta}
  <title>LumaTrader — Stage Wallboard</title>
  <style>
    *, *::before, *::after {{ box-sizing: border-box; margin: 0; padding: 0; }}

    html, body {{
      width: 100vw;
      height: 100vh;
      overflow: hidden;
      background: #050c17;
      font-family: 'Segoe UI', 'Arial Black', Arial, sans-serif;
      color: #f0f6ff;
    }}

    /* ── outer layout ── */
    .shell {{
      display: flex;
      flex-direction: column;
      height: 100vh;
      padding: 2vh 2vw 1vh;
      gap: 1.5vh;
    }}

    /* ── header bar ── */
    .header {{
      display: flex;
      align-items: baseline;
      justify-content: space-between;
      flex-shrink: 0;
    }}
    .logo {{
      font-size: clamp(28px, 3.5vw, 60px);
      font-weight: 900;
      letter-spacing: -0.5px;
      color: #ffffff;
      text-transform: uppercase;
    }}
    .logo span {{ color: #4ac8f0; }}
    .timestamp {{
      font-size: clamp(14px, 1.2vw, 22px);
      opacity: 0.6;
      letter-spacing: 0.5px;
    }}

    /* ── 6-block grid ── */
    .grid {{
      display: grid;
      grid-template-columns: repeat(3, 1fr);
      grid-template-rows: repeat(2, 1fr);
      gap: 1.5vw;
      flex: 1;
      min-height: 0;
    }}

    .block {{
      background: linear-gradient(145deg, #0d1d30 0%, #091525 100%);
      border: 1.5px solid rgba(74, 200, 240, 0.18);
      border-radius: 20px;
      display: flex;
      flex-direction: column;
      justify-content: center;
      align-items: flex-start;
      padding: 3vh 3vw;
      position: relative;
      overflow: hidden;
    }}

    .block::before {{
      content: '';
      position: absolute;
      top: 0; left: 0; right: 0;
      height: 3px;
      background: linear-gradient(90deg, #4ac8f0, #2e85ff, transparent);
      border-radius: 20px 20px 0 0;
    }}

    .block-label {{
      font-size: clamp(14px, 1.4vw, 26px);
      font-weight: 700;
      text-transform: uppercase;
      letter-spacing: 2px;
      opacity: 0.65;
      margin-bottom: 1.2vh;
    }}

    .block-value {{
      font-size: clamp(28px, 4.8vw, 100px);
      font-weight: 900;
      line-height: 1.05;
      letter-spacing: -1px;
      white-space: normal;
      word-break: break-word;
      overflow-wrap: break-word;
    }}

    .block-sub {{
      font-size: clamp(12px, 1.1vw, 20px);
      opacity: 0.55;
      margin-top: 1vh;
      line-height: 1.4;
      max-width: 90%;
    }}

    .sub-tight {{
      max-width: 100%;
      font-size: clamp(12px, 1.0vw, 18px);
    }}

    /* colour variants */
    .c-gold   {{ color: #f5d87a; }}
    .c-teal   {{ color: #4ac8f0; }}
    .c-green  {{ color: #67e5c4; }}
    .c-white  {{ color: #ffffff; }}
    .c-purple {{ color: #c09dff; }}
    .ok       {{ color: #67e5c4; }}
    .bad      {{ color: #ff8d78; }}

    /* ASK block gets an accent background */
    .block-ask {{
      background: linear-gradient(145deg, #0d2240 0%, #061628 100%);
      border-color: rgba(74, 200, 240, 0.38);
    }}
    .block-ask::before {{
      background: linear-gradient(90deg, #f5d87a, #4ac8f0, transparent);
    }}

    /* footer strip */
    .footer {{
      flex-shrink: 0;
      text-align: center;
      font-size: clamp(11px, 1vw, 18px);
      opacity: 0.38;
      letter-spacing: 1px;
      padding-bottom: 0.5vh;
    }}

    .qa-strip {{
      flex-shrink: 0;
      background: rgba(5, 18, 34, 0.9);
      border: 1px solid rgba(74, 200, 240, 0.25);
      border-radius: 14px;
      padding: 0.9vh 1.1vw;
      display: grid;
      gap: 0.55vh;
    }}

    .qa {{
      font-size: clamp(11px, 1.0vw, 20px);
      line-height: 1.25;
      color: #d7e8ff;
      white-space: nowrap;
      overflow: hidden;
      text-overflow: ellipsis;
    }}

    .qa strong {{
      color: #67e5c4;
      font-weight: 800;
    }}
  </style>
</head>
<body>
<div class='shell'>

  <div class='header'>
    <div class='logo'>Luma<span>Trader</span> &nbsp;·&nbsp; Institutional Command Deck</div>
    <div class='timestamp'>{now_utc()}</div>
  </div>

  <div class='grid'>

    <!-- 1 — Rolling Opportunity -->
    <div class='block'>
      <div class='block-label'>Rolling Opportunity</div>
      <div class='block-value c-gold'>{usd(rolling_hour)}<span style='font-size:0.45em;font-weight:700;opacity:0.7'>/hr</span></div>
      <div class='block-sub'>Live rolling window across all scanned sectors</div>
    </div>

    <!-- 2 — Measured Opportunity -->
    <div class='block'>
      <div class='block-label'>Measured Opportunity</div>
      <div class='block-value c-teal'>{usd(measured_hour)}<span style='font-size:0.45em;font-weight:700;opacity:0.7'>/hr</span></div>
      <div class='block-sub'>Grounded in auditable confirmed lanes only</div>
    </div>

    <!-- 3 — System Health -->
    <div class='block'>
      <div class='block-label'>System Health</div>
      <div class='block-value {health_class}'>{health_text}</div>
      <div class='block-sub'>Continuous heartbeat · automated reconnect</div>
    </div>

    <!-- 4 — Top Sector -->
    <div class='block'>
      <div class='block-label'>Measured Coverage</div>
      <div class='block-value c-purple'>{pct(measured_share)}</div>
      <div class='block-sub sub-tight'>Sectors: {sectors_count} · Ranked lanes: {top_rows_count} · Enabled sources: {enabled_sources} · Key families: {key_family_count}</div>
    </div>

    <!-- 5 — Alert Status -->
    <div class='block'>
      <div class='block-label'>Lane Alerts</div>
      <div class='block-value {alert_class}'>{alert_text}</div>
      <div class='block-sub sub-tight'>Critical and warning-level lane deviations · Top lane: {top_sector}</div>
    </div>

    <!-- 6 — The Ask -->
    <div class='block block-ask'>
      <div class='block-label'>The Ask</div>
      <div class='block-value c-white' style='font-size:clamp(22px,2.8vw,54px);white-space:normal;line-height:1.15;'>{ask_line}</div>
      <div class='block-sub'>Contact: luma@lumatrader.com</div>
    </div>

  </div><!-- /grid -->

  <div class='qa-strip'>
    <div class='qa'><strong>{qa_1}</strong></div>
    <div class='qa'>{qa_2}</div>
    <div class='qa'>{qa_3}</div>
  </div>

  <div class='footer'>LUMATRADER INSTITUTIONAL STACK V2 &nbsp;·&nbsp; LIVE ARTIFACTS &nbsp;·&nbsp; AUTO-REFRESHING</div>

</div><!-- /shell -->
</body>
</html>
"""

    DASH.mkdir(parents=True, exist_ok=True)
    STAGE_HTML.write_text(html, encoding="utf-8")
    return str(STAGE_HTML)


# ──────────────────────────── entry point ──────────────────────────────────

def main() -> int:
    parser = argparse.ArgumentParser(description="Stage Mode Wallboard — 6-block full-screen investor view")
    parser.add_argument("--mode", choices=["export", "serve"], default="export",
                        help="export once or continuously refresh")
    parser.add_argument("--refresh-seconds", type=float, default=15.0,
                        help="cadence for serve mode and browser auto-refresh meta tag")
    args = parser.parse_args()

    if args.mode == "serve":
        refresh = max(float(args.refresh_seconds), 5.0)
        count = 0
        print(f"Stage wallboard serve mode — refresh every {refresh}s. Ctrl-C to stop.")
        while True:
            try:
                path = build_stage(refresh_seconds=refresh)
                count += 1
                write_heartbeat("serve", "ok", count, refresh)
                print(f"[{now_utc()}] written → {path}  (#{count})")
            except Exception as exc:
                count += 1
                write_heartbeat("serve", "error", count, refresh, str(exc))
                print(f"[{now_utc()}] ERROR: {exc}")
            time.sleep(refresh)
    else:
        try:
            path = build_stage(refresh_seconds=0.0)
            write_heartbeat("export", "ok", 1)
            print(f"Stage wallboard written → {path}")
        except Exception as exc:
            write_heartbeat("export", "error", 0, error=str(exc))
            print(f"ERROR: {exc}")
            return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
