from __future__ import annotations

import argparse
import json
import os
import re
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib import error, request


ROOT = Path(__file__).resolve().parents[2]
OUT_DIR = ROOT / "out" / "ops"
REPORT_JSON = OUT_DIR / "staleness_report.json"
REPORT_MD = OUT_DIR / "staleness_report.md"


BAD_STATUSES = {"stale", "missing", "error", "broken"}
SEVERITY_ORDER = {"critical": 3, "warn": 2, "info": 1}
STATUS_ORDER = {"fresh": 0, "ok": 0, "warn": 1, "stale": 2, "missing": 3, "error": 4, "broken": 4}


def now_utc() -> datetime:
    return datetime.now(timezone.utc)


def iso_utc(dt: datetime | None) -> str:
    if dt is None:
        return ""
    return dt.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


def parse_timestamp(value: Any) -> datetime | None:
    if value is None:
        return None

    if isinstance(value, (int, float)):
        try:
            # Heuristic: if epoch milliseconds, normalize to seconds.
            ts = float(value)
            if ts > 1_000_000_000_000:
                ts = ts / 1000.0
            return datetime.fromtimestamp(ts, tz=timezone.utc)
        except Exception:
            return None

    if not isinstance(value, str):
        return None

    raw = value.strip()
    if not raw:
        return None

    if raw.endswith("Z"):
        raw = raw[:-1] + "+00:00"

    try:
        return datetime.fromisoformat(raw)
    except Exception:
        return None


def find_timestamp_in_obj(obj: Any, preferred_keys: list[str]) -> datetime | None:
    if isinstance(obj, dict):
        for key in preferred_keys:
            if key in obj:
                parsed = parse_timestamp(obj.get(key))
                if parsed:
                    return parsed

        for value in obj.values():
            parsed = find_timestamp_in_obj(value, preferred_keys)
            if parsed:
                return parsed

    if isinstance(obj, list):
        for item in obj:
            parsed = find_timestamp_in_obj(item, preferred_keys)
            if parsed:
                return parsed

    return None


def calc_age_minutes(ts: datetime | None) -> float | None:
    if ts is None:
        return None
    return round((now_utc() - ts.astimezone(timezone.utc)).total_seconds() / 60.0, 3)


@dataclass
class Probe:
    probe_id: str
    category: str
    target: str
    severity: str
    max_age_minutes: float | None = None
    kind: str = "file"
    timestamp_keys: tuple[str, ...] = (
        "generated_utc",
        "timestamp_utc",
        "timestamp",
        "updated_utc",
        "run_utc",
        "ts",
    )
    hint: str = ""


