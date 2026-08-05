from __future__ import annotations

import importlib.util
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
POLICY = ROOT / "conftest.py"


def load_policy():
    spec = importlib.util.spec_from_file_location("clean_checkout_policy", POLICY)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_artifact_policy_is_narrow_explicit_and_path_scoped():
    module = load_policy()
    policy = module.ARTIFACT_DEPENDENT_TESTS

    assert set(policy) == {
        "tests/test_eia_grid_wave_champion_benchmark.py::test_frozen_eia_panel_and_result_manifests_are_hash_valid_and_claim_safe",
        "tests/test_reviewer_reproducibility_capsule.py::test_published_receipt_reconciles_hashes_assertions_and_public_projection",
        "tests/test_reviewer_reproducibility_capsule.py::test_sbom_has_scoped_component_identity_and_dependency_relationships",
        "tests/test_reviewer_reproducibility_capsule.py::test_markdown_reports_failures_and_unmet_external_gates_plainly",
    }
    assert all(paths for paths in policy.values())
    assert all(path.is_absolute() for paths in policy.values() for path in paths)
    assert all(path.is_relative_to(ROOT) for paths in policy.values() for path in paths)


def test_policy_does_not_skip_when_required_artifacts_exist(tmp_path, monkeypatch):
    module = load_policy()
    required = (tmp_path / "receipt.json", tmp_path / "report.md")
    for path in required:
        path.write_text("bounded\n", encoding="utf-8")

    nodeid = "tests/example.py::test_publication"
    monkeypatch.setattr(module, "ARTIFACT_DEPENDENT_TESTS", {nodeid: required})

    class Item:
        def __init__(self):
            self.nodeid = nodeid
            self.markers = []

        def add_marker(self, marker):
            self.markers.append(marker)

    item = Item()
    module.pytest_collection_modifyitems([item])
    assert item.markers == []
