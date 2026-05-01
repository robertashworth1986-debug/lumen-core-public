from __future__ import annotations

import ast
import json
import socket
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Tuple
from urllib import error, request

ROOT = Path(r"C:\LumaTrader\INSTITUTIONAL_STACK_V2")
CODE_ROOT = ROOT / "code"
LAMASCOUT_ROOT = ROOT / "LamaScout"
OUT_EXEC = ROOT / "out" / "execution"

REPORT_JSON = OUT_EXEC / "universe_audit_report.json"
REPORT_MD = OUT_EXEC / "universe_audit_report.md"

HEARTBEAT_FILES: Dict[str, Path] = {
    "multi_exchange_paper_ticker_status": OUT_EXEC / "multi_exchange_paper_ticker_status.json",
    "institutional_crypto_dashboard_heartbeat": OUT_EXEC / "institutional_crypto_dashboard_heartbeat.json",
    "alpaca_paper_status": OUT_EXEC / "alpaca_paper_status.json",
    "live_engine_heartbeat": OUT_EXEC / "live_engine_heartbeat.json",
    "investor_wallboard_heartbeat": OUT_EXEC / "investor_wallboard_heartbeat.json",
}

ENDPOINTS = [
    "http://127.0.0.1:7700/api/tick",
    "http://127.0.0.1:7700/api/live_readiness",
    "http://127.0.0.1:7700/api/source_breadth",
    "http://127.0.0.1:5016/",
]

ORCHESTRATOR = CODE_ROOT / "execution" / "execution_orchestrator.py"
MODULES_TO_TRIAGE = [
    "shadow_runner",
    "trade_ledger",
    "liquidity_guard",
    "kill_switch",
    "order_router",
    "risk_kernel",
    "live_runtime_guard",
    "audit_chain",
    "payout_bridge",
    "sizing_engine",
    "signal_gate",
]


@dataclass
class Finding:
    severity: str
    area: str
    message: str
    path: str = ""

    def as_dict(self) -> Dict[str, str]:
        return {
            "severity": self.severity,
            "area": self.area,
            "message": self.message,
            "path": self.path,
        }


def now_utc() -> str:
    return datetime.now(timezone.utc).isoformat()


def _is_project_python(path: Path) -> bool:
    return path.suffix.lower() == ".py" and not any(
        part in {".venv", "venv", "site-packages", "__pycache__"} for part in path.parts
    )


def _scan_syntax(roots: List[Path]) -> List[Dict[str, Any]]:
    out: List[Dict[str, Any]] = []
    for root in roots:
        for file_path in root.rglob("*.py"):
            if not _is_project_python(file_path):
                continue
            text = file_path.read_text(encoding="utf-8", errors="ignore")
            try:
                ast.parse(text)
            except SyntaxError as exc:
                out.append(
                    {
                        "path": str(file_path),
                        "line": int(exc.lineno or 0),
                        "message": str(exc.msg),
                    }
                )
    return out


def _check_port(port: int) -> bool:
    sock = socket.socket()
    sock.settimeout(1.5)
    try:
        sock.connect(("127.0.0.1", port))
        return True
    except Exception:
        return False
    finally:
        sock.close()


def _check_endpoints() -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []
    for url in ENDPOINTS:
        row: Dict[str, Any] = {"url": url, "ok": False, "status": None, "error": ""}
        try:
            with request.urlopen(url, timeout=4) as resp:
                row["ok"] = True
                row["status"] = int(resp.status)
        except error.HTTPError as exc:
            row["status"] = int(exc.code)
            row["error"] = str(exc)
        except Exception as exc:
            row["error"] = str(exc)
        rows.append(row)
    return rows


def _heartbeat_status() -> Dict[str, Dict[str, Any]]:
    out: Dict[str, Dict[str, Any]] = {}
    now = datetime.now(timezone.utc)
    for name, file_path in HEARTBEAT_FILES.items():
        row: Dict[str, Any] = {"path": str(file_path), "exists": file_path.exists()}
        if file_path.exists():
            age_sec = (now - datetime.fromtimestamp(file_path.stat().st_mtime, timezone.utc)).total_seconds()
            row["age_sec"] = round(age_sec, 1)
            row["fresh_120s"] = age_sec <= 120.0
            row["fresh_600s"] = age_sec <= 600.0
        out[name] = row
    return out


