from __future__ import annotations

import argparse
import json
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


STACK_ROOT = Path(__file__).resolve().parents[2]
OPS_ROOT = STACK_ROOT / "out" / "ops"

REGISTRY_PATH = STACK_ROOT / "config" / "live_source_registry.json"
LIVE_SOURCES_PATH = STACK_ROOT / "config" / "live_sources.json"
KEY_STATUS_PATH = STACK_ROOT / "dashboard" / "api_key_status.txt"


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def utc_stamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def read_json(path: Path) -> Any:
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def parse_key_status(path: Path) -> dict[str, str]:
    out: dict[str, str] = {}
    if not path.exists():
        return out

    for raw in path.read_text(encoding="utf-8", errors="ignore").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or ":" not in line:
            continue
        key, status = line.split(":", 1)
        out[key.strip().upper()] = status.strip().lower()
    return out


def parse_iso_utc(value: Any) -> datetime | None:
    if not value:
        return None
    s = str(value).strip()
    if not s:
        return None
    try:
        dt = datetime.fromisoformat(s)
        if dt.tzinfo is None:
            return dt.replace(tzinfo=timezone.utc)
        return dt.astimezone(timezone.utc)
    except Exception:
        return None


def infer_lane(sector: str) -> str:
    s = (sector or "").lower()
    if "crypto" in s or "broker" in s or "market" in s or "rates" in s:
        return "Trading"
    if "energy" in s or "weather" in s or "water" in s or "air" in s:
        return "Infra-Energy"
    if "federal" in s or "gov" in s:
        return "Gov"
    if "sports" in s:
        return "Sports"
    if "internal" in s:
        return "Internal"
    return "Unclassified"


