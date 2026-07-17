from __future__ import annotations

import importlib.util
import io
import json
import sys
import urllib.error
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = ROOT / "code" / "opportunity_harvester.py"


def load_module():
    code_dir = str(ROOT / "code")
    if code_dir not in sys.path:
        sys.path.insert(0, code_dir)
    spec = importlib.util.spec_from_file_location("opportunity_harvester", MODULE_PATH)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_sam_search_uses_current_public_production_route(monkeypatch):
    module = load_module()
    urls: list[str] = []
    diagnostic = {}

    def fake_http_json(url, **_kwargs):
        urls.append(url)
        return {"totalRecords": 0, "opportunitiesData": []}

    monkeypatch.setattr(module, "_http_json", fake_http_json)
    assert module.fetch_sam_gov(
        "secret-value", days=1, limit=1, diagnostic=diagnostic
    ) == []

    assert len(urls) == len(module.PROFILE_NAICS) + 1
    assert all(
        url.startswith("https://api.sam.gov/opportunities/v2/search?")
        for url in urls
    )
    assert all("/prod/opportunities/" not in url for url in urls)
    assert all("offset=0" in url for url in urls)
    targeted = urls[1:]
    assert all("ptype=p&ptype=o&ptype=k&ptype=r" in url for url in targeted)
    assert diagnostic["status"] == "LIVE_AUTHENTICATED_ZERO_MATCHES"
    assert diagnostic["live_response_observed"] is True
    assert diagnostic["response_shape_valid"] is True
    assert diagnostic["request_attempts"] == len(module.PROFILE_NAICS) + 1
    assert diagnostic["successful_requests"] == len(module.PROFILE_NAICS) + 1
    assert diagnostic["failed_requests"] == 0
    assert diagnostic["secret_value_published"] is False


def test_sam_search_fails_closed_after_one_health_error(monkeypatch, capsys):
    module = load_module()
    urls: list[str] = []
    diagnostic = {}

    def fake_http_json(url, **_kwargs):
        urls.append(url)
        raise RuntimeError(f"request failed {url}")

    monkeypatch.setattr(module, "_http_json", fake_http_json)
    rows = module.fetch_sam_gov(
        "secret-value", days=1, limit=1, diagnostic=diagnostic
    )

    assert rows == []
    assert len(urls) == 1
    output = capsys.readouterr().out
    assert "secret-value" not in output
    assert "[REDACTED]" in output
    assert diagnostic["status"] == "REQUEST_FAILURE_INCONCLUSIVE"
    assert diagnostic["request_attempts"] == 1
    assert diagnostic["failed_requests"] == 1
    assert diagnostic["response_body_published"] is False


def test_sbir_fetch_uses_one_bounded_open_request(monkeypatch):
    module = load_module()
    urls: list[str] = []
    diagnostic = {}

    def fake_http_json(url, **_kwargs):
        urls.append(url)
        return [
            {
                "solicitation_number": "TEST-1",
                "solicitation_title": "AI test",
                "solicitation_topics": [{"topic_title": "Structured data"}],
                "solicitation_agency_url": "https://example.invalid/test-1",
                "current_status": "open",
            }
        ]

    monkeypatch.setattr(module, "_http_json", fake_http_json)
    rows = module.fetch_sbir_gov(
        ["ai", "machine learning", "forecasting"], diagnostic=diagnostic
    )

    assert urls == [
        "https://api.www.sbir.gov/public/api/solicitations?open=1&rows=50"
    ]
    assert rows[0]["id"] == "TEST-1"
    assert rows[0]["topics"] == [{"topic_title": "Structured data"}]
    assert diagnostic["status"] == "LIVE_RESPONSE_RECORDS_PRESENT"
    assert diagnostic["request_attempts"] == 1
    assert diagnostic["successful_requests"] == 1
    assert diagnostic["records"] == 1


def test_error_text_redacts_query_and_environment_secrets(monkeypatch):
    module = load_module()
    monkeypatch.setenv("SAM_API_KEY", "very-secret-sam-key")
    error = RuntimeError(
        "request failed https://api.sam.gov/test?api_key=very-secret-sam-key&limit=1"
    )

    rendered = module._safe_error_text(error)

    assert "very-secret-sam-key" not in rendered
    assert "api_key=[REDACTED]" in rendered


def test_empty_404_is_classified_without_publishing_response_body() -> None:
    module = load_module()
    error = urllib.error.HTTPError(
        "https://api.sam.gov/redacted",
        404,
        "Not Found",
        {},
        io.BytesIO(b""),
    )

    diagnostic = module._classify_fetch_error(error, credential_required=True)

    assert diagnostic == {
        "status": "HTTP_404_EMPTY_RESPONSE_INCONCLUSIVE",
        "http_status": 404,
        "error_type": "HTTPError",
        "error_body_bytes": 0,
        "response_body_published": False,
        "secret_value_published": False,
    }


