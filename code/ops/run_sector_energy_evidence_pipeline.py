from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(r"C:\LumaTrader\INSTITUTIONAL_STACK_V2")
WORKSPACE_ROOT = ROOT.parent
OUT = ROOT / "out"
OPS = OUT / "ops"
WORKSPACE_OPS = WORKSPACE_ROOT / "out" / "ops"
SECTOR = OUT / "sector_energy"

INVESTOR_SWEEP_SCRIPT = ROOT / "code" / "ops" / "investor_proof_sweep.py"
BUILD_SCRIPT = ROOT / "code" / "ops" / "build_measured_sector_fact_table.py"
AUDIT_SCRIPT = ROOT / "code" / "ops" / "verify_sector_lane_boundary.py"

MEASURED_SUMMARY_JSON = SECTOR / "measured_sector_summary.json"
LANE_AUDIT_LATEST_JSON = OPS / "sector_lane_boundary_audit_latest.json"
SECTOR_INVESTOR_BRIDGE_LATEST_JSON = SECTOR / "sector_energy_investor_bridge_latest.json"
SECTOR_INVESTOR_BRIDGE_LATEST_MD = SECTOR / "sector_energy_investor_bridge_latest.md"


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def utc_stamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def write_json(path: Path, obj: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, indent=2), encoding="utf-8")


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def load_json(path: Path) -> dict | None:
    if not path.exists():
        return None
    encodings = ("utf-8", "utf-8-sig")
    for enc in encodings:
        try:
            return json.loads(path.read_text(encoding=enc))
        except Exception:
            continue
    return None


def run_step(name: str, cmd: list[str], timeout_sec: int, cwd: Path | None = None) -> dict:
    started = utc_now()
    t0 = time.monotonic()
    result = {
        "name": name,
        "cmd": cmd,
        "cwd": str(cwd) if cwd else None,
        "started_utc": started,
        "ended_utc": None,
        "duration_sec": 0.0,
        "ran": False,
        "ok": False,
        "timed_out": False,
        "returncode": None,
        "stdout_tail": "",
        "stderr_tail": "",
    }

    try:
        proc = subprocess.run(
            cmd,
            cwd=str(cwd) if cwd else None,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=max(1, int(timeout_sec)),
        )
        result["ran"] = True
        result["ok"] = proc.returncode == 0
        result["returncode"] = int(proc.returncode)
        result["stdout_tail"] = (proc.stdout or "")[-2500:]
        result["stderr_tail"] = (proc.stderr or "")[-2500:]
    except subprocess.TimeoutExpired as exc:
        result["ran"] = True
        result["timed_out"] = True
        result["ok"] = False
        result["stderr_tail"] = f"timeout after {timeout_sec}s: {exc}"
        result["stdout_tail"] = ((exc.stdout or "") if isinstance(exc.stdout, str) else "")[-2500:]
    except Exception as exc:
        result["ran"] = False
        result["ok"] = False
        result["stderr_tail"] = repr(exc)

    result["ended_utc"] = utc_now()
    result["duration_sec"] = round(time.monotonic() - t0, 3)
    return result


def find_latest_investor_summary() -> Path | None:
    search_roots = [WORKSPACE_OPS, OPS]
    candidates: list[Path] = []
    for base in search_roots:
        if not base.exists():
            continue
        candidates.extend(base.glob("investor_proof_sweep_*"))
    candidates = sorted(candidates, key=lambda p: p.stat().st_mtime, reverse=True)
    for run_dir in candidates:
        summary_path = run_dir / "proof_summary.json"
        if summary_path.exists():
            return summary_path
    return None


def extract_investor_summary_from_step(step: dict | None) -> Path | None:
    if not isinstance(step, dict):
        return None
    text = "\n".join([str(step.get("stdout_tail", "")), str(step.get("stderr_tail", ""))])
    matches = re.findall(r"\[SWEEP\]\s+output:\s*(.+)", text)
    if not matches:
        return None
    out_dir = Path(matches[-1].strip())
    summary = out_dir / "proof_summary.json"
    if summary.exists():
        return summary
    return None


