from __future__ import annotations
import hashlib
import json
from pathlib import Path
from typing import Any, Dict, Iterable, List

from .settings import (
    API_REGISTRY,
    API_REGISTRY_TEMPLATE,
    CFG,
    REP,
    API_SNAPSHOT_DIR,
    utc_now,
)


def _sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def hash_text(value: Any) -> str:
    payload = json.dumps(value, sort_keys=True, default=str).encode("utf-8")
    return _sha256_bytes(payload)


def hash_file(path: Path) -> str:
    try:
        with path.open("rb") as handle:
            return _sha256_bytes(handle.read())
    except Exception:
        return ""


def write_json(path: Path, payload: Dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def build_run_proof(
    run_id: str,
    raw_paths: Iterable[Path],
    live_row_count: int,
    scored_rows: int,
    champions: int,
    watchlist: int,
    pass_count: int,
    top_artists: List[Dict[str, Any]],
    source_snapshots: Dict[str, int],
) -> Path:
    inputs = []
    for path in sorted(raw_paths):
        inputs.append({
            "path": str(path.relative_to(path.parents[2])) if path.is_absolute() else str(path),
            "sha256": hash_file(path),
        })

    active_sources = [
        {
            "name": source.get("name"),
            "display_name": source.get("display_name"),
            "active": source.get("active", False),
            "search_terms": len(source.get("search_terms", []) or []),
            "source_type": source.get("source_type"),
        }
        for source in API_REGISTRY.get("sources", [])
    ]

    proof = {
        "run_id": run_id,
        "generated_utc": utc_now(),
        "config_hash": hash_text(CFG),
        "api_registry_hash": hash_text(API_REGISTRY_TEMPLATE),
        "active_sources": active_sources,
        "raw_inputs": inputs,
        "live_row_count": live_row_count,
        "scored_rows": scored_rows,
        "champions": champions,
        "watchlist": watchlist,
        "pass": pass_count,
        "top_artists": top_artists,
        "api_snapshot_counts": source_snapshots,
    }

    proof_path = REP / CFG.get("audit", {}).get("run_proof_file", "artist_scout_run_proof.json")
    write_json(proof_path, proof)
    return proof_path


def save_api_snapshot(source_name: str, source_config: Dict[str, Any], rows: List[Dict[str, Any]]) -> Path:
    API_SNAPSHOT_DIR.mkdir(parents=True, exist_ok=True)
    snapshot_path = API_SNAPSHOT_DIR / f"{source_name}_snapshot_{utc_now().replace(':', '').replace('T','_').replace('-', '')}.json"
    payload = {
        "source": source_name,
        "endpoint": source_config.get("endpoint"),
        "search_terms": source_config.get("search_terms", []),
        "generated_utc": utc_now(),
        "row_count": len(rows),
        "rows": rows,
    }
    write_json(snapshot_path, payload)
    return snapshot_path
