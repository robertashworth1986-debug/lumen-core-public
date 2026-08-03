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
    progress = builder.portal_progress_snapshot()

    assert registry["schema"] == "lumencore.openai_build_week_devpost_field_registry.v1"
    assert registry["deadline"]["central"] == "2026-07-21T19:00:00-05:00"
    assert registry["deadline"]["utc"] == "2026-07-22T00:00:00Z"
    portal = registry["portal_observation"]
    assert portal["observed_utc"] == progress["recorded_observation_utc"]
    assert portal["authentication_state"] == "SIGNED_IN_AT_OBSERVATION"
    assert portal["hackathon_join_state"] == "REGISTERED_CONFIRMED"
    assert portal["project_state"] == "DRAFT_2_OF_5_CONFIRMED"
    assert portal["submission_confirmation_state"] == "NONE_OBSERVED"
    assert portal["progress_receipt"]["evidence_basis_count"] == 2
    assert portal["progress_receipt"]["evidence_classes"] == [
        "DIRECT_BROWSER_OBSERVATION",
        "INDEPENDENT_GMAIL_METADATA",
    ]
    assert portal["progress_receipt"]["challenge_registration_state"] == "CONFIRMED"
    assert portal["progress_receipt"]["project_shell_creation_state"] == "DRAFT_2_OF_5_CONFIRMED"

    unhashed = dict(registry)
    recorded_hash = unhashed.pop("registry_sha256")
    assert recorded_hash == builder.stable_hash(unhashed)
    assert all(row.get("embedded_integrity", {}).get("valid", True) for row in registry["source_registry"].values())

    fields = {row["field_id"]: row for row in registry["fields"]}
    assert len(fields) == 21
    assert fields["project_name"]["portal_label"] == "Project name"
    assert fields["project_tagline"]["portal_label"] == "Project tagline"
    assert fields["project_tagline"]["format_rule"].startswith("Maximum 140")
    assert fields["thumbnail_image"]["completion_state"] == "SOURCE_BACKED_LOCAL_UPLOAD_READY_PUBLICATION_OPEN"
    assert fields["video_demo_link"]["completion_state"] == "LOCAL_VIDEO_VERIFIED_PUBLICATION_OPEN"
    assert fields["category"]["portal_label"] is None
    assert fields["category"]["portal_label_exact"] is False
    assert fields["confirmed_model_identity"]["proposed_value"] == "gpt-5.6-sol"
    assert fields["feedback_session_id"]["proposed_value"] is None
    assert fields["official_rules_and_terms"]["completion_state"] == "HUMAN_LEGAL_ACCEPTANCE_REQUIRED"
    assert fields["final_submit_action"]["completion_state"] == "FINAL_HUMAN_ACTION_BLOCKED"

    assert registry["model_and_session_placeholders"] == {
        "confirmed_model_label": "gpt-5.6-sol",
        "model_usage_sentence": builder.MODEL_USAGE_SENTENCE,
        "feedback_session_id": None,
        "public_youtube_url": None,
        "thumbnail_asset": "output/video/prooflock_console_build_week_v1/prooflock_console_devpost_thumbnail_v1.png",
        "submitter_type": None,
        "country_of_residence": None,
        "representative_authorization": None,
    }
    assert "submit" in registry["actions_prohibited_for_this_kit"]
    assert "contact_anyone" in registry["actions_prohibited_for_this_kit"]
    assert registry["actions_observed_external_to_this_kit"] == [
        "challenge_registration",
        "project_shell_creation",
    ]


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
    assert receipt["effective_readiness_after_portal_progress"] == {
        "counts": {"gate_total": 10, "pass": 6, "open": 4, "fail": 0},
        "open_gate_ids": ["feedback_session", "final_submission", "model_provenance", "youtube_demo"],
        "newly_satisfied_gate_ids": ["devpost_registration"],
        "ready_for_final_submission": False,
        "basis": "verified portal progress receipt",
    }
    assert receipt["status"] == "NOT_READY_FOR_SUBMISSION"
    assert receipt["ready_for_portal_population"] is False
    assert receipt["ready_for_final_submission"] is False
    assert receipt["actions_performed"] == []
    assert receipt["model_and_session_provenance"]["confirmed_model_label"] == "gpt-5.6-sol"
    assert receipt["model_and_session_provenance"]["feedback_session_id"] is None
    assert "DEVPOST_SIGNED_OUT" not in receipt["hard_blockers"]
    assert "HACKATHON_NOT_JOINED" not in receipt["hard_blockers"]
    assert "PROJECT_CREATION_CAPTCHA_OPEN" not in receipt["hard_blockers"]
    assert "NO_PROVEN_DEVPOST_PROJECT" not in receipt["hard_blockers"]
    assert "MODEL_IDENTITY_UNCONFIRMED" not in receipt["hard_blockers"]
    assert "PROJECT_DETAILS_INCOMPLETE" in receipt["hard_blockers"]
    assert "ADDITIONAL_INFO_INCOMPLETE" in receipt["hard_blockers"]
    assert "CUSTOM_PORTAL_LABELS_UNOBSERVED" in receipt["hard_blockers"]
    assert receipt["actions_observed_external_to_this_builder"] == [
        "challenge_registration",
        "project_shell_creation",
    ]

    unhashed = dict(receipt)
    recorded_hash = unhashed.pop("receipt_sha256")
    assert recorded_hash == builder.stable_hash(unhashed)


