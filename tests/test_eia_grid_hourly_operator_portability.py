from __future__ import annotations

import hashlib
import importlib.util
import json
import sys
import zipfile
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[1]
RUNNER_PATH = (
    ROOT / "code" / "ops" / "RUN_EIA_GRID_HOURLY_OPERATOR_PORTABILITY_CHECK.py"
)
PUBLIC_RECEIPT = (
    ROOT
    / "evidence"
    / "reproducibility"
    / "eia_grid_hourly_operator_portability_receipt_20260721.json"
)


def load_runner():
    spec = importlib.util.spec_from_file_location("eia_operator_portability", RUNNER_PATH)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def fake_packet(tmp_path: Path) -> Path:
    root = tmp_path / "packet"
    verifier = root / "code" / "ops" / "VERIFY_EIA_GRID_HOURLY_REPRODUCTION_PACKET.py"
    verifier.parent.mkdir(parents=True)
    (root / "config").mkdir()
    (root / "REVIEWER_RECEIPT_TEMPLATE.json").write_text("{}\n", encoding="utf-8")
    (
        root / "config" / "eia_grid_hourly_external_evaluator_protocol_template_v1.json"
    ).write_text("{}\n", encoding="utf-8")
    verifier.write_text(
        """import json, sys
if '--receipt' in sys.argv:
    output = {
        'receipt_integrity_passed': True,
        'independent_reproduction_complete': False,
        'performance_promotion_allowed': False,
        'status': 'UNSIGNED_INDEPENDENT_REPRODUCTION_TEMPLATE_VALID',
    }
elif '--evaluator-protocol' in sys.argv:
    output = {
        'protocol_integrity_passed': True,
        'evaluation_design_frozen': False,
        'performance_promotion_allowed': False,
        'status': 'UNSIGNED_EXTERNAL_EVALUATOR_PROTOCOL_TEMPLATE_VALID',
    }
else:
    output = {
        'packet_integrity_passed': True,
        'packet_manifest_file_sha256': 'a' * 64,
        'packet_manifest_payload_sha256': 'b' * 64,
        'snapshot': {
            'protocol_id': 'FIXTURE',
            'prediction_count': 2,
            'settlement_count': 1,
            'common_settled_hour_count': 0,
            'prediction_terminal_sha256': 'c' * 64,
            'settlement_terminal_sha256': 'd' * 64,
        },
    }
print(json.dumps(output, sort_keys=True))
""",
        encoding="utf-8",
    )
    packet_zip = tmp_path / "packet.zip"
    with zipfile.ZipFile(packet_zip, "w") as archive:
        for path in root.rglob("*"):
            if path.is_file():
                archive.write(path, path.relative_to(root).as_posix())
    return packet_zip


def test_operator_check_stays_outside_external_validation(tmp_path: Path) -> None:
    runner = load_runner()
    packet_zip = fake_packet(tmp_path)
    expected = hashlib.sha256(packet_zip.read_bytes()).hexdigest()

    receipt = runner.run_portability_check(
        packet_zip,
        [Path(sys.executable)],
        expected,
    )

    assert receipt["all_checks_passed"] is True
    assert receipt["operator_controlled"] is True
    assert receipt["reviewer_controlled"] is False
    assert receipt["independent_reproduction_complete"] is False
    assert receipt["external_validation_complete"] is False
    assert receipt["performance_promotion_allowed"] is False
    assert receipt["fresh_extraction_per_runtime"] is True
    assert receipt["runner"]["path"].endswith("OPERATOR_PORTABILITY_CHECK.py")
    assert len(receipt["runner"]["sha256"]) == 64
    assert receipt["runner"]["network_required"] is False


@pytest.mark.parametrize("member", ["../escape.txt", "C:/escape.txt"])
def test_zip_traversal_is_rejected(tmp_path: Path, member: str) -> None:
    runner = load_runner()
    packet_zip = tmp_path / "unsafe.zip"
    with zipfile.ZipFile(packet_zip, "w") as archive:
        archive.writestr(member, "blocked")

    with zipfile.ZipFile(packet_zip) as archive:
        with pytest.raises(ValueError, match="unsafe ZIP member"):
            runner.validate_zip_members(archive)


def test_public_portability_receipt_keeps_claim_gates_closed() -> None:
    receipt = json.loads(PUBLIC_RECEIPT.read_text(encoding="utf-8"))

    assert receipt["status"] == "OPERATOR_CONTROLLED_CROSS_VERSION_CHECK_PASSED"
    assert receipt["all_checks_passed"] is True
    assert receipt["cross_version_check_passed"] is True
    assert receipt["runtime_version_count"] >= 2
    assert len(receipt["runner"]["sha256"]) == 64
    assert receipt["independent_reproduction_complete"] is False
    assert receipt["external_validation_complete"] is False
    assert receipt["performance_promotion_allowed"] is False
