from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
GRANTS = ROOT / "dashboard" / "grants.html"
THEME = ROOT / "dashboard" / "assets" / "lumencore.js"


def test_public_grants_dashboard_defaults_to_reviewer_mode() -> None:
    html = GRANTS.read_text(encoding="utf-8")

    assert "window.LUMA_REVIEWER_MODE = !(localHost && params.get('operator') === '1')" in html
    assert "grant_reviewer_feed_v2" in html
    assert "grant_reviewer_feed.json" in html
    assert "Reviewer-safe view" in html
    assert "if (REVIEWER_MODE)" in html
    assert "private application packets" in html
    assert "curated opportunities" in html
    assert "local dossiers indexed" in html
    assert "discovery match ${(score * 100).toFixed(0)}%" not in html
    assert "$3.53M addressable" not in html


def test_reviewer_mode_exposes_freshness_authority_and_exact_receipt_semantics() -> None:
    html = GRANTS.read_text(encoding="utf-8")

    assert "Stale snapshot - reverify deadlines" in html
    assert "TOPIC_MIRROR_VERIFIED_DSIP_RECHECK_REQUIRED" in html
    assert "Unofficial topic mirror - DSIP recheck required" in html
    assert "ZERO_RECORDS_CAUSE_UNVERIFIED" in html
    assert "zero records; cause unverified" in html
    assert "RATE_LIMITED_INCONCLUSIVE" in html
    assert "rate limited; inconclusive" in html
    assert "HTTP_404_EMPTY_RESPONSE_INCONCLUSIVE" in html
    assert "empty HTTP 404; inconclusive" in html
    assert "SAM key rotation overdue; replacement not detected" in html
    assert "successful_submission_or_received" in html
    assert "agency_tracking_assigned" in html
    assert "agency_received" in html
    assert "agency-validated" not in html
    assert "UPSTREAM_API_UNAVAILABLE_DURING_HARVEST" not in html
    assert "UPSTREAM_API_MAINTENANCE_OR_RATE_LIMIT_DURING_HARVEST" not in html


def test_reviewer_mode_does_not_boot_operator_command_fabric_or_live_visuals() -> None:
    html = GRANTS.read_text(encoding="utf-8")
    theme = THEME.read_text(encoding="utf-8")

    assert "if (!window.LUMA_REVIEWER_MODE)" in html
    assert "const STATIC_REVIEWER = Boolean(window.LUMA_REVIEWER_MODE)" in theme
    assert "const wsUrl = STATIC_REVIEWER ? ''" in theme
    assert "if (!STATIC_REVIEWER && window.THREE)" in theme


def test_reviewer_route_precedes_private_detail_loading() -> None:
    html = GRANTS.read_text(encoding="utf-8")
    load_detail = html.index("async function loadDetail(id)")
    reviewer_branch = html.index("if (REVIEWER_MODE)", load_detail)
    private_api = html.index("const d = await api(`/api/grants/", load_detail)

    assert reviewer_branch < private_api
