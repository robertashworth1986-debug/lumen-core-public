from __future__ import annotations

import ast
import hashlib
import importlib.util
import json
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = ROOT / "code" / "ops" / "BUILD_VPS_STORAGE_RECOVERY_PLAN.py"
POLICY_PATH = ROOT / "config" / "vps_storage_retention_policy_v1.json"
GIB = 1024**3


def load_module():
    spec = importlib.util.spec_from_file_location("vps_storage_recovery_plan", MODULE_PATH)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def full_root_snapshot() -> dict:
    capacity = 30 * GIB
    return {
        "schema": "luma.vps_storage_snapshot.v1",
        "observed_at_utc": "2026-07-25T22:00:00Z",
        "scope": {
            "source_kind": "local_json_snapshot",
            "observation_only": True,
            "host_alias": "primary_vps",
        },
        "filesystems": [
            {
                "mount": "/",
                "filesystem_type": "xfs",
                "capacity_bytes": capacity,
                "used_bytes": capacity - 20480,
                "available_bytes": 20480,
                "used_percent": 100.0,
            },
            {
                "mount": "/var/oled",
                "filesystem_type": "xfs",
                "capacity_bytes": 15 * GIB,
                "used_bytes": 2 * GIB,
                "available_bytes": 13 * GIB,
                "used_percent": 13.333,
            },
        ],
        "mounts": [
            {
                "mount": "/",
                "device_alias": "root_logical_volume",
                "volume_role": "system_and_application",
                "separate_volume": False,
            },
            {
                "mount": "/var/oled",
                "device_alias": "oled_volume",
                "volume_role": "separate_data",
                "separate_volume": True,
            },
        ],
        "directory_usage": [
            {
                "path_alias": "government_snapshot_batches",
                "mount": "/",
                "bytes": 15 * GIB,
                "content_class": "snapshots",
            },
            {
                "path_alias": "service_outputs",
                "mount": "/",
                "bytes": 4 * GIB,
                "content_class": "outputs",
            },
            {
                "path_alias": "application_runtime",
                "mount": "/",
                "bytes": 3 * GIB,
                "content_class": "runtime",
            },
        ],
        "service_health": [
            {
                "service_alias": "edge_proxy",
                "status": "active",
                "health": "healthy",
                "depends_on_mounts": ["/"],
            },
            {
                "service_alias": "application_gateway",
                "status": "restart_loop",
                "health": "unhealthy",
                "depends_on_mounts": ["/"],
            },
        ],
        "backup_state": {
            "verified": False,
            "authority_confirmed": False,
            "evidence_refs": [],
            "covers_path_aliases": [],
        },
        "retention_state": {
            "policy_present": False,
            "authority_confirmed": False,
            "policy_ref": None,
        },
        "hosting_state": {
            "static_surface_present": True,
            "dynamic_service_present": True,
            "shared_root_volume": True,
        },
    }


def authority_complete_snapshot() -> dict:
    snapshot = full_root_snapshot()
    snapshot["backup_state"] = {
        "verified": True,
        "authority_confirmed": True,
        "evidence_refs": ["backup-verification-receipt-001"],
        "covers_path_aliases": [
            "government_snapshot_batches",
            "service_outputs",
            "application_runtime",
        ],
    }
    snapshot["retention_state"] = {
        "policy_present": True,
        "authority_confirmed": True,
        "policy_ref": "retention-policy-review-001",
    }
    return snapshot


def recommendation_ids(plan: dict) -> list[str]:
    return [row["id"] for row in plan["recommendations"]]


def assert_valid_self_hash(module, plan: dict) -> None:
    declared = plan["plan_sha256"]
    unsigned = dict(plan)
    unsigned.pop("plan_sha256")
    assert declared == module.sha256_json(unsigned)
    assert module.verify_plan_hash(plan) is True