def build_agent_rows(
    registry: dict[str, Any],
    live_sources: dict[str, Any],
    key_status: dict[str, str],
    stale_after_hours: float,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    now_dt = datetime.now(timezone.utc)

    registry_rows_by_source: dict[str, dict[str, Any]] = {}
    for row in registry.get("sources", []) if isinstance(registry, dict) else []:
        if not isinstance(row, dict):
            continue
        src = str(row.get("source") or "").strip().upper()
        if not src:
            continue
        # Keep latest row for each source.
        registry_rows_by_source[src] = row

    source_keys: set[str] = set(registry_rows_by_source.keys())
    if isinstance(live_sources, dict):
        source_keys.update(str(k).strip().upper() for k in live_sources.keys())

    rows: list[dict[str, Any]] = []
    lane_counts: Counter[str] = Counter()
    sector_counts: Counter[str] = Counter()
    enabled_count = 0
    active_count = 0
    degraded_count = 0
    missing_key_count = 0
    stale_probe_count = 0

    for src in sorted(s for s in source_keys if s):
        registry_row = registry_rows_by_source.get(src, {})
        live_cfg = live_sources.get(src.lower(), {}) if isinstance(live_sources, dict) else {}

        sector = str(
            registry_row.get("sector")
            or live_cfg.get("sector")
            or "unclassified"
        )
        lane = infer_lane(sector)

        env_names = []
        if isinstance(live_cfg.get("env_names"), list):
            env_names = [str(x).strip().upper() for x in live_cfg.get("env_names") if str(x).strip()]
        env_from_registry = str(registry_row.get("env") or "").strip().upper()
        if env_from_registry:
            env_names.append(env_from_registry)
        env_names = sorted(set(env_names))

        env_present = [
            e for e in env_names if key_status.get(e, "") in {"present", "live_key_present"}
        ]
        has_all_keys = bool(env_names) and len(env_present) == len(env_names)
        if not env_names:
            # If no env names are known, rely on registry status.
            has_all_keys = str(registry_row.get("status") or "").upper() == "LIVE_KEY_PRESENT"

        enabled = bool(live_cfg.get("enabled", False))
        if enabled:
            enabled_count += 1

        status = str(registry_row.get("status") or "UNKNOWN").upper()
        measurement_mode = str(live_cfg.get("measurement_mode") or "registry_only")
        last_probe_utc = str(registry_row.get("last_probe_utc") or "")
        last_probe_dt = parse_iso_utc(last_probe_utc)
        last_probe_age_hours = None
        if last_probe_dt is not None:
            last_probe_age_hours = round((now_dt - last_probe_dt).total_seconds() / 3600.0, 3)

        stale_probe = False
        if last_probe_age_hours is not None:
            stale_probe = last_probe_age_hours > stale_after_hours

        if not has_all_keys:
            missing_key_count += 1
        if stale_probe:
            stale_probe_count += 1

        if enabled and has_all_keys and status in {"LIVE_KEY_PRESENT", "READY", "ACTIVE"} and not stale_probe:
            agent_state = "ACTIVE"
            active_count += 1
        elif enabled:
            agent_state = "DEGRADED"
            degraded_count += 1
        else:
            agent_state = "DISABLED"

        lane_counts[lane] += 1
        sector_counts[sector] += 1

        rows.append(
            {
                "agent_id": f"agent_{src.lower()}",
                "source": src,
                "lane": lane,
                "sector": sector,
                "enabled": enabled,
                "agent_state": agent_state,
                "registry_status": status,
                "measurement_mode": measurement_mode,
                "env_names": env_names,
                "env_present": env_present,
                "keys_complete": has_all_keys,
                "last_probe_utc": last_probe_utc or None,
                "last_probe_age_hours": last_probe_age_hours,
                "stale_probe": stale_probe,
            }
        )

    summary = {
        "total_agents": len(rows),
        "enabled_agents": enabled_count,
        "active_agents": active_count,
        "degraded_agents": degraded_count,
        "missing_key_agents": missing_key_count,
        "stale_probe_agents": stale_probe_count,
        "lane_counts": dict(sorted(lane_counts.items())),
        "sector_counts": dict(sorted(sector_counts.items())),
    }
    return rows, summary


def build_markdown(
    generated_utc: str,
    stale_after_hours: float,
    summary: dict[str, Any],
    rows: list[dict[str, Any]],
    json_path: Path,
) -> str:
    lines: list[str] = []
    lines.append("# API Source Agent Monitor")
    lines.append("")
    lines.append(f"Generated UTC: {generated_utc}")
    lines.append(f"Stale threshold (hours): {stale_after_hours}")
    lines.append(f"JSON output: {json_path.as_posix()}")
    lines.append("")
    lines.append("## Summary")
    lines.append(f"- Total agents: {summary.get('total_agents', 0)}")
    lines.append(f"- Enabled agents: {summary.get('enabled_agents', 0)}")
    lines.append(f"- Active agents: {summary.get('active_agents', 0)}")
    lines.append(f"- Degraded agents: {summary.get('degraded_agents', 0)}")
    lines.append(f"- Missing-key agents: {summary.get('missing_key_agents', 0)}")
    lines.append(f"- Stale-probe agents: {summary.get('stale_probe_agents', 0)}")
    lines.append("")
    lines.append("## Lane Counts")
    for lane, count in sorted((summary.get("lane_counts") or {}).items()):
        lines.append(f"- {lane}: {count}")
    lines.append("")
    lines.append("## Agents")
    lines.append("| Agent | Source | Lane | Enabled | State | Keys Complete | Probe Age (h) |")
    lines.append("|---|---|---|---|---|---|---:|")
    for row in rows:
        age = row.get("last_probe_age_hours")
        age_text = f"{age:.3f}" if isinstance(age, (int, float)) else ""
        lines.append(
            "| {agent_id} | {source} | {lane} | {enabled} | {agent_state} | {keys_complete} | {age} |".format(
                agent_id=row.get("agent_id", ""),
                source=row.get("source", ""),
                lane=row.get("lane", ""),
                enabled=row.get("enabled", False),
                agent_state=row.get("agent_state", ""),
                keys_complete=row.get("keys_complete", False),
                age=age_text,
            )
        )
    return "\n".join(lines) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description="Build API source agent monitor from live source registry and key status.")
    parser.add_argument("--stale-after-hours", type=float, default=24.0)
    args = parser.parse_args()

    generated_utc = utc_now()
    stamp = utc_stamp()

    registry = read_json(REGISTRY_PATH)
    live_sources = read_json(LIVE_SOURCES_PATH)
    key_status = parse_key_status(KEY_STATUS_PATH)

    rows, summary = build_agent_rows(
        registry if isinstance(registry, dict) else {},
        live_sources if isinstance(live_sources, dict) else {},
        key_status,
        stale_after_hours=float(args.stale_after_hours),
    )

    payload = {
        "generated_utc": generated_utc,
        "scope": "api_source_agent_monitor",
        "parameters": {
            "stale_after_hours": float(args.stale_after_hours),
        },
        "inputs": {
            "registry_path": str(REGISTRY_PATH),
            "live_sources_path": str(LIVE_SOURCES_PATH),
            "key_status_path": str(KEY_STATUS_PATH),
        },
        "summary": summary,
        "agents": rows,
    }

    OPS_ROOT.mkdir(parents=True, exist_ok=True)
    out_json = OPS_ROOT / f"api_source_agent_monitor_{stamp}.json"
    out_md = OPS_ROOT / f"api_source_agent_monitor_{stamp}.md"
    latest_json = OPS_ROOT / "api_source_agent_monitor_latest.json"
    latest_md = OPS_ROOT / "api_source_agent_monitor_latest.md"

    write_json(out_json, payload)
    latest_json.write_text(out_json.read_text(encoding="utf-8"), encoding="utf-8")

    md = build_markdown(
        generated_utc=generated_utc,
        stale_after_hours=float(args.stale_after_hours),
        summary=summary,
        rows=rows,
        json_path=out_json,
    )
    out_md.write_text(md, encoding="utf-8")
    latest_md.write_text(md, encoding="utf-8")

    print(f"API_MONITOR_JSON={out_json}")
    print(f"API_MONITOR_MD={out_md}")
    print(
        "API_MONITOR_SUMMARY "
        f"TOTAL={summary.get('total_agents', 0)} "
        f"ACTIVE={summary.get('active_agents', 0)} "
        f"DEGRADED={summary.get('degraded_agents', 0)} "
        f"MISSING_KEYS={summary.get('missing_key_agents', 0)} "
        f"STALE={summary.get('stale_probe_agents', 0)}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
