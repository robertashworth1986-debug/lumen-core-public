from __future__ import annotations

import argparse
import hashlib
import json
import shutil
from datetime import datetime, timezone
from pathlib import Path, PurePosixPath
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
DEFAULT_DESTINATION = Path("E:/LumaProofVault/CURRENT_REVIEWER_CONTROL_PACKAGE_20260729")
RECEIPT_PATH = (
    ROOT
    / "grant_submissions"
    / "funding_sprint_20260709"
    / "CURRENT_REVIEWER_E_DRIVE_MIRROR_RECEIPT_2026-07-29.json"
)
FRONT_DOOR_PATH = ROOT / "out" / "ops" / "current_reviewer_front_door_latest.json"
DATA_ROOM_PATH = ROOT / "out" / "ops" / "data_room_manifest_latest.json"

EXTRA_ARTIFACTS: tuple[tuple[str, str, str], ...] = (
    (
        "grant_submissions/funding_sprint_20260709/CURRENT_REVIEWER_FRONT_DOOR_2026-07-29.md",
        "public_safe_human_review_required",
        "reviewer_front_door",
    ),
    (
        "out/ops/current_reviewer_front_door_latest.json",
        "machine_readable_control",
        "reviewer_front_door",
    ),
    (
        "docs/receipts/CURRENT_REVIEWER_PUBLIC_ARTIFACT_MANIFEST_2026-07-29.json",
        "public_safe_machine_readable_control",
        "reviewer_front_door",
    ),
    (
        "grant_submissions/funding_sprint_20260709/DATA_ROOM_MANIFEST_2026-07-09.md",
        "internal_control_human_review_required",
        "data_room_index",
    ),
    (
        "out/ops/data_room_manifest_latest.json",
        "machine_readable_control",
        "data_room_index",
    ),
    (
        "grant_submissions/funding_sprint_20260709/NEAR_DEADLINE_SUBMISSION_COMMAND_BOARD_2026-07-29.md",
        "internal_control_human_review_required",
        "submission_control",
    ),
    (
        "out/ops/near_deadline_submission_command_board_latest.json",
        "machine_readable_control",
        "submission_control",
    ),
    (
        "grant_submissions/funding_sprint_20260709/NEAR_DEADLINE_PACKAGE_DECISION_GATE_2026-07-29.md",
        "internal_control_human_review_required",
        "submission_control",
    ),
    (
        "out/ops/near_deadline_package_decision_gate_latest.json",
        "machine_readable_control",
        "submission_control",
    ),
    (
        "grant_submissions/funding_sprint_20260709/SUBMISSION_CONFORMANCE_GATE_2026-07-25.md",
        "internal_control_human_review_required",
        "submission_control",
    ),
    (
        "out/ops/submission_conformance_gate_latest.json",
        "machine_readable_control",
        "submission_control",
    ),
    (
        "grant_submissions/funding_sprint_20260709/FUNDING_SPRINT_REVIEWER_GATE_2026-07-09.md",
        "internal_control_human_review_required",
        "submission_control",
    ),
    (
        "out/ops/funding_sprint_reviewer_gate_latest.json",
        "machine_readable_control",
        "submission_control",
    ),
    (
        "grant_submissions/funding_sprint_20260709/SUBMISSION_AUTHORITY_MATRIX_2026-07-09.md",
        "internal_control_human_review_required",
        "submission_control",
    ),
    (
        "out/ops/submission_authority_matrix_latest.json",
        "machine_readable_control",
        "submission_control",
    ),
    (
        "grant_submissions/funding_sprint_20260709/AGENCY_SUBMISSION_ASSEMBLY_GATE_2026-07-09.md",
        "internal_control_human_review_required",
        "submission_control",
    ),
    (
        "out/ops/agency_submission_assembly_gate_latest.json",
        "machine_readable_control",
        "submission_control",
    ),
    (
        "grant_submissions/funding_sprint_20260709/LIVE_FUNDING_PORTAL_HANDOFF_2026-07-29.md",
        "internal_control_human_review_required",
        "submission_control",
    ),
    (
        "out/ops/live_funding_portal_handoff_latest.json",
        "machine_readable_control",
        "submission_control",
    ),
    (
        "grant_submissions/NASHVILLE_EC_FALL_2026/NASHVILLE_EC_TAKEOFF_ONBOARDING_REVIEW_PACKET_2026-07-29.md",
        "internal_control_founder_review_required",
        "nashville_ec",
    ),
    (
        "grant_submissions/funding_sprint_20260709/OFFICIAL_INBOUND_STATUS_EVENT_REGISTER_2026-07-25.json",
        "privacy_safe_machine_readable_control",
        "inbound_control",
    ),
    (
        "grant_submissions/funding_sprint_20260709/EMAIL_ACTION_RECONCILIATION_2026-07-18.json",
        "machine_readable_control",
        "inbound_control",
    ),
    (
        "grant_submissions/funding_sprint_20260709/EMAIL_ACTION_RECONCILIATION_2026-07-18.md",
        "internal_control_human_review_required",
        "inbound_control",
    ),
    (
        "grant_submissions/funding_sprint_20260709/DLA_DSIP_OFFICIAL_NON_SUBMISSION_RECEIPT_2026-07-28.json",
        "privacy_safe_official_status_receipt",
        "submission_control",
    ),
    (
        "grant_submissions/funding_sprint_20260709/ARGOS_GOVERNMENT_SUBMISSION_STATUS_2026-07-28.json",
        "privacy_safe_dispatch_receipt",
        "submission_control",
    ),
    (
        "docs/EXTERNAL_VALIDATION_500_SPRINT_2026-07-16.md",
        "public_safe_human_review_required",
        "external_validation",
    ),
    (
        "out/ops/external_validation_500_sprint_latest.json",
        "machine_readable_control",
        "external_validation",
    ),
    (
        "docs/PUBLIC_RELEASE_SYNC_PLAN_2026-07-18.md",
        "internal_control_human_review_required",
        "public_release",
    ),
    (
        "out/ops/PUBLIC_RELEASE_SYNC_PLAN_2026-07-18.json",
        "machine_readable_control",
        "public_release",
    ),
    (
        "grant_submissions/NSF_Project_Pitch/PROJECT_PITCH_PORTAL_FIELDS_2026-07-29.md",
        "public_safe_human_review_required",
        "nsf_project_pitch",
    ),
    (
        "grant_submissions/NSF_Project_Pitch/PROJECT_PITCH_PASTE_CHECK_2026-07-29.md",
        "public_safe_human_review_required",
        "nsf_project_pitch",
    ),
    (
        "grant_submissions/NSF_Project_Pitch/PROJECT_PITCH_READINESS_2026-07-29.md",
        "internal_control_human_review_required",
        "nsf_project_pitch",
    ),
    (
        "grant_submissions/NSF_Project_Pitch/NSF_PROJECT_PITCH_ROUTING_MANIFEST_2026-07-29.json",
        "machine_readable_control",
        "nsf_project_pitch",
    ),
    (
        "grant_submissions/NSF_Project_Pitch/NSF_PROJECT_PITCH_SOURCE_AUDIT_2026-07-29.json",
        "machine_readable_control",
        "nsf_project_pitch",
    ),
    (
        "output/pdf/LumenCore_ERDC_SDC_Solution_Brief_PUBLIC_DRAFT_2026-07-29.pdf",
        "public_draft_human_review_required",
        "erdc_sdc",
    ),
    (
        "grant_submissions/funding_sprint_20260709/ERDC_SDC_SOLUTION_BRIEF_COMPLIANCE_GATE_2026-07-29.json",
        "machine_readable_control",
        "erdc_sdc",
    ),
    (
        "grant_submissions/funding_sprint_20260709/ERDC_SDC_SOLUTION_BRIEF_COMPLIANCE_GATE_2026-07-29.md",
        "internal_control_human_review_required",
        "erdc_sdc",
    ),
    (
        "grant_submissions/funding_sprint_20260709/ERDC_SDC_PHASE2_ROM_GATE_2026-07-29.json",
        "machine_readable_control",
        "erdc_sdc",
    ),
    (
        "grant_submissions/funding_sprint_20260709/ERDC_SDC_PHASE2_ROM_GATE_2026-07-29.md",
        "internal_control_human_review_required",
        "erdc_sdc",
    ),
    (
        "grant_submissions/funding_sprint_20260709/ERDC_SDC_PHASE2_ROM_APPROVAL_WORKFLOW_2026-07-29.md",
        "internal_control_human_review_required",
        "erdc_sdc",
    ),
    (
        "grant_submissions/funding_sprint_20260709/source_attachments/W912HZ26SC005/SOURCE_MANIFEST_2026-07-29.json",
        "official_source_receipt",
        "erdc_sdc",
    ),
    (
        "grant_submissions/funding_sprint_20260709/source_attachments/W912HZ26SC005/CSO_HPCMP_SDC_30April2026_FINAL.pdf",
        "official_public_source",
        "erdc_sdc",
    ),
    (
        "grant_submissions/funding_sprint_20260709/source_attachments/W912HZ26SC005/HPCMP_SDC_FAQ_20Jul2026.pdf",
        "official_public_source",
        "erdc_sdc",
    ),
    (
        "grant_submissions/LAUNCHTN_3686_PITCH_2026/LAUNCHTN_3686_APPLICATION_MANIFEST_2026-07-29.json",
        "machine_readable_control",
        "launchtn_3686",
    ),
    (
        "grant_submissions/LAUNCHTN_3686_PITCH_2026/LAUNCHTN_3686_PORTAL_FIELD_MAP_2026-07-29.md",
        "internal_control_human_review_required",
        "launchtn_3686",
    ),
    (
        "grant_submissions/LAUNCHTN_3686_PITCH_2026/LAUNCHTN_3686_APPLICATION_REFRESH_2026-07-29.md",
        "internal_control_human_review_required",
        "launchtn_3686",
    ),
    (
        "grant_submissions/LAUNCHTN_3686_PITCH_2026/LUMENCORE_3686_PITCH_DECK_2026-07-29_REVIEW_REQUIRED.pptx",
        "internal_control_human_review_required",
        "launchtn_3686",
    ),
    (
        "code/watchers/doe_fy26_watcher.py",
        "reproducibility_source",
        "doe_genesis",
    ),
    (
        "tests/test_doe_fy26_watcher.py",
        "reproducibility_test",
        "doe_genesis",
    ),
    (
        "out/grants/doe_fy26_watch.json",
        "machine_readable_public_source_observation",
        "doe_genesis",
    ),
    (
        "code/ops/BUILD_DOE_GENESIS_PHASE1_PITCH_PACKET.py",
        "reproducibility_source",
        "doe_genesis",
    ),
    (
        "tests/test_doe_genesis_phase1_pitch_packet.py",
        "reproducibility_test",
        "doe_genesis",
    ),
    (
        "grant_submissions/funding_sprint_20260709/DOE_FY26_GENESIS_PHASE1_PITCH_PACKET_2026-07-29.json",
        "machine_readable_control",
        "doe_genesis",
    ),
    (
        "grant_submissions/funding_sprint_20260709/DOE_FY26_GENESIS_PHASE1_PITCH_PACKET_2026-07-29.md",
        "internal_control_human_review_required",
        "doe_genesis",
    ),
    (
        "grant_submissions/funding_sprint_20260709/source_attachments/DOE_FY26_GENESIS/Pitch-Stage-Key-Questions.docx",
        "official_public_source",
        "doe_genesis",
    ),
    (
        "config/market_signal_source_native_benchmark_protocol_v1.json",
        "reproducibility_source",
        "source_native_research",
    ),
    (
        "code/ops/BUILD_MARKET_SIGNAL_SOURCE_NATIVE_BENCHMARK.py",
        "reproducibility_source",
        "source_native_research",
    ),
    (
        "tests/test_market_signal_source_native_benchmark.py",
        "reproducibility_test",
        "source_native_research",
    ),
    (
        "docs/MARKET_SIGNAL_SOURCE_NATIVE_BENCHMARK_2026-07-29.md",
        "public_safe_human_review_required",
        "source_native_research",
    ),
    (
        "code/ops/BUILD_SOURCE_NATIVE_FAMILY_BASELINE_LEDGER.py",
        "reproducibility_source",
        "source_native_research",
    ),
    (
        "tests/test_source_native_family_baseline_ledger.py",
        "reproducibility_test",
        "source_native_research",
    ),
    (
        "docs/SOURCE_NATIVE_FAMILY_BASELINE_LEDGER.md",
        "public_safe_human_review_required",
        "source_native_research",
    ),
    (
        "config/time_series_source_native_prospective_protocol_v1.json",
        "reproducibility_source",
        "source_native_research",
    ),
    (
        "code/ops/VERIFY_TIME_SERIES_SOURCE_NATIVE_PROSPECTIVE_PROTOCOL.py",
        "reproducibility_source",
        "source_native_research",
    ),
    (
        "tests/test_time_series_source_native_prospective_protocol.py",
        "reproducibility_test",
        "source_native_research",
    ),
    (
        "code/ops/BUILD_SOURCE_NATIVE_RESEARCH_WHITEPAPER.py",
        "reproducibility_source",
        "source_native_research",
    ),
    (
        "tests/test_source_native_research_whitepaper.py",
        "reproducibility_test",
        "source_native_research",
    ),
    (
        "docs/LUMENCORE_SOURCE_NATIVE_BENCHMARK_WHITEPAPER_CURRENT.md",
        "public_safe_human_review_required",
        "source_native_research",
    ),
    (
        "dashboard/data/market_signal_source_native_benchmark.json",
        "public_safe_machine_readable",
        "source_native_research",
    ),
    (
        "dashboard/data/source_native_family_baseline_ledger.json",
        "public_safe_machine_readable",
        "source_native_research",
    ),
    (
        "docs/VPS_GATEWAY_RECOVERY_2026-07-29.md",
        "internal_control_human_review_required",
        "vps_recovery",
    ),
    (
        "deploy/REPAIR_LUMA_GATEWAY_MODULE.ps1",
        "reproducibility_source_human_unlock_required",
        "vps_recovery",
    ),
    (
        "tests/test_repair_luma_gateway_module.py",
        "reproducibility_test",
        "vps_recovery",
    ),
    (
        "out/ops/dashboard_vps_mirror_audit_latest.json",
        "machine_readable_observation",
        "vps_recovery",
    ),
    (
        "out/ops/dashboard_vps_mirror_audit_latest.md",
        "internal_control_human_review_required",
        "vps_recovery",
    ),
    (
        "out/ops/live_domain_service_contract_latest.json",
        "machine_readable_observation",
        "public_release",
    ),
    (
        "docs/LIVE_DOMAIN_SERVICE_CONTRACT_2026-07-25.md",
        "internal_control_human_review_required",
        "public_release",
    ),
    (
        "out/ops/live_domain_deployment_feed_latest.json",
        "machine_readable_observation",
        "public_release",
    ),
    (
        "docs/LIVE_DOMAIN_DEPLOYMENT_FEED_2026-06-27.md",
        "internal_control_human_review_required",
        "public_release",
    ),
    (
        "out/ops/live_domain_proof_feed_deploy_bundle_latest.json",
        "machine_readable_control",
        "public_release",
    ),
    (
        "docs/LIVE_DOMAIN_PROOF_FEED_DEPLOY_BUNDLE_2026-06-27.md",
        "internal_control_human_review_required",
        "public_release",
    ),
    (
        "code/ops/BUILD_LIVE_DOMAIN_SERVICE_CONTRACT.py",
        "reproducibility_source",
        "public_release",
    ),
    (
        "code/ops/BUILD_LIVE_DOMAIN_DEPLOYMENT_FEED.py",
        "reproducibility_source",
        "public_release",
    ),
    (
        "code/ops/BUILD_LIVE_DOMAIN_PROOF_FEED_DEPLOY_BUNDLE.py",
        "reproducibility_source",
        "public_release",
    ),
    (
        "deploy/PUSH_PROOF_FEEDS_TO_VPS.ps1",
        "reproducibility_source_human_unlock_required",
        "public_release",
    ),
    (
        "tests/test_live_domain_service_contract.py",
        "reproducibility_test",
        "public_release",
    ),
    (
        "tests/test_live_domain_deployment_feed.py",
        "reproducibility_test",
        "public_release",
    ),
    (
        "tests/test_live_domain_proof_feed_deploy_bundle.py",
        "reproducibility_test",
        "public_release",
    ),
    (
        "out/ops/workspace_secret_value_audit_latest.json",
        "machine_readable_security_receipt",
        "security_control",
    ),
    (
        "code/safe_diagnostics.py",
        "reproducibility_source",
        "security_control",
    ),
    (
        "code/ops/SANITIZE_LIVE_SOURCE_DIAGNOSTICS.py",
        "reproducibility_source",
        "security_control",
    ),
    (
        "code/ops/AUDIT_WORKSPACE_SECRET_VALUES.py",
        "reproducibility_source",
        "security_control",
    ),
    (
        "tests/test_safe_diagnostics.py",
        "reproducibility_test",
        "security_control",
    ),
    (
        "tests/test_workspace_secret_value_audit.py",
        "reproducibility_test",
        "security_control",
    ),
    (
        "code/ops/BUILD_CURRENT_REVIEWER_FRONT_DOOR.py",
        "reproducibility_source",
        "reviewer_front_door",
    ),
    (
        "tests/test_current_reviewer_front_door.py",
        "reproducibility_test",
        "reviewer_front_door",
    ),
    (
        "code/ops/BUILD_DATA_ROOM_MANIFEST.py",
        "reproducibility_source",
        "data_room_index",
    ),
    (
        "tests/test_data_room_manifest.py",
        "reproducibility_test",
        "data_room_index",
    ),
    (
        "code/ops/BUILD_CURRENT_REVIEWER_E_DRIVE_MIRROR.py",
        "reproducibility_source",
        "custody_mirror",
    ),
    (
        "tests/test_current_reviewer_e_drive_mirror.py",
        "reproducibility_test",
        "custody_mirror",
    ),
)

