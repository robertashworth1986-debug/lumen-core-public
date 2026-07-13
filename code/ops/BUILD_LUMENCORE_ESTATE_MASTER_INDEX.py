from __future__ import annotations

import csv
import hashlib
import json
import os
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


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
    "agency_protocol": ("sam", "sbir", "sttr", "darpa", "nsf", "nasa", "fhwa", "erdc", "bop", "dod", "grant", "rfi", "cso", "baa", "federal"),
    "proof_stack": ("proof", "evidence", "audit", "hash", "sha256", "manifest", "ledger", "gate", "reviewer", "validation"),
    "ip_patent": ("ip", "patent", "uspto", "claim", "invention", "counsel", "provisional", "nonprovisional"),
    "quant_trading": ("quant", "trading", "kraken", "alpaca", "paper", "sharpe", "edge", "order", "execution"),
    "geometry_engine": ("geometry", "kuramoto", "brachistochrone", "flowform", "harmonic", "phase", "resonance", "champion"),
    "live_source": ("live", "source", "eia", "faa", "noaa", "nasa", "weather", "ais", "harbor", "breadth"),
    "revenue_pilot": ("revenue", "pilot", "customer", "commercial", "valuation", "paid", "buyer", "outreach"),
    "dashboard_ops": ("dashboard", "mission", "control", "panel", "frontend", "site", "html"),
    "infrastructure_energy": ("grid", "energy", "nuclear", "utility", "infrastructure", "datacenter", "cooling"),
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
    return hashlib.sha256(json.dumps(payload, sort_keys=True, default=str).encode("utf-8")).hexdigest()


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
    path.write_text(json.dumps(payload, indent=2, sort_keys=True, default=str) + "\n", encoding="utf-8")


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
        digest.update(json.dumps(record, sort_keys=True, separators=(",", ":")).encode("utf-8"))
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
    if "/code/" in f"/{lowered}" or ext in {".py", ".ps1", ".sh", ".ts", ".js", ".yml", ".yaml", ".toml"}:
        return "source_code_or_automation"
    if "/out/" in f"/{lowered}" or "ledger" in lowered:
        return "machine_output_or_ledger"
    if "/data/" in f"/{lowered}" or ext in {".csv", ".jsonl", ".parquet", ".xlsx", ".txt"}:
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
    if cls in {"funding_submission_artifact", "document_or_review_packet"} and lowered.endswith((".md", ".pdf", ".pptx", ".docx")):
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
        else sha256_file(path)
        if mode == "content_sha256"
        else ""
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
    large_deferred = [row for row in rows if row["hash_mode"] == "metadata_hash_only_large_file"]
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
    for concept_id, count in sorted(concept_counts.items(), key=lambda item: (-item[1], item[0])):
        concept_registry.append(
            {
                "concept_id": concept_id,
                "file_count": count,
                "example_paths": concept_examples[concept_id],
                "concept_sha256": stable_sha256({"concept_id": concept_id, "count": count, "examples": concept_examples[concept_id]}),
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
            "large_file_deferred_content_hash_count": hash_mode_counts.get("metadata_hash_only_large_file", 0),
            "sensitive_metadata_only_count": hash_mode_counts.get("metadata_hash_only_sensitive_path", 0),
            "inventory_chain_sha256": inventory_chain_sha256(rows),
            "inventory_csv_sha256": sha256_file(OUT_CSV),
            "full_inventory_csv": rel(OUT_CSV),
            "full_inventory_csv_bytes": OUT_CSV.stat().st_size if OUT_CSV.exists() else 0,
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


def main() -> None:
    payload = build_payload()
    markdown = render_markdown(payload)
    sensitive_hits = scan_sensitive_text(markdown)
    if sensitive_hits:
        raise SystemExit(f"Refusing to write sensitive public estate markers: {sensitive_hits}")
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