def test_full_root_fails_closed_and_ranks_safe_recovery_reviews():
    module = load_module()
    plan = module.build_plan(full_root_snapshot())

    assert plan["decision"] == "BLOCKED_BACKUP_OR_RETENTION_AUTHORITY"
    assert plan["validation_issues"] == []
    gap_codes = {row["code"] for row in plan["authority_gaps"]}
    assert {
        "backup_not_verified",
        "backup_authority_missing",
        "backup_evidence_missing",
        "backup_coverage_incomplete",
        "retention_policy_missing",
        "retention_authority_missing",
        "retention_policy_evidence_missing",
    }.issubset(gap_codes)

    pressure = plan["observed_facts"]["derived_observations"]["filesystem_pressure"]
    root = next(row for row in pressure if row["mount"] == "/")
    assert root["used_percent"] == 100.0
    assert root["classification"] == "critical"

    candidates = plan["observed_facts"]["derived_observations"]["archive_review_candidates"]
    assert candidates[0]["path_alias"] == "government_snapshot_batches"
    assert candidates[0]["bytes"] == 15 * GIB
    assert candidates[0]["classification"] == "review_candidate_only"

    ids = recommendation_ids(plan)
    assert ids[:3] == [
        "verify_backup_evidence_and_coverage",
        "review_retention_policy_and_authority",
        "review_largest_archive_candidates",
    ]
    assert "evaluate_separate_mutable_data_volume" in ids
    assert "satisfy_service_restart_prerequisites" in ids
    assert "evaluate_static_dynamic_hosting_split" in ids
    assert all(row["execution_authorized"] is False for row in plan["recommendations"])
    assert all(row["authorization_inferred"] is False for row in plan["recommendations"])
    estimate = plan["observed_facts"]["derived_observations"]["reclaim_estimate"]
    assert estimate["confirmed_reclaimable_bytes"] == 0
    assert estimate["potential_reclaimable_upper_bound_bytes"] == 19 * GIB
    assert estimate["candidate_observed_bytes_are_not_safe_delete_bytes"] is True
    assert all(row["safe_to_delete"] is False for row in estimate["candidates"])
    assert all(row["safe_to_archive"] is False for row in estimate["candidates"])
    assert {
        lane: row["status"]
        for lane, row in plan["decision_lanes"].items()
    } == {
        "archive": "BLOCKED_PREREQUISITES_INCOMPLETE",
        "delete": "BLOCKED_NO_DELETE_AUTHORITY",
        "resize": "BLOCKED_PREREQUISITES_INCOMPLETE",
        "redeploy": "BLOCKED_PREREQUISITES_INCOMPLETE",
    }
    assert_valid_self_hash(module, plan)


def test_complete_authority_is_still_review_only_with_humanunlock_locked():
    module = load_module()
    plan = module.build_plan(authority_complete_snapshot())

    assert plan["decision"] == "HUMAN_REVIEW_READY_READ_ONLY"
    assert plan["validation_issues"] == []
    assert plan["authority_gaps"] == []
    assert plan["safety"] == {
        "network_access_performed": False,
        "filesystem_mutation_performed": False,
        "service_mutation_performed": False,
        "external_action_performed": False,
        "execution_authorized": False,
        "destructive_shell_commands_emitted": False,
    }

    actions = {row["action"]: row for row in plan["human_unlock"]["actions"]}
    assert {
        "deletion",
        "archive_or_move",
        "service_restart",
        "dns_change",
        "storage_purchase",
        "storage_resize",
        "deploy",
        "credential_action",
    } == set(actions)
    assert plan["human_unlock"]["planner_can_grant_human_unlock"] is False
    assert all(row["required"] is True for row in actions.values())
    assert all(row["authorized"] is False for row in actions.values())
    assert plan["decision_lanes"]["archive"]["status"] == (
        "HUMAN_REVIEW_ELIGIBLE_NO_EXECUTION_AUTHORITY"
    )
    assert plan["decision_lanes"]["resize"]["status"] == (
        "HUMAN_REVIEW_ELIGIBLE_NO_EXECUTION_AUTHORITY"
    )
    assert plan["decision_lanes"]["redeploy"]["status"] == (
        "HUMAN_REVIEW_ELIGIBLE_NO_EXECUTION_AUTHORITY"
    )
    assert plan["decision_lanes"]["delete"]["status"] == "BLOCKED_NO_DELETE_AUTHORITY"
    assert all(
        row["human_unlock_required"] is True
        and row["human_unlock_present"] is False
        and row["execution_authorized"] is False
        for row in plan["decision_lanes"].values()
    )
    assert_valid_self_hash(module, plan)


def test_missing_snapshot_fields_fail_closed_before_recovery_decisions():
    module = load_module()
    snapshot = full_root_snapshot()
    del snapshot["service_health"]
    del snapshot["backup_state"]

    plan = module.build_plan(snapshot)

    assert plan["decision"] == "BLOCKED_SNAPSHOT_INCOMPLETE"
    fields = {row["field"] for row in plan["validation_issues"]}
    assert "$.service_health" in fields
    assert "$.backup_state" in fields
    assert recommendation_ids(plan)[0] == "complete_local_snapshot"
    assert plan["safety"]["execution_authorized"] is False


