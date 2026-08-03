from __future__ import annotations

import copy
import importlib.util
import json
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = ROOT / "code" / "ops" / "BUILD_LINKEDIN_GROWTH_PACK.py"
CONFIG_PATH = ROOT / "config" / "linkedin_growth_pack_v1.json"


def load_module():
    spec = importlib.util.spec_from_file_location("linkedin_growth_pack", MODULE_PATH)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.fixture(scope="module")
def module():
    return load_module()


@pytest.fixture()
def production_config():
    return json.loads(CONFIG_PATH.read_text(encoding="utf-8"))


def fixture_config(tmp_path: Path, production_config: dict) -> dict:
    config = copy.deepcopy(production_config)
    (tmp_path / "evidence.txt").write_text("bounded evidence\n", encoding="utf-8")
    media_dir = tmp_path / "media"
    media_dir.mkdir()
    (media_dir / "a.mp4").write_bytes(b"video-a")
    (media_dir / "b.mp4").write_bytes(b"video-b")
    (media_dir / "c.mp4").write_bytes(b"video-a")

    config["source_evidence"] = [
        {
            "path": "evidence.txt",
            "required": True,
            "supports": ["fixture"],
            "public_use_note": "fixture only",
        }
    ]
    config["media"] = {
        "scan_roots": ["media"],
        "primary_assets": [
            {
                "path": "media/a.mp4",
                "media_class": "PRIMARY_RENDER",
                "title": "A",
                "content_summary": "Fixture A",
                "public_use_state": "DRAFT_ONLY",
                "claim_boundary": "Fixture only.",
                "storyboard_rank": 3,
                "receipt_path": "",
                "receipt_schema": "",
            },
            {
                "path": "media/b.mp4",
                "media_class": "PRIMARY_RENDER",
                "title": "B",
                "content_summary": "Fixture B",
                "public_use_state": "DRAFT_ONLY",
                "claim_boundary": "Fixture only.",
                "storyboard_rank": 2,
                "receipt_path": "",
                "receipt_schema": "",
            },
            {
                "path": "media/c.mp4",
                "media_class": "PRIMARY_RENDER",
                "title": "C",
                "content_summary": "Fixture C",
                "public_use_state": "DRAFT_ONLY",
                "claim_boundary": "Fixture only.",
                "storyboard_rank": 1,
                "receipt_path": "",
                "receipt_schema": "",
            },
        ],
    }
    for storyboard, source_path in zip(
        config["storyboard_briefs"],
        ["media/a.mp4", "media/b.mp4", "media/c.mp4"],
        strict=True,
    ):
        storyboard["source_path"] = source_path
    return config


def test_production_config_has_complete_safe_content(module, production_config):
    module.validate_config(production_config)
    safety = module.scan_public_copy(production_config)

    assert len(production_config["calendar"]) == 30
    assert len(production_config["post_drafts"]) == 12
    assert len(production_config["reply_templates"]) == 12
    assert len(production_config["storyboard_briefs"]) == 3
    assert len(production_config["message_action_drafts"]) == 2
    assert len(production_config["profile_gap_actions"]) >= 8
    assert len(production_config["profile"]["headline"]) <= 220
    assert safety == {"private_hits": [], "unsupported_claim_hits": []}
    assert all(
        value is False
        for key, value in production_config["action_controls"].items()
        if key != "human_review_required"
    )
    assert production_config["action_controls"]["human_review_required"] is True
    assert production_config["live_profile_snapshot"]["metrics"] == {
        "connections": 22,
        "followers": 26,
        "profile_views": 15,
        "post_impressions_7d": 25,
        "search_appearances": 3,
    }
    assert all(
        item["status"] == "DRAFT_NOT_SENT" and item["send_allowed"] is False
        for item in production_config["message_action_drafts"]
    )
    assert any(
        item["severity"] == "HIGH"
        and item["automation_action"] == "NONE"
        and "trading post" in item["item"].lower()
        for item in production_config["content_risk_register"]
    )


def test_build_is_deterministic_and_deduplicates_media(
    module, tmp_path, production_config
):
    config = fixture_config(tmp_path, production_config)

    first = module.build_pack(tmp_path, config, probe_media=False)
    second = module.build_pack(tmp_path, config, probe_media=False)

    assert first == second
    assert module.render_outputs(first) == module.render_outputs(second)
    assert first["video_inventory"]["video_file_count"] == 3
    assert first["video_inventory"]["unique_content_count"] == 2
    assert first["video_inventory"]["duplicate_file_count"] == 1

    items = {item["path"]: item for item in first["video_inventory"]["items"]}
    assert items["media/a.mp4"]["duplicate_of"] == ""
    assert items["media/c.mp4"]["duplicate_of"] == "media/a.mp4"
    assert first["safety"]["public_copy_private_hit_count"] == 0
    assert first["safety"]["public_copy_unsupported_claim_hit_count"] == 0


def test_write_and_check_round_trip(module, tmp_path, production_config):
    root = tmp_path / "repo"
    root.mkdir()
    config = fixture_config(root, production_config)
    pack = module.build_pack(root, config, probe_media=False)
    outputs = module.render_outputs(pack)
    out_dir = root / "out" / "linkedin_growth_pack"

    module.write_outputs(out_dir, outputs)
    assert module.check_outputs(out_dir, outputs) == []

    (out_dir / "POST_DRAFTS.md").write_text("tampered\n", encoding="utf-8")
    assert module.check_outputs(out_dir, outputs) == ["mismatch:POST_DRAFTS.md"]


