from __future__ import annotations

import copy
import importlib.util
import json
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "code" / "ops" / "BUILD_PITCH_DECK_GOVERNANCE.py"
CONFIG = ROOT / "config" / "pitch_deck_governance_v1.json"
AS_OF_UTC = "2026-07-29T10:00:00Z"


def load_module():
    spec = importlib.util.spec_from_file_location("pitch_deck_governance", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def load_config() -> dict:
    return json.loads(CONFIG.read_text(encoding="utf-8"))


def test_config_is_fail_closed_and_has_one_current_deck():
    module = load_module()
    config = load_config()
    module.validate_config(config)

    assert config["controls"] == module.EXPECTED_CONTROLS
    assert config["controls"]["external_release_default"] is False
    assert config["controls"]["action_time_human_approval_required"] is True
    assert (
        sum(
            row["status"] == "CURRENT_HUMAN_REVIEW_REQUIRED"
            for row in config["artifacts"]
        )
        == 1
    )


def test_every_discovered_pptx_is_exactly_registered_or_quarantined():
    module = load_module()
    config = load_config()

    exact = {row["path"] for row in config["artifacts"]}
    discovered = set(module.discover_pptx(config))
    unregistered = [
        path
        for path in discovered - exact
        if module.legacy_collection_for(path, config["legacy_collections"]) is None
    ]
    assert unregistered == []
    assert len(discovered) >= 29


def test_registry_blocks_release_and_separates_legacy_decks():
    module = load_module()
    payload = module.build_registry(CONFIG, as_of_utc=AS_OF_UTC)

    assert payload["status"] == "GOVERNED_CURRENT_DECK_WITH_ARCHIVED_LEGACY"
    assert payload["summary"]["registered_pptx_count"] >= 29
    assert payload["summary"]["registered_exact_pptx_count"] == 5
    assert payload["summary"]["legacy_collection_file_count"] >= 24
    assert payload["summary"]["current_deck_count"] == 1
    assert payload["summary"]["current_pdf_companion_count"] == 1
    assert payload["summary"]["historical_or_template_count"] >= 28
    assert payload["summary"]["external_release_authorized_count"] == 0
    assert payload["summary"]["send_eligible_count"] == 0
    assert not any(payload["blockers"].values())


def test_current_deck_has_current_evidence_and_source_notes():
    module = load_module()
    payload = module.build_registry(CONFIG, as_of_utc=AS_OF_UTC)
    current = payload["current_deck"]

    assert current["slide_count"] == 11
    assert current["notes_with_sources_count"] == 11
    assert current["missing_text_markers"] == []
    assert current["present_banned_text_markers"] == []
    assert len(current["sha256"]) == 64
    assert len(current["dependencies"]) == 6
    assert any(
        receipt["path"] == "out/ops/market_signal_source_native_benchmark_latest.json"
        for receipt in current["dependencies"]
    )


def test_current_pdf_companion_matches_current_deck_and_stays_fail_closed():
    module = load_module()
    payload = module.build_registry(CONFIG, as_of_utc=AS_OF_UTC)
    current = payload["current_deck"]
    companion = payload["current_pdf_companion"]

    assert companion["path"] == (
        "output/pdf/LumenCore_Evidence_to_Pilot_Deck_CURRENT_REVIEW_REQUIRED.pdf"
    )
    assert companion["page_count"] == current["slide_count"] == 11
    assert companion["source_pptx_path"] == current["path"]
    assert companion["source_pptx_sha256"] == current["sha256"]
    assert companion["missing_text_markers"] == []
    assert companion["external_release_authorized"] is False
    assert companion["send_eligible"] is False
    assert companion["status"] == "CURRENT_PDF_COMPANION_HUMAN_REVIEW_REQUIRED"
    assert len(companion["sha256"]) == 64


def test_relaxed_release_or_duplicate_path_is_rejected():
    module = load_module()
    relaxed = load_config()
    relaxed["artifacts"][0]["external_release_authorized"] = True
    with pytest.raises(module.DeckGovernanceError, match="block external release"):
        module.validate_config(relaxed)

    duplicate = copy.deepcopy(load_config())
    duplicate["artifacts"][1]["path"] = duplicate["artifacts"][0]["path"]
    with pytest.raises(module.DeckGovernanceError, match="Duplicate"):
        module.validate_config(duplicate)
