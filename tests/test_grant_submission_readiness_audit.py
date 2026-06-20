from __future__ import annotations

import importlib.util
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "code" / "ops" / "BUILD_GRANT_SUBMISSION_READINESS_AUDIT.py"
PUBLIC_SNAPSHOT = ROOT / "dashboard" / "data" / "grant_readiness_status.json"


def load_module():
    spec = importlib.util.spec_from_file_location("grant_submission_readiness_audit", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_public_snapshot_preserves_submission_boundaries():
    snapshot = json.loads(PUBLIC_SNAPSHOT.read_text(encoding="utf-8"))

    assert snapshot["schema"] == "grant_dashboard_status_feed_v1"
    assert snapshot["summary"]["local_blockers"] == 0
    assert snapshot["summary"]["portal_user_blockers"] > 0
    assert snapshot["summary"]["submitted_by_feed"] == 0
    assert any("No grant is marked submitted" in item for item in snapshot["claim_boundaries"])
    assert "raw_file_path" not in snapshot["harbor"]["ais_acquisition"]


def test_readiness_audit_is_honest_without_private_artifacts():
    module = load_module()
    audit = module.build_audit()

    assert audit["schema"] == "grant_submission_readiness_audit_v1"
    assert audit["summary"]["packages"] == 5
    assert audit["posture"] in {"LOCAL_READY_PORTAL_BLOCKED", "LOCAL_BLOCKED"}

    if audit["posture"] == "LOCAL_READY_PORTAL_BLOCKED":
        assert audit["summary"]["local_blockers"] == 0
        assert audit["summary"]["portal_user_blockers"] > 0
    else:
        assert audit["summary"]["local_blockers"] > 0


def test_sam_active_capture_clears_only_entity_status_blocker(tmp_path):
    module = load_module()
    sam_capture = tmp_path / "sam_capture.json"
    sam_capture.write_text(
        json.dumps(
            {
                "schema": "sam_gov_entity_status_capture_v1",
                "registration_status": "Active Registration",
                "uei": "TESTUEI",
                "cage_ncage": "TESTCAGE",
                "purpose_of_registration": "All Awards",
                "expiration_date": "2026-08-30",
            }
        ),
        encoding="utf-8",
    )
    module.SAM_CAPTURE_JSON = sam_capture

    dice = module.package_audit("DICE", module.TOP5["DICE"])
    blockers = "\n".join(dice["portal_user_blockers"])

    assert "SAM.gov entity status/linkage must be verified." not in blockers
    assert "BAAT account, organization profile, and submitter authority are unverified." in blockers
    assert any(
        "SAM.gov active registration verified from signed-in workspace" in fact
        for fact in dice["verified_portal_facts"]
    )
