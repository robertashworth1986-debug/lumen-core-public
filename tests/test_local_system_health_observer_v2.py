from __future__ import annotations

import hashlib
import importlib.util
import json
import os
import subprocess
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = ROOT / "code" / "ops" / "COLLECT_LOCAL_SYSTEM_HEALTH_V2.py"
PROTOCOL_PATH = ROOT / "config" / "local_system_health_observer_protocol_v2.json"
TASK_SCRIPT_PATH = ROOT / "code" / "ops" / "STAGE_LOCAL_SYSTEM_HEALTH_V2_TASK.ps1"


def load_module():
    spec = importlib.util.spec_from_file_location("local_health_v2", MODULE_PATH)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def protocol_payload():
    return json.loads(PROTOCOL_PATH.read_text(encoding="utf-8"))


def fake_snapshot(protocol, state_dir, previous, observed_at):
    del protocol, state_dir, previous
    return {
        "schema": "luma.local_system_health_snapshot.v2",
        "observed_at_utc": observed_at.astimezone(timezone.utc).isoformat().replace("+00:00", "Z"),
        "scope": {
            "host_identity_included": False,
            "user_identity_included": False,
            "absolute_paths_included": False,
            "collector_outputs_excluded": True,
            "collector_process_excluded_where_measurable": True,
            "observation_only": True,
        },
        "cpu": {"available": True, "busy_percent_excluding_collector": 12.5},
        "memory": {"available": True, "used_physical_bytes_excluding_collector": 10},
        "disk": {"available": True, "volumes": [{"volume_alias": "system_volume"}]},
        "battery": {"available": True, "battery_present": True, "charge_percent": 75},
        "windows_update_service": {
            "available": True,
            "service_alias": "windows_update_service",
            "status": "stopped",
            "start_mode": "manual",
        },
        "docker": {
            "status": "backoff",
            "cli_available": True,
            "daemon_reachable": False,
            "next_probe_utc": None,
            "configured_containers": [],
        },
    }


def test_protocol_is_frozen_observation_only_and_preserves_v1_failures():
    payload = protocol_payload()
    assert payload["schema"] == "luma.local_system_health_observer_protocol.v2"
    assert payload["mode"] == "observation_only"
    assert payload["cadence"] == {
        "interval_minutes": 5,
        "single_run_timeout_minutes": 4,
        "docker_unavailable_backoff_minutes": 60,
    }
    assert payload["observations"]["cpu"]["sample_seconds"] == 1.0
    assert payload["observations"]["uptime"]["enabled"] is True
    assert payload["readiness"]["horizons_observed_v2_dates"] == [30, 90, 180]
    assert payload["readiness"]["legacy_dates_credited"] == 0
    assert all(value is False for value in payload["mutation_policy"].values())
    legacy = payload["legacy_v1_genesis_reference"]
    assert legacy["boundary"] == "reference_only_do_not_repair_or_rewrite_v1"
    assert legacy["repair_attempted"] is False
    assert legacy["declared_chain_break_count"] == 288
    assert legacy["declared_fork_count"] == 6
    artifacts = {row["alias"]: row for row in legacy["artifacts"]}
    assert artifacts["legacy_audit_chain"]["record_count"] == 4765
    assert artifacts["legacy_audit_chain"]["sha256"] == (
        "a861401d81ee8ca7549218b118e7744a31c3a6d639273cbcd78ae6b49e79b77a"
    )
    assert artifacts["legacy_frozen_deltas"]["record_count"] == 4787
    assert artifacts["legacy_frozen_deltas"]["sha256"] == (
        "4a983311f380e3aacee69a46ba41440d62b7379a405166468d2043862dca3bb7"
    )


def test_public_protocol_has_no_private_paths_users_or_credentials():
    text = PROTOCOL_PATH.read_text(encoding="utf-8")
    lowered = text.lower()
    assert "c:\\" not in lowered
    assert "c:/" not in lowered
    assert "novac" not in lowered
    assert "credential_value" not in lowered
    assert all("path" not in row for row in protocol_payload()["legacy_v1_genesis_reference"]["artifacts"])


def test_collector_source_contains_no_remediation_commands():
    lowered = MODULE_PATH.read_text(encoding="utf-8").lower()
    assert "start-service" not in lowered
    assert "restart-service" not in lowered
    assert '[executable, "start"' not in lowered
    assert '[executable, "restart"' not in lowered
    assert "install-windowsupdate" not in lowered


class Result:
    def __init__(self, returncode=0, stdout="", stderr=""):
        self.returncode = returncode
        self.stdout = stdout
        self.stderr = stderr


