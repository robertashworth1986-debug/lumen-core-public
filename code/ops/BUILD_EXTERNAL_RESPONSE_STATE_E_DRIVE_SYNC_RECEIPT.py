from __future__ import annotations

import hashlib
import json
import shutil
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
SPRINT_DIR = ROOT / "grant_submissions" / "funding_sprint_20260709"
RECEIPT = SPRINT_DIR / "EXTERNAL_RESPONSE_STATE_E_DRIVE_SYNC_RECEIPT_2026-07-17.json"
DESTINATION_ROOT = Path("E:/LumaProofVault/OUTREACH/EXTERNAL_RESPONSE_STATE_20260717")

SCOPED_ADDITIONS = (
    "code/ops/BUILD_EXTERNAL_RESPONSE_STATE_E_DRIVE_SYNC_RECEIPT.py",
    "code/ops/BUILD_BUILD_WEEK_HANDOFF_INTEGRITY_CONTROL.py",
    "code/ops/BUILD_DARPA_SN_26_97_PUBLIC_SUBMISSION_RECEIPT.py",
    "code/ops/BUILD_TRACTION_OPPORTUNITY_INTAKE_LEDGER.py",
    "code/ops/BUILD_TRACTION_FOLLOWUP_PACKET.py",
    "code/ops/BUILD_EVTIT_TECHNICAL_SPRINT_SCOPE_PACKET.py",
    "code/ops/BUILD_REVIEWER_CONCIERGE_PACKET.py",
    "code/ops/BUILD_AGENCY_SUBMISSION_ASSEMBLY_GATE.py",
    "tests/test_traction_opportunity_intake_ledger.py",
    "tests/test_traction_followup_packet.py",
    "tests/test_evtit_technical_sprint_scope_packet.py",
    "tests/test_reviewer_concierge_packet.py",
    "tests/test_agency_submission_assembly_gate.py",
    "tests/test_darpa_sn_26_97_public_submission_receipt.py",
    "tests/test_build_week_handoff_integrity_control.py",
    "tests/test_flowform_hardware_concept_asset.py",
    "tests/test_missionweave_dsip_action_gate.py",
    "assets/hardware/flowform_curved_motherboard_honeycomb_battery_v3_concept.json",
    "assets/hardware/flowform_curved_motherboard_honeycomb_battery_v3_concept.png",
    "out/ops/traction_opportunity_intake_ledger_latest.json",
    "dashboard/data/traction_opportunity_intake_ledger.json",
    "grant_submissions/funding_sprint_20260709/TRACTION_OPPORTUNITY_INTAKE_LEDGER_2026-07-09.md",
    "out/ops/traction_followup_packet_latest.json",
    "dashboard/data/traction_followup_packet.json",
    "grant_submissions/funding_sprint_20260709/EVTIT_TRACTION_FOLLOWUP_PACKET_2026-07-09.md",
    "out/ops/evtit_technical_sprint_scope_packet_latest.json",
    "dashboard/data/evtit_technical_sprint_scope_packet.json",
    "grant_submissions/funding_sprint_20260709/EVTIT_TECHNICAL_SPRINT_SCOPE_PACKET_2026-07-09.md",
    "out/ops/reviewer_concierge_packet_latest.json",
    "dashboard/data/reviewer_concierge_packet.json",
    "grant_submissions/funding_sprint_20260709/REVIEWER_CONCIERGE_PACKET_INDEX_2026-07-09.md",
    "out/ops/human_action_docket_latest.json",
    "dashboard/data/human_action_docket.json",
    "grant_submissions/funding_sprint_20260709/HUMAN_ACTION_DOCKET_2026-07-09.md",
    "out/ops/reviewer_decision_brief_latest.json",
    "dashboard/data/reviewer_decision_brief.json",
    "grant_submissions/funding_sprint_20260709/REVIEWER_DECISION_BRIEF_2026-07-09.md",
    "out/ops/customer_commercialization_packet_latest.json",
    "dashboard/data/customer_commercialization_packet.json",
    "grant_submissions/funding_sprint_20260709/CUSTOMER_COMMERCIALIZATION_PACKET_2026-07-09.md",
    "out/ops/reviewer_investor_fast_lane_router_latest.json",
    "dashboard/data/reviewer_investor_fast_lane_router.json",
    "grant_submissions/funding_sprint_20260709/REVIEWER_INVESTOR_FAST_LANE_ROUTER_2026-07-09.md",
    "out/ops/agency_submission_assembly_gate_latest.json",
    "dashboard/data/agency_submission_assembly_gate.json",
    "grant_submissions/funding_sprint_20260709/AGENCY_SUBMISSION_ASSEMBLY_GATE_2026-07-09.md",
    "grant_submissions/DLA26BZ03_NV011_MissionWeave/MISSIONWEAVE_DSIP_ACTION_GATE_2026-07-17.json",
    "grant_submissions/DLA26BZ03_NV011_MissionWeave/MISSIONWEAVE_DSIP_ACTION_GATE_2026-07-17.md",
    "grant_submissions/DLA26BZ03_NV011_MissionWeave/MISSIONWEAVE_DSIP_PORTAL_CHECKLIST_2026-07-17.md",
    "grant_submissions/funding_sprint_20260709/DARPA_SN_26_97_PUBLIC_SUBMISSION_RECEIPT_2026-07-17.json",
    "grant_submissions/funding_sprint_20260709/DARPA_SN_26_97_PUBLIC_SUBMISSION_RECEIPT_2026-07-17.md",
    "grant_submissions/OPENAI_BUILD_WEEK_20260721/BUILD_WEEK_HANDOFF_SOURCE_RECEIPT_2026-07-17.json",
    "grant_submissions/OPENAI_BUILD_WEEK_20260721/BUILD_WEEK_HANDOFF_INTEGRITY_CONTROL_2026-07-17.json",
    "grant_submissions/OPENAI_BUILD_WEEK_20260721/BUILD_WEEK_HANDOFF_INTEGRITY_CONTROL_2026-07-17.md",
)


