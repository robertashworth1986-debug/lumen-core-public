from __future__ import annotations

import hashlib
import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "out" / "ops"
GRANTS = ROOT / "grant_submissions"
DOCS = ROOT / "docs"
DASHBOARD_DATA = ROOT / "dashboard" / "data"

JSON_OUT = OUT / "local_icloud_evidence_intake_latest.json"
MD_OUT = GRANTS / "LOCAL_ICLOUD_EVIDENCE_INTAKE_2026-06-21.md"
DOCS_OUT = DOCS / "ROOT_EVIDENCE_VALUATION_BRIDGE_2026-06-22.md"
DASHBOARD_JSON = DASHBOARD_DATA / "local_icloud_evidence_intake.json"

MAX_FILES_PER_ROOT = 2200
MAX_HASH_BYTES = 25 * 1024 * 1024

SCAN_ROOTS = [
    Path("C:/WhiteHole"),
    Path("C:/WhiteHoleLab"),
    Path("C:/Users"),
    Path("C:/LumenLab_Demo_Pack"),
    Path("C:/LumenMacro"),
    Path("C:/LumenOrchestrator"),
    Path("C:/NovaCore"),
    Path("C:/LumenFinanceLab"),
    Path("C:/LumenHybrid"),
    Path("C:/LumenLab"),
    Path("C:/LumaUniverse"),
    Path("C:/LumaTrader"),
    Path("C:/LumenCore"),
    Path("C:/LumenCore_Foundation"),
    Path("C:/LumenCore_GitHub"),
    Path("C:/LumenCore_Government_Review"),
    Path("C:/LumenCore_SBIR"),
    Path("C:/LumenCore_EIA_ProofPack"),
    Path("C:/EchoLock"),
    Path("C:/EchoLockPilot"),
    Path("C:/HyperCore"),
    Path("C:/LumaQuantLab"),
    Path("C:/Users/Novac/iCloudDrive"),
    Path("C:/Users/Novac/DOE_SBIR_LumenCore_PhaseI"),
    Path("C:/Users/Novac/LumenGov"),
    Path("C:/Users/Novac/LumenCoreResearch"),
    Path("C:/Users/Novac/Luma_HardValidation_Lab"),
]

IMAGE_PATHS = [
    Path("C:/Users/Novac/Pictures/iCloud Photos/Photos/26338B61-37B8-4DD4-9DF6-AAC060D7C12E(1).png"),
    Path("C:/Users/Novac/Pictures/iCloud Photos/Photos/7B82BD26-C3CF-4D83-A923-41BFE9F65DD9.png"),
    Path("C:/Users/Novac/Pictures/iCloud Photos/Photos/33F9A5F7-C141-4E0F-93D4-6C94F6EECDD2.png"),
    Path("C:/Users/Novac/Pictures/iCloud Photos/Photos/17D90812-F9B6-4C91-B3BE-DC88DDEB13A9.png"),
    Path("C:/Users/Novac/Pictures/iCloud Photos/Photos/8470CDB9-CE0B-419D-B611-372E174D77A3.png"),
    Path("C:/Users/Novac/Pictures/iCloud Photos/Photos/14CF875E-C0B2-4C5B-853D-A443F449B0E6.png"),
    Path("C:/Users/Novac/Pictures/iCloud Photos/Photos/F9931572-822D-49F6-BDE2-BBBDAF795D40.png"),
    Path("C:/Users/Novac/Pictures/iCloud Photos/Photos/IMG_0A70ED39-73E2-4FB0-9336-BD8EA424470C.jpeg"),
]

EXTENSIONS = {
    ".csv",
    ".docx",
    ".html",
    ".jpeg",
    ".jpg",
    ".json",
    ".md",
    ".pdf",
    ".png",
    ".pptx",
    ".ps1",
    ".stl",
    ".txt",
    ".yaml",
    ".yml",
    ".zip",
}

