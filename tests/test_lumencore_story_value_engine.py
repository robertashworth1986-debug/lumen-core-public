from __future__ import annotations

import importlib.util
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = ROOT / "code" / "social" / "build_lumencore_story_value_engine.py"
POLICY_PATH = ROOT / "config" / "lumencore_story_value_policy_v1.json"


def _load_module():
    spec = importlib.util.spec_from_file_location("build_lumencore_story_value_engine", MODULE_PATH)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _profile(*, privacy_max: float = 0.2) -> dict[str, object]:
    return {
        "weights": {
            "proof_binding": 0.4,
            "narrative_strength": 0.2,
            "visual_strength": 0.1,
            "conversion_alignment": 0.1,
            "rights_confidence": 0.1,
            "reusability": 0.05,
            "freshness": 0.05,
        },
        "penalties": {
            "privacy_risk": 0.3,
            "unsupported_claim_risk": 0.3,
            "provenance_ambiguity": 0.1,
        },
        "hard_gates": {
            "allowed_rights_statuses": ["cleared", "user_owned"],
            "privacy_risk_max": privacy_max,
            "unsupported_claim_risk_max": 0.25,
            "proof_binding_min_for_proof_claim": 0.6,
        },
        "thresholds": {"feature_min": 70.0, "support_min": 45.0, "hold_min": 20.0},
    }


def _spec(module, **overrides):
    raw = {
        "asset_id": "sample",
        "content_role": "narrative",
        "rights_status": "cleared",
        "metrics": {
            "proof_binding": 0.9,
            "narrative_strength": 0.9,
            "visual_strength": 0.9,
            "conversion_alignment": 0.8,
            "rights_confidence": 1.0,
            "reusability": 0.8,
            "freshness": 1.0,
            "privacy_risk": 0.0,
            "unsupported_claim_risk": 0.0,
            "provenance_ambiguity": 0.0,
        },
    }
    raw.update(overrides)
    return module._normalize_spec(raw)


def test_privacy_gate_freezes_even_a_high_scoring_asset() -> None:
    module = _load_module()
    spec = _spec(module)
    spec["metrics"]["privacy_risk"] = 0.21
    score, disposition, reasons = module.score_asset(spec, _profile(privacy_max=0.2))
    assert score > 0
    assert disposition == "FREEZE_PUBLIC_SURFACE"
    assert "privacy_risk_above_profile_limit" in reasons


def test_negative_result_can_be_featured_when_receipt_bound() -> None:
    module = _load_module()
    spec = _spec(module, content_role="proof_claim", negative_or_null_result=True)
    score, disposition, reasons = module.score_asset(spec, _profile())
    assert score >= 70.0
    assert disposition == "FEATURE"
    assert reasons == []


def test_duplicate_custody_is_grouped_without_mutating_sources(tmp_path: Path) -> None:
    module = _load_module()
    source_a = tmp_path / "a.mov"
    source_b = tmp_path / "copy.mov"
    source_a.write_bytes(b"same-media-bytes")
    source_b.write_bytes(b"same-media-bytes")
    before = {path: module.sha256(path) for path in (source_a, source_b)}
    digest = before[source_a]
    policy = {
        "profiles": {"public_documentary": _profile()},
        "repo_assets": [],
        "external_asset_rules_by_sha256": {
            digest: {
                "asset_id": "duplicate_media",
                "content_role": "narrative",
                "rights_status": "cleared",
                "metrics": _spec(module)["metrics"],
            }
        },
    }
    private_records, public_records = module.collect_asset_records(
        policy, "public_documentary", [source_a, source_b]
    )
    assert len(private_records) == 1
    assert len(public_records) == 1
    assert public_records[0]["custody_copy_count"] == 2
    assert "canonical_path" not in public_records[0]
    assert {path: module.sha256(path) for path in (source_a, source_b)} == before


def test_public_manifest_contains_no_absolute_source_paths(tmp_path: Path) -> None:
    module = _load_module()
    media = tmp_path / "private.mov"
    media.write_bytes(b"private-source")
    digest = module.sha256(media)
    policy = {
        "profiles": {"public_documentary": _profile()},
        "repo_assets": [],
        "external_asset_rules_by_sha256": {
            digest: {
                "asset_id": "private_media",
                "content_role": "narrative",
                "rights_status": "cleared",
                "metrics": _spec(module)["metrics"],
            }
        },
    }
    _, public_records = module.collect_asset_records(policy, "public_documentary", [media])
    manifest = module.public_summary(public_records, "public_documentary", policy)
    serialized = json.dumps(manifest)
    assert str(tmp_path) not in serialized
    assert "canonical_path" not in serialized
    assert "custody_paths" not in serialized


def test_constants_are_scoped_by_profile() -> None:
    policy = json.loads(POLICY_PATH.read_text(encoding="utf-8"))
    public = policy["profiles"]["public_documentary"]
    reviewer = policy["profiles"]["reviewer_evidence"]
    archive = policy["profiles"]["private_archive"]
    assert public["hard_gates"]["privacy_risk_max"] < archive["hard_gates"]["privacy_risk_max"]
    assert reviewer["weights"]["proof_binding"] > public["weights"]["proof_binding"]
    assert archive["thresholds"]["hold_min"] == 0.0
