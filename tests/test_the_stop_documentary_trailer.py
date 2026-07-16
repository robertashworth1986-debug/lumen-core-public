from __future__ import annotations

import importlib.util
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = ROOT / "code" / "social" / "build_the_stop_documentary_trailer.py"


def _load_module():
    spec = importlib.util.spec_from_file_location("build_the_stop_documentary_trailer", MODULE_PATH)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_receipt_enforces_failed_gate_and_pending_external_review() -> None:
    module = _load_module()
    payload, metrics = module.load_and_validate_receipt()
    assert payload["independently_validated"] is False
    assert payload["execution_authorized"] is False
    assert payload["capital_at_risk_allowed"] is False
    assert metrics["diagnostic"] > 0
    assert metrics["reviewer"] < 0
    assert metrics["positive"] == 11
    assert metrics["total"] == 20
    assert metrics["promoted"] == 0
    assert metrics["kit_integrity_passed"] is True


def test_documentary_format_and_runtime_are_cinematic() -> None:
    module = _load_module()
    assert (module.WIDTH, module.HEIGHT) == (1920, 1080)
    assert module.FPS == 24
    assert 75.0 <= module.DURATION <= 90.0


def test_conversation_motifs_are_short_and_public_safe() -> None:
    module = _load_module()
    assert "We only claim facts." in module.CONVERSATION_MOTIFS
    assert "I love integrity checks." in module.CONVERSATION_MOTIFS
    assert all(len(value) <= 80 for value in module.CONVERSATION_MOTIFS)


def test_frozen_private_video_is_not_a_render_source() -> None:
    text = MODULE_PATH.read_text(encoding="utf-8").lower()
    assert "video_1.mov" not in text
    assert "img_2361.mov" not in text
    assert "img_2362.mov" not in text
    assert "physical_context_long_video" in text


def test_narration_discloses_boundary_without_promotion_language() -> None:
    module = _load_module()
    narration = module.NARRATION_TEXT.lower()
    assert "the answer went negative" in narration
    assert "no capital at risk" in narration
    assert "independent reviewer" in narration
    prohibited = ["validated alpha", "guaranteed", "approved performance", "kraken endorsed"]
    for phrase in prohibited:
        assert phrase not in narration
    source = MODULE_PATH.read_text(encoding="utf-8")
    assert "Synthetic narration" in source
