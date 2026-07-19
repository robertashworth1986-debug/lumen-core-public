from __future__ import annotations

import argparse
import copy
import hashlib
import importlib.util
import json
import math
import os
import zipfile
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = ROOT / "code" / "ops" / "BUILD_LOCAL_COMPUTE_WORK_PROVENANCE.py"
PROTOCOL_PATH = ROOT / "config" / "local_compute_work_provenance_protocol_v1.json"


def load_module():
    spec = importlib.util.spec_from_file_location("compute_work_provenance", MODULE_PATH)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def line(timestamp: str, row_type: str, payload: dict, *, padding: bool = False) -> str:
    rendered = json.dumps({"timestamp": timestamp, "type": row_type, "payload": payload})
    return f"  {rendered}  " if padding else rendered


def write_lines(path: Path, rows: list[str]) -> None:
    path.write_text("\n".join(rows) + "\n", encoding="utf-8")


def clean_assets() -> dict:
    return {
        "quant_lab": {
            "all_files_including_dependencies": {"file_count": 0},
            "files_excluding_dependencies_and_caches": {"file_count": 0},
        },
        "premium_mirror": {},
    }


def clean_compute() -> dict:
    return {"cpu": {}, "nvidia_gpus": [], "torch_runtime": {}, "cuda_smoke_test": {}}


def protocol_payload() -> dict:
    return json.loads(PROTOCOL_PATH.read_text(encoding="utf-8"))


def one_valid_completion(secret: str = "ignored") -> list[str]:
    return [
        line(
            "2026-01-01T00:00:00Z",
            "event_msg",
            {"type": "task_started", "turn_id": "turn-a", "started_at": -999999},
            padding=True,
        ),
        line(
            "2026-01-01T00:00:00Z",
            "turn_context",
            {"turn_id": "turn-a", "model": "gpt-5.5"},
            padding=True,
        ),
        line("2026-01-01T00:00:00Z", "response_item", {"content": secret}, padding=True),
        line(
            "2026-01-01T00:00:01Z",
            "event_msg",
            {
                "type": "task_complete",
                "turn_id": "turn-a",
                "completed_at": "2026-01-01T00:00:01Z",
                "duration_ms": 1000,
            },
            padding=True,
        ),
    ]


def test_whitespace_overlap_and_private_content_are_noninterfering(tmp_path: Path):
    module = load_module()
    first_root = tmp_path / "first"
    second_root = tmp_path / "second"
    first_root.mkdir()
    second_root.mkdir()
    for root, secret in ((first_root, "SHORT_SECRET"), (second_root, "A_MUCH_LONGER_PRIVATE_SECRET_VALUE")):
        write_lines(root / "a.jsonl", one_valid_completion(secret))
        write_lines(
            root / "b.jsonl",
            [
                line(
                    "2026-01-01T00:00:00.500Z",
                    "event_msg",
                    {"type": "task_started", "turn_id": "turn-b", "started_at": 1},
                    padding=True,
                ),
                line(
                    "2026-01-01T00:00:00.500Z",
                    "turn_context",
                    {"turn_id": "turn-b", "model": "gpt-5.6-sol"},
                    padding=True,
                ),
                line(
                    "2026-01-01T00:00:02Z",
                    "event_msg",
                    {
                        "type": "task_complete",
                        "turn_id": "turn-b",
                        "completed_at": "2026-01-01T00:00:02Z",
                        "duration_ms": 1500,
                    },
                    padding=True,
                ),
            ],
        )

    first = module.scan_sessions(first_root, max_workers=2)
    second = module.scan_sessions(second_root, max_workers=2)

    assert first == second
    assert first["quality"] == "VALID"
    assert first["completed_task_count"] == 2
    assert first["additive_task_elapsed_seconds"] == 2.5
    assert first["calendar_union_elapsed_seconds"] == 2.0
    assert first["calendar_union_elapsed_microseconds"] <= first["additive_task_elapsed_microseconds"]
    assert first["per_model"]["gpt-5.5"]["completed_task_count"] == 1
    assert first["per_model"]["gpt-5.6-sol"]["completed_task_count"] == 1
    serialized = json.dumps(first).lower()
    assert "secret" not in serialized
    assert "sha256" not in serialized
    assert "source_files" not in serialized
    assert str(first_root).lower() not in serialized


