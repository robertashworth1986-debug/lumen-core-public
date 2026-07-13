from __future__ import annotations

import hashlib
import json
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_sector_validation_board_is_auditable_and_keeps_claim_gates_closed() -> None:
    script = ROOT / "code" / "ops" / "BUILD_SECTOR_VALIDATION_PRIORITY_BOARD.py"
    subprocess.run(
        [sys.executable, str(script)],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
        timeout=120,
    )

    payload_path = ROOT / "out" / "ops" / "sector_validation_priority_board_latest.json"
    payload = json.loads(payload_path.read_text(encoding="utf-8"))

    assert payload["schema"] == "sector_validation_priority_board.v1"
    assert payload["summary"]["sector_count"] == 5
    assert payload["summary"]["registered_geometry_family_count"] >= 140
    assert payload["summary"]["current_executable_adapter_count"] >= 5
    assert payload["summary"]["ready_for_real_dollar_claim"] is False
    assert payload["summary"]["ready_for_unbeatable_claim"] is False
    assert payload["geometry_execution_audit"]["all_140_executed_under_one_locked_protocol"] is False
    assert len(payload["top_five_questions"]) == 5
    assert [row["rank"] for row in payload["sectors"]] == [1, 2, 3, 4, 5]
    assert all(row["realized_savings_claim_allowed"] is False for row in payload["sectors"])
    assert all(row["official_loss_surface"]["sources"] for row in payload["sectors"])
    assert all(row["validation_wedge"]["pass_gate"] for row in payload["sectors"])


def test_sector_validation_manifest_hashes_every_public_artifact() -> None:
    manifest_path = ROOT / "out" / "ops" / "sector_validation_priority_board_manifest_latest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))

    assert manifest["schema"] == "sector_validation_priority_board_manifest.v1"
    assert len(manifest["artifacts"]) == 3
    for row in manifest["artifacts"]:
        path = ROOT / row["path"]
        assert path.exists()
        assert path.stat().st_size == row["bytes"]
        assert hashlib.sha256(path.read_bytes()).hexdigest() == row["sha256"]

    expected_chain = hashlib.sha256(
        json.dumps(manifest["artifacts"], sort_keys=True).encode("utf-8")
    ).hexdigest()
    assert manifest["manifest_chain_sha256"] == expected_chain
