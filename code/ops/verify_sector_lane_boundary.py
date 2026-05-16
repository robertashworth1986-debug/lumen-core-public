from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(r"C:\LumaTrader\INSTITUTIONAL_STACK_V2")
OUT = ROOT / "out"
OPS = OUT / "ops"

TRADER_MANIFEST = OUT / "execution" / "trader_alpha_lane" / "lane_boundary_manifest.json"
SECTOR_MANIFEST = OUT / "sector_energy" / "sector_lane_manifest.json"


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def utc_stamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def norm(path_text: str) -> str:
    return str(Path(path_text).resolve()).replace("\\", "/").lower()


def as_norm_set(items) -> set[str]:
    out = set()
    for item in items or []:
        try:
            out.add(norm(str(item)))
        except Exception:
            continue
    return out


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def main() -> None:
    generated_utc = utc_now()
    run_tag = utc_stamp()
    run_dir = OPS / f"sector_lane_boundary_audit_{run_tag}"
    run_dir.mkdir(parents=True, exist_ok=True)

    report = {
        "generated_utc": generated_utc,
        "run_tag": run_tag,
        "trader_manifest_path": str(TRADER_MANIFEST),
        "sector_manifest_path": str(SECTOR_MANIFEST),
        "status": "FAIL",
        "checks": {},
        "violations": [],
    }

    if not TRADER_MANIFEST.exists():
        report["violations"].append("missing trader lane manifest")
    if not SECTOR_MANIFEST.exists():
        report["violations"].append("missing sector lane manifest")

    trader = {}
    sector = {}
    if TRADER_MANIFEST.exists():
        trader = load_json(TRADER_MANIFEST)
    if SECTOR_MANIFEST.exists():
        sector = load_json(SECTOR_MANIFEST)

    if trader and sector:
        trader_writes = as_norm_set(trader.get("writes", []))
        trader_protected_sector = as_norm_set(trader.get("protected_sector_proof_paths", []))

        sector_writes = as_norm_set(sector.get("writes", []))
        sector_guarded_trader = as_norm_set(sector.get("guarded_trader_paths", []))
        sector_guarded_frozen = as_norm_set(sector.get("guarded_frozen_paths", []))

        trader_self_violation = sorted(trader_writes.intersection(trader_protected_sector))

        sector_vs_trader = []
        for w in sorted(sector_writes):
            for t in sorted(sector_guarded_trader):
                if w == t or w.startswith(t + "/"):
                    sector_vs_trader.append({"write": w, "guard": t})

        sector_vs_frozen = []
        for w in sorted(sector_writes):
            for f in sorted(sector_guarded_frozen):
                if w == f:
                    sector_vs_frozen.append({"write": w, "guard": f})

        report["checks"] = {
            "trader_write_intersection_count": len(trader_self_violation),
            "sector_write_vs_trader_count": len(sector_vs_trader),
            "sector_write_vs_frozen_count": len(sector_vs_frozen),
            "trader_write_count": len(trader_writes),
            "sector_write_count": len(sector_writes),
        }

        if trader_self_violation:
            report["violations"].append("trader writes intersect protected sector proof paths")
            report["violations"].extend(trader_self_violation)
        if sector_vs_trader:
            report["violations"].append("sector writes intersect trader-protected paths")
            report["violations"].extend([f"{x['write']} -> {x['guard']}" for x in sector_vs_trader])
        if sector_vs_frozen:
            report["violations"].append("sector writes intersect frozen-protected paths")
            report["violations"].extend([f"{x['write']} -> {x['guard']}" for x in sector_vs_frozen])

    report["status"] = "PASS" if not report["violations"] else "FAIL"

    run_json = run_dir / "sector_lane_boundary_audit.json"
    latest_json = OPS / "sector_lane_boundary_audit_latest.json"
    run_md = run_dir / "sector_lane_boundary_audit.md"
    latest_md = OPS / "sector_lane_boundary_audit_latest.md"

    run_json.write_text(json.dumps(report, indent=2), encoding="utf-8")
    latest_json.write_text(json.dumps(report, indent=2), encoding="utf-8")

    lines = [
        "# Sector Lane Boundary Audit",
        "",
        f"Generated UTC: {generated_utc}",
        f"Status: {report['status']}",
        "",
        "## Checks",
        f"- Trader writes checked: {report['checks'].get('trader_write_count', 0)}",
        f"- Sector writes checked: {report['checks'].get('sector_write_count', 0)}",
        f"- Trader self intersections: {report['checks'].get('trader_write_intersection_count', 0)}",
        f"- Sector vs trader intersections: {report['checks'].get('sector_write_vs_trader_count', 0)}",
        f"- Sector vs frozen intersections: {report['checks'].get('sector_write_vs_frozen_count', 0)}",
        "",
        "## Violations",
    ]
    if report["violations"]:
        lines.extend([f"- {v}" for v in report["violations"]])
    else:
        lines.append("- none")

    text = "\n".join(lines) + "\n"
    run_md.write_text(text, encoding="utf-8")
    latest_md.write_text(text, encoding="utf-8")

    print(str(run_json))
    print(str(latest_json))
    print(report["status"])


if __name__ == "__main__":
    main()
