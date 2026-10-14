from __future__ import annotations

import argparse
import json
import math
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
    def unique_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
        result: dict[str, Any] = {}
        for name, value in pairs:
            if name in result:
                raise ValueError("duplicate JSON member")
            result[name] = value
        return result

    if not path.exists():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"), object_pairs_hook=unique_object)
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
            return None
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
    *,
    now_dt: datetime | None = None,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    if (
        isinstance(stale_after_hours, bool)
        or not isinstance(stale_after_hours, (int, float))
        or not math.isfinite(stale_after_hours)
        or stale_after_hours <= 0
    ):
        raise ValueError("stale_after_hours must be finite and positive")
    now_dt = now_dt or datetime.now(timezone.utc)
    if not isinstance(now_dt, datetime) or now_dt.utcoffset() is None:
        raise ValueError("now_dt must include a timezone")

    registry_rows_by_source: dict[str, dict[str, Any]] = {}
    if not isinstance(registry, dict) or not isinstance(live_sources, dict):
        raise ValueError("registry and live_sources must be JSON objects")
    if sum(name in registry for name in ("rows", "sources")) != 1:
        raise ValueError("registry must contain exactly one rows or sources list")
    registry_rows = registry.get("rows", registry.get("sources"))
    if not isinstance(registry_rows, list):
        raise ValueError("registry rows must be a list")
    for row in registry_rows:
        if not isinstance(row, dict):
            raise ValueError("registry row must be an object")
        name = row.get("source")
        if not isinstance(name, str) or not name.strip():
            raise ValueError("registry source is missing")
        src = name.strip().upper()
        if src in registry_rows_by_source:
            raise ValueError("duplicate registry source")
        registry_rows_by_source[src] = row

    # Current config wraps providers; accept the older direct mapping and sources wrapper.
    if "providers" in live_sources and "sources" in live_sources:
        raise ValueError("live_sources must not contain conflicting source wrappers")
    config_rows = live_sources.get("providers", live_sources.get("sources", live_sources))
    if not isinstance(config_rows, dict):
        raise ValueError("configured sources must be a mapping")
    configs: dict[str, dict[str, Any]] = {}
    for name, config in config_rows.items():
        if name == "generated_utc" and config_rows is live_sources:
            continue
        if not isinstance(name, str) or not name.strip() or not isinstance(config, dict):
            raise ValueError("configured source must be a named object")
        source = name.strip().upper()
        if source in configs:
            raise ValueError("duplicate configured source")
        configs[source] = config
    source_keys: set[str] = set(registry_rows_by_source.keys())
    source_keys.update(configs)

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
        live_cfg = configs.get(src, {})

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
            env_names.extend(e.strip() for e in env_from_registry.split(",") if e.strip())
        env_names = sorted(set(env_names))

        env_present = [
            e for e in env_names if key_status.get(e, "") in {"present", "live_key_present"}
        ]
        has_all_keys = len(env_present) == len(env_names) if env_names else None

        enabled = live_cfg.get("enabled") is True
        if enabled:
            enabled_count += 1

        status = str(registry_row.get("status") or "UNKNOWN").upper()
        measurement_mode = str(live_cfg.get("measurement_mode") or "registry_only")
        last_probe_utc = str(registry_row.get("last_probe_utc") or "")
        last_probe_dt = parse_iso_utc(last_probe_utc)
        # Only a result and timestamp in the same registry record establish probe health.
        # Archived config flags, key presence and measured-file matches are not probes.
        probe_ok = registry_row.get("probe_ok") is True
        last_probe_age_hours = None
        if last_probe_dt is not None:
            last_probe_age_hours = (now_dt - last_probe_dt).total_seconds() / 3600.0

        stale_probe = last_probe_age_hours is None or not 0 <= last_probe_age_hours <= stale_after_hours
        blockers = []
        if not probe_ok:
            blockers.append("probe_not_successful")
        if last_probe_age_hours is None:
            blockers.append("probe_timestamp_missing_or_invalid")
        elif last_probe_age_hours < 0:
            blockers.append("probe_timestamp_in_future")
        elif stale_probe:
            blockers.append("probe_stale")
        if not enabled:
            blockers.append("source_not_enabled")

        if has_all_keys is False:
            missing_key_count += 1
        if stale_probe:
            stale_probe_count += 1

        if enabled and probe_ok and not stale_probe:
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
                "probe_ok": probe_ok,
                "last_probe_utc": last_probe_utc or None,
                "last_probe_age_hours": last_probe_age_hours,
                "stale_probe": stale_probe,
                "blockers": blockers,
                "dataset_review_readiness": "NOT_EVALUATED",
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
    lines.append("ACTIVE means an enabled source has an explicit successful, fresh probe in the supplied registry. It does not establish a usable dataset, measured improvement or savings. This report makes no network calls.")
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
    parser.add_argument("--registry", type=Path, default=REGISTRY_PATH)
    parser.add_argument("--live-sources", type=Path, default=LIVE_SOURCES_PATH)
    parser.add_argument("--key-status", type=Path, default=KEY_STATUS_PATH)
    parser.add_argument("--output-dir", type=Path, default=OPS_ROOT)
    parser.add_argument("--generated-at", help="Timezone-qualified evaluation time; defaults to now.")
    args = parser.parse_args()

    now_dt = parse_iso_utc(args.generated_at) if args.generated_at else datetime.now(timezone.utc)
    if now_dt is None:
        parser.error("--generated-at must be a timezone-qualified ISO timestamp")
    generated_utc = now_dt.isoformat()
    stamp = now_dt.strftime("%Y%m%dT%H%M%SZ")

    registry = read_json(args.registry)
    live_sources = read_json(args.live_sources)
    key_status = parse_key_status(args.key_status)
    if not isinstance(registry, dict) or not isinstance(live_sources, dict):
        parser.error("registry and live-source config must be readable JSON objects")

    try:
        rows, summary = build_agent_rows(
            registry,
            live_sources,
            key_status,
            stale_after_hours=args.stale_after_hours,
            now_dt=now_dt,
        )
    except ValueError as exc:
        parser.error(str(exc))

    payload = {
        "generated_utc": generated_utc,
        "scope": "api_source_agent_monitor",
        "claim_boundary": "Registry probe observations only; dataset readiness, deltas and savings are not evaluated. No network probe is performed by this report.",
        "parameters": {
            "stale_after_hours": float(args.stale_after_hours),
        },
        "inputs": {
            "registry_path": str(args.registry),
            "live_sources_path": str(args.live_sources),
            "key_status_path": str(args.key_status),
        },
        "summary": summary,
        "agents": rows,
    }

    args.output_dir.mkdir(parents=True, exist_ok=True)
    out_json = args.output_dir / f"api_source_agent_monitor_{stamp}.json"
    out_md = args.output_dir / f"api_source_agent_monitor_{stamp}.md"
    latest_json = args.output_dir / "api_source_agent_monitor_latest.json"
    latest_md = args.output_dir / "api_source_agent_monitor_latest.md"

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
