#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import os
import re
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, List, Set, Tuple

STACK_ROOT = Path(__file__).resolve().parents[1]
OUT_DIR = STACK_ROOT / "out" / "execution" / "universe_map"
USER_HOME_NORMALIZED = Path.home().as_posix().lower().rstrip("/")

FOUNDER_PROFILE = {
    "founder": "Robert BabyRay Ashworth",
    "company_system": "LumenCore / NovaCore / LumaCore",
    "uei": "SQY2XW71ZM51",
    "cage": "14TM8",
    "patent_title": "LumenCore: A Modular AI Node Framework for Conscious Systems Integration",
    "private_identifiers_embedded": False,
    "positioning": [
        "contract-ready",
        "SAM.gov active",
        "federal and DoD and DOE and DARPA adjacent",
        "investor-ready",
    ],
}

KERNEL_ARCHITECTURE = [
    "FlowForm geometry",
    "LumanSpiral routing",
    "EtherFrame intelligence layer",
    "LumenShell embodiment layer",
    "AetherReach interface layer",
    "harmonic signal processing",
    "resonance phase coherence logic",
    "evolutionary optimization",
    "chain-of-custody proof",
    "SHA256 ledgering",
    "read-only baselines",
    "frozen deltas",
    "auditability",
    "modular licensing",
]

