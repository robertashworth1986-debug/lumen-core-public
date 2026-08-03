from __future__ import annotations

import copy
import importlib.util
import json
import re
import sys
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "code" / "ops" / "BUILD_CODEX_AGENT_ORCHESTRATION_RECEIPT.py"


def load_module():
    spec = importlib.util.spec_from_file_location("codex_orchestration_receipt", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def write_jsonl(path: Path, rows: list[dict]) -> None:
    path.write_text(
        "".join(json.dumps(row, sort_keys=True) + "\n" for row in rows),
        encoding="utf-8",
    )


def turn_context(timestamp: str) -> dict:
    return {
        "timestamp": timestamp,
        "type": "turn_context",
        "payload": {"model": "gpt-5.6-sol", "effort": "ultra"},
    }


def tool_call(timestamp: str, call_id: str, source: str) -> dict:
    return {
        "timestamp": timestamp,
        "type": "response_item",
        "payload": {
            "type": "custom_tool_call",
            "name": "exec",
            "call_id": call_id,
            "input": source,
        },
    }


def tool_output(timestamp: str, call_id: str, value) -> dict:
    return {
        "timestamp": timestamp,
        "type": "response_item",
        "payload": {
            "type": "custom_tool_call_output",
            "call_id": call_id,
            "output": value,
        },
    }


def function_wait_call(timestamp: str, call_id: str, cell_id: str) -> dict:
    return {
        "timestamp": timestamp,
        "type": "response_item",
        "payload": {
            "type": "function_call",
            "name": "wait",
            "call_id": call_id,
            "arguments": json.dumps({"cell_id": cell_id}),
        },
    }


def function_wait_output(timestamp: str, call_id: str, value) -> dict:
    return {
        "timestamp": timestamp,
        "type": "response_item",
        "payload": {
            "type": "function_call_output",
            "call_id": call_id,
            "output": value,
        },
    }


def content_output(value: dict) -> str:
    return json.dumps(
        [
            {"type": "text", "text": "Script completed"},
            {"type": "text", "text": json.dumps(value, sort_keys=True)},
        ]
    )


def spawn_source(message: str) -> str:
    return (
        "const r = await tools.multi_agent_v1__spawn_agent("
        "{agent_type:\"worker\",fork_context:false,message:"
        + json.dumps(message)
        + "}); text(r);"
    )


def wait_source(agent_id: str) -> str:
    return (
        "const r = await tools.multi_agent_v1__wait_agent({targets:["
        + json.dumps(agent_id)
        + "]}); text(r);"
    )


def build_complete_rows(agent_id: str) -> list[dict]:
    return [
        turn_context("2026-07-19T01:00:00.000Z"),
        tool_call(
            "2026-07-19T01:00:01.000Z",
            "spawn-1",
            spawn_source(
                "OpenAI Build Week: build the Devpost completion kit for ProofLock Console."
            ),
        ),
        tool_output(
            "2026-07-19T01:00:02.000Z",
            "spawn-1",
            content_output({"agent_id": agent_id, "nickname": "redacted"}),
        ),
        tool_call(
            "2026-07-19T01:00:03.000Z",
            "wait-1",
            wait_source(agent_id),
        ),
        tool_output(
            "2026-07-19T01:00:04.000Z",
            "wait-1",
            content_output(
                {"status": {agent_id: {"completed": "private task result"}}, "timed_out": False}
            ),
        ),
    ]


def recompute_hashes(module, receipt: dict) -> None:
    receipt["normalized_facts_sha256"] = module.stable_hash(receipt["facts"])
    unhashed = dict(receipt)
    unhashed.pop("receipt_sha256", None)
    receipt["receipt_sha256"] = module.stable_hash(unhashed)


def test_receipt_is_deterministic_and_counts_direct_terminal_evidence(tmp_path: Path):
    module = load_module()
    source = tmp_path / "session.jsonl"
    write_jsonl(source, build_complete_rows("11111111-1111-4111-8111-111111111111"))

    first = module.build_receipt(source, observed_utc="2026-07-19T01:01:00Z")
    second = module.build_receipt(source, observed_utc="2026-07-19T01:01:00Z")

    assert first == second
    orchestration = first["facts"]["orchestration"]
    assert orchestration["spawn_attempt_count"] == 1
    assert orchestration["total_spawn_events"] == 1
    assert orchestration["role_category_counts"] == {"devpost_submission_readiness": 1}
    assert orchestration["terminal_status_counts"] == {"completed": 1}
    assert orchestration["spawn_events_without_terminal_status"] == 0
    assert first["facts"]["model_provenance"]["records"] == [
        {
            "model": "gpt-5.6-sol",
            "effort": "ultra",
            "spawn_event_count": 1,
            "directly_recorded": True,
            "scope": "coordinator_turn_context_nearest_preceding_spawn_call",
        }
    ]
    assert module.verify_receipt(first) == (True, [])


def test_async_exec_spawn_is_linked_without_exposing_cell_or_agent_ids(tmp_path: Path):
    module = load_module()
    source = tmp_path / "async-session.jsonl"
    agent_id = "22222222-2222-4222-8222-222222222222"
    rows = [
        turn_context("2026-07-19T02:00:00.000Z"),
        tool_call(
            "2026-07-19T02:00:01.000Z",
            "spawn-async",
            spawn_source(
                "OpenAI Build Week portal progress receipt for ProofLock Console on Devpost."
            ),
        ),
        tool_output(
            "2026-07-19T02:00:02.000Z",
            "spawn-async",
            "Script running with cell ID private-cell-123",
        ),
        function_wait_call(
            "2026-07-19T02:00:03.000Z", "outer-wait", "private-cell-123"
        ),
        function_wait_output(
            "2026-07-19T02:00:04.000Z",
            "outer-wait",
            content_output({"agent_id": agent_id, "nickname": "private"}),
        ),
    ]
    write_jsonl(source, rows)

    receipt = module.build_receipt(source, observed_utc="2026-07-19T02:01:00Z")
    serialized = json.dumps(receipt, sort_keys=True)

    assert receipt["facts"]["orchestration"]["total_spawn_events"] == 1
    assert receipt["facts"]["orchestration"]["role_category_counts"] == {
        "portal_progress_receipt": 1
    }
    assert receipt["facts"]["orchestration"]["spawn_events_without_terminal_status"] == 1
    assert agent_id not in serialized
    assert "private-cell-123" not in serialized


def test_privacy_bait_in_task_and_output_never_reaches_receipt(tmp_path: Path):
    module = load_module()
    source = tmp_path / "private-session.jsonl"
    agent_id = "33333333-3333-4333-8333-333333333333"
    private_bait = (
        "OpenAI Build Week Devpost audit for ProofLock Console. "
        "Do not publish person@example.com, sk-privateABC123, "
        "https://private.example.test/item/secret-id, or C:\\Users\\Private\\secret.txt."
    )
    rows = [
        turn_context("2026-07-19T03:00:00.000Z"),
        tool_call("2026-07-19T03:00:01.000Z", "spawn-private", spawn_source(private_bait)),
        tool_output(
            "2026-07-19T03:00:02.000Z",
            "spawn-private",
            content_output(
                {
                    "agent_id": agent_id,
                    "nickname": "person@example.com",
                    "private_result": private_bait,
                }
            ),
        ),
    ]
    write_jsonl(source, rows)

    receipt = module.build_receipt(source, observed_utc="2026-07-19T03:01:00Z")
    serialized = json.dumps(receipt, sort_keys=True)

    for forbidden in (
        "person@example.com",
        "sk-privateABC123",
        "private.example.test",
        "C:\\Users\\Private",
        agent_id,
        private_bait,
    ):
        assert forbidden not in serialized
    assert not re.search(
        r"(?i)\b[0-9a-f]{8}(?:-[0-9a-f]{4}){3}-[0-9a-f]{12}\b", serialized
    )
    assert receipt["facts"]["privacy"] == {
        "task_text_retained": False,
        "messages_emitted": False,
        "agent_identifiers_emitted": False,
        "credentials_emitted": False,
        "private_urls_emitted": False,
        "source_path_emitted": False,
    }


def test_tamper_is_detected_even_when_payload_remains_valid_json(tmp_path: Path):
    module = load_module()
    source = tmp_path / "session.jsonl"
    write_jsonl(source, build_complete_rows("44444444-4444-4444-8444-444444444444"))
    receipt = module.build_receipt(source, observed_utc="2026-07-19T04:01:00Z")

    tampered = copy.deepcopy(receipt)
    tampered["facts"]["orchestration"]["total_spawn_events"] = 2

    valid, errors = module.verify_receipt(tampered)
    assert valid is False
    assert "facts_hash_mismatch" in errors
    assert "receipt_hash_mismatch" in errors


def test_rehashed_concurrency_promotion_is_rejected_semantically(tmp_path: Path):
    module = load_module()
    source = tmp_path / "open-lifecycle.jsonl"
    rows = [
        turn_context("2026-07-19T05:00:00.000Z"),
        tool_call(
            "2026-07-19T05:00:01.000Z",
            "spawn-open",
            spawn_source("OpenAI Build Week ProofLock Console package audit."),
        ),
        tool_output(
            "2026-07-19T05:00:02.000Z",
            "spawn-open",
            content_output(
                {
                    "agent_id": "55555555-5555-4555-8555-555555555555",
                    "nickname": "private",
                }
            ),
        ),
    ]
    write_jsonl(source, rows)
    receipt = module.build_receipt(source, observed_utc="2026-07-19T05:01:00Z")
    orchestration = receipt["facts"]["orchestration"]

    assert orchestration["maximum_concurrent_open_agents"] == "NOT_PROVEN"
    assert orchestration["concurrency_evidence_complete"] is False

    forged = copy.deepcopy(receipt)
    forged_orchestration = forged["facts"]["orchestration"]
    forged_orchestration["maximum_concurrent_open_agents"] = 1
    forged_orchestration["concurrency_evidence_complete"] = True
    recompute_hashes(module, forged)

    valid, errors = module.verify_receipt(forged)
    assert valid is False
    assert "unsupported_concurrency_promotion" in errors
    assert "unsupported_concurrency_evidence" in errors


def test_unrelated_unresolved_spawn_is_excluded_from_build_week_diagnostics(tmp_path: Path):
    module = load_module()
    source = tmp_path / "mixed-session.jsonl"
    agent_id = "77777777-7777-4777-8777-777777777777"
    rows = [
        turn_context("2026-07-19T05:30:00.000Z"),
        tool_call(
            "2026-07-19T05:30:01.000Z",
            "unrelated",
            (
                "const message = getPrivateTask(); "
                "const r = await tools.multi_agent_v1__spawn_agent("
                "{agent_type:\"worker\",fork_context:false,message}); text(r);"
            ),
        ),
        tool_output(
            "2026-07-19T05:30:02.000Z",
            "unrelated",
            content_output({"agent_id": "88888888-8888-4888-8888-888888888888"}),
        ),
        tool_call(
            "2026-07-19T05:30:03.000Z",
            "build-week",
            spawn_source("OpenAI Build Week ProofLock Console package audit."),
        ),
        tool_output(
            "2026-07-19T05:30:04.000Z",
            "build-week",
            content_output({"agent_id": agent_id}),
        ),
    ]
    write_jsonl(source, rows)

    receipt = module.build_receipt(source, observed_utc="2026-07-19T05:31:00Z")
    orchestration = receipt["facts"]["orchestration"]

    assert orchestration["spawn_attempt_count"] == 1
    assert orchestration["total_spawn_events"] == 1
    assert orchestration["unresolved_build_week_spawn_tool_call_count"] == 0
    assert orchestration["ambiguous_build_week_agent_identity_output_count"] == 0


def test_malformed_source_fails_closed(tmp_path: Path):
    module = load_module()
    source = tmp_path / "malformed.jsonl"
    source.write_text('{"timestamp":"2026-07-19T06:00:00Z"}\n{broken\n', encoding="utf-8")

    with pytest.raises(module.ReceiptBuildError, match="parse failed"):
        module.build_receipt(source, observed_utc="2026-07-19T06:01:00Z")


def test_atomic_writer_round_trips_and_leaves_no_temporary_file(tmp_path: Path):
    module = load_module()
    source = tmp_path / "session.jsonl"
    write_jsonl(source, build_complete_rows("66666666-6666-4666-8666-666666666666"))
    receipt = module.build_receipt(source, observed_utc="2026-07-19T07:01:00Z")
    output = tmp_path / "receipt.json"

    module.atomic_write_json(output, receipt)

    assert json.loads(output.read_text(encoding="utf-8")) == receipt
    assert list(tmp_path.glob(".receipt.json.*.tmp")) == []


def test_checked_in_receipt_verifies():
    module = load_module()
    valid, errors = module.verify_receipt_file(module.DEFAULT_OUTPUT)

    assert valid is True, errors
