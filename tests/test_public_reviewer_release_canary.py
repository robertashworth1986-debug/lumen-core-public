from __future__ import annotations

import importlib.util
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "code" / "ops" / "CHECK_PUBLIC_REVIEWER_RELEASE.py"
WORKFLOW = ROOT / ".github" / "workflows" / "health-probe.yml"


def load_module():
    spec = importlib.util.spec_from_file_location("public_release_canary", SCRIPT)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def write_fixture(root: Path, spec, body: bytes) -> None:
    path = root / spec.local_path
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(body)


def test_matching_public_release_passes_without_persisting_bodies(tmp_path: Path) -> None:
    module = load_module()
    html = b"<html>reviewer-marker</html>"
    payload = {"schema": "example.schema.v1", "value": 3}
    json_body = json.dumps(payload, sort_keys=True).encode("utf-8")
    specs = (
        module.EndpointSpec(
            "page", "/proof.html", "dashboard/proof.html", "text/html", "reviewer-marker"
        ),
        module.EndpointSpec(
            "feed",
            "/data/feed.json",
            "dashboard/data/feed.json",
            "application/json",
            "example.schema.v1",
            "example.schema.v1",
        ),
    )
    write_fixture(tmp_path, specs[0], html)
    write_fixture(tmp_path, specs[1], json_body)
    responses = {
        "https://example.test/proof.html": module.FetchResult(200, "text/html", html),
        "https://example.test/data/feed.json": module.FetchResult(
            200, "application/json", json_body
        ),
    }

    receipt = module.build_receipt(
        root=tmp_path,
        base_url="https://example.test",
        endpoints=specs,
        fetcher=lambda url, _timeout: responses[url],
    )

    assert receipt["summary"] == {
        "endpoint_count": 2,
        "passed_count": 2,
        "blocked_count": 0,
        "status": "PASS",
    }
    encoded = json.dumps(receipt)
    assert "reviewer-marker</html>" not in encoded
    assert '"value": 3' not in encoded
    assert receipt["capability_boundary"]["response_bodies_persisted"] is False


def test_hash_mismatch_blocks_release(tmp_path: Path) -> None:
    module = load_module()
    spec = module.EndpointSpec(
        "page", "/proof.html", "dashboard/proof.html", "text/html", "marker"
    )
    write_fixture(tmp_path, spec, b"local marker")

    receipt = module.build_receipt(
        root=tmp_path,
        base_url="https://example.test",
        endpoints=(spec,),
        fetcher=lambda _url, _timeout: module.FetchResult(
            200, "text/html", b"remote marker"
        ),
    )

    row = receipt["endpoints"][0]
    assert receipt["summary"]["status"] == "BLOCKED"
    assert row["status"] == "BLOCKED"
    assert row["checks"]["sha256_matches_local"] is False
    assert "sha256_matches_local" in row["failed_checks"]


def test_http_or_mime_failure_blocks_release(tmp_path: Path) -> None:
    module = load_module()
    spec = module.EndpointSpec(
        "page", "/proof.html", "dashboard/proof.html", "text/html", "marker"
    )
    write_fixture(tmp_path, spec, b"local marker")

    unavailable = module.build_receipt(
        root=tmp_path,
        base_url="https://example.test",
        endpoints=(spec,),
        fetcher=lambda _url, _timeout: module.FetchResult(
            502, None, b"", "HTTP_502"
        ),
    )
    wrong_mime = module.build_receipt(
        root=tmp_path,
        base_url="https://example.test",
        endpoints=(spec,),
        fetcher=lambda _url, _timeout: module.FetchResult(
            200, "application/octet-stream", b"local marker"
        ),
    )

    assert unavailable["summary"]["status"] == "BLOCKED"
    assert unavailable["endpoints"][0]["fetch_error"] == "HTTP_502"
    assert wrong_mime["summary"]["status"] == "BLOCKED"
    assert wrong_mime["endpoints"][0]["checks"]["mime_type_matches"] is False


def test_invalid_remote_json_schema_blocks_release(tmp_path: Path) -> None:
    module = load_module()
    spec = module.EndpointSpec(
        "feed",
        "/data/feed.json",
        "dashboard/data/feed.json",
        "application/json",
        "example.schema.v1",
        "example.schema.v1",
    )
    local_body = b'{"schema":"example.schema.v1"}'
    write_fixture(tmp_path, spec, local_body)

    receipt = module.build_receipt(
        root=tmp_path,
        base_url="https://example.test",
        endpoints=(spec,),
        fetcher=lambda _url, _timeout: module.FetchResult(
            200, "application/json", b'{"schema":"wrong"}'
        ),
    )

    row = receipt["endpoints"][0]
    assert row["checks"]["remote_json_schema_matches"] is False
    assert receipt["summary"]["status"] == "BLOCKED"


def test_health_workflow_runs_canary_and_fails_closed() -> None:
    workflow = WORKFLOW.read_text(encoding="utf-8")
    assert "CHECK_PUBLIC_REVIEWER_RELEASE.py" in workflow
    assert "reviewer_release_canary.json" in workflow
    assert "steps.probe.outputs.reviewer_release != 'pass'" in workflow
    assert "contents: read" in workflow
    assert "git push" not in workflow
