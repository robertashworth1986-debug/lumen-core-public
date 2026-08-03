from __future__ import annotations

import importlib.util
import inspect
from pathlib import Path

from PIL import Image, ImageStat


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "code" / "ops" / "BUILD_PROOFLOCK_BUILD_WEEK_DEMO_VIDEO.py"


def load_module():
    spec = importlib.util.spec_from_file_location("prooflock_demo_video", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_timing_is_unique_bounded_and_matches_narration():
    module = load_module()
    names = [name for name, _ in module.SLIDE_SPECS]
    durations = [duration for _, duration in module.SLIDE_SPECS]

    assert len(names) == len(set(names)) == 8
    assert all(duration > 1 for duration in durations)
    assert sum(durations) < 180
    assert 1 < module.narration_seconds(module.NARRATION_PATH) < 180


def test_builder_does_not_load_private_orchestration_receipts():
    module = load_module()
    source = SCRIPT.read_text(encoding="utf-8")

    assert not hasattr(module, "load_orchestration_receipt")
    assert "CODEX_AGENT_ORCHESTRATION_RECEIPT" not in source
    assert "maximum_concurrent_open_agents" not in source


def test_public_commit_and_test_evidence_are_explicit_build_inputs():
    module = load_module()
    parameters = inspect.signature(module.build_slides).parameters

    assert list(parameters) == ["public_commit", "test_evidence"]
    assert not hasattr(module, "PUBLIC_COMMIT")


def test_slides_render_at_1080p_and_are_not_blank():
    module = load_module()
    slides = module.build_slides("a" * 40, "Focused local tests passed")

    assert [slide.name for slide in slides] == [name for name, _ in module.SLIDE_SPECS]
    for slide in slides:
        with Image.open(slide).convert("RGB") as image:
            assert image.size == (module.WIDTH, module.HEIGHT)
            extrema = ImageStat.Stat(image).extrema
            assert any(high > low for low, high in extrema)


def test_thumbnail_renders_at_devpost_ratio_and_is_not_blank():
    module = load_module()
    thumbnail = module.build_thumbnail()

    with Image.open(thumbnail).convert("RGB") as image:
        assert image.size == (1500, 1000)
        extrema = ImageStat.Stat(image).extrema
        assert any(high > low for low, high in extrema)


def test_visual_claim_boundary_is_present_in_source():
    source = SCRIPT.read_text(encoding="utf-8")

    assert "HUMAN AUTHORITY IS NOT DELEGATED TO THE BUILD SYSTEM" in source
    assert "LOCAL REHEARSAL - PUBLIC RELEASE HELD" in source
    assert "does not prove YouTube publication" in source
    assert "audio_bed\": \"NONE" in source
