from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]

LEGACY_PUBLIC_ROUTES = (
    "dashboard/mission_control.html",
    "dashboard/quant_lab.html",
    "dashboard/kraken_execution_dashboard.html",
    "dashboard/grants.html",
    "dashboard/forecast.html",
    "dashboard/anomalies.html",
    "dashboard/explain.html",
    "dashboard/lab.html",
)

FORBIDDEN_PUBLIC_SURFACE_TERMS = (
    "/api/snapshot",
    "/api/events/recent",
    "mission control · v3.0",
    "unified cockpit · all systems",
    "kraken execution dashboard",
    "loading live execution guardrails",
    "active grant submissions",
)


def test_legacy_dashboard_routes_are_hold_stubs() -> None:
    for relpath in LEGACY_PUBLIC_ROUTES:
        text = (ROOT / relpath).read_text(encoding="utf-8")
        lowered = text.lower()
        assert "legacy-public-route-hold-v1" in lowered
        assert "noindex,nofollow" in lowered
        assert "url=/proof_to_pilot.html" in lowered
        assert "location.replace('/proof_to_pilot.html')" in text
        assert "field validation" in lowered
        assert "production readiness" in lowered
        for forbidden in FORBIDDEN_PUBLIC_SURFACE_TERMS:
            assert forbidden not in lowered
