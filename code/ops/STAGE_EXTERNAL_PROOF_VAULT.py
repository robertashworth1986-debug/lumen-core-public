from __future__ import annotations

import argparse
import hashlib
import json
import shutil
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
OUT_OPS = ROOT / "out" / "ops"
DOCS = ROOT / "docs"

DEFAULT_TARGET_ROOT = Path("E:/LumaProofVault")
LOCAL_MANIFEST = OUT_OPS / "external_proof_vault_manifest_latest.json"
LOCAL_MD = DOCS / "EXTERNAL_PROOF_VAULT_MANIFEST_2026-06-22.md"


PROOF_ARTIFACTS: list[tuple[str, str, bool]] = [
    ("continuity", "AGENTS.md", True),
    ("continuity", "docs/LUMAJARVIS_OPERATING_MEMORY_2026-06-20.md", False),
    ("continuity", "docs/LUMAJARVIS_LEGENDARY_GOAL_PROMPT_2026-06-21.md", False),
    ("continuity", "docs/LUMA_CONTEXT_DASHBOARD_PARITY_AUDIT_2026-06-22.md", True),
    ("continuity", "out/ops/luma_context_dashboard_parity_audit_latest.json", True),
    ("proof_value", "docs/LIVE_PROOF_VALUE_METER_2026-06-22.md", True),
    ("proof_value", "out/ops/live_proof_value_meter_latest.json", True),
    ("proof_value", "docs/CHAMPION_METRIC_GAUNTLET_2026-06-27.md", True),
    ("proof_value", "out/ops/champion_metric_gauntlet_latest.json", True),
    ("proof_value", "dashboard/data/champion_metric_gauntlet.json", True),
    ("proof_value", "docs/DOLLAR_CLAIM_GATE_2026-06-21.md", True),
    ("proof_value", "out/ops/dollar_claim_gate_latest.json", True),
    ("live_breadth", "out/ops/live_breadth_value_panel_latest.json", True),
    ("live_breadth", "out/ops/live_breadth_value_panel_latest.csv", False),
    ("geometry", "config/geometry_championship_v1_registry.json", True),
    ("geometry", "docs/GEOMETRY_CHAMPIONSHIP_BRIDGE_2026-06-21.md", False),
    ("geometry", "out/ops/geometry_championship_bridge_latest.json", False),
    ("geometry", "docs/GEOMETRY_PROOF_FRONTIER_BOARD_2026-06-22.md", True),
    ("geometry", "out/ops/geometry_proof_frontier_board_latest.json", True),
    ("geometry", "docs/GEOMETRY_LIVE_BREADTH_PROOF_QUEUE_2026-06-22.md", True),
    ("geometry", "out/ops/geometry_live_breadth_proof_queue_latest.json", True),
    ("geometry", "dashboard/data/geometry_live_breadth_proof_queue.json", True),
    ("grants", "grant_submissions/GRANT_DEADLINE_TRIAGE_2026-06-22.md", True),
    ("grants", "grant_submissions/TOP5_LIVE_PROOF_SUBMISSION_BOARD_2026-06-22.md", True),
    ("grants", "out/ops/top5_live_proof_submission_board_latest.json", True),
    ("grants", "grant_submissions/LIVE_BREADTH_PROVENANCE_ANNEX_2026-06-21.md", False),
    ("dice", "grant_submissions/DICE_HR001126S0010/DICE_LIVE_BREADTH_REPLAY_2026-06-20.md", True),
    ("dice", "out/ops/dice_live_breadth_replay_latest.json", True),
    ("dice", "grant_submissions/DICE_HR001126S0010/DICE_EVIDENCE_SYNTHESIS_2026-06-20.md", True),
    ("harbor", "grant_submissions/NV063_HarborSentinel/NV063_AIS_INJECTION_BENCHMARK_2026-06-20.md", True),
    ("harbor", "out/ops/harbor_ais_injection_benchmark_latest.json", True),
    ("harbor", "grant_submissions/NV063_HarborSentinel/NV063_NAVY_REVIEWER_PROOF_MATRIX_2026-06-20.md", True),
    ("dashboards", "dashboard/data/live_proof_value_meter.json", True),
    ("dashboards", "dashboard/data/top5_live_proof_submission_board.json", True),
    ("dashboards", "dashboard/data/luma_context_dashboard_parity_audit.json", True),
]