SKIP_PARTS = {
    "$recycle.bin",
    ".git",
    ".hg",
    ".mypy_cache",
    ".pytest_cache",
    ".ruff_cache",
    ".venv",
    "__pycache__",
    "appdata",
    "cache",
    "cookies",
    "driver license documents_",
    "fidelity_",
    "github token key",
    "kraken api",
    "local settings",
    "node_modules",
    "one drive temp",
    "onedrivetemp",
    "open ai api",
    "program files",
    "program files (x86)",
    "programdata",
    "recent",
    "site-packages",
    "system volume information",
    "test key for grant",
    "windows",
}

SKIP_FILE_MARKERS = {
    ".env",
    "api_keys",
    "id_rsa",
    "private_key",
    "secret",
    "token",
}

LOW_VALUE_PATH_MARKERS = {
    ".dist-info",
    ".egg-info",
    ".venv",
    "__pycache__",
    "node_modules",
    "package-lock",
    "site-packages",
    "umath-validation",
}

CATEGORIES = [
    (
        "frozen_provenance",
        ["chain_of_custody", "freeze", "frozen", "manifest", "sha256", "proofs", "locked", "lock"],
        5,
    ),
    (
        "public_live_sources",
        ["public_deltas", "public_sources", "public_incident", "eia_pull", "source_of_truth", "live_breadth"],
        5,
    ),
    (
        "benchmark_evidence",
        ["benchmark", "baseline", "leaderboard", "champion", "scorecard", "simulation", "monte_carlo", "kpi"],
        4,
    ),
    (
        "valuation_broadening",
        ["valuation", "value", "roi", "savings", "loss_ladder", "cost_reduction", "annual_value", "dollar", "funding"],
        4,
    ),
    (
        "grant_submission",
        ["grant", "sbir", "sttr", "darpa", "dice", "dod", "doe", "arpa", "nsf", "harbor", "navy", "submission"],
        4,
    ),
    (
        "patent_legal",
        ["patent", "provisional", "uspto", "claim", "lawyer", "legal", "invention", "non-prob"],
        4,
    ),
    (
        "docker_ops",
        ["docker", "compose", "watchdog", "maintain", "echolock", "prometheus", "grafana", "exporter", "hypercore"],
        3,
    ),
    (
        "trading_private",
        ["kraken", "trader", "quant", "pnl", "alpha", "execution", "live sharp", "odds"],
        3,
    ),
    (
        "geometry_hardware",
        ["flowform", "lumanspiral", "lumenframe", "glyph", "spiral", "harmonic", "geometry", "stl"],
        3,
    ),
    (
        "commercial_visibility",
        ["pitch", "investor", "business", "commercial", "dashboard", "website", "resume", "social", "deck"],
        2,
    ),
]


def now_utc() -> str:
    return datetime.now(timezone.utc).isoformat()


def norm(text: str) -> str:
    return text.replace("\\", "/").lower()


def is_within_root(path: Path) -> bool:
    try:
        path.resolve().relative_to(ROOT.resolve())
        return True
    except Exception:
        return False


def rel(path: Path) -> str:
    try:
        return path.relative_to(ROOT).as_posix()
    except Exception:
        return str(path).replace("\\", "/")


def should_skip(path: Path) -> bool:
    lowered_parts = {part.lower() for part in path.parts}
    if lowered_parts & SKIP_PARTS:
        return True
    lowered_name = path.name.lower()
    lowered_path = norm(str(path))
    if any(marker in lowered_path for marker in LOW_VALUE_PATH_MARKERS):
        return True
    return any(marker in lowered_name for marker in SKIP_FILE_MARKERS)


def classify(path: Path) -> tuple[list[str], int]:
    text = norm(str(path))
    categories: list[str] = []
    score = 0
    for category, markers, weight in CATEGORIES:
        if any(marker in text for marker in markers):
            categories.append(category)
            score += weight
    if path.suffix.lower() in {".sha256", ".txt"} and "sha256" in text:
        score += 3
    if path.suffix.lower() in {".png", ".jpg", ".jpeg", ".pptx"}:
        score += 1
    if path.suffix.lower() in {".zip"} and any(term in text for term in ["proof", "freeze", "packet"]):
        score += 2
    return categories, score