FILE_PROBES: list[Probe] = [
    Probe(
        probe_id="execution_events",
        category="trading",
        target=str(ROOT / "execution_events.jsonl"),
        severity="critical",
        max_age_minutes=20,
        kind="jsonl",
        hint="Relaunch orchestrator and confirm new submit_order/deadman_armed events.",
    ),
    Probe(
        probe_id="rolling_performance",
        category="trading",
        target=str(ROOT / "rolling_performance.json"),
        severity="critical",
        max_age_minutes=20,
        kind="json",
        hint="Ensure execution loop writes rolling_performance.json each cycle.",
    ),
    Probe(
        probe_id="runtime_drift_alert",
        category="risk",
        target=str(ROOT / "out" / "execution" / "runtime_drift_alert.json"),
        severity="warn",
        max_age_minutes=240,
        kind="json",
        hint="If stale, confirm drift monitor is still running and writing alerts.",
    ),
    Probe(
        probe_id="proofpack_latest",
        category="proof",
        target=str(ROOT / "out" / "execution" / "harmonic_backprop_proofpack" / "latest.json"),
        severity="warn",
        max_age_minutes=1440,
        kind="json",
        hint="Re-run harmonic_backprop_proofpack.py to refresh benchmark artifacts.",
    ),
    Probe(
        probe_id="frozen_delta_ledger",
        category="proof",
        target=str(ROOT / "out" / "frozen_delta_ledger.jsonl"),
        severity="warn",
        max_age_minutes=180,
        kind="jsonl",
        hint="Confirm frozen-delta writer is active and appending new entries.",
    ),
    Probe(
        probe_id="live_source_registry",
        category="sources",
        target=str(ROOT / "config" / "live_source_registry.json"),
        severity="warn",
        max_age_minutes=1440,
        kind="json",
        hint="Refresh source registry so investor pages show current source health.",
    ),
    Probe(
        probe_id="dashboard_grid_value",
        category="dashboard",
        target=str(ROOT / "dashboard" / "grid_value_live.json"),
        severity="warn",
        max_age_minutes=240,
        kind="json",
        hint="If stale/zero-only, re-run evidence hydration pipeline for dashboard cards.",
    ),
    Probe(
        probe_id="dashboard_infra_live",
        category="dashboard",
        target=str(ROOT / "dashboard" / "infra_live_dashboard.json"),
        severity="warn",
        max_age_minutes=240,
        kind="json",
        hint="Refresh infrastructure telemetry generator before investor demo.",
    ),
    Probe(
        probe_id="watchdog_status",
        category="ops",
        target=str(ROOT / "dashboard" / "orchestrator_watchdog_status.txt"),
        severity="warn",
        max_age_minutes=30,
        kind="text",
        hint="Watchdog status must update continuously with no unresolved issues.",
    ),
]


HTML_PROBES: list[Probe] = [
    Probe(
        probe_id="quant_lab_html",
        category="ui_integrity",
        target=str(ROOT / "dashboard" / "quant_lab.html"),
        severity="critical",
        kind="html",
        hint="Primary cockpit must parse cleanly for live demos.",
    ),
    Probe(
        probe_id="mission_control_html",
        category="ui_integrity",
        target=str(ROOT / "dashboard" / "mission_control.html"),
        severity="critical",
        kind="html",
        hint="Mission Control is investor-facing and must be structurally valid.",
    ),
    Probe(
        probe_id="scenario_mission_html",
        category="ui_integrity",
        target=str(ROOT / "dashboard" / "scenario_mission.html"),
        severity="warn",
        kind="html",
        hint="Scenario handoff panel should not contain malformed duplicate markup.",
    ),
    Probe(
        probe_id="harmonic_proofpack_html",
        category="ui_integrity",
        target=str(ROOT / "dashboard" / "harmonic_proofpack_mission.html"),
        severity="warn",
        kind="html",
        hint="Proof-pack page must stay valid for benchmark storytelling.",
    ),
    Probe(
        probe_id="luma_experience_html",
        category="ui_integrity",
        target=str(ROOT / "dashboard" / "luma_experience.html"),
        severity="warn",
        kind="html",
        hint="Experience scene should remain structurally valid for cinematic demo.",
    ),
]


API_PROBES: list[Probe] = [
    Probe(
        probe_id="api_health",
        category="api",
        target="/health",
        severity="critical",
        kind="api",
        hint="Gateway must respond on /health before any investor walkthrough.",
    ),
    Probe(
        probe_id="api_snapshot",
        category="api",
        target="/api/snapshot",
        severity="critical",
        max_age_minutes=30,
        kind="api",
        hint="Snapshot freshness drives most cockpit KPIs.",
    ),
    Probe(
        probe_id="api_master_snapshot_v3",
        category="api",
        target="/api/master/snapshot-v3",
        severity="critical",
        max_age_minutes=30,
        kind="api",
        hint="Master snapshot is the single source for premium investor view.",
    ),
    Probe(
        probe_id="api_harmonic_proofpack_latest",
        category="api",
        target="/api/proofpack/harmonic/latest",
        severity="warn",
        max_age_minutes=1440,
        kind="api",
        hint="Proof-pack endpoint should expose latest run and winner metrics.",
    ),
    Probe(
        probe_id="api_scene_runs",
        category="api",
        target="/api/scene/runs?limit=1",
        severity="warn",
        kind="api",
        hint="Scenario telemetry should remain reachable for cinematic mission mode.",
    ),
]


