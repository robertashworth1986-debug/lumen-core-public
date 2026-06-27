from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import tarfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
DASHBOARD_DATA = ROOT / "dashboard" / "data"
OUT_OPS = ROOT / "out" / "ops"
DOCS = ROOT / "docs"
DEPLOY_STAGE = ROOT / ".deploy_stage"

OUT_JSON = OUT_OPS / "live_domain_proof_feed_deploy_bundle_latest.json"
DASHBOARD_JSON = DASHBOARD_DATA / "live_domain_proof_feed_deploy_bundle.json"
OUT_MD = DOCS / "LIVE_DOMAIN_PROOF_FEED_DEPLOY_BUNDLE_2026-06-27.md"

DEFAULT_REMOTE_WEB_ROOTS = [
    "/opt/lumencore/dashboard",
    "/var/www/lumatrader",
    "/var/www/lumen-core",
]

BOUNDARY = (
    "Feed-only deploy bundle. It stages reviewer proof JSON for domain hash verification. "
    "It does not publish secrets, restart execution services, prove field validation, prove realized savings, "
    "set a fixed dollar value per frozen delta, or imply autonomous live trading permission. This is not field validation."
)

REQUIRED_FEEDS = [
    "champion_metric_gauntlet",
    "kuramoto_holdout_expansion",
    "geometry_champion_of_champions",
    "field_money_truth_sweep",
    "live_proof_value_meter",
    "field_validated_dollar_claim_ladder",
    "dollar_claim_gate",
]

OPTIONAL_FEEDS = [
    "geometry_asset_wiring_board",
    "luma_context_dashboard_parity_audit",
    "live_domain_deployment_feed",
]

FORBIDDEN_NAME_FRAGMENTS = [
    ".env",
    "secret",
    "private",
    "credential",
    "token",
    "api_key",
    "apikey",
    ".csv",
    ".jsonl",
    ".zip",
    ".parquet",
]


def now_utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def stamp_utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True, default=str) + "\n", encoding="utf-8")


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text.rstrip("\r\n") + "\n", encoding="utf-8")


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def stable_sha256(payload: Any) -> str:
    encoded = json.dumps(payload, sort_keys=True, default=str).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def read_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}
    return data if isinstance(data, dict) else {}


def is_forbidden_publish_path(path: Path) -> bool:
    lowered = path.name.lower()
    return any(fragment in lowered for fragment in FORBIDDEN_NAME_FRAGMENTS)


def feed_source_path(key: str) -> Path:
    return DASHBOARD_DATA / f"{key}.json"


def copy_verified_feed(source: Path, targets: list[Path], bundle_root: Path) -> dict[str, Any]:
    if not source.exists() or not source.is_file():
        return {
            "source": str(source.relative_to(ROOT) if source.exists() else source),
            "source_exists": False,
            "sha256": "",
            "bytes": 0,
            "copied_targets": [],
            "target_hashes_match": False,
            "error": "source missing",
        }
    if source.suffix.lower() != ".json" or is_forbidden_publish_path(source):
        return {
            "source": str(source.relative_to(ROOT)),
            "source_exists": True,
            "sha256": "",
            "bytes": source.stat().st_size,
            "copied_targets": [],
            "target_hashes_match": False,
            "error": "source path blocked by feed-only safety policy",
        }

    source_sha = sha256_file(source)
    copied: list[dict[str, Any]] = []
    for target in targets:
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, target)
        copied.append(
            {
                "relative_path": str(target.relative_to(bundle_root)).replace("\\", "/"),
                "absolute_path": str(target),
                "bytes": target.stat().st_size,
                "sha256": sha256_file(target),
            }
        )

    return {
        "source": str(source.relative_to(ROOT)).replace("\\", "/"),
        "source_exists": True,
        "sha256": source_sha,
        "bytes": source.stat().st_size,
        "copied_targets": copied,
        "target_hashes_match": all(row["sha256"] == source_sha for row in copied),
        "error": "",
    }


