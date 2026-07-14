from __future__ import annotations

import argparse
import csv
import hashlib
import json
import ntpath
import os
import re
import shutil
import sqlite3
import stat
import subprocess
import uuid
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable, Iterator

ROOT = Path(__file__).resolve().parents[2]
SPRINT_DIR = ROOT / "grant_submissions" / "funding_sprint_20260709"
OUT_OPS = ROOT / "out" / "ops"
DASHBOARD_DATA = ROOT / "dashboard" / "data"
RUN_DATE = datetime.now(timezone.utc).date().isoformat()

OUT_JSON = OUT_OPS / "lumencore_estate_master_index_latest.json"
DASHBOARD_JSON = DASHBOARD_DATA / "lumencore_estate_master_index.json"
OUT_MD = SPRINT_DIR / f"LUMENCORE_ESTATE_MASTER_INDEX_{RUN_DATE}.md"
OUT_CSV = OUT_OPS / "lumencore_estate_file_inventory_latest.csv"
OUT_MANIFEST = OUT_OPS / "lumencore_estate_master_index_manifest_latest.json"

PRIVATE_UNIVERSE_DIR = Path(r"E:\LumaProofVault\PRIVATE_CONTEXT\ESTATE_INDEX")
PRIVATE_UNIVERSE_DB_NAME = "lumencore_private_universe_latest.sqlite3"
PRIVATE_UNIVERSE_RECEIPT_NAME = "lumencore_private_universe_receipt_latest.json"
PRIVATE_UNIVERSE_HISTORY_DIR_NAME = "history"
PRIVATE_UNIVERSE_MIN_FREE_PERCENT = 10.0
PRIVATE_UNIVERSE_LOCK_NAME = ".lumencore_private_universe.lock"
PRIVATE_UNIVERSE_ABSOLUTE_RESERVE_BYTES = 2 * 1024 * 1024 * 1024
PRIVATE_UNIVERSE_DB_ESTIMATE_MULTIPLIER = 4
PRIVATE_UNIVERSE_MIN_ESTIMATED_DB_BYTES = 64 * 1024 * 1024
PRIVATE_UNIVERSE_PUBLIC_RECEIPT = (
    OUT_OPS / "lumencore_private_universe_receipt_latest.json"
)
PRIVATE_UNIVERSE_DASHBOARD_RECEIPT = (
    DASHBOARD_DATA / "lumencore_private_universe_receipt.json"
)

DEFAULT_PRIVATE_UNIVERSE_SOURCES = {
    "scientific_index": Path(
        r"C:\LumaUniverse\SCIENTIFIC_INDEX_20260617T111231Z\index\all_files.csv"
    ),
    "fast_index": Path(
        r"C:\LumaUniverse\FAST_INDEX_20260617T115224Z\index\all_files_fast.csv"
    ),
    "canonical_estate_inventory": OUT_CSV,
    "curated_local_icloud_intake": OUT_OPS / "local_icloud_evidence_intake_latest.json",
    "root_registry": ROOT / "data" / "root_registry" / "MASTER_ROOT_REGISTRY.json",
}

PRIVATE_SOURCE_PRIORITIES = {
    "fast_index": 100,
    "scientific_index": 200,
    "curated_local_icloud_intake": 300,
    "canonical_estate_inventory": 400,
    "explicit_user_supplied_current_file": 500,
}

PUBLIC_ROOT_ROLE_ALLOWLIST = {
    "ACTIVE_ENGINE",
    "ACTIVE_LAB",
    "ARCHIVE_PROOF",
    "FEEDER_DATA",
    "LEGACY_DO_NOT_RUN",
    "UNCLASSIFIED",
}

ARCHIVE_EXTENSIONS = {".zip", ".tar", ".tgz", ".gz", ".7z", ".rar", ".bz2", ".xz"}

UNSAFE_WINDOWS_INPUT_ATTRIBUTE_MASK = (
    getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0x00000400)
    | getattr(stat, "FILE_ATTRIBUTE_OFFLINE", 0x00001000)
    | getattr(stat, "FILE_ATTRIBUTE_RECALL_ON_OPEN", 0x00040000)
    | getattr(stat, "FILE_ATTRIBUTE_RECALL_ON_DATA_ACCESS", 0x00400000)
)

PRIVATE_LANE_RULES: dict[str, tuple[str, ...]] = {
    "hybrid_routing": (
        "hybrid",
        "routing",
        "router",
        "orchestrator",
        "agent_mesh",
        "model_route",
        "mixture_of_experts",
    ),
    "hardware_geometry": (
        "hardware",
        "geometry",
        "mechanical",
        "prototype",
        "fixture",
        "enclosure",
        "cad",
        "solidworks",
        "fusion360",
    ),
    "additive_manufacturing_3d": (
        "3d_print",
        "3dprinter",
        "3d_printer",
        "additive",
        "filament",
        "gcode",
        "slicer",
        "cura",
        "prusa",
        "marlin",
        ".stl",
        ".3mf",
        ".obj",
        ".step",
        ".stp",
    ),
    "field_work_evidence": (
        "field_work",
        "fieldwork",
        "site_visit",
        "onsite",
        "installation",
        "commissioning",
        "inspection",
        "maintenance_log",
        "repair_log",
        "fabrication_log",
    ),
    "computer_health_measurement": (
        "computer_health",
        "system_health",
        "watchdog",
        "telemetry",
        "diagnostic",
        "performance_counter",
        "cpu_usage",
        "memory_usage",
        "disk_health",
        "battery_health",
        "event_log",
    ),
    "media_documentation": (
        ".png",
        ".jpg",
        ".jpeg",
        ".gif",
        ".webp",
        ".heic",
        ".svg",
        ".mp4",
        ".mov",
        ".avi",
        ".wav",
        ".mp3",
        ".pdf",
        ".docx",
        ".pptx",
    ),
    "proof": (
        "proof",
        "evidence",
        "audit",
        "receipt",
        "manifest",
        "chain_of_custody",
        "sha256",
        "validation",
        "benchmark",
    ),
    "funding": (
        "grant",
        "funding",
        "sbir",
        "sttr",
        "rfi",
        "baa",
        "cso",
        "nasa",
        "nsf",
        "darpa",
        "doe",
        "agency",
    ),
    "software": (
        ".py",
        ".ps1",
        ".sh",
        ".js",
        ".ts",
        ".tsx",
        ".jsx",
        ".java",
        ".go",
        ".rs",
        ".cs",
        ".cpp",
        ".c",
        ".h",
        ".sql",
        ".ipynb",
    ),
}

MAX_CONTENT_HASH_BYTES = 50 * 1024 * 1024

SKIP_DIR_NAMES = {
    ".git",
    ".hg",
    ".svn",
    ".venv",
    "venv",
    "env311",
    "node_modules",
    "__pycache__",
    ".pytest_cache",
    ".mypy_cache",
    ".ruff_cache",
    ".cache",
}

SENSITIVE_NAME_TOKENS = (
    ".env",
    "secret",
    "credential",
    "credentials",
    "token",
    "private_key",
    "apikey",
    "api_key",
    "auth",
    "oauth",
    "password",
    "passwd",
)

SENSITIVE_MARKERS = [
    "zoom.us",
    "meeting id",
    "password",
    "one tap mobile",
    "private key",
    "refresh_token",
    "client_secret",
    "api_key",
    "sk-",
    "xox",
]

CONCEPT_RULES: dict[str, tuple[str, ...]] = {
    "agency_protocol": (
        "sam",
        "sbir",
        "sttr",
        "darpa",
        "nsf",
        "nasa",
        "fhwa",
        "erdc",
        "bop",
        "dod",
        "grant",
        "rfi",
        "cso",
        "baa",
        "federal",
    ),
    "proof_stack": (
        "proof",
        "evidence",
        "audit",
        "hash",
        "sha256",
        "manifest",
        "ledger",
        "gate",
        "reviewer",
        "validation",
    ),
    "ip_patent": (
        "ip",
        "patent",
        "uspto",
        "claim",
        "invention",
        "counsel",
        "provisional",
        "nonprovisional",
    ),
    "quant_trading": (
        "quant",
        "trading",
        "kraken",
        "alpaca",
        "paper",
        "sharpe",
        "edge",
        "order",
        "execution",
    ),
    "geometry_engine": (
        "geometry",
        "kuramoto",
        "brachistochrone",
        "flowform",
        "harmonic",
        "phase",
        "resonance",
        "champion",
    ),
    "live_source": (
        "live",
        "source",
        "eia",
        "faa",
        "noaa",
        "nasa",
        "weather",
        "ais",
        "harbor",
        "breadth",
    ),
    "revenue_pilot": (
        "revenue",
        "pilot",
        "customer",
        "commercial",
        "valuation",
        "paid",
        "buyer",
        "outreach",
    ),
    "dashboard_ops": (
        "dashboard",
        "mission",
        "control",
        "panel",
        "frontend",
        "site",
        "html",
    ),
    "infrastructure_energy": (
        "grid",
        "energy",
        "nuclear",
        "utility",
        "infrastructure",
        "datacenter",
        "cooling",
    ),
    "luma_scout": ("lumascout", "scout", "youtube", "spotify", "facebook", "creator"),
    "dice": ("dice", "darpa"),
    "missionweave": ("missionweave", "dla26bz03", "nv011"),
    "harbor_sentinel": ("harbor", "sentinel", "ais", "nv063"),
    "luma_jet_skin_suity": ("lumajet", "luma jet", "skin", "suity"),
}

NAMED_CONCEPTS = [
    {
        "concept_id": "proof_to_pilot_os",
        "name": "Proof-to-pilot evidence operating system",
        "estate_role": "core_invention_and_funding_spine",
        "safe_description": "Turns source, baseline, candidate, metric, hash, reviewer, and claim-boundary records into reviewable proof packets.",
        "public_boundary": "No agency validation, field validation, realized savings, or patent grant claim without the relevant human gate.",
    },
    {
        "concept_id": "agency_protocol_stack",
        "name": "Agency and government protocol readiness stack",
        "estate_role": "funding_and_contract_access_layer",
        "safe_description": "Maps SAM, SBIR, RFI, BAA, and CSO opportunities into human-gated response packets.",
        "public_boundary": "No final submit, reps/certs, price, or signature without human approval.",
    },
    {
        "concept_id": "autonomous_quant_replay_lab",
        "name": "Autonomous quant replay lab",
        "estate_role": "noisy_market_stress_test_layer",
        "safe_description": "Uses market and live-source noise for replay, paper evaluation, and proof hardening.",
        "public_boundary": "No live trading, public performance claim, or capital movement without explicit human runtime approval.",
    },
    {
        "concept_id": "geometry_champion_engine",
        "name": "Geometry champion and live-source validation engine",
        "estate_role": "technical_alpha_and_cross_sector_evidence_layer",
        "safe_description": "Ranks geometry/control families against baselines under frozen replay and holdout constraints.",
        "public_boundary": "Internal evidence supports field-replay requests; it is not external field validation by itself.",
    },
    {
        "concept_id": "ip_claim_boundary_estate",
        "name": "IP claim-boundary estate",
        "estate_role": "invention_preservation_and_counsel_route",
        "safe_description": "Preserves invention families, public disclosure rules, hold-back areas, and counsel questions.",
        "public_boundary": "Licensed counsel controls claim charts, filings, deadlines, and legal conclusions.",
    },
    {
        "concept_id": "luma_jet_skin_suity_lane",
        "name": "Luma Jet / Skin / Suity concept lane",
        "estate_role": "emerging_product_family",
        "safe_description": "Held as named concept territory for future structured evidence, source, and IP mapping.",
        "public_boundary": "Concept naming alone is not proof of technical readiness, market validation, or patent support.",
    },
]


def now_utc() -> str:
    return datetime.now(timezone.utc).isoformat()


def rel(path: Path) -> str:
    try:
        return path.relative_to(ROOT).as_posix()
    except ValueError:
        return str(path)


def stable_sha256(payload: Any) -> str:
    return hashlib.sha256(
        json.dumps(payload, sort_keys=True, default=str).encode("utf-8")
    ).hexdigest()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def load_previous_inventory() -> dict[str, dict[str, str]]:
    if not OUT_CSV.exists():
        return {}
    try:
        with OUT_CSV.open(newline="", encoding="utf-8") as handle:
            return {
                row["relative_path"]: row
                for row in csv.DictReader(handle)
                if row.get("relative_path")
            }
    except (OSError, csv.Error, KeyError):
        return {}


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, indent=2, sort_keys=True, default=str) + "\n",
        encoding="utf-8",
    )


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text.rstrip("\r\n") + "\n", encoding="utf-8")


