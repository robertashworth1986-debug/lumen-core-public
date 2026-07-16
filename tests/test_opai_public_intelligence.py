from __future__ import annotations

import importlib.util
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "code" / "ops" / "BUILD_OPAI_PUBLIC_INTELLIGENCE.py"


def load_module():
    spec = importlib.util.spec_from_file_location("opai_public_intelligence", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def document(module, url: str, html: str):
    return module.FetchedDocument(url=url, body=html.encode("utf-8"))


def test_snapshot_extracts_public_members_workgroups_events_models_and_datasets():
    module = load_module()
    docs = [
        document(
            module,
            "https://openpowerai.org/consortium-membership",
            """
            <html><head><title>Membership | OPAI</title></head><body>
              <h1>Consortium Membership</h1>
              <img alt="LumenCore logo"><img alt="TVA"><img alt="Image">
              <a href="https://restservice.epri.com/publicattachment/92892">Member Benefits</a>
              <p>Contact OpenPowerAI@epri.com</p>
            </body></html>
            """,
        ),
        document(
            module,
            "https://openpowerai.org/group-materials-and-meetings",
            """
            <html><body>
              <h1>Group Materials and Meetings</h1>
              <h3>Domain-Specific Model Work Group</h3>
              <p>Benchmark the DSM and curate governed datasets.</p><p>Lead: Apurba Sakti</p>
              <h3>Use Case Work Group</h3>
              <p>Set up sandboxes to evaluate use cases and protect data and IP.</p><p>Lead: Adrian Kelly</p>
            </body></html>
            """,
        ),
        document(
            module,
            "https://openpowerai.org/events",
            """
            <html><body><h1>Events</h1><h4>Quantum World Congress</h4>
            <p>Sep 23 - Sep 25, 2026</p><p>College Park, Maryland</p></body></html>
            """,
        ),
        document(
            module,
            "https://openpowerai.org/research-and-results",
            """
            <html><body><h1>Research And Results</h1>
              <h2>Models</h2><p>GridLearn</p><p>Type: Multi-Agent A grid coordination testbed.</p>
              <h2>Datasets</h2><p>EIA Dataset</p>
              <p>Source: U.S. EIA License: Public Domain</p><p>Open energy data via API.</p>
            </body></html>
            """,
        ),
    ]

    snapshot = module.build_snapshot_from_documents(
        docs,
        generated_utc="2026-07-16T00:00:00+00:00",
    )

    assert snapshot["schema"] == module.SCHEMA
    assert snapshot["organizations"] == ["LumenCore", "TVA"]
    assert {row["name"] for row in snapshot["work_groups"]} == {
        "Domain-Specific Model Work Group",
        "Use Case Work Group",
    }
    assert {row["lead"] for row in snapshot["work_groups"]} == {
        "Apurba Sakti",
        "Adrian Kelly",
    }
    assert snapshot["events"][0]["title"] == "Quantum World Congress"
    assert snapshot["models"][0]["name"] == "GridLearn"
    assert snapshot["datasets"][0]["name"] == "EIA Dataset"
    assert snapshot["official_contacts"] == ["openpowerai@epri.com"]
    assert snapshot["documents"][0]["url"].endswith("/publicattachment/92892")
    assert len(snapshot["manifest_sha256"]) == 64


def test_manifest_excludes_generation_timestamp_but_includes_source_content():
    module = load_module()
    first_docs = [
        document(
            module,
            "https://openpowerai.org/about",
            "<h1>About</h1><p>Alpha</p>",
        )
    ]
    second_docs = [
        document(
            module,
            "https://openpowerai.org/about",
            "<h1>About</h1><p>Beta</p>",
        )
    ]

    a = module.build_snapshot_from_documents(
        first_docs,
        generated_utc="2026-01-01T00:00:00+00:00",
    )
    b = module.build_snapshot_from_documents(
        first_docs,
        generated_utc="2026-12-31T00:00:00+00:00",
    )
    c = module.build_snapshot_from_documents(
        second_docs,
        generated_utc="2026-01-01T00:00:00+00:00",
    )

    assert a["manifest_sha256"] == b["manifest_sha256"]
    assert a["manifest_sha256"] != c["manifest_sha256"]


def test_crawler_scope_rejects_external_login_and_form_urls():
    module = load_module()
    assert module.is_public_crawl_url("https://openpowerai.org/research-and-results")
    assert not module.is_public_crawl_url("https://openpowerai.org/login")
    assert not module.is_public_crawl_url("https://openpowerai.org/contact-form")
    assert not module.is_public_crawl_url("https://example.com/openpowerai")
    assert not module.is_public_crawl_url("mailto:OpenPowerAI@epri.com")


def test_parser_never_creates_form_submission_records():
    module = load_module()
    doc = document(
        module,
        "https://openpowerai.org/consortium-membership",
        """
        <html><body><h1>Join</h1><form action="/submit"><input name="email"></form>
        <p>Public membership description.</p></body></html>
        """,
    )
    snapshot = module.build_snapshot_from_documents([doc])
    serialized = str(snapshot).lower()
    assert "input name" not in serialized
    assert "submit" not in snapshot["source"]["boundary"].lower()
    assert "no authentication, form submission" in snapshot["source"]["boundary"].lower()
