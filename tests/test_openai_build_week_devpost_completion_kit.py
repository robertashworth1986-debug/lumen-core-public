from __future__ import annotations

import importlib.util
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
BUILDER_PATH = ROOT / "code" / "ops" / "BUILD_OPENAI_BUILD_WEEK_DEVPOST_COMPLETION_KIT.py"
FIXED_GENERATED_UTC = "2026-07-19T03:05:09Z"


def load_builder():
    spec = importlib.util.spec_from_file_location("openai_build_week_devpost_completion_kit", BUILDER_PATH)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_field_registry_is_source_backed_and_fail_closed() -> None:
    builder = load_builder()
    registry = builder.build_field_registry(FIXED_GENERATED_UTC)

    assert registry["schema"] == "lumencore.openai_build_week_devpost_field_registry.v1"
    assert registry["deadline"]["central"] == "2026-07-21T19:00:00-05:00"
    assert registry["deadline"]["utc"] == "2026-07-22T00:00:00Z"
    assert registry["portal_observation"] == {
        "observed_utc": "2026-07-19T03:05:09Z",
        "authentication_state": "SIGNED_OUT",
        "hackathon_join_state": "NOT_JOINED",
        "project_state": "NO_PROJECT_OBSERVED",
        "submission_confirmation_state": "NONE_OBSERVED",
        "observation_basis": (
            "Current task state and the unsigned public submission-manager page displayed Log in, Sign up, "
            "Join hackathon, and Register for this hackathon."
        ),
        "limitations": (
            "No account, project, registration, or confirmation endpoint was opened or changed by this builder."
        ),
    }

    unhashed = dict(registry)
    recorded_hash = unhashed.pop("registry_sha256")
    assert recorded_hash == builder.stable_hash(unhashed)
    assert all(row.get("embedded_integrity", {}).get("valid", True) for row in registry["source_registry"].values())

    fields = {row["field_id"]: row for row in registry["fields"]}
    assert len(fields) == 21
    assert fields["project_name"]["portal_label"] == "Project name"
    assert fields["project_tagline"]["portal_label"] == "Project tagline"
    assert fields["project_tagline"]["format_rule"].startswith("Maximum 140")
    assert fields["thumbnail_image"]["completion_state"] == "MISSING_PUBLIC_ASSET"
    assert fields["video_demo_link"]["completion_state"] == "MISSING_PUBLIC_YOUTUBE_VIDEO"
    assert fields["category"]["portal_label"] is None
    assert fields["category"]["portal_label_exact"] is False
    assert fields["confirmed_model_identity"]["proposed_value"] is None
    assert fields["feedback_session_id"]["proposed_value"] is None
    assert fields["official_rules_and_terms"]["completion_state"] == "HUMAN_LEGAL_ACCEPTANCE_REQUIRED"
    assert fields["final_submit_action"]["completion_state"] == "FINAL_HUMAN_ACTION_BLOCKED"

    assert registry["model_and_session_placeholders"] == {
        "confirmed_model_label": None,
        "model_usage_sentence": None,
        "feedback_session_id": None,
        "public_youtube_url": None,
        "thumbnail_asset": None,
        "submitter_type": None,
        "country_of_residence": None,
        "representative_authorization": None,
    }
    assert "submit" in registry["actions_prohibited_for_this_kit"]
    assert "contact_anyone" in registry["actions_prohibited_for_this_kit"]


def test_readiness_receipt_preserves_five_of_ten_snapshot_and_never_promotes() -> None:
    builder = load_builder()
    registry = builder.build_field_registry(FIXED_GENERATED_UTC)
    snapshot = builder.readiness_snapshot()
    receipt = builder.build_readiness_receipt(FIXED_GENERATED_UTC, registry, snapshot, [])

    assert snapshot["counts"] == {"gate_total": 10, "pass": 5, "open": 5, "fail": 0}
    assert snapshot["open_gate_ids"] == [
        "devpost_registration",
        "feedback_session",
        "final_submission",
        "model_provenance",
        "youtube_demo",
    ]
    assert receipt["status"] == "NOT_READY_FOR_SUBMISSION"
    assert receipt["ready_for_portal_population"] is False
    assert receipt["ready_for_final_submission"] is False
    assert receipt["actions_performed"] == []
    assert receipt["model_and_session_provenance"]["confirmed_model_label"] is None
    assert receipt["model_and_session_provenance"]["feedback_session_id"] is None
    assert "DEVPOST_SIGNED_OUT" in receipt["hard_blockers"]
    assert "CUSTOM_PORTAL_LABELS_UNOBSERVED" in receipt["hard_blockers"]

    unhashed = dict(receipt)
    recorded_hash = unhashed.pop("receipt_sha256")
    assert recorded_hash == builder.stable_hash(unhashed)


def test_generated_completion_artifacts_are_hash_linked_and_contain_no_fabricated_provenance() -> None:
    builder = load_builder()
    outputs = builder.write_outputs(FIXED_GENERATED_UTC)

    registry = json.loads(outputs["field_registry"].read_text(encoding="utf-8"))
    receipt = json.loads(outputs["readiness_receipt"].read_text(encoding="utf-8"))
    project_copy = outputs["project_copy"].read_text(encoding="utf-8")
    completion_kit = outputs["completion_kit"].read_text(encoding="utf-8")

    recorded = {row["path"]: row for row in receipt["submission_artifacts"]}
    for name in ("field_registry", "project_copy", "completion_kit"):
        path = outputs[name]
        row = recorded[path.relative_to(ROOT).as_posix()]
        assert row["sha256"] == builder.file_sha256(path)
        assert row["bytes"] == path.stat().st_size

    assert registry["project_copy"]["copy_state"] == "NOT_PASTE_READY_MODEL_AND_VIDEO_PROVENANCE_OPEN"
    assert "[[CONFIRMED_MODEL_LABEL]]" in project_copy
    assert "[[FEEDBACK_SESSION_ID]]" in project_copy
    assert "[[PUBLIC_YOUTUBE_URL]]" in project_copy
    assert "5/10" in completion_kit
    assert "signed out" in completion_kit.lower()
    assert "not joined" in completion_kit.lower()
    assert "No Devpost project or submission confirmation exists." in completion_kit

    combined = "\n".join(
        [
            outputs["field_registry"].read_text(encoding="utf-8"),
            project_copy,
            completion_kit,
            outputs["readiness_receipt"].read_text(encoding="utf-8"),
        ]
    )
    assert "sk-" not in combined
    assert "Bearer " not in combined
    assert "@gmail.com" not in combined
    assert "ready_for_final_submission\": true" not in combined
