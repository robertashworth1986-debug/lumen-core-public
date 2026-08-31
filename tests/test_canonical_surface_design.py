import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DASHBOARD = ROOT / "dashboard"
CANONICAL_STATE = ROOT / "docs" / "CANONICAL_OPERATING_STATE.md"


PAGES = {
    "home": "operator_home.html",
}

PUBLIC_REVIEW_PAGES = (
    DASHBOARD / "proof_to_pilot.html",
    DASHBOARD / "visual_library.html",
    DASHBOARD / "external_review.html",
    DASHBOARD / "evidence" / "index_bounded.html",
)

LEGACY_ROUTE_HOLDS = (
    DASHBOARD / "mission_control.html",
    DASHBOARD / "quant_lab.html",
    DASHBOARD / "kraken_execution_dashboard.html",
    DASHBOARD / "grants.html",
    DASHBOARD / "forecast.html",
    DASHBOARD / "anomalies.html",
    DASHBOARD / "explain.html",
    DASHBOARD / "lab.html",
)

LEGACY_FORBIDDEN_TERMS = (
    "/api/snapshot",
    "/api/events/recent",
    "mission control · v3.0",
    "unified cockpit · all systems",
    "kraken execution dashboard",
    "loading live execution guardrails",
    "active grant submissions",
)


def page(name: str) -> str:
    return (DASHBOARD / PAGES[name]).read_text(encoding="utf-8")


def test_canonical_state_separates_liveness_from_deployment_and_validation():
    state = CANONICAL_STATE.read_text(encoding="utf-8")
    lower = state.lower()
    normalized = " ".join(lower.split())

    assert "point-in-time public liveness only" in normalized
    assert "do not establish the recovery cause" in normalized
    assert "deployed gateway commit" in normalized
    assert "not exact-byte release parity" in normalized
    assert "production promotion remains `hold`" in normalized
    assert (
        "neither gateway liveness nor exact-byte deployment constitutes external validation"
        in normalized
    )
    assert (
        "dynamic gateway remains degraded and must continue to be reported as http 502"
        not in normalized
    )


def test_public_home_shares_identity_and_runtime_layer():
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


def test_public_review_pages_share_the_canonical_lumaarc_shell():
    for path in PUBLIC_REVIEW_PAGES:
        body = path.read_text(encoding="utf-8")
        assert 'data-luma-surface="review"' in body
        assert '/assets/lumaarc_arc_seal_v1.png' in body
        assert '/assets/luma_institutional_surface.css' in body
        assert '/assets/luma_institutional_surface.js' in body
        assert 'class="lis-review-header"' in body
        assert 'class="lis-review-brand"' in body
        assert 'class="lis-review-links"' in body
        assert "LUMEN<em>CORE</em>" in body

    shared_css = (DASHBOARD / "assets" / "luma_institutional_surface.css").read_text(
        encoding="utf-8"
    )
    shared_js = (DASHBOARD / "assets" / "luma_institutional_surface.js").read_text(
        encoding="utf-8"
    )
    assert 'body[data-luma-surface="review"]' in shared_css
    assert ".lis-review-header" in shared_css
    assert 'review: {' in shared_js
    assert 'surface === "review"' in shared_js


def test_legacy_public_routes_are_noindex_holds():
    for path in LEGACY_ROUTE_HOLDS:
        body = path.read_text(encoding="utf-8")
        lower = body.lower()
        assert '<meta name="robots" content="noindex,nofollow,noarchive">' in body
        assert '<meta name="lumencore-surface" content="legacy-public-route-hold-v1">' in body
        assert '<meta http-equiv="refresh" content="0;url=/proof_to_pilot.html">' in body
        assert "location.replace('/proof_to_pilot.html')" in body
        for term in LEGACY_FORBIDDEN_TERMS:
            assert term.lower() not in lower


def test_public_home_sells_one_bounded_assurance_sequence():
    home = page("home")
    assert 'aria-label="ProofLock assurance sequence"' in home
    for step in ("01 · Scope", "02 · Lock", "03 · Run", "04 · ProofLock", "05 · Decide"):
        assert step in home
    assert 'href="/evidence/"' not in home
    assert "one problem, one baseline, and one decision" in home.lower()
    assert "external validation, field savings, production deployment, or agency endorsement" in home.lower()
    assert "Buyer-Owned Baseline Validation Sprint" in home
    assert "$7,500" in home
    assert "50% at signed scope and 50% at delivery" in home
    assert "30 calendar days maximum" in home
    assert "Pricing is not buyer-tested" in home
    assert "No favorable result, savings, ROI, certification" in home
    assert 'href="/proof_to_pilot.html"' in home
    assert 'href="/visual_library.html"' in home
    assert "ProofLock Opportunity Sprint" not in home


