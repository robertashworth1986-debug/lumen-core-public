from __future__ import annotations

import importlib.util
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "code" / "ops" / "BUILD_HARBOR_AIS_PILOT_REGISTRY.py"


def load_module():
    spec = importlib.util.spec_from_file_location("harbor_ais_pilot_registry", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_offline_registry_preserves_no_download_boundary():
    module = load_module()
    registry = module.build_registry(live_probe=False, max_auto_download_mib=50.0)

    assert registry["posture"] == "PUBLIC_AIS_SOURCES_PROBED_DOWNLOAD_NOT_EXECUTED"
    assert registry["live_probe_enabled"] is False
    assert len(registry["candidates"]) == 2
    assert "does not download AIS rows" in registry["claim_boundary"]

    by_id = {candidate["id"]: candidate for candidate in registry["candidates"]}
    assert "noaa_2024_daily_csv_zip_2024_01_01" in by_id
    assert "noaa_ais_track_geoparquet_2025_02" in by_id
    for candidate in registry["candidates"]:
        assert candidate["probe"]["checked"] is False
        assert candidate["acquisition_decision"] == "UNPROBED"


def test_size_policy_blocks_large_probed_files():
    module = load_module()
    decision = module._decision(
        {
            "checked": True,
            "ok": True,
            "mib": 276.891,
        },
        max_auto_download_mib=50.0,
    )

    assert decision == "DOWNLOAD_BLOCKED_BY_SIZE_POLICY"
