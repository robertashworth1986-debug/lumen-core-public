from pathlib import Path
import yaml
from dotenv import load_dotenv

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

CFG = yaml.safe_load((CONFIG / "artist_scout_config.yaml").read_text(encoding="utf-8"))
API_REGISTRY = yaml.safe_load((CONFIG / "api_registry.yaml").read_text(encoding="utf-8"))
API_SNAPSHOT_DIR = ROOT / CFG.get("audit", {}).get("api_snapshot_dir", "data/raw/api_snapshots")
API_SNAPSHOT_DIR.mkdir(parents=True, exist_ok=True)


def utc_now() -> str:
    from datetime import datetime, timezone

    return datetime.now(timezone.utc).isoformat()
