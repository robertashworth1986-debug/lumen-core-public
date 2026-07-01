from __future__ import annotations

import csv
import hashlib
import importlib.util
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "code" / "ops" / "BUILD_HARBOR_AIS_REVIEW_BURDEN_PROFILE.py"


def load_module():
    spec = importlib.util.spec_from_file_location("harbor_ais_review_burden_profile", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def write_csv(path: Path, *, day: int, speed_offset: float = 0.0) -> None:
    rows = []
    for track in range(8):
        for step in range(10):
            speed = 5.0 + (track % 3) + speed_offset
            rows.append(
                {
                    "MMSI": f"333000{track}",
                    "BaseDateTime": f"2024-01-{day:02d}T{step:02d}:00:00",
                    "LAT": f"{29.0000 + track * 0.01 + step * 0.001:.6f}",
                    "LON": f"{-90.0000 - track * 0.01 + step * 0.001:.6f}",
                    "SOG": f"{speed:.2f}",
                    "COG": f"{45.0 + step * 2.0:.2f}",
                }
            )
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=["MMSI", "BaseDateTime", "LAT", "LON", "SOG", "COG"])
        writer.writeheader()
        writer.writerows(rows)


def split_payload(dev: Path, val: Path) -> dict[str, object]:
    return {
        "selected_region": {"region_id": "unit_test_harbor", "label": "Unit Test Harbor"},
        "splits": {
            "development": {"path": str(dev), "rows": 80},
            "validation": {"path": str(val), "rows": 80},
        },
    }


def test_review_burden_profile_builds_manifested_outputs(tmp_path):
    module = load_module()
    dev = tmp_path / "development.csv"
    val = tmp_path / "validation.csv"
    write_csv(dev, day=1)
    write_csv(val, day=2, speed_offset=0.5)
    split = tmp_path / "split.json"
    split.write_text(json.dumps(split_payload(dev, val)), encoding="utf-8")

    out_dir = tmp_path / "run"
    payload = module.build_profile(
        split_json=split,
        out_dir=out_dir,
        max_interval_minutes=120,
        grid_degrees=0.05,
        caps=(2, 4),
    )

    assert payload["schema"] == "harbor_ais_review_burden_profile_v1"
    assert payload["posture"] == "PUBLIC_AIS_REVIEW_BURDEN_PROFILE_READY"
    assert payload["review_queue"]["validation_segments"] > 0
    assert payload["review_queue"]["validation_hours"] > 0
    assert set(payload["claim_gate"]) == {
        "ready_for_portal_upload",
        "ready_for_submit",
        "measures_false_positive_rate",
        "proves_field_performance",
        "proves_operational_suitability",
    }
    assert not any(payload["claim_gate"].values())

    manifest = json.loads((out_dir / "manifest.sha256.json").read_text(encoding="utf-8"))
    for name, metadata in manifest["files"].items():
        actual = hashlib.sha256((out_dir / name).read_bytes()).hexdigest()
        assert actual == metadata["sha256"]


def test_review_burden_markdown_preserves_boundaries(tmp_path):
    module = load_module()
    dev = tmp_path / "development.csv"
    val = tmp_path / "validation.csv"
    write_csv(dev, day=1)
    write_csv(val, day=2, speed_offset=0.5)
    split = tmp_path / "split.json"
    split.write_text(json.dumps(split_payload(dev, val)), encoding="utf-8")

    payload = module.build_profile(
        split_json=split,
        out_dir=tmp_path / "run",
        max_interval_minutes=120,
        grid_degrees=0.05,
        caps=(2, 4),
    )
    markdown = module.render_markdown(payload)
    serialized = (json.dumps(payload) + markdown).lower()

    assert "unlabeled public ais review-burden profile" in markdown.lower()
    assert "measures_false_positive_rate: false" in markdown
    assert "proves_field_performance: false" in markdown
    assert '"ready_for_portal_upload": true' not in serialized
    assert '"ready_for_submit": true' not in serialized
    assert "field validated" not in serialized