ENGINE_DEFINITIONS: List[Dict[str, Any]] = [
    {
        "engine_id": "trading_institutional_stack",
        "name": "LumaTrader / Institutional Stack",
        "keywords": ["lumatrader", "institutional_stack_v2", "kraken", "execution", "strategy", "trading", "portfolio", "rolling_capital"],
        "purpose": "Trading intelligence, ingestion, strategy ranking, live and paper execution, proof and investor dashboards.",
        "product_form": "Hedge-fund-grade research terminal and execution-risk layer",
        "licensing_target": "Funds, prop desks, fintech labs, analytics groups",
    },
    {
        "engine_id": "kraken_lumasniper",
        "name": "Kraken Trader / LumaSniper",
        "keywords": ["kraken", "sniper", "symbol_registry", "kill_switch", "paper", "live_executor"],
        "purpose": "Crypto API integration, execution readiness, kill switch, verified logs, sniper alerts.",
        "product_form": "Controlled crypto execution and risk engine",
        "licensing_target": "Crypto traders, small funds, automation builders",
    },
    {
        "engine_id": "lumengov_grant_factory",
        "name": "LumenGov / Grant Factory",
        "keywords": ["lumengov", "grant", "sbir", "darpa", "doe", "nsf", "proposal", "capability_statement"],
        "purpose": "Grant discovery and federal proposal packaging with readiness evidence.",
        "product_form": "AI grant-writing and federal-readiness factory",
        "licensing_target": "Startups, inventors, government contractors",
    },
    {
        "engine_id": "infrastructure_outage_prevention",
        "name": "Infrastructure / Outage Prevention Engine",
        "keywords": ["infra", "infrastructure", "snapshot", "drift", "baseline", "frozen_delta", "audit", "uptime"],
        "purpose": "Detect drift against approved baselines and preserve chain-of-custody evidence.",
        "product_form": "Infrastructure integrity and uptime assurance",
        "licensing_target": "Data centers, hospitals, utilities, telecom, manufacturing",
    },
    {
        "engine_id": "lumascout_digital_scout",
        "name": "LumaScout / Digital Scout",
        "keywords": ["lumascout", "artist", "creator", "momentum", "engagement", "scout"],
        "purpose": "Public-signal scout engine for rising creators and targets.",
        "product_form": "Talent discovery radar",
        "licensing_target": "Music labels, agencies, scouts, creator investors",
    },
    {
        "engine_id": "sports_signal_engine",
        "name": "Sports Signal Engine",
        "keywords": ["sports", "odds", "draftkings", "ev_ranked", "alpha_board", "flowform", "bookmaker"],
        "purpose": "Sports odds ingestion, edge detection, ranking, movement comparison and ROI telemetry.",
        "product_form": "Sports analytics and opportunity engine",
        "licensing_target": "Analysts, bettors, media, sportsbook-adjacent users",
    },
    {
        "engine_id": "crowdfunding_engine",
        "name": "CrowdFunding Engine",
        "keywords": ["crowdfund", "kickstarter", "indiegogo", "campaign", "founder_credibility"],
        "purpose": "Scan crowdfunding campaigns for traction and opportunity.",
        "product_form": "Early opportunity detection engine",
        "licensing_target": "Angel investors, scouts, product researchers",
    },
    {
        "engine_id": "cyber_forensics_engine",
        "name": "Cyber / Digital Forensics Engine",
        "keywords": ["forensic", "incident", "triage", "cyber", "court", "evidence", "investigation"],
        "purpose": "AI-assisted investigation support and court-ready chain-of-custody acceleration.",
        "product_form": "Forensic analysis accelerator",
        "licensing_target": "Cyber firms, investigators, legal teams",
    },
    {
        "engine_id": "identity_echoform_twin",
        "name": "Identity / EchoForm / Digital Twin Engine",
        "keywords": ["echoform", "digital_twin", "identity", "memory_model", "legacy", "hologram"],
        "purpose": "Identity architecture, memory profiles and digital echo systems.",
        "product_form": "Digital identity twin platform",
        "licensing_target": "AR/VR, personal AI, legacy platforms, simulation",
    },
    {
        "engine_id": "unity_xr_luma_live_command",
        "name": "Unity XR / Luma Live Command",
        "keywords": ["unity", "holographic", "holo", "command_room", "luma_live_command", "lumaexperience"],
        "purpose": "Immersive command visualization and investor demo orchestration.",
        "product_form": "Immersive command center",
        "licensing_target": "Training, defense simulation, investor demos, museums",
    },
    {
        "engine_id": "smart_city_telecom_engine",
        "name": "Smart City / Telecom Engine",
        "keywords": ["smart_city", "iot", "telecom", "sensor", "edge_compute", "utility"],
        "purpose": "IoT mesh and edge signal intelligence for infrastructure operations.",
        "product_form": "Smart-city intelligence layer",
        "licensing_target": "Cities, utilities, telecom integrators",
    },
    {
        "engine_id": "flowform_hardware_geometry",
        "name": "FlowForm / Hardware Geometry Engine",
        "keywords": ["flowform", "hardware", "motherboard", "honeycomb", "thermal", "cymatic", "spiral"],
        "purpose": "Hardware geometry and routing IP for thermal and electromagnetic efficiency.",
        "product_form": "Hardware IP and OEM licensing package",
        "licensing_target": "Data centers, EV, robotics, aerospace, semiconductors",
    },
    {
        "engine_id": "energy_nuclear_harmonization",
        "name": "Energy / Nuclear Harmonization Engine",
        "keywords": ["energy", "nuclear", "field_stabilization", "radiation", "high_emi", "harmonization"],
        "purpose": "Research and simulation platform for high-field energy environments.",
        "product_form": "Energy research and simulation platform",
        "licensing_target": "DOE labs, energy companies, defense research",
    },
    {
        "engine_id": "world_model_cross_sector",
        "name": "World Model / Cross-Sector Engine",
        "keywords": ["worldmodel", "cross_sector", "scenario", "multisector", "opportunity_intel", "sector"],
        "purpose": "Cross-domain scenario simulation for failure and opportunity prediction.",
        "product_form": "Multi-sector decision intelligence",
        "licensing_target": "Enterprise strategy teams, government, operators",
    },
    {
        "engine_id": "lumacore_orchestrator",
        "name": "LumaCore Agent / Orchestrator",
        "keywords": ["orchestrator", "router", "controller", "watchdog", "master_agent", "luma_core_agent"],
        "purpose": "Master routing agent for engine orchestration, champions and proof packs.",
        "product_form": "Operating system for the engine universe",
        "licensing_target": "Internal first, then enterprise automation",
    },
]

