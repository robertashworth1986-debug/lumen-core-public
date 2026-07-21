from __future__ import annotations

import importlib.util
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "code" / "ops" / "BUILD_CODECHECK_EIA_READINESS.py"
CONFIG = ROOT / "config" / "codecheck_eia_readiness_v1.json"
CODECHECK = ROOT / "codecheck.yml"
WORKFLOW = ROOT / ".github" / "workflows" / "codecheck-eia-readiness.yml"
OUTPUT = (
    ROOT
    / "evidence"
    / "external_validation"
    / "codecheck_eia_author_readiness_20260720.json"
)
MARKDOWN = ROOT / "docs" / "CODECHECK_EIA_AUTHOR_READINESS_2026-07-20.md"
OPERATOR_RECEIPT = (
    ROOT
    / "evidence"
    / "reproducibility"
    / "codecheck_eia_operator_clean_runner_be7776f7_20260721.json"
)
PREPRINT_MARKDOWN = (
    ROOT
    / "docs"
    / "preprint"
    / "BOUNDED_REPRODUCIBILITY_CAPSULE_PREPRINT_2026-07-21.md"
)
PREPRINT_PDF = (
    ROOT
    / "docs"
    / "preprint"
    / "BOUNDED_REPRODUCIBILITY_CAPSULE_PREPRINT_2026-07-21.pdf"
)
REQUEST_DRAFT = ROOT / "docs" / "CODECHECK_COMMUNITY_REQUEST_DRAFT_2026-07-21.md"
RELEASE_CONFIG = ROOT / "config" / "codecheck_eia_release_candidate_v1.json"
RELEASE_SCRIPT = ROOT / "code" / "ops" / "BUILD_CODECHECK_EIA_RELEASE_CANDIDATE.py"
RELEASE_PLAN = ROOT / "docs" / "release" / "CODECHECK_EIA_IMMUTABLE_RELEASE_PLAN_2026-07-21.md"


