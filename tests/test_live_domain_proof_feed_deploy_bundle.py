from __future__ import annotations

import importlib.util
import json
import tarfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "code" / "ops" / "BUILD_LIVE_DOMAIN_PROOF_FEED_DEPLOY_BUNDLE.py"


def load_module():
    spec = importlib.util.spec_from_file_location("live_domain_proof_feed_deploy_bundle", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def seed_workspace(module, tmp_path: Path) -> None:
    module.ROOT = tmp_path
    module.DASHBOARD_DATA = tmp_path / "dashboard" / "data"
    module.OUT_OPS = tmp_path / "out" / "ops"
    module.DOCS = tmp_path / "docs"
    module.DEPLOY_STAGE = tmp_path / ".deploy_stage"
    module.OUT_JSON = tmp_path / "out" / "ops" / "live_domain_proof_feed_deploy_bundle_latest.json"
    module.DASHBOARD_JSON = tmp_path / "dashboard" / "data" / "live_domain_proof_feed_deploy_bundle.json"
    module.OUT_MD = tmp_path / "docs" / "LIVE_DOMAIN_PROOF_FEED_DEPLOY_BUNDLE_2026-06-27.md"
    module.DASHBOARD_DATA.mkdir(parents=True, exist_ok=True)

    for key in module.REQUIRED_FEEDS + module.OPTIONAL_FEEDS:
        payload = {
            "generated_utc": "2026-06-27T00:00:00Z",
            "schema": f"{key}_v1",
            "key": key,
            "rows": 123,
            "claim_boundary": "internal benchmark, not field validation",
        }
        (module.DASHBOARD_DATA / f"{key}.json").write_text(
            json.dumps(payload, sort_keys=True),
            encoding="utf-8",
        )


def test_bundle_copies_each_required_feed_to_both_public_lanes(tmp_path):
    module = load_module()
    seed_workspace(module, tmp_path)

    manifest = module.build_bundle()
    required = [row for row in manifest["feeds"] if row["required"]]

    assert manifest["schema"] == "live_domain_proof_feed_deploy_bundle_v1"
    assert manifest["summary"]["feed_only_deploy_ready"] is True
    assert manifest["summary"]["required_ready_count"] == len(module.REQUIRED_FEEDS)
    assert len(required) == len(module.REQUIRED_FEEDS)
    for row in required:
        targets = {target["relative_path"] for target in row["copied_targets"]}
        assert targets == {
            f"data/{row['key']}.json",
            f"dashboard/data/{row['key']}.json",
        }
        assert row["target_hashes_match"] is True
        assert all(target["sha256"] == row["sha256"] for target in row["copied_targets"])


def test_bundle_manifest_and_archive_exclude_secret_or_bulk_data_paths(tmp_path):
    module = load_module()
    seed_workspace(module, tmp_path)

    manifest = module.build_bundle()
    archive = Path(manifest["archive_path"])

    with tarfile.open(archive, "r:gz") as tar:
        names = tar.getnames()

    assert "manifest.json" in names
    assert all(not name.lower().endswith((".env", ".csv", ".jsonl", ".zip", ".parquet")) for name in names)
    staged_paths = json.dumps(
        [
            target["relative_path"]
            for row in manifest["feeds"]
            for target in row["copied_targets"]
        ]
    ).lower()
    assert "secret" not in staged_paths
    assert manifest["summary"]["publishes_config_or_secrets"] is False
    assert manifest["summary"]["broad_stack_deploy_allowed"] is False
    assert manifest["summary"]["service_restart_required"] is False


def test_missing_required_feed_blocks_deploy_ready(tmp_path):
    module = load_module()
    seed_workspace(module, tmp_path)
    (module.DASHBOARD_DATA / "dollar_claim_gate.json").unlink()

    manifest = module.build_bundle()

    assert manifest["summary"]["feed_only_deploy_ready"] is False
    assert "dollar_claim_gate" in manifest["summary"]["missing_required_feeds"]
    assert manifest["summary"]["required_ready_count"] == len(module.REQUIRED_FEEDS) - 1


def test_markdown_keeps_feed_deploy_separate_from_field_validation_and_money_claims(tmp_path):
    module = load_module()
    seed_workspace(module, tmp_path)

    manifest = module.build_bundle()
    rendered = module.render_markdown(manifest)
    dumped = json.dumps(manifest).lower()

    assert "Live Domain Proof Feed Deploy Bundle" in rendered
    assert "feed-only" in rendered.lower()
    assert "Field-validation claim allowed: `false`" in rendered
    assert "Real-dollar savings claim allowed: `false`" in rendered
    assert "not field validation" in rendered.lower()
    assert "guaranteed grant" not in dumped
    assert "guaranteed profit" not in dumped
    assert "money printer" not in dumped
