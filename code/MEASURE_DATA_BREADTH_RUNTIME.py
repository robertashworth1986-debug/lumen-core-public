from __future__ import annotations

import importlib.util
import json
import random
import statistics
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(r"C:\LumaTrader\INSTITUTIONAL_STACK_V2")
OUT = ROOT / "out"
OUT_OPS = OUT / "ops"
CONF = ROOT / "config"

DATASET_CATALOG = OUT / "dataset_catalog.json"
LIVE_REGISTRY = CONF / "live_source_registry.json"

NODE_RED_BASE = "http://127.0.0.1:1880"
GATEWAY_BASE = "http://127.0.0.1:8787"

GOV_SOURCE_HINTS = (
    "NOAA",
    "USGS",
    "EPA",
    "FRED",
    "BLS",
    "CENSUS",
    "EIA",
    "NASA",
    "NREL",
    "BEA",
    "DOE",
    "DOT",
    "USDA",
    "HUD",
    "HHS",
    "CDC",
    "NIST",
    "DOL",
    "VA",
    "SSA",
)

GOV_SECTOR_HINTS = {
    "energy",
    "energy_lab",
    "rates",
    "macro",
    "demographic",
    "labor",
    "weather",
    "water",
    "air_quality",
    "space",
    "public_health",
    "transport",
    "housing",
}

PREMIUM_MODULES = [
    "pandas",
    "numpy",
    "scipy",
    "sklearn",
    "xgboost",
    "lightgbm",
    "shap",
    "polars",
    "pyarrow",
    "statsmodels",
    "pypfopt",
    "quantstats",
    "openpyxl",
]


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def stamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def load_json(path: Path, default: Any) -> Any:
    try:
        if path.exists():
            return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        pass
    return default


def http_probe(url: str, timeout: int = 8) -> dict[str, Any]:
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "LumenCore/RuntimeProbe"})
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            body = resp.read(160).decode("utf-8", errors="ignore")
            return {"ok": True, "status": int(resp.getcode()), "sample": body}
    except urllib.error.HTTPError as ex:
        return {"ok": False, "status": int(ex.code), "error": str(ex)}
    except Exception as ex:
        return {"ok": False, "status": None, "error": str(ex)}


def looks_like_gov(row: dict[str, Any]) -> bool:
    src = str(row.get("source", "")).upper()
    sector = str(row.get("sector", "")).strip().lower()
    env_blob = str(row.get("env", "")).upper()
    if any(h in src for h in GOV_SOURCE_HINTS):
        return True
    if sector in GOV_SECTOR_HINTS:
        return True
    if any(h in env_blob for h in GOV_SOURCE_HINTS):
        return True
    return False


def build_dataset_summary(files: list[dict[str, Any]]) -> dict[str, Any]:
    format_counts: dict[str, int] = {}
    parse_ok = 0
    zipped_members = 0
    total_rows = 0
    total_bytes = 0

    for row in files:
        fmt = str(row.get("format", "unknown") or "unknown").lower()
        format_counts[fmt] = format_counts.get(fmt, 0) + 1
        if str(row.get("scan_note", "")).lower() == "ok":
            parse_ok += 1
        if bool(row.get("in_archive", False)):
            zipped_members += 1
        total_rows += int(row.get("rows", 0) or 0)
        total_bytes += int(row.get("bytes", 0) or 0)

    top_rows = sorted(
        [r for r in files if int(r.get("rows", 0) or 0) > 0],
        key=lambda r: int(r.get("rows", 0) or 0),
        reverse=True,
    )[:10]

    return {
        "datasets_measured": len(files),
        "parse_ok_count": parse_ok,
        "parse_ok_pct": round((100.0 * parse_ok / max(1, len(files))), 2),
        "zipped_member_count": zipped_members,
        "format_counts": format_counts,
        "rows_total": total_rows,
        "bytes_total": total_bytes,
        "top_rows": [
            {
                "path": str(r.get("path", "")),
                "rows": int(r.get("rows", 0) or 0),
                "format": str(r.get("format", "unknown")),
            }
            for r in top_rows
        ],
    }


def simulate_processing(files: list[dict[str, Any]], runs: int = 600) -> dict[str, Any]:
    if not files:
        return {
            "sim_runs": runs,
            "p50_sec": 0.0,
            "p95_sec": 0.0,
            "avg_sec": 0.0,
            "note": "no_files",
        }

    base_seconds = 0.0
    for row in files:
        rows = max(0, int(row.get("rows", 0) or 0))
        size_bytes = max(0, int(row.get("bytes", 0) or 0))
        # Deterministic baseline estimate: row cost + IO cost.
        base_seconds += (rows / 28000.0) + (size_bytes / (52.0 * 1024.0 * 1024.0))

    rng = random.Random(42)
    sims: list[float] = []
    for _ in range(runs):
        jitter = max(0.55, min(1.80, 1.0 + rng.gauss(0.0, 0.18)))
        sims.append(base_seconds * jitter)

    sims.sort()
    p50 = sims[int(0.50 * (len(sims) - 1))]
    p95 = sims[int(0.95 * (len(sims) - 1))]

    return {
        "sim_runs": runs,
        "p50_sec": round(p50, 3),
        "p95_sec": round(p95, 3),
        "avg_sec": round(statistics.mean(sims), 3),
        "base_sec": round(base_seconds, 3),
    }


