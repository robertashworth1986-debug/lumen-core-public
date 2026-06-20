import importlib.util
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
    assert "grant_submissions/NV063_HarborSentinel/NV063_DATA_SOURCE_ACCESS_AUDIT_2026-06-20.md" in harbor_required
    assert "grant_submissions/NV063_HarborSentinel/NV063_AIS_PILOT_SOURCE_REGISTRY_2026-06-20.md" in harbor_required
    assert "grant_submissions/NV063_HarborSentinel/NV063_AIS_PILOT_ACQUISITION_2026-06-20.md" in harbor_required
    assert "grant_submissions/NV063_HarborSentinel/NV063_AIS_HELDOUT_SPLIT_MANIFEST_2026-06-20.md" in harbor_required
    assert "grant_submissions/NV063_HarborSentinel/NV063_PUBLIC_AIS_GATE_2026-06-20.md" in harbor_required


def test_nsf_pitch_fields_stay_under_portal_limits():
    module = load_module()
    audit = module.build_audit()
    nsf = next(package for package in audit["packages"] if package["name"] == "NSF Project Pitch")

    assert set(nsf["nsf_fields"]) == set(module.NSF_LIMITS)
    for field, row in nsf["nsf_fields"].items():
        assert row["ok"], field
        assert row["characters"] <= row["limit"], field
