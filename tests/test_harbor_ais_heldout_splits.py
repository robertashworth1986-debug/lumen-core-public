from __future__ import annotations

import importlib.util
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "code" / "ops" / "BUILD_HARBOR_AIS_HELDOUT_SPLITS.py"


def load_module():
    spec = importlib.util.spec_from_file_location("harbor_ais_heldout_splits", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_region_assignment_and_temporal_split():
    module = load_module()
    row = {"LAT": "36.9", "LON": "-76.2", "BaseDateTime": "2024-01-01T11:59:00"}

    region = module.row_region(row)

    assert region is not None
    assert region.region_id == "hampton_roads"
    assert module.split_for_time(row["BaseDateTime"]) == "development"
    assert module.split_for_time("2024-01-01T12:00:00") == "validation"


def test_stable_key_is_deterministic():
    module = load_module()
    row = {
        "MMSI": "111000111",
        "BaseDateTime": "2024-01-01T00:00:00",
        "LAT": "36.9",
        "LON": "-76.2",
    }

    assert module.stable_key(row) == module.stable_key(dict(row))