def test_public_visual_library_is_complete_hash_bound_and_claim_bounded():
    visual_root = DASHBOARD / "assets" / "visuals"
    payload = json.loads((visual_root / "manifest.json").read_text(encoding="utf-8"))
    page_body = (DASHBOARD / "visual_library.html").read_text(encoding="utf-8")

    assert payload["schema"] == "lumencore.public_visual_library.v1"
    assert payload["asset_count"] == 12
    assert len(payload["items"]) == 12
    assert payload["total_web_bytes"] == sum(item["bytes"] for item in payload["items"])
    assert "concept art" in payload["authority_boundary"].lower()
    assert "external validation" in payload["authority_boundary"].lower()
    assert 'rel="canonical" href="https://lumen-core.ai/visual_library.html"' in page_body
    assert 'href="/assets/visuals/manifest.json"' in page_body
    assert "CONCEPT ART ≠ OBSERVATION" in page_body
    assert "CUSTODY ≠ AUTHORITY" in page_body
    assert "FIRST-PARTY ≠ INDEPENDENT VALIDATION" in page_body
    assert page_body.count('<article class="card') == 12

    seen_assets = set()
    total_bytes = 0
    for item in payload["items"]:
        assert set(item) == {
            "id",
            "title",
            "evidence_class",
            "public_boundary",
            "source_filename",
            "source_sha256",
            "web_asset",
            "web_sha256",
            "width",
            "height",
            "bytes",
        }
        asset_name = item["web_asset"]
        assert asset_name not in seen_assets
        seen_assets.add(asset_name)
        assert asset_name.endswith(".webp")
        asset = visual_root / asset_name
        body = asset.read_bytes()
        assert len(body) == item["bytes"]
        assert hashlib.sha256(body).hexdigest() == item["web_sha256"]
        assert item["width"] > 0 and item["height"] > 0
        assert item["public_boundary"].strip()
        assert f'/assets/visuals/{asset_name}' in page_body
        total_bytes += len(body)

    assert len(seen_assets) == 12
    assert total_bytes == payload["total_web_bytes"]
    assert total_bytes < 3_500_000
    assert "C:\\Users\\" not in json.dumps(payload)


def test_public_home_proof_lattice_is_claim_bounded_and_progressively_enhanced():
    home = page("home")
    assert 'data-proof-lattice' in home
    assert 'class="lis-lattice-webgl-canvas"' in home
    assert 'class="lis-lattice-canvas"' in home
    assert "assets/vendor/three.min.js" in home
    assert 'data-luma-three-loader' in home
    assert 'script.async = true' in home
    assert 'connection.effectiveType' in home
    assert 'navigator.deviceMemory < 4' in home
    assert 'navigator.hardwareConcurrency < 4' in home
    assert 'requestIdleCallback' in home
    assert 'luma:three-ready' in home
    assert 'sha384-qOkzR5Ke/XkQxuGVJ9hpFEpDlcoLtWwVYhnJf06cLIZa2vaIptSqaubivErzmD5O' in home
    assert home.index('class="lis-proofline"') < home.index('class="hero"')
    assert '<button type="button" data-lattice-step="0" aria-pressed="false">Source</button>' in home
    assert 'class="lis-lattice-readout" aria-live="polite"' in home
    assert "Source" in home
    assert "Baseline" in home
    assert "Metric" in home
    assert "Hash" in home
    assert "Decision" in home
    assert "design model, not a scientific result or validation claim" in home

    shared_js = (DASHBOARD / "assets" / "luma_institutional_surface.js").read_text(
        encoding="utf-8"
    )
    assert "THREE.WebGLRenderer" in shared_js
    assert "THREE.ShaderMaterial" in shared_js
    assert "THREE.AdditiveBlending" in shared_js
    assert "THREE.IcosahedronGeometry" in shared_js
    assert "THREE.InstancedMesh" in shared_js
    assert "THREE.TorusKnotGeometry" in shared_js
    assert "THREE.Points" in shared_js
    assert "makeDeepStarField" in shared_js
    assert "recursiveProofClusters" in shared_js
    assert "recursiveCellClusters" in shared_js
    assert "proofCellMeshes" in shared_js
    assert "cells.userData.fullCount" in shared_js
    assert 'modeLabel.textContent = "DEEP SPACE / WEBGL MODEL"' in shared_js
    assert "updateProofLatticeStep" in shared_js
    assert "bindProofLatticeControls" in shared_js
    assert 'canvas.addEventListener("webglcontextlost"' in shared_js
    assert 'canvas.addEventListener("webglcontextrestored"' in shared_js
    assert 'viewport.dataset.quality = "adaptive"' in shared_js
    assert "deliveredFps < 28" in shared_js
    assert "not a scientific result or validation claim" in home
    assert "Recursive custody clusters" in home
    assert "Procedural recursive geometry" in home
    assert 'canvas.getContext("2d"' in shared_js
    assert "prefers-reduced-motion: reduce" in shared_js
    assert "connection.saveData" in shared_js
    assert 'dataset.lumaWebglPending === "true"' in shared_js
    assert 'DEEP SPACE / INITIALIZING' in shared_js
    assert "navigator.deviceMemory" in shared_js
    assert "navigator.hardwareConcurrency" in shared_js
    assert '"ResizeObserver" in window' in shared_js
    assert '"IntersectionObserver" in window' in shared_js
    assert "requestAnimationFrame" in shared_js
    assert "execution_authorized" not in shared_js
    assert "WebSocket" not in shared_js

    shared_css = (DASHBOARD / "assets" / "luma_institutional_surface.css").read_text(
        encoding="utf-8"
    )
    assert ".lis-lattice-stage" in shared_css
    assert ".lis-lattice-viewport" in shared_css
    assert ".lis-lattice-webgl-canvas" in shared_css
    assert ".lis-lattice-canvas" in shared_css