def premium_probe() -> dict[str, Any]:
    rows = []
    ok_count = 0
    for mod in PREMIUM_MODULES:
        present = importlib.util.find_spec(mod) is not None
        if present:
            ok_count += 1
        rows.append({"module": mod, "present": present})
    return {
        "present_count": ok_count,
        "total_count": len(PREMIUM_MODULES),
        "present_pct": round((100.0 * ok_count / max(1, len(PREMIUM_MODULES))), 2),
        "rows": rows,
    }


def render_markdown(payload: dict[str, Any]) -> str:
    ds = payload.get("dataset_summary", {})
    gov = payload.get("gov_key_breadth", {})
    nodered = payload.get("nodered_runtime", {})
    premium = payload.get("premium_packages", {})
    sim = payload.get("processing_simulation", {})

    lines = [
        "# Data Breadth Runtime Probe",
        "",
        f"Generated UTC: {payload.get('generated_utc', '')}",
        "",
        "## Dataset Breadth",
        f"- datasets_measured: {ds.get('datasets_measured', 0)}",
        f"- zipped_member_count: {ds.get('zipped_member_count', 0)}",
        f"- parse_ok_pct: {ds.get('parse_ok_pct', 0)}",
        f"- rows_total: {ds.get('rows_total', 0)}",
        "",
        "## Gov Key Breadth",
        f"- gov_sources_total: {gov.get('gov_sources_total', 0)}",
        f"- gov_sources_enabled: {gov.get('gov_sources_enabled', 0)}",
        f"- gov_sources_measured: {gov.get('gov_sources_measured', 0)}",
        "",
        "## Node-RED Runtime",
        f"- node_red_ok: {nodered.get('node_red_ok', False)}",
        f"- gateway_ok: {nodered.get('gateway_ok', False)}",
        "",
        "## Premium Packages",
        f"- present_count: {premium.get('present_count', 0)}/{premium.get('total_count', 0)}",
        f"- present_pct: {premium.get('present_pct', 0)}",
        "",
        "## Processing Simulation",
        f"- p50_sec: {sim.get('p50_sec', 0)}",
        f"- p95_sec: {sim.get('p95_sec', 0)}",
        f"- avg_sec: {sim.get('avg_sec', 0)}",
    ]
    return "\n".join(lines) + "\n"


def main() -> int:
    OUT_OPS.mkdir(parents=True, exist_ok=True)

    catalog = load_json(DATASET_CATALOG, {})
    files = catalog.get("files", []) if isinstance(catalog, dict) else []
    files = [r for r in files if isinstance(r, dict)]

    registry = load_json(LIVE_REGISTRY, {})
    reg_rows = []
    if isinstance(registry, dict):
        raw = registry.get("rows", registry.get("sources", []))
        if isinstance(raw, list):
            reg_rows = [r for r in raw if isinstance(r, dict)]

    gov_rows = [r for r in reg_rows if looks_like_gov(r)]
    gov_enabled = [r for r in gov_rows if bool(r.get("enabled", False))]
    gov_measured = [
        r
        for r in gov_rows
        if bool(r.get("enabled", False)) and (bool(r.get("probe_ok", False)) or int(r.get("rows", 0) or 0) > 0)
    ]

    node_red_probe = http_probe(f"{NODE_RED_BASE}/")
    gateway_probe = http_probe(f"{GATEWAY_BASE}/health")

    payload = {
        "generated_utc": now_iso(),
        "scope": "data_breadth_runtime_probe",
        "dataset_summary": build_dataset_summary(files),
        "gov_key_breadth": {
            "gov_sources_total": len(gov_rows),
            "gov_sources_enabled": len(gov_enabled),
            "gov_sources_measured": len(gov_measured),
            "sources": [str(r.get("source", "")) for r in gov_rows],
        },
        "nodered_runtime": {
            "node_red_ok": bool(node_red_probe.get("ok", False)),
            "node_red_status": node_red_probe.get("status"),
            "node_red_error": node_red_probe.get("error"),
            "gateway_ok": bool(gateway_probe.get("ok", False)),
            "gateway_status": gateway_probe.get("status"),
            "gateway_error": gateway_probe.get("error"),
        },
        "premium_packages": premium_probe(),
        "processing_simulation": simulate_processing(files),
        "artifact_inputs": {
            "dataset_catalog": str(DATASET_CATALOG),
            "live_source_registry": str(LIVE_REGISTRY),
        },
    }

    ts = stamp()
    tagged_json = OUT_OPS / f"data_breadth_runtime_probe_{ts}.json"
    latest_json = OUT_OPS / "data_breadth_runtime_probe_latest.json"
    tagged_md = OUT_OPS / f"data_breadth_runtime_probe_{ts}.md"
    latest_md = OUT_OPS / "data_breadth_runtime_probe_latest.md"

    md = render_markdown(payload)

    tagged_json.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    latest_json.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    tagged_md.write_text(md, encoding="utf-8")
    latest_md.write_text(md, encoding="utf-8")

    print(f"PROBE_JSON={latest_json}")
    print(f"PROBE_MD={latest_md}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