CHAINS: list[dict[str, Any]] = [
    {
        "chain_id": "trading_execution_chain",
        "title": "Trading Execution Chain",
        "probes": [
            "api_health",
            "api_snapshot",
            "execution_events",
            "rolling_performance",
            "watchdog_status",
        ],
    },
    {
        "chain_id": "investor_proof_chain",
        "title": "Investor Proof Chain",
        "probes": [
            "api_master_snapshot_v3",
            "api_harmonic_proofpack_latest",
            "proofpack_latest",
            "frozen_delta_ledger",
            "harmonic_proofpack_html",
        ],
    },
    {
        "chain_id": "showcase_visual_chain",
        "title": "Showcase Visual Chain",
        "probes": [
            "quant_lab_html",
            "mission_control_html",
            "luma_experience_html",
            "scenario_mission_html",
            "api_scene_runs",
        ],
    },
]


def _probe_status_from_age(age_minutes: float | None, max_age: float | None) -> str:
    if max_age is None:
        return "fresh"
    if age_minutes is None:
        return "warn"
    return "fresh" if age_minutes <= max_age else "stale"


def _render_html_probe(probe: Probe) -> dict[str, Any]:
    path = Path(probe.target)
    if not path.exists():
        return {
            "id": probe.probe_id,
            "category": probe.category,
            "severity": probe.severity,
            "target": probe.target,
            "status": "missing",
            "hint": probe.hint,
            "notes": "File is missing.",
        }

    text = ""
    try:
        text = path.read_text(encoding="utf-8", errors="replace")
    except Exception as exc:
        return {
            "id": probe.probe_id,
            "category": probe.category,
            "severity": probe.severity,
            "target": probe.target,
            "status": "error",
            "hint": probe.hint,
            "notes": f"Could not read html: {exc}",
        }

    html_open = len(re.findall(r"<html(?:\s|>)", text, flags=re.IGNORECASE))
    html_close = len(re.findall(r"</html\s*>", text, flags=re.IGNORECASE))
    head_open = len(re.findall(r"<head(?:\s|>)", text, flags=re.IGNORECASE))
    body_open = len(re.findall(r"<body(?:\s|>)", text, flags=re.IGNORECASE))

    structural_issues: list[str] = []
    advisory_issues: list[str] = []
    if html_open == 0 or html_close == 0:
        structural_issues.append("missing html root tags")
    if html_open > 1 or html_close > 1:
        structural_issues.append("duplicate html root markers")
    if head_open > 1:
        structural_issues.append("duplicate head sections")
    if body_open > 1:
        structural_issues.append("duplicate body sections")

    localhost_literals = text.count("127.0.0.1")
    if localhost_literals > 0:
        advisory_issues.append(f"contains {localhost_literals} localhost literal(s)")

    if structural_issues:
        status = "broken"
    elif advisory_issues:
        status = "warn"
    else:
        status = "fresh"

    issues = structural_issues + advisory_issues
    mtime = datetime.fromtimestamp(path.stat().st_mtime, tz=timezone.utc)

    return {
        "id": probe.probe_id,
        "category": probe.category,
        "severity": probe.severity,
        "target": probe.target,
        "status": status,
        "hint": probe.hint,
        "last_timestamp_utc": iso_utc(mtime),
        "age_minutes": calc_age_minutes(mtime),
        "max_age_minutes": probe.max_age_minutes,
        "notes": "; ".join(issues) if issues else "HTML structure looks valid.",
    }


def _load_json(path: Path) -> tuple[dict[str, Any] | list[Any] | None, str | None]:
    try:
        obj = json.loads(path.read_text(encoding="utf-8"))
        return obj, None
    except Exception as exc:
        return None, str(exc)