def inventory_chain_sha256(rows: list[dict[str, Any]]) -> str:
    digest = hashlib.sha256()
    for row in sorted(rows, key=lambda item: str(item["relative_path"]).lower()):
        custody_hash = row["content_sha256"] or row["metadata_sha256"]
        record = {
            "relative_path": row["relative_path"],
            "size_bytes": row["size_bytes"],
            "hash_mode": row["hash_mode"],
            "custody_sha256": custody_hash,
        }
        digest.update(
            json.dumps(record, sort_keys=True, separators=(",", ":")).encode("utf-8")
        )
        digest.update(b"\n")
    return digest.hexdigest()


def output_manifest(payload: dict[str, Any]) -> dict[str, Any]:
    files = {}
    for path in (OUT_JSON, DASHBOARD_JSON, OUT_MD, OUT_CSV):
        files[rel(path)] = {
            "size_bytes": path.stat().st_size,
            "sha256": sha256_file(path),
        }
    manifest = {
        "schema": "lumencore_estate_output_manifest_v1",
        "generated_utc": now_utc(),
        "estate_index_sha256": payload["estate_index_sha256"],
        "inventory_chain_sha256": payload["summary"]["inventory_chain_sha256"],
        "files": files,
        "self_reference_excluded": True,
    }
    manifest["manifest_sha256"] = stable_sha256(manifest)
    return manifest


def is_sensitive_path(relative_path: str) -> bool:
    lowered = relative_path.lower()
    return any(token in lowered for token in SENSITIVE_NAME_TOKENS)


def should_skip_dir(dirname: str) -> bool:
    return dirname.lower() in SKIP_DIR_NAMES


def asset_class(path: Path, relative_path: str) -> str:
    lowered = relative_path.lower()
    ext = path.suffix.lower()
    if is_sensitive_path(relative_path):
        return "restricted_sensitive_metadata"
    if "grant_submissions/" in lowered or "funding_sprint" in lowered:
        return "funding_submission_artifact"
    if "/docs/" in f"/{lowered}" or ext in {".md", ".pdf", ".docx", ".pptx"}:
        return "document_or_review_packet"
    if "/dashboard/" in f"/{lowered}" or ext in {".html", ".css", ".js"}:
        return "dashboard_or_frontend"
    if "/code/" in f"/{lowered}" or ext in {
        ".py",
        ".ps1",
        ".sh",
        ".ts",
        ".js",
        ".yml",
        ".yaml",
        ".toml",
    }:
        return "source_code_or_automation"
    if "/out/" in f"/{lowered}" or "ledger" in lowered:
        return "machine_output_or_ledger"
    if "/data/" in f"/{lowered}" or ext in {
        ".csv",
        ".jsonl",
        ".parquet",
        ".xlsx",
        ".txt",
    }:
        return "data_asset"
    if ext in {".png", ".jpg", ".jpeg", ".gif", ".webp", ".heic", ".svg"}:
        return "visual_media_asset"
    if ext in {".zip", ".tgz", ".tar", ".gz", ".7z"}:
        return "archive_asset"
    if ext in {".json"}:
        return "structured_state_or_config"
    return "working_material"


def concept_tags(relative_path: str) -> list[str]:
    lowered = relative_path.lower().replace("\\", "/")
    tags = []
    for concept, tokens in CONCEPT_RULES.items():
        if any(token in lowered for token in tokens):
            tags.append(concept)
    return sorted(set(tags))


def custody_tier(relative_path: str, cls: str, size_bytes: int) -> str:
    lowered = relative_path.lower()
    if is_sensitive_path(relative_path):
        return "restricted_private_metadata_only"
    if size_bytes > MAX_CONTENT_HASH_BYTES:
        return "large_asset_metadata_hash_content_hash_deferred"
    if cls in {
        "funding_submission_artifact",
        "document_or_review_packet",
    } and lowered.endswith((".md", ".pdf", ".pptx", ".docx")):
        return "reviewer_packet_public_safe_after_human_review"
    if cls == "source_code_or_automation":
        return "source_code_audit_ready"
    if cls == "data_asset":
        return "data_asset_hash_backed"
    if cls == "machine_output_or_ledger":
        return "machine_receipt_hash_backed"
    return "estate_inventory_hash_backed"


def hash_mode(relative_path: str, size_bytes: int) -> str:
    if is_sensitive_path(relative_path):
        return "metadata_hash_only_sensitive_path"
    if size_bytes > MAX_CONTENT_HASH_BYTES:
        return "metadata_hash_only_large_file"
    return "content_sha256"


def file_row(path: Path, previous: dict[str, str] | None = None) -> dict[str, Any]:
    stat = path.stat()
    relative_path = rel(path)
    cls = asset_class(path, relative_path)
    mode = hash_mode(relative_path, stat.st_size)
    modified_utc = datetime.fromtimestamp(stat.st_mtime, tz=timezone.utc).isoformat()
    metadata_hash = stable_sha256(
        {
            "relative_path": relative_path,
            "size_bytes": stat.st_size,
            "mtime_ns": stat.st_mtime_ns,
            "extension": path.suffix.lower(),
        }
    )
    can_reuse_content_hash = bool(
        previous
        and mode == "content_sha256"
        and previous.get("hash_mode") == mode
        and previous.get("size_bytes") == str(stat.st_size)
        and previous.get("modified_utc") == modified_utc
        and len(previous.get("content_sha256", "")) == 64
    )
    content_hash = (
        str(previous["content_sha256"])
        if can_reuse_content_hash and previous
        else sha256_file(path) if mode == "content_sha256" else ""
    )
    tags = concept_tags(relative_path)
    return {
        "relative_path": relative_path,
        "name": path.name,
        "extension": path.suffix.lower(),
        "size_bytes": stat.st_size,
        "modified_utc": modified_utc,
        "asset_class": cls,
        "custody_tier": custody_tier(relative_path, cls, stat.st_size),
        "concept_tags": ";".join(tags),
        "concept_tag_count": len(tags),
        "sensitive_path": is_sensitive_path(relative_path),
        "hash_mode": mode,
        "content_sha256": content_hash,
        "metadata_sha256": metadata_hash,
        "_content_hash_reused": can_reuse_content_hash,
    }


def iter_files() -> list[Path]:
    files: list[Path] = []
    generated_outputs = {OUT_JSON, DASHBOARD_JSON, OUT_MD, OUT_CSV, OUT_MANIFEST}
    for current_root, dirnames, filenames in os.walk(ROOT):
        dirnames[:] = [dirname for dirname in dirnames if not should_skip_dir(dirname)]
        root_path = Path(current_root)
        for filename in filenames:
            path = root_path / filename
            if path in generated_outputs:
                continue
            files.append(path)
    return sorted(files, key=lambda item: rel(item).lower())


def write_inventory_csv(rows: list[dict[str, Any]]) -> None:
    OUT_CSV.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = [
        "relative_path",
        "name",
        "extension",
        "size_bytes",
        "modified_utc",
        "asset_class",
        "custody_tier",
        "concept_tags",
        "concept_tag_count",
        "sensitive_path",
        "hash_mode",
        "content_sha256",
        "metadata_sha256",
    ]
    with OUT_CSV.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow({field: row[field] for field in fieldnames})


def build_payload() -> dict[str, Any]:
    rows: list[dict[str, Any]] = []
    scan_errors: list[dict[str, str]] = []
    previous_inventory = load_previous_inventory()
    for path in iter_files():
        try:
            relative_path = rel(path)
            rows.append(file_row(path, previous_inventory.get(relative_path)))
        except (FileNotFoundError, PermissionError, OSError) as exc:
            scan_errors.append(
                {
                    "relative_path": rel(path),
                    "error_type": type(exc).__name__,
                    "error": str(exc)[:300],
                }
            )
    write_inventory_csv(rows)

    asset_counts = Counter(row["asset_class"] for row in rows)
    custody_counts = Counter(row["custody_tier"] for row in rows)
    extension_counts = Counter(row["extension"] or "[none]" for row in rows)
    hash_mode_counts = Counter(row["hash_mode"] for row in rows)
    reused_content_hash_count = sum(1 for row in rows if row["_content_hash_reused"])
    computed_content_hash_count = sum(
        1
        for row in rows
        if row["hash_mode"] == "content_sha256" and not row["_content_hash_reused"]
    )
    concept_counts: Counter[str] = Counter()
    concept_examples: dict[str, list[str]] = defaultdict(list)
    for row in rows:
        tags = [tag for tag in row["concept_tags"].split(";") if tag]
        for tag in tags:
            concept_counts[tag] += 1
            if not row["sensitive_path"] and len(concept_examples[tag]) < 8:
                concept_examples[tag].append(row["relative_path"])

    total_bytes = sum(int(row["size_bytes"]) for row in rows)
    sensitive = [row for row in rows if row["sensitive_path"]]
    largest = sorted(
        [row for row in rows if not row["sensitive_path"]],
        key=lambda row: int(row["size_bytes"]),
        reverse=True,
    )[:25]
    high_signal = [
        row
        for row in rows
        if not row["sensitive_path"]
        if row["asset_class"]
        in {
            "funding_submission_artifact",
            "document_or_review_packet",
            "source_code_or_automation",
            "machine_output_or_ledger",
        }
        and row["concept_tag_count"] >= 2
    ][:50]

    concept_registry = []
    for concept_id, count in sorted(
        concept_counts.items(), key=lambda item: (-item[1], item[0])
    ):
        concept_registry.append(
            {
                "concept_id": concept_id,
                "file_count": count,
                "example_paths": concept_examples[concept_id],
                "concept_sha256": stable_sha256(
                    {
                        "concept_id": concept_id,
                        "count": count,
                        "examples": concept_examples[concept_id],
                    }
                ),
            }
        )

    payload = {
        "schema": "lumencore_estate_master_index_v2",
        "generated_utc": now_utc(),
        "status": "LUMENCORE_ESTATE_MASTER_INDEX_READY",
        "summary": {
            "managed_file_count": len(rows),
            "managed_total_bytes": total_bytes,
            "asset_class_count": len(asset_counts),
            "custody_tier_count": len(custody_counts),
            "concept_tag_count": len(concept_counts),
            "named_concept_count": len(NAMED_CONCEPTS),
            "content_sha256_file_count": hash_mode_counts.get("content_sha256", 0),
            "content_sha256_reused_count": reused_content_hash_count,
            "content_sha256_computed_count": computed_content_hash_count,
            "large_file_deferred_content_hash_count": hash_mode_counts.get(
                "metadata_hash_only_large_file", 0
            ),
            "sensitive_metadata_only_count": hash_mode_counts.get(
                "metadata_hash_only_sensitive_path", 0
            ),
            "inventory_chain_sha256": inventory_chain_sha256(rows),
            "inventory_csv_sha256": sha256_file(OUT_CSV),
            "full_inventory_csv": rel(OUT_CSV),
            "full_inventory_csv_bytes": (
                OUT_CSV.stat().st_size if OUT_CSV.exists() else 0
            ),
            "scan_error_count": len(scan_errors),
            "public_safe_markdown": True,
            "secret_content_indexed": False,
            "sensitive_paths_redacted_from_public_payload": True,
            "generated_outputs_excluded_from_inventory": True,
            "final_submission_allowed_without_human": False,
            "legal_or_ip_action_allowed_without_human": False,
            "live_trading_allowed": False,
        },
        "asset_class_counts": dict(sorted(asset_counts.items())),
        "custody_tier_counts": dict(sorted(custody_counts.items())),
        "extension_counts_top": dict(extension_counts.most_common(30)),
        "hash_mode_counts": dict(sorted(hash_mode_counts.items())),
        "concept_registry": concept_registry,
        "named_concepts": NAMED_CONCEPTS,
        "largest_files": [
            {
                "relative_path": row["relative_path"],
                "size_bytes": row["size_bytes"],
                "asset_class": row["asset_class"],
                "hash_mode": row["hash_mode"],
                "metadata_sha256": row["metadata_sha256"],
            }
            for row in largest
        ],
        "sensitive_metadata_only_examples": [
            {
                "asset_class": row["asset_class"],
                "custody_tier": row["custody_tier"],
                "metadata_sha256": row["metadata_sha256"],
            }
            for row in sensitive[:25]
        ],
        "scan_error_examples": scan_errors[:25],
        "high_signal_estate_examples": [
            {
                "relative_path": row["relative_path"],
                "asset_class": row["asset_class"],
                "concept_tags": row["concept_tags"],
                "custody_tier": row["custody_tier"],
                "content_sha256": row["content_sha256"],
                "metadata_sha256": row["metadata_sha256"],
            }
            for row in high_signal
        ],
        "audit_rules": {
            "scope": "Managed workspace files under C:/LumaTrader/INSTITUTIONAL_STACK_V2 excluding git, dependency, cache, and bytecode internals.",
            "every_managed_file_inventory": True,
            "secret_contents_not_published": True,
            "sensitive_paths_metadata_only": True,
            "large_files_metadata_hash_until_dedicated_custody_pass": True,
            "reviewer_markdown_is_summary_only": True,
            "public_payload_redacts_sensitive_paths": True,
            "generated_outputs_excluded_to_prevent_self_reference": True,
            "full_inventory_csv_is_local_custody_artifact": True,
        },
        "outputs": {
            "json": rel(OUT_JSON),
            "dashboard_json": rel(DASHBOARD_JSON),
            "markdown": rel(OUT_MD),
            "full_inventory_csv": rel(OUT_CSV),
            "output_manifest": rel(OUT_MANIFEST),
        },
    }
    payload["estate_index_sha256"] = stable_sha256(payload)
    return payload


