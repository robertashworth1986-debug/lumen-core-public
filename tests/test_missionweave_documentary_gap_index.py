from __future__ import annotations

import importlib.util
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "code" / "ops" / "BUILD_MISSIONWEAVE_DOCUMENTARY_GAP_INDEX.py"
OUT_JSON = (
    ROOT
    / "grant_submissions"
    / "DLA26BZ03_NV011_MissionWeave"
    / "MISSIONWEAVE_DOCUMENTARY_GAP_INDEX_2026-07-18.json"
)


def load_module():
    spec = importlib.util.spec_from_file_location(
        "missionweave_documentary_gap_index", SCRIPT
    )
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_filename_classifier_is_bounded_to_plausible_evidence_files():
    module = load_module()

    assert module.classify_filename("DD_Form_2345_certified.pdf") == {
        "DD2345_OR_JCP_APPLICATION_EVIDENCE"
    }
    assert module.classify_filename("Joint_Certification_Program_application.pdf") == {
        "DD2345_OR_JCP_APPLICATION_EVIDENCE"
    }
    assert module.classify_filename("annual_FWA_training_certificate.pdf") == {
        "MISSIONWEAVE_FWA_TRAINING_EVIDENCE"
    }
    assert module.classify_filename("SAM_representations_2026.pdf") == {
        "SAM_REPRESENTATIONS_EVIDENCE"
    }
    assert module.classify_filename(
        "MissionWeave_portal_preview_receipt.json"
    ) == {"MISSIONWEAVE_PORTAL_PREVIEW_RECEIPT"}

    assert module.classify_filename("JCPB.json") == set()
    assert module.classify_filename("generic_portal_preview_receipt.json") == set()
    assert module.classify_filename("SAM_registration.pdf") == set()
    assert module.classify_filename("FWA_notes.exe") == set()


def test_metadata_scan_skips_cache_noise_and_never_publishes_paths(tmp_path):
    module = load_module()
    root = tmp_path / "private-root-name"
    root.mkdir()
    for name in (
        "DD2345_application.pdf",
        "annual_FWA_training_certificate.pdf",
        "SAM_representations.pdf",
        "MissionWeave_portal_preview_receipt.json",
    ):
        (root / name).write_bytes(b"private content must not be read or published")

    cache = root / ".venv" / "Lib"
    cache.mkdir(parents=True)
    (cache / "JCP_evidence.pdf").write_bytes(b"noise")
    execution = root / "out" / "execution"
    execution.mkdir(parents=True)
    (execution / "JCP.json").write_bytes(b"market symbol noise")

    payload = module.build_payload(
        [("synthetic_root", root)],
        generated_utc="2026-07-18T12:00:00+00:00",
    )
    rendered = json.dumps(payload, sort_keys=True)

    assert payload["status"] == "PRIVATE_MANUAL_DOCUMENT_REVIEW_REQUIRED"
    assert payload["summary"]["candidate_total"] == 4
    assert payload["summary"]["candidate_counts"] == {
        "DD2345_OR_JCP_APPLICATION_EVIDENCE": 1,
        "MISSIONWEAVE_FWA_TRAINING_EVIDENCE": 1,
        "MISSIONWEAVE_PORTAL_PREVIEW_RECEIPT": 1,
        "SAM_REPRESENTATIONS_EVIDENCE": 1,
    }
    assert payload["controls"]["file_contents_read"] is False
    assert payload["controls"]["candidate_paths_published"] is False
    assert payload["roots"][0]["candidate_details_published"] is False
    assert "private-root-name" not in rendered
    assert "DD2345_application.pdf" not in rendered
    assert "private content" not in rendered
    assert payload["roots"][0]["skipped_directory_count"] == 2

    unhashed = dict(payload)
    recorded = unhashed.pop("index_sha256")
    assert recorded == module.stable_hash(unhashed)


def test_zero_candidate_scan_keeps_every_documentary_gate_open(tmp_path):
    module = load_module()
    root = tmp_path / "empty"
    root.mkdir()
    (root / "ordinary_note.txt").write_text("not evidence", encoding="utf-8")

    payload = module.build_payload(
        [("synthetic_root", root)],
        generated_utc="2026-07-18T12:00:00+00:00",
    )

    assert payload["status"] == "NO_QUALIFYING_DOCUMENTARY_CANDIDATES_LOCATED"
    assert payload["summary"]["candidate_total"] == 0
    assert all(
        payload["gate_decisions"][name] == "NO_CHANGE_KEEP_GATE_OPEN"
        for name in module.DOCUMENT_CLASSES
    )
    assert payload["gate_decisions"]["DSIP_FIRM_PIN_AVAILABILITY"] == (
        "PORTAL_ONLY_NO_FILE_INFERENCE"
    )
    assert "does not prove that no document exists elsewhere" in payload[
        "claim_boundary"
    ]


def test_written_public_index_is_private_path_free_and_fail_closed():
    module = load_module()
    payload = json.loads(OUT_JSON.read_text(encoding="utf-8"))
    rendered = json.dumps(payload, sort_keys=True).lower()

    assert payload["schema"] == module.SCHEMA
    assert payload["status"] == "NO_QUALIFYING_DOCUMENTARY_CANDIDATES_LOCATED"
    assert payload["summary"]["candidate_total"] == 0
    assert payload["summary"]["complete_root_count"] == payload["summary"][
        "root_count"
    ]
    assert payload["controls"]["file_contents_read"] is False
    assert payload["controls"]["candidate_paths_published"] is False
    assert "c:\\users" not in rendered
    assert "e:\\" not in rendered
    assert "@gmail.com" not in rendered
    assert '"firm_pin":' not in rendered
    assert '"firm_pin_value":' not in rendered
    assert payload["gate_decisions"]["DSIP_FIRM_PIN_AVAILABILITY"] == (
        "PORTAL_ONLY_NO_FILE_INFERENCE"
    )

    unhashed = dict(payload)
    recorded = unhashed.pop("index_sha256")
    assert recorded == module.stable_hash(unhashed)