def make_archive(bundle_root: Path, archive_path: Path) -> None:
    archive_path.parent.mkdir(parents=True, exist_ok=True)
    with tarfile.open(archive_path, "w:gz") as tar:
        for rel in ["manifest.json", "data", "dashboard/data"]:
            path = bundle_root / rel
            if path.exists():
                tar.add(path, arcname=rel)


def build_bundle(include_optional: bool = True, remote_web_roots: list[str] | None = None) -> dict[str, Any]:
    generated = now_utc()
    stamp = stamp_utc()
    remote_roots = remote_web_roots or DEFAULT_REMOTE_WEB_ROOTS
    feed_keys = REQUIRED_FEEDS + (OPTIONAL_FEEDS if include_optional else [])

    bundle_root = DEPLOY_STAGE / f"live_domain_proof_feeds_{stamp}"
    data_dir = bundle_root / "data"
    dashboard_data_dir = bundle_root / "dashboard" / "data"
    bundle_root.mkdir(parents=True, exist_ok=True)

    feed_rows: list[dict[str, Any]] = []
    for key in feed_keys:
        source = feed_source_path(key)
        row = copy_verified_feed(
            source,
            [
                data_dir / f"{key}.json",
                dashboard_data_dir / f"{key}.json",
            ],
            bundle_root,
        )
        row.update(
            {
                "key": key,
                "required": key in REQUIRED_FEEDS,
                "domain_candidate_paths": [
                    f"/data/{key}.json",
                    f"/dashboard/data/{key}.json",
                ],
            }
        )
        feed_rows.append(row)

    required = [row for row in feed_rows if row["required"]]
    missing_required = [row["key"] for row in required if not row["source_exists"] or row["error"]]
    copied_required = [row for row in required if row["source_exists"] and not row["error"] and row["target_hashes_match"]]
    forbidden_hits = [
        target["relative_path"]
        for row in feed_rows
        for target in row.get("copied_targets", [])
        if is_forbidden_publish_path(Path(target["relative_path"]))
    ]

    manifest: dict[str, Any] = {
        "generated_utc": generated,
        "schema": "live_domain_proof_feed_deploy_bundle_v1",
        "purpose": "Stage only reviewer-safe proof feeds for live-domain hash verification.",
        "boundary": BOUNDARY,
        "bundle_root": str(bundle_root),
        "archive_path": str(DEPLOY_STAGE / f"live_domain_proof_feeds_{stamp}.tgz"),
        "remote_web_roots": remote_roots,
        "required_feeds": REQUIRED_FEEDS,
        "optional_feeds": OPTIONAL_FEEDS if include_optional else [],
        "feeds": feed_rows,
        "summary": {
            "required_feed_count": len(REQUIRED_FEEDS),
            "required_ready_count": len(copied_required),
            "optional_feed_count": len(OPTIONAL_FEEDS) if include_optional else 0,
            "feed_only_deploy_ready": len(missing_required) == 0 and not forbidden_hits,
            "missing_required_feeds": missing_required,
            "forbidden_publish_hits": forbidden_hits,
            "broad_stack_deploy_allowed": False,
            "service_restart_required": False,
            "publishes_config_or_secrets": False,
            "field_validation_claim_allowed": False,
            "real_dollar_savings_claim_allowed": False,
            "fixed_frozen_delta_price_claim_allowed": False,
        },
        "safe_deploy_command": (
            ".\\deploy\\PUSH_PROOF_FEEDS_TO_VPS.ps1 "
            f"-BundleRoot \"{bundle_root}\""
        ),
        "dry_run_command": (
            ".\\deploy\\PUSH_PROOF_FEEDS_TO_VPS.ps1 "
            f"-BundleRoot \"{bundle_root}\" -DryRun"
        ),
        "post_deploy_verify_command": "python .\\code\\ops\\BUILD_LIVE_DOMAIN_DEPLOYMENT_FEED.py --timeout 8",
    }

    manifest["bundle_sha256"] = stable_sha256(
        {
            "required_feeds": manifest["required_feeds"],
            "optional_feeds": manifest["optional_feeds"],
            "feeds": [
                {
                    "key": row["key"],
                    "required": row["required"],
                    "sha256": row["sha256"],
                    "target_hashes_match": row["target_hashes_match"],
                }
                for row in feed_rows
            ],
            "summary": manifest["summary"],
        }
    )

    write_json(bundle_root / "manifest.json", manifest)
    archive_path = Path(str(manifest["archive_path"]))
    make_archive(bundle_root, archive_path)
    manifest["archive_sha256"] = sha256_file(archive_path)
    write_json(OUT_JSON, manifest)
    write_json(DASHBOARD_JSON, manifest)
    write_text(OUT_MD, render_markdown(manifest))
    return manifest


