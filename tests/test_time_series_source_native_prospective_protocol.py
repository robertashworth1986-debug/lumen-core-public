from __future__ import annotations

import importlib.util
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = (
    ROOT
    / "code"
    / "ops"
    / "VERIFY_TIME_SERIES_SOURCE_NATIVE_PROSPECTIVE_PROTOCOL.py"
)


def load_module():
    spec = importlib.util.spec_from_file_location(
        "verify_time_series_source_native_prospective_protocol",
        SCRIPT,
    )
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_frozen_protocol_is_self_bound_and_waiting_for_future_rows():
    module = load_module()
    protocol = module.read_protocol()

    errors = module.validate_protocol(protocol)
    status = module.build_status(protocol, errors)

    assert errors == []
    assert status["verification_passed"] is True
    assert status["frozen_artifact_count"] == 5
    assert status["eligible_future_observation_count"] == 0
    assert status["promotion_decision"] == "WAITING_FOR_NEW_SOURCE_ROWS"
    assert status["performance_claim_allowed"] is False
    assert len(status["status_receipt_sha256"]) == 64


def test_protocol_verifier_rejects_artifact_hash_tampering():
    module = load_module()
    protocol = json.loads(
        json.dumps(module.read_protocol())
    )
    protocol["frozen_artifacts"][0]["sha256"] = "0" * 64
    unsigned = {
        key: value
        for key, value in protocol.items()
        if key != "protocol_payload_sha256"
    }
    protocol["protocol_payload_sha256"] = module.canonical_sha256(unsigned)

    errors = module.validate_protocol(protocol)

    assert any(
        error.startswith("frozen_artifact_hash_mismatch:")
        for error in errors
    )
