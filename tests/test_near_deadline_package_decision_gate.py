import importlib.util
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "code" / "ops" / "BUILD_NEAR_DEADLINE_PACKAGE_DECISION_GATE.py"


def load_module():
    spec = importlib.util.spec_from_file_location("near_deadline_package_gate", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_gate_ranks_truthful_direct_fit_before_partner_dependent_bid():
    module = load_module()
    gate = module.build_gate()
    lanes = {item["lane"]: item for item in gate["lanes"]}

    assert gate["decision"]["primary_lane"] == "NSF Project Pitch"
    assert gate["decision"]["secondary_lane"] == "ERDC Sovereign Defense Cloud CSO"
    assert gate["decision"]["partner_only_lane"] == "FHWA TSMO Data Initiative"
    assert lanes["NSF Project Pitch"]["local_ready"] is False
    assert lanes["NSF Project Pitch"]["local_draft_complete"] is True
    assert lanes["FHWA TSMO Data Initiative"]["qualified_partner_evidence_present"] is False
    assert lanes["FHWA TSMO Data Initiative"]["qualified_target_contacted"] is True
    assert lanes["FHWA TSMO Data Initiative"]["delivery_failure_count"] == 1
    assert lanes["FHWA TSMO Data Initiative"]["replacement_send_count"] == 1
    assert lanes["FHWA TSMO Data Initiative"]["confirmed_delivery_count"] == 1
    assert lanes["FHWA TSMO Data Initiative"][
        "qualified_response_lead_referral_count"
    ] == 1
    assert lanes["FHWA TSMO Data Initiative"][
        "threaded_acknowledgment_send_count"
    ] == 1
    assert lanes["FHWA TSMO Data Initiative"]["fit_check_confirmed_count"] == 0
    assert lanes["FHWA TSMO Data Initiative"]["inbound_response_count"] == 2
    assert lanes["FHWA TSMO Data Initiative"]["team_set_decline_count"] == 1
    assert lanes["FHWA TSMO Data Initiative"]["outreach_route_closed"] is True
    assert lanes["FHWA TSMO Data Initiative"]["posture"] == (
        "TEAM_SET_DECLINED_NO_GO_UNLESS_NEW_QUALIFIED_PARTNER_JOINS"
    )
    assert lanes["FHWA TSMO Data Initiative"]["partner_outreach_control"].endswith(
        "FHWA_TSMO_PARTNER_OUTREACH_CONTROL_2026-07-17.json"
    )
    assert "five or more years" in " ".join(
        lanes["FHWA TSMO Data Initiative"]["hard_gates"]
    ).lower()


def test_nsf_fields_and_current_schedule_are_bounded():
    module = load_module()
    gate = module.build_gate()
    nsf = next(item for item in gate["lanes"] if item["lane"] == "NSF Project Pitch")

    assert set(nsf["field_counts"]) == set(module.NSF_LIMITS)
    assert all(item["passes"] for item in nsf["field_counts"].values())

    source = module.nsf_source_audit(gate)
    facts = source["verified_public_facts"]
    assert facts["listed_full_proposal_deadlines"] == [
        "2026-07-27",
        "2026-11-04",
        "2027-03-04",
        "2027-07-07",
    ]
    assert facts["next_listed_full_proposal_deadline"] == "2026-11-04"
    assert facts["full_proposal_requires_official_invitation"] is True
    assert source["authenticated_portal_access_performed"] is False


def test_erdc_sources_are_present_hashed_and_claim_bounded():
    module = load_module()
    manifest = module.erdc_source_manifest()

    assert manifest["all_present"] is True
    assert manifest["all_current_checks_pass"] is True
    assert manifest["schema"] == "lumencore.erdc_sdc_source_manifest.v2"
    assert manifest["as_of_date"] == "2026-07-29"
    assert len(manifest["files"]) == 2
    for item in manifest["files"]:
        assert item["exists"] is True
        assert item["actual_bytes"] > 0
        assert len(item["actual_sha256"]) == 64
        assert item["bytes_match"] is True
        assert item["sha256_match"] is True
        assert item["official_url"].startswith("https://www.erdcwerx.org/")
    assert "do not establish selection" in manifest["claim_boundary"].lower()


def test_rendered_teaming_request_does_not_invent_a_partner():
    module = load_module()
    text = module.render_teaming_request()
    lowered = text.lower()

    assert "[name]" in lowered
    assert "we will not represent experience that we cannot document" in lowered
    assert "do not state that a teaming relationship exists" in lowered
    assert "no confidential information is needed" in lowered


def test_written_json_remains_free_of_entity_identifiers(tmp_path):
    module = load_module()
    gate = module.build_gate()
    serialized = json.dumps(gate)

    assert "uei" not in serialized.lower()
    assert "cage" not in serialized.lower()
    assert "ein" not in serialized.lower()
    assert "identifiers_included\": false" in serialized.lower()
