from __future__ import annotations

import hashlib
import importlib.util
import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import yaml
from dotenv import dotenv_values


ROOT = Path(__file__).resolve().parents[2]
SPRINT_DIR = ROOT / "grant_submissions" / "funding_sprint_20260709"
OUT_OPS = ROOT / "out" / "ops"
DASHBOARD_DATA = ROOT / "dashboard" / "data"

API_REGISTRY_SCRIPT = ROOT / "code" / "execution" / "api_key_purpose_registry.py"
API_REGISTRY_REPORT = ROOT / "out" / "execution" / "api_key_registry_report.json"
LAMASCOUT_REGISTRY = ROOT / "LamaScout" / "config" / "api_registry.yaml"

OUT_JSON = OUT_OPS / "key_governance_firewall_latest.json"
DASHBOARD_JSON = DASHBOARD_DATA / "key_governance_firewall.json"
OUT_MD = SPRINT_DIR / "KEY_GOVERNANCE_FIREWALL_2026-07-09.md"

ENV_CANDIDATES = [
    ROOT / "config" / "luma_live_keys.env",
    ROOT / "config" / "luma_outreach_keys.env",
    ROOT / ".env",
    ROOT / "LamaScout" / ".env",
]

SECRET_MARKERS = [
    "password",
    "client_secret",
    "api_key:",
    "access_token:",
    "bearer_token:",
    "refresh_token",
    "private key",
    "sk-",
    "xox",
]

LITERAL_SECRET_KEYS = {
    "api_key",
    "client_secret",
    "access_token",
    "bearer_token",
    "refresh_token",
    "private_key",
}

WRITE_OR_SPEND_ACTIONS = {
    "post",
    "upload",
    "comment",
    "message",
    "dm",
    "ad",
    "ad_spend",
    "page_edit",
    "follow",
    "trade",
    "withdraw",
    "order",
}


def now_utc() -> str:
    return datetime.now(timezone.utc).isoformat()


def rel(path: Path) -> str:
    try:
        return path.relative_to(ROOT).as_posix()
    except ValueError:
        return str(path)


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def ensure_api_registry_report() -> None:
    if API_REGISTRY_REPORT.exists():
        return
    spec = importlib.util.spec_from_file_location("api_key_purpose_registry", API_REGISTRY_SCRIPT)
    module = importlib.util.module_from_spec(spec)
    if spec.loader is None:
        raise RuntimeError(f"Cannot load {API_REGISTRY_SCRIPT}")
    spec.loader.exec_module(module)
    payload = module.build_report()
    API_REGISTRY_REPORT.parent.mkdir(parents=True, exist_ok=True)
    API_REGISTRY_REPORT.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


def sha256_text(value: Any) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, default=str).encode("utf-8")).hexdigest()


def load_env_key_names() -> set[str]:
    names: set[str] = set()
    for path in ENV_CANDIDATES:
        if not path.exists():
            continue
        values = dotenv_values(path)
        for key, value in values.items():
            if key and value:
                names.add(str(key))
    for key, value in os.environ.items():
        if value:
            names.add(str(key))
    return names


def has_env(names: set[str], candidates: list[str]) -> bool:
    return any(name in names for name in candidates if name)


def registry_inline_secret_hits(source: Any, prefix: str = "") -> list[str]:
    hits: list[str] = []
    if isinstance(source, dict):
        for key, value in source.items():
            next_prefix = f"{prefix}.{key}" if prefix else str(key)
            if key in LITERAL_SECRET_KEYS and isinstance(value, str) and value.strip():
                if not value.strip().startswith("YOUR_") and not value.strip().endswith("_ENV"):
                    hits.append(next_prefix)
            hits.extend(registry_inline_secret_hits(value, next_prefix))
    elif isinstance(source, list):
        for idx, item in enumerate(source):
            hits.extend(registry_inline_secret_hits(item, f"{prefix}[{idx}]"))
    return hits


def auth_env_candidates(auth: dict[str, Any]) -> list[str]:
    names: list[str] = []
    for key in ("api_key_env", "client_id_env", "client_secret_env", "access_token_env", "bearer_token_env"):
        value = str(auth.get(key, "") or "").strip()
        if value:
            names.append(value)
    for key in ("aliases", "client_id_aliases", "client_secret_aliases"):
        value = auth.get(key, [])
        if isinstance(value, str):
            value = [value]
        if isinstance(value, list):
            names.extend(str(item).strip() for item in value if str(item).strip())
    return names


