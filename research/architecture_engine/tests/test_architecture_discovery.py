import importlib.util
import sys
from pathlib import Path

MODULE_PATH = Path(__file__).resolve().parents[1] / "architecture_discovery.py"
SPEC = importlib.util.spec_from_file_location("architecture_discovery", MODULE_PATH)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
sys.modules[SPEC.name] = MODULE
SPEC.loader.exec_module(MODULE)


def test_phase_architecture_receives_validation_recipe(tmp_path):
    source = tmp_path / "phase_controller.py"
    source.write_text(
        """\nimport argparse\n\ndef run(seed=7):\n    # baseline, locked metric, checksum, negative result\n    return seed\n""",
        encoding="utf-8",
    )
    candidate = MODULE.score_candidate(
        source,
        source.read_text(encoding="utf-8"),
        "content",
        "repo",
        tmp_path,
    )
    assert candidate.category == "phase_control"
    assert "phase coherence" in candidate.locked_metrics
    assert candidate.executable_score >= 3


def test_patent_and_safety_signals_raise_gate(tmp_path):
    source = tmp_path / "private_controller.md"
    source.write_text(
        "Patent-sensitive proprietary controller. Excludes weapon targeting and lethal use.",
        encoding="utf-8",
    )
    candidate = MODULE.score_candidate(
        source,
        source.read_text(encoding="utf-8"),
        "content",
        "repo",
        tmp_path,
    )
    assert candidate.patent_sensitive is True
    assert candidate.safety_sensitive is True
    assert candidate.disclosure_risk_score >= 3
    assert "Do not execute" in candidate.claim_boundary


def test_external_metadata_mode_does_not_parse_symbols(tmp_path):
    source = tmp_path / "LumaSecretEngine.py"
    source.write_text("def undisclosed_private_method():\n    return 1\n", encoding="utf-8")
    candidates = MODULE.scan_root(tmp_path, "authorized_external_1", "metadata", 100)
    assert len(candidates) == 1
    assert candidates[0].symbols == []
    assert candidates[0].scan_mode == "metadata"