ROOT_REQUESTED = [
    "C:/LumaTrader",
    "C:/LumaTrader/INSTITUTIONAL_STACK_V2",
    "C:/WhiteHole",
    "C:/WhiteHoleLab",
    "C:/LumaUniverse",
    "C:/LumenCore",
    "C:/LumenGov",
    "C:/LumenLab",
    "C:/LumaSniper",
    "C:/LumaLive",
    "C:/LumaTraderV2",
    "C:/LumenCoreTrader",
    "C:/LumenCoreResearch",
    "C:/LumenCore_Energy_Lab",
    "C:/LumenCore_WorldModel_Lab",
    "C:/FLOWFORM_TOURNAMENT",
    str(Path.home() / "iCloudDrive"),
    str(Path.home() / "OneDrive"),
    str(Path.home() / "Google Drive"),
    str(Path.home() / "GoogleDrive"),
    str(Path.home() / "My Drive"),
    str(Path.home()),
]

SKIP_DIR_NAMES = {
    ".git",
    ".hg",
    ".svn",
    "__pycache__",
    "node_modules",
    ".venv",
    "venv",
    "venv3.11",
    "env",
    "env311",
    ".mypy_cache",
    ".pytest_cache",
    ".cache",
    ".next",
    "dist",
    "build",
    ".idea",
    ".vs",
}

SKIP_DIR_PREFIXES = (
    "$recycle.bin",
    "system volume information",
)

SKIP_HEAVY_UNDER_USER = {
    ".cagent",
    ".config",
    ".copilot",
    ".docker",
    ".matplotlib",
    ".vscode",
    ".vscode-shared",
    "appdata",
    "application data",
    "local settings",
    "nethood",
    "printhood",
    "recent",
    "sendto",
    "start menu",
    "templates",
    "cookies",
    "searches",
}

SKIP_FILE_PREFIXES = (
    "ntuser.dat",
    "ntuser.ini",
)

DATA_EXT = {
    ".csv",
    ".json",
    ".jsonl",
    ".parquet",
    ".feather",
    ".xlsx",
    ".xls",
    ".duckdb",
    ".db",
    ".sqlite",
    ".tsv",
    ".txt",
}

SCRIPT_EXT = {
    ".py",
    ".ps1",
    ".sh",
    ".bat",
    ".cmd",
    ".js",
    ".ts",
    ".tsx",
    ".ipynb",
    ".sql",
}

DASHBOARD_EXT = {".html", ".htm", ".css"}

DOCUMENT_EXT = {".pdf", ".docx", ".doc", ".ppt", ".pptx", ".md"}

PROOF_KEYWORDS = [
    "proof",
    "evidence",
    "audit",
    "ledger",
    "sha256",
    "chain_of_custody",
    "frozen_delta",
    "txid",
    "truth",
]

BUSINESS_KEYWORDS = [
    "patent",
    "uspto",
    "grant",
    "sbir",
    "darpa",
    "doe",
    "dod",
    "cage",
    "uei",
    "ein",
    "proposal",
    "investor",
    "pitch",
    "business",
    "licensing",
]


def now_utc() -> str:
    return datetime.now(timezone.utc).isoformat()


def normalize_path(path: Path) -> str:
    return path.as_posix()


def read_sha256(path: Path, chunk_size: int = 1024 * 1024) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as f:
        while True:
            chunk = f.read(chunk_size)
            if not chunk:
                break
            digest.update(chunk)
    return digest.hexdigest()


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")


def resolve_requested_roots(requested: Iterable[str]) -> List[Dict[str, Any]]:
    resolved: List[Dict[str, Any]] = []
    seen: Set[str] = set()
    for raw in requested:
        req = Path(raw)
        candidate = req
        alias_from = None
        exists = candidate.exists()

        # Fallback: if C:/Name is missing, check the current user's home directory.
        parts = req.parts
        if not exists and len(parts) == 2 and parts[0].lower().startswith("c:\\"):
            fallback = Path.home() / parts[1]
            if fallback.exists():
                candidate = fallback
                exists = True
                alias_from = normalize_path(req)

        key = normalize_path(candidate if exists else req)
        if key in seen:
            continue
        seen.add(key)

        resolved.append(
            {
                "requested": normalize_path(req),
                "resolved": normalize_path(candidate if exists else req),
                "exists": bool(exists),
                "alias_from": alias_from,
            }
        )
    return resolved


