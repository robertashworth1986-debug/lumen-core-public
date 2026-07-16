from __future__ import annotations

import importlib.util
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = ROOT / "code" / "social" / "build_tiktok_truth_video.py"


def _load_module():
    spec = importlib.util.spec_from_file_location("build_tiktok_truth_video", MODULE_PATH)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_receipt_enforces_rejection_boundary() -> None:
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


def test_video_format_is_vertical_and_tiktok_native() -> None:
    module = _load_module()
    assert module.WIDTH == 1080
    assert module.HEIGHT == 1920
    assert module.FPS == 30
    assert 20.0 <= module.DURATION <= 60.0


def test_public_copy_does_not_promote_performance() -> None:
    text = MODULE_PATH.read_text(encoding="utf-8").lower()
    prohibited = [
        "guaranteed alpha",
        "kraken endorsed",
        "independently validated alpha",
        "approved performance",
    ]
    for phrase in prohibited:
        assert phrase not in text
