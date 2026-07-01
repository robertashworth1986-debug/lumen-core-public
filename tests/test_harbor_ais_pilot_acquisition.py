from __future__ import annotations

import importlib.util
import zipfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "code" / "ops" / "ACQUIRE_HARBOR_AIS_PILOT_DATA.py"


def load_module():
    spec = importlib.util.spec_from_file_location("harbor_ais_pilot_acquisition", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_layout_keeps_raw_data_outside_repo(tmp_path):
    module = load_module()
    paths = module.layout(tmp_path / "HarborSentinel")

    assert paths["raw_noaa_ais"].as_posix().endswith("HarborSentinel/raw/noaa_ais")
    assert paths["working_noaa_ais"].as_posix().endswith("HarborSentinel/working/noaa_ais")
    assert paths["manifests"].as_posix().endswith("HarborSentinel/manifests")


def test_zip_csv_profile_records_schema_without_raw_rows(tmp_path):
    module = load_module()
    sample_zip = tmp_path / "AIS_sample.zip"
    csv_text = "\n".join(
        [
            "MMSI,BaseDateTime,LAT,LON,SOG",
            "111000111,2024-01-01T00:00:00,29.1,-90.2,4.5",
            "222000222,2024-01-01T00:01:00,29.2,-90.1,6.5",
            "111000111,2024-01-01T00:02:00,29.4,-90.0,5.0",
        ]
    )
    with zipfile.ZipFile(sample_zip, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("AIS_sample.csv", csv_text)

    profile = module.profile_zip_csv(sample_zip, sample_rows=10)

    assert profile["profile_status"] == "sampled"
    assert profile["columns"] == ["MMSI", "BaseDateTime", "LAT", "LON", "SOG"]
    assert profile["sample_rows"] == 3
    assert profile["unique_mmsi_in_sample"] == 2
    assert profile["lat_min_in_sample"] == 29.1
    assert profile["lat_max_in_sample"] == 29.4
    assert "raw_rows" not in profile
