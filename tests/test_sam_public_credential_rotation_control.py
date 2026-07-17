from __future__ import annotations

import importlib.util
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "code" / "ops" / "BUILD_SAM_PUBLIC_CREDENTIAL_ROTATION_CONTROL.py"


def load_module():
    spec = importlib.util.spec_from_file_location("sam_public_credential_rotation_control", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def records(secret: str = "secret-one") -> list[dict[str, str]]:
    return [
        {
            "name": "SAM_API_KEY",
            "value": secret,
            "source_kind": "env_file",
            "source": "config/luma_live_keys.env",
        },
        {
            "name": "SAM_GOV_API_KEY",
            "value": secret,
            "source_kind": "env_file",
            "source": "config/luma_live_keys.env",
        },
        {
            "name": "DATA_GOV_API_KEY_PRIMARY",
            "value": secret,
            "source_kind": "env_file",
            "source": "config/luma_live_keys.env",
        },
    ]


def probe(classification: str, *, live: bool = False, status: int | None = 404):
    return {
        "classification": classification,
        "http_status": status,
        "response_shape_valid": live,
        "live_authenticated_response": live,
        "response_body_published": False,
        "endpoint": "SAM_ASSISTANCE_LISTINGS_PUBLIC_API",
        "probe_listing_id": "43.008",
        "official_documentation": "https://open.gsa.gov/api/assistance-listings-api/",
        "request_url_published": False,
        "secret_value_published": False,
    }


def test_alias_discovery_is_consistent_and_secret_free(tmp_path: Path):
    module = load_module()
    env_file = tmp_path / "keys.env"
    env_file.write_text(
        "SAM_API_KEY=same-secret\nSAM_GOV_API_KEY=same-secret\n"
        "DATA_GOV_API_KEY_PRIMARY=same-secret\nOTHER_KEY=do-not-read\n",
        encoding="utf-8",
    )
    found = module.discover_key_records(environ={}, env_paths=[env_file])
    summary = module.public_source_summary(found)

    assert len(found) == 3
    assert summary["configured_entry_count"] == 3
    assert summary["distinct_secret_value_count"] == 1
    assert summary["aliases_consistent"] is True
    assert summary["secret_values_exposed"] is False
    assert "same-secret" not in json.dumps(summary)


def test_same_fingerprint_remains_due_and_unverified():
    module = load_module()
    source_records = records()
    baseline = {
        "fingerprint_sha256": module.secret_fingerprint("secret-one"),
    }
    payload = module.build_payload(
        records=source_records,
        baseline=baseline,
        probe=probe("HTTP_404_EMPTY_RESPONSE_INCONCLUSIVE"),
        generated_utc="2026-07-16T23:30:00Z",
    )

    assert payload["status"] == "ROTATION_DUE_REPLACEMENT_NOT_DETECTED"
    assert payload["local_configuration"]["replacement_installation_detected"] is False
    assert payload["rotation_verified"] is False
    assert "secret-one" not in json.dumps(payload)
    assert module.secret_fingerprint("secret-one") not in json.dumps(payload)


def test_changed_fingerprint_and_live_probe_verify_rotation():
    module = load_module()
    baseline = {
        "fingerprint_sha256": module.secret_fingerprint("old-secret"),
    }
    payload = module.build_payload(
        records=records("new-secret"),
        baseline=baseline,
        probe=probe("LIVE_AUTHENTICATED_RESPONSE", live=True, status=200),
        generated_utc="2026-07-17T12:00:00Z",
    )

    assert payload["status"] == "ROTATION_VERIFIED_NEW_KEY_LIVE"
    assert payload["local_configuration"]["replacement_installation_detected"] is True
    assert payload["rotation_verified"] is True


def test_missing_key_has_a_distinct_truthful_decision():
    module = load_module()
    payload = module.build_payload(
        records=[],
        baseline=None,
        probe=probe("PROBE_SKIPPED_INCONCLUSIVE", status=None),
        generated_utc="2026-07-16T23:30:00Z",
    )

    assert payload["status"] == "SAM_API_KEY_MISSING"
    assert payload["deadline"]["state"] == "DUE_TODAY"
    assert payload["local_configuration"]["aliases_consistent"] is False
    assert payload["rotation_verified"] is False
    assert payload["decision"].startswith("No configured SAM public API credential")


def test_probe_classification_does_not_overstate_empty_404():
    module = load_module()

    empty_404 = module.classify_probe(404, b"")
    rejected = module.classify_probe(401, b'{"message":"invalid"}')
    live = module.classify_probe(
        200,
        b'{"totalRecords":1,"assistanceListingsData":[{"assistanceListingId":"43.008"}]}',
    )

    assert empty_404["classification"] == "HTTP_404_EMPTY_RESPONSE_INCONCLUSIVE"
    assert empty_404["live_authenticated_response"] is False
    assert rejected["classification"] == "KEY_REJECTED_OR_MISSING"
    assert live["classification"] == "LIVE_AUTHENTICATED_RESPONSE"
    assert live["live_authenticated_response"] is True


def test_private_baseline_is_write_once_and_public_output_is_safe(tmp_path: Path):
    module = load_module()
    baseline_path = tmp_path / "private" / "baseline.json"
    first = module.capture_private_baseline(
        records("first-secret")[0],
        path=baseline_path,
        captured_utc="2026-07-16T20:00:00Z",
    )
    second = module.capture_private_baseline(
        records("second-secret")[0],
        path=baseline_path,
        captured_utc="2026-07-16T21:00:00Z",
    )

    assert first == second
    assert first["fingerprint_sha256"] == module.secret_fingerprint("first-secret")
    assert first["fingerprint_sha256"] != module.secret_fingerprint("second-secret")

    payload = module.build_payload(
        records=records("first-secret"),
        baseline=first,
        probe=probe("HTTP_404_EMPTY_RESPONSE_INCONCLUSIVE"),
        generated_utc="2026-07-16T23:30:00Z",
    )
    rendered = module.render_markdown(payload)
    serialized = json.dumps(payload, sort_keys=True)
    module.ensure_public_safe(serialized, ["first-secret"])
    module.ensure_public_safe(rendered, ["first-secret"])

    assert "No secret value" in rendered
    assert "fingerprint" in rendered.lower()
    assert "first-secret" not in rendered
    assert first["fingerprint_sha256"] not in rendered
    assert "api_key=" not in rendered.lower()
