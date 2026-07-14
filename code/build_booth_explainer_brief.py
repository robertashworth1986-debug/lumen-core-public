#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import hashlib
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from booth_public_contract import (
    public_booth_contains_forbidden_value,
    public_booth_projection,
)

STACK_ROOT = Path(__file__).resolve().parents[1]
OUT_DIR = STACK_ROOT / "out" / "execution" / "universe_map"

UNIVERSE_MAP_FILE = OUT_DIR / "lumencore_universe_map.json"
NOBEL_CATALOG_FILE = OUT_DIR / "lumencore_nobel_engine_catalog.json"
LIVE_HEARTBEAT_FILE = STACK_ROOT / "out" / "execution" / "live_executor_heartbeat.json"
LIVE_TRADE_LEDGER_FILE = STACK_ROOT / "out" / "execution" / "live_trade_ledger.jsonl"
PREMIUM_MIRROR_LATEST_FILE = STACK_ROOT.parent / "premium_packages_mirror" / "premium_package_mirror_latest.json"
MASTER_VALUATION_FILE = STACK_ROOT / "out" / "ops" / "master_valuation" / "master_valuation_latest.json"
LUMA_EXPLAINER_FILE = STACK_ROOT / "out" / "ops" / "luma_explainer" / "luma_explainer_quantified_latest.json"
PUBLIC_TRUTH_FILE = STACK_ROOT / "out" / "ops" / "public_truth" / "public_truth_latest.json"

OUTPUT_JSON = OUT_DIR / "booth_explainer_brief.json"
OUTPUT_MD = OUT_DIR / "booth_explainer_brief.md"
OUTPUT_SHA = OUT_DIR / "booth_explainer_brief_sha256.json"
OUTPUT_HISTORY = OUT_DIR / "booth_explainer_brief_history.jsonl"
UPLOAD_READY_ROOT = STACK_ROOT / "out" / "ops" / "linkedin_master_pack" / "upload_ready"

_COPY_JSON_NAME = re.compile(
    r"^booth_explainer_brief(?P<variant>__\d+)?\.json$",
    re.IGNORECASE,
)
_COPY_MD_NAME = re.compile(
    r"^booth_explainer_brief(?P<variant>__\d+)?\.md$",
    re.IGNORECASE,
)
_COPY_SHA_NAME = re.compile(
    r"^booth_explainer_brief_sha256(?P<variant>__\d+)?\.json$",
    re.IGNORECASE,
)

DEFAULT_FOUNDER_PROFILE = {
    "founder": "Robert BabyRay Ashworth",
    "company_system": "LumenCore / NovaCore / LumaCore",
    "uei": "SQY2XW71ZM51",
    "cage": "14TM8",
    "patent_title": "LumenCore: A Modular AI Node Framework for Conscious Systems Integration",
    "private_identifiers_embedded": False,
}

PRIVATE_FOUNDER_FIELDS = {
    "ein",
    "tin",
    "uspto_non_provisional_application",
    "patent_center_reference",
}


def now_utc() -> str:
    return datetime.now(timezone.utc).isoformat()


def load_json(path: Path, default: Any) -> Any:
    try:
        if path.exists():
            return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        pass
    return default


def read_sha256(path: Path, chunk_size: int = 1024 * 1024) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as fh:
        while True:
            chunk = fh.read(chunk_size)
            if not chunk:
                break
            digest.update(chunk)
    return digest.hexdigest()


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")


def _tail_jsonl(path: Path, n: int) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    if n <= 0:
        return rows

    try:
        lines = path.read_text(encoding="utf-8", errors="ignore").splitlines()
    except Exception:
        return rows

    for raw in lines[-n:]:
        text = raw.strip()
        if not text:
            continue
        try:
            row = json.loads(text)
            if isinstance(row, dict):
                rows.append(row)
        except Exception:
            continue
    return rows


def _safe_int(value: Any, default: int = 0) -> int:
    try:
        return int(float(value))
    except Exception:
        return int(default)