def test_generated_completion_artifacts_are_hash_linked_and_contain_no_fabricated_provenance(
    tmp_path: Path,
    monkeypatch,
) -> None:
    builder = load_builder()
    output_names = {
        "FIELD_REGISTRY_PATH": "field_registry.json",
        "PROJECT_COPY_PATH": "project_copy.md",
        "COMPLETION_KIT_PATH": "completion_kit.md",
        "READINESS_RECEIPT_PATH": "readiness_receipt.json",
    }
    for attribute, filename in output_names.items():
        monkeypatch.setattr(builder, attribute, tmp_path / filename)

    original_repo_relative = builder.repo_relative

    def bounded_test_relative(path: Path) -> str:
        try:
            return path.resolve().relative_to(tmp_path.resolve()).as_posix()
        except ValueError:
            return original_repo_relative(path)

    monkeypatch.setattr(builder, "repo_relative", bounded_test_relative)
    outputs = builder.write_outputs(FIXED_GENERATED_UTC)

    registry = json.loads(outputs["field_registry"].read_text(encoding="utf-8"))
    receipt = json.loads(outputs["readiness_receipt"].read_text(encoding="utf-8"))
    project_copy = outputs["project_copy"].read_text(encoding="utf-8")
    completion_kit = outputs["completion_kit"].read_text(encoding="utf-8")

    recorded = {row["path"]: row for row in receipt["submission_artifacts"]}
    for name in ("field_registry", "project_copy", "completion_kit"):
        path = outputs[name]
        row = recorded[path.name]
        assert row["sha256"] == builder.file_sha256(path)
        assert row["bytes"] == path.stat().st_size

    assert registry["project_copy"]["copy_state"] == "VIDEO_ASSETS_VERIFIED_FEEDBACK_AND_PUBLICATION_OPEN"
    assert "[[CONFIRMED_MODEL_LABEL]]" not in project_copy
    assert "gpt-5.6-sol" in project_copy
    assert "[[FEEDBACK_SESSION_ID]]" in project_copy
    assert "[[PUBLIC_YOUTUBE_URL]]" in project_copy
    assert "6/10" in completion_kit
    assert "REGISTERED_CONFIRMED" in completion_kit
    assert "DRAFT_2_OF_5_CONFIRMED" in completion_kit
    assert "two-of-five project draft are confirmed" in completion_kit

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