def test_model_attribution_is_event_correct_and_ambiguity_safe(tmp_path: Path):
    module = load_module()
    sessions = tmp_path / "sessions"
    sessions.mkdir()
    rows = [
        line("2026-01-01T00:00:00Z", "turn_context", {"turn_id": "exact", "model": "model-a"}),
        line(
            "2026-01-01T00:00:01Z",
            "event_msg",
            {"type": "task_complete", "turn_id": "exact", "duration_ms": 1000},
        ),
        line(
            "2026-01-01T00:00:02Z",
            "event_msg",
            {"type": "task_complete", "turn_id": "late", "duration_ms": 1000},
        ),
        line("2026-01-01T00:00:03Z", "turn_context", {"turn_id": "late", "model": "too-late"}),
        line("2026-01-01T00:00:03Z", "turn_context", {"turn_id": "amb", "model": "model-a"}),
        line("2026-01-01T00:00:03Z", "turn_context", {"turn_id": "amb", "model": "model-b"}),
        line(
            "2026-01-01T00:00:04Z",
            "event_msg",
            {"type": "task_complete", "turn_id": "amb", "duration_ms": 1000},
        ),
    ]
    write_lines(sessions / "events.jsonl", rows)

    work = module.scan_sessions(sessions, max_workers=1)

    assert work["per_model"]["model-a"]["completed_task_count"] == 1
    assert work["per_model"][module.UNATTRIBUTED_MODEL]["completed_task_count"] == 1
    assert work["per_model"][module.AMBIGUOUS_MODEL]["completed_task_count"] == 1
    assert "too-late" not in work["per_model"]
    assert work["late_model_context_count"] == 1
    assert work["ambiguous_model_completion_count"] == 1
    assert work["unattributed_model_completion_count"] == 1
    assert work["quality"] == "DEGRADED"


def test_duplicate_completions_pending_tasks_and_authoritative_intervals(tmp_path: Path):
    module = load_module()
    sessions = tmp_path / "sessions"
    sessions.mkdir()
    rows = [
        line(
            "2026-01-01T00:00:00Z",
            "event_msg",
            {"type": "task_started", "turn_id": "done", "started_at": "2001-01-01T00:00:00Z"},
        ),
        line(
            "2026-01-01T00:00:00Z",
            "event_msg",
            {"type": "task_started", "turn_id": "done", "started_at": "2099-01-01T00:00:00Z"},
        ),
        line("2026-01-01T00:00:00Z", "turn_context", {"turn_id": "done", "model": "model-a"}),
        line(
            "2026-01-01T00:00:01Z",
            "event_msg",
            {
                "type": "task_complete",
                "turn_id": "done",
                "completed_at": "2026-01-01T00:00:01Z",
                "duration_ms": 1000,
            },
        ),
        line(
            "2026-01-01T00:00:01Z",
            "event_msg",
            {
                "type": "task_complete",
                "turn_id": "done",
                "completed_at": "2026-01-01T00:00:01Z",
                "duration_ms": 1000,
            },
        ),
        line("2026-01-01T00:00:02Z", "event_msg", {"type": "task_started", "turn_id": "pending"}),
        line("2026-01-01T00:00:02Z", "event_msg", {"type": "task_started", "turn_id": "aborted"}),
        line("2026-01-01T00:00:03Z", "event_msg", {"type": "turn_aborted", "turn_id": "aborted"}),
        line("2026-01-01T00:00:03Z", "turn_context", {"turn_id": "conflict", "model": "model-b"}),
        line(
            "2026-01-01T00:00:04Z",
            "event_msg",
            {"type": "task_complete", "turn_id": "conflict", "duration_ms": 1000},
        ),
        line(
            "2026-01-01T00:00:04Z",
            "event_msg",
            {"type": "task_complete", "turn_id": "conflict", "duration_ms": 2000},
        ),
    ]
    write_lines(sessions / "events.jsonl", rows)

    work = module.scan_sessions(sessions, max_workers=1)

    assert work["completion_event_count"] == 4
    assert work["duplicate_completion_count"] == 2
    assert work["conflicting_duplicate_task_count"] == 1
    assert work["completed_task_count"] == 1
    assert work["pending_task_count"] == 1
    assert work["duplicate_task_start_count"] == 1
    assert work["task_aborted_count"] == 1
    assert work["additive_task_elapsed_microseconds"] == 1_000_000
    assert work["calendar_union_elapsed_microseconds"] == 1_000_000
    assert work["measurement_interval_start_utc"] == "2026-01-01T00:00:00.000000Z"