def render_markdown(manifest: dict[str, Any]) -> str:
    summary = manifest["summary"]
    lines = [
        "# Live Domain Proof Feed Deploy Bundle",
        "",
        f"Generated UTC: `{manifest['generated_utc']}`",
        f"Bundle root: `{manifest['bundle_root']}`",
        f"Archive: `{manifest['archive_path']}`",
        "",
        "## Decision",
        "",
        (
            "The feed-only deploy bundle is ready. It can publish proof JSON feeds to the public domain paths "
            "without restarting trading, gateway, or dashboard services."
            if summary["feed_only_deploy_ready"]
            else "The feed-only deploy bundle is not ready because required feeds are missing or blocked."
        ),
        "",
        "## Safety Gates",
        "",
        f"- Required ready: `{summary['required_ready_count']}/{summary['required_feed_count']}`",
        f"- Feed-only deploy ready: `{str(summary['feed_only_deploy_ready']).lower()}`",
        f"- Broad stack deploy allowed: `{str(summary['broad_stack_deploy_allowed']).lower()}`",
        f"- Service restart required: `{str(summary['service_restart_required']).lower()}`",
        f"- Publishes config or secrets: `{str(summary['publishes_config_or_secrets']).lower()}`",
        f"- Field-validation claim allowed: `{str(summary['field_validation_claim_allowed']).lower()}`",
        f"- Real-dollar savings claim allowed: `{str(summary['real_dollar_savings_claim_allowed']).lower()}`",
        "",
        "## Feed Table",
        "",
        "| Feed | Required | Source | Copied | SHA-256 |",
        "|---|---:|---|---:|---|",
    ]
    for row in manifest["feeds"]:
        copied_count = len(row.get("copied_targets", []))
        lines.append(
            "| "
            f"`{row['key']}` | "
            f"`{str(row['required']).lower()}` | "
            f"`{row['source']}` | "
            f"`{copied_count}` | "
            f"`{row['sha256'][:12]}` |"
        )
    lines.extend(
        [
            "",
            "## Commands",
            "",
            f"- Dry run: `{manifest['dry_run_command']}`",
            f"- Deploy feeds: `{manifest['safe_deploy_command']}`",
            f"- Verify domain hashes: `{manifest['post_deploy_verify_command']}`",
            "",
            "## Remote Web Roots Tried By Deploy Script",
            "",
        ]
    )
    for root in manifest["remote_web_roots"]:
        lines.append(f"- `{root}`")
    lines.extend(
        [
            "",
            "## Boundary",
            "",
            manifest["boundary"],
            "",
            f"Bundle SHA-256: `{manifest['bundle_sha256']}`",
            f"Archive SHA-256: `{manifest['archive_sha256']}`",
        ]
    )
    return "\n".join(lines)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build a feed-only live-domain proof deploy bundle.")
    parser.add_argument("--required-only", action="store_true", help="Stage only the required proof feeds.")
    parser.add_argument(
        "--remote-web-root",
        action="append",
        default=None,
        help="Remote web root to target. Can be specified multiple times.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    manifest = build_bundle(
        include_optional=not args.required_only,
        remote_web_roots=args.remote_web_root or DEFAULT_REMOTE_WEB_ROOTS,
    )
    print(f"Wrote {OUT_JSON}")
    print(f"Wrote {DASHBOARD_JSON}")
    print(f"Wrote {OUT_MD}")
    print(f"Bundle root: {manifest['bundle_root']}")
    print(f"Archive: {manifest['archive_path']}")
    print(f"Feed-only deploy ready: {manifest['summary']['feed_only_deploy_ready']}")
    return 0 if manifest["summary"]["feed_only_deploy_ready"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
