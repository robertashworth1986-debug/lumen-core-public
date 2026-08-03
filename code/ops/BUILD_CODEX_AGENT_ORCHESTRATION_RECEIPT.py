from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import tempfile
from collections import Counter
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable


ROOT = Path(__file__).resolve().parents[2]
DEFAULT_OUTPUT = (
    ROOT
    / "grant_submissions"
    / "OPENAI_BUILD_WEEK_20260721"
    / "CODEX_AGENT_ORCHESTRATION_RECEIPT_2026-07-19.json"
)
SCHEMA = "lumencore.codex_agent_orchestration_receipt.v1"
CUTOFF_UTC = "2026-07-17T00:00:00.000Z"
RECEIPT_STATUS = "RECORDED_METADATA_ONLY"
CONCURRENCY_NOT_PROVEN = "NOT_PROVEN"

BUILD_WEEK_MARKERS = (
    "openai build week",
    "openai_build_week",
    "prooflock console",
    "prooflock_console",
    "devpost",
)
ROLE_CATEGORIES = (
    "orchestration_receipt",
    "portal_progress_receipt",
    "devpost_submission_readiness",
    "public_demo_evidence",
    "demo_media",
    "package_integrity_review",
    "build_week_support_other",
)
TERMINAL_STATUSES = ("cancelled", "closed", "completed", "errored", "failed", "interrupted")
UUID_RE = re.compile(
    r"(?i)\b[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}\b"
)
UUID_FULL_RE = re.compile(
    r"(?i)^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$"
)
SCRIPT_RUNNING_RE = re.compile(r"Script running with cell ID\s+([A-Za-z0-9_-]+)")
EMAIL_RE = re.compile(r"(?i)\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b")
URL_RE = re.compile(r"(?i)\bhttps?://\S+")
PRIVATE_PATH_RE = re.compile(r"(?i)(?:[A-Z]:\\Users\\|/Users/|/home/)[^\s\"']+")
SECRET_RE = re.compile(
    r"(?i)(?:\bsk-[A-Za-z0-9_-]{8,}\b|\b(?:api[_ -]?key|password|passwd|secret)\s*[:=])"
)

CLAIM_BOUNDARY = (
    "This receipt attests only to metadata-level Codex orchestration events recorded in the "
    "bounded local session window. A spawn event means a tool result exposed an opaque agent "
    "identity; it does not establish autonomous operation, current activity, task success, "
    "correctness, external validation, an award, endorsement, or a seven-agent lineup. "
    "Maximum concurrency is not claimed."
)


class ReceiptBuildError(RuntimeError):
    pass


@dataclass(frozen=True)
class SpawnDescriptor:
    role: str | None


@dataclass
class ToolCall:
    timestamp_utc: str
    spawn_descriptors: tuple[SpawnDescriptor, ...]
    terminal_tools: tuple[str, ...]
    target_agent_ids: tuple[str, ...]
    model_context: tuple[str, str] | None
    mapped_agent_ids: set[str]