@pytest.mark.parametrize(
    "value",
    [True, -1, float("nan"), float("inf"), -float("inf"), 604_800_001, "1000", None],
)
def test_duration_validation_rejects_invalid_values(value):
    module = load_module()
    assert module.duration_ms_to_microseconds(value) is None


def test_duration_and_timestamp_rounding_are_explicit():
    module = load_module()
    assert module.duration_ms_to_microseconds(0.0005) == 1
    assert module.rounded_seconds(1500) == 0.002
    assert module.duration_label_microseconds(499_999) == "0d 00h 00m 00s"
    assert module.duration_label_microseconds(500_000) == "0d 00h 00m 01s"
    assert module.parse_utc_instant_microseconds("2026-01-01T00:00:00") is None
    assert module.parse_utc_instant_microseconds(True) is None
    assert module.parse_utc_instant_microseconds("2025-12-31T18:00:00-06:00") == module.parse_utc_instant_microseconds(
        "2026-01-01T00:00:00Z"
    )
    with pytest.raises(ValueError):
        module.strict_json_loads('{"duration_ms": NaN}')


def test_rejected_completion_values_degrade_without_inflating_totals(tmp_path: Path):
    module = load_module()
    sessions = tmp_path / "sessions"
    sessions.mkdir()
    rows = [
        line(
            "2026-01-01T00:00:01Z",
            "event_msg",
            {"type": "task_complete", "turn_id": "bool", "duration_ms": True},
        ),
        line(
            "2026-01-01T00:00:01Z",
            "event_msg",
            {"type": "task_complete", "turn_id": "negative", "duration_ms": -1},
        ),
        line(
            "2026-01-01T00:00:01Z",
            "event_msg",
            {"type": "task_complete", "turn_id": "huge", "duration_ms": 604_800_001},
        ),
        line(
            "2026-01-01T00:00:01Z",
            "event_msg",
            {
                "type": "task_complete",
                "turn_id": "naive-time",
                "completed_at": "2026-01-01T00:00:01",
                "duration_ms": 1,
            },
        ),
        line(
            "2026-01-01T00:00:01Z",
            "event_msg",
            {"type": "task_complete", "turn_id": "zero", "duration_ms": 0},
        ),
        '{"timestamp":"2026-01-01T00:00:01Z","type":"event_msg","payload":{"type":"task_complete","turn_id":"nan","duration_ms":NaN}}',
    ]
    write_lines(sessions / "events.jsonl", rows)

    work = module.scan_sessions(sessions, max_workers=1)

    assert work["quality"] == "DEGRADED"
    assert work["completion_event_count"] == 5
    assert work["rejected_completion_event_count"] == 4
    assert work["invalid_duration_count"] == 3
    assert work["invalid_completion_timestamp_count"] == 1
    assert work["parse_error_count"] == 1
    assert work["completed_task_count"] == 1
    assert work["additive_task_elapsed_microseconds"] == 0


