import importlib.util
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "code" / "auto_ticket_producer.py"


def load_module():
    spec = importlib.util.spec_from_file_location("auto_ticket_producer_authority", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_validate_only_ticket_does_not_consume_live_authority(monkeypatch):
    module = load_module()

    def unexpected_validator(**_kwargs):
        raise AssertionError("paper validation must not inspect live authority")

    monkeypatch.setattr(module, "validate_live_action_authority", unexpected_validator)

    state = module._require_live_authority(
        validate=True,
        controller="Robert",
        action="paper ticket",
    )

    assert state["required"] is False
    assert state["authorized"] is False
    assert state["reasons"] == ["validate_only_ticket"]


def test_live_ticket_fails_closed_without_fresh_authority(monkeypatch):
    module = load_module()
    monkeypatch.setattr(
        module,
        "validate_live_action_authority",
        lambda **_kwargs: {"authorized": False, "reasons": ["receipt_expired"]},
    )

    with pytest.raises(RuntimeError, match="fresh hash-bound human action-time authority required"):
        module._require_live_authority(
            validate=False,
            controller="Robert",
            action="live ticket",
        )


def test_live_ticket_accepts_shared_authority_validator(monkeypatch):
    module = load_module()
    calls = []

    def authorized_validator(**kwargs):
        calls.append(kwargs)
        return {"authorized": True, "reasons": []}

    monkeypatch.setattr(module, "validate_live_action_authority", authorized_validator)

    state = module._require_live_authority(
        validate=False,
        controller="Robert",
        action="live ticket",
    )

    assert state["authorized"] is True
    assert state["required"] is True
    assert calls == [{
        "runtime_path": module.RUNTIME_CONTROL_FILE,
        "receipt_path": module.LIVE_ACTION_RECEIPT_FILE,
        "controller": "Robert",
        "ttl_seconds": module.DEFAULT_AUTHORITY_TTL_SEC,
    }]


def test_live_cycle_and_each_automatic_decision_recheck_authority():
    source = SCRIPT.read_text(encoding="utf-8")

    cycle_gate = source.index('action="live ticket cycle"')
    first_scan = source.index("scan_source =")
    decision_gate = source.index('action=f"automatic approval for {tid}"')
    approval_request = source.index('f"{gateway_url}/api/master/approval/decide"')

    assert cycle_gate < first_scan
    assert decision_gate < approval_request