def recommended_use(categories: list[str], path: Path) -> str:
    suffix = path.suffix.lower()
    category_set = set(categories)
    if "frozen_provenance" in category_set:
        return "usable_now_as_chain_of_custody_or_provenance"
    if "public_live_sources" in category_set:
        return "usable_after_source_and_hash_check_as_public_replay_context"
    if "benchmark_evidence" in category_set and "valuation_broadening" in category_set:
        return "usable_as_candidate_value_signal_after_replay_and_claim_gate"
    if "valuation_broadening" in category_set:
        return "usable_as_valuation_context_not_realized_money"
    if "benchmark_evidence" in category_set:
        return "usable_as_candidate_benchmark_context_after_reproduction"
    if "docker_ops" in category_set:
        return "usable_as_read_only_ops_scaffold_after_health_check"
    if "grant_submission" in category_set:
        return "usable_as_draft_or_prior_submission_context_after_review"
    if "patent_legal" in category_set:
        return "private_legal_context_only_until_counsel_review"
    if "trading_private" in category_set:
        return "private_engineering_only_no_profit_or_grant_claim"
    if "geometry_hardware" in category_set and suffix in {".png", ".jpg", ".jpeg", ".pdf", ".stl"}:
        return "usable_as_concept_visual_or_design_prior_artifact_not_performance_proof"
    if "commercial_visibility" in category_set:
        return "usable_as_marketing_or_commercialization_context_after_claim_cleanup"
    return "review_later"


def grant_lanes(categories: list[str], path: Path) -> list[str]:
    text = norm(str(path))
    lanes: set[str] = set()
    if "grant_submission" in categories:
        lanes.add("federal_grant_context")
    if "public_live_sources" in categories or "frozen_provenance" in categories:
        lanes.add("evidence_provenance")
    if "benchmark_evidence" in categories:
        lanes.add("benchmark_reproduction")
    if "valuation_broadening" in categories:
        lanes.add("valuation_broadening")
    if any(term in text for term in ["eia", "energy", "grid", "echolock", "hypercore", "public_deltas_datacenter"]):
        lanes.add("DOE_or_critical_infrastructure")
    if any(term in text for term in ["dice", "darpa", "dso"]):
        lanes.add("DICE")
    if any(term in text for term in ["harbor", "navy", "ais"]):
        lanes.add("HarborSentinel")
    if "patent_legal" in categories or any(term in text for term in ["flowform", "lumanspiral", "lumenframe"]):
        lanes.add("patent_legal")
    if "trading_private" in categories:
        lanes.add("trading_stack_private")
    if "commercial_visibility" in categories:
        lanes.add("commercialization")
    if "docker_ops" in categories:
        lanes.add("ops_scaffold")
    return sorted(lanes)


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def sidecar_hash(path: Path) -> str:
    for candidate in [
        Path(str(path) + ".sha256.txt"),
        Path(str(path) + ".sha256"),
        path.with_suffix(path.suffix + ".sha256.txt"),
    ]:
        if candidate.exists() and candidate.is_file() and not should_skip(candidate):
            try:
                text = candidate.read_text(encoding="utf-8", errors="ignore")
            except Exception:
                continue
            for token in text.replace("\n", " ").split():
                clean = token.strip().lower()
                if len(clean) == 64 and all(ch in "0123456789abcdef" for ch in clean):
                    return clean
    return ""


