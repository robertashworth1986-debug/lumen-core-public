from __future__ import annotations

import importlib.util
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "code" / "ops" / "BUILD_EPRI_OPAI_BRAND_ASSET_PACKET.py"


def load_module():
    spec = importlib.util.spec_from_file_location("epri_brand_packet", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_packet_seals_both_logo_variants_without_send_authority():
    module = load_module()
    payload = module.build_packet()

    assert payload["status"] == "ASSETS_READY_HUMAN_SEND_REQUIRED"
    assert payload["summary"] == {
        "asset_count": 2,
        "ready_asset_count": 2,
        "all_assets_ready": True,
        "attachment_count_if_approved": 2,
    }
    assert {row["intended_background"] for row in payload["assets"]} == {
        "dark",
        "light",
    }
    for row in payload["assets"]:
        assert row["ready"] is True
        assert row["width"] == 1024
        assert row["height"] == 1024
        assert row["bytes"] > 0
        assert len(row["sha256"]) == 64

    assert payload["controls"]["send_performed"] is False
    assert payload["controls"]["gmail_draft_created"] is False
    assert (
        payload["controls"]["external_send_allowed_without_human"] is False
    )
    assert payload["controls"]["fresh_duplicate_check_required"] is True

    unhashed = {
        key: value for key, value in payload.items() if key != "packet_sha256"
    }
    assert payload["packet_sha256"] == module.canonical_sha256(unhashed)
    serialized = json.dumps(payload).lower()
    assert "password" not in serialized
    assert "meeting id" not in serialized
    assert "passcode" not in serialized
