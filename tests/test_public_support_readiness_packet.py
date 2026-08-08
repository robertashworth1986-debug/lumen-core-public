from __future__ import annotations

import importlib.util
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "code" / "ops" / "BUILD_PUBLIC_SUPPORT_READINESS_PACKET.py"
PUBLIC_MD = ROOT / "docs" / "PUBLIC_SUPPORT_AND_REVIEWER_READINESS_2026-06-20.md"
PUBLIC_JSON = ROOT / "dashboard" / "data" / "public_support_readiness_packet.json"


def load_module():
    spec = importlib.util.spec_from_file_location("public_support_readiness_packet", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_public_support_packet_is_bounded_and_source_backed():
    module = load_module()
    payload = module.build_payload()

    assert payload["schema"] == "public_support_readiness_packet_v1"
    assert payload["public_posture"]["local_blockers"] == 0
    assert payload["public_posture"]["portal_user_blockers"] > 0
    assert payload["public_posture"]["submitted_by_feed"] == 0
    assert len(payload["official_support_lanes"]) >= 5
    urls = {lane["url"] for lane in payload["official_support_lanes"]}
    assert "https://www.sba.gov/local-assistance/federal-contracting-assistance" in urls
    assert "https://business.defense.gov/Programs/Cyber-Security-Resources/" in urls
    assert "https://www.sbir.gov/community/fast" in urls
    assert "does not prove portal authority" in payload["boundary"]
    assert any("HarborSentinel" in item for item in payload["strong_public_evidence"])
    assert any("provenance-gated" in item for item in payload["strong_public_evidence"])
    breadth_claims = [
        item for item in payload["strong_public_evidence"] if "provenance-gated" in item
    ]
    assert breadth_claims
    assert "Economic estimates are omitted" in breadth_claims[0]
    assert "$" not in breadth_claims[0]
    assert payload["source_artifacts"]["live_breadth_provenance_gate"].endswith(
        "LIVE_BREADTH_PROVENANCE_GATE_CAPSULE_2026-06-21.md"
    )
    assert payload["source_artifacts"]["live_breadth_provenance_gate_json"].endswith(
        "live_breadth_provenance_gate.json"
    )


def test_public_support_markdown_and_snapshot_avoid_private_claims():
    module = load_module()
    payload = module.build_payload()
    markdown = module.render_markdown(payload)
    serialized = json.dumps(payload).lower() + markdown.lower()

    assert "PUBLIC_SUPPORT_AND_REVIEWER_READINESS_2026-06-20.md".lower() not in serialized
    assert "guaranteed funding" in serialized
    assert "do not claim" in markdown.lower()
    assert "provenance-gated" in serialized
    assert "context-only" in serialized
    assert "submitted by public feed: 0" in markdown.lower()
    assert "uei" in serialized
    assert "cage" in serialized
    assert ("sk-" + "proj") not in serialized
    assert "ready_to_submit\": true" not in serialized
    assert "field validated" in serialized


def test_generated_public_support_files_exist_after_builder_run():
    assert PUBLIC_MD.exists()
    assert PUBLIC_JSON.exists()
    payload = json.loads(PUBLIC_JSON.read_text(encoding="utf-8"))
    assert payload["schema"] == "public_support_readiness_packet_v1"
    assert payload["public_posture"]["submitted_by_feed"] == 0