def _load_last_jsonl(path: Path) -> tuple[dict[str, Any] | None, str | None]:
    try:
        with path.open("r", encoding="utf-8", errors="replace") as handle:
            lines = [line.strip() for line in handle if line.strip()]
        if not lines:
            return None, "jsonl has no lines"
        obj = json.loads(lines[-1])
        if isinstance(obj, dict):
            return obj, None
        return None, "last jsonl line is not an object"
    except Exception as exc:
        return None, str(exc)


def _render_file_probe(probe: Probe) -> dict[str, Any]:
    path = Path(probe.target)
    if not path.exists():
        return {
            "id": probe.probe_id,
            "category": probe.category,
            "severity": probe.severity,
            "target": probe.target,
            "status": "missing",
            "hint": probe.hint,
            "notes": "File is missing.",
        }

    mtime = datetime.fromtimestamp(path.stat().st_mtime, tz=timezone.utc)
    timestamp = mtime
    notes = ""
    status = "fresh"

    if probe.kind == "json":
        obj, err = _load_json(path)
        if err is not None:
            status = "broken"
            notes = f"Invalid JSON: {err}"
        else:
            parsed = find_timestamp_in_obj(obj, list(probe.timestamp_keys))
            if parsed is not None:
                timestamp = parsed
            notes = "Timestamp from payload." if parsed else "No timestamp in payload; using mtime."

    elif probe.kind == "jsonl":
        obj, err = _load_last_jsonl(path)
        if err is not None:
            status = "broken"
            notes = f"Invalid JSONL: {err}"
        else:
            parsed = find_timestamp_in_obj(obj, list(probe.timestamp_keys))
            if parsed is not None:
                timestamp = parsed
            notes = "Timestamp from latest JSONL event." if parsed else "No timestamp in latest event; using mtime."

    elif probe.kind == "text":
        try:
            text = path.read_text(encoding="utf-8", errors="replace")
            if "ISSUES DETECTED" in text:
                status = "stale"
                notes = "Watchdog reports active issues."
            else:
                notes = "Watchdog status has no issue marker."
        except Exception as exc:
            status = "error"
            notes = f"Could not read text file: {exc}"

    age = calc_age_minutes(timestamp)
    if status == "fresh":
        status = _probe_status_from_age(age, probe.max_age_minutes)

    return {
        "id": probe.probe_id,
        "category": probe.category,
        "severity": probe.severity,
        "target": probe.target,
        "status": status,
        "hint": probe.hint,
        "last_timestamp_utc": iso_utc(timestamp),
        "age_minutes": age,
        "max_age_minutes": probe.max_age_minutes,
        "notes": notes,
    }


def _fetch_api_json(url: str, timeout_sec: int = 6) -> tuple[int | None, dict[str, Any] | list[Any] | None, str | None]:
    req = request.Request(url, headers={"User-Agent": "LumaStalenessFinder/1.0"})
    try:
        with request.urlopen(req, timeout=timeout_sec) as resp:
            status = int(resp.status)
            raw = resp.read().decode("utf-8", errors="replace")
            if not raw.strip():
                return status, None, "empty response body"
            try:
                payload = json.loads(raw)
                return status, payload, None
            except Exception as exc:
                return status, None, f"invalid json response: {exc}"
    except error.HTTPError as exc:
        return int(exc.code), None, f"http error: {exc}"
    except Exception as exc:
        return None, None, str(exc)


