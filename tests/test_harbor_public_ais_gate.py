from __future__ import annotations

import csv
import importlib.util
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "code" / "ops" / "BUILD_HARBOR_PUBLIC_AIS_GATE.py"


def load_module():
    spec = importlib.util.spec_from_file_location("harbor_public_ais_gate", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def write_csv(path: Path, rows: list[dict[str, str]]) -> None:
    fieldnames = ["MMSI", "BaseDateTime", "LAT", "LON", "SOG", "COG", "VesselType"]
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def sample_rows(prefix_hour: str, count: int = 8) -> list[dict[str, str]]:
    rows = []
    for idx in range(count):
        rows.append(
            {
                "MMSI": f"111000{idx % 3}",
                "BaseDateTime": f"2024-01-01T{prefix_hour}:{idx:02d}:00",
                "LAT": f"{36.8 + idx * 0.001:.4f}",
                "LON": f"{-76.2 + idx * 0.001:.4f}",
                "SOG": "5.0",
                "COG": "90.0",
                "VesselType": "70",
            }
        )
    return rows


def test_gate_preserves_no_performance_claim_boundary(tmp_path):
    module = load_module()
    dev = tmp_path / "development.csv"
    val = tmp_path / "validation.csv"
    write_csv(dev, sample_rows("01"))
    write_csv(val, sample_rows("13"))
    split = {
        "data_root": str(tmp_path),
        "selected_region": {"region_id": "hampton_roads", "label": "Hampton Roads / Norfolk"},
        "raw_source": {"sha256": "0" * 64},
        "splits": {
            "development": {"path": str(dev)},
            "validation": {"path": str(val)},
        },
    }
    split_json = tmp_path / "split.json"
    split_json.write_text(json.dumps(split), encoding="utf-8")

    payload = module.build_gate(split_json, min_track_points=2, write_outputs=False)

    assert payload["schema"] == "harbor_public_ais_gate_v1"
    assert payload["posture"] == "PUBLIC_AIS_SINGLE_LANE_GATE_BLOCKED"
    assert payload["development"]["row_metrics"]["rows"] == 8
    assert payload["validation"]["row_metrics"]["rows"] == 8
    assert "does not establish HarborSentinel detection performance" in payload["claim_boundary"]
    assert payload["validation"]["track_features_and_diagnostics"]["diagnostic_boundary"].startswith("Outlier rates")