PROHIBITED_PARTS = {
    ".env",
    "credentials",
    "credential",
    "private",
    "secrets",
    "secret",
    "tokens",
    "token",
}


def now_utc() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def read_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"Expected JSON object: {path}")
    return value


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest().upper()


def validate_relative_path(relative_path: str) -> str:
    normalized = PurePosixPath(relative_path)
    if normalized.is_absolute() or ".." in normalized.parts:
        raise ValueError(f"Unsafe mirror path: {relative_path}")
    lowered = {part.lower() for part in normalized.parts}
    if lowered & PROHIBITED_PARTS:
        raise ValueError(f"Private or credential path blocked: {relative_path}")
    return normalized.as_posix()


def collect_artifacts() -> list[dict[str, Any]]:
    front_door = read_json(FRONT_DOOR_PATH)
    data_room = read_json(DATA_ROOM_PATH)
    if front_door.get("status") != (
        "CURRENT_REVIEWER_FRONT_DOOR_READY_HUMAN_RELEASE_REQUIRED"
    ):
        raise ValueError("Current reviewer front door is not in the expected state")
    if front_door.get("summary", {}).get("external_release_authorized_count") != 0:
        raise ValueError("Reviewer front door unexpectedly authorizes external release")
    if data_room.get("summary", {}).get("unsafe_secret_count") != 0:
        raise ValueError("Data-room secret scan is not clear")
    if data_room.get("summary", {}).get("unsafe_claim_count") != 0:
        raise ValueError("Data-room claim scan is not clear")

    candidates: list[tuple[str, str, str]] = [
        (
            str(row["path"]),
            str(row.get("classification", "public_safe_human_review_required")),
            "current_reviewer_front_door",
        )
        for row in front_door["artifacts"]
    ]
    candidates.extend(EXTRA_ARTIFACTS)
    deploy_bundle = read_json(
        ROOT / "out" / "ops" / "live_domain_proof_feed_deploy_bundle_latest.json"
    )
    archive_path = Path(str(deploy_bundle.get("archive_path", ""))).resolve()
    try:
        archive_relative = archive_path.relative_to(ROOT.resolve()).as_posix()
    except ValueError as exc:
        raise ValueError("Current public deploy archive is outside the repository") from exc
    if not archive_path.is_file():
        raise FileNotFoundError(archive_path)
    if sha256_file(archive_path).lower() != str(
        deploy_bundle.get("archive_sha256", "")
    ).lower():
        raise ValueError("Current public deploy archive hash does not match its manifest")
    candidates.append(
        (
            archive_relative,
            "feed_only_deployment_bundle_human_unlock_required",
            "public_release",
        )
    )

    records: list[dict[str, Any]] = []
    seen: set[str] = set()
    for relative_path, classification, role in candidates:
        relative_path = validate_relative_path(relative_path)
        if relative_path in seen:
            continue
        seen.add(relative_path)
        source = ROOT / Path(relative_path)
        if not source.is_file():
            raise FileNotFoundError(source)
        records.append(
            {
                "path": relative_path,
                "classification": classification,
                "role": role,
                "bytes": source.stat().st_size,
                "sha256": sha256_file(source),
            }
        )
    return sorted(records, key=lambda row: row["path"])


