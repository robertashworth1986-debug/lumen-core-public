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
    assert candidates[0].sha256 == ""
    assert candidates[0].content_hash_status == "not_computed_metadata_only"


def test_external_metadata_mode_never_hashes_private_file_contents(tmp_path):
    source = tmp_path / "LumaPrivateArchitecture.py"
    source.write_text("TOP SECRET CONTENT SENTINEL", encoding="utf-8")
    original = MODULE.sha256_file

    def guarded_sha256(path):
        if path == source:
            raise AssertionError("metadata-only scan attempted to read private contents")
        return original(path)

    MODULE.sha256_file = guarded_sha256
    try:
        candidates = MODULE.scan_root(tmp_path, "authorized_external_1", "metadata", 100)
    finally:
        MODULE.sha256_file = original

    assert len(candidates) == 1
    assert candidates[0].relative_path == "LumaPrivateArchitecture.py"
    assert candidates[0].sha256 == ""


def test_dependency_and_generated_trees_are_excluded(tmp_path):
    private_dependency = tmp_path / "runtime" / "site-packages" / "luma_engine.py"
    private_dependency.parent.mkdir(parents=True)
    private_dependency.write_text("def dependency_engine(): pass", encoding="utf-8")
    generated = tmp_path / "out" / "luma_engine.py"
    generated.parent.mkdir(parents=True)
    generated.write_text("def generated_engine(): pass", encoding="utf-8")
    worktree_copy = tmp_path / "stack.worktrees" / "luma_engine.py"
    worktree_copy.parent.mkdir(parents=True)
    worktree_copy.write_text("def copied_engine(): pass", encoding="utf-8")
    flattened = tmp_path / "exports" / "luma_site-packages_engine.py"
    flattened.parent.mkdir(parents=True)
    flattened.write_text("def flattened_dependency(): pass", encoding="utf-8")
    source = tmp_path / "src" / "luma_engine.py"
    source.parent.mkdir(parents=True)
    source.write_text("def source_engine(): pass", encoding="utf-8")

    candidates = MODULE.scan_root(tmp_path, "authorized_external_1", "metadata", 100)
    assert [candidate.relative_path for candidate in candidates] == ["src/luma_engine.py"]


def test_vanishing_file_does_not_abort_inventory(tmp_path, monkeypatch):
    stable = tmp_path / "stable_luma_engine.py"
    vanishing = tmp_path / "vanishing_luma_engine.py"
    stable.write_text("def stable(): pass", encoding="utf-8")
    vanishing.write_text("def vanishing(): pass", encoding="utf-8")
    original = MODULE.safe_stat

    def simulated_stat(path):
        if path == vanishing:
            return None
        return original(path)

    monkeypatch.setattr(MODULE, "safe_stat", simulated_stat)
    candidates = MODULE.scan_root(tmp_path, "authorized_external_1", "metadata", 100)
    assert [candidate.relative_path for candidate in candidates] == ["stable_luma_engine.py"]


def test_duplicate_register_distinguishes_exact_and_probable_matches(tmp_path):
    public_root = tmp_path / "public"
    external_root = tmp_path / "external"
    public_root.mkdir()
    external_root.mkdir()
    first = public_root / "luma_router_v1.py"
    second = public_root / "luma_router_copy.py"
    external = external_root / "luma_router_final.py"
    for path in (first, second, external):
        path.write_text("def luma_router():\n    return 1\n", encoding="utf-8")

    candidates = [
        MODULE.score_candidate(path, path.read_text(encoding="utf-8"), "content", "repo", public_root)
        for path in (first, second)
    ]
    candidates.extend(MODULE.scan_root(external_root, "authorized_external_1", "metadata", 100))
    report = tmp_path / "duplicates.md"
    MODULE.write_duplicate_conflict_register(report, candidates)
    text = report.read_text(encoding="utf-8")
    assert "Exact public duplicate groups: `1`" in text
    assert "Probable metadata duplicate groups: `1`" in text
    assert "Version/conflict families: `1`" in text


def test_canonical_source_outranks_checksum_or_mirror_receipt(tmp_path):
    source = tmp_path / "Luma_Lexicon.json"
    source.write_text('{"luma": "architecture"}', encoding="utf-8")
    receipt = tmp_path / "mirror" / "LEXICON.zip.sha256.txt"
    receipt.parent.mkdir()
    receipt.write_text("0" * 64, encoding="utf-8")
    source_candidate = MODULE.score_candidate(
        source, source.read_text(encoding="utf-8"), "content", "repo", tmp_path
    )
    receipt_candidate = MODULE.score_candidate(
        receipt, receipt.name, "metadata", "authorized_external_1", tmp_path
    )
    assert MODULE.canonical_path_score(source_candidate) > MODULE.canonical_path_score(
        receipt_candidate
    )
    unrelated = tmp_path / "luma_router.py"
    unrelated.write_text("def luma_router(): pass", encoding="utf-8")
    unrelated_candidate = MODULE.score_candidate(
        unrelated,
        unrelated.read_text(encoding="utf-8"),
        "content",
        "repo",
        tmp_path,
    )
    assert MODULE.canonical_path_score(unrelated_candidate) == 0
