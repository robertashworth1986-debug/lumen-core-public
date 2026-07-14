from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

import pytest
from pydantic import ValidationError


ROOT = Path(__file__).resolve().parents[1]
CODE = ROOT / "code"
if str(CODE) not in sys.path:
    sys.path.insert(0, str(CODE))

import autonomous_agent_manifest as manifest  # noqa: E402


def test_human_unlock_bearer_token_is_required_and_exact() -> None:
    assert manifest._human_unlock_authorized("", "Bearer value") is False
    assert manifest._human_unlock_authorized("value", None) is False
    assert manifest._human_unlock_authorized("value", "Basic value") is False
    assert manifest._human_unlock_authorized("value", "Bearer wrong") is False
    assert manifest._human_unlock_authorized("value", "Bearer value") is True


def test_approval_request_rejects_unbounded_actions_and_types() -> None:
    with pytest.raises(ValidationError):
        manifest.ApproveRequest(item_id="item-1", item_type="unknown", action="approve")
    with pytest.raises(ValidationError):
        manifest.ApproveRequest(item_id="item-1", item_type="grant_submission", action="submit")
    with pytest.raises(ValidationError):
        manifest.ApproveRequest(item_id="../../item", item_type="grant_submission", action="approve")


def test_public_queue_snapshot_removes_private_source_payloads() -> None:
    snapshot = manifest._public_queue_snapshot(
        {
            "generated_utc": "2026-07-13T00:00:00Z",
            "total_pending": 1,
            "items": [
                {
                    "id": "item-1",
                    "agent_type": "email_dispatch",
                    "title": "Review",
                    "metadata": {"api_key": "must-not-leak", "recipient": "private@example.test"},
                }
            ],
        }
    )
    assert snapshot["items"][0]["id"] == "item-1"
    assert "metadata" not in snapshot["items"][0]
    assert "must-not-leak" not in json.dumps(snapshot)


def test_approval_audit_receipts_form_a_verifiable_hash_chain(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setattr(manifest, "_OUT", tmp_path)
    first = manifest._append_audit_entry({"item_id": "one", "action": "approve"})
    second = manifest._append_audit_entry({"item_id": "two", "action": "delay"})

    assert first["previous_hash"] == "0" * 64
    assert second["previous_hash"] == first["entry_hash"]

    for entry in (first, second):
        body = {key: value for key, value in entry.items() if key != "entry_hash"}
        canonical = json.dumps(body, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
        assert hashlib.sha256(canonical.encode("utf-8")).hexdigest() == entry["entry_hash"]

    lines = (tmp_path / "ops" / "agent_approval_log.jsonl").read_text(encoding="utf-8").splitlines()
    assert len(lines) == 2


def test_short_ids_use_sha256_and_are_deterministic() -> None:
    expected = hashlib.sha256(b"same-input").hexdigest()[:12]
    assert manifest._short_id("same-input") == expected
    assert manifest._short_id("same-input") == manifest._short_id("same-input")
