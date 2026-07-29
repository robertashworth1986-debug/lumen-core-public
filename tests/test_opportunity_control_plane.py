from __future__ import annotations

import ast
import copy
import importlib.util
import json
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "code" / "ops" / "BUILD_OPPORTUNITY_CONTROL_PLANE.py"
CONFIG = ROOT / "config" / "opportunity_control_plane_v1.json"
FIXTURES = ROOT / "tests" / "fixtures" / "opportunity_control_plane"
PUBLIC_LEADS = FIXTURES / "public_leads.json"
GMAIL_JOB_ALERTS = FIXTURES / "gmail_job_alert_leads_2026-07-23.json"
AS_OF_UTC = "2026-07-23T18:00:00Z"


def load_module():
    spec = importlib.util.spec_from_file_location(
        "opportunity_control_plane",
        SCRIPT,
    )
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def write_document(path: Path, records: list[dict]) -> Path:
    path.write_text(
        json.dumps(
            {
                "schema": "lumencore.public_opportunity_leads.v1",
                "environment": "TEST_FIXTURE",
                "records": records,
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    return path


def build_fixture_payload(module):
    return module.build_control_plane(
        [PUBLIC_LEADS, GMAIL_JOB_ALERTS],
        as_of_utc=AS_OF_UTC,
        config_path=CONFIG,
    )


def action_by_record(payload: dict) -> dict[str, dict]:
    return {action["record_id"]: action for action in payload["actions"]}


def test_config_is_complete_and_fail_closed():
    payload = load_json(CONFIG)

    assert payload["schema"] == "lumencore.opportunity_control_plane_config.v1"
    assert payload["version"] == 1
    assert payload["input_schema"] == "lumencore.public_opportunity_leads.v1"
    assert payload["record_schema"] == "lumencore.public_opportunity_lead.v1"
    assert payload["default_input_paths"] == [
        "grant_submissions/funding_sprint_20260709/"
        "CURRENT_PUBLIC_OPPORTUNITY_LEADS_2026-07-25.json"
    ]
    assert payload["controls"] == {
        "action_time_human_approval_required": True,
        "authenticated_access_allowed": False,
        "autonomous_apply_allowed": False,
        "autonomous_certify_allowed": False,
        "autonomous_login_allowed": False,
        "autonomous_post_allowed": False,
        "autonomous_send_allowed": False,
        "autonomous_sign_allowed": False,
        "autonomous_submit_allowed": False,
        "duplicate_suppression_required": True,
        "eligibility_uncertainty_fail_closed": True,
        "external_mutation_allowed": False,
        "local_files_only": True,
        "missing_claim_boundary_fail_closed": True,
        "missing_source_url_fail_closed": True,
        "network_access_allowed": False,
        "stale_source_fail_closed": True,
    }
    assert set(payload["lane_policies"]) == {
        "government",
        "job",
        "licensing",
        "venture_partner",
        "pilot",
    }
    for lane_id, policy in payload["lane_policies"].items():
        questions = policy["reviewer_questions"]
        assert questions, lane_id
        assert len({question["id"] for question in questions}) == len(questions)
        assert any(question["required_for_draft"] for question in questions)
        assert policy["stale_after_hours"] > 0
        assert 0 <= policy["minimum_fit_score"] <= 100

    module = load_module()
    module.validate_config(payload)


def test_default_discovery_uses_configured_production_feed_only_without_overrides():
    module = load_module()
    config = load_json(CONFIG)
    expected = (ROOT / config["default_input_paths"][0]).resolve()

    discovered = module.discover_input_paths([], [], config=config)
    explicit = module.discover_input_paths([PUBLIC_LEADS], [], config=config)

    assert expected in {path.resolve() for path in discovered}
    assert {path.resolve() for path in explicit} == {PUBLIC_LEADS.resolve()}


def test_config_rejects_default_input_path_traversal():
    module = load_module()
    config = load_json(CONFIG)
    config["default_input_paths"] = ["../outside.json"]

    with pytest.raises(
        module.OpportunityControlError,
        match="normalized repo-relative paths",
    ):
        module.validate_config(config)


def test_fixture_builds_all_ranked_lanes_and_draft_actions_deterministically():
    module = load_module()
    first = build_fixture_payload(module)
    second = module.build_control_plane(
        [GMAIL_JOB_ALERTS, PUBLIC_LEADS],
        as_of_utc=AS_OF_UTC,
        config_path=CONFIG,
    )

    assert first == second
    module.validate_payload(first)
    assert first["status"] == "TEST_FIXTURE_ONLY"
    assert first["summary"] == {
        "input_file_count": 2,
        "input_record_count": 14,
        "valid_record_count_before_deduplication": 14,
        "ranked_opportunity_count": 13,
        "draft_ready_action_count": 2,
        "research_required_action_count": 9,
        "blocked_or_closed_action_count": 2,
        "suppressed_duplicate_count": 1,
        "rejected_record_count": 0,
        "stale_source_count": 1,
        "future_source_observation_count": 0,
        "exact_deadline_count": 2,
        "eligibility_uncertain_count": 8,
        "metadata_only_job_alert_count": 8,
        "action_state_counts": {
            "BLOCKED_SOURCE_FRESHNESS": 1,
            "CLOSED_DEADLINE": 1,
            "DRAFT_READY_HUMAN_REVIEW": 2,
            "RESEARCH_REQUIRED": 9,
        },
        "lane_counts": {
            "government": 1,
            "job": 9,
            "licensing": 1,
            "venture_partner": 1,
            "pilot": 1,
        },
        "external_action_count": 0,
    }
    assert set(first["ranked_queues"]["by_lane"]) == set(module.SUPPORTED_LANES)
    assert len(first["control_sha256"]) == 64
    assert first["source_evidence"]["builder"]["path"] == (
        "code/ops/BUILD_OPPORTUNITY_CONTROL_PLANE.py"
    )
    assert first["source_evidence"]["builder"]["sha256"] == module.sha256_file(SCRIPT)

    ranks = [row["rank"] for row in first["ranked_queues"]["all"]]
    assert ranks == list(range(1, 14))
    assert {
        action["record_id"] for action in first["draft_ready_actions"]
    } == {
        "fixture-job-first-party-001",
        "fixture-license-first-party-001",
    }


def test_duplicate_control_prefers_official_source_and_preserves_observations():
    module = load_module()
    payload = build_fixture_payload(module)
    by_record = action_by_record(payload)

    government = by_record["fixture-gov-official-001"]
    assert government["duplicate_count"] == 1
    assert government["source"]["authority"] == "OFFICIAL"
    assert government["canonical_opportunity_url"].endswith("utm_source=test")
    assert len(government["source_observations"]) == 2
    assert {
        observation["source_authority"]
        for observation in government["source_observations"]
    } == {"OFFICIAL", "TRUSTED_AGGREGATOR"}

    duplicate_control = payload["duplicate_control"]
    assert duplicate_control["suppressed_count"] == 1
    suppressed = duplicate_control["suppressed_records"][0]
    assert suppressed["record_id"] == "fixture-gov-aggregator-duplicate-001"
    assert suppressed["reason"] == (
        "DUPLICATE_CANONICAL_OPPORTUNITY_URL_AND_LANE"
    )


def test_exact_deadlines_preserve_utc_local_timezone_and_source_text():
    module = load_module()
    payload = build_fixture_payload(module)
    by_record = action_by_record(payload)

    deadline = by_record["fixture-gov-official-001"]["deadline"]
    assert deadline == {
        "state": "EXACT",
        "at_utc": "2026-08-01T21:00:00Z",
        "local": "2026-08-01T17:00:00-04:00",
        "timezone": "America/New_York",
        "source_text": (
            "Synthetic fixture deadline: August 1, 2026 at 5:00 PM Eastern."
        ),
        "seconds_remaining": 788400,
        "is_closed": False,
    }
    closed = by_record["fixture-pilot-expired-001"]
    assert closed["action_state"] == "CLOSED_DEADLINE"
    assert closed["deadline"]["is_closed"] is True
    assert closed["deadline"]["timezone"] == "America/Chicago"


def test_job_alert_metadata_is_quarantined_until_first_party_recheck():
    module = load_module()
    payload = build_fixture_payload(module)
    alerts = [
        action
        for action in payload["actions"]
        if action["lead_origin"] == "JOB_ALERT_METADATA"
    ]

    assert len(alerts) == 8
    assert {action["title"] for action in alerts} == {
        "Technology Strategy Innovation and Delivery Transformation Manager",
        "AI Business Solution Architect",
        "AI Solutions Engineer",
        "Enterprise AI Portfolio Lead",
        "Field CTO - Cyber, Cloud and Data",
        "Army and Defense Agencies Sector CTO",
        "Chief AI Officer",
        "CTO",
    }
    assert all(action["lane"] == "job" for action in alerts)
    assert all(action["action_state"] == "RESEARCH_REQUIRED" for action in alerts)
    assert all(action["draft_ready"] is False for action in alerts)
    assert all(action["canonical_opportunity_url"] is None for action in alerts)
    assert all(action["source"]["url"] is None for action in alerts)
    assert all(
        action["source"]["verification_state"]
        == "PUBLIC_SOURCE_RECHECK_REQUIRED"
        for action in alerts
    )
    assert all(
        action["source"]["observed_precision"] == "DATE_ONLY"
        and action["source"]["observed_date"] == "2026-07-23"
        and action["source"]["observed_utc"] == "2026-07-23T00:00:00Z"
        for action in alerts
    )
    assert all(action["deadline"]["state"] == "UNKNOWN" for action in alerts)
    assert all(
        "PUBLIC_SOURCE_URL_REQUIRED" in action["missing_facts"]
        and "EMPLOYER_POSTING_RECHECK_REQUIRED" in action["missing_facts"]
        and "EXACT_DEADLINE_OR_NONE_STATED_CONFIRMATION_REQUIRED"
        in action["missing_facts"]
        for action in alerts
    )
    assert all(
        action["controls"]["action_time_human_approval_required"] is True
        and action["controls"]["apply_allowed"] is False
        and action["apply_performed"] is False
        for action in alerts
    )

    by_record = action_by_record(payload)
    vibes = by_record["gmail-alert-vibes-meet-cto-20260723"]
    assert vibes["compensation"]["state"] == "CAVEAT"
    assert "salary only after investment" in vibes["compensation"]["source_text"]
    assert "COMPENSATION_TERMS_REQUIRE_CONFIRMATION" in vibes["missing_facts"]
    highspring = by_record["gmail-alert-highspring-ai-portfolio-20260723"]
    assert "Easy Apply is not application authority" in highspring["claim_boundary"]


def test_every_action_is_local_only_and_preserves_claim_boundaries():
    module = load_module()
    payload = build_fixture_payload(module)

    assert payload["summary"]["external_action_count"] == 0
    assert payload["controls"]["final_external_action_performed"] is False
    assert payload["controls"]["draft_ready_does_not_authorize_external_action"] is True
    for action in payload["actions"]:
        assert action["claim_boundary"]
        assert action["global_claim_boundary"]
        assert action["controls"] == {
            "human_review_required": True,
            "action_time_human_approval_required": True,
            "login_allowed": False,
            "send_allowed": False,
            "post_allowed": False,
            "apply_allowed": False,
            "certify_allowed": False,
            "sign_allowed": False,
            "submit_allowed": False,
            "external_mutation_allowed": False,
        }
        assert action["send_performed"] is False
        assert action["post_performed"] is False
        assert action["apply_performed"] is False
        assert action["certify_performed"] is False
        assert action["sign_performed"] is False
        assert action["submit_performed"] is False


def test_stale_source_and_open_reviewer_questions_fail_closed():
    module = load_module()
    payload = build_fixture_payload(module)
    by_record = action_by_record(payload)

    stale = by_record["fixture-venture-stale-001"]
    assert stale["source"]["observation_state"] == "STALE"
    assert stale["action_state"] == "BLOCKED_SOURCE_FRESHNESS"
    assert "SOURCE_STALE_RECHECK_REQUIRED" in stale["blockers"]

    government = by_record["fixture-gov-official-001"]
    assert government["source"]["observation_state"] == "FRESH"
    assert government["action_state"] == "RESEARCH_REQUIRED"
    assert len(
        [
            fact
            for fact in government["missing_facts"]
            if fact.startswith("REVIEWER_QUESTION:")
        ]
    ) == 12


def test_timezone_mismatch_is_rejected_without_promoting_other_fields(tmp_path: Path):
    module = load_module()
    record = copy.deepcopy(load_json(PUBLIC_LEADS)["records"][0])
    record["deadline"]["local"] = "2026-08-01T16:00:00-04:00"
    path = write_document(tmp_path / "bad-deadline.json", [record])

    payload = module.build_control_plane(
        [path],
        as_of_utc=AS_OF_UTC,
        config_path=CONFIG,
    )

    assert payload["status"] == "ALL_INPUT_REJECTED_FAIL_CLOSED"
    assert payload["summary"]["ranked_opportunity_count"] == 0
    assert payload["summary"]["rejected_record_count"] == 1
    assert "do not identify one instant" in payload["rejected_records"][0]["errors"][0]


def test_verified_lead_without_public_urls_is_rejected(tmp_path: Path):
    module = load_module()
    record = copy.deepcopy(load_json(PUBLIC_LEADS)["records"][2])
    record["canonical_opportunity_url"] = None
    record["source"]["url"] = None
    path = write_document(tmp_path / "missing-public-url.json", [record])

    payload = module.build_control_plane(
        [path],
        as_of_utc=AS_OF_UTC,
        config_path=CONFIG,
    )

    assert payload["status"] == "ALL_INPUT_REJECTED_FAIL_CLOSED"
    assert payload["summary"]["ranked_opportunity_count"] == 0
    assert payload["summary"]["rejected_record_count"] == 1
    assert "canonical_opportunity_url must be text" in (
        payload["rejected_records"][0]["errors"][0]
    )


def test_unverified_metadata_cannot_smuggle_a_posting_url(tmp_path: Path):
    module = load_module()
    record = copy.deepcopy(load_json(GMAIL_JOB_ALERTS)["records"][0])
    record["canonical_opportunity_url"] = "https://careers.example.com/jobs/unverified"
    record["source"]["url"] = "https://careers.example.com/jobs/unverified"
    path = write_document(tmp_path / "smuggled-url.json", [record])

    payload = module.build_control_plane(
        [path],
        as_of_utc=AS_OF_UTC,
        config_path=CONFIG,
    )

    assert payload["status"] == "ALL_INPUT_REJECTED_FAIL_CLOSED"
    assert payload["summary"]["rejected_record_count"] == 1
    assert "must be null" in payload["rejected_records"][0]["errors"][0]


def test_prohibited_secret_shaped_keys_are_rejected_and_not_echoed(tmp_path: Path):
    module = load_module()
    record = copy.deepcopy(load_json(PUBLIC_LEADS)["records"][2])
    record["api_key"] = "DO_NOT_PUBLISH"
    path = write_document(tmp_path / "secret-shaped.json", [record])

    payload = module.build_control_plane(
        [path],
        as_of_utc=AS_OF_UTC,
        config_path=CONFIG,
    )
    rendered = json.dumps(payload)

    assert payload["summary"]["ranked_opportunity_count"] == 0
    assert payload["summary"]["rejected_record_count"] == 1
    assert "prohibited key material" in payload["rejected_records"][0]["errors"][0]
    assert "DO_NOT_PUBLISH" not in rendered


def test_jsonl_envelope_is_supported_without_relaxing_schema(tmp_path: Path):
    module = load_module()
    record = copy.deepcopy(load_json(PUBLIC_LEADS)["records"][2])
    path = tmp_path / "one-lead.jsonl"
    path.write_text(
        json.dumps(
            {
                "schema": "lumencore.public_opportunity_lead.v1",
                "environment": "TEST_FIXTURE",
                "record": record,
            }
        )
        + "\n",
        encoding="utf-8",
    )

    payload = module.build_control_plane(
        [path],
        as_of_utc=AS_OF_UTC,
        config_path=CONFIG,
    )

    assert payload["status"] == "TEST_FIXTURE_ONLY"
    assert payload["summary"]["ranked_opportunity_count"] == 1
    assert payload["summary"]["draft_ready_action_count"] == 1
    assert payload["actions"][0]["record_id"] == "fixture-job-first-party-001"


def test_payload_validation_detects_rehashed_external_action_tampering():
    module = load_module()
    payload = build_fixture_payload(module)
    tampered = copy.deepcopy(payload)
    tampered["actions"][0]["controls"]["apply_allowed"] = True
    tampered["control_sha256"] = module.canonical_json_sha256(
        {
            key: value
            for key, value in tampered.items()
            if key != "control_sha256"
        }
    )

    with pytest.raises(module.OpportunityControlError, match="apply_allowed"):
        module.validate_payload(tampered)


def test_payload_validation_detects_rehashed_queue_reconciliation_tampering():
    module = load_module()
    payload = build_fixture_payload(module)
    tampered = copy.deepcopy(payload)
    tampered["draft_ready_actions"] = tampered["draft_ready_actions"][:-1]
    tampered["control_sha256"] = module.canonical_json_sha256(
        {
            key: value
            for key, value in tampered.items()
            if key != "control_sha256"
        }
    )

    with pytest.raises(module.OpportunityControlError, match="draft_ready_actions"):
        module.validate_payload(tampered)


def test_empty_input_is_explicit_and_never_implies_no_opportunities():
    module = load_module()
    payload = module.build_control_plane(
        [],
        as_of_utc=AS_OF_UTC,
        config_path=CONFIG,
    )

    assert payload["status"] == "NO_INPUT_FILES_DISCOVERED"
    assert payload["summary"]["ranked_opportunity_count"] == 0
    assert payload["summary"]["external_action_count"] == 0
    assert payload["ranked_queues"]["all"] == []
    assert "does not prove that the source remains unchanged or open" in (
        payload["claim_boundaries"]["source_freshness"]
    )


def test_outputs_are_atomic_hashed_and_markdown_is_bounded(tmp_path: Path):
    module = load_module()
    payload = build_fixture_payload(module)

    json_path, markdown_path = module.write_outputs(payload, tmp_path)
    actual = load_json(json_path)
    markdown = markdown_path.read_text(encoding="utf-8")

    assert actual == payload
    module.validate_payload(actual)
    assert actual["control_sha256"] in markdown
    assert "External actions performed: `0`" in markdown
    assert "does not authorize login" in markdown
    assert not list(tmp_path.glob("*.tmp"))
    assert not list(tmp_path.glob(".*.tmp"))


def test_builder_imports_no_network_browser_or_messaging_clients():
    tree = ast.parse(SCRIPT.read_text(encoding="utf-8"))
    imported: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imported.add(node.module)

    forbidden = {
        "httpx",
        "playwright",
        "requests",
        "selenium",
        "smtplib",
        "socket",
        "subprocess",
        "urllib.request",
        "webbrowser",
    }
    assert imported.isdisjoint(forbidden)
    assert "urllib.parse" in imported