def render_markdown(payload: dict[str, Any]) -> str:
    summary = payload["summary"]
    lines = [
        f"# LumenCore Estate Master Index - {RUN_DATE}",
        "",
        "Purpose: make the LumenCore universe estate-grade by inventorying the managed workspace, classifying every managed file, connecting concept families to evidence lanes, and keeping sensitive material private.",
        "",
        "This is an audit and custody artifact. It does not claim a valuation, patent grant, agency approval, realized savings, field validation, live trading authority, or final submission authority.",
        "",
        "## Status",
        "",
        f"- Status: `{payload['status']}`",
        f"- Managed file count: `{summary['managed_file_count']}`",
        f"- Managed total bytes: `{summary['managed_total_bytes']}`",
        f"- Asset classes: `{summary['asset_class_count']}`",
        f"- Custody tiers: `{summary['custody_tier_count']}`",
        f"- Concept tags: `{summary['concept_tag_count']}`",
        f"- Named concepts: `{summary['named_concept_count']}`",
        f"- Content SHA-256 file count: `{summary['content_sha256_file_count']}`",
        f"- Reused unchanged content hashes: `{summary['content_sha256_reused_count']}`",
        f"- Computed new or changed content hashes: `{summary['content_sha256_computed_count']}`",
        f"- Large-file deferred content hashes: `{summary['large_file_deferred_content_hash_count']}`",
        f"- Sensitive metadata-only files: `{summary['sensitive_metadata_only_count']}`",
        f"- Inventory chain SHA-256: `{summary['inventory_chain_sha256']}`",
        f"- Inventory CSV SHA-256: `{summary['inventory_csv_sha256']}`",
        f"- Full inventory CSV: `{summary['full_inventory_csv']}`",
        f"- Full inventory CSV bytes: `{summary['full_inventory_csv_bytes']}`",
        f"- Scan errors recorded: `{summary['scan_error_count']}`",
        f"- Secret content indexed: `{str(summary['secret_content_indexed']).lower()}`",
        f"- Sensitive paths redacted from public payload: `{str(summary['sensitive_paths_redacted_from_public_payload']).lower()}`",
        f"- Generated outputs excluded from inventory: `{str(summary['generated_outputs_excluded_from_inventory']).lower()}`",
        f"- Final submission without human: `{str(summary['final_submission_allowed_without_human']).lower()}`",
        f"- Legal/IP action without human: `{str(summary['legal_or_ip_action_allowed_without_human']).lower()}`",
        f"- Live trading allowed: `{str(summary['live_trading_allowed']).lower()}`",
        f"- Estate index SHA-256: `{payload['estate_index_sha256']}`",
        "",
        "## Asset Classes",
        "",
    ]
    for key, value in payload["asset_class_counts"].items():
        lines.append(f"- `{key}`: `{value}`")
    lines.extend(["", "## Custody Tiers", ""])
    for key, value in payload["custody_tier_counts"].items():
        lines.append(f"- `{key}`: `{value}`")
    lines.extend(["", "## Concept Registry", ""])
    for concept in payload["concept_registry"][:20]:
        lines.extend(
            [
                f"### {concept['concept_id']}",
                "",
                f"- File count: `{concept['file_count']}`",
                f"- Concept SHA-256: `{concept['concept_sha256']}`",
                "- Example paths:",
            ]
        )
        for path in concept["example_paths"][:5]:
            lines.append(f"  - `{path}`")
        lines.append("")

    lines.extend(["## Named Concepts", ""])
    for concept in payload["named_concepts"]:
        lines.extend(
            [
                f"### {concept['name']}",
                "",
                f"- Concept ID: `{concept['concept_id']}`",
                f"- Estate role: `{concept['estate_role']}`",
                f"- Safe description: {concept['safe_description']}",
                f"- Public boundary: {concept['public_boundary']}",
                "",
            ]
        )

    lines.extend(["## Largest Files", ""])
    for row in payload["largest_files"][:15]:
        lines.append(
            f"- `{row['relative_path']}` bytes=`{row['size_bytes']}` class=`{row['asset_class']}` hash_mode=`{row['hash_mode']}` metadata_sha256=`{row['metadata_sha256']}`"
        )

    if payload["scan_error_examples"]:
        lines.extend(["", "## Scan Exceptions", ""])
        for row in payload["scan_error_examples"]:
            lines.append(f"- `{row['relative_path']}` error_type=`{row['error_type']}`")

    lines.extend(["", "## Audit Rules", ""])
    for key, value in payload["audit_rules"].items():
        lines.append(f"- {key}: `{value}`")
    return "\n".join(lines) + "\n"


def scan_sensitive_text(text: str) -> list[str]:
    lowered = text.lower()
    return sorted({marker for marker in SENSITIVE_MARKERS if marker in lowered})


class PrivateUniverseConfig:
    """Explicit inputs for the zero-copy private manifest federation."""

    def __init__(
        self,
        *,
        scientific_manifest: Path = DEFAULT_PRIVATE_UNIVERSE_SOURCES[
            "scientific_index"
        ],
        fast_manifest: Path = DEFAULT_PRIVATE_UNIVERSE_SOURCES["fast_index"],
        canonical_inventory: Path = DEFAULT_PRIVATE_UNIVERSE_SOURCES[
            "canonical_estate_inventory"
        ],
        curated_intake: Path = DEFAULT_PRIVATE_UNIVERSE_SOURCES[
            "curated_local_icloud_intake"
        ],
        root_registry: Path = DEFAULT_PRIVATE_UNIVERSE_SOURCES["root_registry"],
        private_output_dir: Path = PRIVATE_UNIVERSE_DIR,
        public_receipt: Path = PRIVATE_UNIVERSE_PUBLIC_RECEIPT,
        dashboard_receipt: Path = PRIVATE_UNIVERSE_DASHBOARD_RECEIPT,
        database_name: str = PRIVATE_UNIVERSE_DB_NAME,
        explicit_files: Iterable[Path] = (),
        minimum_output_free_percent: float = PRIVATE_UNIVERSE_MIN_FREE_PERCENT,
    ) -> None:
        self.scientific_manifest = Path(scientific_manifest)
        self.fast_manifest = Path(fast_manifest)
        self.canonical_inventory = Path(canonical_inventory)
        self.curated_intake = Path(curated_intake)
        self.root_registry = Path(root_registry)
        self.private_output_dir = Path(private_output_dir)
        self.public_receipt = Path(public_receipt)
        self.dashboard_receipt = Path(dashboard_receipt)
        self.database_name = database_name
        self.explicit_files = tuple(Path(path) for path in explicit_files)
        self.minimum_output_free_percent = float(minimum_output_free_percent)

    @property
    def database_path(self) -> Path:
        return self.private_output_dir / self.database_name

    @property
    def private_receipt_path(self) -> Path:
        return self.private_output_dir / PRIVATE_UNIVERSE_RECEIPT_NAME

    def source_paths(self) -> dict[str, Path]:
        return {
            "scientific_index": self.scientific_manifest,
            "fast_index": self.fast_manifest,
            "canonical_estate_inventory": self.canonical_inventory,
            "curated_local_icloud_intake": self.curated_intake,
            "root_registry": self.root_registry,
        }


def validate_private_output_layout(config: PrivateUniverseConfig) -> dict[str, Path]:
    database_name = str(config.database_name or "")
    if (
        not database_name
        or database_name in {".", ".."}
        or ".." in database_name
        or "/" in database_name
        or "\\" in database_name
        or ntpath.isabs(database_name)
        or bool(ntpath.splitdrive(database_name)[0])
    ):
        raise ValueError(
            "Private-universe database name must be a traversal-free basename."
        )
    if not database_name.lower().endswith((".sqlite", ".sqlite3", ".db")):
        raise ValueError("Private-universe database name must use a SQLite extension")

    output_directory = Path(os.path.abspath(config.private_output_dir)).resolve(
        strict=False
    )
    layout = {
        "private_output_dir": output_directory,
        "database_path": (output_directory / database_name).resolve(strict=False),
        "private_receipt_path": (
            output_directory / PRIVATE_UNIVERSE_RECEIPT_NAME
        ).resolve(strict=False),
        "history_directory": (
            output_directory / PRIVATE_UNIVERSE_HISTORY_DIR_NAME
        ).resolve(strict=False),
        "lock_path": (output_directory / PRIVATE_UNIVERSE_LOCK_NAME).resolve(
            strict=False
        ),
    }
    for key, path in layout.items():
        if key == "private_output_dir":
            continue
        try:
            path.relative_to(output_directory)
        except ValueError:
            raise ValueError(
                "Resolved private-universe output escaped the private output directory."
            ) from None
    return layout


def validate_distinct_publish_targets(
    config: PrivateUniverseConfig,
    layout: dict[str, Path],
) -> None:
    targets = [
        layout["database_path"],
        layout["private_receipt_path"],
        Path(os.path.abspath(config.public_receipt)).resolve(strict=False),
        Path(os.path.abspath(config.dashboard_receipt)).resolve(strict=False),
    ]
    normalized = {os.path.normcase(str(path)) for path in targets}
    if len(normalized) != len(targets):
        raise ValueError(
            "Private-universe publish targets must be four distinct files."
        )


class PrivateUniverseWriterLock:
    def __init__(self, lock_path: Path) -> None:
        self.lock_path = lock_path
        self.file_descriptor: int | None = None

    def __enter__(self) -> "PrivateUniverseWriterLock":
        try:
            self.file_descriptor = os.open(
                self.lock_path,
                os.O_CREAT | os.O_EXCL | os.O_WRONLY,
                0o600,
            )
        except FileExistsError:
            raise RuntimeError(
                "Private-universe build lock is already held; no outputs were changed."
            ) from None
        lock_record = json.dumps(
            {
                "pid": os.getpid(),
                "acquired_utc": now_utc(),
                "purpose": "private_universe_single_writer",
            },
            sort_keys=True,
        ).encode("utf-8")
        try:
            os.write(self.file_descriptor, lock_record)
            os.fsync(self.file_descriptor)
        except BaseException:
            os.close(self.file_descriptor)
            self.file_descriptor = None
            self.lock_path.unlink(missing_ok=True)
            raise
        return self

    def __exit__(self, exc_type: Any, exc: Any, traceback: Any) -> None:
        if self.file_descriptor is not None:
            os.close(self.file_descriptor)
            self.file_descriptor = None
        try:
            self.lock_path.unlink()
        except FileNotFoundError:
            pass


def has_unsafe_windows_input_attributes(file_stat: Any) -> bool:
    file_attributes = int(getattr(file_stat, "st_file_attributes", 0) or 0)
    return bool(file_attributes & UNSAFE_WINDOWS_INPUT_ATTRIBUTE_MASK)


def require_safe_input_parent_chain(path: Path) -> None:
    current = Path(os.path.abspath(path)).parent
    while True:
        try:
            parent_stat = current.lstat()
        except OSError:
            raise FileNotFoundError(
                "Required private-universe input parent is missing or unreadable."
            ) from None
        if current.is_symlink() or has_unsafe_windows_input_attributes(parent_stat):
            raise ValueError(
                "Private-universe input parent uses an unsafe reparse, offline, or recall attribute."
            )
        parent = current.parent
        if parent == current:
            return
        current = parent


def require_regular_manifest(path: Path) -> os.stat_result:
    try:
        file_stat = path.lstat()
    except OSError:
        raise FileNotFoundError(
            "Required private-universe input is missing or unreadable."
        ) from None
    if path.is_symlink() or not stat.S_ISREG(file_stat.st_mode):
        raise ValueError("Private-universe input must be a regular, non-symlink file.")
    if has_unsafe_windows_input_attributes(file_stat):
        raise ValueError(
            "Private-universe input uses an unsafe reparse, offline, or recall attribute."
        )
    require_safe_input_parent_chain(path)
    return file_stat