def canonical_utc(value: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ReceiptBuildError("A timezone-aware UTC timestamp is required.")
    normalized = value.strip()
    if normalized.endswith("Z"):
        normalized = normalized[:-1] + "+00:00"
    try:
        parsed = datetime.fromisoformat(normalized)
    except ValueError as exc:
        raise ReceiptBuildError("Invalid ISO-8601 timestamp.") from exc
    if parsed.tzinfo is None:
        raise ReceiptBuildError("Timestamp must include a timezone.")
    return parsed.astimezone(timezone.utc).isoformat(timespec="milliseconds").replace(
        "+00:00", "Z"
    )


def stable_hash(value: Any) -> str:
    encoded = json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
        allow_nan=False,
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _scan_js_string(source: str, start: int) -> tuple[str, int]:
    quote = source[start]
    if quote not in ('"', "'", "`"):
        raise ValueError("Not a JavaScript string literal.")
    cursor = start + 1
    decoded: list[str] = []
    simple_escapes = {
        "b": "\b",
        "f": "\f",
        "n": "\n",
        "r": "\r",
        "t": "\t",
        "v": "\v",
        "0": "\0",
    }
    while cursor < len(source):
        char = source[cursor]
        if char == quote:
            return "".join(decoded), cursor + 1
        if char != "\\":
            decoded.append(char)
            cursor += 1
            continue
        if cursor + 1 >= len(source):
            raise ValueError("Truncated JavaScript escape.")
        escaped = source[cursor + 1]
        if escaped == "u" and cursor + 5 < len(source):
            digits = source[cursor + 2 : cursor + 6]
            if re.fullmatch(r"[0-9a-fA-F]{4}", digits):
                decoded.append(chr(int(digits, 16)))
                cursor += 6
                continue
        if escaped == "x" and cursor + 3 < len(source):
            digits = source[cursor + 2 : cursor + 4]
            if re.fullmatch(r"[0-9a-fA-F]{2}", digits):
                decoded.append(chr(int(digits, 16)))
                cursor += 4
                continue
        if escaped in ("\n", "\r"):
            cursor += 2
            continue
        decoded.append(simple_escapes.get(escaped, escaped))
        cursor += 2
    raise ValueError("Unterminated JavaScript string literal.")


def _balanced_segment(source: str, start: int, opener: str, closer: str) -> tuple[str, int]:
    if source[start] != opener:
        raise ValueError("Balanced segment does not start with the expected delimiter.")
    cursor = start
    depth = 0
    while cursor < len(source):
        char = source[cursor]
        if char in ('"', "'", "`"):
            _, cursor = _scan_js_string(source, cursor)
            continue
        if char == opener:
            depth += 1
        elif char == closer:
            depth -= 1
            if depth == 0:
                return source[start : cursor + 1], cursor + 1
        cursor += 1
    raise ValueError("Unterminated balanced segment.")


def _task_array_messages(source: str) -> list[str]:
    messages: list[str] = []
    pattern = re.compile(r"\bconst\s+[A-Za-z_$][A-Za-z0-9_$]*\s*=\s*\[")
    for match in pattern.finditer(source):
        try:
            blob, _ = _balanced_segment(source, match.end() - 1, "[", "]")
            rows = json.loads(blob)
        except (ValueError, json.JSONDecodeError):
            continue
        if not isinstance(rows, list):
            continue
        for row in rows:
            if isinstance(row, list) and len(row) >= 2 and isinstance(row[1], str):
                messages.append(row[1])
    return messages


def _direct_messages(source: str) -> list[str]:
    messages: list[str] = []
    for match in re.finditer(r"\bmessage\s*:\s*", source):
        cursor = match.end()
        if cursor >= len(source) or source[cursor] not in ('"', "'", "`"):
            continue
        try:
            message, _ = _scan_js_string(source, cursor)
        except ValueError:
            continue
        messages.append(message)
    return messages


def _is_build_week_task(message: str) -> bool:
    lowered = message.lower()
    return any(marker in lowered for marker in BUILD_WEEK_MARKERS)


def _role_for_task(message: str) -> str:
    lowered = message.lower()
    if (
        "build_codex_agent_orchestration_receipt" in lowered
        or "agent-orchestration receipt" in lowered
    ):
        return "orchestration_receipt"
    if (
        "build_openai_build_week_portal_progress_receipt" in lowered
        or "portal-progress receipt" in lowered
        or "portal progress receipt" in lowered
    ):
        return "portal_progress_receipt"
    if (
        "build_openai_build_week_devpost_completion_kit" in lowered
        or "devpost completion kit" in lowered
    ):
        return "devpost_submission_readiness"
    if (
        "build_openai_build_week_public_demo_receipt" in lowered
        or "public demo receipt" in lowered
    ):
        return "public_demo_evidence"
    if any(
        marker in lowered
        for marker in ("demo narration", "storyboard", "youtube demo", "voiceover")
    ):
        return "demo_media"
    if any(marker in lowered for marker in ("independent review", "read-only review", "audit")):
        return "package_integrity_review"
    return "build_week_support_other"


def extract_spawn_descriptors(source: str) -> tuple[SpawnDescriptor, ...]:
    messages = _task_array_messages(source) + _direct_messages(source)
    return tuple(
        SpawnDescriptor(role=_role_for_task(message) if _is_build_week_task(message) else None)
        for message in messages
    )


def _extract_target_agent_ids(source: str) -> tuple[str, ...]:
    targets: list[str] = []
    for match in re.finditer(r"\btarget\s*:\s*", source):
        cursor = match.end()
        if cursor < len(source) and source[cursor] in ('"', "'", "`"):
            try:
                target, _ = _scan_js_string(source, cursor)
            except ValueError:
                continue
            if UUID_FULL_RE.fullmatch(target):
                targets.append(target.lower())
    for match in re.finditer(r"\btargets\s*:\s*\[", source):
        try:
            blob, _ = _balanced_segment(source, match.end() - 1, "[", "]")
            values = json.loads(blob)
        except (ValueError, json.JSONDecodeError):
            continue
        if isinstance(values, list):
            for value in values:
                if isinstance(value, str) and UUID_FULL_RE.fullmatch(value):
                    targets.append(value.lower())
    return tuple(dict.fromkeys(targets))


def _parse_structured_string(value: str) -> Any | None:
    stripped = value.strip()
    if not stripped or stripped[0] not in "[{":
        return None
    try:
        return json.loads(stripped)
    except json.JSONDecodeError:
        return None


def _walk_structured(value: Any, *, depth: int = 0) -> Iterable[Any]:
    if depth > 12:
        return
    yield value
    if isinstance(value, dict):
        for child in value.values():
            yield from _walk_structured(child, depth=depth + 1)
    elif isinstance(value, list):
        for child in value:
            yield from _walk_structured(child, depth=depth + 1)
    elif isinstance(value, str):
        parsed = _parse_structured_string(value)
        if parsed is not None:
            yield from _walk_structured(parsed, depth=depth + 1)


def _structured_output(raw_output: Any) -> Any:
    if isinstance(raw_output, str):
        parsed = _parse_structured_string(raw_output)
        return parsed if parsed is not None else raw_output
    return raw_output


def _extract_agent_ids(raw_output: Any) -> tuple[str, ...]:
    found: list[str] = []
    for node in _walk_structured(_structured_output(raw_output)):
        if not isinstance(node, dict):
            continue
        value = node.get("agent_id")
        if isinstance(value, str) and UUID_FULL_RE.fullmatch(value):
            normalized = value.lower()
            if normalized not in found:
                found.append(normalized)
    return tuple(found)


def _terminal_status_from_mapping(value: Any) -> str | None:
    if not isinstance(value, dict):
        return None
    for status in TERMINAL_STATUSES:
        if status in value:
            return status
    direct = value.get("status")
    if isinstance(direct, str) and direct.lower() in TERMINAL_STATUSES:
        return direct.lower()
    return None


def _extract_terminal_statuses(
    raw_output: Any,
    target_agent_ids: tuple[str, ...],
) -> dict[str, str]:
    statuses: dict[str, str] = {}
    generic_previous: list[str] = []
    for node in _walk_structured(_structured_output(raw_output)):
        if not isinstance(node, dict):
            continue
        status_map = node.get("status")
        if isinstance(status_map, dict):
            for agent_id, value in status_map.items():
                if isinstance(agent_id, str) and UUID_FULL_RE.fullmatch(agent_id):
                    terminal = _terminal_status_from_mapping(value)
                    if terminal is not None:
                        statuses[agent_id.lower()] = terminal
        previous = node.get("previous_status")
        terminal = _terminal_status_from_mapping(previous)
        if terminal is not None:
            generic_previous.append(terminal)
        agent_id = node.get("agent_id")
        direct_status = node.get("status")
        if (
            isinstance(agent_id, str)
            and UUID_FULL_RE.fullmatch(agent_id)
            and isinstance(direct_status, str)
            and direct_status.lower() in TERMINAL_STATUSES
        ):
            statuses[agent_id.lower()] = direct_status.lower()
    if len(target_agent_ids) == 1 and generic_previous:
        statuses[target_agent_ids[0]] = generic_previous[-1]
    return statuses


def _raw_output_text(raw_output: Any) -> str:
    if isinstance(raw_output, str):
        return raw_output
    return json.dumps(raw_output, sort_keys=True, separators=(",", ":"), ensure_ascii=True)


def _privacy_findings(payload: Any) -> list[str]:
    findings: set[str] = set()

    def visit(value: Any) -> None:
        if isinstance(value, dict):
            for key, child in value.items():
                visit(str(key))
                visit(child)
            return
        if isinstance(value, list):
            for child in value:
                visit(child)
            return
        if not isinstance(value, str):
            return
        if UUID_RE.search(value):
            findings.add("uuid_like_identifier")
        if EMAIL_RE.search(value):
            findings.add("email_address")
        if URL_RE.search(value):
            findings.add("url")
        if PRIVATE_PATH_RE.search(value):
            findings.add("private_local_path")
        if SECRET_RE.search(value):
            findings.add("credential_like_text")

    visit(payload)
    return sorted(findings)


def _ordered_counts(counter: Counter[str], allowed: Iterable[str]) -> dict[str, int]:
    return {key: int(counter[key]) for key in allowed if counter[key]}


def build_receipt(
    source_path: Path,
    *,
    observed_utc: str,
    cutoff_utc: str = CUTOFF_UTC,
) -> dict[str, Any]:
    source_path = Path(source_path)
    if not source_path.is_file():
        raise ReceiptBuildError("Codex session source is missing.")

    observed = canonical_utc(observed_utc)
    cutoff = canonical_utc(cutoff_utc)
    observed_dt = datetime.fromisoformat(observed.replace("Z", "+00:00"))
    cutoff_dt = datetime.fromisoformat(cutoff.replace("Z", "+00:00"))
    if observed_dt < cutoff_dt:
        raise ReceiptBuildError("Observation timestamp precedes the Build Week cutoff.")

    calls: dict[str, ToolCall] = {}
    cell_to_call: dict[str, str] = {}
    outer_wait_to_call: dict[str, str] = {}
    current_model: tuple[str, str] | None = None
    attempts: list[tuple[str, tuple[str, str] | None]] = []
    spawn_events: list[tuple[str, str, tuple[str, str] | None]] = []
    terminal_by_agent: dict[str, str] = {}
    in_window_records = 0
    unresolved_build_week_spawn_tool_calls = 0
    ambiguous_build_week_agent_identity_outputs = 0

    def process_output(call_id: str, raw_output: Any) -> None:
        nonlocal ambiguous_build_week_agent_identity_outputs
        call = calls.get(call_id)
        if call is None:
            return
        raw_text = _raw_output_text(raw_output)
        running = SCRIPT_RUNNING_RE.search(raw_text)
        if running is not None:
            cell_to_call[running.group(1)] = call_id
            return

        if call.spawn_descriptors:
            observed_ids = [
                agent_id
                for agent_id in _extract_agent_ids(raw_output)
                if agent_id not in call.mapped_agent_ids
            ]
            if observed_ids and len(observed_ids) == len(call.spawn_descriptors):
                for descriptor, agent_id in zip(call.spawn_descriptors, observed_ids, strict=True):
                    call.mapped_agent_ids.add(agent_id)
                    if descriptor.role is not None:
                        spawn_events.append((agent_id, descriptor.role, call.model_context))
            elif observed_ids and any(
                descriptor.role is not None for descriptor in call.spawn_descriptors
            ):
                ambiguous_build_week_agent_identity_outputs += len(observed_ids)

        if call.terminal_tools:
            terminal_by_agent.update(
                _extract_terminal_statuses(raw_output, call.target_agent_ids)
            )

    try:
        with source_path.open("r", encoding="utf-8", errors="strict") as handle:
            for line_number, line in enumerate(handle, start=1):
                try:
                    record = json.loads(line)
                except (UnicodeDecodeError, json.JSONDecodeError) as exc:
                    raise ReceiptBuildError(
                        f"Session JSONL parse failed at line {line_number}; no receipt was emitted."
                    ) from exc
                if not isinstance(record, dict):
                    raise ReceiptBuildError("Session JSONL record is not an object.")
                timestamp = record.get("timestamp")
                if not isinstance(timestamp, str):
                    raise ReceiptBuildError("Session JSONL record lacks a timestamp.")
                try:
                    timestamp_utc = canonical_utc(timestamp)
                except ReceiptBuildError as exc:
                    raise ReceiptBuildError("Session JSONL contains an invalid timestamp.") from exc
                timestamp_dt = datetime.fromisoformat(timestamp_utc.replace("Z", "+00:00"))
                if timestamp_dt < cutoff_dt or timestamp_dt > observed_dt:
                    continue
                in_window_records += 1

                payload = record.get("payload")
                record_type = record.get("type")
                if record_type == "turn_context" and isinstance(payload, dict):
                    model = payload.get("model")
                    effort = payload.get("effort")
                    current_model = (
                        (model, effort)
                        if isinstance(model, str) and isinstance(effort, str)
                        else None
                    )
                    continue
                if record_type != "response_item" or not isinstance(payload, dict):
                    continue

                payload_type = payload.get("type")
                if payload_type in ("custom_tool_call", "function_call"):
                    call_id = payload.get("call_id")
                    name = payload.get("name")
                    source = (
                        payload.get("input")
                        if payload_type == "custom_tool_call"
                        else payload.get("arguments")
                    )
                    if not isinstance(call_id, str) or not isinstance(source, str):
                        continue
                    if name == "wait" and payload_type == "function_call":
                        try:
                            wait_args = json.loads(source)
                        except json.JSONDecodeError:
                            wait_args = {}
                        cell_id = wait_args.get("cell_id") if isinstance(wait_args, dict) else None
                        if isinstance(cell_id, str) and cell_id in cell_to_call:
                            outer_wait_to_call[call_id] = cell_to_call[cell_id]
                        continue

                    has_spawn = "tools.multi_agent_v1__spawn_agent(" in source
                    terminal_tools = tuple(
                        tool
                        for tool in ("wait_agent", "close_agent")
                        if f"tools.multi_agent_v1__{tool}(" in source
                    )
                    if not has_spawn and not terminal_tools:
                        continue
                    descriptors = extract_spawn_descriptors(source) if has_spawn else ()
                    if has_spawn and not descriptors and any(
                        marker in source.lower() for marker in BUILD_WEEK_MARKERS
                    ):
                        unresolved_build_week_spawn_tool_calls += 1
                    for descriptor in descriptors:
                        if descriptor.role is not None:
                            attempts.append((descriptor.role, current_model))
                    calls[call_id] = ToolCall(
                        timestamp_utc=timestamp_utc,
                        spawn_descriptors=descriptors,
                        terminal_tools=terminal_tools,
                        target_agent_ids=_extract_target_agent_ids(source),
                        model_context=current_model,
                        mapped_agent_ids=set(),
                    )
                    continue

                if payload_type not in ("custom_tool_call_output", "function_call_output"):
                    continue
                output_call_id = payload.get("call_id")
                if not isinstance(output_call_id, str):
                    continue
                original_call_id = outer_wait_to_call.get(output_call_id, output_call_id)
                process_output(original_call_id, payload.get("output"))
    except OSError as exc:
        raise ReceiptBuildError("Codex session source could not be read.") from exc

    attempt_roles = Counter(role for role, _ in attempts)
    event_roles = Counter(role for _, role, _ in spawn_events)
    terminal_counts: Counter[str] = Counter()
    without_terminal = 0
    for agent_id, _, _ in spawn_events:
        terminal = terminal_by_agent.get(agent_id)
        if terminal is None:
            without_terminal += 1
        else:
            terminal_counts[terminal] += 1

    model_counts: Counter[tuple[str, str]] = Counter()
    model_unproven = 0
    for _, _, model_context in spawn_events:
        if model_context is None:
            model_unproven += 1
        else:
            model_counts[model_context] += 1
    model_provenance = [
        {
            "model": model,
            "effort": effort,
            "spawn_event_count": count,
            "directly_recorded": True,
            "scope": "coordinator_turn_context_nearest_preceding_spawn_call",
        }
        for (model, effort), count in sorted(model_counts.items())
    ]

    total_spawn_events = len(spawn_events)
    facts: dict[str, Any] = {
        "observation_window": {
            "cutoff_utc": cutoff,
            "observed_utc": observed,
            "scope": "OpenAI Build Week task markers in Codex tool-event metadata",
        },
        "source": {
            "kind": "local_codex_session_jsonl",
            "path_emitted": False,
            "raw_lines_emitted": False,
            "in_window_record_count": in_window_records,
            "parse_mode": "metadata_and_tool_events_only",
        },
        "orchestration": {
            "spawn_attempt_count": len(attempts),
            "total_spawn_events": total_spawn_events,
            "spawn_event_definition": "spawn tool result with opaque agent identity evidence",
            "spawn_attempts_without_agent_identity_evidence": len(attempts)
            - total_spawn_events,
            "attempt_role_category_counts": _ordered_counts(attempt_roles, ROLE_CATEGORIES),
            "role_category_counts": _ordered_counts(event_roles, ROLE_CATEGORIES),
            "terminal_status_counts": _ordered_counts(terminal_counts, TERMINAL_STATUSES),
            "spawn_events_without_terminal_status": without_terminal,
            "maximum_concurrent_open_agents": CONCURRENCY_NOT_PROVEN,
            "concurrency_evidence_complete": False,
            "concurrency_reason": (
                "The session does not provide a complete gap-free lifecycle ledger for every "
                "Build Week spawn, close, and completion transition."
            ),
            "unresolved_build_week_spawn_tool_call_count": (
                unresolved_build_week_spawn_tool_calls
            ),
            "ambiguous_build_week_agent_identity_output_count": (
                ambiguous_build_week_agent_identity_outputs
            ),
        },
        "model_provenance": {
            "records": model_provenance,
            "spawn_events_without_direct_model_context": model_unproven,
            "subagent_model_claimed": False,
        },
        "privacy": {
            "task_text_retained": False,
            "messages_emitted": False,
            "agent_identifiers_emitted": False,
            "credentials_emitted": False,
            "private_urls_emitted": False,
            "source_path_emitted": False,
        },
    }
    if total_spawn_events != sum(event_roles.values()):
        raise ReceiptBuildError("Internal spawn-event accounting failed closed.")
    if total_spawn_events != sum(terminal_counts.values()) + without_terminal:
        raise ReceiptBuildError("Internal terminal-status accounting failed closed.")

    receipt: dict[str, Any] = {
        "schema": SCHEMA,
        "generated_utc": observed,
        "receipt_status": RECEIPT_STATUS,
        "facts": facts,
        "normalized_facts_sha256": stable_hash(facts),
        "claim_boundary": CLAIM_BOUNDARY,
    }
    privacy_findings = _privacy_findings(receipt)
    if privacy_findings:
        raise ReceiptBuildError(
            "Privacy gate failed closed: " + ", ".join(privacy_findings)
        )
    receipt["receipt_sha256"] = stable_hash(receipt)
    valid, errors = verify_receipt(receipt)
    if not valid:
        raise ReceiptBuildError("Receipt self-verification failed: " + "; ".join(errors))
    return receipt


def verify_receipt(receipt: Any) -> tuple[bool, list[str]]:
    errors: list[str] = []
    if not isinstance(receipt, dict):
        return False, ["receipt_not_object"]
    expected_top_level = {
        "schema",
        "generated_utc",
        "receipt_status",
        "facts",
        "normalized_facts_sha256",
        "claim_boundary",
        "receipt_sha256",
    }
    if set(receipt) != expected_top_level:
        errors.append("unexpected_top_level_fields")
    if receipt.get("schema") != SCHEMA:
        errors.append("schema_mismatch")
    if receipt.get("receipt_status") != RECEIPT_STATUS:
        errors.append("status_mismatch")
    if receipt.get("claim_boundary") != CLAIM_BOUNDARY:
        errors.append("claim_boundary_mismatch")
    facts = receipt.get("facts")
    if not isinstance(facts, dict):
        errors.append("facts_missing")
    else:
        if receipt.get("normalized_facts_sha256") != stable_hash(facts):
            errors.append("facts_hash_mismatch")
        window = facts.get("observation_window")
        if not isinstance(window, dict) or receipt.get("generated_utc") != window.get(
            "observed_utc"
        ):
            errors.append("observation_timestamp_mismatch")
        orchestration = facts.get("orchestration")
        if not isinstance(orchestration, dict):
            errors.append("orchestration_missing")
        else:
            total = orchestration.get("total_spawn_events")
            attempts = orchestration.get("spawn_attempt_count")
            roles = orchestration.get("role_category_counts")
            terminal = orchestration.get("terminal_status_counts")
            without_terminal = orchestration.get("spawn_events_without_terminal_status")
            if not isinstance(total, int) or total < 0:
                errors.append("invalid_spawn_total")
            if not isinstance(attempts, int) or attempts < 0 or (
                isinstance(total, int) and attempts < total
            ):
                errors.append("invalid_spawn_attempt_total")
            if not isinstance(roles, dict) or any(
                key not in ROLE_CATEGORIES or not isinstance(value, int) or value <= 0
                for key, value in (roles.items() if isinstance(roles, dict) else ())
            ):
                errors.append("invalid_role_counts")
            elif isinstance(total, int) and sum(roles.values()) != total:
                errors.append("role_total_mismatch")
            if not isinstance(terminal, dict) or any(
                key not in TERMINAL_STATUSES or not isinstance(value, int) or value <= 0
                for key, value in (terminal.items() if isinstance(terminal, dict) else ())
            ):
                errors.append("invalid_terminal_counts")
            elif (
                isinstance(total, int)
                and isinstance(without_terminal, int)
                and sum(terminal.values()) + without_terminal != total
            ):
                errors.append("terminal_total_mismatch")
            if orchestration.get("maximum_concurrent_open_agents") != CONCURRENCY_NOT_PROVEN:
                errors.append("unsupported_concurrency_promotion")
            if orchestration.get("concurrency_evidence_complete") is not False:
                errors.append("unsupported_concurrency_evidence")
        model_provenance = facts.get("model_provenance")
        if not isinstance(model_provenance, dict):
            errors.append("model_provenance_missing")
        else:
            records = model_provenance.get("records")
            if not isinstance(records, list) or any(
                not isinstance(row, dict) or row.get("directly_recorded") is not True
                for row in (records if isinstance(records, list) else ())
            ):
                errors.append("unsupported_model_provenance")
            if model_provenance.get("subagent_model_claimed") is not False:
                errors.append("unsupported_subagent_model_claim")
        privacy = facts.get("privacy")
        if not isinstance(privacy, dict) or any(privacy.values()):
            errors.append("privacy_controls_invalid")

    unhashed = dict(receipt)
    recorded_receipt_hash = unhashed.pop("receipt_sha256", None)
    if recorded_receipt_hash != stable_hash(unhashed):
        errors.append("receipt_hash_mismatch")
    errors.extend(f"privacy_{finding}" for finding in _privacy_findings(receipt))
    return not errors, sorted(set(errors))


def verify_receipt_file(path: Path) -> tuple[bool, list[str]]:
    try:
        payload = json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return False, ["receipt_file_unreadable"]
    return verify_receipt(payload)


def atomic_write_json(path: Path, payload: dict[str, Any]) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary_name = tempfile.mkstemp(
        prefix=f".{path.name}.", suffix=".tmp", dir=path.parent
    )
    temporary_path = Path(temporary_name)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8", newline="\n") as handle:
            json.dump(payload, handle, indent=2, sort_keys=True, ensure_ascii=True, allow_nan=False)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary_path, path)
        # Windows requires a writable descriptor for fsync after the atomic replace.
        with path.open("r+b") as handle:
            os.fsync(handle.fileno())
        try:
            directory_descriptor = os.open(path.parent, os.O_RDONLY)
        except OSError:
            directory_descriptor = None
        if directory_descriptor is not None:
            try:
                os.fsync(directory_descriptor)
            except OSError:
                pass
            finally:
                os.close(directory_descriptor)
    except Exception:
        temporary_path.unlink(missing_ok=True)
        raise