def file_record(path: Path, root: Path) -> dict[str, Any] | None:
    if path.suffix.lower() not in EXTENSIONS and not any(term in path.name.lower() for term in ["sha256", "manifest"]):
        return None
    if should_skip(path):
        return None
    categories, score = classify(path)
    if score <= 0:
        return None
    try:
        stat = path.stat()
    except OSError:
        return None
    digest = ""
    digest_mode = "not_hashed"
    if stat.st_size <= MAX_HASH_BYTES and path.is_file():
        try:
            digest = sha256_file(path)
            digest_mode = "computed"
        except Exception:
            digest = ""
    if not digest:
        digest = sidecar_hash(path)
        digest_mode = "sidecar" if digest else "large_or_unavailable"
    return {
        "path": rel(path),
        "absolute_path": str(path),
        "root": str(root),
        "bytes": stat.st_size,
        "last_write_utc": datetime.fromtimestamp(stat.st_mtime, tz=timezone.utc).isoformat(),
        "extension": path.suffix.lower(),
        "categories": categories,
        "score": score,
        "sha256": digest,
        "sha256_mode": digest_mode,
        "recommended_use": recommended_use(categories, path),
        "grant_lanes": grant_lanes(categories, path),
    }


def scan_root(root: Path) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    records: list[dict[str, Any]] = []
    seen = 0
    skipped = 0
    if not root.exists():
        return records, {"root": str(root), "exists": False, "seen": 0, "skipped": 0, "kept": 0}
    for dirpath, dirnames, filenames in os.walk(root):
        base = Path(dirpath)
        dirnames[:] = [name for name in dirnames if not should_skip(base / name)]
        if should_skip(base):
            skipped += 1
            dirnames[:] = []
            continue
        for name in filenames:
            seen += 1
            path = base / name
            if should_skip(path):
                skipped += 1
                continue
            record = file_record(path, root)
            if record:
                records.append(record)
            if seen >= MAX_FILES_PER_ROOT:
                return records, {
                    "root": str(root),
                    "exists": True,
                    "seen": seen,
                    "skipped": skipped,
                    "kept": len(records),
                    "truncated": True,
                }
    return records, {
        "root": str(root),
        "exists": True,
        "seen": seen,
        "skipped": skipped,
        "kept": len(records),
        "truncated": False,
    }


def image_records() -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for path in IMAGE_PATHS:
        if not path.exists() or should_skip(path):
            continue
        record = file_record(path, path.parent)
        if not record:
            try:
                stat = path.stat()
            except OSError:
                continue
            record = {
                "path": rel(path),
                "absolute_path": str(path),
                "root": str(path.parent),
                "bytes": stat.st_size,
                "last_write_utc": datetime.fromtimestamp(stat.st_mtime, tz=timezone.utc).isoformat(),
                "extension": path.suffix.lower(),
                "categories": ["geometry_hardware", "commercial_visibility"],
                "score": 4,
                "sha256": sha256_file(path) if stat.st_size <= MAX_HASH_BYTES else "",
                "sha256_mode": "computed" if stat.st_size <= MAX_HASH_BYTES else "large_or_unavailable",
                "recommended_use": "usable_as_concept_visual_or_design_prior_artifact_not_performance_proof",
                "grant_lanes": ["commercialization", "patent_legal"],
            }
        rows.append(record)
    return rows


def summarize(records: list[dict[str, Any]]) -> dict[str, Any]:
    by_use: dict[str, int] = {}
    by_category: dict[str, int] = {}
    by_lane: dict[str, int] = {}
    for record in records:
        by_use[record["recommended_use"]] = by_use.get(record["recommended_use"], 0) + 1
        for category in record["categories"]:
            by_category[category] = by_category.get(category, 0) + 1
        for lane in record["grant_lanes"]:
            by_lane[lane] = by_lane.get(lane, 0) + 1
    return {
        "records": len(records),
        "by_recommended_use": dict(sorted(by_use.items())),
        "by_category": dict(sorted(by_category.items())),
        "by_grant_lane": dict(sorted(by_lane.items())),
    }


def top_records(records: list[dict[str, Any]], *, limit: int = 80) -> list[dict[str, Any]]:
    return sorted(
        records,
        key=lambda row: (int(row["score"]), int(row["bytes"] > 0), str(row["last_write_utc"])),
        reverse=True,
    )[:limit]



