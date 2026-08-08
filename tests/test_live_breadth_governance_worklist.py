from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[1]
OPS = ROOT / "code" / "ops"
SCRIPT = OPS / "build_live_breadth_governance_worklist.py"


def load_module():
    sys.path.insert(0, str(OPS))
    try:
        spec = importlib.util.spec_from_file_location("live_breadth_governance_worklist", SCRIPT)
        module = importlib.util.module_from_spec(spec)
        assert spec.loader is not None
        spec.loader.exec_module(module)
        return module
    finally:
        sys.path.pop(0)


def registry() -> dict:
    return {
        "generated_utc": "2026-08-08T09:00:00+00:00",
        "rows": [
            {
                "source": "PRIVATE_PROVIDER_A",
                "sector": "energy",
                "enabled": True,
                "measured": True,
                "probe_ok": True,
                "rows": 150,
                "last_probe_utc": "2026-08-08T09:30:00+00:00",
                "env_names": ["PRIVATE_API_KEY"],
                "translated_value": {"year": 999999999},
            }
        ],
    }


def complete_item(item: dict) -> None:
    item.update(
        {
            "rights_status": "verified_for_review",
            "rights_evidence_url": "https://example.test/authorized-terms",
            "relevance_status": "verified",
            "intended_decision": "energy-demand forecast replay",
            "minimum_rows": 100,
            "minimum_rows_basis": "locked replay requires 100 observations",
            "max_age_hours": 2,
            "max_age_basis": "decision SLA is two hours",
            "dataset_snapshot_sha256": "a" * 64,
            "dataset_snapshot_observed_utc": "2026-08-08T09:30:00+00:00",
        }
    )
    item["blockers"] = []
    item["ready_for_protocol_review"] = True


def reseal_worklist(module, worklist: dict) -> None:
    worklist["summary"] = module.summarize_worklist(worklist)
    worklist["integrity"]["worklist_sha256"] = module.worklist_sha256(worklist)


def test_worklist_is_private_and_omits_credentials_and_economic_fields() -> None:
    module = load_module()
    worklist = module.build_worklist(
        registry(),
        registry_sha256="b" * 64,
        generated_utc="2026-08-08T10:00:00+00:00",
    )
    serialized = json.dumps(worklist).lower()

    assert worklist["classification"] == "PRIVATE_DO_NOT_PUBLISH"
    assert worklist["summary"]["sources"] == 1
    assert worklist["summary"]["sources_blocked"] == 1
    assert worklist["summary"]["blocking_fields"] == 10
    assert "private_provider_a" in serialized
    assert "private_api_key" not in serialized
    assert "translated_value" not in serialized
    assert "999999999" not in serialized
    assert module.verify_worklist(worklist) is True


def test_incomplete_worklist_cannot_be_promoted() -> None:
    module = load_module()
    worklist = module.build_worklist(
        registry(),
        registry_sha256="b" * 64,
        generated_utc="2026-08-08T10:00:00+00:00",
    )
    with pytest.raises(ValueError, match="approval"):
        module.promote_worklist(worklist)


def test_completed_and_approved_worklist_promotes_to_sealed_governance() -> None:
    module = load_module()
    worklist = module.build_worklist(
        registry(),
        registry_sha256="b" * 64,
        generated_utc="2026-08-08T10:00:00+00:00",
    )
    complete_item(worklist["items"][0])
    worklist["registry_max_age_hours"] = 2
    worklist["protocol_review"] = {
        "approval_status": "approved",
        "reviewed_by_role": "data_governance_owner",
        "reviewed_utc": "2026-08-08T09:45:00+00:00",
        "review_note": "Reviewed against authorized terms and replay need.",
    }
    reseal_worklist(module, worklist)

    governance = module.promote_worklist(worklist)
    validation = module.public_manifest.validate_governance(governance, "b" * 64)
    manifest = module.public_manifest.build_manifest(
        registry(),
        registry_sha256="b" * 64,
        governance=governance,
        generated_utc="2026-08-08T10:00:00+00:00",
    )

    assert validation["valid"] is True
    assert governance["protocol"]["worklist_sha256"] == worklist["integrity"]["worklist_sha256"]
    assert manifest["summary"]["review_ready_sources"] == 1
    assert manifest["claim_gate"]["review_ready_source_count_claim_allowed"] is True


def test_tampered_worklist_and_governance_are_rejected() -> None:
    module = load_module()
    worklist = module.build_worklist(
        registry(),
        registry_sha256="b" * 64,
        generated_utc="2026-08-08T10:00:00+00:00",
    )
    worklist["items"][0]["minimum_rows"] = 1
    assert module.verify_worklist(worklist) is False
    with pytest.raises(ValueError, match="integrity"):
        module.promote_worklist(worklist)


def test_registry_hash_mismatch_invalidates_governance() -> None:
    module = load_module()
    governance = module.public_manifest.seal_governance(
        {
            "schema": "public_live_breadth_governance_v1",
            "registry_sha256": "a" * 64,
            "registry_max_age_hours": 2,
            "protocol": {
                "approval_status": "approved",
                "reviewed_by_role": "data_governance_owner",
                "reviewed_utc": "2026-08-08T09:45:00+00:00",
                "worklist_sha256": "c" * 64,
            },
            "sources": {"PRIVATE_PROVIDER_A": {}},
        }
    )
    validation = module.public_manifest.validate_governance(governance, "b" * 64)
    assert validation["valid"] is False
    assert "registry_hash_mismatch" in validation["issues"]