def build_investor_cmd(args: argparse.Namespace, python_exe: str) -> list[str]:
    cmd = [
        python_exe,
        str(INVESTOR_SWEEP_SCRIPT),
        "--root",
        str(WORKSPACE_ROOT),
        "--stack-root",
        str(ROOT),
        "--min-rows",
        str(args.investor_min_rows),
        "--min-span-years",
        str(args.investor_min_span_years),
    ]
    if args.investor_max_files > 0:
        cmd.extend(["--max-files", str(args.investor_max_files)])
    if args.investor_max_series > 0:
        cmd.extend(["--max-series", str(args.investor_max_series)])
    if args.push_nodered:
        cmd.extend(["--push-nodered", "--nodered-base", args.nodered_base])
    return cmd


def write_chain_of_custody(path: Path, artifacts: list[Path], generated_utc: str, run_dir: Path) -> None:
    lines = [
        f"generated_utc={generated_utc}",
        f"run_dir={run_dir}",
    ]
    for artifact in artifacts:
        if artifact.exists():
            lines.append(f"artifact={artifact}")
            lines.append(f"sha256={sha256_file(artifact)}")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description="Run sector-energy evidence pipeline with optional investor sweep.")
    parser.add_argument("--python-exe", default=sys.executable)
    parser.add_argument("--run-investor-sweep", action="store_true")
    parser.add_argument("--push-nodered", action="store_true")
    parser.add_argument("--nodered-base", default="http://127.0.0.1:8787")
    parser.add_argument("--investor-max-files", type=int, default=0)
    parser.add_argument("--investor-max-series", type=int, default=0)
    parser.add_argument("--investor-min-rows", type=int, default=252)
    parser.add_argument("--investor-min-span-years", type=float, default=1.0)
    parser.add_argument("--step-timeout-sec", type=int, default=5400)
    args = parser.parse_args()

    generated_utc = utc_now()
    run_tag = utc_stamp()

    run_dir = OPS / f"sector_energy_evidence_pipeline_{run_tag}"
    run_dir.mkdir(parents=True, exist_ok=True)

    run_summary_json = run_dir / "sector_energy_evidence_pipeline_summary.json"
    run_summary_md = run_dir / "sector_energy_evidence_pipeline_summary.md"
    run_hash_manifest_json = run_dir / "artifact_hash_manifest.json"
    run_chain_of_custody_txt = run_dir / "sector_energy_evidence_chain_of_custody.sha256.txt"

    latest_json = OPS / "sector_energy_evidence_pipeline_latest.json"
    latest_md = OPS / "sector_energy_evidence_pipeline_latest.md"

    steps = []

    if args.run_investor_sweep:
        investor_cmd = build_investor_cmd(args, args.python_exe)
        steps.append(
            run_step(
                name="investor_proof_sweep",
                cmd=investor_cmd,
                timeout_sec=args.step_timeout_sec,
                cwd=ROOT,
            )
        )

    build_cmd = [args.python_exe, str(BUILD_SCRIPT)]
    build_result = run_step(
        name="build_measured_sector_fact_table",
        cmd=build_cmd,
        timeout_sec=args.step_timeout_sec,
        cwd=ROOT,
    )
    steps.append(build_result)

    audit_result = {
        "name": "verify_sector_lane_boundary",
        "cmd": [args.python_exe, str(AUDIT_SCRIPT)],
        "cwd": str(ROOT),
        "started_utc": utc_now(),
        "ended_utc": utc_now(),
        "duration_sec": 0.0,
        "ran": False,
        "ok": False,
        "timed_out": False,
        "returncode": None,
        "stdout_tail": "",
        "stderr_tail": "skipped: build_measured_sector_fact_table failed",
    }
    if build_result["ok"]:
        audit_result = run_step(
            name="verify_sector_lane_boundary",
            cmd=[args.python_exe, str(AUDIT_SCRIPT)],
            timeout_sec=args.step_timeout_sec,
            cwd=ROOT,
        )
    steps.append(audit_result)

    measured_summary = load_json(MEASURED_SUMMARY_JSON)
    lane_audit_summary = load_json(LANE_AUDIT_LATEST_JSON)
    investor_step = next((x for x in steps if x.get("name") == "investor_proof_sweep"), None)

    lane_status = None
    lane_ok = False
    if isinstance(lane_audit_summary, dict):
        lane_status = str(lane_audit_summary.get("status", "")).upper()
        lane_ok = lane_status == "PASS"

    latest_investor_summary_path = extract_investor_summary_from_step(investor_step)
    if latest_investor_summary_path is None:
        latest_investor_summary_path = find_latest_investor_summary()
    investor_summary = load_json(latest_investor_summary_path) if latest_investor_summary_path else None

    investor_ok = bool(investor_step and investor_step.get("ok")) if args.run_investor_sweep else True

    checks = {
        "build_ok": bool(build_result.get("ok")),
        "audit_ok": bool(audit_result.get("ok")),
        "lane_boundary_status": lane_status,
        "lane_boundary_ok": lane_ok,
        "run_investor_sweep": bool(args.run_investor_sweep),
        "investor_sweep_ok": investor_ok,
        "investor_summary_found": bool(investor_summary),
        "investor_backtested_series": (
            investor_summary.get("coverage", {}).get("backtested_series")
            if isinstance(investor_summary, dict)
            else None
        ),
        "fact_rows": measured_summary.get("fact_rows") if isinstance(measured_summary, dict) else None,
        "constraint_rows": measured_summary.get("constraint_rows") if isinstance(measured_summary, dict) else None,
        "coherence_rows": measured_summary.get("coherence_rows") if isinstance(measured_summary, dict) else None,
        "datasets_seen": measured_summary.get("datasets_seen") if isinstance(measured_summary, dict) else [],
    }

    status = "PASS"
    if not (checks["build_ok"] and checks["audit_ok"] and checks["lane_boundary_ok"]):
        status = "FAIL"
    if args.run_investor_sweep and not (checks["investor_sweep_ok"] and checks["investor_summary_found"]):
        status = "FAIL"

    summary = {
        "generated_utc": generated_utc,
        "run_tag": run_tag,
        "scope": "sector_energy_evidence_pipeline",
        "status": status,
        "parameters": {
            "python_exe": args.python_exe,
            "run_investor_sweep": bool(args.run_investor_sweep),
            "push_nodered": bool(args.push_nodered),
            "nodered_base": args.nodered_base,
            "investor_max_files": int(args.investor_max_files),
            "investor_max_series": int(args.investor_max_series),
            "investor_min_rows": int(args.investor_min_rows),
            "investor_min_span_years": float(args.investor_min_span_years),
            "step_timeout_sec": int(args.step_timeout_sec),
        },
        "steps": steps,
        "checks": checks,
        "artifacts": {
            "run_summary_json": str(run_summary_json),
            "run_summary_md": str(run_summary_md),
            "run_hash_manifest_json": str(run_hash_manifest_json),
            "run_chain_of_custody_sha256_txt": str(run_chain_of_custody_txt),
            "latest_summary_json": str(latest_json),
            "latest_summary_md": str(latest_md),
            "measured_sector_summary_json": str(MEASURED_SUMMARY_JSON),
            "lane_boundary_audit_latest_json": str(LANE_AUDIT_LATEST_JSON),
            "investor_summary_json": str(latest_investor_summary_path) if latest_investor_summary_path else None,
            "sector_investor_bridge_latest_json": str(SECTOR_INVESTOR_BRIDGE_LATEST_JSON),
            "sector_investor_bridge_latest_md": str(SECTOR_INVESTOR_BRIDGE_LATEST_MD),
        },
    }

    write_json(run_summary_json, summary)
    write_json(latest_json, summary)

    bridge = {
        "generated_utc": generated_utc,
        "run_tag": run_tag,
        "status": status,
        "lane_boundary_status": lane_status,
        "fact_rows": checks["fact_rows"],
        "constraint_rows": checks["constraint_rows"],
        "coherence_rows": checks["coherence_rows"],
        "datasets_seen": checks["datasets_seen"],
        "investor_backtested_series": checks["investor_backtested_series"],
        "source_refs": {
            "measured_sector_summary_json": str(MEASURED_SUMMARY_JSON),
            "lane_boundary_audit_latest_json": str(LANE_AUDIT_LATEST_JSON),
            "investor_summary_json": str(latest_investor_summary_path) if latest_investor_summary_path else None,
            "pipeline_latest_json": str(latest_json),
        },
    }
    write_json(SECTOR_INVESTOR_BRIDGE_LATEST_JSON, bridge)

    md_lines = [
        "# Sector Energy Evidence Pipeline",
        "",
        f"Generated UTC: {generated_utc}",
        f"Run Tag: {run_tag}",
        f"Status: {status}",
        "",
        "## Checks",
        f"- Build step ok: {checks['build_ok']}",
        f"- Audit step ok: {checks['audit_ok']}",
        f"- Lane boundary status: {checks['lane_boundary_status']}",
        f"- Lane boundary pass: {checks['lane_boundary_ok']}",
        f"- Investor sweep requested: {checks['run_investor_sweep']}",
        f"- Investor sweep ok: {checks['investor_sweep_ok']}",
        f"- Investor summary found: {checks['investor_summary_found']}",
        f"- Investor backtested series: {checks['investor_backtested_series']}",
        f"- Fact rows: {checks['fact_rows']}",
        f"- Constraint rows: {checks['constraint_rows']}",
        f"- Coherence rows: {checks['coherence_rows']}",
        f"- Datasets seen: {len(checks['datasets_seen'])}",
        "",
        "## Steps",
    ]
    for step in steps:
        md_lines.append(
            f"- {step['name']}: ok={step['ok']} returncode={step['returncode']} duration_sec={step['duration_sec']} timed_out={step['timed_out']}"
        )

    md_lines.extend(["", "## Artifacts"])
    for key, value in summary["artifacts"].items():
        if value:
            md_lines.append(f"- {key}: {value}")

    text = "\n".join(md_lines) + "\n"
    run_summary_md.write_text(text, encoding="utf-8")
    latest_md.write_text(text, encoding="utf-8")
    SECTOR_INVESTOR_BRIDGE_LATEST_MD.write_text(
        "\n".join(
            [
                "# Sector + Investor Bridge",
                "",
                f"Generated UTC: {generated_utc}",
                f"Run Tag: {run_tag}",
                f"Status: {status}",
                f"Lane boundary: {lane_status}",
                f"Fact rows: {checks['fact_rows']}",
                f"Constraint rows: {checks['constraint_rows']}",
                f"Coherence rows: {checks['coherence_rows']}",
                f"Investor backtested series: {checks['investor_backtested_series']}",
                f"Pipeline latest: {latest_json}",
            ]
        )
        + "\n",
        encoding="utf-8",
    )

    hash_rows = []
    artifact_paths = [
        run_summary_json,
        run_summary_md,
        latest_json,
        latest_md,
        SECTOR_INVESTOR_BRIDGE_LATEST_JSON,
        SECTOR_INVESTOR_BRIDGE_LATEST_MD,
    ]
    if latest_investor_summary_path and latest_investor_summary_path.exists():
        artifact_paths.append(latest_investor_summary_path)
    for path in artifact_paths:
        if path.exists():
            hash_rows.append(
                {
                    "path": str(path),
                    "bytes": int(path.stat().st_size),
                    "sha256": sha256_file(path),
                }
            )

    hash_manifest = {
        "generated_utc": generated_utc,
        "run_tag": run_tag,
        "artifact_count": len(hash_rows),
        "artifacts": hash_rows,
    }
    write_json(run_hash_manifest_json, hash_manifest)
    write_chain_of_custody(
        path=run_chain_of_custody_txt,
        artifacts=artifact_paths + [run_hash_manifest_json],
        generated_utc=generated_utc,
        run_dir=run_dir,
    )

    print(str(run_summary_json))
    print(str(latest_json))
    print(str(SECTOR_INVESTOR_BRIDGE_LATEST_JSON))
    print(status)

    return 0 if status == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