def _load_runtime() -> Dict[str, Any]:
    runtime_path = ROOT / "config" / "runtime_control.json"
    if not runtime_path.exists():
        return {}
    try:
        return json.loads(runtime_path.read_text(encoding="utf-8"))
    except Exception:
        return {}


def _module_triage() -> List[Dict[str, Any]]:
    text = ORCHESTRATOR.read_text(encoding="utf-8", errors="ignore") if ORCHESTRATOR.exists() else ""
    rows: List[Dict[str, Any]] = []
    for mod in MODULES_TO_TRIAGE:
        rows.append(
            {
                "module": mod,
                "referenced_in_orchestrator": (mod in text),
                "path": str(CODE_ROOT / "execution" / f"{mod}.py"),
                "exists": (CODE_ROOT / "execution" / f"{mod}.py").exists(),
            }
        )
    return rows


def _orchestrator_drift_signals() -> Dict[str, Any]:
    result = {
        "exists": ORCHESTRATOR.exists(),
        "top_level_print_count": 0,
        "sys_path_hack_count": 0,
        "sleep_calls": 0,
    }
    if not ORCHESTRATOR.exists():
        return result

    text = ORCHESTRATOR.read_text(encoding="utf-8", errors="ignore")
    result["top_level_print_count"] = text.count("print(")
    result["sys_path_hack_count"] = text.count("sys.path.insert") + text.count("sys.path.append")
    result["sleep_calls"] = text.count("time.sleep(")
    return result


def _build_findings(
    syntax_errors: List[Dict[str, Any]],
    endpoints: List[Dict[str, Any]],
    heartbeats: Dict[str, Dict[str, Any]],
    runtime_cfg: Dict[str, Any],
    drift: Dict[str, Any],
) -> List[Finding]:
    findings: List[Finding] = []

    for err in syntax_errors:
        sev = "high" if "\\execution\\" in err["path"].lower() else "medium"
        findings.append(
            Finding(
                severity=sev,
                area="syntax",
                message=f"Syntax error on line {err['line']}: {err['message']}",
                path=err["path"],
            )
        )

    for ep in endpoints:
        if not ep.get("ok"):
            findings.append(
                Finding(
                    severity="high",
                    area="api",
                    message=f"Endpoint unhealthy: {ep['url']} status={ep.get('status')} error={ep.get('error')}",
                    path=ep["url"],
                )
            )

    stale_critical = [
        "multi_exchange_paper_ticker_status",
        "institutional_crypto_dashboard_heartbeat",
    ]
    stale_secondary = [
        "alpaca_paper_status",
        "live_engine_heartbeat",
        "investor_wallboard_heartbeat",
    ]

    for key in stale_critical:
        row = heartbeats.get(key, {})
        if not row.get("exists") or not row.get("fresh_120s"):
            findings.append(
                Finding(
                    severity="high",
                    area="heartbeat",
                    message=f"Critical heartbeat stale/missing: {key}",
                    path=row.get("path", ""),
                )
            )

    for key in stale_secondary:
        row = heartbeats.get(key, {})
        if row.get("exists") and not row.get("fresh_600s"):
            findings.append(
                Finding(
                    severity="medium",
                    area="heartbeat",
                    message=f"Secondary heartbeat stale: {key}",
                    path=row.get("path", ""),
                )
            )

    if runtime_cfg:
        mode = str(runtime_cfg.get("mode", "")).lower()
        allow_live = bool(runtime_cfg.get("allow_live_orders", False))
        if mode != "paper" and allow_live:
            findings.append(
                Finding(
                    severity="medium",
                    area="runtime",
                    message="Runtime is armed for live orders; confirm this is intentional.",
                    path=str(ROOT / "config" / "runtime_control.json"),
                )
            )

    if drift.get("sys_path_hack_count", 0) > 0 or drift.get("sleep_calls", 0) > 0:
        findings.append(
            Finding(
                severity="medium",
                area="drift",
                message=(
                    "Orchestrator contains import-time side-effect signals "
                    f"(sys.path hacks={drift.get('sys_path_hack_count', 0)}, "
                    f"sleep calls={drift.get('sleep_calls', 0)})."
                ),
                path=str(ORCHESTRATOR),
            )
        )

    return findings


