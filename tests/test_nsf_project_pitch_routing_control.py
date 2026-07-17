import hashlib
import importlib.util
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "code" / "ops" / "BUILD_NSF_PROJECT_PITCH_ROUTING_CONTROL.py"
MANIFEST = (
    ROOT
    / "grant_submissions"
    / "NSF_Project_Pitch"
    / "NSF_PROJECT_PITCH_ROUTING_MANIFEST_2026-07-16.json"
)
MIRROR_RECEIPT = (
    ROOT
    / "grant_submissions"
    / "NSF_Project_Pitch"
    / "NSF_PROJECT_PITCH_ROUTING_E_DRIVE_SYNC_RECEIPT_2026-07-17.json"
)


def load_module():
    spec = importlib.util.spec_from_file_location("nsf_routing_control", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest().upper()


def test_manifest_matches_deterministic_routing_control():
    module = load_module()
    expected = module.build_manifest()
    actual = json.loads(MANIFEST.read_text(encoding="utf-8"))

    module.validate_manifest(actual)
    assert actual == expected


def test_listed_deadline_is_separate_from_current_access():
    module = load_module()
    manifest = module.build_manifest()
    full = manifest["full_proposal"]

    assert full["listed_deadlines"] == [
        "2026-07-27",
        "2026-11-04",
        "2027-03-04",
        "2027-07-07",
    ]
    assert full["nearest_listed_deadline"] == "2026-07-27"
    assert full["july_27_2026_currently_listed"] is True
    assert full["july_27_2026_reachable"] is False
    assert full["invitation_verified"] is False
    assert full["submission_allowed"] is False
    assert full["next_planning_target"] == "2026-11-04"


def test_project_pitch_remains_rolling_and_human_gated():
    module = load_module()
    pitch = module.build_manifest()["project_pitch"]

    assert pitch["deadline"] is None
    assert pitch["typical_response_time"] == "1-2 months"
    assert pitch["one_active_pitch_at_a_time"] is True
    assert pitch["final_submit_allowed_without_human"] is False


def test_bounded_mirror_receipt_matches_local_sources():
    receipt = json.loads(MIRROR_RECEIPT.read_text(encoding="utf-8-sig"))

    assert receipt["schema"] == "lumencore.bounded_mirror_receipt.v1"
    assert receipt["artifact_count"] == len(receipt["artifacts"]) == 14
    assert receipt["all_sha256_matched_after_copy"] is True
    assert receipt["browser_navigation_performed"] is False
    assert receipt["private_founder_values_mirrored"] is False

    for artifact in receipt["artifacts"]:
        source = ROOT / artifact["source"]
        assert source.is_file(), artifact["source"]
        assert source.stat().st_size == artifact["bytes"], artifact["source"]
        assert sha256_file(source) == artifact["sha256"], artifact["source"]
        assert artifact["copy_sha256_matched"] is True