def nearest_existing_ancestor(path: Path) -> Path:
    candidate = Path(os.path.abspath(path))
    while not candidate.exists():
        parent = candidate.parent
        if parent == candidate:
            raise RuntimeError(
                "No existing ancestor was found for the private output volume."
            )
        candidate = parent
    return candidate


def estimate_private_index_output(config: PrivateUniverseConfig) -> dict[str, int]:
    manifest_bytes = 0
    for path in config.source_paths().values():
        manifest_bytes += int(require_regular_manifest(path).st_size)
    explicit_files = {
        normalized_path_key(path): Path(normalize_windows_path(path))
        for path in config.explicit_files
        if normalized_path_key(path)
    }
    explicit_bytes = sum(
        int(require_regular_manifest(path).st_size) for path in explicit_files.values()
    )
    estimated_database_bytes = max(
        PRIVATE_UNIVERSE_MIN_ESTIMATED_DB_BYTES,
        manifest_bytes * PRIVATE_UNIVERSE_DB_ESTIMATE_MULTIPLIER,
    )
    return {
        "manifest_input_bytes": manifest_bytes,
        "explicit_input_bytes": explicit_bytes,
        "estimated_database_bytes": estimated_database_bytes,
        "absolute_reserve_bytes": PRIVATE_UNIVERSE_ABSOLUTE_RESERVE_BYTES,
        "required_free_bytes": estimated_database_bytes
        + PRIVATE_UNIVERSE_ABSOLUTE_RESERVE_BYTES,
    }


def check_private_output_volume(
    output_directory: Path,
    minimum_free_percent: float = PRIVATE_UNIVERSE_MIN_FREE_PERCENT,
    output_estimate: dict[str, int] | None = None,
) -> dict[str, Any]:
    if not 0.0 <= minimum_free_percent <= 100.0:
        raise ValueError(
            "Output-volume minimum free percent must be between 0 and 100."
        )
    ancestor = nearest_existing_ancestor(output_directory)
    usage = shutil.disk_usage(ancestor)
    free_percent = 0.0 if usage.total <= 0 else (100.0 * usage.free / usage.total)
    if free_percent < minimum_free_percent:
        raise RuntimeError(
            "Private-universe output-volume preflight failed: "
            f"{free_percent:.2f}% free is below the {minimum_free_percent:.2f}% minimum."
        )
    output_estimate = output_estimate or {
        "manifest_input_bytes": 0,
        "explicit_input_bytes": 0,
        "estimated_database_bytes": 0,
        "absolute_reserve_bytes": 0,
        "required_free_bytes": 0,
    }
    required_free_bytes = int(output_estimate["required_free_bytes"])
    if usage.free < required_free_bytes:
        raise RuntimeError(
            "Private-universe output-volume reserve preflight failed: available bytes "
            "are below the estimated database plus absolute reserve requirement."
        )
    return {
        "gate_passed": True,
        "minimum_free_percent": float(minimum_free_percent),
        "observed_free_percent": round(free_percent, 2),
        "observed_free_bytes": int(usage.free),
        "estimated_database_bytes": int(output_estimate["estimated_database_bytes"]),
        "absolute_reserve_bytes": int(output_estimate["absolute_reserve_bytes"]),
        "required_free_bytes": required_free_bytes,
        "database_estimate_multiplier": PRIVATE_UNIVERSE_DB_ESTIMATE_MULTIPLIER,
        "database_estimate_basis": "aggregate_manifest_bytes_times_multiplier_with_minimum_floor",
        "nearest_existing_ancestor_checked_before_output_creation": True,
        "output_volume_only": True,
        "input_volume_gate_required": False,
        "input_scope": "manifest_only_plus_individually_authorized_explicit_files",
    }


def stage_json_artifact(path: Path, payload: dict[str, Any]) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    staged_path = path.with_name(f".{path.name}.{uuid.uuid4().hex}.stage")
    try:
        with staged_path.open("x", encoding="utf-8", newline="\n") as handle:
            json.dump(payload, handle, indent=2, sort_keys=True, default=str)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        return staged_path
    except BaseException:
        staged_path.unlink(missing_ok=True)
        raise


def clone_regular_file(source: Path, destination: Path) -> None:
    if source.is_symlink() or not source.is_file():
        raise RuntimeError("Publish source or prior artifact is not a regular file.")
    destination.parent.mkdir(parents=True, exist_ok=True)
    if destination.exists():
        raise RuntimeError("Publish backup destination already exists.")
    try:
        os.link(source, destination)
    except OSError:
        try:
            shutil.copy2(source, destination)
            with destination.open("r+b") as handle:
                handle.flush()
                os.fsync(handle.fileno())
        except BaseException:
            destination.unlink(missing_ok=True)
            raise


def atomic_replace(source: Path, destination: Path) -> None:
    os.replace(source, destination)


def prepare_prior_private_custody(config: PrivateUniverseConfig) -> dict[str, Any]:
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
    history_directory = config.private_output_dir / PRIVATE_UNIVERSE_HISTORY_DIR_NAME
    result: dict[str, Any] = {
        "prior_database_present": False,
        "prior_database_preserved": False,
        "prior_database_sha256": "",
        "prior_database_bytes": 0,
        "prior_database_archive_path": "",
        "prior_private_receipt_present": False,
        "prior_private_receipt_preserved": False,
        "prior_private_receipt_sha256": "",
        "prior_private_receipt_bytes": 0,
        "prior_private_receipt_archive_path": "",
    }

    if config.database_path.exists() and (
        config.database_path.is_symlink() or not config.database_path.is_file()
    ):
        raise RuntimeError("Existing private latest database is not a regular file.")
    if config.private_receipt_path.exists() and (
        config.private_receipt_path.is_symlink()
        or not config.private_receipt_path.is_file()
    ):
        raise RuntimeError("Existing private latest receipt is not a regular file.")

    prior_database_sha256 = (
        sha256_file(config.database_path) if config.database_path.exists() else ""
    )
    prior_receipt_sha256 = (
        sha256_file(config.private_receipt_path)
        if config.private_receipt_path.exists()
        else ""
    )

    if config.database_path.exists():
        prior_bytes = config.database_path.stat().st_size
        archive_path = history_directory / (
            f"lumencore_private_universe_{timestamp}_{prior_database_sha256[:16]}.sqlite3"
        )
        result.update(
            {
                "prior_database_present": True,
                "prior_database_preserved": True,
                "prior_database_sha256": prior_database_sha256,
                "prior_database_bytes": prior_bytes,
                "prior_database_archive_path": str(archive_path),
            }
        )

    if config.private_receipt_path.exists():
        prior_receipt_bytes = config.private_receipt_path.stat().st_size
        receipt_archive = history_directory / (
            f"lumencore_private_universe_receipt_{timestamp}_{prior_receipt_sha256[:16]}.json"
        )
        result.update(
            {
                "prior_private_receipt_present": True,
                "prior_private_receipt_preserved": True,
                "prior_private_receipt_sha256": prior_receipt_sha256,
                "prior_private_receipt_bytes": prior_receipt_bytes,
                "prior_private_receipt_archive_path": str(receipt_archive),
            }
        )
    return result


def publish_staged_private_universe_artifacts(
    staged_artifacts: dict[str, Path],
    final_artifacts: dict[str, Path],
    prior_custody: dict[str, Any],
) -> None:
    publish_order = (
        "database",
        "private_receipt",
        "public_receipt",
        "dashboard_receipt",
    )
    backups: dict[str, Path | None] = {}
    transient_backups: list[Path] = []
    installed: list[str] = []
    try:
        for key in publish_order:
            final_path = final_artifacts[key]
            if not final_path.exists():
                backups[key] = None
                continue
            if key == "database":
                backup_path = Path(prior_custody["prior_database_archive_path"])
            elif key == "private_receipt":
                backup_path = Path(prior_custody["prior_private_receipt_archive_path"])
            else:
                backup_path = final_path.with_name(
                    f".{final_path.name}.{uuid.uuid4().hex}.rollback"
                )
                transient_backups.append(backup_path)
            clone_regular_file(final_path, backup_path)
            backups[key] = backup_path

        for key in publish_order:
            installed.append(key)
            atomic_replace(staged_artifacts[key], final_artifacts[key])
    except BaseException as publish_error:
        rollback_errors: list[str] = []
        for key in reversed(installed):
            final_path = final_artifacts[key]
            backup_path = backups.get(key)
            try:
                if backup_path is None:
                    final_path.unlink(missing_ok=True)
                else:
                    restore_stage = final_path.with_name(
                        f".{final_path.name}.{uuid.uuid4().hex}.restore"
                    )
                    clone_regular_file(backup_path, restore_stage)
                    atomic_replace(restore_stage, final_path)
            except BaseException as rollback_error:
                rollback_errors.append(type(rollback_error).__name__)
        detail = (
            f" Rollback errors: {','.join(sorted(rollback_errors))}."
            if rollback_errors
            else " Prior publish set was restored."
        )
        raise RuntimeError(
            "Private-universe publish transaction failed; output paths are withheld."
            + detail
        ) from publish_error
    finally:
        for staged_path in staged_artifacts.values():
            try:
                staged_path.unlink()
            except OSError:
                pass
        for backup_path in transient_backups:
            try:
                backup_path.unlink()
            except OSError:
                pass


def normalize_windows_path(value: Any) -> str:
    raw = str(value or "").strip().strip('"')
    if not raw:
        return ""
    normalized = ntpath.normpath(raw.replace("/", "\\"))
    if normalized.upper().startswith("\\\\?\\UNC\\"):
        normalized = "\\\\" + normalized[8:]
    elif normalized.startswith("\\\\?\\"):
        normalized = normalized[4:]
    return normalized


def normalized_path_key(value: Any) -> str:
    return normalize_windows_path(value).casefold()


def stable_root_alias(root_path: Any) -> str:
    key = normalized_path_key(root_path) or "[unmapped]"
    return f"root_{hashlib.sha256(key.encode('utf-8')).hexdigest()[:16]}"


def stable_asset_id(path_key: str) -> str:
    return f"asset_{hashlib.sha256(path_key.encode('utf-8')).hexdigest()}"


def is_absolute_windows_path(value: str) -> bool:
    return bool(re.match(r"^[A-Za-z]:\\", value)) or value.startswith("\\\\")


def path_within_root(path_value: str, root_value: str) -> bool:
    path_key = normalized_path_key(path_value)
    root_key = normalized_path_key(root_value).rstrip("\\")
    return bool(
        path_key
        and root_key
        and (path_key == root_key or path_key.startswith(root_key + "\\"))
    )


def relative_to_reported_root(path_value: str, root_value: str) -> str:
    if not path_within_root(path_value, root_value):
        return ""
    try:
        relative = ntpath.relpath(
            normalize_windows_path(path_value), normalize_windows_path(root_value)
        )
    except ValueError:
        return ""
    return "" if relative == "." else relative


def coerce_int(value: Any) -> int | None:
    if value is None or value == "":
        return None
    try:
        return int(float(str(value).replace(",", "")))
    except (TypeError, ValueError):
        return None


def valid_sha256(value: Any) -> str:
    candidate = str(value or "").strip().lower()
    return candidate if re.fullmatch(r"[0-9a-f]{64}", candidate) else ""


def private_lane_tags(
    path_value: str,
    extension: str = "",
    supplemental_terms: Iterable[str] = (),
) -> list[str]:
    normalized = path_value.lower().replace("\\", "/")
    ext = extension.lower().strip()
    if ext and not ext.startswith("."):
        ext = f".{ext}"
    haystack = " ".join(
        [normalized, ext, *(str(term).lower() for term in supplemental_terms)]
    )
    tags = {
        lane
        for lane, tokens in PRIVATE_LANE_RULES.items()
        if any(token in haystack for token in tokens)
    }
    return sorted(tags)


def source_id_for(kind: str, source_sha256: str, locator_key: str = "") -> str:
    identity = f"{kind}:{source_sha256}:{locator_key}"
    return f"source_{hashlib.sha256(identity.encode('utf-8')).hexdigest()}"


def builder_git_identity() -> dict[str, Any]:
    builder_relative_path = rel(Path(__file__))
    try:
        commit_result = subprocess.run(
            ["git", "-C", str(ROOT), "rev-parse", "HEAD"],
            check=False,
            capture_output=True,
            text=True,
            timeout=15,
        )
        status_result = subprocess.run(
            [
                "git",
                "-C",
                str(ROOT),
                "status",
                "--porcelain",
                "--untracked-files=all",
                "--",
                builder_relative_path,
            ],
            check=False,
            capture_output=True,
            text=True,
            timeout=15,
        )
    except (OSError, subprocess.SubprocessError):
        return {
            "builder_git_commit": "unavailable",
            "builder_git_state": "unavailable_dirty_marker",
            "builder_git_dirty": True,
            "builder_source_is_committed_snapshot": False,
        }

    commit = commit_result.stdout.strip().lower()
    if commit_result.returncode != 0 or not re.fullmatch(r"[0-9a-f]{40}", commit):
        commit = "unavailable"
    status = status_result.stdout.strip()
    if status_result.returncode != 0:
        state = "unavailable_dirty_marker"
        dirty = True
    elif not status:
        state = "tracked_clean"
        dirty = False
    elif status.startswith("??"):
        state = "untracked_dirty"
        dirty = True
    else:
        state = "tracked_modified_dirty"
        dirty = True
    return {
        "builder_git_commit": commit,
        "builder_git_state": state,
        "builder_git_dirty": dirty,
        "builder_source_is_committed_snapshot": bool(
            commit != "unavailable" and not dirty
        ),
    }