def load_lamascout_sources(env_names: set[str]) -> tuple[list[dict[str, Any]], list[str]]:
    registry = yaml.safe_load(LAMASCOUT_REGISTRY.read_text(encoding="utf-8")) or {}
    inline_hits = registry_inline_secret_hits(registry)
    rows: list[dict[str, Any]] = []
    for source in registry.get("sources", []) or []:
        auth = source.get("auth", {}) or {}
        candidates = auth_env_candidates(auth)
        rows.append(
            {
                "name": source.get("name", ""),
                "display_name": source.get("display_name", ""),
                "source_type": source.get("source_type", ""),
                "active": bool(source.get("active", False)),
                "access_mode": source.get("access_mode", ""),
                "endpoint": source.get("endpoint", ""),
                "search_term_count": len(source.get("search_terms", []) or []),
                "env_candidates": candidates,
                "credential_present": has_env(env_names, candidates) if candidates else True,
                "write_or_spend_allowed": False,
                "human_action_required_for_account_mutation": True,
            }
        )
    return rows, inline_hits


def build_payload() -> dict[str, Any]:
    ensure_api_registry_report()
    env_names = load_env_key_names()
    api_report = read_json(API_REGISTRY_REPORT)
    lamascout_sources, inline_hits = load_lamascout_sources(env_names)

    total_keys = int(api_report.get("total_keys") or 0)
    present_keys = int(api_report.get("present_keys") or 0)
    active_media_sources = [row for row in lamascout_sources if row["active"]]
    active_media_present = [row for row in active_media_sources if row["credential_present"]]
    write_or_spend_count = sum(1 for row in lamascout_sources if row["write_or_spend_allowed"])

    payload = {
        "generated_utc": now_utc(),
        "schema": "api_key_governance_firewall_v1",
        "status": "KEY_FIREWALL_READY_HUMAN_GATED" if not inline_hits and write_or_spend_count == 0 else "KEY_FIREWALL_BLOCKED",
        "summary": {
            "registry_total_key_slots": total_keys,
            "registry_present_key_slots": present_keys,
            "registry_missing_key_slots": int(api_report.get("missing_keys") or 0),
            "registry_coverage_pct": float(api_report.get("coverage_pct") or 0.0),
            "lamascout_source_count": len(lamascout_sources),
            "lamascout_active_source_count": len(active_media_sources),
            "lamascout_active_sources_with_credentials": len(active_media_present),
            "lamascout_inline_credential_hit_count": len(inline_hits),
            "write_or_spend_allowed_count": write_or_spend_count,
            "raw_credential_values_stored": False,
            "final_action_allowed_without_human": False,
            "live_trading_allowed": False,
            "social_posting_allowed": False,
            "ad_spend_allowed": False,
        },
        "api_key_registry_report": {
            "path": rel(API_REGISTRY_REPORT),
            "schema": api_report.get("schema", ""),
            "total_keys": total_keys,
            "present_keys": present_keys,
            "coverage_pct": api_report.get("coverage_pct"),
            "notes": api_report.get("notes", []),
        },
        "lamascout_sources": lamascout_sources,
        "inline_secret_hits": inline_hits,
        "firewall_rules": [
            "Never commit raw API values to tracked registry files.",
            "Use *_env fields and ignored local env files for all credential material.",
            "LumaScout media sources are read-only metric/source-intelligence lanes.",
            "No posting, messaging, comments, uploads, page edits, ad spend, trading, withdrawals, or capital movement without explicit human approval and a separate purpose-built workflow.",
            "Public reports may show provider names, key presence booleans, source counts, hashes, and claim boundaries only.",
        ],
        "allowed_actions": [
            "presence_audit",
            "purpose_mapping",
            "read_only_source_metrics",
            "dashboard_receipt",
            "reviewer_safe_summary",
        ],
        "blocked_actions": sorted(WRITE_OR_SPEND_ACTIONS),
        "outputs": {
            "json": rel(OUT_JSON),
            "dashboard_json": rel(DASHBOARD_JSON),
            "markdown": rel(OUT_MD),
        },
    }
    payload["key_firewall_sha256"] = sha256_text(payload)
    return payload


