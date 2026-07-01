from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
CONFIG = ROOT / "config"
OUT_OPS = ROOT / "out" / "ops"
DOCS = ROOT / "docs"
DASHBOARD_DATA = ROOT / "dashboard" / "data"

ENV_FILES = [
    CONFIG / "luma_live_keys.env",
    ROOT / ".env.live",
    ROOT / ".env.sports",
]
REGISTRY_JSON = CONFIG / "live_source_registry.json"
LIVE_SOURCES_JSON = CONFIG / "live_sources.json"
MAXIMIZER_JSON = OUT_OPS / "live_source_measurement_maximizer_latest.json"

OUT_JSON = OUT_OPS / "safe_key_provider_ping_latest.json"
DASHBOARD_JSON = DASHBOARD_DATA / "safe_key_provider_ping.json"
OUT_MD = DOCS / f"SAFE_KEY_PROVIDER_PING_{datetime.now(timezone.utc).strftime('%Y-%m-%d')}.md"


def now_utc() -> str:
    return datetime.now(timezone.utc).isoformat()


def read_json(path: Path) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text.rstrip("\r\n") + "\n", encoding="utf-8")


def sha256_prefix(value: str, chars: int = 12) -> str:
    if not value:
        return ""
    return hashlib.sha256(value.encode("utf-8")).hexdigest().upper()[:chars]


def file_hash_prefix(path: Path, chars: int = 16) -> str:
    h = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest().upper()[:chars]


def looks_real(value: str | None) -> bool:
    text = str(value or "").strip().strip('"').strip("'")
    if len(text) < 8:
        return False
    bad = ("your_", "replace", "example", "changeme", "paste_here", "none", "null")
    return not any(marker in text.lower() for marker in bad)


def load_env_file(path: Path) -> dict[str, str]:
    env: dict[str, str] = {}
    if not path.exists():
        return env
    for raw in path.read_text(encoding="utf-8", errors="ignore").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        if key:
            env[key] = value
    return env


def hydrate_env() -> dict[str, str]:
    loaded: dict[str, str] = {}
    for path in ENV_FILES:
        loaded.update(load_env_file(path))
    for key, value in loaded.items():
        if value and not os.environ.get(key):
            os.environ[key] = value
    return loaded


def env_inventory(loaded: dict[str, str]) -> list[dict[str, Any]]:
    names = sorted(
        name
        for name in set(loaded) | set(os.environ)
        if re.search(r"(?i)(api|key|secret|token|webhook)", name)
    )
    rows: list[dict[str, Any]] = []
    for name in names:
        value = os.environ.get(name, loaded.get(name, ""))
        rows.append(
            {
                "name": name,
                "present": looks_real(value),
                "length": len(value or ""),
                "sha256_prefix": sha256_prefix(value or ""),
            }
        )
    return rows


def registry_provider_rows() -> list[dict[str, Any]]:
    payload = read_json(REGISTRY_JSON)
    if isinstance(payload, dict):
        providers = payload.get("rows") or payload.get("providers") or payload.get("sources") or []
    elif isinstance(payload, list):
        providers = payload
    else:
        providers = []

    if isinstance(providers, dict):
        providers = [
            {"source": source, **value}
            for source, value in providers.items()
            if isinstance(value, dict)
        ]

    if not providers:
        fallback = read_json(LIVE_SOURCES_JSON)
        if isinstance(fallback, dict):
            fallback_providers = fallback.get("providers") or fallback.get("sources") or {}
            if isinstance(fallback_providers, dict):
                providers = [
                    {"source": source, **value}
                    for source, value in fallback_providers.items()
                    if isinstance(value, dict)
                ]
            elif isinstance(fallback_providers, list):
                providers = fallback_providers

    rows: list[dict[str, Any]] = []
    for item in providers:
        if not isinstance(item, dict):
            continue
        env_names = item.get("env_names") or item.get("env") or item.get("required_env") or []
        if isinstance(env_names, str):
            env_names = [env_names]
        present = [name for name in env_names if looks_real(os.environ.get(str(name), ""))]
        rows.append(
            {
                "source": item.get("source") or item.get("name") or item.get("id"),
                "sector": item.get("sector"),
                "enabled": bool(item.get("enabled", True)),
                "env_names": env_names,
                "present_env_names": present,
                "key_ready": bool(present) or not env_names,
                "missing_env_names": [name for name in env_names if name not in present],
            }
        )
    return rows


def latest_provider_status() -> dict[str, dict[str, Any]]:
    payload = read_json(MAXIMIZER_JSON)
    rows = payload.get("provider_rows", []) if isinstance(payload, dict) else []
    out: dict[str, dict[str, Any]] = {}
    for row in rows:
        if isinstance(row, dict) and row.get("source"):
            out[str(row["source"])] = {
                "status": row.get("status"),
                "rows": row.get("rows", 0),
                "probe_ok": row.get("probe_ok"),
                "http_status": row.get("http_status"),
                "probe_note": row.get("probe_note"),
                "snapshot_sha256": row.get("snapshot_sha256"),
            }
    return out