def mirror(
    destination_root: Path,
    *,
    receipt_path: Path = RECEIPT_PATH,
    generated_utc: str | None = None,
) -> dict[str, Any]:
    destination_root.mkdir(parents=True, exist_ok=True)
    artifacts = collect_artifacts()
    copied_count = 0
    unchanged_count = 0

    for artifact in artifacts:
        source = ROOT / Path(artifact["path"])
        destination = destination_root / Path(artifact["path"])
        destination.parent.mkdir(parents=True, exist_ok=True)
        if destination.is_file() and sha256_file(destination) == artifact["sha256"]:
            unchanged_count += 1
        else:
            shutil.copy2(source, destination)
            copied_count += 1
        artifact["destination_relative_path"] = artifact["path"]
        artifact["copy_bytes"] = destination.stat().st_size
        artifact["copy_sha256"] = sha256_file(destination)
        artifact["copy_sha256_matched"] = (
            artifact["copy_bytes"] == artifact["bytes"]
            and artifact["copy_sha256"] == artifact["sha256"]
        )

    payload: dict[str, Any] = {
        "schema": "lumencore.current_reviewer_e_drive_mirror_receipt.v1",
        "generated_utc": generated_utc or now_utc(),
        "status": (
            "CURRENT_REVIEWER_E_DRIVE_MIRROR_COMPLETE_HUMAN_RELEASE_REQUIRED"
        ),
        "source_root": str(ROOT),
        "destination_root": str(destination_root),
        "artifact_count": len(artifacts),
        "copied_count": copied_count,
        "unchanged_count": unchanged_count,
        "all_copy_sha256_matched": all(
            row["copy_sha256_matched"] for row in artifacts
        ),
        "private_values_mirrored": False,
        "unapproved_launchtn_financial_model_mirrored": False,
        "external_release_authorized": False,
        "final_submission_allowed_without_human": False,
        "source_front_door_sha256": sha256_file(FRONT_DOOR_PATH),
        "source_data_room_manifest_sha256": sha256_file(DATA_ROOM_PATH),
        "artifacts": artifacts,
        "omitted_gated_artifacts": [
            {
                "path": (
                    "grant_submissions/LAUNCHTN_3686_PITCH_2026/"
                    "LUMENCORE_3686_FINANCIAL_MODEL_2026-07-17.xlsx"
                ),
                "reason": "Founder approval of planning assumptions remains open.",
            },
            {
                "path": "Any ignored private capture or portal-input file",
                "reason": "Private values are excluded from the bounded reviewer mirror.",
            },
        ],
        "claim_boundary": (
            "This receipt proves only local file custody and SHA-256 parity for the "
            "listed artifacts. It does not authorize external release, prove submission, "
            "selection, award, independent validation, field performance, savings, "
            "revenue, or a promoted champion."
        ),
    }
    if not payload["all_copy_sha256_matched"]:
        raise ValueError("One or more E-drive mirror copies failed SHA-256 verification")

    receipt_path.parent.mkdir(parents=True, exist_ok=True)
    receipt_path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    receipt_destination = destination_root / "_receipts" / receipt_path.name
    receipt_destination.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(receipt_path, receipt_destination)
    if sha256_file(receipt_path) != sha256_file(receipt_destination):
        raise ValueError("Mirror receipt copy failed SHA-256 verification")
    return payload


