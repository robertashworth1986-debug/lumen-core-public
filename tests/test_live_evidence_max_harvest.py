from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_safe_key_provider_ping_masks_and_writes() -> None:
    script = ROOT / "code" / "ops" / "BUILD_SAFE_CREDENTIAL_PROVIDER_PING.py"
    subprocess.run([sys.executable, str(script)], cwd=ROOT, check=True, capture_output=True, text=True, timeout=120)

    payload_path = ROOT / "out" / "ops" / "safe_key_provider_ping_latest.json"
    payload = json.loads(payload_path.read_text(encoding="utf-8"))

    assert payload["schema"] == "safe_key_provider_ping.v1"
    assert payload["summary"]["provider_count"] > 0
    assert "env_rows" in payload
    rendered = json.dumps(payload)
    assert "KRAKEN_API_SECRET=" not in rendered
    assert "ALPACA_API_SECRET=" not in rendered


def test_live_evidence_harvest_skip_network_keeps_claim_gates_closed() -> None:
    script = ROOT / "code" / "ops" / "BUILD_LIVE_EVIDENCE_MAX_HARVEST.py"
    subprocess.run(
        [sys.executable, str(script), "--skip-network"],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
        timeout=240,
    )

    payload_path = ROOT / "out" / "ops" / "live_evidence_max_harvest_latest.json"
    payload = json.loads(payload_path.read_text(encoding="utf-8"))
    summary = payload["summary"]

    assert payload["schema"] == "live_evidence_max_harvest.v2"
    assert payload["mode"] == "reuse_existing_snapshots"
    assert summary["steps_ok"] == summary["steps_count"]
    assert summary["kraken_live_execution_allowed"] is False
    assert summary["ready_for_live_geometry_claim"] is False
    assert summary["ready_for_real_dollar_claim"] is False
    assert summary["requested_max_rows_per_source"] == 250
    assert summary["requested_source_timeout_seconds"] == 30
    assert summary["paired_inference_card_count"] == 4
    assert summary["energy_pressure_ready_for_proxy_claim"] is False
    assert summary["energy_stress_proxy_description_allowed"] is True
    assert 0 <= summary["holm_positive_card_count"] <= summary["paired_inference_card_count"]
    assert len(payload["next_actions"]) >= 5