@pytest.mark.parametrize(
    ("mutator", "expected"),
    [
        (
            lambda config: config["profile"].__setitem__(
                "about",
                config["profile"]["about"] + "\nContact person@example.com.",
            ),
            "private markers",
        ),
        (
            lambda config: config["post_drafts"][0].__setitem__(
                "body",
                config["post_drafts"][0]["body"] + "\nThis is government-approved.",
            ),
            "unsupported claims",
        ),
        (
            lambda config: config["post_drafts"][0].__setitem__(
                "body",
                config["post_drafts"][0]["body"] + "\nGuaranteed outcomes.",
            ),
            "unsupported claims",
        ),
    ],
)
def test_public_copy_fails_closed_on_private_or_unsupported_language(
    module, production_config, mutator, expected
):
    config = copy.deepcopy(production_config)
    mutator(config)

    with pytest.raises(module.GrowthPackError, match=expected):
        module.validate_config(config)


def test_featured_link_and_calendar_rules_fail_closed(module, production_config):
    dead_link = copy.deepcopy(production_config)
    dead_link["featured_links"][0]["http_status"] = 502
    with pytest.raises(module.GrowthPackError, match="HTTP 200"):
        module.validate_config(dead_link)

    calendar_gap = copy.deepcopy(production_config)
    calendar_gap["calendar"][1]["date"] = "2026-07-30"
    with pytest.raises(module.GrowthPackError, match="consecutive"):
        module.validate_config(calendar_gap)


def test_path_escape_and_unknown_storyboard_source_fail_closed(
    module, production_config
):
    escaped = copy.deepcopy(production_config)
    escaped["source_evidence"][0]["path"] = "../private.txt"
    with pytest.raises(module.GrowthPackError, match="Unsafe"):
        module.validate_config(escaped)

    unknown_source = copy.deepcopy(production_config)
    unknown_source["storyboard_briefs"][0]["source_path"] = "media/unknown.mp4"
    with pytest.raises(module.GrowthPackError, match="not a configured primary asset"):
        module.validate_config(unknown_source)


def test_production_build_has_receipt_backed_clips_and_holds_raw_media(
    module, production_config
):
    pack = module.build_pack(ROOT, production_config, probe_media=False)
    inventory = pack["video_inventory"]
    items = {item["path"]: item for item in inventory["items"]}

    assert inventory["video_file_count"] >= 35
    assert inventory["unique_content_count"] < inventory["video_file_count"]
    assert inventory["primary_asset_count"] == 8
    assert inventory["receipt_backed_primary_count"] == 3
    assert (
        items["data/IMG_2361.mov"]["public_use_state"]
        == "HOLD_CONTEXT_AND_RIGHTS_CONFIRMATION_REQUIRED"
    )
    assert items[
        "output/video/prooflock_console_build_week_v2/"
        "prooflock_console_openai_build_week_demo_v2.mp4"
    ]["receipt"]["schema_matches"] is True
    assert (
        items["data/IMG_0694.MOV"]["public_use_state"]
        == "HOLD_PRIVACY_AND_CONSENT_REQUIRED"
    )
    assert (
        items["data/Grants outreach_/Important documents_/IMG_5059.MOV"][
            "public_use_state"
        ]
        == "HOLD_THIRD_PARTY_CONSENT_AND_CONTEXT_REQUIRED"
    )


def test_output_set_is_complete_and_public_copy_omits_resume_identifiers(
    module, production_config
):
    pack = module.build_pack(ROOT, production_config, probe_media=False)
    outputs = module.render_outputs(pack)

    assert set(outputs) == {
        "README.md",
        "LINKEDIN_PROFILE_REWRITE.md",
        "FEATURED_SECTION_PLAN.md",
        "PROFILE_GAP_ACTION_PLAN.md",
        "CONTENT_CALENDAR_30_DAY.md",
        "POST_DRAFTS.md",
        "ENGAGEMENT_REPLY_TEMPLATES.md",
        "MESSAGE_ACTION_DRAFTS.md",
        "VIDEO_INVENTORY.md",
        "CAPCUT_STORYBOARDS.md",
        "linkedin_growth_pack.json",
        "MANIFEST.json",
    }
    public_markdown = b"\n".join(
        payload for name, payload in outputs.items() if name.endswith(".md")
    ).decode("utf-8")
    assert "mailto:" not in public_markdown
    assert "@gmail.com" not in public_markdown
    assert "615-438" not in public_markdown
    assert "SQY2" not in public_markdown
    assert "14TM8" not in public_markdown
    assert pack["safety"]["all_public_actions_blocked"] is True


def test_recruiter_draft_preserves_material_fit_gaps(module, production_config):
    pack = module.build_pack(ROOT, production_config, probe_media=False)
    recruiter = next(
        item
        for item in pack["message_action_drafts"]
        if item["recipient_public_name"] == "Roberto Gomez Castro"
    )

    assert recruiter["selected_action"] == "CLARIFY_MUST_HAVE_REQUIREMENTS_BEFORE_APPLYING"
    assert recruiter["send_allowed"] is False
    assert any("bachelor" in item.lower() for item in recruiter["missing_or_unverified_fit"])
    assert any("CCTV" in item for item in recruiter["missing_or_unverified_fit"])
    assert "do not want to overstate" in recruiter["draft"].lower()