def _render_api_probe(probe: Probe, api_base: str) -> dict[str, Any]:
    url = api_base.rstrip("/") + probe.target
    http_status, payload, err = _fetch_api_json(url)

    if err is not None:
        return {
            "id": probe.probe_id,
            "category": probe.category,
            "severity": probe.severity,
            "target": url,
            "status": "error",
            "hint": probe.hint,
            "http_status": http_status,
            "notes": err,
        }

    if http_status is None or http_status >= 400:
        return {
            "id": probe.probe_id,
            "category": probe.category,
            "severity": probe.severity,
            "target": url,
            "status": "error",
            "hint": probe.hint,
            "http_status": http_status,
            "notes": "HTTP failure while probing endpoint.",
        }

    timestamp = find_timestamp_in_obj(payload, list(probe.timestamp_keys)) if payload is not None else None
    age = calc_age_minutes(timestamp)
    status = _probe_status_from_age(age, probe.max_age_minutes)
    notes = "API responded with JSON payload."
    if timestamp is None:
        notes = "API responded but no timestamp key found."

    return {
        "id": probe.probe_id,
        "category": probe.category,
        "severity": probe.severity,
        "target": url,
        "status": status,
        "hint": probe.hint,
        "http_status": http_status,
        "last_timestamp_utc": iso_utc(timestamp),
        "age_minutes": age,
        "max_age_minutes": probe.max_age_minutes,
        "notes": notes,
    }


def _build_chain_rows(results_by_id: dict[str, dict[str, Any]]) -> list[dict[str, Any]]:
    chain_rows: list[dict[str, Any]] = []

    for chain in CHAINS:
        statuses: list[str] = []
        missing_ids: list[str] = []
        for probe_id in chain["probes"]:
            item = results_by_id.get(probe_id)
            if item is None:
                missing_ids.append(probe_id)
                statuses.append("missing")
                continue
            statuses.append(str(item.get("status", "error")))

        worst = "fresh"
        for st in statuses:
            if STATUS_ORDER.get(st, 99) > STATUS_ORDER.get(worst, 99):
                worst = st

        chain_rows.append(
            {
                "chain_id": chain["chain_id"],
                "title": chain["title"],
                "status": worst,
                "probe_count": len(chain["probes"]),
                "missing_probes": missing_ids,
                "probes": chain["probes"],
            }
        )

    return chain_rows


def _calc_score(results: list[dict[str, Any]]) -> int:
    penalty = 0
    for row in results:
        status = str(row.get("status", "error"))
        if status not in BAD_STATUSES:
            continue

        severity = str(row.get("severity", "warn"))
        if severity == "critical":
            penalty += 25
        elif severity == "warn":
            penalty += 10
        else:
            penalty += 4

    return max(0, 100 - penalty)


def _overall_status(results: list[dict[str, Any]]) -> str:
    critical_bad = any(
        str(r.get("severity", "warn")) == "critical" and str(r.get("status", "error")) in BAD_STATUSES
        for r in results
    )
    if critical_bad:
        return "critical"

    warn_bad = any(str(r.get("status", "error")) in BAD_STATUSES for r in results)
    if warn_bad:
        return "warn"

    return "ok"


def _recommendations(results: list[dict[str, Any]]) -> list[str]:
    bad = [r for r in results if str(r.get("status", "error")) in BAD_STATUSES]
    bad.sort(
        key=lambda r: (
            -SEVERITY_ORDER.get(str(r.get("severity", "warn")), 0),
            float(r.get("age_minutes") or -1),
        )
    )

    recs: list[str] = []
    for row in bad[:10]:
        recs.append(f"{row.get('id')}: {row.get('hint') or row.get('notes')}")
    return recs