def render_markdown(payload: dict[str, Any]) -> str:
    summary = payload["summary"]
    lines = [
        "# Key Governance Firewall - 2026-07-09",
        "",
        "Purpose: make the live-key registry useful for proof and source breadth without exposing credential values or authorizing live account actions.",
        "",
        "This firewall records provider purpose, credential presence, and human-action boundaries only. It never stores raw credential values.",
        "",
        "## Status",
        "",
        f"- Status: `{payload['status']}`",
        f"- Registry key slots: `{summary['registry_total_key_slots']}`",
        f"- Present key slots: `{summary['registry_present_key_slots']}`",
        f"- Missing key slots: `{summary['registry_missing_key_slots']}`",
        f"- Coverage: `{summary['registry_coverage_pct']}`",
        f"- LumaScout sources: `{summary['lamascout_source_count']}`",
        f"- LumaScout active sources: `{summary['lamascout_active_source_count']}`",
        f"- Active LumaScout sources with credentials: `{summary['lamascout_active_sources_with_credentials']}`",
        f"- Inline credential hits: `{summary['lamascout_inline_credential_hit_count']}`",
        f"- Write/spend actions allowed: `{summary['write_or_spend_allowed_count']}`",
        f"- Raw credential values stored: `{str(summary['raw_credential_values_stored']).lower()}`",
        f"- Final action without human: `{str(summary['final_action_allowed_without_human']).lower()}`",
        f"- Live trading allowed: `{str(summary['live_trading_allowed']).lower()}`",
        f"- Social posting allowed: `{str(summary['social_posting_allowed']).lower()}`",
        f"- Ad spend allowed: `{str(summary['ad_spend_allowed']).lower()}`",
        f"- Firewall SHA-256: `{payload['key_firewall_sha256']}`",
        "",
        "## LumaScout Media Sources",
        "",
    ]
    for row in payload["lamascout_sources"]:
        lines.extend(
            [
                f"### {row['display_name']}",
                "",
                f"- Name: `{row['name']}`",
                f"- Type: `{row['source_type']}`",
                f"- Active: `{str(row['active']).lower()}`",
                f"- Access mode: `{row['access_mode']}`",
                f"- Search terms: `{row['search_term_count']}`",
                f"- Credential present: `{str(row['credential_present']).lower()}`",
                f"- Write/spend allowed: `{str(row['write_or_spend_allowed']).lower()}`",
                f"- Account mutation requires human: `{str(row['human_action_required_for_account_mutation']).lower()}`",
                "",
            ]
        )
    lines.extend(["## Firewall Rules", ""])
    for rule in payload["firewall_rules"]:
        lines.append(f"- {rule}")
    lines.extend(["", "## Blocked Actions", ""])
    for action in payload["blocked_actions"]:
        lines.append(f"- `{action}`")
    lines.append("")
    return "\n".join(lines)


def scan_sensitive_text(text: str) -> list[str]:
    lowered = text.lower()
    return sorted({marker for marker in SECRET_MARKERS if marker in lowered})


def main() -> int:
    payload = build_payload()
    markdown = render_markdown(payload)
    sensitive_hits = scan_sensitive_text(markdown)
    if sensitive_hits:
        raise SystemExit(f"Refusing to write sensitive public key-firewall markers: {sensitive_hits}")
    write_json(OUT_JSON, payload)
    write_json(DASHBOARD_JSON, payload)
    write_text(OUT_MD, markdown)
    print(
        json.dumps(
            {
                "status": payload["status"],
                "present_keys": payload["summary"]["registry_present_key_slots"],
                "total_keys": payload["summary"]["registry_total_key_slots"],
                "lamascout_active_sources": payload["summary"]["lamascout_active_source_count"],
                "inline_credential_hits": payload["summary"]["lamascout_inline_credential_hit_count"],
                "markdown": rel(OUT_MD),
            },
            indent=2,
        )
    )
    return 0 if payload["status"] == "KEY_FIREWALL_READY_HUMAN_GATED" else 1


if __name__ == "__main__":
    raise SystemExit(main())
