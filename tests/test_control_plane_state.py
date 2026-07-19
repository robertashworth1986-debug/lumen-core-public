from __future__ import annotations

import copy
import importlib.util
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "code" / "ops" / "VERIFY_CONTROL_PLANE_STATE.py"
STATE = ROOT / "dashboard" / "data" / "control_plane_state.json"
WORKFLOW = ROOT / ".github" / "workflows" / "control-plane-state-gate.yml"
CANONICAL_DOC = ROOT / "docs" / "CANONICAL_OPERATING_STATE.md"
RECONCILIATION_DOC = ROOT / "docs" / "CONTROL_PLANE_RECONCILIATION_2026-07-19.md"
CHECKED_NOW = datetime(2026, 7, 19, 3, 0, tzinfo=timezone.utc)


def load_module():
    spec = importlib.util.spec_from_file_location("verify_control_plane_state", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def load_state() -> dict:
    return json.loads(STATE.read_text(encoding="utf-8"))


def refresh_self_hash(module, state: dict) -> dict:
    state["state_sha256"] = module.stable_hash(module.state_payload(state))
    return state


def verify(module, state: dict, **overrides):
    options = {
        "now": CHECKED_NOW,
        "max_age_hours": 24,
        "max_future_skew_minutes": 5,
    }
    options.update(overrides)
    return module.verify_state(state, **options)


def test_checked_in_control_plane_state_is_valid_and_fail_closed():
    module = load_module()
    state = load_state()
    report = verify(module, state)

    assert report["integrity_valid"] is True, report["errors"]
    assert report["state_hash"]["matches"] is True
    assert report["state_hash"]["scope"] == "EMBEDDED_SELF_CONSISTENCY_ONLY"
    assert report["state_hash"]["custody_anchor"] == "GIT_COMMIT"
    assert report["lane_count"] == report["required_lane_count"] == 9
    assert state["failure_mode"] == "FAIL_CLOSED"
    assert state["hash_scope"] == module.HASH_SCOPE
    assert state["owner_role"] == module.OWNER_ROLE
    assert "owner" not in state
    assert set(state["controls"]) == module.NO_ACTION_CONTROL_KEYS
    assert all(value is False for value in state["controls"].values())


def test_ci_requires_finite_age_and_bounded_future_skew():
    workflow = WORKFLOW.read_text(encoding="utf-8")

    assert "--max-age-hours 24" in workflow
    assert "--max-future-skew-minutes 5" in workflow


@pytest.mark.parametrize("bad_limit", [float("nan"), float("inf"), 0, -1])
def test_non_finite_or_non_positive_max_age_fails_closed(bad_limit):
    module = load_module()
    report = verify(module, load_state(), max_age_hours=bad_limit)

    assert report["integrity_valid"] is False
    assert "max_age_hours must be a finite positive number" in report["errors"]


@pytest.mark.parametrize("bad_limit", [float("nan"), float("inf"), -1])
def test_non_finite_or_negative_future_skew_limit_fails_closed(bad_limit):
    module = load_module()
    report = verify(module, load_state(), max_future_skew_minutes=bad_limit)

    assert report["integrity_valid"] is False
    assert "max_future_skew_minutes must be a finite non-negative number" in report[
        "errors"
    ]


def test_stale_state_fails_even_with_a_matching_embedded_hash():
    module = load_module()
    state = load_state()
    generated = datetime.fromisoformat(state["generated_utc"].replace("Z", "+00:00"))

    report = verify(module, state, now=generated + timedelta(hours=24, seconds=1))

    assert report["integrity_valid"] is False
    assert report["state_hash"]["matches"] is True
    assert "control-plane state is stale" in " ".join(report["errors"])


def test_excessive_future_skew_fails_even_after_rehash():
    module = load_module()
    mutated = copy.deepcopy(load_state())
    mutated["generated_utc"] = (CHECKED_NOW + timedelta(minutes=6)).isoformat().replace(
        "+00:00", "Z"
    )
    refresh_self_hash(module, mutated)

    report = verify(module, mutated)

    assert report["integrity_valid"] is False
    assert report["state_hash"]["matches"] is True
    assert "control-plane state is too far in the future" in " ".join(report["errors"])


def test_deadline_locks_and_lane_states_are_explicit():
    state = load_state()
    lanes = {row["lane_id"]: row for row in state["lanes"]}

    assert lanes["prooflock"]["deadline_utc"] == "2026-07-22T00:00:00Z"
    assert lanes["missionweave"]["deadline_utc"] == "2026-07-22T16:00:00Z"
    assert lanes["harbor_sentinel"]["deadline_utc"] == "2026-07-22T16:00:00Z"
    assert lanes["dice"]["deadline_utc"] == "2026-08-25T18:00:00Z"
    assert lanes["missionweave"]["state"] == "BLOCKED"
    assert lanes["harbor_sentinel"]["state"] == "RECONCILIATION_REQUIRED"
    assert lanes["prooflock"]["state"] == "HOLD"
    assert lanes["outreach_governance"]["state"] == "NO_ACTION_DUE"
    assert lanes["eia_prospective"]["state"] == "PRELIMINARY"


def test_eia_prospective_lane_cannot_be_removed_and_rehashed():
    module = load_module()
    mutated = copy.deepcopy(load_state())
    mutated["lanes"] = [
        lane for lane in mutated["lanes"] if lane["lane_id"] != "eia_prospective"
    ]
    refresh_self_hash(module, mutated)

    report = verify(module, mutated)

    assert report["integrity_valid"] is False
    assert report["state_hash"]["matches"] is True
    assert "missing required lanes: eia_prospective" in report["errors"]


def test_duplicate_lane_and_missing_gate_fail_closed_after_rehash():
    module = load_module()
    mutated = copy.deepcopy(load_state())
    mutated["lanes"][1]["lane_id"] = mutated["lanes"][0]["lane_id"]
    mutated["lanes"][0]["open_gates"] = []
    refresh_self_hash(module, mutated)

    report = verify(module, mutated)

    assert report["integrity_valid"] is False
    assert report["state_hash"]["matches"] is True
    assert "duplicate lane_id" in " ".join(report["errors"])
    assert "open_gates" in " ".join(report["errors"])


@pytest.mark.parametrize(
    "control_key",
    [
        "external_email_sent_by_this_state",
        "portal_submission_performed",
        "signature_or_certification_performed",
        "final_confirmation_performed",
        "merge_performed",
        "deployment_performed",
        "payment_or_legal_acceptance_performed",
        "public_video_publication_performed",
        "devpost_submission_performed",
        "claim_expansion_performed",
    ],
)
def test_each_no_action_control_must_remain_false(control_key):
    module = load_module()
    mutated = copy.deepcopy(load_state())
    mutated["controls"][control_key] = True
    refresh_self_hash(module, mutated)

    report = verify(module, mutated)

    assert report["integrity_valid"] is False
    assert report["state_hash"]["matches"] is True
    assert f"{control_key} must be explicitly false" in report["errors"]


def test_missing_and_unknown_no_action_controls_fail_closed():
    module = load_module()
    missing = copy.deepcopy(load_state())
    missing["controls"].pop("final_confirmation_performed")
    refresh_self_hash(module, missing)
    unknown = copy.deepcopy(load_state())
    unknown["controls"]["unreviewed_control"] = False
    refresh_self_hash(module, unknown)

    missing_report = verify(module, missing)
    unknown_report = verify(module, unknown)

    assert missing_report["integrity_valid"] is False
    assert missing_report["state_hash"]["matches"] is True
    assert "controls missing required keys: final_confirmation_performed" in missing_report[
        "errors"
    ]
    assert unknown_report["integrity_valid"] is False
    assert unknown_report["state_hash"]["matches"] is True
    assert "controls contain unknown keys: unreviewed_control" in unknown_report["errors"]


def test_embedded_hash_cannot_be_reframed_as_the_custody_anchor():
    module = load_module()
    mutated = copy.deepcopy(load_state())
    mutated["hash_scope"] = "EMBEDDED_SHA256_IS_CUSTODY_PROOF"
    refresh_self_hash(module, mutated)

    report = verify(module, mutated)

    assert report["integrity_valid"] is False
    assert report["state_hash"]["matches"] is True
    assert "Git commit as the custody anchor" in " ".join(report["errors"])


@pytest.mark.parametrize(
    ("private_value", "expected_label"),
    [
        ("analyst@private.example", "email address"),
        ("+1 (312) 555-0199", "phone number"),
        ("020 7946 0958", "phone number"),
        ("442079460958", "phone number"),
        (r"D:\private\receipt.json", "local filesystem path"),
        ("/home/analyst/private/receipt.json", "local filesystem path"),
        (r"\\private-host\share\receipt.json", "local filesystem path"),
        ("api_token=AbCdEf0123456789Secret", "credential or token"),
        ("xoxb-AbCdEf0123456789", "credential or token"),
    ],
)
def test_generic_private_patterns_fail_even_after_rehash(
    private_value, expected_label
):
    module = load_module()
    mutated = copy.deepcopy(load_state())
    mutated["claim_boundary"] = private_value
    refresh_self_hash(module, mutated)

    report = verify(module, mutated)

    assert report["integrity_valid"] is False
    assert report["state_hash"]["matches"] is True
    assert f"public state contains prohibited {expected_label} pattern" in report["errors"]


@pytest.mark.parametrize(
    "identity_mutation",
    [
        {"owner": "Named Person"},
        {"owner_role": "Named Person"},
    ],
)
def test_named_owner_publication_is_rejected(identity_mutation):
    module = load_module()
    mutated = copy.deepcopy(load_state())
    mutated.update(identity_mutation)
    refresh_self_hash(module, mutated)

    report = verify(module, mutated)

    assert report["integrity_valid"] is False
    assert report["state_hash"]["matches"] is True
    assert any("owner" in error for error in report["errors"])


def test_public_state_marks_stale_sources_without_private_identifiers():
    state = load_state()
    rendered = json.dumps(state, sort_keys=True).lower()
    stale_paths = {row["path"] for row in state["stale_or_conflicting_sources"]}

    assert "robert ashworth" not in rendered
    assert "docs/CANONICAL_OPERATING_STATE.md" in stale_paths
    assert "dashboard/data/grant_readiness_status.json" in stale_paths
    assert "historical" in rendered


def test_docs_bound_hash_and_historical_prooflock_semantics():
    state = load_state()
    canonical = CANONICAL_DOC.read_text(encoding="utf-8")
    reconciliation = RECONCILIATION_DOC.read_text(encoding="utf-8")

    current_heading = "## Current ProofLock status"
    historical_heading = "## Historical operating snapshot"
    assert canonical.index(current_heading) < canonical.index(historical_heading)
    assert "The `Current ProofLock status` section is current only" in canonical
    assert "This historical statement does not authorize outbound action now." in canonical
    assert "operational statements below" not in canonical
    assert "Embedded state SHA-256 (self-consistency only)" in reconciliation
    assert "Git commit" in reconciliation
    assert "hash-locked" not in reconciliation
    assert state["state_sha256"] in reconciliation
    assert "Robert Ashworth" not in canonical + reconciliation