def test_sensitive_input_is_rejected_without_echoing_the_value():
    module = load_module()
    snapshot = full_root_snapshot()
    snapshot["api_token"] = "must-not-appear-in-plan"

    plan = module.build_plan(snapshot)
    serialized = json.dumps(plan, sort_keys=True)

    assert plan["decision"] == "BLOCKED_SNAPSHOT_INCOMPLETE"
    assert plan["observed_facts"]["accepted"] is False
    assert "sensitive_input_rejected" in {
        row["code"] for row in plan["validation_issues"]
    }
    assert "must-not-appear-in-plan" not in serialized
    assert_valid_self_hash(module, plan)


def test_private_evidence_references_are_hashed_not_echoed():
    module = load_module()
    snapshot = authority_complete_snapshot()
    snapshot["backup_state"]["evidence_refs"] = [
        "private-person@example.invalid",
        "local-private-receipt-123",
    ]
    snapshot["retention_state"]["policy_ref"] = "private-retention-record-456"

    plan = module.build_plan(snapshot)
    serialized = json.dumps(plan, sort_keys=True)

    assert "private-person@example.invalid" not in serialized
    assert "local-private-receipt-123" not in serialized
    assert "private-retention-record-456" not in serialized
    summary = plan["observed_facts"]["backup_state"]["evidence_references"]
    assert summary["count"] == 2
    assert len(summary["reference_sha256"]) == 2
    assert all(len(value) == 64 for value in summary["reference_sha256"])
    assert_valid_self_hash(module, plan)


def test_private_mount_like_value_is_rejected_without_echo():
    module = load_module()
    snapshot = full_root_snapshot()
    private_mount = "/home/private_person"
    snapshot["filesystems"][0]["mount"] = private_mount
    snapshot["mounts"][0]["mount"] = private_mount
    snapshot["directory_usage"][0]["mount"] = private_mount
    snapshot["service_health"][0]["depends_on_mounts"] = [private_mount]

    plan = module.build_plan(snapshot)
    serialized = json.dumps(plan, sort_keys=True)

    assert plan["decision"] == "BLOCKED_SNAPSHOT_INCOMPLETE"
    assert "invalid_mount" in {row["code"] for row in plan["validation_issues"]}
    assert plan["observed_facts"]["accepted"] is False
    assert private_mount not in serialized
    assert_valid_self_hash(module, plan)


def test_policy_is_self_hashed_and_all_pinned_local_sources_verify():
    module = load_module()
    policy = json.loads(POLICY_PATH.read_text(encoding="utf-8"))

    issues, summary, candidates = module.validate_policy(policy, ROOT)

    assert issues == []
    assert summary["accepted"] is True
    assert summary["policy_payload_sha256"] == summary["computed_policy_payload_sha256"]
    assert summary["candidate_count"] == 7
    assert set(candidates) == {
        "application_runtime",
        "archive_outputs",
        "execution_outputs",
        "government_snapshot_batches",
        "paper_ticker_ledger",
        "service_outputs",
        "system_logs",
    }
    assert all(
        row["status"] == "VERIFIED_LOCAL_FILE"
        and row["expected_sha256"] == row["observed_sha256"]
        for row in summary["evidence_sources"]
    )


def test_policy_tampering_fails_closed_even_without_source_file_verification():
    module = load_module()
    policy = json.loads(POLICY_PATH.read_text(encoding="utf-8"))
    policy["scope"]["external_actions_authorized"] = True

    issues, summary, _ = module.validate_policy(
        policy,
        ROOT,
        verify_evidence_files=False,
    )

    codes = {row["code"] for row in issues}
    assert "policy_external_action_authorized" in codes
    assert "policy_self_hash_mismatch" in codes
    assert summary["accepted"] is False

    plan = module.build_plan(
        full_root_snapshot(),
        policy,
        repo_root=ROOT,
        verify_evidence_files=False,
    )
    assert plan["decision"] == "BLOCKED_POLICY_OR_EVIDENCE_DRIFT"
    assert all(
        row["execution_authorized"] is False
        for row in plan["decision_lanes"].values()
    )
    assert_valid_self_hash(module, plan)


def test_plan_never_contains_destructive_command_payloads():
    module = load_module()
    serialized = json.dumps(module.build_plan(full_root_snapshot())).lower()
    prohibited_fragments = (
        "rm -rf",
        "remove-item",
        "del /",
        "mkfs",
        "lvextend",
        "resize2fs",
        "docker system prune",
        "systemctl restart",
        "shutdown -",
        "reboot",
    )
    assert not any(fragment in serialized for fragment in prohibited_fragments)


