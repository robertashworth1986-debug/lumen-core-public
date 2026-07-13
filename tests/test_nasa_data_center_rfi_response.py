from __future__ import annotations

import importlib.util
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SOURCE = (
    ROOT
    / "grant_submissions"
    / "funding_sprint_20260709"
    / "NASA_DATA_CENTER_RFI_READY_RESPONSE_2026-07-11.md"
)
MODULE_PATH = ROOT / "code" / "render_nasa_data_center_rfi_response.py"


def load_module():
    spec = importlib.util.spec_from_file_location("render_nasa_rfi", MODULE_PATH)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_source_answers_all_seven_nasa_topics_and_preserves_boundaries():
    text = SOURCE.read_text(encoding="utf-8")
    required = [
        "Partnership Models and Value Creation",
        "Future Data Center Concepts",
        "Modernization of Legacy Facilities",
        "Reliability, Resilience, and Security",
        "Operational and Service Models",
        "Scalability and Future Demand",
        "Sustainability and Efficiency",
    ]
    assert all(label in text for label in required)
    assert "No pricing is included" in text
    assert "No NASA deployment" in text
    assert "READY_FOR_HUMAN_REVIEW" not in text
    assert "Attachments To Consider" not in text


def test_renderer_builds_a_nontrivial_pdf(tmp_path: Path):
    module = load_module()
    output = tmp_path / "nasa-rfi.pdf"
    built = module.build_pdf(SOURCE, output)
    payload = built.read_bytes()
    assert payload.startswith(b"%PDF")
    assert len(payload) > 10_000