def check(destination_root: Path, receipt_path: Path = RECEIPT_PATH) -> None:
    payload = read_json(receipt_path)
    if payload.get("destination_root") != str(destination_root):
        raise ValueError("Mirror receipt destination does not match")
    current = {row["path"]: row for row in collect_artifacts()}
    recorded = {row["path"]: row for row in payload.get("artifacts", [])}
    if set(current) != set(recorded):
        raise ValueError("Mirror artifact set is stale")
    for relative_path, row in current.items():
        if row["sha256"] != recorded[relative_path].get("sha256"):
            raise ValueError(f"Source artifact changed: {relative_path}")
        destination = destination_root / Path(relative_path)
        if not destination.is_file() or sha256_file(destination) != row["sha256"]:
            raise ValueError(f"Mirror copy is stale or missing: {relative_path}")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Build a bounded current reviewer mirror on the E drive."
    )
    parser.add_argument(
        "--destination-root",
        type=Path,
        default=DEFAULT_DESTINATION,
    )
    parser.add_argument("--generated-utc")
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()

    if args.check:
        check(args.destination_root)
        print("current reviewer E-drive mirror is current")
        return

    payload = mirror(
        args.destination_root,
        generated_utc=args.generated_utc,
    )
    print(
        json.dumps(
            {
                "status": payload["status"],
                "artifacts": payload["artifact_count"],
                "copied": payload["copied_count"],
                "unchanged": payload["unchanged_count"],
                "destination_root": payload["destination_root"],
                "receipt": RECEIPT_PATH.relative_to(ROOT).as_posix(),
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
