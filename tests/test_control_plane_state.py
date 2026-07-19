from __future__ import annotations

import copy
import importlib.util
import json
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "code" / "ops" / "VERIFY_CONTROL_PLANE_STATE.py"
STATE = ROOT / "dashboard" / "data" / "control_plane_state.json"


def load_module():
    spec = importlib.util.spec_from_file_location("verify_control_plane_state", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def load_state() -> dict:
    return json.loads(STATE.read_text(encoding="utf-8"))


def test_checked_in_control_plane_state_is_valid_and_fail_closed():
    module = load_module()
    state = load_state()
    report = module.verify_state(
        state,
        now=datetime(2026, 7, 19, 3, 0, tzinfo=timezone.utc),
        max_age_hours=24,
    )

    assert report["integrity_valid"] is True, report["errors"]
    assert report["state_hash"]["matches"] is True
    assert report["lane_count"] >= report["required_lane_count"]
    assert state["failure_mode"] == "FAIL_CLOSED"
    assert all(value is False for value in state["controls"].values())


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


def test_duplicate_lane_and_missing_gate_fail_closed():
    module = load_module()
    state = load_state()
    mutated = copy.deepcopy(state)
    mutated["lanes"][1]["lane_id"] = mutated["lanes"][0]["lane_id"]
    mutated["lanes"][0]["open_gates"] = []
    mutated["state_sha256"] = module.stable_hash(module.state_payload(mutated))

    report = module.verify_state(mutated)

    assert report["integrity_valid"] is False
    assert "duplicate lane_id" in " ".join(report["errors"])
    assert "open_gates" in " ".join(report["errors"])


def test_any_action_authority_or_payload_mutation_fails():
    module = load_module()
    state = load_state()

    mutated = copy.deepcopy(state)
    mutated["controls"]["merge_performed"] = True
    report = module.verify_state(mutated)

    assert report["integrity_valid"] is False
    assert report["state_hash"]["matches"] is False
    assert "merge_performed must be explicitly false" in report["errors"]


def test_public_state_excludes_private_identifiers_and_marks_stale_sources():
    state = load_state()
    rendered = json.dumps(state, sort_keys=True).lower()
    stale_paths = {row["path"] for row in state["stale_or_conflicting_sources"]}

    assert "@gmail.com" not in rendered
    assert "c:\\users\\" not in rendered
    assert "e:\\" not in rendered
    assert "docs/CANONICAL_OPERATING_STATE.md" in stale_paths
    assert "dashboard/data/grant_readiness_status.json" in stale_paths
    assert "historical" in rendered
