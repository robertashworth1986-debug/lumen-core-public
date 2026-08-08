from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DASHBOARD = ROOT / "dashboard"


PAGES = {
    "home": "operator_home.html",
    "mission": "mission_control.html",
    "quant": "quant_lab.html",
    "grants": "grants.html",
    "trade": "kraken_execution_dashboard.html",
}


def page(name: str) -> str:
    return (DASHBOARD / PAGES[name]).read_text(encoding="utf-8")


def test_five_canonical_surfaces_share_identity_and_runtime_layer():
    for surface in PAGES:
        body = page(surface)
        assert f'data-luma-surface="{surface}"' in body
        assert '/assets/lumaarc_arc_seal_v1.png' in body
        assert "assets/luma_institutional_surface.css" in body
        assert "assets/luma_institutional_surface.js" in body
        assert "assets/luma_command_fabric.js" in body


def test_founder_confirmed_lumaarc_is_the_shared_dashboard_mark():
    asset_name = "lumaarc_arc_seal_v1.png"
    public_mark = DASHBOARD / "assets" / asset_name
    brand_master = ROOT / "assets" / "brand" / asset_name
    assert public_mark.read_bytes() == brand_master.read_bytes()

    shared_css = (DASHBOARD / "assets" / "luma_institutional_surface.css").read_text(
        encoding="utf-8"
    )
    shared_fabric = (DASHBOARD / "assets" / "luma_command_fabric.js").read_text(
        encoding="utf-8"
    )
    assert asset_name in shared_css
    assert asset_name in shared_fabric
    assert "lumencore-mark.svg" not in shared_css
    assert "lumencore-mark.svg" not in shared_fabric

    assert "LUMEN<span>CORE</span>" in page("home")
    assert "<h1>LUMENCORE</h1>" in page("mission")
    assert "LUMENCORE / QUANT LAB" in page("quant")
    assert "Lumen<span>Core</span>" in page("trade")
    assert "LUMENCORE / GRANTS" in page("grants")


def test_operator_surfaces_are_not_search_index_targets():
    for surface in ("mission", "quant", "grants", "trade"):
        assert '<meta name="robots" content="noindex,nofollow,noarchive">' in page(surface)


def test_mission_live_breadth_is_an_evidence_lane_not_a_value_claim():
    mission = page("mission")
    assert "Live Evidence Breadth" in mission
    assert "Dollar Claim Gate" in mission
    assert "$0 CLAIMABLE" in mission
    assert "NOT PROMOTED" in mission
    assert "live breadth is an evidence collection rail, not proof of alpha or field savings" in mission
    assert "Annual Preserved Value" not in mission
    assert "Hourly Preserved Value" not in mission
    assert 'data-luma-legacy="true"' in mission


def test_public_home_sells_one_bounded_assurance_sequence():
    home = page("home")
    assert 'aria-label="ProofLock assurance sequence"' in home
    for step in ("01 · Scope", "02 · Lock", "03 · Run", "04 · ProofLock", "05 · Decide"):
        assert step in home
    assert 'href="/evidence/"' not in home
    assert "one problem, one baseline, and one decision" in home.lower()
    assert "external validation, field savings, production deployment, or agency endorsement" in home.lower()
    assert "ProofLock Opportunity Sprint" in home
    assert "$3,500" in home
    assert "50% kickoff deposit" in home
    assert "ten business days after source permissions" in home
    assert "No guaranteed eligibility, award, legal advice, certification" in home
    assert "final submission" in home
    assert 'href="/opportunity_sprint.html"' in home


def test_public_browser_path_uses_only_minimal_public_runtime_contracts():
    home = page("home")
    assert "/api/public/status" in home
    assert "/api/snapshot" not in home
    assert 'href="/mission_control.html"' not in home
    assert 'href="/external_review.html"' in home
    assert "LIVE ORDERS NOT AUTHORIZED" in home
    assert "operational detail remains token-protected" in home

    fabric = (DASHBOARD / "assets" / "luma_command_fabric.js").read_text(
        encoding="utf-8"
    )
    assert "var isOperatorSurface" in fabric
    public_update = fabric.split("function updatePublicStatus()", 1)[1].split(
        "function updateOperatorStatus()", 1
    )[0]
    operator_update = fabric.split("function updateOperatorStatus()", 1)[1].split(
        "function updateStatus()", 1
    )[0]
    assert 'fetchJson("/health")' in public_update
    assert 'fetchJson("/api/public/status")' in public_update
    assert "/api/snapshot" not in public_update
    assert 'surface: "public"' in public_update
    assert 'snapshot: null' in public_update
    assert 'fetchJson("/api/snapshot")' in operator_update
    assert 'surface: "operator"' in operator_update


