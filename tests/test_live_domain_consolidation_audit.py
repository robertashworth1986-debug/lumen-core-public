from __future__ import annotations

import importlib.util
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "code" / "ops" / "BUILD_LIVE_DOMAIN_CONSOLIDATION_AUDIT.py"


def load_module():
    spec = importlib.util.spec_from_file_location("live_domain_consolidation_audit", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def fake_html(title: str, body: str, links: list[str] | None = None) -> bytes:
    link_html = "\n".join(f'<a href="{href}">{href}</a>' for href in links or [])
    return f"<html><head><title>{title}</title></head><body>{body}{link_html}</body></html>".encode("utf-8")


def seed_workspace(module, tmp_path: Path) -> None:
    module.OUT_OPS = tmp_path / "out" / "ops"
    module.DOCS = tmp_path / "docs"
    module.DASHBOARD_DATA = tmp_path / "dashboard" / "data"
    module.LIVE_DOMAIN_FEED = module.OUT_OPS / "live_domain_deployment_feed_latest.json"
    module.CHAMPION_BRIDGE = module.OUT_OPS / "champion_sample_expansion_and_economic_bridge_latest.json"
    module.OUT_JSON = module.OUT_OPS / "live_domain_consolidation_audit_latest.json"
    module.DASHBOARD_JSON = module.DASHBOARD_DATA / "live_domain_consolidation_audit.json"
    module.OUT_MD = module.DOCS / "LIVE_DOMAIN_CONSOLIDATION_AUDIT_2026-06-30.md"
    module.OUT_OPS.mkdir(parents=True, exist_ok=True)

    module.LIVE_DOMAIN_FEED.write_text(
        json.dumps(
            {
                "summary": {
                    "local_required_ready": True,
                    "live_domain_reviewer_ready": False,
                    "required_feed_count": 11,
                    "required_remote_hash_match_count": 5,
                    "required_remote_reachable_count": 8,
                },
                "required_remote_missing_or_stale": [
                    {"key": "champion_metric_gauntlet"},
                    {"key": "field_validation_control_room"},
                ],
            }
        ),
        encoding="utf-8",
    )
    module.CHAMPION_BRIDGE.write_text(
        json.dumps(
            {
                "summary": {
                    "wave_resonance_win_rate": 1.0,
                    "estimated_rows_replayed": 7_289_287,
                }
            }
        ),
        encoding="utf-8",
    )


def fake_fetch_url(url: str) -> dict:
    pages = {
        "https://lumen-core.ai/": fake_html(
            "LumenCore Operator Home",
            "This page mentions guaranteed profit and billion sector math.",
            [
                "/mission_control.html",
                "/quant_lab.html",
                "/grants.html",
                "/evidence/",
                "/kraken_execution_dashboard.html",
                "/missing.html",
                "/assets/lumencore.css",
            ],
        ),
        "https://lumen-core.ai/mission_control.html": fake_html(
            "LumenCore - Mission Control",
            "Executive surface with realized proof language.",
        ),
        "https://lumen-core.ai/quant_lab.html": fake_html(
            "Luma Quant Lab",
            "Technical evidence surface with baseline rows.",
        ),
        "https://lumen-core.ai/grants.html": fake_html(
            "LumenCore - Grants Console",
            "Funding submission surface.",
        ),
        "https://lumen-core.ai/evidence/": fake_html(
            "LumenCore - Undeniable Evidence",
            "Hash chained evidence ledger.",
        ),
        "https://lumen-core.ai/kraken_execution_dashboard.html": fake_html(
            "LumenCore - Kraken Execution Mission Control",
            "Paper trading surface.",
        ),
    }
    if url in pages:
        return {
            "ok": True,
            "status": 200,
            "url": url,
            "content_type": "text/html",
            "bytes": len(pages[url]),
            "body": pages[url],
            "error": "",
        }
    if url == "https://lumen-core.ai/assets/lumencore.css":
        body = b"body { color: white; }"
        return {
            "ok": True,
            "status": 200,
            "url": url,
            "content_type": "text/css",
            "bytes": len(body),
            "body": body,
            "error": "",
        }
    return {
        "ok": False,
        "status": None,
        "url": url,
        "content_type": "",
        "bytes": 0,
        "body": b"",
        "error": "HTTP Error 404: Not Found",
    }


def test_live_domain_audit_catches_stale_feeds_broken_links_and_claim_boundaries(tmp_path, monkeypatch):
    module = load_module()
    seed_workspace(module, tmp_path)
    monkeypatch.setattr(module, "fetch_url", fake_fetch_url)

    payload = module.build_payload()
    summary = payload["summary"]
    classification = payload["classification"]

    assert payload["schema"] == "live_domain_consolidation_audit_v1"
    assert summary["public_domain_up"] is True
    assert summary["live_domain_reviewer_ready"] is False
    assert summary["required_remote_hash_match_count"] == 5
    assert summary["stale_required_feed_count"] == 2
    assert summary["wave_resonance_win_rate"] == 1.0
    assert summary["estimated_rows_replayed"] == 7_289_287
    assert summary["field_validation_claim_allowed"] is False
    assert summary["real_dollar_savings_claim_allowed"] is False
    assert summary["fixed_frozen_delta_price_claim_allowed"] is False

    broken_urls = {row["url"] for row in classification["broken_internal_links"]}
    assert "https://lumen-core.ai/missing.html" in broken_urls
    assert any("kraken" in row["url"] for row in classification["demote_or_internalize"])
    assert any("guaranteed" in row["risk_terms_seen"] for row in classification["risk_language_review"])

    module.write_outputs(payload)
    rendered = module.OUT_MD.read_text(encoding="utf-8")
    dumped = json.dumps(payload).lower()
    assert module.OUT_JSON.exists()
    assert module.DASHBOARD_JSON.exists()
    assert "Live Domain Consolidation Audit" in rendered
    assert "Live-domain reviewer ready: `False`" in rendered
    assert "Field-validation claim allowed: `False`" in rendered
    assert "Real-dollar savings claim allowed: `False`" in rendered
    assert "money printer" not in dumped
