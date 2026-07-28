import os
from pathlib import Path

import yaml
from dotenv import load_dotenv

from .credential_config import (
    resolve_registry_environment,
    validate_registry_auth_references,
)

load_dotenv()

ROOT = Path(__file__).resolve().parents[1]
CONFIG = ROOT / "config"
DATA = ROOT / "data"
RAW = DATA / "raw"
NORM = DATA / "normalized"
OUT = ROOT / "out"
REP = ROOT / "reports"
LOG = ROOT / "logs"

for p in [RAW, NORM, OUT, REP, LOG]:
    p.mkdir(parents=True, exist_ok=True)


def _load_yaml_object(path: Path) -> dict:
    payload = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"expected YAML object: {path.name}")
    return payload


CFG = _load_yaml_object(CONFIG / "artist_scout_config.yaml")
API_REGISTRY_TEMPLATE = _load_yaml_object(CONFIG / "api_registry.yaml")
validate_registry_auth_references(API_REGISTRY_TEMPLATE)
API_REGISTRY = resolve_registry_environment(API_REGISTRY_TEMPLATE, os.environ)
API_SNAPSHOT_DIR = ROOT / CFG.get("audit", {}).get("api_snapshot_dir", "data/raw/api_snapshots")
API_SNAPSHOT_DIR.mkdir(parents=True, exist_ok=True)


def utc_now() -> str:
    from datetime import datetime, timezone

    return datetime.now(timezone.utc).isoformat()