def valuation_bridge(records: list[dict[str, Any]]) -> dict[str, Any]:
    candidate_uses = {
        "usable_now_as_chain_of_custody_or_provenance",
        "usable_after_source_and_hash_check_as_public_replay_context",
        "usable_as_candidate_value_signal_after_replay_and_claim_gate",
        "usable_as_candidate_benchmark_context_after_reproduction",
        "usable_as_valuation_context_not_realized_money",
    }
    rows = [
        record
        for record in records
        if record["recommended_use"] in candidate_uses
    ]
    top = top_records(rows, limit=30)
    by_root: dict[str, int] = {}
    for record in rows:
        by_root[record["root"]] = by_root.get(record["root"], 0) + 1
    return {
        "candidate_count": len(rows),
        "top_candidate_count": len(top),
        "candidate_roots": dict(sorted(by_root.items(), key=lambda item: item[1], reverse=True)),
        "top_candidates": top,
        "safe_use": [
            "Use provenance and SHA records to strengthen custody language.",
            "Use public/live source records only after source-rights, hash, and replay checks.",
            "Use benchmark and leaderboard artifacts as reproduction targets, not final performance claims.",
            "Use valuation files as hypothesis/context until replayed against frozen baselines.",
        ],
        "blocked_claims": [
            "No realized revenue, customer savings, government savings, or company valuation from metadata intake.",
            "No trading-profit, live-execution, CMMC, field-validation, or award-likelihood claim from old folders.",
            "No portal upload of old packets until each artifact passes solicitation relevance and privacy review.",
        ],
    }

def render_markdown(payload: dict[str, Any]) -> str:
    summary = payload["summary"]
    top = payload["top_records"]
    bridge = payload["valuation_bridge"]
    lines = [
        "# Local + iCloud Evidence Intake",
        "",
        f"Generated UTC: `{payload['generated_utc']}`",
        "",
        "## Boundary",
        "",
        "This is a non-destructive metadata intake. It does not upload, submit, certify, trade, or expose secrets. "
        "Sensitive credential, personal-ID, API-key, and account folders were skipped or kept out of the report.",
        "",
        "## Summary",
        "",
        f"- Candidate records kept: {summary['records']}",
        f"- Roots inspected: {len(payload['roots'])}",
        "- Best current use: provenance, grant context, read-only ops scaffold, patent/legal context, benchmark reproduction targets, valuation context, and concept visuals.",
        "- Not proof by itself: screenshots, marketing images, old zips, trading folders, valuation spreadsheets, and Docker scaffolds without fresh health checks.",
        "",
        "## Recommended Use Counts",
        "",
    ]
    for use, count in summary["by_recommended_use"].items():
        lines.append(f"- {use}: {count}")
    lines.extend(["", "## Grant/Workstream Counts", ""])
    for lane, count in summary["by_grant_lane"].items():
        lines.append(f"- {lane}: {count}")
    lines.extend(["", "## Valuation Bridge", ""])
    lines.append(f"- Candidate artifacts that can broaden valuation after gates: {bridge['candidate_count']}")
    lines.append("- Safe use:")
    for item in bridge["safe_use"]:
        lines.append(f"  - {item}")
    lines.append("- Blocked claims:")
    for item in bridge["blocked_claims"]:
        lines.append(f"  - {item}")
    lines.extend(["", "### Top Valuation Candidates", ""])
    for idx, record in enumerate(bridge["top_candidates"][:12], start=1):
        lanes = ", ".join(record["grant_lanes"]) or "review"
        lines.append(f"{idx}. `{record['path']}` - {record['recommended_use']} ({lanes})")
    lines.extend(
        [
            "",
            "## High-Value Candidate Records",
            "",
            "| # | Use | Lanes | Categories | Bytes | SHA mode | Path |",
            "|---:|---|---|---|---:|---|---|",
        ]
    )
    for idx, record in enumerate(top[:40], start=1):
        lines.append(
            f"| {idx} | {record['recommended_use']} | {', '.join(record['grant_lanes']) or 'review'} | "
            f"{', '.join(record['categories'])} | {record['bytes']} | {record['sha256_mode']} | `{record['path']}` |"
        )
    lines.extend(
        [
            "",
            "## WhiteHole / Docker / Popup Findings",
            "",
            "- `WhiteHole-Maintain` is the likely visible popup source: it runs `C:/WhiteHole/wh_maintain.ps1`, calls Microsoft Update, and writes interactive output.",
            "- `WhiteHole-DockerWatchdog` is useful evidence of an ops scaffold, but Docker was not reachable during inspection, so container health is not currently proven.",
            "- `EchoLock_Stethoscope_Pilot/docker-compose.yml` is usable as a read-only Prometheus/Grafana pilot scaffold after a fresh Docker health check.",
            "- Do not use Docker logs as uptime proof until the daemon is running and container statuses are freshly captured.",
            "",
            "## What Can Be Used Now",
            "",
            "- Chain-of-custody, manifest, and SHA-256 records can support provenance and work-history claims.",
            "- Public source/delta files can support public replay-context claims after source and hash checks.",
            "- Existing grant, pilot, and executive abstract files can seed cleaner proposal language after claim cleanup.",
            "- Benchmark, leaderboard, KPI, and value artifacts can identify reproduction targets for stronger valuation lanes.",
            "- FlowForm/LumanSpiral/LumenFrame images and STL/design files can support architecture visuals and patent-context discussions, not performance claims.",
            "",
            "## Stop Lines",
            "",
            "- Do not cite API-key, account, SAM/UEI/CAGE, driver-license, banking, or exchange-login folders.",
            "- Do not claim field validation, customer savings, trading profit, CMMC certification, award likelihood, or operational deployment from this intake.",
            "- Do not upload huge old evidence zips into portals unless a specific solicitation asks for them and the contents are reviewed.",
            "",
        ]
    )
    return "\n".join(lines)


