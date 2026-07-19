from __future__ import annotations

import copy
import importlib.util
import json
import subprocess
import sys
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
EXPECTED_NO_ACTION_CONTROLS = {
    "external_email_sent_by_this_state",
    "portal_access_performed",
    "portal_modification_performed",
    "portal_upload_performed",
    "portal_submission_performed",
    "proposal_submission_performed",
    "signature_performed",
    "certification_performed",
    "final_confirmation_performed",
    "merge_performed",
    "deployment_performed",
    "dns_change_performed",
    "payment_performed",
    "legal_acceptance_performed",
    "public_video_publication_performed",
    "devpost_submission_performed",
    "claim_expansion_performed",
}


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


def iter_report_text(value):
    if isinstance(value, dict):
        for key, item in value.items():
            yield str(key)
            yield from iter_report_text(item)
    elif isinstance(value, list):
        for item in value:
            yield from iter_report_text(item)
    elif isinstance(value, str):
        yield value


def test_checked_in_control_plane_state_is_valid_and_fail_closed():
    module = load_module()
    state = load_state()
    report = verify(module, state)

    assert report["integrity_valid"] is True, report["errors"]
    assert report["state_hash"]["matches"] is True
    assert report["state_hash"]["scope"] == "SELF_CONSISTENCY_ONLY_NOT_CUSTODY"
    assert "custody_anchor" not in report["state_hash"]
    assert report["custody"] == {
        "authoritative_anchor": "GIT_COMMIT_OR_COMMIT_BOUND_RECEIPT",
        "embedded_hash_is_custody_anchor": False,
    }
    assert report["freshness_policy"] == {
        "max_age_hours": 24.0,
        "max_future_skew_minutes": 5.0,
    }
    assert report["lane_count"] == report["required_lane_count"] == 9
    assert state["failure_mode"] == "FAIL_CLOSED"
    assert state["hash_scope"] == module.HASH_SCOPE
    assert state["custody_anchor"] == module.CUSTODY_ANCHOR
    assert state["owner_role"] == module.OWNER_ROLE
    assert "owner" not in state
    assert set(state["controls"]) == EXPECTED_NO_ACTION_CONTROLS
    assert module.NO_ACTION_CONTROL_KEYS == EXPECTED_NO_ACTION_CONTROLS
    assert all(value is False for value in state["controls"].values())
    assert module.public_safety_findings(state) == set()


def test_ci_requires_finite_age_and_bounded_future_skew():
    module = load_module()
    workflow = WORKFLOW.read_text(encoding="utf-8")

    assert module.DEFAULT_MAX_AGE_HOURS == 24.0
    assert module.DEFAULT_MAX_FUTURE_SKEW_MINUTES == 5.0
    assert "--max-age-hours 24" in workflow
    assert "--max-future-skew-minutes 5" in workflow


@pytest.mark.parametrize(
    "bad_limit",
    [None, True, float("nan"), float("inf"), 0, -1],
)
def test_non_finite_or_non_positive_max_age_fails_closed(bad_limit):
    module = load_module()
    report = verify(module, load_state(), max_age_hours=bad_limit)

    assert report["integrity_valid"] is False
    assert "max_age_hours must be a finite positive number" in report["errors"]


@pytest.mark.parametrize(
    "bad_limit",
    [None, True, float("nan"), float("inf"), -1],
)
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

    report = module.verify_state(
        state,
        now=generated + timedelta(hours=24, seconds=1),
    )

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

    report = module.verify_state(mutated, now=CHECKED_NOW)

    assert report["integrity_valid"] is False
    assert report["state_hash"]["matches"] is True
    assert "control-plane state is too far in the future" in " ".join(report["errors"])


