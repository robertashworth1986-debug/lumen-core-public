from __future__ import annotations

import importlib.util
import json
import sys
from copy import deepcopy
from pathlib import Path

import pytest


sys.dont_write_bytecode = True

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "code" / "ops" / "BUILD_GOV_REVIEWER_QUESTION_MATRIX.py"
CONFIG = ROOT / "config" / "gov_reviewer_question_matrix_v1.json"


def load_module():
    spec = importlib.util.spec_from_file_location(
        "gov_reviewer_question_matrix",
        SCRIPT,
    )
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def load_config() -> dict:
    return json.loads(CONFIG.read_text(encoding="utf-8"))


def question_index(payload: dict) -> dict[str, dict]:
    return {
        question["question_id"]: question
        for role in payload["roles"]
        for question in role["questions"]
    }


def fixture_config(tmp_path: Path) -> tuple[dict, Path]:
    (tmp_path / "README.md").write_text(
        "bounded evidence is available\n",
        encoding="utf-8",
    )
    (tmp_path / "state.json").write_text(
        json.dumps(
            {
                "generated_utc": "2026-07-23T11:30:00Z",
                "gate_open": False,
            }
        )
        + "\n",
        encoding="utf-8",
    )
    roles = [
        {
            "role_id": "federal_reviewer",
            "name": "Federal Reviewer",
            "mandate": "Review bounded evidence.",
        },
        {
            "role_id": "contracting_officer",
            "name": "Contracting Officer",
            "mandate": "Review contracting evidence.",
        },
        {
            "role_id": "technical_evaluator",
            "name": "Technical Evaluator",
            "mandate": "Review technical evidence.",
        },
        {
            "role_id": "cybersecurity_reviewer",
            "name": "Cybersecurity Reviewer",
            "mandate": "Review security evidence.",
        },
        {
            "role_id": "licensing_officer",
            "name": "Licensing Officer",
            "mandate": "Review licensing evidence.",
        },
    ]
    prefixes = {
        "federal_reviewer": "FED",
        "contracting_officer": "CO",
        "technical_evaluator": "TECH",
        "cybersecurity_reviewer": "CYB",
        "licensing_officer": "LIC",
    }
    questions = []
    for role in roles:
        for number in range(1, 6):
            questions.append(
                {
                    "question_id": f"{prefixes[role['role_id']]}-{number:03d}",
                    "role_id": role["role_id"],
                    "priority": "high",
                    "question": f"Is bounded fixture evidence available for item {number}?",
                    "decision_use": "Exercise deterministic source evaluation.",
                    "answer_class": "SUPPORTED",
                    "answer": "The fixture supports a bounded answer.",
                    "missing_evidence": [],
                    "next_receipt": "A refreshed bounded fixture receipt.",
                    "prohibited_claims": ["Any broader conclusion"],
                    "assertions": [
                        {
                            "assertion_id": "bounded_policy",
                            "source_id": "policy",
                            "selector": {"type": "text", "value": ""},
                            "operator": "contains",
                            "expected": "bounded evidence",
                            "meaning": "The fixture policy contains the bounded phrase.",
                        }
                    ],
                }
            )
    config = {
        "schema": "lumencore.gov_reviewer_question_matrix_config.v1",
        "title": "Fixture Reviewer Matrix",
        "snapshot_utc": "2026-07-23T12:00:00Z",
        "claim_boundary": "Fixture-only bounded evidence.",
        "roles": roles,
        "sources": [
            {
                "source_id": "policy",
                "path": "README.md",
                "format": "text",
                "authority": "Fixture policy.",
                "freshness": {"mode": "timeless"},
            },
            {
                "source_id": "state",
                "path": "state.json",
                "format": "json",
                "authority": "Fixture state.",
                "freshness": {
                    "mode": "max_age",
                    "timestamp_pointer": "/generated_utc",
                    "max_age_hours": 1,
                },
            },
        ],
        "questions": questions,
    }
    config_path = tmp_path / "config.json"
    config_path.write_text(
        json.dumps(config, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return config, config_path


def test_frozen_matrix_covers_all_roles_and_fails_closed_on_source_drift():
    module = load_module()
    payload = module.build_matrix(
        load_config(),
        root=ROOT,
        config_path=CONFIG,
        generator_path=SCRIPT,
    )

    assert payload["schema"] == "lumencore.gov_reviewer_question_matrix.v1"
    assert payload["status"] == "MATRIX_HAS_UNRESOLVED_QUESTIONS"
    assert payload["summary"]["role_count"] == 5
    assert payload["summary"]["question_count"] == 30
    assert payload["summary"]["verified_answer_count"] >= 24
    assert payload["summary"]["unresolved_question_count"] >= 3
    assert (
        payload["summary"]["verified_answer_count"]
        + payload["summary"]["unresolved_question_count"]
        == payload["summary"]["question_count"]
    )
    assert payload["summary"]["missing_source_count"] == 0
    assert payload["summary"]["invalid_source_count"] == 0
    assert {role["role_id"] for role in payload["roles"]} == {
        "federal_reviewer",
        "contracting_officer",
        "technical_evaluator",
        "cybersecurity_reviewer",
        "licensing_officer",
    }
    assert all(role["summary"]["question_count"] == 6 for role in payload["roles"])

    by_id = question_index(payload)
    assert by_id["FED-003"]["status"] == "SUPPORTED_NEGATIVE"
    assert by_id["CO-003"]["status"] == "SUPPORTED_NEGATIVE"
    assert by_id["TECH-003"]["status"] == "BLOCKED"
    assert by_id["CYB-001"]["status"] == "BLOCKED"
    assert by_id["LIC-001"]["status"] == "UNRESOLVED"
    assert by_id["FED-006"]["status"] == "UNRESOLVED"
    assert by_id["CO-005"]["status"] == "UNRESOLVED"
    assert by_id["TECH-001"]["status"] == "UNRESOLVED"
    assert by_id["TECH-004"]["status"] == "UNRESOLVED"
    assert all(
        assertion["passed"]
        for question in by_id.values()
        if question["proof_state"] == "VERIFIED_ANSWER"
        for assertion in question["evidence_assertions"]
    )
    assert all(
        any(not assertion["passed"] for assertion in by_id[question_id]["evidence_assertions"])
        for question_id in ("FED-006", "CO-005", "TECH-001", "TECH-004", "LIC-001")
    )

    assert all(value is False for value in payload["controls"].values())
    assert module.verify_matrix_hash(payload)
    assert len(payload["integrity"]["source_chain_sha256"]) == 64
    assert all(
        source["sha256"] is None or len(source["sha256"]) == 64
        for source in payload["source_manifest"]
    )


def test_blocked_and_partial_questions_name_missing_evidence_and_next_receipt():
    module = load_module()
    config = load_config()
    module.validate_config(config, root=ROOT)

    assert len(config["questions"]) == 30
    for question in config["questions"]:
        assert question["next_receipt"].strip()
        assert question["prohibited_claims"]
        if question["answer_class"] in {"BLOCKED", "PARTIAL_DATED"}:
            assert question["missing_evidence"]


def test_json_and_markdown_outputs_are_deterministic(tmp_path):
    module = load_module()
    config, config_path = fixture_config(tmp_path)
    first = module.build_matrix(
        config,
        root=tmp_path,
        config_path=config_path,
        generator_path=SCRIPT,
    )
    second = module.build_matrix(
        deepcopy(config),
        root=tmp_path,
        config_path=config_path,
        generator_path=SCRIPT,
    )
    assert first == second

    first_json = tmp_path / "first.json"
    first_md = tmp_path / "first.md"
    second_json = tmp_path / "second.json"
    second_md = tmp_path / "second.md"
    module.write_outputs(first, out_json=first_json, out_md=first_md)
    module.write_outputs(second, out_json=second_json, out_md=second_md)

    assert first_json.read_bytes() == second_json.read_bytes()
    assert first_md.read_bytes() == second_md.read_bytes()
    assert module.output_differences(
        first,
        out_json=first_json,
        out_md=first_md,
    ) == []
    assert first["integrity"]["matrix_sha256"] in first_md.read_text(
        encoding="utf-8"
    )


def test_missing_source_fails_every_dependent_answer_closed(tmp_path):
    module = load_module()
    config, config_path = fixture_config(tmp_path)
    config["sources"][0]["path"] = "missing.md"
    config_path.write_text(
        json.dumps(config, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )

    payload = module.build_matrix(
        config,
        root=tmp_path,
        config_path=config_path,
        generator_path=SCRIPT,
    )
    assert payload["status"] == "MATRIX_HAS_UNRESOLVED_QUESTIONS"
    assert payload["summary"]["missing_source_count"] == 1
    assert payload["summary"]["unresolved_question_count"] == 25
    assert all(
        question["proof_state"] == "UNRESOLVED"
        for question in question_index(payload).values()
    )
    assert "could not be verified" in payload["roles"][0]["questions"][0][
        "answer"
    ]


def test_content_tampering_and_invalid_json_fail_closed(tmp_path):
    module = load_module()
    config, config_path = fixture_config(tmp_path)
    (tmp_path / "README.md").write_text("changed evidence\n", encoding="utf-8")
    payload = module.build_matrix(
        config,
        root=tmp_path,
        config_path=config_path,
        generator_path=SCRIPT,
    )
    assert payload["summary"]["unresolved_question_count"] == 25

    for question in config["questions"]:
        question["assertions"] = [
            {
                "assertion_id": "state_gate",
                "source_id": "state",
                "selector": {"type": "json_pointer", "value": "/gate_open"},
                "operator": "is_false",
                "meaning": "The fixture gate is closed.",
            }
        ]
    (tmp_path / "state.json").write_text("{", encoding="utf-8")
    config_path.write_text(
        json.dumps(config, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    payload = module.build_matrix(
        config,
        root=tmp_path,
        config_path=config_path,
        generator_path=SCRIPT,
    )
    assert payload["summary"]["invalid_source_count"] == 1
    assert payload["summary"]["unresolved_question_count"] == 25


def test_stale_and_future_source_states_are_deterministic_gates(tmp_path):
    module = load_module()
    config, config_path = fixture_config(tmp_path)
    state_path = tmp_path / "state.json"
    state_path.write_text(
        json.dumps(
            {
                "generated_utc": "2026-07-23T09:00:00Z",
                "gate_open": False,
            }
        )
        + "\n",
        encoding="utf-8",
    )
    for question in config["questions"]:
        question["assertions"] = [
            {
                "assertion_id": "stale_state",
                "source_id": "state",
                "selector": {
                    "type": "source_metadata",
                    "value": "freshness_state",
                },
                "operator": "equals",
                "expected": "STALE",
                "meaning": "The fixture source is stale.",
            }
        ]
    config_path.write_text(
        json.dumps(config, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    payload = module.build_matrix(
        config,
        root=tmp_path,
        config_path=config_path,
        generator_path=SCRIPT,
    )
    source = next(
        row for row in payload["source_manifest"] if row["source_id"] == "state"
    )
    assert source["freshness_state"] == "STALE"
    assert payload["summary"]["unresolved_question_count"] == 0

    state_path.write_text(
        json.dumps(
            {
                "generated_utc": "2026-07-23T12:01:00Z",
                "gate_open": False,
            }
        )
        + "\n",
        encoding="utf-8",
    )
    payload = module.build_matrix(
        config,
        root=tmp_path,
        config_path=config_path,
        generator_path=SCRIPT,
    )
    source = next(
        row for row in payload["source_manifest"] if row["source_id"] == "state"
    )
    assert source["freshness_state"] == "FUTURE"
    assert payload["summary"]["unresolved_question_count"] == 25


def test_unsafe_source_paths_and_sensitive_selectors_are_rejected(tmp_path):
    module = load_module()
    config, _ = fixture_config(tmp_path)
    config["sources"][0]["path"] = "../outside.md"
    with pytest.raises(module.MatrixConfigError, match="escapes repository root"):
        module.validate_config(config, root=tmp_path)

    config, _ = fixture_config(tmp_path)
    config["questions"][0]["assertions"] = [
        {
            "assertion_id": "unsafe_identifier",
            "source_id": "state",
            "selector": {"type": "json_pointer", "value": "/uei"},
            "operator": "nonempty",
            "meaning": "Unsafe selector fixture.",
        }
    ]
    with pytest.raises(module.MatrixConfigError, match="sensitive material"):
        module.validate_config(config, root=tmp_path)


def test_unqualified_claim_language_is_rejected(tmp_path):
    module = load_module()
    config, _ = fixture_config(tmp_path)
    config["questions"][0][
        "answer"
    ] = "The fixture is independently validated."
    with pytest.raises(
        module.MatrixConfigError,
        match="unqualified claim phrases",
    ):
        module.validate_config(config, root=tmp_path)


def test_matrix_hash_detects_tampering():
    module = load_module()
    payload = module.build_matrix(
        load_config(),
        root=ROOT,
        config_path=CONFIG,
        generator_path=SCRIPT,
    )
    assert module.verify_matrix_hash(payload)
    payload["summary"]["question_count"] += 1
    assert not module.verify_matrix_hash(payload)


def test_markdown_is_reviewer_safe_and_exposes_source_freshness():
    module = load_module()
    payload = module.build_matrix(
        load_config(),
        root=ROOT,
        config_path=CONFIG,
        generator_path=SCRIPT,
    )
    markdown = module.render_markdown(payload)

    for heading in (
        "Skeptical Federal Reviewer",
        "Contracting Officer",
        "Technical Evaluator",
        "Cybersecurity Reviewer",
        "Licensing Officer",
    ):
        assert f"## {heading}" in markdown
    assert "## Proof-Gap Register" in markdown
    assert "## Source Manifest" in markdown
    assert "`STALE`" in markdown
    assert "performed no email send" in markdown
    assert "portal action" in markdown
    assert payload["integrity"]["matrix_sha256"] in markdown
    assert "MATRIX_HAS_UNRESOLVED_QUESTIONS" in markdown
