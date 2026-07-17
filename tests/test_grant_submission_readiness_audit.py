import importlib.util
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "code" / "ops" / "BUILD_GRANT_SUBMISSION_READINESS_AUDIT.py"


def load_module():
    spec = importlib.util.spec_from_file_location("grant_submission_readiness_audit", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_manifest_rehashes_canonical_evidence_runs():
    module = load_module()
    audit = module.build_audit()

    for package in audit["packages"]:
        for manifest in package["evidence_manifests"]:
            assert manifest["exists"], manifest
            assert manifest["expected"] > 0, manifest
            assert manifest["matched"] == manifest["expected"], manifest
            assert manifest["mismatches"] == [], manifest

    geometry = audit["geometry_registry"]
    assert geometry["matched"] == geometry["expected"]
    assert geometry["mismatches"] == []


def test_top_five_have_no_local_readiness_blockers():
    module = load_module()
    audit = module.build_audit()

    assert audit["posture"] == "LOCAL_READY_PORTAL_BLOCKED"
    assert audit["summary"]["local_blockers"] == 0
    assert audit["summary"]["portal_user_blockers"] > 0

    by_name = {package["name"]: package for package in audit["packages"]}
    assert by_name["DICE"]["render"]["ok"] is True
    assert by_name["HarborSentinel"]["render"]["ok"] is True
    dice_required = {row["path"] for row in by_name["DICE"]["required_artifacts"]}
    harbor_required = {row["path"] for row in by_name["HarborSentinel"]["required_artifacts"]}
    assert "grant_submissions/DICE_HR001126S0010/DICE_REFERENCE_RELEVANCE_MATRIX_2026-06-20.md" in dice_required
    assert "grant_submissions/DICE_HR001126S0010/DICE_EVIDENCE_SYNTHESIS_2026-06-20.md" in dice_required
    assert "grant_submissions/DICE_HR001126S0010/DICE_LIVE_BREADTH_REPLAY_2026-06-20.md" in dice_required
    assert "grant_submissions/LIVE_BREADTH_PROVENANCE_ANNEX_2026-06-21.md" in dice_required
    assert "grant_submissions/LIVE_BREADTH_PROVENANCE_ANNEX_2026-06-21.md" in harbor_required
    assert "grant_submissions/NV063_HarborSentinel/NV063_DSIP_ASSEMBLY_MAP_2026-07-16.md" in harbor_required
    assert "grant_submissions/NV063_HarborSentinel/NV063_DSIP_VOLUME1_PUBLIC_TEXT_2026-07-16.md" in harbor_required
    assert "grant_submissions/NV063_HarborSentinel/NV063_DSIP_VOLUME2_FINAL_CANDIDATE_2026-07-16.docx" in harbor_required
    assert "grant_submissions/NV063_HarborSentinel/NV063_DSIP_VOLUME3_COST_INPUTS_2026-07-16.md" in harbor_required
    assert "grant_submissions/NV063_HarborSentinel/NV063_DSIP_VOLUME5_WORKSHEET_2026-07-16.md" in harbor_required
    assert "grant_submissions/NV063_HarborSentinel/NV063_DSIP_PACKAGE_MANIFEST_2026-07-16.json" in harbor_required
    assert "grant_submissions/NV063_HarborSentinel/source_attachments/DoW_2026_SBIR_BAA_RELEASE_3_PREFACE.pdf" in harbor_required
    assert (
        by_name["HarborSentinel"]["render"]["render_dir"]
        == "grant_submissions/NV063_HarborSentinel/render_qa_20260716_dsip_candidate_v1"
    )
    assert by_name["HarborSentinel"]["render"]["png_count"] == 5
    assert "grant_submissions/NV063_HarborSentinel/NV063_DATA_SOURCE_ACCESS_AUDIT_2026-06-20.md" in harbor_required
    assert "grant_submissions/NV063_HarborSentinel/NV063_AIS_PILOT_SOURCE_REGISTRY_2026-06-20.md" in harbor_required
    assert "grant_submissions/NV063_HarborSentinel/NV063_AIS_PILOT_ACQUISITION_2026-06-20.md" in harbor_required
    assert "grant_submissions/NV063_HarborSentinel/NV063_AIS_HELDOUT_SPLIT_MANIFEST_2026-06-20.md" in harbor_required
    assert "grant_submissions/NV063_HarborSentinel/NV063_PUBLIC_AIS_GATE_2026-06-20.md" in harbor_required
    assert "grant_submissions/NV063_HarborSentinel/NV063_AIS_INJECTION_BENCHMARK_2026-06-20.md" in harbor_required
    assert "grant_submissions/NV063_HarborSentinel/NV063_AIS_REVIEW_BURDEN_PROFILE_2026-06-21.md" in harbor_required
    assert any(
        "controlled-injection benchmark ready" in fact
        for fact in by_name["HarborSentinel"]["verified_portal_facts"]
    )
    assert any(
        "AIS review-burden profile ready" in fact
        for fact in by_name["HarborSentinel"]["verified_portal_facts"]
    )
    assert any(
        "harbor_ais_review_burden" in manifest["run_dir"]
        for manifest in by_name["HarborSentinel"]["evidence_manifests"]
    )
    assert any(
        "DICE frozen live-breadth replay ready" in fact
        for fact in by_name["DICE"]["verified_portal_facts"]
    )
    assert any(
        "dice_live_breadth_replay" in manifest["run_dir"]
        for manifest in by_name["DICE"]["evidence_manifests"]
    )


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


def test_nsf_pitch_fields_stay_under_portal_limits():
    module = load_module()
    audit = module.build_audit()
    nsf = next(package for package in audit["packages"] if package["name"] == "NSF Project Pitch")

    assert set(nsf["nsf_fields"]) == set(module.NSF_LIMITS)
    for field, row in nsf["nsf_fields"].items():
        assert row["ok"], field
        assert row["characters"] <= row["limit"], field

    required = {row["path"] for row in nsf["required_artifacts"]}
    assert (
        "grant_submissions/NSF_Project_Pitch/PROJECT_PITCH_PORTAL_FIELDS_2026-07-16.md"
        in required
    )
    assert (
        "grant_submissions/NSF_Project_Pitch/NSF_PROJECT_PITCH_ROUTING_MANIFEST_2026-07-16.json"
        in required
    )

    routing = nsf["nsf_routing"]
    assert routing["schema"] == "lumencore.nsf_project_pitch_routing.v1"
    assert routing["project_pitch"]["deadline"] is None
    assert routing["project_pitch"]["final_submit_allowed_without_human"] is False
    assert routing["full_proposal"]["invitation_required"] is True
    assert routing["full_proposal"]["invitation_verified"] is False
    assert routing["full_proposal"]["submission_allowed"] is False
    assert routing["full_proposal"]["july_27_2026_reachable"] is False
    assert routing["full_proposal"]["july_27_2026_currently_listed"] is False
    assert routing["full_proposal"]["current_official_schedule_checked_on"] == "2026-07-16"
    assert routing["full_proposal"]["current_official_schedule_deadline"] == "2026-11-04"
    assert routing["full_proposal"]["next_planning_target"] == "2026-11-04"


def test_nsf_pitch_is_claim_bounded_and_contains_required_reviewer_content():
    packet = (
        ROOT
        / "grant_submissions"
        / "NSF_Project_Pitch"
        / "PROJECT_PITCH_PORTAL_FIELDS_2026-07-16.md"
    ).read_text(encoding="utf-8")
    lowered = packet.lower()

    for required in (
        "high-risk technical innovation",
        "leakage-resistant",
        "abstention",
        "initial customer",
        "competitors include",
        "team plan",
        "negative result",
        "originated in repeated internal benchmark work",
    ):
        assert required in lowered

    for stale_metric in ("29-source", "25 measured", "2,580"):
        assert stale_metric not in packet

    assert "does not claim an NSF invitation" in packet
    assert "does not claim" in lowered
    assert "july 27 is not listed on the current schedule" in lowered