def run_staged_sqlite_quick_check(database_path: Path) -> dict[str, Any]:
    connection = sqlite3.connect(f"file:{database_path.as_posix()}?mode=ro", uri=True)
    try:
        rows = [
            str(row[0]) for row in connection.execute("PRAGMA quick_check").fetchall()
        ]
    finally:
        connection.close()
    if rows != ["ok"]:
        raise RuntimeError(
            "Staged private-universe SQLite quick_check failed; no publish was attempted."
        )
    return {
        "sqlite_quick_check": "ok",
        "staged_database_quick_check_passed": True,
    }


def read_source_file_identity(
    path: Path,
    source_kind: str,
    *,
    require_stable_during_hash: bool = False,
) -> dict[str, Any]:
    try:
        before = require_regular_manifest(path)
        source_sha256 = sha256_file(path)
        after = require_regular_manifest(path)
        if require_stable_during_hash and (
            before.st_size != after.st_size or before.st_mtime_ns != after.st_mtime_ns
        ):
            raise ValueError("Input changed while its SHA-256 was being computed.")
        return {
            "sha256": source_sha256,
            "bytes": after.st_size,
            "modified_utc": datetime.fromtimestamp(
                after.st_mtime,
                tz=timezone.utc,
            ).isoformat(),
        }
    except (OSError, ValueError) as exc:
        raise RuntimeError(
            f"Unable to read private-universe source kind '{source_kind}' "
            f"({type(exc).__name__})."
        ) from None


def iter_csv_rows(
    path: Path, required_fields: set[str]
) -> Iterator[tuple[int, dict[str, str]]]:
    with path.open("r", newline="", encoding="utf-8-sig") as handle:
        reader = csv.DictReader(handle)
        fields = set(reader.fieldnames or [])
        missing = sorted(required_fields - fields)
        if missing:
            raise ValueError(f"Manifest schema missing required fields {missing}")
        for row_number, row in enumerate(reader, start=2):
            yield row_number, {
                str(key): str(value or "")
                for key, value in row.items()
                if key is not None
            }


def load_json_manifest(path: Path) -> Any:
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def source_observations(kind: str, path: Path) -> Iterator[tuple[int, dict[str, Any]]]:
    if kind in {"scientific_index", "fast_index"}:
        for row_number, row in iter_csv_rows(
            path,
            {"root", "path", "extension", "size", "last_write_utc", "sha256"},
        ):
            yield row_number, {
                "path": row["path"],
                "root": row["root"],
                "extension": row["extension"],
                "size_bytes": coerce_int(row["size"]),
                "modified_utc": row["last_write_utc"],
                "reported_sha256": valid_sha256(row["sha256"]),
                "reported_hash_mode": "historical_manifest_sha256",
                "reported_hash_domain": "content_sha256",
                "supplemental_terms": (),
            }
        return

    if kind == "canonical_estate_inventory":
        for row_number, row in iter_csv_rows(
            path,
            {"relative_path", "extension", "size_bytes", "modified_utc", "hash_mode"},
        ):
            relative_path = row["relative_path"].replace("/", "\\")
            content_hash = valid_sha256(row.get("content_sha256"))
            metadata_hash = valid_sha256(row.get("metadata_sha256"))
            reported_hash = content_hash or metadata_hash
            reported_hash_domain = (
                "content_sha256"
                if content_hash
                else "metadata_sha256" if metadata_hash else "not_available"
            )
            yield row_number, {
                "path": ntpath.join(str(ROOT), relative_path),
                "root": str(ROOT),
                "extension": row["extension"],
                "size_bytes": coerce_int(row["size_bytes"]),
                "modified_utc": row["modified_utc"],
                "reported_sha256": reported_hash,
                "reported_hash_mode": row["hash_mode"] or "historical_hash_unspecified",
                "reported_hash_domain": reported_hash_domain,
                "supplemental_terms": (
                    row.get("asset_class", ""),
                    row.get("concept_tags", ""),
                    row.get("custody_tier", ""),
                ),
            }
        return

    if kind == "curated_local_icloud_intake":
        payload = load_json_manifest(path)
        records = payload.get("records", []) if isinstance(payload, dict) else []
        if not isinstance(records, list):
            raise ValueError("Curated intake records must be a JSON list")
        for row_number, row in enumerate(records, start=1):
            if not isinstance(row, dict):
                continue
            categories = row.get("categories", [])
            grant_lanes = row.get("grant_lanes", [])
            supplemental = [
                *(categories if isinstance(categories, list) else [categories]),
                *(grant_lanes if isinstance(grant_lanes, list) else [grant_lanes]),
                row.get("recommended_use", ""),
            ]
            yield row_number, {
                "path": row.get("absolute_path") or row.get("path"),
                "root": row.get("root", ""),
                "extension": row.get("extension", ""),
                "size_bytes": coerce_int(row.get("bytes")),
                "modified_utc": str(row.get("last_write_utc", "")),
                "reported_sha256": valid_sha256(row.get("sha256")),
                "reported_hash_mode": str(
                    row.get("sha256_mode", "historical_hash_unspecified")
                ),
                "reported_hash_domain": (
                    "metadata_sha256"
                    if "metadata" in str(row.get("sha256_mode", "")).lower()
                    else (
                        "content_sha256"
                        if valid_sha256(row.get("sha256"))
                        else "not_available"
                    )
                ),
                "supplemental_terms": supplemental,
            }
        return

    raise ValueError(f"Unsupported observation source kind: {kind}")


def normalize_private_observation(
    source_kind: str,
    source_id: str,
    source_row_number: int,
    raw: dict[str, Any],
) -> dict[str, Any]:
    root_path = normalize_windows_path(raw.get("root"))
    path_value = normalize_windows_path(raw.get("path"))
    if path_value and not is_absolute_windows_path(path_value) and root_path:
        path_value = normalize_windows_path(ntpath.join(root_path, path_value))
    path_is_absolute = is_absolute_windows_path(path_value)
    if not path_value:
        path_value = f"[unmapped]\\{source_kind}\\{source_row_number}"
    path_key = normalized_path_key(path_value)
    if not root_path:
        drive, _ = ntpath.splitdrive(path_value)
        root_path = f"{drive}\\" if drive else "[unmapped]"
    root_alias = stable_root_alias(root_path)
    path_belongs_to_reported_root = path_within_root(path_value, root_path)
    extension = (
        str(raw.get("extension") or ntpath.splitext(path_value)[1]).lower().strip()
    )
    if extension and not extension.startswith("."):
        extension = f".{extension}"
    reported_hash = valid_sha256(raw.get("reported_sha256"))
    hash_mode = str(raw.get("reported_hash_mode") or "historical_hash_unspecified")
    hash_domain = str(raw.get("reported_hash_domain") or "unknown_sha256")
    if not reported_hash:
        hash_domain = "not_available"
    elif hash_domain not in {"content_sha256", "metadata_sha256"}:
        hash_domain = "unknown_sha256"
    hash_status = (
        "historical_unverified"
        if reported_hash
        else "not_available_or_not_content_sha256"
    )
    supplemental_terms = [
        str(value) for value in raw.get("supplemental_terms", ()) if value
    ]
    lanes = private_lane_tags(path_value, extension, supplemental_terms)
    return {
        "asset_id": stable_asset_id(path_key),
        "path_key": path_key,
        "path_value": path_value,
        "path_is_absolute": path_is_absolute,
        "root_path": root_path,
        "root_alias": root_alias,
        "relative_path": relative_to_reported_root(path_value, root_path),
        "path_belongs_to_reported_root": path_belongs_to_reported_root,
        "extension": extension,
        "size_bytes": coerce_int(raw.get("size_bytes")),
        "modified_utc": str(raw.get("modified_utc") or ""),
        "reported_sha256": reported_hash,
        "reported_hash_mode": hash_mode,
        "reported_hash_domain": hash_domain,
        "hash_verification_status": hash_status,
        "archive_reference": extension in ARCHIVE_EXTENSIONS,
        "lanes": lanes,
        "supplemental_terms_json": json.dumps(
            sorted(set(supplemental_terms)), separators=(",", ":")
        ),
        "source_kind": source_kind,
        "source_id": source_id,
        "source_row_number": source_row_number,
        "selection_priority": PRIVATE_SOURCE_PRIORITIES[source_kind],
    }


def create_private_universe_schema(connection: sqlite3.Connection) -> None:
    connection.executescript("""
        PRAGMA foreign_keys = ON;
        CREATE TABLE metadata (
            key TEXT PRIMARY KEY,
            value TEXT NOT NULL
        );
        CREATE TABLE sources (
            source_id TEXT PRIMARY KEY,
            source_kind TEXT NOT NULL,
            source_path TEXT NOT NULL,
            source_sha256 TEXT NOT NULL,
            source_bytes INTEGER NOT NULL,
            source_modified_utc TEXT NOT NULL,
            manifest_row_count INTEGER NOT NULL DEFAULT 0,
            observation_count INTEGER NOT NULL DEFAULT 0,
            invalid_observation_count INTEGER NOT NULL DEFAULT 0,
            asset_bytes_read_for_sha256 INTEGER NOT NULL DEFAULT 0,
            reported_historical_hashes_reverified INTEGER NOT NULL DEFAULT 0
        );
        CREATE TABLE roots (
            root_alias TEXT PRIMARY KEY,
            normalized_root_path TEXT NOT NULL UNIQUE,
            registry_role TEXT,
            registry_exists INTEGER,
            registry_file_count INTEGER,
            intake_exists INTEGER,
            intake_seen_count INTEGER,
            intake_kept_count INTEGER,
            intake_skipped_count INTEGER,
            intake_truncated INTEGER,
            observed_unique_asset_count INTEGER NOT NULL DEFAULT 0,
            effective_asset_count INTEGER NOT NULL DEFAULT 0,
            observation_count INTEGER NOT NULL DEFAULT 0,
            source_count INTEGER NOT NULL DEFAULT 0,
            coverage_quality TEXT NOT NULL DEFAULT 'not_evaluated',
            coverage_flags_json TEXT NOT NULL DEFAULT '[]'
        );
        CREATE TABLE assets (
            asset_id TEXT PRIMARY KEY,
            normalized_path_key TEXT NOT NULL UNIQUE,
            absolute_path TEXT NOT NULL,
            path_is_absolute INTEGER NOT NULL,
            root_alias TEXT NOT NULL REFERENCES roots(root_alias),
            relative_path TEXT NOT NULL,
            extension TEXT NOT NULL,
            size_bytes INTEGER,
            modified_utc TEXT NOT NULL,
            selected_reported_sha256 TEXT NOT NULL,
            selected_hash_mode TEXT NOT NULL,
            selected_hash_domain TEXT NOT NULL,
            selected_hash_verification_status TEXT NOT NULL,
            selected_source_kind TEXT NOT NULL,
            selected_source_id TEXT NOT NULL REFERENCES sources(source_id),
            selection_priority INTEGER NOT NULL,
            archive_reference INTEGER NOT NULL DEFAULT 0
        );
        CREATE TABLE observations (
            observation_id INTEGER PRIMARY KEY AUTOINCREMENT,
            source_id TEXT NOT NULL REFERENCES sources(source_id),
            source_kind TEXT NOT NULL,
            source_row_number INTEGER NOT NULL,
            asset_id TEXT NOT NULL REFERENCES assets(asset_id),
            reported_root_alias TEXT NOT NULL REFERENCES roots(root_alias),
            reported_path TEXT NOT NULL,
            reported_relative_path TEXT NOT NULL,
            path_belongs_to_reported_root INTEGER NOT NULL,
            size_bytes INTEGER,
            modified_utc TEXT NOT NULL,
            reported_sha256 TEXT NOT NULL,
            reported_hash_mode TEXT NOT NULL,
            reported_hash_domain TEXT NOT NULL,
            hash_verification_status TEXT NOT NULL,
            supplemental_terms_json TEXT NOT NULL,
            UNIQUE(source_id, source_row_number)
        );
        CREATE TABLE asset_lanes (
            asset_id TEXT NOT NULL REFERENCES assets(asset_id),
            lane TEXT NOT NULL,
            PRIMARY KEY(asset_id, lane)
        );
        """)


