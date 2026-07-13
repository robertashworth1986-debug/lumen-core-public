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
    ("live_breadth", "docs/LIVE_EVIDENCE_MAX_HARVEST_2026-07-13.md", True),
    ("live_breadth", "out/ops/live_evidence_max_harvest_latest.json", True),
    ("live_breadth", "config/live_source_registry.json", True),
    ("live_breadth", "config/live_sources.json", True),
    ("geometry", "config/geometry_championship_v1_registry.json", True),
    ("geometry", "docs/GEOMETRY_CHAMPIONSHIP_BRIDGE_2026-06-21.md", False),
    ("geometry", "out/ops/geometry_championship_bridge_latest.json", False),
    ("geometry", "docs/GEOMETRY_PROOF_FRONTIER_BOARD_2026-06-22.md", True),
    ("geometry", "out/ops/geometry_proof_frontier_board_latest.json", True),
    ("geometry", "docs/GEOMETRY_LIVE_BREADTH_PROOF_QUEUE_2026-06-22.md", True),
    ("geometry", "out/ops/geometry_live_breadth_proof_queue_latest.json", True),
    ("geometry", "dashboard/data/geometry_live_breadth_proof_queue.json", True),
    ("geometry", "docs/TOP_GEOMETRY_LIVE_REPLAY_RESULTS_2026-06-24.md", True),
    ("geometry", "out/ops/top_geometry_live_replay_results_latest.json", True),
    ("geometry", "dashboard/data/top_geometry_live_replay_results.json", True),
    ("geometry", "docs/SECTOR_VALIDATION_PRIORITY_BOARD_2026-07-13.md", True),
    ("geometry", "out/ops/sector_validation_priority_board_latest.json", True),
    ("geometry", "out/ops/sector_validation_priority_board_manifest_latest.json", True),
    ("geometry", "dashboard/data/sector_validation_priority_board.json", True),
    ("grants", "grant_submissions/GRANT_DEADLINE_TRIAGE_2026-06-22.md", True),
    ("grants", "grant_submissions/TOP5_LIVE_PROOF_SUBMISSION_BOARD_2026-06-22.md", True),
    ("grants", "out/ops/top5_live_proof_submission_board_latest.json", True),
    ("grants", "grant_submissions/LIVE_BREADTH_PROVENANCE_ANNEX_2026-06-21.md", False),
    ("grants", "grant_submissions/funding_sprint_20260709/NEAR_DEADLINE_SUBMISSION_COMMAND_BOARD_2026-07-13.md", True),
    ("grants", "out/ops/near_deadline_submission_command_board_latest.json", True),
    ("submissions", "grant_submissions/funding_sprint_20260709/EXTERNAL_SUBMISSION_RECEIPT_2026-07-13.md", True),
    ("submissions", "grant_submissions/funding_sprint_20260709/EXTERNAL_SUBMISSION_RECEIPT_2026-07-13.json", True),
    ("submissions", "grant_submissions/funding_sprint_20260709/ARMY_AIDP_RFI4_EMAIL_DRAFT_2026-07-13.md", True),
    ("submissions", "grant_submissions/funding_sprint_20260709/ARMY_AIDP_RFI4_SOURCE_MANIFEST_2026-07-13.md", True),
    ("submissions", "outputs/aidp-rfi4-20260713/AIDP - Questions and Feedback Submission Sheet - LumenCore Draft.xlsx", True),
    ("submissions", "outputs/aidp-rfi4-20260713/AIDP - Questions and Feedback Submission Sheet - LumenCore Draft.xlsx.inspect.ndjson", True),
    ("submissions", "outputs/aidp-rfi4-20260713/AIDP_RFI4_feedback_preview.png", False),
    ("submissions", "grant_submissions/funding_sprint_20260709/NASA_DATA_CENTER_RFI_EMAIL_DRAFT_2026-07-11.md", True),
    ("submissions", "grant_submissions/funding_sprint_20260709/NASA_DATA_CENTER_RFI_READY_RESPONSE_2026-07-11.md", True),
    ("submissions", "grant_submissions/funding_sprint_20260709/NASA_DATA_CENTER_RFI_READY_RESPONSE_2026-07-11.pdf", True),
    ("routing", "config/eia_grid_wave_champion_protocol_v1.json", True),
    ("routing", "config/eia_grid_residual_moe_protocol_v1.json", True),
    ("routing", "config/eia_grid_prospective_hybrid_router_protocol_v1.json", True),
    ("routing", "code/eia_grid_wave_champion_benchmark.py", True),
    ("routing", "code/eia_grid_residual_moe_benchmark.py", True),
    ("routing", "code/eia_grid_prospective_hybrid_router.py", True),
    ("routing", "docs/EIA_GRID_WAVE_CHAMPION_BENCHMARK_2026-07-13.md", True),
    ("routing", "docs/EIA_GRID_RESIDUAL_MOE_BENCHMARK_2026-07-13.md", True),
    ("routing", "docs/EIA_GRID_PROSPECTIVE_HYBRID_ROUTER_2026-07-13.md", True),
    ("routing", "out/eia_grid_wave_champion/eia_grid_wave_champion_benchmark_latest.json", True),
    ("routing", "out/eia_grid_wave_champion/eia_grid_wave_champion_manifest_latest.json", True),
    ("routing", "out/eia_grid_wave_champion/eia_grid_wave_champion_rows_latest.csv", True),
    ("routing", "out/eia_grid_residual_moe/eia_grid_residual_moe_benchmark_latest.json", True),
    ("routing", "out/eia_grid_residual_moe/eia_grid_residual_moe_manifest_latest.json", True),
    ("routing", "out/eia_grid_residual_moe/eia_grid_residual_moe_rows_latest.csv", True),
    ("routing", "tests/test_eia_grid_wave_champion_benchmark.py", True),
    ("routing", "tests/test_eia_grid_residual_moe_benchmark.py", True),
    ("routing", "tests/test_eia_grid_prospective_hybrid_router.py", True),
    ("opf", "config/ieee_acopf_routing_protocol_v1.json", True),
    ("opf", "docs/IEEE_ACOPF_ROUTE_READINESS_2026-07-13.md", True),
    ("mda", "grant_submissions/MDA26BZ04_NV007_ControlAssessment/MDA26BZ04_NV007_SOURCE_MANIFEST_2026-07-13.md", True),
    ("mda", "grant_submissions/MDA26BZ04_NV007_ControlAssessment/MDA26BZ04_NV007_GO_NO_GO_AND_PROPOSAL_MAP_2026-07-13.md", True),
    ("mda", "grant_submissions/MDA26BZ04_NV007_ControlAssessment/MDA26BZ04_NV007_PHASE_I_TECHNICAL_VOLUME_SKELETON_2026-07-13.md", True),
    ("mda", "grant_submissions/MDA26BZ04_NV007_ControlAssessment/MDA26BZ04_NV007_DSIP_ASSEMBLY_MAP_2026-07-13.md", True),
    ("mda", "grant_submissions/MDA26BZ04_NV007_ControlAssessment/MDA26BZ04_NV007_CURRENT_CAPABILITY_BOUNDARY_2026-07-13.md", True),
    ("mda", "grant_submissions/MDA26BZ04_NV007_ControlAssessment/MDA26BZ04_NV007_LAWFUL_CORPUS_AND_BENCHMARK_PLAN_2026-07-13.md", True),
    ("estate", "grant_submissions/funding_sprint_20260709/LUMENCORE_ESTATE_MASTER_INDEX_2026-07-13.md", True),
    ("estate", "out/ops/lumencore_estate_master_index_latest.json", True),
    ("estate", "out/ops/lumencore_estate_master_index_manifest_latest.json", True),
    ("estate", "out/ops/lumencore_estate_file_inventory_latest.csv", True),
    ("reproducibility", "code/geometry_time_series_model_routing_benchmark.py", True),
    ("reproducibility", "code/ops/BUILD_TOP_GEOMETRY_LIVE_REPLAY_RESULTS.py", True),
    ("reproducibility", "code/ops/BUILD_LIVE_EVIDENCE_MAX_HARVEST.py", True),
    ("reproducibility", "code/ops/BUILD_SECTOR_VALIDATION_PRIORITY_BOARD.py", True),
    ("reproducibility", "code/ops/BUILD_LUMENCORE_ESTATE_MASTER_INDEX.py", True),
    ("reproducibility", "code/ops/BUILD_NEAR_DEADLINE_SUBMISSION_COMMAND_BOARD.py", True),
    ("reproducibility", "code/render_nasa_data_center_rfi_response.py", True),
    ("reproducibility", "tools/Run-LiveEvidenceMaxHarvest.ps1", True),
    ("reproducibility", "tests/test_geometry_time_series_model_routing_benchmark.py", True),
    ("reproducibility", "tests/test_top_geometry_live_replay_results.py", True),
    ("reproducibility", "tests/test_live_evidence_max_harvest.py", True),
    ("reproducibility", "tests/test_sector_validation_priority_board.py", True),
    ("reproducibility", "tests/test_lumencore_estate_master_index.py", True),
    ("reproducibility", "tests/test_near_deadline_submission_command_board.py", True),
    ("reproducibility", "tests/test_nasa_data_center_rfi_response.py", True),
    ("reproducibility", "tests/test_external_submission_receipt.py", True),
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