def test_three_dependency_is_byte_stable_and_sri_bound():
    asset = DASHBOARD / "assets" / "vendor" / "three.min.js"
    readme = (asset.parent / "README.md").read_text(encoding="utf-8")
    digest = hashlib.sha256(asset.read_bytes()).hexdigest()
    assert digest == "170c6789f43217c96b3170f4b42fafe135de7f7cd48497a4218f9757ee1d49fa"
    assert digest in readme
    assert "sha384-qOkzR5Ke/XkQxuGVJ9hpFEpDlcoLtWwVYhnJf06cLIZa2vaIptSqaubivErzmD5O" in readme


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
    assert "var isOperatorSurface = false" in fabric
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


def test_opportunity_sprint_is_secondary_bounded_and_human_gated():
    body = (DASHBOARD / "opportunity_sprint.html").read_text(encoding="utf-8")
    assert "Secondary funding-workflow variant" in body
    assert "not the primary public offer" in body
    assert "No active standalone public price" in body
    assert "former $3,500 launch price" in body
    assert 'href="/proof_to_pilot.html"' in body
    assert "pursue, revise, hold, or stop" in body
    assert "AI can draft. ProofLock governs the decision." in body
    assert "A named person accountable for the agreed deliverables" in body
    assert "No signatures, certifications, or final submit" in body
    assert "does not guarantee eligibility, award, legal compliance" in body
    assert "Start with the public opportunity link—not your confidential files." in body
    assert "PROOFLOCK_OPPORTUNITY_SPRINT_DATA_HANDLING_SCHEDULE.md" in body
    assert "approved operators, systems, external AI or service providers" in body
    assert 'rel="canonical" href="https://lumen-core.ai/opportunity_sprint.html"' in body


def test_opportunity_sprint_data_handling_schedule_is_fail_closed():
    schedule = (
        ROOT / "docs" / "PROOFLOCK_OPPORTUNITY_SPRINT_DATA_HANDLING_SCHEDULE.md"
    ).read_text(encoding="utf-8")
    scope = (ROOT / "docs" / "PROOFLOCK_OPPORTUNITY_SPRINT_SCOPE.md").read_text(
        encoding="utf-8"
    )
    intake = (ROOT / "docs" / "PROOFLOCK_OPPORTUNITY_SPRINT_INTAKE.md").read_text(
        encoding="utf-8"
    )

    for required in (
        "Prohibited by default",
        "External AI and service-provider rule",
        "Retention and deletion register",
        "Incident and exception handling",
        "Publicity and evidence boundary",
        "No source, system, person, or service is authorized merely because it is",
        "Client-confidential content must not be submitted to an external AI",
        "A hash proves byte identity",
        "outside the operator's\ncontrol",
        "does not by itself establish endorsement, external validation",
    ):
        assert required in schedule

    assert "PROOFLOCK_OPPORTUNITY_SPRINT_DATA_HANDLING_SCHEDULE.md" in scope
    assert "PROOFLOCK_OPPORTUNITY_SPRINT_DATA_HANDLING_SCHEDULE.md" in intake
    assert "Do **not** email credentials" in intake


def test_quant_legacy_route_redirects_to_public_review_path():
    quant = (DASHBOARD / "quant_lab.html").read_text(encoding="utf-8")
    assert "/proof_to_pilot.html" in quant
    assert 'data-src="/mission_control.html"' not in quant
    assert 'data-src="/kraken_execution_dashboard.html"' not in quant
    assert "$3.53M" not in quant
    assert "click-Approve" not in quant
    assert "let localContextPromise = null" not in quant


def test_grants_public_review_is_fail_closed_in_the_browser_layer():
    script = (DASHBOARD / "assets" / "luma_institutional_surface.js").read_text(
        encoding="utf-8"
    )
    assert 'surface !== "grants"' in script
    assert 'button.disabled = true' in script
    assert 'button.setAttribute("aria-disabled", "true")' in script
    assert "Final submission human-only" in script


def test_trade_legacy_route_does_not_expose_live_execution_guardrails():
    trade = (DASHBOARD / "kraken_execution_dashboard.html").read_text(encoding="utf-8")
    assert "/proof_to_pilot.html" in trade
    assert "heartbeat?.live_orders_armed === true" not in trade
    assert "live_orders_armed ?? true" not in trade
    assert "OFFLINE / DISARMED" not in trade
    assert "/api/events/recent" not in trade


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
    assert "var OPERATOR_ROUTES" not in fabric
    assert "var PUBLIC_ROUTES" in fabric
    assert 'label: "ProofLock"' in fabric
    assert 'label: "Proof"' in fabric
    assert 'label: "Evidence"' in fabric
    assert 'label: "External Review"' in fabric
    assert 'label: "Quant"' not in fabric
    assert 'label: "Grants"' not in fabric
