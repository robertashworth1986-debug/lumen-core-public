from __future__ import annotations

import importlib.util
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "code" / "ops" / "BUILD_OPENAI_BUILD_WEEK_PUBLIC_DEMO_RECEIPT.py"


def load_module():
    spec = importlib.util.spec_from_file_location("build_week_public_demo_receipt", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def source_bytes_by_url(module) -> dict[str, bytes]:
    return {
        f"{module.BASE_URL}{url_path}": (module.ROOT / relative_path).read_bytes()
        for relative_path, url_path in module.PUBLIC_FILES
    }


def test_public_demo_receipt_requires_every_file_to_match():
    module = load_module()
    bodies = source_bytes_by_url(module)

    def fetcher(url: str):
        return 200, bodies[url], url

    payload = module.build_payload(fetcher, generated_utc="2026-07-18T07:30:00Z")

    assert payload["schema"] == "lumencore.openai_build_week_public_demo_receipt.v1"
    assert payload["status"] == "PUBLIC_DEMO_HASH_VERIFIED"
    assert payload["public_demo_verified"] is True
    assert payload["required_file_count"] == 10
    assert payload["http_200_count"] == 10
    assert payload["hash_match_count"] == 10
    assert payload["browser_qa_verified"] is True
    assert payload["browser_qa"]["capture_hash_valid"] is True
    assert all(row["hash_matches"] for row in payload["artifacts"])
    unhashed = dict(payload)
    recorded = unhashed.pop("receipt_sha256")
    assert recorded == module.stable_hash(unhashed)


def test_public_demo_receipt_fails_closed_on_remote_mutation():
    module = load_module()
    bodies = source_bytes_by_url(module)
    mutated_url = next(iter(bodies))
    bodies[mutated_url] += b"changed"

    def fetcher(url: str):
        return 200, bodies[url], url

    payload = module.build_payload(fetcher, generated_utc="2026-07-18T07:30:00Z")

    assert payload["status"] == "PUBLIC_DEMO_VERIFICATION_FAILED"
    assert payload["public_demo_verified"] is False
    assert payload["http_200_count"] == 10
    assert payload["hash_match_count"] == 9


def test_public_demo_receipt_fails_closed_on_http_error():
    module = load_module()
    bodies = source_bytes_by_url(module)
    failed_url = next(iter(bodies))

    def fetcher(url: str):
        if url == failed_url:
            return 502, b"", url
        return 200, bodies[url], url

    payload = module.build_payload(fetcher, generated_utc="2026-07-18T07:30:00Z")

    assert payload["public_demo_verified"] is False
    assert payload["all_http_200"] is False
    assert payload["http_200_count"] == 9
