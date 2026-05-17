#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import hashlib
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

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

DEFAULT_FOUNDER_PROFILE = {
    "founder": "Robert BabyRay Ashworth",
    "company_system": "LumenCore / NovaCore / LumaCore",
    "uei": "SQY2XW71ZM51",
    "cage": "14TM8",
    "ein": "39-3507463",
    "uspto_non_provisional_application": "19/281,546",
    "patent_title": "LumenCore: A Modular AI Node Framework for Conscious Systems Integration",
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
    trade = live.get("latest_trade", {}) if isinstance(live, dict) else {}
    mirror = payload.get("premium_mirror", {}) if isinstance(payload, dict) else {}
    grant_win = payload.get("autonomous_grant_win", {}) if isinstance(payload, dict) else {}

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
        "ein",
        "uspto_non_provisional_application",
        "patent_title",
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

    lines.append("## Live Execution")
    lines.append(f"- heartbeat_status: {hb.get('status', '')}")
    lines.append(f"- heartbeat_reason: {hb.get('reason', '')}")
    lines.append(f"- heartbeat_symbol: {hb.get('symbol', '')}")
    lines.append(f"- latest_trade_txid: {trade.get('txid', '')}")
    lines.append(f"- latest_trade_symbol: {trade.get('symbol', '')}")
    lines.append(f"- latest_trade_status: {trade.get('status', '')}")
    lines.append("")

    lines.append("## Premium Mirror")
    lines.append(f"- total_sources: {mirror.get('total_sources', 0)}")
    lines.append(f"- total_files_seen: {mirror.get('total_files_seen', 0)}")
    lines.append(f"- total_files_copied: {mirror.get('total_files_copied', 0)}")
    lines.append("")
    lines.append("## Autonomous Grant Win Lock")
    lines.append(f"- valuation_increment_usd: {grant_win.get('valuation_increment_usd', 0)}")
    lines.append(f"- master_valuation_proxy_usd: {grant_win.get('master_valuation_proxy_usd', 0)}")
    lines.append(f"- ip_entry_sha256: {grant_win.get('ip_entry_sha256', '')}")
    lines.append(f"- event_id: {grant_win.get('event_id', '')}")
    lines.append(f"- explainer_generated_utc: {grant_win.get('explainer_generated_utc', '')}")
    lines.append(f"- public_truth_status: {grant_win.get('public_truth_status', '')}")
    lines.append(f"- public_truth_chain_entry_sha256: {grant_win.get('public_truth_chain_entry_sha256', '')}")

    return "\n".join(lines).strip() + "\n"


def _append_history(path: Path, payload: dict[str, Any]) -> None:
    row = {
        "generated_utc": payload.get("generated_utc"),
        "files_indexed": ((payload.get("indexing", {}) or {}).get("files_indexed", 0)),
        "engine_count": ((payload.get("catalog", {}) or {}).get("engine_count", 0)),
        "heartbeat_status": (((payload.get("live_execution", {}) or {}).get("heartbeat", {}) or {}).get("status", "")),
        "latest_trade_txid": (((payload.get("live_execution", {}) or {}).get("latest_trade", {}) or {}).get("txid", "")),
        "mirror_files_seen": ((payload.get("premium_mirror", {}) or {}).get("total_files_seen", 0)),
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(row, ensure_ascii=False) + "\n")


def main() -> None:
    parser = argparse.ArgumentParser(description="Build Luma booth explainer brief from universe map, catalog, and live execution artifacts.")
    parser.add_argument("--recent-trade-rows", type=int, default=80, help="How many ledger rows to inspect for recent trade context.")
    args = parser.parse_args()

    payload = _build_payload(recent_trade_rows=max(1, int(args.recent_trade_rows)))

    write_json(OUTPUT_JSON, payload)
    OUTPUT_MD.write_text(_render_markdown(payload), encoding="utf-8")

    sha_payload = {
        "generated_utc": now_utc(),
        "files": {
            str(OUTPUT_JSON.as_posix()): read_sha256(OUTPUT_JSON),
            str(OUTPUT_MD.as_posix()): read_sha256(OUTPUT_MD),
        },
    }
    write_json(OUTPUT_SHA, sha_payload)

    _append_history(OUTPUT_HISTORY, payload)

    print(str(OUTPUT_JSON.as_posix()))
    print(str(OUTPUT_MD.as_posix()))
    print(str(OUTPUT_SHA.as_posix()))
    print(str(OUTPUT_HISTORY.as_posix()))


if __name__ == "__main__":
    main()