def extra_file_summary(path_text: str | None) -> dict[str, Any] | None:
    if not path_text:
        return None
    path = Path(path_text)
    result: dict[str, Any] = {
        "path": str(path),
        "exists": path.exists(),
        "bytes": 0,
        "line_count": 0,
        "sha256_prefix": None,
        "labeled_fields": [],
        "unlabeled_secret_like_lines": 0,
    }
    if not path.exists():
        return result
    raw = path.read_text(encoding="utf-8", errors="ignore")
    result["bytes"] = len(raw.encode("utf-8"))
    result["line_count"] = len([line for line in raw.splitlines() if line.strip()])
    result["sha256_prefix"] = file_hash_prefix(path)
    labels: list[str] = []
    unlabeled = 0
    for line in raw.splitlines():
        text = line.strip()
        if not text:
            continue
        match = re.match(r"^([A-Za-z0-9_ ./-]{2,80})\s*[:=]", text)
        if match:
            labels.append(match.group(1).strip())
        elif len(text) >= 20 and re.match(r"^[A-Za-z0-9+/=_\-.]+$", text):
            unlabeled += 1
    result["labeled_fields"] = sorted(set(labels))
    result["unlabeled_secret_like_lines"] = unlabeled
    return result


def render_markdown(payload: dict[str, Any]) -> str:
    summary = payload["summary"]
    lines = [
        "# Safe Key Provider Ping",
        "",
        f"- Generated UTC: `{payload['generated_utc']}`",
        f"- Key-like env names detected: `{summary['key_like_env_count']}`",
        f"- Registry providers checked: `{summary['provider_count']}`",
        f"- Key-ready providers: `{summary['key_ready_provider_count']}`",
        f"- Latest measured providers: `{summary['latest_measured_provider_count']}`",
        f"- Latest blocked/thin providers: `{summary['latest_blocked_or_thin_provider_count']}`",
        "",
        "No plaintext secrets are written to this artifact. Hash prefixes are for continuity only.",
        "",
        "## Immediate Key/Provider Gaps",
    ]
    for row in payload["provider_rows"]:
        latest = row.get("latest_status") or {}
        status = latest.get("status")
        if row.get("key_ready") and status in {"MEASURED", "READY", "OK"}:
            continue
        missing = ", ".join(row.get("missing_env_names") or []) or "none"
        lines.append(
            f"- `{row.get('source')}`: key_ready `{str(row.get('key_ready')).lower()}`, "
            f"latest `{status or 'unknown'}`, rows `{latest.get('rows', 0)}`, missing `{missing}`"
        )
    if lines[-1] == "## Immediate Key/Provider Gaps":
        lines.append("- No immediate key/provider gaps detected in the current registry snapshot.")
    lines.extend(
        [
            "",
            "## Claim Boundary",
            "",
            "This is a credential/readiness and latest-measurement inventory. It does not prove field validation, realized savings, trading profit, or award value.",
        ]
    )
    return "\n".join(lines)


def build_payload(extra_key_file: str | None) -> dict[str, Any]:
    loaded = hydrate_env()
    env_rows = env_inventory(loaded)
    latest = latest_provider_status()
    provider_rows = registry_provider_rows()
    for row in provider_rows:
        row["latest_status"] = latest.get(str(row.get("source")), {})

    latest_measured = [
        row
        for row in provider_rows
        if str((row.get("latest_status") or {}).get("status", "")).upper() == "MEASURED"
    ]
    latest_blocked = [
        row
        for row in provider_rows
        if (row.get("latest_status") or {}).get("status")
        and str((row.get("latest_status") or {}).get("status", "")).upper() != "MEASURED"
    ]

    payload = {
        "generated_utc": now_utc(),
        "schema": "safe_key_provider_ping.v1",
        "summary": {
            "key_like_env_count": len(env_rows),
            "provider_count": len(provider_rows),
            "key_ready_provider_count": len([row for row in provider_rows if row.get("key_ready")]),
            "latest_measured_provider_count": len(latest_measured),
            "latest_blocked_or_thin_provider_count": len(latest_blocked),
        },
        "env_rows": env_rows,
        "provider_rows": provider_rows,
        "extra_key_file_summary": extra_file_summary(extra_key_file),
        "claim_boundary": "No plaintext secrets. No live orders. No submissions. No field/financial claims.",
    }
    return payload


def main() -> int:
    parser = argparse.ArgumentParser(description="Build a masked key/provider readiness ping artifact.")
    parser.add_argument("--extra-key-file", default="", help="Optional local key file to summarize without printing values.")
    args = parser.parse_args()

    payload = build_payload(args.extra_key_file or None)
    write_json(OUT_JSON, payload)
    write_json(DASHBOARD_JSON, payload)
    write_text(OUT_MD, render_markdown(payload))
    print(f"wrote {OUT_JSON}")
    print(f"wrote {DASHBOARD_JSON}")
    print(f"wrote {OUT_MD}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