def test_grants_gov_diagnostic_distinguishes_live_zero_records(monkeypatch) -> None:
    module = load_module()
    diagnostic = {}

    monkeypatch.setattr(
        module,
        "_http_json",
        lambda *_args, **_kwargs: {"data": {"oppHits": []}},
    )
    rows = module.fetch_grants_gov(
        rows=1,
        keywords=["ai", "energy"],
        diagnostic=diagnostic,
    )

    assert rows == []
    assert diagnostic["status"] == "LIVE_RESPONSES_ZERO_RECORDS"
    assert diagnostic["request_attempts"] == 2
    assert diagnostic["successful_requests"] == 2
    assert diagnostic["failed_requests"] == 0


def test_rotation_control_status_is_public_and_bounded(tmp_path: Path) -> None:
    module = load_module()
    path = tmp_path / "rotation.json"
    path.write_text(
        json.dumps(
            {
                "schema": "lumencore.sam_public_credential_rotation_control.v1",
                "generated_utc": "2026-07-17T06:04:23Z",
                "status": "ROTATION_OVERDUE_REPLACEMENT_NOT_DETECTED",
                "rotation_verified": False,
                "deadline": {"state": "PAST_DUE"},
                "private_value": "must-not-propagate",
            }
        ),
        encoding="utf-8",
    )

    result = module._read_sam_rotation_status(path)

    assert result == {
        "status": "ROTATION_OVERDUE_REPLACEMENT_NOT_DETECTED",
        "generated_utc": "2026-07-17T06:04:23Z",
        "rotation_verified": False,
        "deadline_state": "PAST_DUE",
    }
    assert "must-not-propagate" not in json.dumps(result)


def test_harvest_writes_atomic_source_health_and_linked_control_hashes(
    monkeypatch, tmp_path: Path
) -> None:
    module = load_module()
    monkeypatch.setattr(module, "OUT", tmp_path)
    monkeypatch.setattr(module, "SOURCE_HEALTH_PATH", tmp_path / "source_health_latest.json")
    monkeypatch.setattr(module, "_hydrate_known_env_files", lambda: None)
    monkeypatch.setattr(module, "load_application_profile", lambda: {})
    monkeypatch.setattr(module, "_first_nonempty_env", lambda *_names: (None, None))
    monkeypatch.setattr(module, "enrich_grants_gov_synopsis", lambda *_args, **_kwargs: 0)
    monkeypatch.setattr(module, "fetch_skip_grants", lambda: [])

    def no_records(source, endpoint, *, credential_required=False):
        return {
            **module._source_diagnostic(
                source,
                endpoint,
                credential_required=credential_required,
                credential_configured=False,
            ),
            "status": "BOUNDED_TEST_ZERO_RECORDS",
            "response_shape_valid": True,
        }

    def fake_grants(*_args, diagnostic=None, **_kwargs):
        module._set_diagnostic(diagnostic, no_records("grants.gov", "TEST_GRANTS"))
        return []

    def fake_sbir(*_args, diagnostic=None, **_kwargs):
        module._set_diagnostic(diagnostic, no_records("sbir.gov", "TEST_SBIR"))
        return []

    def fake_sam(*_args, diagnostic=None, **_kwargs):
        module._set_diagnostic(
            diagnostic,
            no_records("sam.gov", "TEST_SAM", credential_required=True),
        )
        return []

    monkeypatch.setattr(module, "fetch_grants_gov", fake_grants)
    monkeypatch.setattr(module, "fetch_sbir_gov", fake_sbir)
    monkeypatch.setattr(module, "fetch_sam_gov", fake_sam)

    ranked = module.harvest(min_score=0.3, limit=10)
    source_health = json.loads((tmp_path / "source_health_latest.json").read_text())
    raw_path = next(tmp_path.glob("harvest_*.json"))
    raw = json.loads(raw_path.read_text())

    unsigned_health = dict(source_health)
    health_hash = unsigned_health.pop("control_sha256")
    assert health_hash == module._stable_sha256(unsigned_health)
    assert raw["source_health"] == source_health["sources"]
    assert ranked["source_health_control_sha256"] == health_hash
    assert ranked["harvest_control_sha256"] == raw["control_sha256"]
    assert ranked["control_sha256"] == module._stable_sha256(
        {key: value for key, value in ranked.items() if key != "control_sha256"}
    )
    assert list(tmp_path.glob("*.tmp")) == []