def _root_priority(path_str: str) -> Tuple[int, str]:
    p = path_str.lower().replace("\\", "/").rstrip("/")
    if p == USER_HOME_NORMALIZED:
        return (900, p)
    if "iclouddrive" in p or "onedrive" in p or "google drive" in p or "googledrive" in p:
        return (700, p)
    if p.startswith("c:/lumatrader") or p.startswith("c:/whitehole") or p.startswith("c:/whiteholelab"):
        return (100, p)
    return (300, p)


def prioritize_roots(resolved_roots: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    return sorted(resolved_roots, key=lambda r: _root_priority(str(r.get("resolved") or r.get("requested") or "")))


def should_skip_dir(root_resolved: str, dir_name: str) -> bool:
    name = dir_name.lower()
    if name in SKIP_DIR_NAMES:
        return True
    if any(name.startswith(prefix) for prefix in SKIP_DIR_PREFIXES):
        return True
    normalized_root = root_resolved.lower().replace("\\", "/").rstrip("/")
    if normalized_root == USER_HOME_NORMALIZED and name in SKIP_HEAVY_UNDER_USER:
        return True
    return False


def classify_categories(path_str_lower: str, ext: str) -> List[str]:
    categories: Set[str] = set()

    if ext in DASHBOARD_EXT or "dashboard" in path_str_lower or "command_room" in path_str_lower or "holo" in path_str_lower:
        categories.add("dashboard")
    if ext in SCRIPT_EXT:
        categories.add("script")
    if ext in DATA_EXT:
        categories.add("dataset")
    if ext in DOCUMENT_EXT:
        categories.add("document")
    if "unity" in path_str_lower or ext in {".unity", ".prefab", ".asset"}:
        categories.add("unity_xr_asset")

    if any(k in path_str_lower for k in PROOF_KEYWORDS):
        categories.add("proof_artifact")

    if any(k in path_str_lower for k in BUSINESS_KEYWORDS):
        categories.add("patent_grant_business_doc")

    if not categories:
        categories.add("other")

    return sorted(categories)


def keyword_in_path(path_str_lower: str, keyword: str) -> bool:
    kw = keyword.lower().strip()
    if not kw:
        return False
    if len(kw) >= 4:
        return kw in path_str_lower

    # For very short tokens, require token-like boundaries to avoid broad substring noise.
    tokenized = re.sub(r"[^a-z0-9]+", "/", path_str_lower)
    return f"/{kw}/" in f"/{tokenized}/"


def classify_engines(path_str_lower: str) -> List[str]:
    matches: List[str] = []
    for engine in ENGINE_DEFINITIONS:
        if any(keyword_in_path(path_str_lower, keyword) for keyword in engine["keywords"]):
            matches.append(engine["engine_id"])
    return sorted(set(matches))


def _is_subpath(child: Path, parent: Path) -> bool:
    try:
        child.resolve().relative_to(parent.resolve())
        return True
    except Exception:
        return False


def scan_roots(
    resolved_roots: List[Dict[str, Any]],
    max_files: int,
    per_root_max_files: int,
    hash_limit_bytes: int,
    max_hash_files: int,
) -> Dict[str, Any]:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    csv_path = OUT_DIR / "lumencore_universe_assets.csv"

    category_counts: Counter[str] = Counter()
    engine_counts: Counter[str] = Counter()
    extension_counts: Counter[str] = Counter()
    root_counts: Counter[str] = Counter()
    total_size_bytes = 0
    files_scanned = 0
    skipped_by_cap = False
    hash_budget_exhausted = False
    hashed_files = 0

    category_samples: Dict[str, List[str]] = defaultdict(list)
    engine_samples: Dict[str, List[str]] = defaultdict(list)
    proof_manifest: List[Dict[str, Any]] = []
    scanned_root_paths: List[Path] = []

    with csv_path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(
            [
                "path",
                "root",
                "size_bytes",
                "mtime_utc",
                "extension",
                "categories",
                "engines",
                "sha256",
            ]
        )

        for root_meta in resolved_roots:
            if not root_meta["exists"]:
                continue
            root_path = Path(root_meta["resolved"])
            root_key = normalize_path(root_path)
            root_files_scanned = 0
            root_scan_capped = False

            # Avoid duplicate work: if a parent root is already scanned, this root is already covered.
            if any(_is_subpath(root_path, parent) for parent in scanned_root_paths):
                root_meta["scan_included"] = False
                root_meta["covered_by_parent"] = True
                continue

            root_meta["scan_included"] = True
            root_meta["covered_by_parent"] = False
            scanned_root_paths.append(root_path)

            for current_root, dirs, files in os.walk(root_path, topdown=True):
                dirs[:] = [d for d in dirs if not should_skip_dir(root_key, d)]

                for name in files:
                    if any(name.lower().startswith(prefix) for prefix in SKIP_FILE_PREFIXES):
                        continue
                    path = Path(current_root) / name
                    path_str = normalize_path(path)
                    path_lower = path_str.lower()

                    try:
                        stat = path.stat()
                    except OSError:
                        continue

                    ext = path.suffix.lower()
                    categories = classify_categories(path_lower, ext)
                    engines = classify_engines(path_lower)

                    digest = ""
                    critical = "proof_artifact" in categories or "patent_grant_business_doc" in categories
                    if critical and stat.st_size <= hash_limit_bytes and hashed_files < max_hash_files:
                        try:
                            digest = read_sha256(path)
                            hashed_files += 1
                        except OSError:
                            digest = ""
                    elif critical and hashed_files >= max_hash_files:
                        hash_budget_exhausted = True

                    writer.writerow(
                        [
                            path_str,
                            root_key,
                            stat.st_size,
                            datetime.fromtimestamp(stat.st_mtime, timezone.utc).isoformat(),
                            ext,
                            ";".join(categories),
                            ";".join(engines),
                            digest,
                        ]
                    )

                    files_scanned += 1
                    root_files_scanned += 1
                    total_size_bytes += stat.st_size
                    root_counts[root_key] += 1
                    extension_counts[ext or "<none>"] += 1

                    for c in categories:
                        category_counts[c] += 1
                        if len(category_samples[c]) < 80:
                            category_samples[c].append(path_str)

                    for e in engines:
                        engine_counts[e] += 1
                        if len(engine_samples[e]) < 50:
                            engine_samples[e].append(path_str)

                    if digest:
                        proof_manifest.append(
                            {
                                "path": path_str,
                                "sha256": digest,
                                "size_bytes": stat.st_size,
                                "mtime_utc": datetime.fromtimestamp(stat.st_mtime, timezone.utc).isoformat(),
                            }
                        )

                    if files_scanned >= max_files:
                        skipped_by_cap = True
                        break

                    if root_files_scanned >= per_root_max_files:
                        root_scan_capped = True
                        break

                if skipped_by_cap:
                    break

                if root_scan_capped:
                    break

            if root_scan_capped:
                root_meta["root_scan_capped"] = True
            else:
                root_meta["root_scan_capped"] = False

            if skipped_by_cap:
                break

    return {
        "csv_path": normalize_path(csv_path),
        "files_scanned": files_scanned,
        "total_size_bytes": total_size_bytes,
        "root_counts": dict(root_counts),
        "category_counts": dict(category_counts),
        "engine_counts": dict(engine_counts),
        "extension_counts_top": dict(extension_counts.most_common(60)),
        "category_samples": dict(category_samples),
        "engine_samples": dict(engine_samples),
        "proof_manifest": proof_manifest,
        "hashed_files": hashed_files,
        "max_hash_files": max_hash_files,
        "hash_budget_exhausted": hash_budget_exhausted,
        "scan_capped": skipped_by_cap,
        "scan_cap": max_files,
    }


def build_engine_table(engine_counts: Dict[str, int], engine_samples: Dict[str, List[str]]) -> List[Dict[str, Any]]:
    by_id = {e["engine_id"]: e for e in ENGINE_DEFINITIONS}
    rows: List[Dict[str, Any]] = []
    for engine in ENGINE_DEFINITIONS:
        engine_id = engine["engine_id"]
        rows.append(
            {
                "engine_id": engine_id,
                "name": engine["name"],
                "purpose": engine["purpose"],
                "product_form": engine["product_form"],
                "licensing_target": engine["licensing_target"],
                "asset_hits": int(engine_counts.get(engine_id, 0)),
                "sample_assets": list(engine_samples.get(engine_id, []))[:12],
            }
        )

    # Include any extra IDs detected unexpectedly.
    for extra_id, count in sorted(engine_counts.items()):
        if extra_id not in by_id:
            rows.append(
                {
                    "engine_id": extra_id,
                    "name": extra_id,
                    "purpose": "Detected by keyword scan",
                    "product_form": "Unmapped",
                    "licensing_target": "Unmapped",
                    "asset_hits": int(count),
                    "sample_assets": list(engine_samples.get(extra_id, []))[:8],
                }
            )

    return rows


def render_markdown(payload: Dict[str, Any]) -> str:
    lines: List[str] = []
    lines.append("# LumenCore Universe Memory Map")
    lines.append("")
    lines.append(f"Generated UTC: {payload['generated_utc']}")
    lines.append("")

    lines.append("## Founder and Readiness Identifiers")
    for k, v in payload["founder_profile"].items():
        if isinstance(v, list):
            lines.append(f"- {k}: {', '.join(str(x) for x in v)}")
        else:
            lines.append(f"- {k}: {v}")
    lines.append("")

    lines.append("## Shared Kernel Architecture")
    for item in payload["kernel_architecture"]:
        lines.append(f"- {item}")
    lines.append("")

    lines.append("## Root Coverage")
    for root in payload["roots"]:
        status = "present" if root["exists"] else "missing"
        alias = f" (alias of {root['alias_from']})" if root.get("alias_from") else ""
        lines.append(f"- {root['requested']} -> {root['resolved']} [{status}]{alias}")
    lines.append("")

    scan = payload["scan"]
    lines.append("## Scan Totals")
    lines.append(f"- Files indexed: {scan['files_scanned']}")
    lines.append(f"- Total bytes indexed: {scan['total_size_bytes']}")
    lines.append(f"- Scan cap hit: {scan['scan_capped']}")
    lines.append(f"- Searchable asset CSV: {payload['artifacts']['assets_csv']}")
    lines.append("")

    lines.append("## Artifact Category Counts")
    for name, count in sorted(scan["category_counts"].items(), key=lambda x: (-x[1], x[0])):
        lines.append(f"- {name}: {count}")
    lines.append("")

    lines.append("## Engine Product Lines")
    for row in payload["engine_map"]:
        lines.append(f"### {row['name']}")
        lines.append(f"- Engine ID: {row['engine_id']}")
        lines.append(f"- Purpose: {row['purpose']}")
        lines.append(f"- Product form: {row['product_form']}")
        lines.append(f"- Licensing target: {row['licensing_target']}")
        lines.append(f"- Indexed asset hits: {row['asset_hits']}")
        if row["sample_assets"]:
            lines.append("- Sample assets:")
            for p in row["sample_assets"][:5]:
                lines.append(f"  - {p}")
        lines.append("")

    lines.append("## Chain of Custody")
    lines.append("- Raw files were not modified or deleted.")
    lines.append("- This map was generated into new snapshot artifacts only.")
    lines.append("- SHA256 hashes were computed for proof and business-critical artifacts under scan limits.")
    lines.append("")

    return "\n".join(lines).strip() + "\n"


def append_history(path: Path, payload: Dict[str, Any]) -> None:
    row = {
        "generated_utc": payload["generated_utc"],
        "files_scanned": payload["scan"]["files_scanned"],
        "total_size_bytes": payload["scan"]["total_size_bytes"],
        "scan_capped": payload["scan"]["scan_capped"],
        "roots_present": sum(1 for r in payload["roots"] if r["exists"]),
        "roots_missing": sum(1 for r in payload["roots"] if not r["exists"]),
        "category_counts": payload["scan"]["category_counts"],
        "top_engine_hits": sorted(
            ({"engine_id": k, "asset_hits": v} for k, v in payload["scan"]["engine_counts"].items()),
            key=lambda x: x["asset_hits"],
            reverse=True,
        )[:12],
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(row, ensure_ascii=False) + "\n")


def main() -> None:
    parser = argparse.ArgumentParser(description="Build searchable LumenCore and NovaCore universe memory map.")
    parser.add_argument("--max-files", type=int, default=300000, help="Maximum number of files to index.")
    parser.add_argument("--per-root-max-files", type=int, default=50000, help="Maximum files to index per root.")
    parser.add_argument("--hash-limit-mb", type=int, default=25, help="Hash only files at or below this size in MB.")
    parser.add_argument("--max-hash-files", type=int, default=3000, help="Maximum number of critical files to hash.")
    parser.add_argument("--roots", nargs="*", default=None, help="Optional explicit root list; overrides built-in roots.")
    args = parser.parse_args()

    generated_utc = now_utc()
    requested_roots = args.roots if args.roots else ROOT_REQUESTED
    resolved_roots = prioritize_roots(resolve_requested_roots(requested_roots))

    scan = scan_roots(
        resolved_roots=resolved_roots,
        max_files=max(1, args.max_files),
        per_root_max_files=max(1, args.per_root_max_files),
        hash_limit_bytes=max(1, args.hash_limit_mb) * 1024 * 1024,
        max_hash_files=max(1, args.max_hash_files),
    )

    engine_map = build_engine_table(scan["engine_counts"], scan["engine_samples"])

    payload = {
        "generated_utc": generated_utc,
        "schema": "lumencore_universe_memory_map_v1",
        "objective": "Company-grade searchable memory map for the LumenCore and NovaCore engine universe.",
        "founder_profile": FOUNDER_PROFILE,
        "kernel_architecture": KERNEL_ARCHITECTURE,
        "roots": resolved_roots,
        "scan": scan,
        "engine_map": engine_map,
        "safeguards": {
            "raw_data_mutated": False,
            "raw_data_deleted": False,
            "snapshot_only_output": True,
            "chain_of_custody": "sha256_manifest_for_critical_artifacts",
        },
        "artifacts": {},
    }

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    json_path = OUT_DIR / "lumencore_universe_map.json"
    md_path = OUT_DIR / "lumencore_universe_map.md"
    hash_path = OUT_DIR / "lumencore_universe_map_sha256.json"
    history_path = OUT_DIR / "lumencore_universe_map_history.jsonl"

    payload["artifacts"] = {
        "json": normalize_path(json_path),
        "markdown": normalize_path(md_path),
        "assets_csv": scan["csv_path"],
        "sha256": normalize_path(hash_path),
        "history": normalize_path(history_path),
    }

    write_json(json_path, payload)
    md_path.write_text(render_markdown(payload), encoding="utf-8")

    hash_payload = {
        "generated_utc": generated_utc,
        "files": {
            normalize_path(json_path): read_sha256(json_path),
            normalize_path(md_path): read_sha256(md_path),
            normalize_path(Path(scan["csv_path"])): read_sha256(Path(scan["csv_path"])),
        },
        "critical_manifest_count": len(scan["proof_manifest"]),
        "critical_manifest": scan["proof_manifest"],
    }
    write_json(hash_path, hash_payload)

    append_history(history_path, payload)

    print(normalize_path(json_path))
    print(normalize_path(md_path))
    print(scan["csv_path"])
    print(normalize_path(hash_path))
    print(normalize_path(history_path))


if __name__ == "__main__":
    main()
