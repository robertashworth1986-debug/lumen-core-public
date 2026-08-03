from __future__ import annotations

import hashlib
import importlib.util
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "code" / "CANONICAL_GOV_DATA_COLLECTOR.py"


def load_module():
    spec = importlib.util.spec_from_file_location("canonical_gov_collector", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_identical_snapshots_are_content_addressed_and_deduplicated(tmp_path):
    module = load_module()
    module.SNAP_DIR = tmp_path
    payload = {"response": {"data": [{"period": "2026-07-25", "value": 1}]}}

    first = module.write_content_addressed_snapshot("eia_rto", payload)
    second = module.write_content_addressed_snapshot("eia_rto", payload)

    assert first["snapshot"] == second["snapshot"]
    assert first["snapshot_sha256"] == second["snapshot_sha256"]
    assert first["snapshot_new"] is True
    assert second["snapshot_new"] is False
    assert len(list(tmp_path.glob("*.json"))) == 1

    path = Path(first["snapshot"])
    assert first["snapshot_bytes"] == path.stat().st_size
    assert first["snapshot_sha256"] == hashlib.sha256(path.read_bytes()).hexdigest()
    assert first["snapshot_sha256"][:20] in path.name


def test_changed_snapshot_gets_a_new_immutable_path(tmp_path):
    module = load_module()
    module.SNAP_DIR = tmp_path

    first = module.write_content_addressed_snapshot("usgs_iv", {"value": 1})
    second = module.write_content_addressed_snapshot("usgs_iv", {"value": 2})

    assert first["snapshot"] != second["snapshot"]
    assert first["snapshot_sha256"] != second["snapshot_sha256"]
    assert second["snapshot_new"] is True
    assert len(list(tmp_path.glob("*.json"))) == 2


def test_collector_redacts_secret_values_in_urls_and_errors():
    module = load_module()
    fake_key = "FAKE-COLLECTOR-SECRET-123"
    fake_email = "owner@example.test"
    row = {
        "source": "FIXTURE",
        "url": (
            "https://example.test/probe?"
            f"email={fake_email}&api_key={fake_key}&limit=5"
        ),
        "error": (
            f'failed: {{"email":"{fake_email}",'
            f'"key":"{fake_key}"}}'
        ),
    }

    sanitized = module.sanitize_check_row(row)
    serialized = str(sanitized)

    assert fake_key not in serialized
    assert fake_email not in serialized
    assert "limit=5" in sanitized["url"]
    assert "REDACTED" in serialized