def _safe_float(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except Exception:
        return float(default)


def _build_payload(recent_trade_rows: int) -> dict[str, Any]:
    universe_map = load_json(UNIVERSE_MAP_FILE, {})
    catalog = load_json(NOBEL_CATALOG_FILE, {})
    heartbeat = load_json(LIVE_HEARTBEAT_FILE, {})
    mirror = load_json(PREMIUM_MIRROR_LATEST_FILE, {})
    master_valuation = load_json(MASTER_VALUATION_FILE, {})
    luma_explainer = load_json(LUMA_EXPLAINER_FILE, {})
    public_truth = load_json(PUBLIC_TRUTH_FILE, {})
    trade_rows = _tail_jsonl(LIVE_TRADE_LEDGER_FILE, max(1, recent_trade_rows))

    founder_profile = DEFAULT_FOUNDER_PROFILE
    if isinstance(universe_map, dict):
        maybe_profile = universe_map.get("founder_profile")
        if isinstance(maybe_profile, dict) and maybe_profile:
            founder_profile = maybe_profile
    founder_profile = {
        key: value for key, value in founder_profile.items() if key not in PRIVATE_FOUNDER_FIELDS
    }
    founder_profile["private_identifiers_embedded"] = False

    scan = universe_map.get("scan", {}) if isinstance(universe_map, dict) else {}
    roots = universe_map.get("roots", []) if isinstance(universe_map, dict) else []
    engine_counts = scan.get("engine_counts", {}) if isinstance(scan, dict) else {}

    roots_present = sum(1 for r in roots if isinstance(r, dict) and bool(r.get("exists")))
    roots_total = len([r for r in roots if isinstance(r, dict)])

    engine_catalog_rows = catalog.get("engines", []) if isinstance(catalog, dict) else []
    if not isinstance(engine_catalog_rows, list):
        engine_catalog_rows = []
    catalog_by_id = {
        str(row.get("engine_id", "")): row
        for row in engine_catalog_rows
        if isinstance(row, dict) and str(row.get("engine_id", ""))
    }

    ranked_counts = []
    if isinstance(engine_counts, dict):
        for key, value in engine_counts.items():
            ranked_counts.append((str(key), _safe_int(value, 0)))
    ranked_counts.sort(key=lambda x: x[1], reverse=True)

    top_engines: list[dict[str, Any]] = []
    for engine_id, hits in ranked_counts[:15]:
        cat = catalog_by_id.get(engine_id, {})
        top_engines.append(
            {
                "engine_id": engine_id,
                "name": str(cat.get("name", engine_id)),
                "asset_hits": int(hits),
                "readiness_score_0_100": round(_safe_float(cat.get("readiness_score_0_100", 0.0), 0.0), 2),
                "what_it_does": str(((cat.get("one_pager", {}) or {}).get("what_it_does", ""))),
                "who_buys_it": str(((cat.get("one_pager", {}) or {}).get("who_buys_it", ""))),
            }
        )

    latest_trade = trade_rows[-1] if trade_rows else {}
    if not isinstance(latest_trade, dict):
        latest_trade = {}

    recent_trades = []
    for row in trade_rows[-12:]:
        if not isinstance(row, dict):
            continue
        recent_trades.append(
            {
                "timestamp": str(row.get("timestamp", "") or ""),
                "txid": str(row.get("txid", "") or ""),
                "symbol": str(row.get("symbol", "") or ""),
                "pair": str(row.get("pair", "") or ""),
                "side": str(row.get("side", "") or ""),
                "status": str(row.get("status", "") or ""),
                "size_usd": round(_safe_float(row.get("size_usd", 0.0), 0.0), 6),
            }
        )

    payload = {
        "generated_utc": now_utc(),
        "schema": "luma_booth_explainer_brief_v1",
        "founder_profile": founder_profile,
        "indexing": {
            "files_indexed": _safe_int((scan or {}).get("files_scanned", 0), 0),
            "total_size_bytes": _safe_int((scan or {}).get("total_size_bytes", 0), 0),
            "roots_present": int(roots_present),
            "roots_total": int(roots_total),
            "scan_capped": bool((scan or {}).get("scan_capped", False)),
        },
        "catalog": {
            "engine_count": len(engine_catalog_rows),
            "assets_source_rows": _safe_int(catalog.get("assets_source_rows", 0), 0) if isinstance(catalog, dict) else 0,
            "top_engines": top_engines,
        },
        "live_execution": {
            "heartbeat": {
                "status": str((heartbeat or {}).get("status", "unknown")),
                "reason": str((heartbeat or {}).get("reason", "")),
                "symbol": str((heartbeat or {}).get("selected_symbol") or (heartbeat or {}).get("symbol") or ""),
                "universe_candidate_count": _safe_int((heartbeat or {}).get("universe_candidate_count", 0), 0),
                "timestamp_utc": str((heartbeat or {}).get("timestamp_utc", "")),
            },
            "latest_trade": {
                "timestamp": str(latest_trade.get("timestamp", "") or ""),
                "txid": str(latest_trade.get("txid", "") or ""),
                "symbol": str(latest_trade.get("symbol", "") or ""),
                "pair": str(latest_trade.get("pair", "") or ""),
                "side": str(latest_trade.get("side", "") or ""),
                "status": str(latest_trade.get("status", "") or ""),
                "size_usd": round(_safe_float(latest_trade.get("size_usd", 0.0), 0.0), 6),
            },
            "recent_trade_count": len(recent_trades),
            "recent_trades": recent_trades,
        },
        "premium_mirror": {
            "generated_utc": str((mirror or {}).get("generated_utc", "")),
            "destination_root": str((mirror or {}).get("destination_root", "")),
            "total_sources": _safe_int((mirror or {}).get("total_sources", 0), 0),
            "total_files_seen": _safe_int((mirror or {}).get("total_files_seen", 0), 0),
            "total_files_copied": _safe_int((mirror or {}).get("total_files_copied", 0), 0),
            "total_bytes_seen": _safe_int((mirror or {}).get("total_bytes_seen", 0), 0),
            "chain_of_custody_sha256": str((mirror or {}).get("chain_of_custody_sha256", "")),
        },
        "autonomous_grant_win": {
            "master_valuation_generated_utc": str((master_valuation or {}).get("generated_utc", "")),
            "master_valuation_proxy_usd": _safe_float(
                ((master_valuation or {}).get("valuation", {}) or {}).get("master_valuation_proxy_usd", 0.0),
                0.0,
            ),
            "valuation_increment_usd": _safe_float(
                ((master_valuation or {}).get("valuation", {}) or {}).get("valuation_increment_usd", 0.0),
                0.0,
            ),
            "ip_entry_sha256": str((((master_valuation or {}).get("ip_lock", {}) or {}).get("entry_sha256", ""))),
            "event_id": str((((master_valuation or {}).get("ip_lock", {}) or {}).get("event_id", ""))),
            "explainer_generated_utc": str((luma_explainer or {}).get("generated_utc", "")),
            "explainer_entry_sha256": str((luma_explainer or {}).get("entry_sha256", "")),
            "public_truth_status": str((public_truth or {}).get("status", "")),
            "public_truth_generated_utc": str((public_truth or {}).get("generated_utc", "")),
            "public_truth_chain_entry_sha256": str((((public_truth or {}).get("chain", {}) or {}).get("entry_sha256", ""))),
        },
        "artifacts": {
            "universe_map_json": str(UNIVERSE_MAP_FILE.as_posix()),
            "nobel_engine_catalog_json": str(NOBEL_CATALOG_FILE.as_posix()),
            "live_trade_ledger_jsonl": str(LIVE_TRADE_LEDGER_FILE.as_posix()),
            "live_executor_heartbeat_json": str(LIVE_HEARTBEAT_FILE.as_posix()),
            "premium_mirror_latest_json": str(PREMIUM_MIRROR_LATEST_FILE.as_posix()),
            "master_valuation_latest_json": str(MASTER_VALUATION_FILE.as_posix()),
            "luma_explainer_quantified_latest_json": str(LUMA_EXPLAINER_FILE.as_posix()),
            "public_truth_latest_json": str(PUBLIC_TRUTH_FILE.as_posix()),
        },
    }

    return payload


def _render_markdown(payload: dict[str, Any]) -> str:
    founder = payload.get("founder_profile", {}) if isinstance(payload, dict) else {}
    indexing = payload.get("indexing", {}) if isinstance(payload, dict) else {}
    catalog = payload.get("catalog", {}) if isinstance(payload, dict) else {}
    live = payload.get("live_execution", {}) if isinstance(payload, dict) else {}
    hb = live.get("heartbeat", {}) if isinstance(live, dict) else {}
    mirror = payload.get("premium_mirror", {}) if isinstance(payload, dict) else {}

    lines: list[str] = []
    lines.append("# Luma Booth Explainer Brief")
    lines.append("")
    lines.append(f"Generated UTC: {payload.get('generated_utc', '')}")
    lines.append("")

    lines.append("## Founder Profile")
    for key in (
        "founder",
        "company_system",
        "uei",
        "cage",
        "patent_title",
        "private_identifiers_embedded",
    ):
        lines.append(f"- {key}: {founder.get(key, '')}")
    lines.append("")

    lines.append("## Indexing")
    lines.append(f"- files_indexed: {indexing.get('files_indexed', 0)}")
    lines.append(f"- roots_present: {indexing.get('roots_present', 0)}/{indexing.get('roots_total', 0)}")
    lines.append(f"- scan_capped: {indexing.get('scan_capped', False)}")
    lines.append("")

    lines.append("## Catalog")
    lines.append(f"- engine_count: {catalog.get('engine_count', 0)}")
    lines.append(f"- assets_source_rows: {catalog.get('assets_source_rows', 0)}")
    lines.append("")

    lines.append("## Execution Boundary")
    lines.append(f"- heartbeat_status: {hb.get('status', '')}")
    lines.append(f"- heartbeat_timestamp_utc: {hb.get('timestamp_utc', '')}")
    lines.append(f"- universe_candidate_count: {hb.get('universe_candidate_count', 0)}")
    lines.append(f"- recent_event_count: {live.get('recent_trade_count', 0)}")
    lines.append(f"- details_redacted: {str(live.get('details_redacted', True)).lower()}")
    lines.append(f"- public_claim_allowed: {str(live.get('public_claim_allowed', False)).lower()}")
    lines.append(f"- live_execution_authority: {str(live.get('live_execution_authority', False)).lower()}")
    lines.append("")

    lines.append("## Premium Mirror")
    lines.append(f"- total_sources: {mirror.get('total_sources', 0)}")
    lines.append(f"- total_files_seen: {mirror.get('total_files_seen', 0)}")
    lines.append(f"- total_files_copied: {mirror.get('total_files_copied', 0)}")
    lines.append("")
    lines.append("## Claim Boundary")
    lines.append(f"- supported_maturity_level: Level {payload.get('supported_maturity_level', 3)}")
    lines.append(f"- profit_claim_allowed: {str(payload.get('profit_claim_allowed', False)).lower()}")
    lines.append(f"- live_execution_authority: {str(payload.get('live_execution_authority', False)).lower()}")
    lines.append("")
    lines.append(str(payload.get("claim_boundary", "")))

    return "\n".join(lines).strip() + "\n"


def _safe_history_text(value: Any) -> str:
    text = str(value or "")
    return "" if public_booth_contains_forbidden_value(text) else text


def _history_row_from_payload(payload: dict[str, Any]) -> dict[str, Any]:
    return {
        "generated_utc": payload.get("generated_utc"),
        "files_indexed": ((payload.get("indexing", {}) or {}).get("files_indexed", 0)),
        "engine_count": ((payload.get("catalog", {}) or {}).get("engine_count", 0)),
        "heartbeat_status": (((payload.get("live_execution", {}) or {}).get("heartbeat", {}) or {}).get("status", "")),
        "details_redacted": True,
        "public_claim_allowed": False,
        "mirror_files_seen": ((payload.get("premium_mirror", {}) or {}).get("total_files_seen", 0)),
    }


def _sanitize_history_row(row: dict[str, Any]) -> dict[str, Any]:
    """Reduce a legacy history row to the bounded public-history contract."""

    return {
        "generated_utc": _safe_history_text(row.get("generated_utc")),
        "files_indexed": max(0, _safe_int(row.get("files_indexed", 0), 0)),
        "engine_count": max(0, _safe_int(row.get("engine_count", 0), 0)),
        "heartbeat_status": _safe_history_text(row.get("heartbeat_status")),
        "details_redacted": True,
        "public_claim_allowed": False,
        "mirror_files_seen": max(0, _safe_int(row.get("mirror_files_seen", 0), 0)),
    }


def _rewrite_history(path: Path, payload: dict[str, Any]) -> None:
    rows: list[dict[str, Any]] = []
    if path.exists():
        try:
            for raw in path.read_text(encoding="utf-8", errors="ignore").splitlines():
                try:
                    row = json.loads(raw)
                except Exception:
                    continue
                if isinstance(row, dict):
                    rows.append(_sanitize_history_row(row))
        except Exception:
            rows = []

    rows.append(_sanitize_history_row(_history_row_from_payload(payload)))
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        "".join(json.dumps(row, ensure_ascii=False) + "\n" for row in rows),
        encoding="utf-8",
    )


