from __future__ import annotations

import importlib.util
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "code" / "ops" / "BUILD_DICE_SUBMISSION_LOCK_PACKET.py"


def load_module():
    spec = importlib.util.spec_from_file_location("dice_submission_lock_packet", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_dice_lock_packet_has_no_local_blockers():
    module = load_module()
    packet = module.build_packet()

    assert packet["posture"] == "LOCAL_LOCKED_PORTAL_BLOCKED"
    assert packet["local_blockers"] == []
    assert packet["portal_user_blockers"]
    assert "does not approve upload" in packet["claim_boundary"]
    artifact_paths = {row["path"] for row in packet["artifacts"]}
    assert "grant_submissions/DICE_HR001126S0010/DICE_EVIDENCE_SYNTHESIS_2026-06-20.md" in artifact_paths
    assert "grant_submissions/DICE_HR001126S0010/DICE_LIVE_BREADTH_REPLAY_2026-06-20.md" in artifact_paths


def test_dice_lock_packet_preserves_docx_and_render_guards():
    module = load_module()
    packet = module.build_packet()
    text = packet["docx_checks"]["visible_text"]
    parts = packet["docx_checks"]["parts"]
    render = packet["render_check"]

    assert parts["zip_ok"] is True
    assert parts["forbidden_parts_present"] == []
    assert parts["forbidden_prefix_parts_present"] == []
    assert parts["stale_relationship_or_content_type_refs"] == []
    assert text["working_draft_warning_present"] is True
    assert all(text["required_sections_present"].values())
    assert text["visible_url_count"] == 12
    assert text["visible_urls_with_trailing_punctuation"] == []
    assert text["placeholder_hits"] == []
    assert text["rom_cost_boundary_present"] is True
    assert render["ok"] is True
    assert render["page_png_count"] == 7