def load_module():
    spec = importlib.util.spec_from_file_location("codecheck_eia_readiness", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_codecheck_configuration_is_author_scoped_and_manifest_exact():
    module = load_module()
    config = json.loads(CONFIG.read_text(encoding="utf-8"))
    parsed = module.parse_codecheck_config(CODECHECK)

    assert parsed["utf8_decoded"] is True
    assert parsed["explicit_document_start"] is True
    assert parsed["yaml_directive"] == "%YAML 1.1"
    assert parsed["version"] == "https://codecheck.org.uk/spec/config/1.0/"
    assert parsed["manifest"] == config["execution"]["manifest_paths"]
    assert parsed["manifest_paths_safe"] is True
    assert parsed["manifest_paths_unique"] is True
    assert parsed["paper_title_present"] is True
    assert (
        parsed["paper_reference"]
        == config["preprint_and_request"]["paper_reference"]
    )
    assert parsed["corresponding_author_present"] is True
    assert parsed["codechecker_metadata_present"] is False
    assert parsed["report_metadata_present"] is False


def test_manifest_parser_rejects_absolute_traversal_and_duplicate_paths(tmp_path):
    module = load_module()
    unsafe = tmp_path / "codecheck.yml"
    unsafe.write_text(
        "---\n"
        "manifest:\n"
        "  - file: \"../escape.json\"\n"
        "  - file: \"C:/private.json\"\n"
        "  - file: \"../escape.json\"\n",
        encoding="utf-8",
    )

    parsed = module.parse_codecheck_config(unsafe)

    assert parsed["manifest_paths_safe"] is False
    assert parsed["manifest_paths_unique"] is False


def test_authoritative_archive_matches_all_declared_outputs_and_checksums():
    module = load_module()
    payload = module.build_payload(generated_utc="2026-07-20T00:00:00+00:00")
    archive = payload["authoritative_archive"]

    assert archive["verified"] is True
    assert archive["checksum_entry_count"] == 6
    assert archive["checksum_pass_count"] == 6
    assert archive["complete_file_coverage"] is True
    assert archive["suite_count"] == archive["suite_pass_count"] == 3
    assert archive["assertion_count"] == archive["assertion_pass_count"] == 31
    assert archive["external_validation_complete"] is False
    assert payload["checks"]["archive_manifest_matches_codecheck_manifest"] is True
    assert payload["checks"]["archived_computational_identity_still_matches"] is True
    assert archive["source_reconciliation"]["full_source_exact_match"] is False
    assert archive["source_reconciliation"]["computational_identity_exact_match"] is True
    assert archive["source_reconciliation"]["mismatch_paths"] == [
        ".gitignore",
        "README.md",
    ]


def test_operator_clean_runner_is_hash_locked_clean_and_not_external():
    module = load_module()
    payload = module.build_payload(generated_utc="2026-07-20T00:00:00+00:00")
    runner = payload["operator_clean_runner"]

    assert runner["verified"] is True
    assert runner["receipt_path"] == OPERATOR_RECEIPT.relative_to(ROOT).as_posix()
    assert runner["relevant_source_clean"] is True
    assert runner["clean_runner_replay"] is True
    assert runner["authoritative_runtime_match"] is True
    assert runner["dependency_closure_exact_match"] is True
    assert runner["fixture_tests_passed"] is True
    assert runner["suite_count"] == runner["suite_pass_count"] == 3
    assert runner["assertion_count"] == runner["assertion_pass_count"] == 31
    assert runner["source_reconciliation"]["full_source_exact_match"] is True
    assert (
        runner["source_reconciliation"]["computational_identity_exact_match"]
        is True
    )
    assert runner["source_reconciliation"]["mismatch_paths"] == []
    assert runner["external_validation_complete"] is False


def test_operator_clean_runner_rejects_a_tampered_receipt(tmp_path):
    module = load_module()
    control = json.loads(CONFIG.read_text(encoding="utf-8"))[
        "operator_clean_runner"
    ]
    receipt = json.loads(OPERATOR_RECEIPT.read_text(encoding="utf-8"))
    receipt["status"] = "TAMPERED"
    tampered = tmp_path / "receipt.json"
    tampered.write_text(json.dumps(receipt), encoding="utf-8")

    result = module.verify_operator_clean_runner(control, receipt_path=tampered)

    assert result["verified"] is False
    assert result["checks"]["receipt_sha256_matched"] is False
    assert result["checks"]["status_matched"] is False
    assert result["external_validation_complete"] is False


def test_preprint_and_request_are_hash_locked_bounded_and_unopened():
    module = load_module()
    payload = module.build_payload(generated_utc="2026-07-20T00:00:00+00:00")
    packet = payload["preprint_and_request"]

    assert packet["verified"] is True
    assert packet["markdown_path"] == PREPRINT_MARKDOWN.relative_to(ROOT).as_posix()
    assert packet["pdf_path"] == PREPRINT_PDF.relative_to(ROOT).as_posix()
    assert packet["request_path"] == REQUEST_DRAFT.relative_to(ROOT).as_posix()
    assert packet["pdf_page_count"] == 5
    assert packet["stable_public_identifier"] is None
    assert packet["immutable_public_source_release"] is None
    assert packet["duplicate_request_reconciled"] is False
    assert packet["community_request_ready"] is False
    assert packet["community_request_opened"] is False
    assert all(packet["checks"].values())


def test_preprint_verification_rejects_tampered_source(tmp_path):
    module = load_module()
    control = json.loads(CONFIG.read_text(encoding="utf-8"))[
        "preprint_and_request"
    ]
    tampered = tmp_path / "preprint.md"
    tampered.write_text(
        PREPRINT_MARKDOWN.read_text(encoding="utf-8") + "\nunsupported claim\n",
        encoding="utf-8",
    )

    result = module.verify_preprint_and_request(
        control,
        markdown_path=tampered,
        pdf_path=PREPRINT_PDF,
        request_path=REQUEST_DRAFT,
    )

    assert result["verified"] is False
    assert result["checks"]["source_sha256_matched"] is False
    assert result["community_request_ready"] is False
    assert result["community_request_opened"] is False


def test_release_candidate_is_integrated_but_every_publication_gate_is_closed():
    module = load_module()
    payload = module.build_payload(generated_utc="2026-07-20T00:00:00+00:00")
    candidate = payload["release_candidate"]

    assert RELEASE_CONFIG.is_file()
    assert RELEASE_SCRIPT.is_file()
    assert RELEASE_PLAN.is_file()
    assert candidate["internal_release_candidate_ready"] is True
    assert candidate["publication_ready"] is False
    assert candidate["publication_state"]["github_release_published"] is False
    assert candidate["publication_state"]["zenodo_doi_issued"] is False
    assert candidate["publication_state"]["codecheck_request_opened"] is False
    assert candidate["publication_state"]["external_validation_complete"] is False
    assert all(candidate["checks"].values())


def test_ci_gate_is_read_only_pinned_and_retriggers_for_portable_inputs():
    config = json.loads(CONFIG.read_text(encoding="utf-8"))
    workflow = WORKFLOW.read_text(encoding="utf-8")

    assert "permissions:\n  contents: read" in workflow
    assert "runs-on: ubuntu-24.04" in workflow
    assert 'python-version: "3.11.9"' in workflow
    assert "BUILD_CODECHECK_EIA_READINESS.py --check-only" in workflow
    assert "tests/test_codecheck_eia_readiness.py" in workflow
    assert "actions/checkout@93cb6efe18208431cddfb8368fd83d5badbf9bfd" in workflow
    assert "actions/setup-python@ece7cb06caefa5fff74198d8649806c4678c61a1" in workflow
    for path in config["portable_input_paths"]:
        assert workflow.count(f'- "{path}"') == 2, path


def test_internal_readiness_pass_keeps_every_external_gate_closed():
    module = load_module()
    payload = module.build_payload(generated_utc="2026-07-20T00:00:00+00:00")
    summary = payload["summary"]

    assert payload["status"] == "AUTHOR_PACKET_READY_FOR_HUMAN_REVIEW"
    assert summary["internal_gate_passed"] is True
    assert summary["internal_check_count"] == summary["internal_check_pass_count"]
    assert summary["archive_full_source_exact_match"] is False
    assert summary["archived_computational_identity_still_matches"] is True
    assert summary["operator_clean_runner_receipt_verified"] is True
    assert summary["operator_clean_runner_full_source_exact_match"] is True
    assert summary["operator_clean_runner_computational_identity_current"] is True
    assert summary["current_commit_clean_runner_complete"] is False
    assert summary["public_preprint_draft_complete"] is True
    assert summary["release_candidate_definition_ready"] is True
    assert summary["release_candidate_publication_ready"] is False
    assert summary["stable_public_preprint_identifier_complete"] is False
    assert summary["immutable_public_source_release_complete"] is False
    assert summary["duplicate_request_reconciled"] is False
    assert summary["community_request_ready"] is False
    assert summary["community_request_opened"] is False
    assert summary["human_author_review_complete"] is False
    assert summary["submission_authorized"] is False
    assert summary["codechecker_assigned"] is False
    assert summary["independent_execution_complete"] is False
    assert summary["certificate_issued"] is False
    assert summary["external_validation_complete"] is False
    assert all(gate["complete"] is False for gate in payload["external_gates"])
    assert payload["privacy_scan"]["passed"] is True


def test_method_and_license_controls_preserve_the_claim_boundary():
    module = load_module()
    payload = module.build_payload(generated_utc="2026-07-20T00:00:00+00:00")

    assert payload["checks"]["license_distinguishes_code_and_eia_data"] is True
    assert payload["checks"]["method_note_preserves_failed_gates"] is True
    assert "does not prove that CODECHECK accepted" in payload["claim_boundary"]
    assert "cannot be used to promote the live router" in payload[
        "live_runtime_boundary"
    ]
    assert "would not establish" in payload["value_bridge"]


def test_every_portable_input_is_present_hashed_and_path_safe():
    module = load_module()
    payload = module.build_payload(generated_utc="2026-07-20T00:00:00+00:00")

    assert all(payload["path_checks"].values())
    assert len(payload["portable_inputs"]) >= 10
    assert all(len(row["sha256"]) == 64 for row in payload["portable_inputs"])
    assert payload["portable_input_chain_sha256"] == module.canonical_sha256(
        payload["portable_inputs"]
    )
    without_hash = {
        key: value for key, value in payload.items() if key != "readiness_sha256"
    }
    assert payload["readiness_sha256"] == module.canonical_sha256(without_hash)


def test_published_outputs_match_a_timestamp_stable_rebuild():
    module = load_module()
    published = json.loads(OUTPUT.read_text(encoding="utf-8"))
    rebuilt = module.build_payload(generated_utc=published["generated_utc"])

    assert module.published_output_differences(rebuilt) == []
    rendered = MARKDOWN.read_text(encoding="utf-8")
    assert "AUTHOR_PACKET_READY_FOR_HUMAN_REVIEW" in rendered
    assert "Independent execution complete: `false`" in rendered
    assert "Operator clean-runner receipt verified: `true`" in rendered
    assert (
        "Operator clean-runner computational identity current: `true`"
        in rendered
    )
    assert "Certificate issued: `false`" in rendered
    assert "External validation complete: `false`" in rendered
    assert "Public preprint draft complete: `true`" in rendered
    assert "Deterministic release-candidate definition ready: `true`" in rendered
    assert "Release publication ready: `false`" in rendered
    assert "Stable public preprint identifier complete: `false`" in rendered
    assert "Community request opened: `false`" in rendered


def test_published_output_comparison_fails_closed_on_stale_json(tmp_path):
    module = load_module()
    payload = module.build_payload(generated_utc="2026-07-20T00:00:00+00:00")
    json_path = tmp_path / "readiness.json"
    markdown_path = tmp_path / "readiness.md"
    module.write_json(json_path, payload)
    module.write_text(markdown_path, module.render_markdown(payload))

    assert module.published_output_differences(
        payload, json_path=json_path, markdown_path=markdown_path
    ) == []

    json_path.write_text("{}\n", encoding="utf-8")
    differences = module.published_output_differences(
        payload, json_path=json_path, markdown_path=markdown_path
    )
    assert differences == [f"stale:{module.display_path(json_path)}"]
