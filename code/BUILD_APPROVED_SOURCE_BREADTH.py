from __future__ import annotations

import json
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(r"C:\LumaTrader\INSTITUTIONAL_STACK_V2")
CONF = ROOT / "config"
OUT = ROOT / "out"
EXEC = OUT / "execution"

KEY_REGISTRY = CONF / "live_source_registry.json"
OPEN_ACCESS_CATALOG = CONF / "approved_open_access_sources.json"

BREADTH_JSON = OUT / "approved_source_breadth_registry.json"
BREADTH_MD = OUT / "approved_source_breadth_registry.md"
EXEC_BREADTH_JSON = EXEC / "approved_source_breadth_registry.json"


def now_utc() -> str:
    return datetime.now(timezone.utc).isoformat()


def load_json(path: Path, default: Any) -> Any:
    try:
        if path.exists():
            return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        pass
    return default


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    EXEC.mkdir(parents=True, exist_ok=True)

    key_registry = load_json(KEY_REGISTRY, {})
    catalog = load_json(OPEN_ACCESS_CATALOG, {})

    key_rows = []
    if isinstance(key_registry, dict):
        raw = key_registry.get("rows", key_registry.get("sources", []))
        if isinstance(raw, list):
            key_rows = [r for r in raw if isinstance(r, dict)]

    open_rows = []
    if isinstance(catalog, dict):
        raw = catalog.get("sources", [])
        if isinstance(raw, list):
            open_rows = [r for r in raw if isinstance(r, dict) and str(r.get("approval", "")).lower() == "approved"]

    enabled_key_rows = [r for r in key_rows if bool(r.get("enabled", False))]

    by_sector = defaultdict(lambda: {"key_backed": 0, "open_access": 0})
    for row in enabled_key_rows:
        sector = str(row.get("sector", "unknown")).strip() or "unknown"
        by_sector[sector]["key_backed"] += 1
    for row in open_rows:
        sector = str(row.get("sector", "unknown")).strip() or "unknown"
        by_sector[sector]["open_access"] += 1

    sector_rows = []
    for sector, counts in sorted(by_sector.items(), key=lambda item: (item[0])):
        key_count = int(counts.get("key_backed", 0))
        open_count = int(counts.get("open_access", 0))
        sector_rows.append(
            {
                "sector": sector,
                "key_backed_sources": key_count,
                "open_access_sources": open_count,
                "combined_sources": key_count + open_count,
            }
        )

    payload = {
        "generated_utc": now_utc(),
        "key_backed_enabled_sources": len(enabled_key_rows),
        "open_access_approved_sources": len(open_rows),
        "combined_approved_sources": len(enabled_key_rows) + len(open_rows),
        "sector_count": len(sector_rows),
        "sectors": sector_rows,
    }

    BREADTH_JSON.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    EXEC_BREADTH_JSON.write_text(json.dumps(payload, indent=2), encoding="utf-8")

    lines = [
        "# Approved Source Breadth Registry",
        "",
        f"Generated UTC: {payload['generated_utc']}",
        f"- Key-backed enabled sources: {payload['key_backed_enabled_sources']}",
        f"- Open-access approved sources: {payload['open_access_approved_sources']}",
        f"- Combined approved sources: {payload['combined_approved_sources']}",
        f"- Sector count: {payload['sector_count']}",
        "",
        "## Sector Coverage",
    ]
    for row in sector_rows:
        lines.append(
            f"- {row['sector']}: key_backed={row['key_backed_sources']}, open_access={row['open_access_sources']}, combined={row['combined_sources']}"
        )
    BREADTH_MD.write_text("\n".join(lines) + "\n", encoding="utf-8")

    print("APPROVED SOURCE BREADTH WRITTEN")
    print(BREADTH_JSON)
    print(EXEC_BREADTH_JSON)
    print(BREADTH_MD)
    print(f"Combined approved sources: {payload['combined_approved_sources']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