def test_opportunity_sprint_is_buyable_bounded_and_human_gated():
    body = (DASHBOARD / "opportunity_sprint.html").read_text(encoding="utf-8")
    assert "ProofLock Opportunity Sprint" in body
    assert "$3,500" in body
    assert "50% kickoff deposit" in body
    assert "ten business days" in body
    assert "pursue, revise, hold, or stop" in body
    assert "AI can draft. ProofLock governs the decision." in body
    assert "A named person accountable for the agreed deliverables" in body
    assert "No signatures, certifications, or final submit" in body
    assert "does not guarantee eligibility, award, legal compliance" in body
    assert 'rel="canonical" href="https://lumen-core.ai/opportunity_sprint.html"' in body


def test_quant_visible_navigation_contains_only_canonical_routes():
    quant = page("quant")
    required = (
        "/mission_control.html",
        "/kraken_execution_dashboard.html",
        "/forecast.html",
        "/anomalies.html",
        "/explain.html",
        "/lab.html",
        "/grants.html",
        "/proof_to_pilot.html",
        "/evidence/",
    )
    for route in required:
        assert f'data-src="{route}"' in quant

    stale_visible_routes = (
        "/investor_command_room.html",
        "/lumaq_brain_command_center.html",
        "/live_positions.html",
        "/alpaca_paper_live_dashboard.html",
        "/dashboard_analytics.html",
        "/lumascout.html",
        "/investor_wallboard.html",
        "/master_evidence.html",
    )
    for route in stale_visible_routes:
        assert f'data-src="{route}"' not in quant

    assert "$3.53M" not in quant
    assert "click-Approve" not in quant
    assert "let localContextPromise = null" in quant
    assert "if (!force && localContextPromise) return localContextPromise" in quant


def test_grants_public_review_is_fail_closed_in_the_browser_layer():
    script = (DASHBOARD / "assets" / "luma_institutional_surface.js").read_text(
        encoding="utf-8"
    )
    assert 'surface !== "grants"' in script
    assert 'button.disabled = true' in script
    assert 'button.setAttribute("aria-disabled", "true")' in script
    assert "Final submission human-only" in script


def test_trade_missing_data_defaults_to_offline_and_disarmed():
    trade = page("trade")
    assert "heartbeat?.live_orders_armed === true" in trade
    assert "String(heartbeat?.runtime_mode || 'OFFLINE')" in trade
    assert "String(heartbeat?.status || 'offline')" in trade
    assert "!heartbeat" in trade
    assert "OFFLINE / DISARMED" in trade
    assert "live_orders_armed ?? true" not in trade


def test_shared_visual_system_has_accessibility_and_motion_boundaries():
    css = (DASHBOARD / "assets" / "luma_institutional_surface.css").read_text(
        encoding="utf-8"
    )
    assert ":focus-visible" in css
    assert "@media (prefers-reduced-motion: reduce)" in css
    assert "@media (max-width:" in css
    assert "--lis-text:" in css

    fabric_css = (DASHBOARD / "assets" / "luma_command_fabric.css").read_text(
        encoding="utf-8"
    )
    assert "@media (max-width: 820px)" in fabric_css
    assert "position: relative" in fabric_css


def test_customer_path_and_operator_path_are_deliberately_separate():
    fabric = (DASHBOARD / "assets" / "luma_command_fabric.js").read_text(
        encoding="utf-8"
    )
    assert "var OPERATOR_ROUTES" in fabric
    assert "var PUBLIC_ROUTES" in fabric
    assert 'label: "ProofLock"' in fabric
    assert 'label: "Quant"' in fabric
    assert 'label: "Grants"' in fabric