def now_utc() -> str:
    return datetime.now(timezone.utc).isoformat()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text.rstrip("\r\n") + "\n", encoding="utf-8")


def artifact_card(category: str, rel_path: str, required: bool, packet_dir: Path) -> dict[str, Any]:
    source = ROOT / rel_path
    exists = source.exists() and source.is_file()
    vault_rel = Path("artifacts") / category / Path(rel_path)
    return {
        "category": category,
        "relative_path": rel_path,
        "source_path": str(source),
        "vault_relative_path": str(vault_rel).replace("\\", "/"),
        "vault_path": str(packet_dir / vault_rel),
        "required": required,
        "exists": exists,
        "bytes": source.stat().st_size if exists else 0,
        "modified_utc": datetime.fromtimestamp(source.stat().st_mtime, tz=timezone.utc).isoformat()
        if exists
        else None,
        "sha256": sha256_file(source) if exists else "",
        "status": "READY" if exists else ("MISSING_REQUIRED" if required else "MISSING_OPTIONAL"),
    }


def build_manifest(target_root: Path, package_name: str | None = None) -> dict[str, Any]:
    generated = now_utc()
    stamp = generated.replace("-", "").replace(":", "").split(".")[0].replace("+0000", "Z")
    package = package_name or f"LUMA_PROOF_VAULT_PACKET_{stamp}Z"
    packet_dir = target_root / package
    disk = shutil.disk_usage(target_root.anchor or target_root.drive or ".") if target_root.anchor else shutil.disk_usage(".")
    artifacts = [artifact_card(category, rel_path, required, packet_dir) for category, rel_path, required in PROOF_ARTIFACTS]
    ready = [row for row in artifacts if row["exists"]]
    missing_required = [row for row in artifacts if row["required"] and not row["exists"]]
    total_bytes = sum(int(row["bytes"]) for row in ready)
    return {
        "generated_utc": generated,
        "schema": "external_proof_vault_manifest_v1",
        "purpose": "Non-destructive staging manifest for high-value proof artifacts on external storage.",
        "repo_root": str(ROOT),
        "target_root": str(target_root),
        "packet_dir": str(packet_dir),
        "copy_policy": "Copy selected proof artifacts only. Never delete, move, clean, or overwrite source work.",
        "drive": {
            "anchor": target_root.anchor or target_root.drive,
            "total_bytes": disk.total,
            "free_bytes": disk.free,
            "used_bytes": disk.used,
        },
        "summary": {
            "artifact_count": len(artifacts),
            "ready_count": len(ready),
            "missing_required_count": len(missing_required),
            "missing_optional_count": sum(1 for row in artifacts if (not row["required"] and not row["exists"])),
            "total_ready_bytes": total_bytes,
            "ready_megabytes": round(total_bytes / 1024 / 1024, 3),
            "packet_ready": len(missing_required) == 0,
        },
        "claim_boundary": (
            "A proof vault is provenance and reproducibility infrastructure. It does not create revenue, "
            "field validation, customer savings, government savings, or trading profit by itself."
        ),
        "artifacts": artifacts,
    }


def copy_artifacts(manifest: dict[str, Any]) -> dict[str, Any]:
    packet_dir = Path(str(manifest["packet_dir"]))
    copied = []
    for row in manifest["artifacts"]:
        if not row["exists"]:
            continue
        source = Path(str(row["source_path"]))
        destination = Path(str(row["vault_path"]))
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, destination)
        copied_sha = sha256_file(destination)
        copied.append(
            {
                "relative_path": row["relative_path"],
                "vault_relative_path": row["vault_relative_path"],
                "bytes": destination.stat().st_size,
                "sha256": copied_sha,
                "verified": copied_sha == row["sha256"],
            }
        )
    manifest["copy_result"] = {
        "copied_count": len(copied),
        "verified_count": sum(1 for row in copied if row["verified"]),
        "all_copied_hashes_verified": all(row["verified"] for row in copied),
        "copied": copied,
    }
    return manifest


