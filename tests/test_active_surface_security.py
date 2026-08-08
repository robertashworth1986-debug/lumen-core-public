from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest
from fastapi import HTTPException


ROOT = Path(__file__).resolve().parents[1]
CODE = ROOT / "code"
if str(CODE) not in sys.path:
    sys.path.insert(0, str(CODE))

import forecast_api  # noqa: E402
import grants_api  # noqa: E402


def _write_grant_run(grants_root: Path, grant_id: str) -> Path:
    run = grants_root / grant_id / "20260808T120000Z"
    run.mkdir(parents=True)
    (run / "application.json").write_text(
        json.dumps(
            {
                "agency": '<script>alert("agency")</script>',
                "program": '<img src=x onerror=alert("program")>',
                "topic_area": "<svg onload=alert(1)>",
                "ceiling_usd": 1000,
                "duration_months": 6,
                "run_utc": "20260808T120000Z",
            }
        ),
        encoding="utf-8",
    )
    (run / "budget.json").write_text(
        json.dumps(
            {
                "total": 1000,
                "duration_months": 6,
                "categories": {"<img onerror=alert(1)>": 1000},
                "notes": ["<script>alert('note')</script>"],
            }
        ),
        encoding="utf-8",
    )
    (run / "application.md").write_text(
        "# Safe heading\n[unsafe](javascript:alert(1))\n<script>alert('md')</script>",
        encoding="utf-8",
    )
    return run


def test_grant_route_parameter_cannot_escape_evidence_root(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    grants_root = tmp_path / "grants"
    valid_run = _write_grant_run(grants_root, "VALID-001")
    outside_run = _write_grant_run(tmp_path / "outside", "ESCAPE")
    monkeypatch.setattr(grants_api, "GRANTS", grants_root)

    assert grants_api._latest_grant_run("VALID-001") == valid_run
    assert grants_api._latest_grant_run("../outside/ESCAPE") is None
    assert grants_api._latest_grant_run(str(outside_run.parent)) is None


def test_grant_print_view_escapes_artifact_content(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    grants_root = tmp_path / "grants"
    _write_grant_run(grants_root, "VALID-001")
    monkeypatch.setattr(grants_api, "GRANTS", grants_root)

    body = grants_api.print_html("VALID-001").body.decode("utf-8")

    assert "<script>alert" not in body
    assert "<img src=x" not in body
    assert "<svg onload" not in body
    assert "javascript:alert" not in body
    assert "&lt;script&gt;alert" in body
    assert "&lt;img src=x onerror" in body


def test_forecast_route_parameter_selects_only_enumerated_csv(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    raw_dir = tmp_path / "raw"
    raw_dir.mkdir()
    safe = raw_dir / "SAFE_SERIES.csv"
    safe.write_text("date,value\n2026-01-01,1\n", encoding="utf-8")
    outside = tmp_path / "outside.csv"
    outside.write_text("date,value\n2026-01-01,2\n", encoding="utf-8")
    monkeypatch.setattr(forecast_api._S, "raw_dir", raw_dir)

    assert forecast_api._dataset_source("SAFE_SERIES") == safe
    for attack in ("../outside", "..\\outside", str(outside), "SAFE_SERIES/../../outside"):
        with pytest.raises(HTTPException) as exc_info:
            forecast_api._dataset_source(attack)
        assert exc_info.value.status_code == 404
        assert exc_info.value.detail == "dataset not found"


def test_active_dashboards_use_fail_closed_url_and_dom_boundaries() -> None:
    grants = (ROOT / "dashboard" / "grants.html").read_text(encoding="utf-8")
    mission = (ROOT / "dashboard" / "mission_control.html").read_text(encoding="utf-8")
    forecast = (ROOT / "dashboard" / "forecast.html").read_text(encoding="utf-8")
    quant = (ROOT / "dashboard" / "quant_lab.html").read_text(encoding="utf-8")
    evidence = (ROOT / "dashboard" / "evidence" / "index.html").read_text(encoding="utf-8")
    shared = (ROOT / "dashboard" / "assets" / "lumencore.js").read_text(encoding="utf-8")
    sector = (ROOT / "code" / "execution" / "sector_opp_gain_dashboard.html").read_text(
        encoding="utf-8"
    )

    assert "TRUSTED_GRANT_DOMAINS" in grants
    assert "TRUSTED_GRANT_DOMAINS" in mission
    assert "host.includes(" not in grants
    assert "host.includes(" not in mission
    assert "trustedGrantUrl(target)" in mission
    assert "li.innerHTML" not in forecast
    assert "cpList.innerHTML" not in quant
    assert "host.innerHTML" not in quant
    assert "\n    t.innerHTML =" not in shared
    assert 'document.getElementById("figs").innerHTML' not in evidence
    assert 'body.innerHTML = rows.map' not in evidence
    assert "RUN_URL" not in evidence
    assert "function canonicalRunUtc(value)" in evidence
    assert "match.slice(1).map(Number)" in evidence
    assert "ACTIVE_RUN_UTC = rawUtc" not in evidence
    assert "unapproved evidence artifact" in evidence
    assert 'case "summary.json"' in evidence
    assert "candidate.origin !== window.location.origin" in evidence
    assert "cross-origin evidence artifact blocked" in evidence
    assert "document.getElementById('af').innerHTML" not in sector
    assert "document.getElementById('srs').innerHTML" not in sector
    assert "document.getElementById('tti').innerHTML" not in sector


def test_api_error_contracts_do_not_expose_exception_text_or_server_paths() -> None:
    forecast = (ROOT / "code" / "forecast_api.py").read_text(encoding="utf-8")
    grants = (ROOT / "code" / "grants_api.py").read_text(encoding="utf-8")

    forbidden = (
        'detail=f"read error:',
        'detail=f"router failed:',
        'detail=f"factory import failed:',
        'detail=f"submission kit import failed:',
    )
    for marker in forbidden:
        assert marker not in forecast
        assert marker not in grants