def build_payload() -> dict[str, Any]:
    all_records: list[dict[str, Any]] = []
    root_summaries: list[dict[str, Any]] = []
    for root in SCAN_ROOTS:
        records, summary = scan_root(root)
        all_records.extend(records)
        root_summaries.append(summary)
    all_records.extend(image_records())
    unique: dict[str, dict[str, Any]] = {}
    for record in all_records:
        unique[record["absolute_path"]] = record
    records = list(unique.values())
    payload = {
        "schema": "local_icloud_evidence_intake_v1",
        "generated_utc": now_utc(),
        "claim_gate": {
            "ready_for_portal_upload": False,
            "ready_for_submit": False,
            "contains_secret_values": False,
            "field_validation_proven": False,
            "trading_profit_proven": False,
            "boundary": "Metadata intake only; each artifact needs claim-specific review before grant, legal, public, or trading use.",
        },
        "roots": root_summaries,
        "summary": summarize(records),
        "top_records": top_records(records),
        "valuation_bridge": valuation_bridge(records),
        "records": sorted(records, key=lambda row: row["absolute_path"]),
    }
    return payload


def write_outputs(payload: dict[str, Any]) -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    GRANTS.mkdir(parents=True, exist_ok=True)
    DOCS.mkdir(parents=True, exist_ok=True)
    DASHBOARD_DATA.mkdir(parents=True, exist_ok=True)
    for path in [JSON_OUT, DASHBOARD_JSON, MD_OUT, DOCS_OUT]:
        path.parent.mkdir(parents=True, exist_ok=True)
    JSON_OUT.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    DASHBOARD_JSON.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    markdown = render_markdown(payload)
    MD_OUT.write_text(markdown, encoding="utf-8")
    DOCS_OUT.write_text(markdown, encoding="utf-8")


def main() -> int:
    payload = build_payload()
    write_outputs(payload)
    print(
        json.dumps(
            {
                "schema": payload["schema"],
                "records": payload["summary"]["records"],
                "roots": len(payload["roots"]),
                "json": rel(JSON_OUT),
                "dashboard_json": rel(DASHBOARD_JSON),
                "markdown": rel(MD_OUT),
                "docs_markdown": rel(DOCS_OUT),
                "valuation_candidates": payload["valuation_bridge"]["candidate_count"],
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
