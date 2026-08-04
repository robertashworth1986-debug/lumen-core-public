from __future__ import annotations

import importlib.util
import json
import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "code" / "ops" / "BUILD_VPS_PUBLIC_RELEASE_SECURITY_AUDIT.py"


def load_module():
    spec = importlib.util.spec_from_file_location("vps_public_release_security_audit", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_current_audit_is_fail_closed_and_privacy_preserving():
    module = load_module()
    audit = module.build_audit(as_of_utc="2026-08-02T15:00:00Z")

    assert audit["schema"] == "lumencore.vps_public_release_security_audit.v1"
    assert audit["summary"]["status"] == "BLOCKED"
    assert audit["summary"]["public_release_allowed"] is False
    assert audit["summary"]["vps_mutation_allowed"] is False
    assert audit["summary"]["public_endpoint_passed_count"] == 0
    assert audit["summary"]["public_endpoint_count"] == 4
    assert audit["summary"]["candidate_artifact_count"] == 3
    assert audit["summary"]["candidate_plan_blocked_artifact_count"] == 0
    assert audit["summary"]["deferred_full_plan_artifact_count"] == 3
    assert audit["summary"]["blocked_artifact_count"] == 3
    assert audit["release_scope_hygiene"]["status"] == (
        "PASS_RELEASE_STAGE_HYGIENE"
    )
    assert audit["release_scope_hygiene"]["staged_path_count"] == 3
    assert audit["release_scope_hygiene"]["prohibited_staged_path_count"] == 0
    assert audit["release_scope_hygiene"]["hash_verified_path_count"] == 3
    assert audit["release_scope_hygiene"]["plan_binding_matches"] is True
    assert audit["repository_index_hygiene"]["status"] == (
        "BLOCKED_PROHIBITED_STAGED_PATH_CLASSES"
    )
    assert audit["repository_index_hygiene"]["staged_path_count"] > 3
    assert audit["repository_index_hygiene"]["prohibited_staged_path_count"] > 0
    assert audit["repository_index_hygiene"]["affects_isolated_release_stage"] is False
    assert audit["gateway_repair_candidate"]["status"] == (
        "BOUNDED_REPAIR_PREPARED_ACTION_TIME_APPROVAL_REQUIRED"
    )
    assert audit["gateway_repair_candidate"]["apply_allowed"] is False
    approval_text = audit["gateway_repair_candidate"][
        "required_exact_approval_text"
    ]
    assert approval_text.startswith("APPROVE ONE VPS GATEWAY MODULE REPAIR NOW:")
    assert audit["gateway_repair_candidate"]["module_sha256"] in approval_text
    assert audit["gateway_repair_candidate"]["repair_script_sha256"] in approval_text
    assert "no DNS, reverse-proxy, proof-feed, publication" in approval_text
    assert "LUMA_HUMAN_UNLOCK_TOKEN" not in approval_text
    assert "PUBLIC_REVIEWER_CANARY_BLOCKED" in audit["blockers"]
    assert "RELEASE_STAGE_HYGIENE_OR_BINDING_BLOCKED" not in audit["blockers"]
    assert "DEPLOY_TRANSPORT_HARDENING_REQUIRED" not in audit["blockers"]
    assert audit["summary"]["transport_script_passed_count"] == 4
    assert audit["summary"]["transport_script_count"] == 4

    candidate_ids = {
        item["id"]
        for item in audit["release_plan"]["bounded_candidates_after_global_gates"]
    }
    assert candidate_ids == {
        "model_geometry_evidence_ledger",
        "quant_hub_reviewer_context_json",
        "quant_hub_reviewer_context_markdown",
    }
    assert all(
        item["external_action_allowed"] is False
        for item in audit["release_plan"]["bounded_candidates_after_global_gates"]
    )
    assert {
        item["id"]
        for item in audit["release_plan"]["deferred_full_plan_artifacts"]
    } == {
        "current_evidence_to_pilot_deck_pdf",
        "federal_capability_statement_pdf",
        "source_native_benchmark_whitepaper_pdf",
    }

    serialized = json.dumps(audit, sort_keys=True)
    assert re.search(r"(?<![\w.])(?:\d{1,3}\.){3}\d{1,3}(?![\w.])", serialized) is None
    assert ".key" not in serialized.lower()
    assert audit["privacy_controls"] == {
        "credentials_accessed": False,
        "credential_values_recorded": False,
        "host_values_recorded": False,
        "key_filenames_recorded": False,
        "response_bodies_recorded": False,
        "remote_mutation_performed": False,
        "publication_performed": False,
    }

    unsealed = dict(audit)
    receipt = unsealed.pop("audit_sha256")
    assert module.canonical_sha256(unsealed) == receipt


def test_transport_audit_confirms_all_paths_are_hardened_without_emitting_values():
    module = load_module()
    audit = module.build_audit(as_of_utc="2026-08-02T15:00:00Z")
    rows = {row["path"]: row for row in audit["deployment_transport_audit"]}

    legacy = rows["code/ops/UPLOAD_TO_ORACLE.ps1"]
    assert legacy["strict_host_key_checking_no_detected"] is False
    assert legacy["strict_host_key_checking_yes_detected"] is True
    assert legacy["human_unlock_gate_detected"] is True
    assert legacy["transport_hardening_passed"] is True

    repair = rows["deploy/REPAIR_LUMA_GATEWAY_MODULE.ps1"]
    assert repair["human_unlock_gate_detected"] is True
    assert repair["transport_hardening_passed"] is True
    assert repair["hardcoded_ipv4_count"] == 0
    assert repair["machine_specific_key_candidate_count"] == 0


def test_markdown_reports_gates_without_claiming_publication():
    module = load_module()
    audit = module.build_audit(as_of_utc="2026-08-02T15:00:00Z")
    markdown = module.render_markdown(audit)

    assert "Keep publication and VPS mutation blocked" in markdown
    assert "Passed endpoints: `0/4`" in markdown
    assert "Bounded Release Candidates" in markdown
    assert "Isolated Release Stage" in markdown
    assert "Deferred Full-Plan Artifacts" in markdown
    assert "Hash verified: `3/3`" in markdown
    assert "Prohibited paths: `0`" in markdown
    assert "Apply allowed by this audit: `false`" in markdown
    assert "Required exact one-time approval text" in markdown
    assert "APPROVE ONE VPS GATEWAY MODULE REPAIR NOW" in markdown
    assert "no DNS, reverse-proxy, proof-feed, publication" in markdown
    assert "Audit SHA-256" in markdown
    assert "deployment transport controls pass the local static audit" in markdown
    assert "hardening remains incomplete" not in markdown
    assert "preserve the currently passing SSH host-verification controls" in markdown
    assert "harden SSH host verification" not in markdown
    assert "published successfully" not in markdown.lower()


def test_audit_output_writer_updates_current_pointers_atomically(tmp_path: Path):
    module = load_module()
    audit = module.build_audit(as_of_utc="2026-08-02T15:00:00Z")
    dated_json = tmp_path / "audit_20260802.json"
    dated_markdown = tmp_path / "audit_20260802.md"
    latest_json = tmp_path / "audit_latest.json"
    latest_markdown = tmp_path / "audit_current.md"

    module.write_audit_outputs(
        audit,
        output_json=dated_json,
        output_markdown=dated_markdown,
        latest_json=latest_json,
        latest_markdown=latest_markdown,
    )

    assert json.loads(dated_json.read_text(encoding="utf-8")) == audit
    assert json.loads(latest_json.read_text(encoding="utf-8")) == audit
    assert dated_markdown.read_text(encoding="utf-8") == latest_markdown.read_text(
        encoding="utf-8"
    )
    assert not list(tmp_path.glob(".*.tmp"))