def build_report(api_base: str) -> dict[str, Any]:
    results: list[dict[str, Any]] = []

    for probe in FILE_PROBES:
        results.append(_render_file_probe(probe))

    for probe in HTML_PROBES:
        results.append(_render_html_probe(probe))

    for probe in API_PROBES:
        results.append(_render_api_probe(probe, api_base))

    results.sort(
        key=lambda r: (
            -SEVERITY_ORDER.get(str(r.get("severity", "warn")), 0),
            STATUS_ORDER.get(str(r.get("status", "error")), 99),
            str(r.get("id", "")),
        )
    )

    by_id = {str(item.get("id")): item for item in results}
    chains = _build_chain_rows(by_id)

    counts = {
        "total": len(results),
        "fresh": sum(1 for r in results if str(r.get("status")) in {"fresh", "ok"}),
        "stale": sum(1 for r in results if str(r.get("status")) == "stale"),
        "missing": sum(1 for r in results if str(r.get("status")) == "missing"),
        "error": sum(1 for r in results if str(r.get("status")) == "error"),
        "broken": sum(1 for r in results if str(r.get("status")) == "broken"),
    }

    blockers = [
        {
            "id": r.get("id"),
            "severity": r.get("severity"),
            "status": r.get("status"),
            "target": r.get("target"),
            "notes": r.get("notes"),
        }
        for r in results
        if str(r.get("severity")) == "critical" and str(r.get("status")) in BAD_STATUSES
    ]

    report = {
        "generated_utc": iso_utc(now_utc()),
        "api_base": api_base,
        "overall_status": _overall_status(results),
        "score_0_100": _calc_score(results),
        "summary": counts,
        "blockers": blockers,
        "chains": chains,
        "recommendations": _recommendations(results),
        "probes": results,
    }

    return report


def to_markdown(report: dict[str, Any]) -> str:
    lines: list[str] = []
    lines.append("# End-to-End Staleness Report")
    lines.append("")
    lines.append(f"Generated UTC: {report.get('generated_utc', '')}")
    lines.append(f"Overall: {report.get('overall_status', 'unknown').upper()} | Score: {report.get('score_0_100', 0)}")
    lines.append("")

    summary = report.get("summary", {})
    lines.append("## Summary")
    lines.append(f"- Total probes: {summary.get('total', 0)}")
    lines.append(f"- Fresh: {summary.get('fresh', 0)}")
    lines.append(f"- Stale: {summary.get('stale', 0)}")
    lines.append(f"- Missing: {summary.get('missing', 0)}")
    lines.append(f"- Error: {summary.get('error', 0)}")
    lines.append(f"- Broken: {summary.get('broken', 0)}")
    lines.append("")

    lines.append("## Chains")
    for chain in report.get("chains", []):
        lines.append(f"- {chain.get('title', chain.get('chain_id'))}: {str(chain.get('status', 'unknown')).upper()}")
    lines.append("")

    lines.append("## Blockers")
    blockers = report.get("blockers", [])
    if not blockers:
        lines.append("- None")
    else:
        for row in blockers:
            lines.append(f"- {row.get('id')}: {row.get('status')} :: {row.get('notes')}")
    lines.append("")

    lines.append("## Recommendations")
    recs = report.get("recommendations", [])
    if not recs:
        lines.append("- None")
    else:
        for rec in recs:
            lines.append(f"- {rec}")
    lines.append("")

    lines.append("## Probe Details")
    for row in report.get("probes", []):
        lines.append(
            "- {id} [{severity}] {status} | age={age}m | max={max_age}m | {target} | {notes}".format(
                id=row.get("id", "?"),
                severity=row.get("severity", "?"),
                status=row.get("status", "?"),
                age=row.get("age_minutes", "n/a"),
                max_age=row.get("max_age_minutes", "n/a"),
                target=row.get("target", "?"),
                notes=row.get("notes", ""),
            )
        )

    lines.append("")
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description="End-to-end staleness and drift finder for LumaTrader stack.")
    parser.add_argument(
        "--api-base",
        default=os.getenv("LUMA_STALENESS_API_BASE", "http://127.0.0.1:8787"),
        help="Gateway base URL for API probes.",
    )
    parser.add_argument(
        "--print-json",
        action="store_true",
        help="Print generated JSON report to stdout.",
    )
    parser.add_argument(
        "--fail-on-blockers",
        action="store_true",
        help="Return exit code 2 when critical blockers are present.",
    )
    args = parser.parse_args()

    report = build_report(args.api_base)

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    REPORT_JSON.write_text(json.dumps(report, indent=2), encoding="utf-8")
    REPORT_MD.write_text(to_markdown(report), encoding="utf-8")

    if args.print_json:
        print(json.dumps(report, indent=2))

    if args.fail_on_blockers and report.get("blockers"):
        return 2

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
