from __future__ import annotations

import importlib.util
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "code" / "ops" / "BUILD_PORTAL_PREVIEW_RUNBOOK.py"


def load_module():
    spec = importlib.util.spec_from_file_location("portal_preview_runbook", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_portal_preview_runbook_links_exact_frozen_upload_artifacts():
    module = load_module()
    payload = module.build_runbook()

    assert payload["schema"] == "portal_preview_runbook_v1"
    assert payload["ready_for_upload_or_submit"] is False
    assert len(payload["freeze_signature_sha256"]) == 64
    assert len(payload["runbooks"]) == 2

    by_package = {row["package"]: row for row in payload["runbooks"]}
    assert set(by_package) == {"DICE", "HarborSentinel"}
    assert by_package["DICE"]["ready_for_preview"] is True
    assert by_package["HarborSentinel"]["ready_for_preview"] is True
    assert by_package["DICE"]["ready_for_upload_or_submit"] is False
    assert by_package["HarborSentinel"]["ready_for_upload_or_submit"] is False
    dice_candidates = "\n".join(row["path"] for row in by_package["DICE"]["upload_candidates"])
    harbor_candidates = "\n".join(row["path"] for row in by_package["HarborSentinel"]["upload_candidates"])
    assert "LumenCore_DICE_Abstract_WORKING_DRAFT.docx" in dice_candidates
    assert "NV063_VOLUME2_TECHNICAL_DRAFT_2026-06-19.docx" in harbor_candidates


def test_portal_preview_runbook_preserves_no_click_and_no_secret_rules():
    module = load_module()
    payload = module.build_runbook()
    rendered = module.render_markdown(payload)

    assert "Ready for upload or submit: False" in rendered
    assert "Stop before upload finalization" in rendered
    assert "MFA or one-time codes" in rendered
    assert "passwords" in rendered
    assert "workspace lock" in rendered
    assert "Fresh action-time approval" in rendered
    assert "submitter authority" in rendered
