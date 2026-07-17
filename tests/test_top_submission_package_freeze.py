from __future__ import annotations

import importlib.util
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "code" / "ops" / "BUILD_TOP_SUBMISSION_PACKAGE_FREEZE.py"


def load_module():
    spec = importlib.util.spec_from_file_location("top_submission_package_freeze", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_freeze_hashes_dice_and_harbor_upload_candidates_without_upload_approval():
    module = load_module()
    payload = module.build_freeze()

    assert payload["schema"] == "top_submission_package_freeze_v1"
    assert payload["source_posture"] == "LOCAL_READY_PORTAL_BLOCKED"
    assert payload["package_count"] == 2
    assert payload["all_required_artifacts_present"] is True
    assert payload["ready_for_portal_upload"] is False
    assert len(payload["freeze_signature_sha256"]) == 64

    packages = {package["name"]: package for package in payload["packages"]}
    assert set(packages) == {"DICE", "HarborSentinel"}
    dice_roles = {artifact["role"] for artifact in packages["DICE"]["artifacts"]}
    assert "evidence_synthesis" in dice_roles
    assert "frozen_live_replay_evidence" in dice_roles
    assert "provenance_annex" in dice_roles
    harbor_roles = {artifact["role"] for artifact in packages["HarborSentinel"]["artifacts"]}
    assert "review_burden_evidence" in harbor_roles
    assert "provenance_annex" in harbor_roles
    for package in packages.values():
        assert package["local_ready"] is True
        assert package["ready_for_portal_upload"] is False
        assert package["portal_user_blocker_count"] > 0
        assert package["upload_candidates"]
        for artifact in package["artifacts"]:
            assert artifact["exists"], artifact["path"]
            assert artifact["bytes"] > 0
            assert len(artifact["sha256"]) == 64


def test_freeze_markdown_preserves_submission_boundary_and_current_harbor_render():
    module = load_module()
    payload = module.build_freeze()
    rendered = module.render_markdown(payload)

    assert "does not approve upload" in rendered
    assert "Ready for portal upload: False" in rendered
    assert "LumenCore_DICE_Abstract_WORKING_DRAFT.docx" in rendered
    assert "NV063_VOLUME2_TECHNICAL_DRAFT_2026-06-19.docx" in rendered
    assert "LIVE_BREADTH_PROVENANCE_ANNEX_2026-06-21.md" in rendered
    assert "render_qa_20260716_dsip_candidate_v1" in rendered
    assert "render_qa_20260620_baselines_v1" not in rendered
    assert "render_qa_20260620_injection_v2" not in rendered
