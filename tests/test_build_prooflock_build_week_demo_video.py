from __future__ import annotations

import importlib.util
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "code" / "ops" / "BUILD_PROOFLOCK_BUILD_WEEK_DEMO_VIDEO.py"


def load_module():
    spec = importlib.util.spec_from_file_location("prooflock_demo_video", SCRIPT)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_builder_uses_current_bounded_v2_inputs() -> None:
    module = load_module()

    assert module.MEDIA_RECEIPT_SCHEMA.endswith(".v2")
    assert module.CONSOLE_REPO_PATH == "build_week/prooflock_console"
    assert module.WORK_DIR.name == "prooflock_console_build_week_v2"
    assert module.NARRATION_PATH.name == "prooflock_console_build_week_narration_v2.wav"
    assert module.OUTPUT_PATH.name == "prooflock_console_openai_build_week_demo_v2.mp4"
    assert [name for name, _ in module.SLIDE_SPECS] == [
        "01_boundary.png",
        "02_verified.png",
        "03_separation.png",
        "04_authority_attack.png",
        "05_restored.png",
        "06_reproducibility.png",
        "07_codex_boundary.png",
        "08_close.png",
    ]
    assert sum(duration for _, duration in module.SLIDE_SPECS) < 180


def test_builder_contains_no_stale_orchestration_or_model_claim() -> None:
    source = SCRIPT.read_text(encoding="utf-8")

    assert source.count("built.append(save_slide(") == len(load_module().SLIDE_SPECS)
    assert "LOCAL REHEARSAL - PUBLIC RELEASE HELD" in source
    assert "lumen-core.ai/build_week/prooflock_console/" not in source
    assert "loudnorm=I=-16:TP=-1.5:LRA=11" in source
    for stale in (
        "CODEX_AGENT_ORCHESTRATION_RECEIPT",
        "maximum_concurrent_open_agents",
        "identity-backed spawns",
        "gpt-5.6-sol",
        "281b76fe20d281974a2e2b44670a6a63815fe421",
    ):
        assert stale not in source


def test_receipt_hash_verifier_detects_mutation() -> None:
    module = load_module()
    receipt = {
        "schema": "lumencore.prooflock_build_week_demo_video_receipt.v2",
        "narration": {
            "duration_seconds": 120.0,
            "openai_audio_api_succeeded": False,
            "voice_disclosure": "Computer-generated narration.",
        },
        "video": {},
        "thumbnail": {"width": 1500, "height": 1000, "aspect_ratio": "3:2"},
        "source_frames": [],
        "slides": [],
        "motion_segments": [],
        "public_console_commit": "a" * 40,
        "focused_test_evidence": "50 passed, 3 skipped",
    }
    receipt["facts_sha256"] = module.stable_hash(receipt)
    receipt["receipt_sha256"] = module.stable_hash(receipt)

    valid, errors = module.verify_video_receipt(json.loads(json.dumps(receipt)))
    assert not valid
    assert "source_frame_count_mismatch" in errors
    assert "slide_count_mismatch" in errors
    assert "segment_count_mismatch" in errors

    receipt["focused_test_evidence"] = ""
    valid, errors = module.verify_video_receipt(receipt)
    assert not valid
    assert "receipt_hash_mismatch" in errors
    assert "focused_test_evidence_missing" in errors


def test_capture_provenance_requires_a_byte_identical_console_tree() -> None:
    module = load_module()
    commit = module.subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()

    provenance = module.build_capture_provenance(commit, commit)

    assert provenance["frame_source_commit"] == commit
    assert provenance["public_console_commit"] == commit
    assert provenance["console_repo_path"] == "build_week/prooflock_console"
    assert provenance["console_tree_identity_match"] is True
    assert provenance["frame_source_console_tree_oid"] == provenance["public_console_tree_oid"]


def test_normalize_utc_requires_timezone() -> None:
    module = load_module()

    assert module.normalize_utc("2026-07-20T17:00:00-05:00") == "2026-07-20T22:00:00Z"
    try:
        module.normalize_utc("2026-07-20T17:00:00")
    except ValueError as exc:
        assert "timezone" in str(exc)
    else:
        raise AssertionError("naive timestamp should be rejected")