def ensure_private_root(connection: sqlite3.Connection, root_path: str) -> str:
    normalized = normalize_windows_path(root_path) or "[unmapped]"
    alias = stable_root_alias(normalized)
    connection.execute(
        "INSERT OR IGNORE INTO roots(root_alias, normalized_root_path) VALUES (?, ?)",
        (alias, normalized),
    )
    return alias


def register_private_sources(
    connection: sqlite3.Connection,
    config: PrivateUniverseConfig,
) -> dict[str, dict[str, Any]]:
    registered: dict[str, dict[str, Any]] = {}
    for source_kind, source_path in config.source_paths().items():
        identity = read_source_file_identity(
            source_path,
            source_kind,
            require_stable_during_hash=True,
        )
        source_sha256 = identity["sha256"]
        source_id = source_id_for(source_kind, source_sha256)
        source_info = {
            "source_id": source_id,
            "source_kind": source_kind,
            "source_path": str(source_path),
            "source_sha256": source_sha256,
            "source_bytes": identity["bytes"],
            "source_modified_utc": identity["modified_utc"],
        }
        connection.execute(
            """
            INSERT INTO sources(
                source_id, source_kind, source_path, source_sha256, source_bytes,
                source_modified_utc, asset_bytes_read_for_sha256,
                reported_historical_hashes_reverified
            ) VALUES (?, ?, ?, ?, ?, ?, 0, 0)
            """,
            (
                source_id,
                source_kind,
                str(source_path),
                source_sha256,
                identity["bytes"],
                source_info["source_modified_utc"],
            ),
        )
        registered[source_kind] = source_info
    return registered


def verify_registered_manifest_inputs_unchanged(
    sources: dict[str, dict[str, Any]],
) -> int:
    verified_count = 0
    for source_kind, source in sorted(sources.items()):
        identity = read_source_file_identity(
            Path(source["source_path"]),
            source_kind,
            require_stable_during_hash=True,
        )
        if identity["sha256"] != source["source_sha256"]:
            raise RuntimeError(
                f"Private-universe source kind '{source_kind}' changed during import; "
                "source paths are withheld."
            )
        verified_count += 1
    return verified_count


def import_explicit_user_files(
    connection: sqlite3.Connection,
    explicit_files: Iterable[Path],
) -> int:
    unique_files: dict[str, Path] = {}
    for file_path in explicit_files:
        normalized = normalize_windows_path(file_path)
        key = normalized_path_key(normalized)
        if key:
            unique_files.setdefault(key, Path(normalized))

    imported = 0
    for locator_key, file_path in sorted(unique_files.items()):
        source_kind = "explicit_user_supplied_current_file"
        identity = read_source_file_identity(
            file_path,
            source_kind,
            require_stable_during_hash=True,
        )
        current_sha256 = identity["sha256"]
        source_id = source_id_for(source_kind, current_sha256, locator_key)
        modified_utc = identity["modified_utc"]
        connection.execute(
            """
            INSERT INTO sources(
                source_id, source_kind, source_path, source_sha256, source_bytes,
                source_modified_utc, manifest_row_count, observation_count,
                invalid_observation_count, asset_bytes_read_for_sha256,
                reported_historical_hashes_reverified
            ) VALUES (?, ?, ?, ?, ?, ?, 1, 1, 0, 1, 0)
            """,
            (
                source_id,
                source_kind,
                str(file_path),
                current_sha256,
                identity["bytes"],
                modified_utc,
            ),
        )
        observation = normalize_private_observation(
            source_kind,
            source_id,
            1,
            {
                "path": str(file_path),
                "root": str(file_path.parent),
                "extension": file_path.suffix,
                "size_bytes": identity["bytes"],
                "modified_utc": modified_utc,
                "reported_sha256": current_sha256,
                "reported_hash_mode": "current_content_sha256_explicitly_authorized",
                "reported_hash_domain": "content_sha256",
                "supplemental_terms": ("explicit_user_supplied_current_file",),
            },
        )
        observation["hash_verification_status"] = (
            "current_content_sha256_verified_in_this_run"
        )
        insert_observation_batch(connection, [observation])
        imported += 1
    return imported


def import_root_registry(
    connection: sqlite3.Connection,
    source: dict[str, Any],
) -> None:
    payload = load_json_manifest(Path(source["source_path"]))
    if not isinstance(payload, list):
        raise ValueError("Root registry must be a JSON list")
    row_count = 0
    for row in payload:
        if not isinstance(row, dict) or not row.get("root"):
            continue
        row_count += 1
        alias = ensure_private_root(connection, str(row["root"]))
        exists_value = row.get("exists")
        exists_int = None if exists_value is None else int(bool(exists_value))
        connection.execute(
            """
            UPDATE roots
            SET registry_role = ?, registry_exists = ?, registry_file_count = ?
            WHERE root_alias = ?
            """,
            (
                str(row.get("role") or "UNCLASSIFIED"),
                exists_int,
                coerce_int(row.get("file_count")),
                alias,
            ),
        )
    connection.execute(
        "UPDATE sources SET manifest_row_count = ? WHERE source_id = ?",
        (row_count, source["source_id"]),
    )


def import_curated_root_summaries(
    connection: sqlite3.Connection,
    source: dict[str, Any],
) -> None:
    payload = load_json_manifest(Path(source["source_path"]))
    roots = payload.get("roots", []) if isinstance(payload, dict) else []
    if not isinstance(roots, list):
        return
    for row in roots:
        if not isinstance(row, dict) or not row.get("root"):
            continue
        alias = ensure_private_root(connection, str(row["root"]))
        exists_value = row.get("exists")
        connection.execute(
            """
            UPDATE roots
            SET intake_exists = ?, intake_seen_count = ?, intake_kept_count = ?,
                intake_skipped_count = ?, intake_truncated = ?
            WHERE root_alias = ?
            """,
            (
                None if exists_value is None else int(bool(exists_value)),
                coerce_int(row.get("seen")),
                coerce_int(row.get("kept")),
                coerce_int(row.get("skipped")),
                int(bool(row.get("truncated"))),
                alias,
            ),
        )


