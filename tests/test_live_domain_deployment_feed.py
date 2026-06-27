from __future__ import annotations

import importlib.util
import json
from pathlib import Path
from urllib.parse import urlparse


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "code" / "ops" / "BUILD_LIVE_DOMAIN_DEPLOYMENT_FEED.py"


def load_module():
    spec = importlib.util.spec_from_file_location("live_domain_deployment_feed", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def seed_workspace(module, tmp_path: Path) -> Path:
    module.ROOT = tmp_path
    module.OUT_OPS = tmp_path / "out" / "ops"
    module.DOCS = tmp_path / "docs"
    module.DASHBOARD = tmp_path / "dashboard"
    module.DASHBOARD_DATA = tmp_path / "dashboard" / "data"
    module.PRODUCTION_MANIFEST = tmp_path / "dashboard" / "PRODUCTION_MANIFEST.json"
    module.OUT_JSON = tmp_path / "out" / "ops" / "live_domain_deployment_feed_latest.json"
    module.DASHBOARD_JSON = tmp_path / "dashboard" / "data" / "live_domain_deployment_feed.json"
    module.OUT_MD = tmp_path / "docs" / "LIVE_DOMAIN_DEPLOYMENT_FEED_2026-06-27.md"
    module.DASHBOARD_DATA.mkdir(parents=True, exist_ok=True)
    module.PRODUCTION_MANIFEST.write_text(
        json.dumps({"deployment_domain": "https://example.test"}),
        encoding="utf-8",
    )

    for spec in module.PROOF_FEEDS:
        path = tmp_path / spec["local"]
        path.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "generated_utc": "2026-06-27T00:00:00+00:00",
            "schema": f"{spec['key']}_v1",
            "key": spec["key"],
        }
        if spec["key"] == "champion_metric_gauntlet":
            payload.update(
                {
                    "summary": {
                        "holdout_wins": 24,
                        "holdout_count": 24,
                        "holdout_win_rate": 1.0,
                        "estimated_rows_replayed": 2_506_267,
                        "source_system_count": 4,
                        "buyer_authorized_field_replay_request_ready": True,
                    },
                    "strongest_current": {
                        "family": "kuramoto_phase_coupling",
                        "label": "Kuramoto phase coupling",
                        "named_baseline": "kalman_filter",
                    },
                }
            )
        path.write_text(json.dumps(payload, sort_keys=True), encoding="utf-8")
    return module.DASHBOARD_DATA


def fake_fetch_matching(module, data_dir: Path):
    def fake_fetch(url: str, timeout: int = 10):
        key = Path(urlparse(url).path).stem
        data = (data_dir / f"{key}.json").read_bytes()
        return {
            "ok": True,
            "url": url,
            "status": 200,
            "bytes": len(data),
            "sha256": module.sha256_bytes(data),
            "content_type": "application/json",
            "error": "",
        }

    return fake_fetch


def test_skip_live_check_reports_local_ready_but_not_domain_verified(tmp_path):
    module = load_module()
    seed_workspace(module, tmp_path)

    payload = module.build_payload(check_live_domain=False)
    summary = payload["summary"]

    assert payload["schema"] == "live_domain_deployment_feed_v1"
    assert summary["local_required_ready"] is True
    assert summary["live_domain_reviewer_ready"] is False
    assert summary["required_remote_hash_match_count"] == 0
    assert summary["field_validation_claim_allowed"] is False
    assert summary["real_dollar_savings_claim_allowed"] is False


def test_all_required_hosted_hashes_matching_makes_domain_reviewer_ready(tmp_path, monkeypatch):
    module = load_module()
    data_dir = seed_workspace(module, tmp_path)
    monkeypatch.setattr(module, "fetch_url_bytes", fake_fetch_matching(module, data_dir))

    payload = module.build_payload(check_live_domain=True)
    summary = payload["summary"]
    required = [row for row in payload["feeds"] if row["required"]]

    assert summary["live_domain_reviewer_ready"] is True
    assert summary["domain_deployment_state"] == "LIVE_DOMAIN_HASH_VERIFIED"
    assert summary["required_remote_hash_match_count"] == len(required)
    assert payload["current_champion"]["family"] == "kuramoto_phase_coupling"
    assert payload["current_champion"]["field_validation_claim_allowed"] is False
    assert payload["current_champion"]["real_dollar_savings_claim_allowed"] is False


def test_stale_required_feed_blocks_reviewer_ready_even_if_reachable(tmp_path, monkeypatch):
    module = load_module()
    data_dir = seed_workspace(module, tmp_path)

    def fake_fetch(url: str, timeout: int = 10):
        key = Path(urlparse(url).path).stem
        if key == "champion_metric_gauntlet":
            data = b'{"stale": true}'
        else:
            data = (data_dir / f"{key}.json").read_bytes()
        return {
            "ok": True,
            "url": url,
            "status": 200,
            "bytes": len(data),
            "sha256": module.sha256_bytes(data),
            "content_type": "application/json",
            "error": "",
        }

    monkeypatch.setattr(module, "fetch_url_bytes", fake_fetch)
    payload = module.build_payload(check_live_domain=True)

    assert payload["summary"]["live_domain_reviewer_ready"] is False
    assert payload["summary"]["domain_deployment_state"] == "LOCAL_READY_DOMAIN_NOT_VERIFIED_OR_STALE"
    assert any(row["key"] == "champion_metric_gauntlet" for row in payload["required_remote_missing_or_stale"])


def test_markdown_keeps_public_deployment_separate_from_field_validation(tmp_path, monkeypatch):
    module = load_module()
    data_dir = seed_workspace(module, tmp_path)
    monkeypatch.setattr(module, "fetch_url_bytes", fake_fetch_matching(module, data_dir))
    payload = module.build_payload(check_live_domain=True)
    rendered = module.render_markdown(payload)
    dumped = json.dumps(payload).lower()

    assert "Live Domain Deployment Feed" in rendered
    assert "Live-domain reviewer-ready: `true`" in rendered
    assert "Field-validation claim allowed: `false`" in rendered
    assert "Real-dollar savings claim allowed: `false`" in rendered
    assert "not field validation" in rendered.lower()
    assert "guaranteed grant" not in dumped
    assert "guaranteed profit" not in dumped
    assert "money printer" not in dumped
