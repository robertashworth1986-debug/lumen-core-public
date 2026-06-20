import importlib.util
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "code" / "ops" / "BUILD_PUBLIC_EVIDENCE_READINESS_AUDIT.py"


def load_module():
    spec = importlib.util.spec_from_file_location("public_evidence_readiness_audit", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_public_evidence_audit_is_ready():
    module = load_module()
    audit = module.build_audit()

    assert audit["posture"] == "PUBLIC_SAFE_READY"
    assert audit["summary"]["blockers"] == 0
    assert audit["summary"]["manifests_matched"] == audit["summary"]["manifests_expected"]
    assert audit["summary"]["docs_checked"] == len(module.PUBLIC_DOCS)


def test_public_evidence_audit_does_not_read_private_submission_packets():
    module = load_module()
    scanned = "\n".join(
        [*(str(path) for path in module.PUBLIC_DOCS), *(str(path) for path in module.PUBLIC_EVIDENCE_RUNS)]
    ).lower()

    assert "grant_submissions" not in scanned
    assert "sam.gov" not in scanned
    assert "baat" not in scanned
    assert "dsip" not in scanned
    assert "workspace" not in scanned


def test_positive_claim_scanner_allows_boundary_language():
    module = load_module()
    dice_doc = ROOT / "docs" / "DICE_PRELIMINARY_BENCHMARK_2026-06-13.md"
    harbor_doc = ROOT / "docs" / "HARBOR_SENTINEL_VALIDATION_2026-06-13.md"

    assert module.positive_claim_hits(dice_doc) == []
    assert module.positive_claim_hits(harbor_doc) == []