def selected_proof_artifacts() -> list[tuple[str, str, bool]]:
    selected = list(PROOF_ARTIFACTS)
    seen = {rel_path.casefold() for _, rel_path, _ in selected}
    replay_path = OUT_OPS / "top_geometry_live_replay_results_latest.json"
    if not replay_path.exists():
        return selected

    replay = json.loads(replay_path.read_text(encoding="utf-8"))
    for card in replay.get("replay_cards", []):
        for profile in card.get("source_profiles", []):
            rel_path = str(profile.get("snapshot_json") or "").replace("\\", "/")
            if not rel_path or rel_path.casefold() in seen:
                continue
            candidate = (ROOT / rel_path).resolve()
            try:
                candidate.relative_to(ROOT.resolve())
            except ValueError:
                continue
            if candidate.suffix.lower() != ".json":
                continue
            selected.append(("frozen_inputs", rel_path, True))
            seen.add(rel_path.casefold())
    return selected


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
    artifacts = [
        artifact_card(category, rel_path, required, packet_dir)
        for category, rel_path, required in selected_proof_artifacts()
    ]
    ready = [row for row in artifacts if row["exists"]]
    missing_required = [row for row in artifacts if row["required"] and not row["exists"]]
    total_bytes = sum(int(row["bytes"]) for row in ready)
    return {
        "generated_utc": generated,
        "schema": "external_proof_vault_manifest_v2",
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
            "frozen_input_count": sum(1 for row in artifacts if row["category"] == "frozen_inputs"),
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