@pytest.mark.parametrize(
    ("generated_delta", "expected_error"),
    [
        (timedelta(hours=-25), "control-plane state is stale"),
        (timedelta(minutes=10), "control-plane state is too far in the future"),
    ],
)
def test_ci_command_rejects_stale_and_future_state(
    tmp_path, generated_delta, expected_error
):
    module = load_module()
    mutated = copy.deepcopy(load_state())
    mutated["generated_utc"] = (
        datetime.now(timezone.utc) + generated_delta
    ).isoformat().replace("+00:00", "Z")
    refresh_self_hash(module, mutated)
    state_path = tmp_path / "timestamp-policy-state.json"
    state_path.write_text(json.dumps(mutated), encoding="utf-8")

    completed = subprocess.run(
        [
            sys.executable,
            str(SCRIPT),
            str(state_path),
            "--max-age-hours",
            "24",
            "--max-future-skew-minutes",
            "5",
        ],
        check=False,
        capture_output=True,
        text=True,
    )

    assert completed.returncode == 1
    assert expected_error in completed.stdout


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
    assert "duplicates another lane_id" in " ".join(report["errors"])
    assert "open_gates" in " ".join(report["errors"])


@pytest.mark.parametrize("control_key", sorted(EXPECTED_NO_ACTION_CONTROLS))
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
    assert "controls contain unknown keys" in unknown_report["errors"]


@pytest.mark.parametrize(
    ("mutate", "expected_error"),
    [
        (
            lambda state: state.__setitem__("portal_submission_authorized", True),
            "control-plane state contains unknown keys",
        ),
        (
            lambda state: state["lanes"][0].__setitem__(
                "portal_submission_authorized", True
            ),
            "lanes[0] contains unknown keys",
        ),
        (
            lambda state: state["lanes"][0]["evidence"][0].__setitem__(
                "action_authority", "submit"
            ),
            "lanes[0].evidence[0] contains unknown keys",
        ),
        (
            lambda state: state["stale_or_conflicting_sources"][0].__setitem__(
                "action_authority", "submit"
            ),
            "stale_or_conflicting_sources[0] contains unknown keys",
        ),
    ],
)
def test_unknown_fields_cannot_create_action_authority_after_rehash(
    mutate, expected_error
):
    module = load_module()
    mutated = copy.deepcopy(load_state())
    mutate(mutated)
    refresh_self_hash(module, mutated)

    report = verify(module, mutated)

    assert report["integrity_valid"] is False
    assert report["state_hash"]["matches"] is True
    assert expected_error in report["errors"]


@pytest.mark.parametrize("bad_value", [float("nan"), float("inf"), float("-inf")])
def test_non_finite_values_fail_closed_after_rehash(bad_value):
    module = load_module()
    mutated = copy.deepcopy(load_state())
    mutated["lanes"][0]["summary"] = bad_value
    refresh_self_hash(module, mutated)

    report = verify(module, mutated)

    assert report["integrity_valid"] is False
    assert report["state_hash"]["matches"] is True
    assert "control-plane state value item value contains a non-finite number" in report[
        "errors"
    ]


@pytest.mark.parametrize(
    ("field", "value", "expected_error"),
    [
        (
            "hash_scope",
            "EMBEDDED_SHA256_IS_CUSTODY_PROOF",
            "hash_scope must limit the embedded SHA-256 to self-consistency only",
        ),
        (
            "custody_anchor",
            "EMBEDDED_SHA256",
            "custody_anchor must identify the Git commit or a receipt bound to that commit",
        ),
    ],
)
def test_embedded_hash_cannot_be_reframed_as_the_custody_anchor(
    field, value, expected_error
):
    module = load_module()
    mutated = copy.deepcopy(load_state())
    mutated[field] = value
    refresh_self_hash(module, mutated)

    report = verify(module, mutated)

    assert report["integrity_valid"] is False
    assert report["state_hash"]["matches"] is True
    assert expected_error in report["errors"]
    assert report["custody"]["embedded_hash_is_custody_anchor"] is False


