from __future__ import annotations

import importlib.util
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "code" / "ops" / "BUILD_PUBLICATION_APPROVAL_PACKET.py"


def load_module():
    spec = importlib.util.spec_from_file_location("publication_approval_packet", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_packet_requires_approval_before_public_actions():
    module = load_module()
    payload = module.build_payload()

    assert payload["schema"] == "publication_approval_packet_v3"
    assert payload["publication_policy"]["approval_required_before_live_profile_or_social_changes"] is True
    assert payload["publication_policy"]["no_auto_posting"] is True
    assert (
        payload["publication_policy"][
            "action_time_approval_required_for_every_external_publication"
        ]
        is True
    )
    assert payload["github"]["branch"] == "geometry-coverage-audit-20260623"
    assert "pull/new/geometry-coverage-audit-20260623" in payload["github"]["pr_url"]


def test_linkedin_copy_uses_bounded_evidence_numbers():
    module = load_module()
    payload = module.build_payload()
    profile = payload["linkedin_profile_draft"]
    posts = payload["social_posts"]
    registered = str(payload["geometry_audit_summary"]["registered_family_count"])

    assert "LumenCore" in profile["headline"]
    assert registered in profile["about"]
    assert "field validation" in profile["about"]
    assert "qualified direct-source links" in profile["about"]
    assert (
        payload["geometry_audit_summary"][
            "direct_source_replay_build_ready_lane_count"
        ]
        == 2
    )
    assert any("synthetic discovers" in post["copy"].lower() for post in posts)
    assert all(post["status"] == "draft_needs_user_approval" for post in posts)


def test_packet_does_not_overclaim_or_expose_secret_terms():
    module = load_module()
    payload = module.build_payload()
    rendered = module.render_markdown(payload).lower()

    forbidden = [
        "guaranteed funding",
        "guaranteed profit",
        "realized savings claim",
        "field validated families: `75`",
        "api_key",
        "bearer ",
        "private key",
        "github_pat",
    ]
    for term in forbidden:
        assert term not in rendered
    assert "must not claim field validation" in rendered
    assert "award certainty" in rendered


def test_channel_plan_prioritizes_github_site_then_linkedin():
    module = load_module()
    payload = module.build_payload()
    channels = {row["channel"]: row for row in payload["channel_plan"]}

    assert channels["GitHub"]["priority"] == 1
    assert channels["lumen-core.ai"]["priority"] == 2
    assert channels["LinkedIn"]["priority"] == 3
    assert channels["GitHub"]["approval_required"] is True
    assert channels["LinkedIn"]["approval_required"] is True