def render_readme(manifest: dict[str, Any]) -> str:
    summary = manifest["summary"]
    drive = manifest["drive"]
    lines = [
        "# Luma External Proof Vault Packet",
        "",
        f"Generated UTC: `{manifest['generated_utc']}`",
        "",
        "## Purpose",
        "",
        manifest["purpose"],
        "",
        "## Summary",
        "",
        f"- Artifacts ready: `{summary['ready_count']}/{summary['artifact_count']}`",
        f"- Missing required: `{summary['missing_required_count']}`",
        f"- Ready bytes: `{summary['total_ready_bytes']}`",
        f"- Drive free bytes at staging time: `{drive['free_bytes']}`",
        f"- Packet ready: `{str(summary['packet_ready']).lower()}`",
        "",
        "## Boundary",
        "",
        manifest["claim_boundary"],
        "",
        "## Included Artifacts",
        "",
    ]
    for row in manifest["artifacts"]:
        if row["exists"]:
            lines.append(f"- `{row['relative_path']}` -> `{row['vault_relative_path']}` | sha256 `{row['sha256']}`")
    missing = [row for row in manifest["artifacts"] if not row["exists"]]
    if missing:
        lines.extend(["", "## Missing Inputs", ""])
        for row in missing:
            lines.append(f"- `{row['relative_path']}` | `{row['status']}`")
    return "\n".join(lines)


def write_packet_manifest(manifest: dict[str, Any]) -> None:
    packet_dir = Path(str(manifest["packet_dir"]))
    write_json(packet_dir / "manifest.json", manifest)
    write_text(packet_dir / "README.md", render_readme(manifest))
    sha_lines = []
    for row in manifest["artifacts"]:
        if row["exists"]:
            sha_lines.append(f"{row['sha256']}  {row['vault_relative_path']}")
    write_text(packet_dir / "manifest.sha256.txt", "\n".join(sha_lines))


def stage_vault(target_root: Path, package_name: str | None = None, copy_files: bool = True) -> dict[str, Any]:
    target_root.mkdir(parents=True, exist_ok=True)
    manifest = build_manifest(target_root=target_root, package_name=package_name)
    if copy_files:
        manifest = copy_artifacts(manifest)
    write_packet_manifest(manifest)
    write_json(LOCAL_MANIFEST, manifest)
    write_text(LOCAL_MD, render_readme(manifest))
    return manifest


def main() -> int:
    parser = argparse.ArgumentParser(description="Stage a hashable Luma proof-vault packet to external storage.")
    parser.add_argument("--target-root", default=str(DEFAULT_TARGET_ROOT))
    parser.add_argument("--package-name", default="")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    manifest = stage_vault(
        target_root=Path(args.target_root),
        package_name=args.package_name or None,
        copy_files=not args.dry_run,
    )
    print(
        json.dumps(
            {
                "schema": manifest["schema"],
                "packet_dir": manifest["packet_dir"],
                "ready_count": manifest["summary"]["ready_count"],
                "artifact_count": manifest["summary"]["artifact_count"],
                "missing_required_count": manifest["summary"]["missing_required_count"],
                "copied_count": manifest.get("copy_result", {}).get("copied_count", 0),
                "all_copied_hashes_verified": manifest.get("copy_result", {}).get("all_copied_hashes_verified", False),
                "local_manifest": str(LOCAL_MANIFEST.relative_to(ROOT)).replace("\\", "/"),
                "local_markdown": str(LOCAL_MD.relative_to(ROOT)).replace("\\", "/"),
            },
            indent=2,
        )
    )
    return 0 if manifest["summary"]["missing_required_count"] == 0 else 2


if __name__ == "__main__":
    raise SystemExit(main())