@pytest.mark.parametrize(
    ("private_value", "expected_label"),
    [
        ("analyst@private.example", "direct identifier"),
        ("+1 (312) 555-0199", "direct identifier"),
        ("123-45-6789", "direct identifier"),
        ("742 Evergreen Avenue", "direct identifier"),
        (r"D:\private\receipt.json", "private or patent-sensitive path"),
        ("/home/analyst/private/receipt.json", "private or patent-sensitive path"),
        (r"\\private-host\share\receipt.json", "private or patent-sensitive path"),
        ("private/patent_claims.docx", "private or patent-sensitive path"),
        ("docs/PATENT_EMERGENCY_PACKET.md", "private or patent-sensitive path"),
        ("api_token=AbCdEf0123456789Secret", "credential or token"),
        ("xoxb-AbCdEf0123456789", "credential or token"),
        ("-----BEGIN PRIVATE KEY-----", "credential or token"),
        ("application 19/281,546", "private or patent-sensitive content"),
        (
            "draft patent claim 1: a non-public implementation",
            "private or patent-sensitive content",
        ),
        ("attorney-client privileged", "private or patent-sensitive content"),
    ],
)
def test_public_safety_categories_fail_without_echoing_matches(
    private_value, expected_label
):
    module = load_module()
    mutated = copy.deepcopy(load_state())
    mutated["claim_boundary"] = private_value
    refresh_self_hash(module, mutated)

    report = verify(module, mutated)

    assert report["integrity_valid"] is False
    assert report["state_hash"]["matches"] is True
    assert f"public state contains prohibited {expected_label}" in report["errors"]
    assert all(private_value not in text for text in iter_report_text(report))


@pytest.mark.parametrize("identity_field", ["owner", "contact_name", "inventor_name"])
def test_direct_identifier_fields_are_rejected(identity_field):
    module = load_module()
    mutated = copy.deepcopy(load_state())
    mutated[identity_field] = "Named Person"
    refresh_self_hash(module, mutated)

    report = verify(module, mutated)

    assert report["integrity_valid"] is False
    assert report["state_hash"]["matches"] is True
    assert "public state contains prohibited direct identifier" in report["errors"]
    assert all("Named Person" not in text for text in iter_report_text(report))


def test_cli_privacy_failure_never_prints_sensitive_values(tmp_path):
    secret = "sk-proj-DoNotEchoThisCredential123456"
    hex_secret = "ab" * 32
    mutated = copy.deepcopy(load_state())
    mutated["state_id"] = secret
    mutated["state_sha256"] = hex_secret
    mutated["controls"][secret] = False
    state_path = tmp_path / "unsafe-state.json"
    state_path.write_text(json.dumps(mutated), encoding="utf-8")

    completed = subprocess.run(
        [sys.executable, str(SCRIPT), str(state_path)],
        check=False,
        capture_output=True,
        text=True,
    )

    assert completed.returncode == 1
    assert secret not in completed.stdout
    assert secret not in completed.stderr
    assert hex_secret not in completed.stdout
    assert hex_secret not in completed.stderr
    report = json.loads(completed.stdout)
    assert report["state_id"] == "REDACTED"
    assert report["state_hash"]["expected"] is None
    assert "controls contain unknown keys" in report["errors"]
    assert "public state contains prohibited credential or token" in report["errors"]


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
    current_index = canonical.index(current_heading)
    historical_index = canonical.index(historical_heading)
    current_prooflock = canonical[current_index:historical_index]
    historical_snapshot = canonical[historical_index:]

    assert current_index < historical_index
    assert "The `Current ProofLock status` section is current only" in canonical
    assert "4584a41dbedd2f856bba5fa8202e7dcc8e4a448f" in current_prooflock
    assert "build-week/prooflock-judge-ready" in current_prooflock
    assert "release of the existing proof-to-pilot product" in current_prooflock
    assert "not a new company, research lane, or replacement operating system" in (
        current_prooflock
    )
    assert "The console may prove receipt integrity" in current_prooflock
    assert "No other outbound message is currently authorized" in current_prooflock
    assert "This historical statement does not authorize outbound action now." in (
        historical_snapshot
    )
    assert "operational statements below" not in canonical
    assert (
        "Embedded state SHA-256 (self-consistency only; not a custody anchor)"
        in reconciliation
    )
    assert "Authoritative custody/history anchor" in reconciliation
    assert "verification receipt that identifies that exact commit" in reconciliation
    assert "no more than 24 hours old and no more than 5 minutes in the future" in (
        reconciliation
    )
    assert "hash-locked" not in reconciliation
    assert "custody hash" not in reconciliation.lower()
    assert state["state_sha256"] in reconciliation
    assert "Robert Ashworth" not in canonical + reconciliation