def _safe_summary(receipt: dict[str, Any]) -> dict[str, Any]:
    orchestration = receipt["facts"]["orchestration"]
    return {
        "receipt_status": receipt["receipt_status"],
        "observed_utc": receipt["generated_utc"],
        "spawn_attempt_count": orchestration["spawn_attempt_count"],
        "total_spawn_events": orchestration["total_spawn_events"],
        "terminal_status_counts": orchestration["terminal_status_counts"],
        "maximum_concurrent_open_agents": orchestration[
            "maximum_concurrent_open_agents"
        ],
        "receipt_sha256": receipt["receipt_sha256"],
    }


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Build or verify a privacy-preserving Codex orchestration receipt."
    )
    parser.add_argument("--source", type=Path, help="Local Codex session JSONL source.")
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--observed-utc", help="Explicit deterministic observation cutoff.")
    parser.add_argument("--verify", action="store_true", help="Verify --output without rebuilding.")
    args = parser.parse_args()

    if args.verify:
        valid, errors = verify_receipt_file(args.output)
        print(json.dumps({"valid": valid, "errors": errors}, indent=2, sort_keys=True))
        return 0 if valid else 1
    if args.source is None or args.observed_utc is None:
        parser.error("--source and --observed-utc are required when building.")
    try:
        receipt = build_receipt(args.source, observed_utc=args.observed_utc)
        atomic_write_json(args.output, receipt)
    except ReceiptBuildError as exc:
        print(json.dumps({"receipt_status": "FAILED_CLOSED", "error": str(exc)}, indent=2))
        return 1
    print(json.dumps(_safe_summary(receipt), indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