def _sha_manifest(files: list[Path], generated_utc: str) -> dict[str, Any]:
    return {
        "generated_utc": generated_utc,
        "public_copy": True,
        "details_redacted": True,
        "files": {path.name: read_sha256(path) for path in files if path.is_file()},
    }


def _path_is_within_root(path: Path, root: Path) -> bool:
    try:
        path.resolve().relative_to(root.resolve())
    except (OSError, ValueError):
        return False
    return True


def _rewrite_upload_ready_copies(
    root: Path,
    payload: dict[str, Any],
    markdown: str,
    manifest_generated_utc: str,
) -> list[Path]:
    """Rewrite only existing booth copies below the bounded upload-ready root."""

    if not root.is_dir():
        return []

    candidates = sorted(root.rglob("booth_explainer_brief*"))
    candidates = [
        path
        for path in candidates
        if path.is_file() and not path.is_symlink() and _path_is_within_root(path, root)
    ]
    rewritten: list[Path] = []

    for path in candidates:
        if _COPY_JSON_NAME.fullmatch(path.name):
            write_json(path, payload)
            rewritten.append(path)
        elif _COPY_MD_NAME.fullmatch(path.name):
            path.write_text(markdown, encoding="utf-8")
            rewritten.append(path)

    for path in candidates:
        match = _COPY_SHA_NAME.fullmatch(path.name)
        if not match:
            continue
        variant = match.group("variant") or ""
        related = [
            path.parent / f"booth_explainer_brief{variant}.json",
            path.parent / f"booth_explainer_brief{variant}.md",
        ]
        write_json(path, _sha_manifest(related, manifest_generated_utc))
        rewritten.append(path)

    return rewritten


def main() -> None:
    parser = argparse.ArgumentParser(description="Build Luma booth explainer brief from universe map, catalog, and live execution artifacts.")
    parser.add_argument("--recent-trade-rows", type=int, default=80, help="How many ledger rows to inspect for recent trade context.")
    args = parser.parse_args()

    payload = public_booth_projection(
        _build_payload(recent_trade_rows=max(1, int(args.recent_trade_rows)))
    )

    write_json(OUTPUT_JSON, payload)
    markdown = _render_markdown(payload)
    OUTPUT_MD.write_text(markdown, encoding="utf-8")

    manifest_generated_utc = now_utc()
    write_json(
        OUTPUT_SHA,
        _sha_manifest([OUTPUT_JSON, OUTPUT_MD], manifest_generated_utc),
    )

    _rewrite_history(OUTPUT_HISTORY, payload)
    _rewrite_upload_ready_copies(
        UPLOAD_READY_ROOT,
        payload,
        markdown,
        manifest_generated_utc,
    )

    print(str(OUTPUT_JSON.as_posix()))
    print(str(OUTPUT_MD.as_posix()))
    print(str(OUTPUT_SHA.as_posix()))
    print(str(OUTPUT_HISTORY.as_posix()))


if __name__ == "__main__":
    main()
