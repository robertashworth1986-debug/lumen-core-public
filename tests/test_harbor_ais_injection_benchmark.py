from __future__ import annotations

import csv
import importlib.util
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "code" / "ops" / "BUILD_HARBOR_AIS_INJECTION_BENCHMARK.py"


def load_module():
    spec = importlib.util.spec_from_file_location("harbor_ais_injection_benchmark", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def write_csv(path: Path, *, hour: str) -> None:
    rows = []
    for track in range(4):
        for step in range(6):
            rows.append(
                {
                    "MMSI": f"222000{track}",
                    "BaseDateTime": f"2024-01-01T{hour}:{step * 5:02d}:00",
                    "LAT": f"{29.0000 + track * 0.01 + step * 0.001:.6f}",
                    "LON": f"{-90.0000 - track * 0.01 + step * 0.001:.6f}",
                    "SOG": "6.0",
                    "COG": "45.0",
                }
            )
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=["MMSI", "BaseDateTime", "LAT", "LON", "SOG", "COG"])
        writer.writeheader()
        writer.writerows(rows)


def test_injection_benchmark_preserves_claim_boundary(tmp_path):
    module = load_module()
    dev = tmp_path / "development.csv"
    val = tmp_path / "validation.csv"
    write_csv(dev, hour="01")
    write_csv(val, hour="13")
    split = {
        "selected_region": {"region_id": "unit_test_harbor", "label": "Unit Test Harbor"},
        "raw_source": {
            "source_url": "https://example.invalid/ais.csv",
            "source_label": "unit fixture",
            "sha256": "0" * 64,
            "bytes": 1,
        },
        "splits": {
            "development": {"path": str(dev), "rows": 24},
            "validation": {"path": str(val), "rows": 24},
        },
    }
    split_json = tmp_path / "split.json"
    split_json.write_text(json.dumps(split), encoding="utf-8")

    payload = module.build_benchmark(
        split_json,
        max_interval_minutes=30,
        max_injections_per_family=4,
        min_segments=4,
        write_outputs=False,
    )

    assert payload["schema"] == "harbor_ais_injection_benchmark_v1"
    assert payload["development"]["segments"] >= 4
    assert payload["validation"]["segments"] >= 4
    assert payload["controlled_injection_benchmark"]["total_injected_segments"] > 0
    assert payload["controlled_injection_benchmark"]["motion_consistency_recall"] >= (
        payload["controlled_injection_benchmark"]["speed_only_baseline_recall"]
    )
    suite = payload["controlled_injection_benchmark"]["baseline_suite"]
    assert set(suite["baselines"]) == {
        "reported_speed_sog_p99",
        "derived_trajectory_speed_p99",
        "speed_gap_consistency_p99",
        "heading_rate_p99",
    }
    assert suite["best_single_axis_baseline"]["recall"] <= payload["controlled_injection_benchmark"]["motion_consistency_recall"]
    assert "does not establish HarborSentinel operational detection performance" in payload["claim_boundary"]