def _render_markdown(report: Dict[str, Any]) -> str:
    lines: List[str] = []
    lines.append("# Universe Audit Report")
    lines.append("")
    lines.append(f"Generated UTC: {report['generated_utc']}")
    lines.append("")
    lines.append("## Summary")
    lines.append(f"- Python files scanned: {report['summary']['python_files_scanned']}")
    lines.append(f"- Syntax errors: {report['summary']['syntax_error_count']}")
    lines.append(f"- Findings total: {report['summary']['findings_total']}")
    lines.append("")

    lines.append("## Findings")
    if not report["findings"]:
        lines.append("- No blocking findings detected.")
    else:
        for f in report["findings"]:
            lines.append(
                f"- [{f['severity'].upper()}] {f['area']}: {f['message']} ({f.get('path','')})"
            )
    lines.append("")

    lines.append("## Endpoint Health")
    for ep in report["runtime"]["endpoints"]:
        lines.append(
            f"- {ep['url']}: ok={ep['ok']} status={ep.get('status')} error={ep.get('error','')}"
        )
    lines.append("")

    lines.append("## Heartbeats")
    for name, hb in report["runtime"]["heartbeats"].items():
        lines.append(
            f"- {name}: exists={hb.get('exists')} age_sec={hb.get('age_sec')} fresh_120s={hb.get('fresh_120s')} fresh_600s={hb.get('fresh_600s')}"
        )
    lines.append("")

    lines.append("## Module Triage")
    for row in report["integration"]["module_triage"]:
        lines.append(
            f"- {row['module']}: exists={row['exists']} referenced_in_orchestrator={row['referenced_in_orchestrator']}"
        )
    lines.append("")

    lines.append("## Drift Signals")
    drift = report["integration"]["orchestrator_drift_signals"]
    lines.append(
        f"- orchestrator_exists={drift.get('exists')} top_level_print_count={drift.get('top_level_print_count')} sys_path_hack_count={drift.get('sys_path_hack_count')} sleep_calls={drift.get('sleep_calls')}"
    )
    lines.append("")

    return "\n".join(lines)


def run_audit() -> Dict[str, Any]:
    OUT_EXEC.mkdir(parents=True, exist_ok=True)

    python_files_scanned = 0
    for root in [CODE_ROOT, LAMASCOUT_ROOT]:
        for p in root.rglob("*.py"):
            if _is_project_python(p):
                python_files_scanned += 1

    syntax_errors = _scan_syntax([CODE_ROOT, LAMASCOUT_ROOT])
    endpoints = _check_endpoints()
    heartbeats = _heartbeat_status()
    runtime_cfg = _load_runtime()
    module_triage = _module_triage()
    drift = _orchestrator_drift_signals()

    findings = _build_findings(syntax_errors, endpoints, heartbeats, runtime_cfg, drift)
    findings_sorted = sorted(findings, key=lambda x: {"high": 0, "medium": 1, "low": 2}.get(x.severity, 9))

    report: Dict[str, Any] = {
        "generated_utc": now_utc(),
        "summary": {
            "python_files_scanned": python_files_scanned,
            "syntax_error_count": len(syntax_errors),
            "findings_total": len(findings_sorted),
        },
        "syntax_errors": syntax_errors,
        "runtime": {
            "ports": {
                "7700": _check_port(7700),
                "5016": _check_port(5016),
            },
            "endpoints": endpoints,
            "heartbeats": heartbeats,
            "runtime_control": {
                "mode": runtime_cfg.get("mode"),
                "allow_live_orders": runtime_cfg.get("allow_live_orders"),
                "kill_switch": runtime_cfg.get("kill_switch"),
            },
        },
        "integration": {
            "module_triage": module_triage,
            "orchestrator_drift_signals": drift,
        },
        "findings": [f.as_dict() for f in findings_sorted],
    }

    REPORT_JSON.write_text(json.dumps(report, indent=2), encoding="utf-8")
    REPORT_MD.write_text(_render_markdown(report), encoding="utf-8")
    return report


def main() -> int:
    report = run_audit()
    print("Universe audit complete")
    print(f"Findings: {report['summary']['findings_total']}")
    print(f"Syntax errors: {report['summary']['syntax_error_count']}")
    print(f"JSON: {REPORT_JSON}")
    print(f"MD: {REPORT_MD}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
