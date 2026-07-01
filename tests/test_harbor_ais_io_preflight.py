from __future__ import annotations

import hashlib
import importlib.util
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "code" / "ops" / "BUILD_HARBOR_AIS_IO_PREFLIGHT.py"


def load_module():
    spec = importlib.util.spec_from_file_location("harbor_ais_io_preflight", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def write_fixture(path: Path, text: str) -> dict[str, object]:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    data = path.read_bytes()
    return {"path": str(path), "bytes": len(data), "sha256": hashlib.sha256(data).hexdigest()}


def test_io_preflight_marks_temp_splits_ready_with_full_hash(tmp_path):
    module = load_module()
    dev = write_fixture(tmp_path / "development.csv", "MMSI,BaseDateTime,LAT,LON\n1,2024-01-01T00:00:00,1,1\n")
    val = write_fixture(tmp_path / "validation.csv", "MMSI,BaseDateTime,LAT,LON\n2,2024-01-01T12:00:00,2,2\n")
    split_json = tmp_path / "split.json"
    split_json.write_text(
        json.dumps(
            {
                "selected_region": {"region_id": "unit", "label": "Unit Harbor"},
                "splits": {"development": dev, "validation": val},
            }
        ),
        encoding="utf-8",
    )

    payload = module.build_preflight(
        split_json,
        timeout_seconds=2,
        sample_bytes=16,
        full_hash=True,
        use_subprocess=False,
        write_outputs=False,
    )

    assert payload["schema"] == "harbor_ais_io_preflight_v1"
    assert payload["posture"] == "PUBLIC_AIS_SPLIT_IO_READY"
    assert payload["summary"]["required_ok"] == 2
    assert payload["summary"]["all_required_ok"] is True
    assert all(row["sha256_matches"] is True for row in payload["probes"])
    assert "does not establish HarborSentinel detection performance" in payload["claim_boundary"]


def test_io_preflight_blocks_missing_validation_split(tmp_path):
    module = load_module()
    dev = write_fixture(tmp_path / "development.csv", "MMSI,BaseDateTime,LAT,LON\n1,2024-01-01T00:00:00,1,1\n")
    split_json = tmp_path / "split.json"
    split_json.write_text(
        json.dumps(
            {
                "selected_region": {"region_id": "unit", "label": "Unit Harbor"},
                "splits": {
                    "development": dev,
                    "validation": {
                        "path": str(tmp_path / "missing_validation.csv"),
                        "bytes": 10,
                        "sha256": "0" * 64,
                    },
                },
            }
        ),
        encoding="utf-8",
    )

    payload = module.build_preflight(
        split_json,
        timeout_seconds=2,
        sample_bytes=16,
        full_hash=True,
        use_subprocess=False,
        write_outputs=False,
    )

    assert payload["posture"] == "PUBLIC_AIS_SPLIT_IO_BLOCKED"
    assert payload["summary"]["required_ok"] == 1
    missing = next(row for row in payload["probes"] if row["label"] == "validation")
    assert missing["status"] == "missing"
    assert missing["ok"] is False
