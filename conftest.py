"""Clean-checkout policy for generated and retained evidence artifacts.

The frozen CODECHECK source files remain byte-identical to their reviewed
commit. Some publication tests intentionally target files produced later by
the authoritative replay workflow or retained outside Git. A clean checkout
marks only those exact tests as artifact-dependent while their inputs are
absent. Once the artifacts exist, the tests execute normally and fail closed.
"""

from __future__ import annotations

from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parent

ARTIFACT_DEPENDENT_TESTS = {
    "tests/test_eia_grid_wave_champion_benchmark.py::test_frozen_eia_panel_and_result_manifests_are_hash_valid_and_claim_safe": (
        ROOT / "data/live_measured/eia_grid_validation/eia_grid_validation_panel_latest.json",
        ROOT / "out/eia_grid_wave_champion/eia_grid_wave_champion_benchmark_latest.json",
        ROOT / "out/eia_grid_wave_champion/eia_grid_wave_champion_manifest_latest.json",
    ),
    "tests/test_reviewer_reproducibility_capsule.py::test_published_receipt_reconciles_hashes_assertions_and_public_projection": (
        ROOT / "out/ops/reviewer_reproducibility_capsule_latest.json",
        ROOT / "dashboard/data/reviewer_reproducibility_capsule.json",
    ),
    "tests/test_reviewer_reproducibility_capsule.py::test_sbom_has_scoped_component_identity_and_dependency_relationships": (
        ROOT / "evidence/reproducibility/reviewer_suite_sbom_20260714.cdx.json",
    ),
    "tests/test_reviewer_reproducibility_capsule.py::test_markdown_reports_failures_and_unmet_external_gates_plainly": (
        ROOT / "docs/REVIEWER_REPRODUCIBILITY_CAPSULE_2026-07-14.md",
    ),
}


def pytest_collection_modifyitems(items: list[pytest.Item]) -> None:
    for item in items:
        required = ARTIFACT_DEPENDENT_TESTS.get(item.nodeid)
        if not required:
            continue
        missing = [
            path.relative_to(ROOT).as_posix()
            for path in required
            if not path.is_file()
        ]
        if missing:
            item.add_marker(
                pytest.mark.skip(
                    reason="artifact-dependent check; missing from clean checkout: "
                    + ", ".join(missing)
                )
            )
