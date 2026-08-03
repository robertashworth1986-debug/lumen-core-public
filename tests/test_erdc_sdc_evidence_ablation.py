from __future__ import annotations

import importlib.util
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "code" / "ops" / "BUILD_ERDC_SDC_EVIDENCE_ABLATION.py"
OUT_JSON = ROOT / "out" / "ops" / "erdc_sdc_evidence_ablation_latest.json"
OUT_MD = ROOT / "docs" / "ERDC_SDC_EVIDENCE_ABLATION_2026-07-29.md"


def load_module():
    spec = importlib.util.spec_from_file_location("erdc_sdc_ablation", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def result_index(payload: dict) -> dict[str, dict]:
    return {row["profile_id"]: row for row in payload["results"]}


def attack_index(result: dict) -> dict[str, dict]:
    return {
        row["attack"]: row
        for row in result["control_attack_detection"]["cases"]
    }


def test_ablation_is_bounded_anchor_aware_and_detects_adaptive_attacks():
    module = load_module()
    payload = module.build_payload()
    results = result_index(payload)
    full = results["lumencore_full"]
    full_attacks = attack_index(full)

    assert payload["schema"] == "lumencore.erdc_sdc_evidence_ablation.v2"
    assert payload["status"] == (
        "SYNTHETIC_CONTROL_ABLATION_PASS_EXTERNAL_TRUST_ROOT_HPCMP_AND_"
        "INDEPENDENT_VALIDATION_REQUIRED"
    )
    assert payload["synthetic_workflows"]["count"] == 48
    assert payload["synthetic_workflows"]["raw_rows_published"] is False
    assert payload["all_checks_pass"] is True
    assert payload["promotion_or_performance_claim_allowed"] is False
    assert full["control_attack_detection"]["detected_count"] == 7
    assert full["control_attack_detection"]["case_count"] == 7
    assert full_attacks["adaptive_delete_rechain_and_reseal"]["detected"] is True
    assert full_attacks["adaptive_policy_rechain_and_reseal"]["detected"] is True
    assert full["adverse_outcome_recall"] == 1.0
    assert full["artifact_bytes_rehash_rate"] == 1.0
    assert full["predeclared_gate_execution_pass"] is True
    assert full["posthoc_promotion_change_detected"] is True

    assert (
        results["lumencore_no_chain"]["control_attack_detection"]["detection_rate"]
        < full["control_attack_detection"]["detection_rate"]
    )
    assert (
        results["lumencore_no_failure_retention"]["adverse_outcome_recall"]
        < full["adverse_outcome_recall"]
    )
    assert (
        results["lumencore_no_predeclared_gates"][
            "predeclared_gate_execution_pass"
        ]
        is False
    )
    assert results["lumencore_no_failure_retention"]["clean_profile_valid"] is True


def test_named_standards_are_context_only_and_not_attack_ranked():
    module = load_module()
    payload = module.build_payload()
    sources = {row["id"]: row for row in payload["baseline_sources"]}
    contexts = {
        row["profile_id"]: row
        for row in payload["interoperability_context_profiles"]
    }

    assert sources["opentelemetry_logs_1_59"]["version"] == "1.59.0"
    assert sources["slsa_build_provenance_1_2"]["version"] == "1.2"
    assert sources["opentelemetry_logs_1_59"]["comparison_role"] == (
        "INTEROPERABILITY_CONTEXT_NOT_RANKED"
    )
    assert sources["slsa_build_provenance_1_2"]["comparison_role"] == (
        "INTEROPERABILITY_CONTEXT_NOT_RANKED"
    )
    assert contexts["opentelemetry_logs_1_59"]["attack_comparison_performed"] is False
    assert (
        contexts["slsa_build_provenance_1_2"]["attack_comparison_performed"]
        is False
    )
    assert "attack_detection" not in contexts["opentelemetry_logs_1_59"]
    assert "not an HPCMP workload" in payload["claim_boundary"]
    assert "not ranked or attacked" in payload["claim_boundary"]
    assert "not an external signature" in payload["trusted_anchor_model"]


def test_written_outputs_are_public_safe_deterministic_and_current():
    module = load_module()
    payload = json.loads(OUT_JSON.read_text(encoding="utf-8"))
    markdown = OUT_MD.read_text(encoding="utf-8")

    assert payload["all_checks_pass"] is True
    assert payload["protocol_sha256"] in markdown
    assert "OpenTelemetry Logs Data Model 1.59.0" in markdown
    assert "SLSA Build Provenance 1.2" in markdown
    assert "Interoperability Contexts - Not Ranked" in markdown
    assert "adaptive attacks and ablations" in markdown
    assert "not an HPCMP workload" in markdown
    assert "Median verify" not in markdown
    module.check_outputs(module.build_payload())
