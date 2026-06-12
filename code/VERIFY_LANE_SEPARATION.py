from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(
    os.environ.get("LUMA_STACK_ROOT", str(Path(__file__).resolve().parent.parent))
).expanduser().resolve()
CODE = ROOT / "code"
OUT = ROOT / "out"
DASH = Path(
    os.environ.get("LUMA_DASHBOARD_DIR", str(ROOT / "dashboard"))
).expanduser().resolve()
LAMASCOUT = ROOT / "LamaScout"
CONF = ROOT / "config"

REPORT_JSON = OUT / "lane_separation_audit.json"
REPORT_HTML = DASH / "lane_separation_audit.html"


def now_utc() -> str:
    return datetime.now(timezone.utc).isoformat()


def check(paths):
    result = []
    for p in paths:
        result.append({"path": str(p), "exists": p.exists()})
    return result


def score_lane(items):
    total = len(items)
    ok = sum(1 for i in items if i["exists"])
    pct = (ok / total * 100.0) if total else 0.0
    return ok, total, round(pct, 2)


def build_html(report):
    def render(name, lane):
        rows = "".join(
            f"<tr><td>{r['path']}</td><td>{'YES' if r['exists'] else 'NO'}</td></tr>" for r in lane["files"]
        )
        return f"""
        <div class='card'>
          <h3>{name}</h3>
          <div class='kpi'>Coverage: {lane['present']}/{lane['total']} ({lane['coverage_pct']}%)</div>
          <table><thead><tr><th>File</th><th>Exists</th></tr></thead><tbody>{rows}</tbody></table>
        </div>
        """

    return f"""
<!doctype html>
<html><head><meta charset='utf-8'><meta name='viewport' content='width=device-width, initial-scale=1'>
<title>LumenCore Lane Separation Audit</title>
<style>
body{{font-family:Segoe UI,Arial,sans-serif;background:#081426;color:#e9f3ff;margin:0;padding:24px;}}
.wrap{{max-width:1400px;margin:0 auto;}}
.card{{background:#0f1f3e;border:1px solid #264d82;border-radius:12px;padding:16px;margin-bottom:16px;}}
h1{{margin:0 0 8px 0;color:#73ffd6;}}
.small{{color:#a9c4ec;font-size:13px;}}
.kpi{{font-size:15px;color:#7fffd4;margin-bottom:10px;}}
table{{width:100%;border-collapse:collapse;}}
th,td{{border-bottom:1px solid #2a4c79;padding:8px;text-align:left;font-size:12px;}}
</style>
</head><body><div class='wrap'>
<h1>Lane Separation Audit</h1>
<div class='card'><div class='small'>Generated UTC: {report['generated_utc']}</div>
<div class='small'>Overall status: <b>{report['overall_status']}</b></div>
<div class='small'>Interlace policy: Shared control-plane files allowed, execution/state files lane-bound.</div></div>
{render('Trader Lane', report['trader_lane'])}
{render('Scout Lane', report['scout_lane'])}
{render('Cross-Sector Lane', report['cross_sector_lane'])}
{render('Shared Control Plane', report['shared_control_plane'])}
</div></body></html>
"""


def main():
    trader_files = [
        OUT / "paper_trade_state.json",
        OUT / "paper_trade_ledger.jsonl",
        OUT / "rolling_performance.json",
        DASH / "alpaca_paper_live_dashboard.html",
        CODE / "alpaca_paper_loop_builder.py",
    ]

    scout_files = [
        LAMASCOUT / "out" / "truth_engine_summary.json",
        DASH / "lumascout_dashboard.html",
        LAMASCOUT / "src" / "artist_scout_engine.py",
        LAMASCOUT / "run" / "RUN_LAMASCOUT.ps1",
    ]

    cross_sector_files = [
        OUT / "sector_value_matrix.json",
        OUT / "source_truth_table.json",
        DASH / "infra_institutional_live_dashboard.html",
        CODE / "execution" / "sector_opp_gain_server.py",
        CODE / "RUN_CROSS_SECTOR_INTEL_STACK.ps1",
    ]

    shared_files = [
        CONF / "runtime_control.json",
        CONF / "paper_trader_runtime.json",
        OUT / "unified_dashboard_chain_of_custody_sha256.json",
        DASH / "LUMENCORE_MASTER_DASHBOARD_UNIFIED_20260425.html",
        DASH / "advanced_fleet_validation.html",
    ]

    trader = {"files": check(trader_files)}
    scout = {"files": check(scout_files)}
    cross = {"files": check(cross_sector_files)}
    shared = {"files": check(shared_files)}

    for lane in (trader, scout, cross, shared):
        present, total, pct = score_lane(lane["files"])
        lane["present"] = present
        lane["total"] = total
        lane["coverage_pct"] = pct

    all_pct = [trader["coverage_pct"], scout["coverage_pct"], cross["coverage_pct"], shared["coverage_pct"]]
    status = "PASS" if min(all_pct) >= 80.0 else "WARN"

    report = {
        "generated_utc": now_utc(),
        "overall_status": status,
        "trader_lane": trader,
        "scout_lane": scout,
        "cross_sector_lane": cross,
        "shared_control_plane": shared,
    }

    REPORT_JSON.write_text(json.dumps(report, indent=2), encoding="utf-8")
    REPORT_HTML.write_text(build_html(report), encoding="utf-8")
    print(f"[LANE] wrote {REPORT_JSON}")
    print(f"[LANE] wrote {REPORT_HTML}")
    print(f"[LANE] overall_status={status}")


if __name__ == "__main__":
    main()
