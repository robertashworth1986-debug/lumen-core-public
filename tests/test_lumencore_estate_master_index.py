from __future__ import annotations

import csv
import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PAYLOAD = ROOT / "out" / "ops" / "lumencore_estate_master_index_latest.json"
INVENTORY = ROOT / "out" / "ops" / "lumencore_estate_file_inventory_latest.csv"
MANIFEST = ROOT / "out" / "ops" / "lumencore_estate_master_index_manifest_latest.json"


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def load_payload() -> dict:
    assert PAYLOAD.exists(), "Run code/ops/BUILD_LUMENCORE_ESTATE_MASTER_INDEX.py before this test."
    return json.loads(PAYLOAD.read_text(encoding="utf-8"))


def test_estate_master_index_covers_managed_workspace_and_inventory_csv():
    payload = load_payload()
    summary = payload["summary"]

    assert payload["schema"] == "lumencore_estate_master_index_v2"
    assert payload["status"] == "LUMENCORE_ESTATE_MASTER_INDEX_READY"
    assert summary["managed_file_count"] > 50_000
    assert summary["managed_total_bytes"] > 1_000_000_000
    assert summary["asset_class_count"] >= 8
    assert summary["custody_tier_count"] >= 6
    assert summary["concept_tag_count"] >= 8
    assert summary["named_concept_count"] == 6
    assert summary["content_sha256_file_count"] > 1_000
    assert (
        summary["content_sha256_reused_count"]
        + summary["content_sha256_computed_count"]
        == summary["content_sha256_file_count"]
    )
    assert summary["content_sha256_reused_count"] > 1_000
    assert summary["large_file_deferred_content_hash_count"] > 0
    assert summary["sensitive_metadata_only_count"] > 0
    assert summary["secret_content_indexed"] is False
    assert summary["sensitive_paths_redacted_from_public_payload"] is True
    assert summary["generated_outputs_excluded_from_inventory"] is True
    assert len(summary["inventory_chain_sha256"]) == 64
    assert INVENTORY.exists()
    assert summary["full_inventory_csv_bytes"] == INVENTORY.stat().st_size
    assert summary["inventory_csv_sha256"] == sha256_file(INVENTORY)
    assert len(payload["estate_index_sha256"]) == 64

    with INVENTORY.open(newline="", encoding="utf-8") as handle:
        row_count = sum(1 for _ in csv.DictReader(handle))
    assert row_count == summary["managed_file_count"]

    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    assert manifest["schema"] == "lumencore_estate_output_manifest_v1"
    assert manifest["estate_index_sha256"] == payload["estate_index_sha256"]
    assert manifest["inventory_chain_sha256"] == summary["inventory_chain_sha256"]
    assert manifest["self_reference_excluded"] is True
    for relative_path, record in manifest["files"].items():
        path = ROOT / relative_path
        assert path.exists()
        assert record["sha256"] == sha256_file(path)
        assert record["size_bytes"] == path.stat().st_size


def test_estate_master_index_classifies_concepts_and_keeps_final_gates_closed():
    payload = load_payload()
    summary = payload["summary"]
    concepts = {row["concept_id"]: row for row in payload["concept_registry"]}
    named = {row["concept_id"]: row for row in payload["named_concepts"]}

    for concept_id in [
        "agency_protocol",
        "proof_stack",
        "ip_patent",
        "quant_trading",
        "geometry_engine",
        "live_source",
    ]:
        assert concept_id in concepts
        assert concepts[concept_id]["file_count"] > 0
        assert len(concepts[concept_id]["concept_sha256"]) == 64

    assert "proof_to_pilot_os" in named
    assert "luma_jet_skin_suity_lane" in named
    assert summary["final_submission_allowed_without_human"] is False
    assert summary["legal_or_ip_action_allowed_without_human"] is False
    assert summary["live_trading_allowed"] is False
    assert payload["audit_rules"]["every_managed_file_inventory"] is True
    assert payload["audit_rules"]["secret_contents_not_published"] is True
    assert payload["audit_rules"]["public_payload_redacts_sensitive_paths"] is True
    assert payload["audit_rules"]["generated_outputs_excluded_to_prevent_self_reference"] is True
    assert payload["audit_rules"]["full_inventory_csv_is_local_custody_artifact"] is True
    assert all("relative_path" not in row for row in payload["sensitive_metadata_only_examples"])
