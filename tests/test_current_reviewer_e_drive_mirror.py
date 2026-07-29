from __future__ import annotations

import importlib.util
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "code" / "ops" / "BUILD_CURRENT_REVIEWER_E_DRIVE_MIRROR.py"


def load_module():
    spec = importlib.util.spec_from_file_location(
        "current_reviewer_e_drive_mirror", SCRIPT
    )
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_mirror_allowlist_is_current_and_excludes_private_inputs():
    module = load_module()
    artifacts = module.collect_artifacts()
    paths = {row["path"] for row in artifacts}

    assert len(artifacts) >= 75
    assert len(paths) == len(artifacts)
    assert "out/ops/current_reviewer_front_door_latest.json" in paths
    assert (
        "docs/receipts/CURRENT_REVIEWER_PUBLIC_ARTIFACT_MANIFEST_2026-07-29.json"
    ) in paths
    assert "out/ops/source_native_family_baseline_ledger_latest.json" in paths
    assert "out/ops/market_signal_source_native_benchmark_latest.json" in paths
    assert "dashboard/data/market_signal_source_native_benchmark.json" in paths
    assert "dashboard/data/source_native_family_baseline_ledger.json" in paths
    assert (
        "output/pdf/LumenCore_Evidence_to_Pilot_Deck_CURRENT_REVIEW_REQUIRED.pdf"
    ) in paths
    assert "out/ops/PUBLIC_RELEASE_SYNC_PLAN_2026-07-18.json" in paths
    assert "deploy/REPAIR_LUMA_GATEWAY_MODULE.ps1" in paths
    assert "docs/VPS_GATEWAY_RECOVERY_2026-07-29.md" in paths
    assert "out/ops/live_domain_service_contract_latest.json" in paths
    assert "out/ops/live_domain_proof_feed_deploy_bundle_latest.json" in paths
    assert "out/ops/workspace_secret_value_audit_latest.json" in paths
    assert "code/ops/AUDIT_WORKSPACE_SECRET_VALUES.py" in paths
    assert (
        "grant_submissions/NASHVILLE_EC_FALL_2026/"
        "NASHVILLE_EC_TAKEOFF_ONBOARDING_REVIEW_PACKET_2026-07-29.md"
    ) in paths
    assert (
        "grant_submissions/funding_sprint_20260709/"
        "OFFICIAL_INBOUND_STATUS_EVENT_REGISTER_2026-07-25.json"
    ) in paths
    assert any(
        path.startswith(".deploy_stage/live_domain_proof_feeds_")
        and path.endswith(".tgz")
        for path in paths
    )
    assert (
        "grant_submissions/NSF_Project_Pitch/"
        "NSF_PROJECT_PITCH_ROUTING_MANIFEST_2026-07-29.json"
    ) in paths
    assert (
        "output/pdf/LumenCore_ERDC_SDC_Solution_Brief_PUBLIC_DRAFT_2026-07-29.pdf"
    ) in paths
    assert (
        "grant_submissions/LAUNCHTN_3686_PITCH_2026/"
        "LAUNCHTN_3686_APPLICATION_MANIFEST_2026-07-29.json"
    ) in paths
    assert (
        "grant_submissions/funding_sprint_20260709/"
        "DOE_FY26_GENESIS_PHASE1_PITCH_PACKET_2026-07-29.json"
    ) in paths
    assert "code/watchers/doe_fy26_watcher.py" in paths
    assert "out/grants/doe_fy26_watch.json" in paths
    assert not any("/private/" in f"/{path.lower()}/" for path in paths)
    assert not any(path.lower().endswith(".env") for path in paths)
    assert not any(
        path.endswith("LUMENCORE_3686_FINANCIAL_MODEL_2026-07-17.xlsx")
        for path in paths
    )
    assert all(len(row["sha256"]) == 64 for row in artifacts)


def test_mirror_copies_with_hash_parity_and_remains_human_gated(tmp_path: Path):
    module = load_module()
    destination = tmp_path / "mirror"
    receipt = tmp_path / "receipt.json"

    payload = module.mirror(
        destination,
        receipt_path=receipt,
        generated_utc="2026-07-29T18:00:00Z",
    )

    assert payload["status"] == (
        "CURRENT_REVIEWER_E_DRIVE_MIRROR_COMPLETE_HUMAN_RELEASE_REQUIRED"
    )
    assert payload["all_copy_sha256_matched"] is True
    assert payload["private_values_mirrored"] is False
    assert payload["unapproved_launchtn_financial_model_mirrored"] is False
    assert payload["external_release_authorized"] is False
    assert payload["final_submission_allowed_without_human"] is False
    assert payload["artifact_count"] == payload["copied_count"]
    assert payload["unchanged_count"] == 0
    assert all(row["copy_sha256_matched"] for row in payload["artifacts"])
    assert receipt.is_file()
    mirrored_receipt = destination / "_receipts" / receipt.name
    assert mirrored_receipt.is_file()
    assert json.loads(receipt.read_text(encoding="utf-8"))["claim_boundary"].startswith(
        "This receipt proves only local file custody"
    )

    module.check(destination, receipt)
