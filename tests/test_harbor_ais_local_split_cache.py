from __future__ import annotations

import hashlib
import importlib.util
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "code" / "ops" / "BUILD_HARBOR_AIS_LOCAL_SPLIT_CACHE.py"


def load_module():
    spec = importlib.util.spec_from_file_location("harbor_ais_local_split_cache", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def write_csv(path: Path, text: str) -> dict[str, object]:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    data = path.read_bytes()
    return {"path": str(path), "bytes": len(data), "sha256": hashlib.sha256(data).hexdigest(), "rows": 1}


def test_local_split_cache_writes_hash_matched_cached_manifest(tmp_path):
    module = load_module()
    dev = write_csv(tmp_path / "source" / "development.csv", "MMSI,BaseDateTime,LAT,LON\n1,2024-01-01T00:00:00,1,1\n")
    val = write_csv(tmp_path / "source" / "validation.csv", "MMSI,BaseDateTime,LAT,LON\n2,2024-01-01T12:00:00,2,2\n")
    split_json = tmp_path / "split.json"
    split_json.write_text(
        json.dumps(
            {
                "schema": "harbor_ais_heldout_splits_v1",
                "selected_region": {"region_id": "unit", "label": "Unit Harbor"},
                "splits": {"development": dev, "validation": val},
            }
        ),
        encoding="utf-8",
    )

    payload = module.build_cache(
        split_json,
        cache_root=tmp_path / "cache",
        timeout_seconds=2,
        use_subprocess=False,
        write_outputs=False,
    )
    cached_manifest = module.cached_split_manifest(json.loads(split_json.read_text()), payload["entries"])

    assert payload["schema"] == "harbor_ais_local_split_cache_v1"
    assert payload["posture"] == "PUBLIC_AIS_LOCAL_SPLIT_CACHE_READY"
    assert payload["summary"]["required_ok"] == 2
    assert all(row["sha256_matches"] is True for row in payload["entries"])
    assert cached_manifest["splits"]["development"]["path"] != dev["path"]
    assert Path(cached_manifest["splits"]["development"]["path"]).exists()
    assert "does not establish HarborSentinel detection performance" in payload["claim_boundary"]


def test_local_split_cache_blocks_missing_validation_source(tmp_path):
    module = load_module()
    dev = write_csv(tmp_path / "source" / "development.csv", "MMSI,BaseDateTime,LAT,LON\n1,2024-01-01T00:00:00,1,1\n")
    split_json = tmp_path / "split.json"
    split_json.write_text(
        json.dumps(
            {
                "schema": "harbor_ais_heldout_splits_v1",
                "selected_region": {"region_id": "unit", "label": "Unit Harbor"},
                "splits": {
                    "development": dev,
                    "validation": {
                        "path": str(tmp_path / "source" / "missing_validation.csv"),
                        "bytes": 10,
                        "sha256": "0" * 64,
                        "rows": 1,
                    },
                },
            }
        ),
        encoding="utf-8",
    )

    payload = module.build_cache(
        split_json,
        cache_root=tmp_path / "cache",
        timeout_seconds=2,
        use_subprocess=False,
        write_outputs=False,
    )

    assert payload["posture"] == "PUBLIC_AIS_LOCAL_SPLIT_CACHE_BLOCKED"
    assert payload["summary"]["required_ok"] == 1
    validation = next(row for row in payload["entries"] if row["label"] == "validation")
    assert validation["status"] == "source_missing"
    assert validation["ok"] is False