def test_docker_unavailable_uses_one_daemon_query_then_hourly_backoff():
    module = load_module()
    protocol = module.load_protocol(PROTOCOL_PATH)
    calls = []

    def runner(command, *, timeout):
        calls.append((command, timeout))
        return Result(returncode=1)

    now = datetime(2026, 7, 14, 12, tzinfo=timezone.utc)
    observed = module.observe_docker(
        protocol,
        None,
        now,
        which=lambda name: "docker.exe",
        runner=runner,
    )
    assert len(calls) == 1
    assert calls[0][0][1:] == ["version", "--format", "{{.Server.Version}}"]
    assert observed["next_probe_utc"] == "2026-07-14T13:00:00Z"

    calls.clear()
    skipped = module.observe_docker(
        protocol,
        observed,
        now + timedelta(minutes=5),
        which=lambda name: "docker.exe",
        runner=runner,
    )
    assert calls == []
    assert skipped["status"] == "backoff"
    assert skipped["next_probe_utc"] == "2026-07-14T13:00:00Z"


def test_docker_available_uses_one_daemon_and_one_ps_a_and_redacts_other_names():
    module = load_module()
    protocol = module.load_protocol(PROTOCOL_PATH)
    calls = []
    inventory = "\n".join(
        [
            json.dumps({"Names": "grafana", "State": "running", "Image": "private/image"}),
            json.dumps({"Names": "private-customer-container", "State": "running"}),
            json.dumps({"Names": "prometheus", "State": "exited"}),
        ]
    )

    def runner(command, *, timeout):
        calls.append((command, timeout))
        if command[1] == "version":
            return Result(stdout="27.0")
        return Result(stdout=inventory)

    observed = module.observe_docker(
        protocol,
        None,
        datetime(2026, 7, 14, 12, tzinfo=timezone.utc),
        which=lambda name: "docker.exe",
        runner=runner,
    )
    assert [call[0][1] for call in calls] == ["version", "ps"]
    assert calls[1][0][1:] == ["ps", "-a", "--format", "{{json .}}"]
    encoded = json.dumps(observed)
    assert "private-customer-container" not in encoded
    assert "private/image" not in encoded
    assert observed["configured_containers"] == [
        {"name": "grafana", "state": "running"},
        {"name": "prometheus", "state": "exited"},
    ]


def test_genesis_chain_is_append_fsync_hash_linked_and_atomic_latest(tmp_path):
    module = load_module()
    first_time = datetime(2026, 7, 14, 12, tzinfo=timezone.utc)
    first = module.run_once(
        PROTOCOL_PATH,
        tmp_path,
        now=first_time,
        snapshot_factory=fake_snapshot,
    )
    second = module.run_once(
        PROTOCOL_PATH,
        tmp_path,
        now=first_time + timedelta(days=1),
        snapshot_factory=fake_snapshot,
    )
    assert first["record_type"] == "v2_genesis_observation"
    assert first["sequence"] == 1
    assert first["prior_event_hash"] == "0" * 64
    assert first["legacy_v1_genesis_reference"]["declared_chain_break_count"] == 288
    assert first["legacy_v1_genesis_reference"]["declared_fork_count"] == 6
    assert second["record_type"] == "v2_observation"
    assert second["sequence"] == 2
    assert second["prior_event_hash"] == first["event_hash"]
    assert "legacy_v1_genesis_reference" not in second
    assert second["readiness"]["distinct_v2_observed_date_count"] == 2
    assert second["readiness"]["legacy_dates_credited"] == 0
    assert all(not gate["ready"] for gate in second["readiness"]["gates"].values())

    latest = json.loads((tmp_path / "health_observer_v2_latest.json").read_text(encoding="utf-8"))
    assert latest["event"] == second
    assert not list(tmp_path.glob("*.tmp"))
    verification = module.verify_chain(PROTOCOL_PATH, tmp_path)
    assert verification["status"] == "verified"
    assert verification["row_count"] == 2
    assert verification["tail_event_hash"] == second["event_hash"]


def test_chain_verification_detects_snapshot_tampering(tmp_path):
    module = load_module()
    module.run_once(
        PROTOCOL_PATH,
        tmp_path,
        now=datetime(2026, 7, 14, 12, tzinfo=timezone.utc),
        snapshot_factory=fake_snapshot,
    )
    segment = next(tmp_path.glob("health_observer_v2_*.jsonl"))
    event = json.loads(segment.read_text(encoding="utf-8"))
    event["snapshot"]["cpu"]["busy_percent_excluding_collector"] = 99
    segment.write_text(json.dumps(event, sort_keys=True, separators=(",", ":")) + "\n", encoding="utf-8")
    with pytest.raises(ValueError, match="snapshot content hash mismatch"):
        module.verify_chain(PROTOCOL_PATH, tmp_path)

    with pytest.raises(ValueError, match="previous snapshot content hash mismatch"):
        module.run_once(
            PROTOCOL_PATH,
            tmp_path,
            now=datetime(2026, 7, 14, 12, 5, tzinfo=timezone.utc),
            snapshot_factory=fake_snapshot,
        )


