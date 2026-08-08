from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def section(text: str, start: str, end: str) -> str:
    return text.split(start, 1)[1].split(end, 1)[0]


def test_root_five_minute_path_uses_current_canonical_implementations():
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    path = section(readme, "## Five-minute technical path", "### Independent execution target")

    assert "pull/101" in path
    assert "pull/98" in path
    assert "QUICKSTART.md" in path
    assert "CODECHECK_INDEPENDENT_EXECUTOR_HANDOFF_2026-07-21.md" in path
    assert "PROOFLOCK_OPPORTUNITY_SPRINT_DATA_HANDLING_SCHEDULE.md" in path
    assert "pull/34" not in path
    assert "pull/35" not in path
    assert "pull/36" not in path


def test_reviewer_start_separates_commit_bound_live_and_computation_truth():
    start = (ROOT / "docs" / "REVIEWER_START_HERE.md").read_text(encoding="utf-8")
    normalized = " ".join(start.split())

    assert "../dashboard/reviewer_docket.json" in start
    assert "https://lumen-core.ai/reviewer_docket.json" in start
    assert "Record any mismatch as live-release drift" in normalized
    assert "python code/proof_capsule_verifier.py" in start
    assert 'must return `"valid": true`' in normalized
    assert "Ubuntu 24.04 x86-64" in start
    assert "CPython 3.11.9" in start
    assert "a Windows or different-Python run is not protocol-matched evidence" in normalized
    assert "No non-author execution receipt or CODECHECK certificate is currently claimed" in normalized


def test_readme_labels_current_proof_capsule_standard_as_v3():
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    capability_table = section(
        readme,
        "## Current strongest public capabilities",
        "## Evidence-state definitions",
    )

    assert "Version 3 current standard merged" in capability_table
    assert "Version 2 foundation merged" not in capability_table