def insert_observation_batch(
    connection: sqlite3.Connection, batch: list[dict[str, Any]]
) -> None:
    if not batch:
        return
    connection.executemany(
        "INSERT OR IGNORE INTO roots(root_alias, normalized_root_path) VALUES (?, ?)",
        [(row["root_alias"], row["root_path"]) for row in batch],
    )
    connection.executemany(
        """
        INSERT INTO assets(
            asset_id, normalized_path_key, absolute_path, path_is_absolute, root_alias,
            relative_path, extension, size_bytes, modified_utc, selected_reported_sha256,
            selected_hash_mode, selected_hash_domain, selected_hash_verification_status,
            selected_source_kind, selected_source_id, selection_priority, archive_reference
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(normalized_path_key) DO UPDATE SET
            absolute_path = excluded.absolute_path,
            path_is_absolute = excluded.path_is_absolute,
            root_alias = excluded.root_alias,
            relative_path = excluded.relative_path,
            extension = excluded.extension,
            size_bytes = excluded.size_bytes,
            modified_utc = excluded.modified_utc,
            selected_reported_sha256 = excluded.selected_reported_sha256,
            selected_hash_mode = excluded.selected_hash_mode,
            selected_hash_domain = excluded.selected_hash_domain,
            selected_hash_verification_status = excluded.selected_hash_verification_status,
            selected_source_kind = excluded.selected_source_kind,
            selected_source_id = excluded.selected_source_id,
            selection_priority = excluded.selection_priority,
            archive_reference = excluded.archive_reference
        WHERE excluded.selection_priority > assets.selection_priority
        """,
        [
            (
                row["asset_id"],
                row["path_key"],
                row["path_value"],
                int(row["path_is_absolute"]),
                row["root_alias"],
                row["relative_path"],
                row["extension"],
                row["size_bytes"],
                row["modified_utc"],
                row["reported_sha256"],
                row["reported_hash_mode"],
                row["reported_hash_domain"],
                row["hash_verification_status"],
                row["source_kind"],
                row["source_id"],
                row["selection_priority"],
                int(row["archive_reference"]),
            )
            for row in batch
        ],
    )
    connection.executemany(
        """
        INSERT INTO observations(
            source_id, source_kind, source_row_number, asset_id, reported_root_alias,
            reported_path, reported_relative_path, path_belongs_to_reported_root,
            size_bytes, modified_utc,
            reported_sha256, reported_hash_mode, reported_hash_domain,
            hash_verification_status, supplemental_terms_json
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        [
            (
                row["source_id"],
                row["source_kind"],
                row["source_row_number"],
                row["asset_id"],
                row["root_alias"],
                row["path_value"],
                row["relative_path"],
                int(row["path_belongs_to_reported_root"]),
                row["size_bytes"],
                row["modified_utc"],
                row["reported_sha256"],
                row["reported_hash_mode"],
                row["reported_hash_domain"],
                row["hash_verification_status"],
                row["supplemental_terms_json"],
            )
            for row in batch
        ],
    )
    connection.executemany(
        "INSERT OR IGNORE INTO asset_lanes(asset_id, lane) VALUES (?, ?)",
        [(row["asset_id"], lane) for row in batch for lane in row["lanes"]],
    )


def import_private_observation_source(
    connection: sqlite3.Connection,
    source: dict[str, Any],
    batch_size: int = 2000,
) -> None:
    source_kind = source["source_kind"]
    source_id = source["source_id"]
    batch: list[dict[str, Any]] = []
    row_count = 0
    invalid_count = 0
    for row_number, raw in source_observations(
        source_kind, Path(source["source_path"])
    ):
        row_count += 1
        observation = normalize_private_observation(
            source_kind, source_id, row_number, raw
        )
        if not observation["path_is_absolute"]:
            invalid_count += 1
        batch.append(observation)
        if len(batch) >= batch_size:
            insert_observation_batch(connection, batch)
            batch.clear()
    insert_observation_batch(connection, batch)
    connection.execute(
        """
        UPDATE sources
        SET manifest_row_count = ?, observation_count = ?, invalid_observation_count = ?
        WHERE source_id = ?
        """,
        (row_count, row_count, invalid_count, source_id),
    )


def assign_most_specific_effective_roots(
    connection: sqlite3.Connection,
    batch_size: int = 5000,
) -> int:
    root_candidates = [
        (
            normalized_path_key(root_path).rstrip("\\"),
            normalize_windows_path(root_path),
            root_alias,
        )
        for root_alias, root_path in connection.execute(
            "SELECT root_alias, normalized_root_path FROM roots"
        ).fetchall()
        if is_absolute_windows_path(normalize_windows_path(root_path))
    ]
    root_candidates.sort(
        key=lambda item: len(item[0]),
        reverse=True,
    )
    updated_count = 0
    updates: list[tuple[str, str, str]] = []
    cursor = connection.execute("""
        SELECT asset_id, absolute_path, root_alias, relative_path
        FROM assets
        WHERE path_is_absolute = 1
        ORDER BY asset_id
        """)
    while True:
        rows = cursor.fetchmany(batch_size)
        if not rows:
            break
        for asset_id, absolute_path, current_alias, current_relative in rows:
            path_key = normalized_path_key(absolute_path)
            for root_key, root_path, root_alias in root_candidates:
                if path_key != root_key and not path_key.startswith(root_key + "\\"):
                    continue
                relative_path = relative_to_reported_root(absolute_path, root_path)
                if root_alias != current_alias or relative_path != current_relative:
                    updates.append((root_alias, relative_path, asset_id))
                    updated_count += 1
                break
        if updates:
            connection.executemany(
                "UPDATE assets SET root_alias = ?, relative_path = ? WHERE asset_id = ?",
                updates,
            )
            updates.clear()

    connection.execute("UPDATE roots SET effective_asset_count = 0")
    connection.execute("""
        UPDATE roots
        SET effective_asset_count = COALESCE((
            SELECT COUNT(*) FROM assets WHERE assets.root_alias = roots.root_alias
        ), 0)
        """)
    return updated_count


def finalize_private_root_coverage(connection: sqlite3.Connection) -> None:
    root_rows = connection.execute("""
        SELECT
            roots.root_alias,
            roots.registry_file_count,
            roots.registry_role,
            roots.intake_truncated,
            COUNT(DISTINCT observations.asset_id) AS unique_assets,
            COUNT(observations.observation_id) AS observations,
            COUNT(DISTINCT observations.source_id) AS source_count
        FROM roots
        LEFT JOIN observations ON observations.reported_root_alias = roots.root_alias
        GROUP BY roots.root_alias
        """).fetchall()
    for row in root_rows:
        (
            alias,
            registry_count,
            registry_role,
            intake_truncated,
            unique_assets,
            observations,
            source_count,
        ) = row
        flags = ["mixed_freshness_not_live_reconciled"]
        if registry_role is not None:
            flags.append("root_registry_present")
        if observations:
            flags.append("manifest_observations_present")
        else:
            flags.append("no_manifest_observations")
        if source_count > 1:
            flags.append("multi_source_provenance")
        if intake_truncated:
            flags.append("curated_intake_truncated")
        if registry_count is not None and observations:
            if unique_assets >= registry_count:
                flags.append("observed_count_at_or_above_legacy_registry_count")
            else:
                flags.append("observed_count_below_legacy_registry_count")
        if not observations and registry_role is not None:
            quality = "registry_only_no_manifest_observation"
        elif intake_truncated:
            quality = "partial_curated_coverage_truncated"
        elif source_count > 1:
            quality = "federated_multi_source_mixed_freshness"
        elif observations:
            quality = "single_source_manifest_coverage"
        else:
            quality = "unclassified_no_observation"
        connection.execute(
            """
            UPDATE roots
            SET observed_unique_asset_count = ?, observation_count = ?, source_count = ?,
                coverage_quality = ?, coverage_flags_json = ?
            WHERE root_alias = ?
            """,
            (
                unique_assets,
                observations,
                source_count,
                quality,
                json.dumps(sorted(flags), separators=(",", ":")),
                alias,
            ),
        )


def create_private_indexes(connection: sqlite3.Connection) -> None:
    connection.executescript("""
        CREATE INDEX observations_asset_id_idx ON observations(asset_id);
        CREATE INDEX observations_source_kind_idx ON observations(source_kind);
        CREATE INDEX observations_root_alias_idx ON observations(reported_root_alias);
        CREATE INDEX assets_root_alias_idx ON assets(root_alias);
        CREATE INDEX assets_selected_source_idx ON assets(selected_source_kind);
        CREATE INDEX asset_lanes_lane_idx ON asset_lanes(lane);
        """)


def scalar(
    connection: sqlite3.Connection, query: str, parameters: tuple[Any, ...] = ()
) -> int:
    row = connection.execute(query, parameters).fetchone()
    return int(row[0] if row and row[0] is not None else 0)


def build_public_private_universe_receipt(
    connection: sqlite3.Connection,
    output_volume_preflight: dict[str, Any],
    generation_id: str,
    builder_sha256: str,
    git_identity: dict[str, Any],
) -> dict[str, Any]:
    source_rows = connection.execute("""
        SELECT source_kind, source_sha256, source_bytes, source_modified_utc,
               manifest_row_count, observation_count, invalid_observation_count
        FROM sources
        WHERE source_kind <> 'explicit_user_supplied_current_file'
        ORDER BY source_kind
        """).fetchall()
    lane_counts = {
        lane: count
        for lane, count in connection.execute(
            "SELECT lane, COUNT(*) FROM asset_lanes GROUP BY lane ORDER BY lane"
        ).fetchall()
    }
    coverage_counts = {
        quality: count
        for quality, count in connection.execute(
            "SELECT coverage_quality, COUNT(*) FROM roots GROUP BY coverage_quality ORDER BY coverage_quality"
        ).fetchall()
    }
    registry_role_counts: Counter[str] = Counter()
    for role, count in connection.execute("""
        SELECT registry_role, COUNT(*)
        FROM roots
        WHERE registry_role IS NOT NULL
        GROUP BY registry_role
        ORDER BY registry_role
        """).fetchall():
        safe_role = (
            role
            if role in PUBLIC_ROOT_ROLE_ALLOWLIST
            else "OTHER_PRIVATE_ROLE_REDACTED"
        )
        registry_role_counts[safe_role] += int(count)
    observation_count = scalar(connection, "SELECT COUNT(*) FROM observations")
    unique_asset_count = scalar(connection, "SELECT COUNT(*) FROM assets")
    hash_conflict_count = scalar(
        connection,
        """
        SELECT COUNT(*) FROM (
            SELECT asset_id
            FROM observations
            WHERE reported_sha256 <> ''
              AND reported_hash_domain = 'content_sha256'
            GROUP BY asset_id
            HAVING COUNT(DISTINCT lower(reported_sha256)) > 1
        )
        """,
    )
    historical_content_hash_observation_count = scalar(
        connection,
        """
        SELECT COUNT(*) FROM observations
        WHERE reported_sha256 <> ''
          AND reported_hash_domain = 'content_sha256'
          AND hash_verification_status = 'historical_unverified'
        """,
    )
    historical_metadata_hash_observation_count = scalar(
        connection,
        """
        SELECT COUNT(*) FROM observations
        WHERE reported_sha256 <> ''
          AND reported_hash_domain = 'metadata_sha256'
          AND hash_verification_status = 'historical_unverified'
        """,
    )
    explicit_file_count = scalar(
        connection,
        "SELECT COUNT(*) FROM sources WHERE source_kind = 'explicit_user_supplied_current_file'",
    )
    explicit_file_hash_coverage_count = scalar(
        connection,
        """
        SELECT COUNT(*) FROM sources
        WHERE source_kind = 'explicit_user_supplied_current_file'
          AND length(source_sha256) = 64
          AND asset_bytes_read_for_sha256 = 1
        """,
    )
    public = {
        "schema": "lumencore_private_universe_receipt_v1",
        "generation_id": generation_id,
        "generated_utc": now_utc(),
        "status": "PRIVATE_UNIVERSE_ZERO_COPY_FEDERATION_READY_LIMITED",
        "methodology": {
            "federation_mode": "zero_copy_manifest_federation",
            "freshness": "mixed_freshness",
            "full_live_reconciliation": False,
            "source_manifest_files_read_and_parsed": True,
            "manifest_referenced_file_bytes_read": False,
            "referenced_historical_asset_files_opened": False,
            "explicit_file_bytes_read_for_sha256": explicit_file_count > 0,
            "explicit_file_contents_parsed_or_extracted": False,
            "referenced_historical_asset_contents_parsed_or_extracted": False,
            "broad_roots_scanned": False,
            "archives_unpacked": False,
            "historical_hashes_reverified": False,
            "historical_hash_status": "reported_by_source_manifest_unverified_in_this_run",
            "explicit_user_supplied_files_hashed": explicit_file_count > 0,
            "explicit_user_supplied_hash_scope": "only_individually_authorized_files",
            "deduplication_key": "case_insensitive_normalized_file_identity",
            "source_provenance_preserved": True,
            "manifest_initial_hash_stat_stable": True,
            "manifest_inputs_rehashed_after_import": True,
            "manifest_inputs_unchanged_after_import": True,
            "manifest_input_count_reverified": len(source_rows),
            "effective_root_attribution": "most_specific_declared_root",
            "lane_classification_method": "filename_extension_and_manifest_metadata_heuristics_only",
            "lane_counts_are_content_validated": False,
            "sqlite_temp_store": "memory_not_system_volume",
            "public_receipt_path_free": True,
            "output_volume_preflight": output_volume_preflight,
        },
        "transformation_identity": {
            "builder_sha256": builder_sha256,
            "parser_schema_version": "lumencore_private_universe_parser_v2",
            "sqlite_version": sqlite3.sqlite_version,
            "manifest_post_import_rehash_passed": True,
            "generation_id": generation_id,
            **git_identity,
        },
        "summary": {
            "source_manifest_count": len(source_rows),
            "source_observation_count": observation_count,
            "unique_asset_count": unique_asset_count,
            "duplicate_observation_count": max(
                0, observation_count - unique_asset_count
            ),
            "historical_content_sha256_observation_count": historical_content_hash_observation_count,
            "historical_metadata_sha256_observation_count": historical_metadata_hash_observation_count,
            "historical_content_sha256_conflict_asset_count": hash_conflict_count,
            "explicit_file_count": explicit_file_count,
            "explicit_file_sha256_coverage_count": explicit_file_hash_coverage_count,
            "root_alias_count": scalar(connection, "SELECT COUNT(*) FROM roots"),
            "root_registry_entry_count": scalar(
                connection,
                "SELECT COUNT(*) FROM roots WHERE registry_role IS NOT NULL",
            ),
            "candidate_lane_count": len(lane_counts),
            "archive_reference_asset_count": scalar(
                connection,
                "SELECT COUNT(*) FROM assets WHERE archive_reference = 1",
            ),
            "unmapped_observation_count": scalar(
                connection,
                "SELECT COALESCE(SUM(invalid_observation_count), 0) FROM sources",
            ),
            "reported_root_mismatch_observation_count": scalar(
                connection,
                "SELECT COUNT(*) FROM observations WHERE path_belongs_to_reported_root = 0",
            ),
        },
        "source_summary": [
            {
                "source_kind": row[0],
                "source_sha256": row[1],
                "source_bytes": row[2],
                "source_modified_utc": row[3],
                "manifest_row_count": row[4],
                "observation_count": row[5],
                "invalid_observation_count": row[6],
                "manifest_referenced_file_bytes_read": False,
                "historical_hashes_reverified": False,
            }
            for row in source_rows
        ],
        "candidate_lane_counts": lane_counts,
        "root_summary": {
            "coverage_quality_counts": coverage_counts,
            "registry_role_counts": dict(sorted(registry_role_counts.items())),
            "coverage_is_current_live_truth": False,
            "coverage_flags_are_claim_bounded": True,
        },
        "claim_boundaries": {
            "complete_universe_claim_allowed": False,
            "current_file_existence_claim_allowed": False,
            "content_ownership_claim_allowed": False,
            "field_validation_claim_allowed": False,
            "technical_readiness_claim_allowed": False,
            "valuation_claim_allowed": False,
            "public_filename_disclosure_allowed": False,
            "private_path_disclosure_allowed": False,
        },
    }
    public["receipt_sha256"] = stable_sha256(public)
    assert_public_private_universe_receipt_safe(public)
    return public


def iter_string_values(value: Any) -> Iterator[str]:
    if isinstance(value, str):
        yield value
    elif isinstance(value, dict):
        for key, child in value.items():
            if isinstance(key, str):
                yield key
            yield from iter_string_values(child)
    elif isinstance(value, (list, tuple)):
        for child in value:
            yield from iter_string_values(child)


def assert_public_private_universe_receipt_safe(payload: dict[str, Any]) -> None:
    forbidden = []
    for value in iter_string_values(payload):
        if re.search(r"(?:[A-Za-z]:[\\/]|\\\\)", value):
            forbidden.append("absolute_path")
        if re.search(r"(?:^|[\\/])Users(?:[\\/]|$)", value, flags=re.IGNORECASE):
            forbidden.append("user_profile")
        if "novac" in value.lower():
            forbidden.append("username")
    if forbidden:
        raise ValueError(
            f"Public private-universe receipt failed privacy gate: {sorted(set(forbidden))}"
        )


def build_private_receipt(
    public_receipt: dict[str, Any],
    connection: sqlite3.Connection,
    config: PrivateUniverseConfig,
    database_sha256: str,
    database_bytes: int,
    prior_custody: dict[str, Any],
) -> dict[str, Any]:
    sources = [
        {
            "source_kind": row[0],
            "source_path": row[1],
            "source_sha256": row[2],
            "source_bytes": row[3],
            "manifest_row_count": row[4],
            "observation_count": row[5],
        }
        for row in connection.execute("""
            SELECT source_kind, source_path, source_sha256, source_bytes,
                   manifest_row_count, observation_count
            FROM sources ORDER BY source_kind
            """).fetchall()
    ]
    roots = [
        {
            "root_alias": row[0],
            "root_path": row[1],
            "registry_role": row[2],
            "registry_file_count": row[3],
            "observed_unique_asset_count": row[4],
            "effective_asset_count": row[5],
            "observation_count": row[6],
            "source_count": row[7],
            "coverage_quality": row[8],
            "coverage_flags": json.loads(row[9]),
        }
        for row in connection.execute("""
            SELECT root_alias, normalized_root_path, registry_role, registry_file_count,
                   observed_unique_asset_count, effective_asset_count,
                   observation_count, source_count, coverage_quality, coverage_flags_json
            FROM roots ORDER BY root_alias
            """).fetchall()
    ]
    private_receipt = {
        "schema": "lumencore_private_universe_private_receipt_v1",
        "generation_id": public_receipt["generation_id"],
        "generated_utc": public_receipt["generated_utc"],
        "public_receipt_sha256": public_receipt["receipt_sha256"],
        "database_path": str(config.database_path),
        "database_sha256": database_sha256,
        "database_bytes": database_bytes,
        "source_manifests": sources,
        "root_coverage": roots,
        "prior_latest_custody": prior_custody,
        "custody": {
            "private_context_only": True,
            "source_manifest_files_read_and_parsed": True,
            "manifest_referenced_file_bytes_read": False,
            "referenced_historical_asset_files_opened": False,
            "explicit_file_bytes_read_for_sha256": public_receipt["methodology"][
                "explicit_file_bytes_read_for_sha256"
            ],
            "explicit_file_contents_parsed_or_extracted": False,
            "referenced_historical_asset_contents_parsed_or_extracted": False,
            "archives_unpacked": False,
            "historical_hashes_reverified": False,
            "sqlite_quick_check": public_receipt["transformation_identity"][
                "sqlite_quick_check"
            ],
            "staged_database_quick_check_passed": public_receipt[
                "transformation_identity"
            ]["staged_database_quick_check_passed"],
            "explicit_user_supplied_file_count": public_receipt["summary"][
                "explicit_file_count"
            ],
            "explicit_user_supplied_files_hashed": public_receipt["methodology"][
                "explicit_user_supplied_files_hashed"
            ],
            "atomic_database_replace": True,
        },
        "public_summary": public_receipt,
    }
    private_receipt["private_receipt_sha256"] = stable_sha256(private_receipt)
    return private_receipt


def build_private_universe(
    config: PrivateUniverseConfig | None = None,
) -> dict[str, Any]:
    config = config or PrivateUniverseConfig()
    layout = validate_private_output_layout(config)
    validate_distinct_publish_targets(config, layout)
    config.private_output_dir = layout["private_output_dir"]
    output_estimate = estimate_private_index_output(config)
    output_volume_preflight = check_private_output_volume(
        config.private_output_dir,
        config.minimum_output_free_percent,
        output_estimate,
    )
    config.private_output_dir.mkdir(parents=True, exist_ok=True)
    generation_id = f"generation_{uuid.uuid4().hex}"
    builder_sha256 = sha256_file(Path(__file__))
    git_identity = builder_git_identity()
    temporary_database = config.database_path.with_name(
        f".{config.database_path.name}.{uuid.uuid4().hex}.tmp"
    )
    connection: sqlite3.Connection | None = None
    staged_json_paths: list[Path] = []
    with PrivateUniverseWriterLock(layout["lock_path"]):
        try:
            connection = sqlite3.connect(temporary_database)
            connection.execute("PRAGMA journal_mode = DELETE")
            connection.execute("PRAGMA synchronous = FULL")
            connection.execute("PRAGMA temp_store = MEMORY")
            create_private_universe_schema(connection)
            connection.executemany(
                "INSERT INTO metadata(key, value) VALUES (?, ?)",
                [
                    ("schema", "lumencore_private_universe_sqlite_v1"),
                    ("generation_id", generation_id),
                    ("generated_utc", now_utc()),
                    ("federation_mode", "zero_copy_manifest_federation"),
                    ("source_manifest_files_read_and_parsed", "true"),
                    ("manifest_referenced_file_bytes_read", "false"),
                    ("referenced_historical_asset_files_opened", "false"),
                    ("explicit_file_contents_parsed_or_extracted", "false"),
                    (
                        "referenced_historical_asset_contents_parsed_or_extracted",
                        "false",
                    ),
                    ("archives_unpacked", "false"),
                    ("historical_hashes_reverified", "false"),
                    ("full_live_reconciliation", "false"),
                    ("parser_schema_version", "lumencore_private_universe_parser_v2"),
                    ("builder_sha256", builder_sha256),
                    ("sqlite_version", sqlite3.sqlite_version),
                    ("sqlite_temp_store", "memory_not_system_volume"),
                    ("sqlite_quick_check_required_before_publish", "true"),
                ],
            )
            sources = register_private_sources(connection, config)
            try:
                import_root_registry(connection, sources["root_registry"])
                import_curated_root_summaries(
                    connection, sources["curated_local_icloud_intake"]
                )
                for source_kind in (
                    "fast_index",
                    "scientific_index",
                    "curated_local_icloud_intake",
                    "canonical_estate_inventory",
                ):
                    import_private_observation_source(connection, sources[source_kind])
                explicit_file_count = import_explicit_user_files(
                    connection, config.explicit_files
                )
                verified_manifest_count = verify_registered_manifest_inputs_unchanged(
                    sources
                )
            except (OSError, ValueError, csv.Error, json.JSONDecodeError) as exc:
                raise RuntimeError(
                    "Unable to import a private-universe source "
                    f"({type(exc).__name__}); source paths are withheld."
                ) from None
            effective_root_update_count = assign_most_specific_effective_roots(
                connection
            )
            connection.executemany(
                "INSERT INTO metadata(key, value) VALUES (?, ?)",
                [
                    (
                        "explicit_user_supplied_file_count",
                        str(explicit_file_count),
                    ),
                    (
                        "explicit_file_bytes_read_for_sha256",
                        str(explicit_file_count > 0).lower(),
                    ),
                    ("manifest_initial_hash_stat_stable", "true"),
                    ("manifest_inputs_rehashed_after_import", "true"),
                    ("manifest_inputs_unchanged_after_import", "true"),
                    (
                        "manifest_input_count_reverified",
                        str(verified_manifest_count),
                    ),
                    (
                        "effective_root_attribution_update_count",
                        str(effective_root_update_count),
                    ),
                ],
            )
            finalize_private_root_coverage(connection)
            create_private_indexes(connection)
            public_receipt = build_public_private_universe_receipt(
                connection,
                output_volume_preflight,
                generation_id,
                builder_sha256,
                git_identity,
            )
            connection.commit()
            connection.close()
            connection = None
            with temporary_database.open("r+b") as handle:
                handle.flush()
                os.fsync(handle.fileno())

            quick_check = run_staged_sqlite_quick_check(temporary_database)
            public_receipt["transformation_identity"].update(quick_check)
            database_sha256 = sha256_file(temporary_database)
            database_bytes = temporary_database.stat().st_size
            prior_custody = prepare_prior_private_custody(config)
            public_receipt["private_index_custody"] = {
                "generation_id": generation_id,
                "database_sha256": database_sha256,
                "database_bytes": database_bytes,
                "locator_alias": "private_proof_vault_estate_index_latest",
                "publish_set_artifact_count": 4,
                "atomic_per_artifact_replace": True,
                "rollback_protected_publish_set": True,
                "staged_database_quick_check_passed": quick_check[
                    "staged_database_quick_check_passed"
                ],
                "prior_latest_database_present": prior_custody[
                    "prior_database_present"
                ],
                "prior_latest_database_preserved": prior_custody[
                    "prior_database_preserved"
                ],
                "prior_latest_database_sha256": prior_custody["prior_database_sha256"],
                "prior_latest_database_bytes": prior_custody["prior_database_bytes"],
                "prior_latest_private_receipt_present": prior_custody[
                    "prior_private_receipt_present"
                ],
                "prior_latest_private_receipt_preserved": prior_custody[
                    "prior_private_receipt_preserved"
                ],
                "prior_latest_private_receipt_sha256": prior_custody[
                    "prior_private_receipt_sha256"
                ],
                "prior_latest_private_receipt_bytes": prior_custody[
                    "prior_private_receipt_bytes"
                ],
            }
            public_receipt.pop("receipt_sha256", None)
            public_receipt["receipt_sha256"] = stable_sha256(public_receipt)
            assert_public_private_universe_receipt_safe(public_receipt)

            read_connection = sqlite3.connect(
                f"file:{temporary_database.as_posix()}?mode=ro", uri=True
            )
            try:
                private_receipt = build_private_receipt(
                    public_receipt,
                    read_connection,
                    config,
                    database_sha256,
                    database_bytes,
                    prior_custody,
                )
            finally:
                read_connection.close()

            staged_private_receipt = stage_json_artifact(
                config.private_receipt_path,
                private_receipt,
            )
            staged_json_paths.append(staged_private_receipt)
            staged_public_receipt = stage_json_artifact(
                config.public_receipt,
                public_receipt,
            )
            staged_json_paths.append(staged_public_receipt)
            staged_dashboard_receipt = stage_json_artifact(
                config.dashboard_receipt,
                public_receipt,
            )
            staged_json_paths.append(staged_dashboard_receipt)
            publish_staged_private_universe_artifacts(
                {
                    "database": temporary_database,
                    "private_receipt": staged_private_receipt,
                    "public_receipt": staged_public_receipt,
                    "dashboard_receipt": staged_dashboard_receipt,
                },
                {
                    "database": config.database_path,
                    "private_receipt": config.private_receipt_path,
                    "public_receipt": config.public_receipt,
                    "dashboard_receipt": config.dashboard_receipt,
                },
                prior_custody,
            )
            return public_receipt
        finally:
            if connection is not None:
                connection.close()
            try:
                temporary_database.unlink()
            except OSError:
                pass
            for staged_path in staged_json_paths:
                try:
                    staged_path.unlink()
                except OSError:
                    pass


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Build the canonical LumenCore estate index."
    )
    parser.add_argument(
        "--private-universe",
        action="store_true",
        help="Federate approved historical manifests into the private zero-copy SQLite index.",
    )
    parser.add_argument(
        "--scientific-manifest",
        type=Path,
        default=DEFAULT_PRIVATE_UNIVERSE_SOURCES["scientific_index"],
    )
    parser.add_argument(
        "--fast-manifest",
        type=Path,
        default=DEFAULT_PRIVATE_UNIVERSE_SOURCES["fast_index"],
    )
    parser.add_argument(
        "--canonical-inventory",
        type=Path,
        default=DEFAULT_PRIVATE_UNIVERSE_SOURCES["canonical_estate_inventory"],
    )
    parser.add_argument(
        "--curated-intake",
        type=Path,
        default=DEFAULT_PRIVATE_UNIVERSE_SOURCES["curated_local_icloud_intake"],
    )
    parser.add_argument(
        "--root-registry",
        type=Path,
        default=DEFAULT_PRIVATE_UNIVERSE_SOURCES["root_registry"],
    )
    parser.add_argument("--private-output-dir", type=Path, default=PRIVATE_UNIVERSE_DIR)
    parser.add_argument(
        "--public-receipt", type=Path, default=PRIVATE_UNIVERSE_PUBLIC_RECEIPT
    )
    parser.add_argument(
        "--dashboard-receipt", type=Path, default=PRIVATE_UNIVERSE_DASHBOARD_RECEIPT
    )
    parser.add_argument("--database-name", default=PRIVATE_UNIVERSE_DB_NAME)
    parser.add_argument(
        "--explicit-file",
        type=Path,
        action="append",
        default=[],
        help="Hash and import one explicitly authorized current file; repeat for more files. Directories are rejected.",
    )
    parser.add_argument(
        "--minimum-output-free-percent",
        type=float,
        default=PRIVATE_UNIVERSE_MIN_FREE_PERCENT,
        help="Minimum free-space percentage on the private output volume (production default: 10).",
    )
    return parser.parse_args(argv)


def main() -> None:
    args = parse_args()
    if args.private_universe:
        payload = build_private_universe(
            PrivateUniverseConfig(
                scientific_manifest=args.scientific_manifest,
                fast_manifest=args.fast_manifest,
                canonical_inventory=args.canonical_inventory,
                curated_intake=args.curated_intake,
                root_registry=args.root_registry,
                private_output_dir=args.private_output_dir,
                public_receipt=args.public_receipt,
                dashboard_receipt=args.dashboard_receipt,
                database_name=args.database_name,
                explicit_files=args.explicit_file,
                minimum_output_free_percent=args.minimum_output_free_percent,
            )
        )
        print(
            json.dumps(
                {
                    "status": payload["status"],
                    "schema": payload["schema"],
                    "summary": payload["summary"],
                    "receipt_sha256": payload["receipt_sha256"],
                },
                indent=2,
            )
        )
        return
    payload = build_payload()
    markdown = render_markdown(payload)
    sensitive_hits = scan_sensitive_text(markdown)
    if sensitive_hits:
        raise SystemExit(
            f"Refusing to write sensitive public estate markers: {sensitive_hits}"
        )
    write_json(OUT_JSON, payload)
    write_json(DASHBOARD_JSON, payload)
    write_text(OUT_MD, markdown)
    manifest = output_manifest(payload)
    write_json(OUT_MANIFEST, manifest)
    print(
        json.dumps(
            {
                "status": payload["status"],
                "managed_file_count": payload["summary"]["managed_file_count"],
                "full_inventory_csv": payload["summary"]["full_inventory_csv"],
                "markdown": rel(OUT_MD),
                "inventory_chain_sha256": payload["summary"]["inventory_chain_sha256"],
                "output_manifest": rel(OUT_MANIFEST),
                "output_manifest_sha256": manifest["manifest_sha256"],
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