def test_existing_chain_rejects_frozen_protocol_drift(tmp_path):
    module = load_module()
    observed_at = datetime(2026, 7, 14, 12, tzinfo=timezone.utc)
    module.run_once(
        PROTOCOL_PATH,
        tmp_path,
        now=observed_at,
        snapshot_factory=fake_snapshot,
    )
    changed_protocol = tmp_path / "changed_protocol.json"
    payload = protocol_payload()
    payload["cadence"]["interval_minutes"] = 6
    changed_protocol.write_text(json.dumps(payload), encoding="utf-8")
    with pytest.raises(ValueError, match="frozen protocol hash changed"):
        module.run_once(
            changed_protocol,
            tmp_path,
            now=observed_at + timedelta(minutes=5),
            snapshot_factory=fake_snapshot,
        )


def test_readiness_counts_observed_v2_dates_not_elapsed_or_legacy_days():
    module = load_module()
    previous = {
        "readiness": {
            "first_v2_observed_date_utc": "2026-07-14",
            "last_v2_observed_date_utc": "2026-07-14",
            "distinct_v2_observed_date_count": 29,
        }
    }
    same_day = module.compute_readiness(
        previous,
        datetime(2026, 7, 14, 23, tzinfo=timezone.utc),
        [30, 90, 180],
    )
    assert same_day["distinct_v2_observed_date_count"] == 29
    assert same_day["gates"]["30"]["ready"] is False
    next_observed_date = module.compute_readiness(
        previous,
        datetime(2026, 12, 1, tzinfo=timezone.utc),
        [30, 90, 180],
    )
    assert next_observed_date["distinct_v2_observed_date_count"] == 30
    assert next_observed_date["gates"]["30"]["ready"] is True
    assert next_observed_date["gates"]["90"]["ready"] is False
    assert next_observed_date["legacy_dates_credited"] == 0


def test_single_writer_lock_rejects_a_second_writer(tmp_path):
    module = load_module()
    lock_path = tmp_path / ".lock"
    with module.SingleWriterLock(lock_path):
        with pytest.raises(module.LockUnavailable):
            with module.SingleWriterLock(lock_path):
                pass


def test_task_stager_is_dry_run_by_default_and_apply_is_dual_gated():
    source = TASK_SCRIPT_PATH.read_text(encoding="utf-8")
    lowered = source.lower()
    assert "[switch]$apply" in lowered
    assert "if (-not $apply)" in lowered
    assert "$env:luma_human_unlock_token" in lowered
    assert "-noninteractive" in lowered
    assert "-windowstyle hidden" in lowered
    assert "exit `$lastexitcode" in lowered
    assert "private_proof_vault" in lowered
    assert "new-scheduledtasksettingsset" in lowered
    assert "-hidden" in lowered
    assert "register-scheduledtask" in lowered
    assert "start-service" not in lowered
    assert "restart-service" not in lowered
    assert "docker start" not in lowered
    assert "docker restart" not in lowered
    assert "c:\\whitehole" not in lowered

    completed = subprocess.run(
        ["powershell.exe", "-NoLogo", "-NoProfile", "-NonInteractive", "-File", str(TASK_SCRIPT_PATH)],
        capture_output=True,
        text=True,
        check=False,
        timeout=15,
    )
    assert completed.returncode == 0, completed.stderr
    plan = json.loads(completed.stdout)
    assert plan["status"] == "dry_run"
    assert plan["mutation_performed"] is False
    assert plan["hidden"] is True
    assert plan["noninteractive"] is True

    environment = dict(os.environ)
    environment.pop("LUMA_HUMAN_UNLOCK_TOKEN", None)
    blocked = subprocess.run(
        [
            "powershell.exe",
            "-NoLogo",
            "-NoProfile",
            "-NonInteractive",
            "-File",
            str(TASK_SCRIPT_PATH),
            "-Apply",
        ],
        capture_output=True,
        text=True,
        check=False,
        timeout=15,
        env=environment,
    )
    assert blocked.returncode != 0
    assert "LUMA_HUMAN_UNLOCK_TOKEN" in blocked.stderr


def test_event_contains_exact_protocol_and_script_hashes(tmp_path):
    module = load_module()
    event = module.run_once(
        PROTOCOL_PATH,
        tmp_path,
        now=datetime(2026, 7, 14, 12, tzinfo=timezone.utc),
        snapshot_factory=fake_snapshot,
    )
    assert event["protocol_sha256"] == hashlib.sha256(PROTOCOL_PATH.read_bytes()).hexdigest()
    assert event["collector_script_sha256"] == hashlib.sha256(MODULE_PATH.read_bytes()).hexdigest()
    assert event["task_staging_script_sha256"] == hashlib.sha256(TASK_SCRIPT_PATH.read_bytes()).hexdigest()
    assert event["snapshot_content_sha256"] == module.sha256_bytes(
        module.canonical_bytes(event["snapshot"])
    )