def test_root_parse_read_and_mutation_quality_states(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    module = load_module()
    assert module.scan_sessions(tmp_path / "missing", 1)["quality"] == "INVALID"

    empty = tmp_path / "empty"
    empty.mkdir()
    assert module.scan_sessions(empty, 1)["quality"] == "VALID"

    malformed = tmp_path / "malformed"
    malformed.mkdir()
    write_lines(malformed / "events.jsonl", ["not-json", *one_valid_completion()])
    degraded = module.scan_sessions(malformed, 1)
    assert degraded["quality"] == "DEGRADED"
    assert degraded["parse_error_count"] == 1
    assert degraded["completed_task_count"] == 1

    unreadable = tmp_path / "unreadable"
    unreadable.mkdir()
    write_lines(unreadable / "events.jsonl", one_valid_completion())
    original_scan = module.scan_session_file

    def fail_read(path: Path, root: Path):
        raise PermissionError(path)

    monkeypatch.setattr(module, "scan_session_file", fail_read)
    failed = module.scan_sessions(unreadable, 1)
    assert failed["quality"] == "INVALID"
    assert failed["source_file_failure_reasons"] == [{"reason": "SOURCE_READ_ERROR", "count": 1}]

    monkeypatch.setattr(module, "scan_session_file", original_scan)
    monkeypatch.setattr(module, "_same_source_snapshot", lambda first, second: False)
    mutated = module.scan_sessions(unreadable, 1)
    assert mutated["quality"] == "INVALID"
    assert "SOURCE_MUTATED_DURING_SCAN" in mutated["quality_reasons"]


def test_symlink_sources_and_roots_are_never_scanned(tmp_path: Path):
    module = load_module()
    outside = tmp_path / "outside.jsonl"
    write_lines(outside, one_valid_completion("OUTSIDE_PRIVATE_VALUE"))
    sessions = tmp_path / "sessions"
    sessions.mkdir()
    write_lines(sessions / "inside.jsonl", one_valid_completion())
    linked_file = sessions / "linked.jsonl"
    linked_root = tmp_path / "linked-root"
    try:
        os.symlink(outside, linked_file)
        os.symlink(sessions, linked_root, target_is_directory=True)
    except OSError as exc:
        pytest.skip(f"symlink creation unavailable: {exc}")

    work = module.scan_sessions(sessions, 1)
    assert work["quality"] == "DEGRADED"
    assert work["completed_task_count"] == 1
    assert work["source_file_discovery_count"] == 2
    assert "SOURCE_SYMLINK_FILE_REJECTED" in work["quality_reasons"]
    assert "outside" not in json.dumps(work).lower()
    linked = module.scan_sessions(linked_root, 1)
    assert linked["quality"] == "INVALID"
    assert linked["quality_reasons"] == ["ROOT_IS_SYMLINK"]


def test_aggregation_and_receipt_build_do_not_mutate_inputs(tmp_path: Path):
    module = load_module()
    sessions = tmp_path / "sessions"
    sessions.mkdir()
    source = sessions / "events.jsonl"
    write_lines(source, one_valid_completion())
    scan = module.scan_session_file(source, sessions)
    scans = [scan]
    scans_before = copy.deepcopy(scans)

    work = module.aggregate_session_scans(scans)
    assert scans == scans_before

    protocol = protocol_payload()
    compute = clean_compute()
    assets = clean_assets()
    snapshots = copy.deepcopy((protocol, work, compute, assets))
    payload = module.build_payload(protocol, PROTOCOL_PATH, work, compute, assets, None)
    assert (protocol, work, compute, assets) == snapshots
    assert payload["status"] == "MEASURED_VALID"
    expected = dict(payload)
    receipt_sha = expected.pop("receipt_sha256")
    assert receipt_sha == module.stable_sha256(expected)


def test_protocol_schema_status_and_privacy_invariants(tmp_path: Path):
    module = load_module()
    protocol = protocol_payload()
    module.validate_protocol(protocol)
    assert protocol["status"] == "frozen"
    assert protocol["privacy"]["message_content_read_for_measurement"] is False
    assert protocol["privacy"]["input_file_content_hashes_written_to_receipt"] is False
    assert protocol["privacy"]["stable_source_aliases_written_to_receipt"] is False
    assert protocol["privacy"]["session_identity_mode"] == "none"
    assert protocol["work_measurement"]["rounding"] == module.ROUNDING_POLICY
    assert "half-open interval" in protocol["work_measurement"]["authoritative_interval"]

    invalid_protocol = copy.deepcopy(protocol)
    invalid_protocol["privacy"]["session_paths_written_to_receipt"] = True
    with pytest.raises(ValueError, match="privacy.session_paths"):
        module.validate_protocol(invalid_protocol)

    sessions = tmp_path / "sessions"
    sessions.mkdir()
    valid_work = module.scan_sessions(sessions, 1)
    bad_work = copy.deepcopy(valid_work)
    bad_work["calendar_union_elapsed_microseconds"] = 1
    bad_work["calendar_union_elapsed_seconds"] = 0.001
    with pytest.raises(ValueError, match="union exceeds additive"):
        module.build_payload(protocol, PROTOCOL_PATH, bad_work, clean_compute(), clean_assets(), None)

    malformed = tmp_path / "malformed"
    malformed.mkdir()
    write_lines(malformed / "events.jsonl", ["not-json"])
    degraded_work = module.scan_sessions(malformed, 1)
    degraded_payload = module.build_payload(
        protocol, PROTOCOL_PATH, degraded_work, clean_compute(), clean_assets(), None
    )
    assert degraded_payload["status"] == "MEASURED_DEGRADED"
    assert "VERIFIED" not in json.dumps(degraded_payload).upper()

    invalid_work = module.scan_sessions(tmp_path / "missing", 1)
    invalid_payload = module.build_payload(
        protocol, PROTOCOL_PATH, invalid_work, clean_compute(), clean_assets(), None
    )
    assert invalid_payload["status"] == "MEASUREMENT_INVALID"


def test_goal_snapshot_rejects_invalid_numeric_metadata():
    module = load_module()

    def args(seconds, tokens=1, created="2026-01-01T00:00:00Z"):
        return argparse.Namespace(
            active_goal_seconds=seconds,
            active_goal_tokens=tokens,
            active_goal_model="model-a",
            active_goal_created_utc=created,
        )

    with pytest.raises(ValueError):
        module.goal_snapshot(args(float("nan")))
    with pytest.raises(ValueError):
        module.goal_snapshot(args(-1))
    with pytest.raises(ValueError):
        module.goal_snapshot(args(1, tokens=True))
    with pytest.raises(ValueError):
        module.goal_snapshot(args(1, created="2026-01-01T00:00:00"))
    snapshot = module.goal_snapshot(args(0.0000015, tokens=0))
    assert snapshot["time_used_microseconds"] == 2


def test_archive_packets_are_atomic_and_collision_protected(tmp_path: Path):
    module = load_module()
    sessions = tmp_path / "sessions"
    sessions.mkdir()
    work = module.scan_sessions(sessions, 1)
    payload = module.build_payload(
        protocol_payload(), PROTOCOL_PATH, work, clean_compute(), clean_assets(), None
    )
    payload_before = copy.deepcopy(payload)
    output = tmp_path / "output"

    result = module.write_packet(payload, [output])

    assert payload == payload_before
    packet = output / result[0]["packet_name"]
    assert packet.is_file()
    original_packet = packet.read_bytes()
    with zipfile.ZipFile(packet) as archive:
        assert set(archive.namelist()) == {
            "local_compute_work_provenance.json",
            "local_compute_work_provenance.md",
            "manifest.json",
        }
        receipt_bytes = archive.read("local_compute_work_provenance.json")
        markdown_bytes = archive.read("local_compute_work_provenance.md")
        manifest = json.loads(archive.read("manifest.json"))
    assert manifest["schema"] == module.PACKET_MANIFEST_SCHEMA
    file_hashes = {row["name"]: row["sha256"] for row in manifest["files"]}
    assert file_hashes["local_compute_work_provenance.json"] == hashlib.sha256(receipt_bytes).hexdigest()
    assert file_hashes["local_compute_work_provenance.md"] == hashlib.sha256(markdown_bytes).hexdigest()
    pointer = json.loads((output / "local_compute_work_provenance_latest_packet.json").read_text())
    assert pointer["packet_name"] == packet.name

    with pytest.raises(FileExistsError):
        module.write_packet(payload, [output])
    assert packet.read_bytes() == original_packet
    assert not list(output.glob(".*.tmp"))


def test_protocol_contains_no_local_identity_or_count_inflation_claims():
    payload = protocol_payload()
    text = PROTOCOL_PATH.read_text(encoding="utf-8").lower()
    assert any("File, row, exposure" in row for row in payload["claim_boundaries"])
    assert "c:\\users" not in text
    assert "novac" not in text
    assert "verified" not in text or payload["source_validation"]["verified_status"] is False