def now_utc() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest().upper()


def read_json(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"Expected JSON object: {path}")
    return payload


def safe_source(relative_path: str) -> Path:
    candidate = Path(relative_path)
    if candidate.is_absolute() or ".." in candidate.parts:
        raise ValueError(f"Unsafe mirror source path: {relative_path}")
    source = (ROOT / candidate).resolve()
    if not source.is_relative_to(ROOT.resolve()) or not source.is_file():
        raise ValueError(f"Missing or out-of-root mirror source: {relative_path}")
    return source


def artifact_sources() -> list[str]:
    existing = read_json(RECEIPT)
    if existing.get("schema") != "lumencore.bounded_mirror_receipt.v1":
        raise ValueError("Existing bounded mirror receipt has the wrong schema")
    previous = [
        str(row.get("source"))
        for row in existing.get("artifacts", [])
        if isinstance(row, dict) and row.get("source")
    ]
    sources = list(dict.fromkeys([*previous, *SCOPED_ADDITIONS]))
    basenames = [Path(source).name.casefold() for source in sources]
    if len(basenames) != len(set(basenames)):
        raise ValueError("Flat E-drive mirror would overwrite duplicate basenames")
    return sources


def build_receipt(created_utc: str | None = None) -> dict[str, Any]:
    if not DESTINATION_ROOT.parent.exists():
        raise ValueError(f"E-drive mirror parent is unavailable: {DESTINATION_ROOT.parent}")
    DESTINATION_ROOT.mkdir(parents=True, exist_ok=True)

    artifacts = []
    for relative_path in artifact_sources():
        source = safe_source(relative_path)
        destination = (DESTINATION_ROOT / source.name).resolve()
        if not destination.is_relative_to(DESTINATION_ROOT.resolve()):
            raise ValueError(f"Unsafe mirror destination: {destination}")
        shutil.copy2(source, destination)
        source_hash = sha256_file(source)
        destination_hash = sha256_file(destination)
        hashes_match = source_hash == destination_hash
        bytes_match = source.stat().st_size == destination.stat().st_size
        if not hashes_match or not bytes_match:
            raise ValueError(f"Mirror verification failed: {relative_path}")
        artifacts.append(
            {
                "source": relative_path,
                "bytes": source.stat().st_size,
                "sha256": source_hash,
                "copy_sha256_matched": hashes_match,
            }
        )

    count = len(artifacts)
    return {
        "schema": "lumencore.bounded_mirror_receipt.v1",
        "created_utc": created_utc or now_utc(),
        "destination_root": DESTINATION_ROOT.as_posix(),
        "artifact_count": count,
        "all_sha256_matched_after_copy": True,
        "browser_navigation_performed": False,
        "private_founder_values_mirrored": False,
        "artifacts": artifacts,
        "claim_boundary": (
            f"This receipt proves only that {count} bounded response-control, deadline, reviewer-pipeline, "
            "test, hardware-concept, MissionWeave action-gate, and public-safe dashboard artifacts were "
            "copied to the stated E-drive directory with matching SHA-256 hashes. It does not prove portal "
            "submission, application acceptance, investor activity beyond cited written evidence, funding, "
            "selection, award, endorsement, external validation, technical performance, hardware feasibility, "
            "safety certification, or commercial readiness."
        ),
    }


def main() -> None:
    payload = build_receipt()
    RECEIPT.write_text(
        json.dumps(payload, indent=2, ensure_ascii=True) + "\n",
        encoding="utf-8",
    )
    print(
        json.dumps(
            {
                "status": "E_DRIVE_MIRROR_VERIFIED",
                "artifact_count": payload["artifact_count"],
                "destination_root": payload["destination_root"],
                "receipt": RECEIPT.relative_to(ROOT).as_posix(),
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