def test_planner_source_has_no_network_or_mutation_apis():
    source = MODULE_PATH.read_text(encoding="utf-8")
    tree = ast.parse(source)
    imported_roots: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported_roots.update(alias.name.split(".", 1)[0] for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imported_roots.add(node.module.split(".", 1)[0])

    assert imported_roots.isdisjoint(
        {"ftplib", "http", "requests", "shutil", "socket", "subprocess", "urllib"}
    )
    mutation_methods = {
        "chmod",
        "hardlink_to",
        "mkdir",
        "rename",
        "rmdir",
        "symlink_to",
        "touch",
        "unlink",
        "write_bytes",
        "write_text",
    }
    called_attributes = {
        node.func.attr
        for node in ast.walk(tree)
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute)
    }
    called_names = {
        node.func.id
        for node in ast.walk(tree)
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name)
    }
    assert called_attributes.isdisjoint(mutation_methods)
    assert "open" not in called_names


def test_cli_reads_snapshot_and_only_emits_stdout(tmp_path: Path):
    snapshot_path = tmp_path / "snapshot.json"
    snapshot_bytes = json.dumps(authority_complete_snapshot(), sort_keys=True).encode("utf-8")
    snapshot_path.write_bytes(snapshot_bytes)
    before_hash = hashlib.sha256(snapshot_path.read_bytes()).hexdigest()
    before_mtime = snapshot_path.stat().st_mtime_ns
    before_entries = sorted(path.name for path in tmp_path.iterdir())

    result = subprocess.run(
        [sys.executable, str(MODULE_PATH), "--snapshot", str(snapshot_path)],
        cwd=tmp_path,
        check=False,
        capture_output=True,
        text=True,
        timeout=20,
    )

    assert result.returncode == 0
    plan = json.loads(result.stdout)
    assert plan["decision"] == "HUMAN_REVIEW_READY_READ_ONLY"
    assert_valid_self_hash(load_module(), plan)
    assert result.stderr == ""
    assert hashlib.sha256(snapshot_path.read_bytes()).hexdigest() == before_hash
    assert snapshot_path.stat().st_mtime_ns == before_mtime
    assert sorted(path.name for path in tmp_path.iterdir()) == before_entries


def test_cli_returns_blocked_plan_for_missing_authority(tmp_path: Path):
    snapshot_path = tmp_path / "snapshot.json"
    snapshot_path.write_text(json.dumps(full_root_snapshot()), encoding="utf-8")

    result = subprocess.run(
        [sys.executable, str(MODULE_PATH), "--snapshot", str(snapshot_path)],
        cwd=tmp_path,
        check=False,
        capture_output=True,
        text=True,
        timeout=20,
    )

    assert result.returncode == 2
    plan = json.loads(result.stdout)
    assert plan["decision"] == "BLOCKED_BACKUP_OR_RETENTION_AUTHORITY"
    assert plan["safety"]["filesystem_mutation_performed"] is False
    assert_valid_self_hash(load_module(), plan)


def test_cli_without_snapshot_emits_blocked_inventory_only_plan(tmp_path: Path):
    before_entries = sorted(path.name for path in tmp_path.iterdir())

    result = subprocess.run(
        [sys.executable, str(MODULE_PATH)],
        cwd=tmp_path,
        check=False,
        capture_output=True,
        text=True,
        timeout=20,
    )

    assert result.returncode == 2
    assert result.stderr == ""
    plan = json.loads(result.stdout)
    assert plan["decision"] == "BLOCKED_CURRENT_SNAPSHOT_MISSING"
    assert plan["policy"]["accepted"] is True
    facts = plan["observed_facts"]
    assert facts["source"] == "source_pinned_policy_inventory_only"
    assert facts["current_vps_state_claimed"] is False
    inventory = facts["derived_observations"]["known_candidate_inventory"]
    assert len(inventory) == 7
    assert all(row["current_observed_bytes"] is None for row in inventory)
    estimate = facts["derived_observations"]["reclaim_estimate"]
    assert estimate["confirmed_reclaimable_bytes"] == 0
    assert estimate["potential_reclaimable_upper_bound_bytes"] is None
    assert estimate["status"] == "BLOCKED_CURRENT_SIZE_EVIDENCE_MISSING"
    assert sorted(path.name for path in tmp_path.iterdir()) == before_entries
    assert_valid_self_hash(load_module(), plan)
