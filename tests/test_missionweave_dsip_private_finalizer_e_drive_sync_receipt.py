from __future__ import annotations

import hashlib
import importlib.util
import json
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = (
    ROOT
    / "code"
    / "ops"
    / "BUILD_MISSIONWEAVE_DSIP_PRIVATE_FINALIZER_E_DRIVE_SYNC_RECEIPT.py"
)


def load_module():
    spec = importlib.util.spec_from_file_location(
        "missionweave_dsip_private_finalizer_e_drive_sync_receipt", SCRIPT
    )
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def configure_workspace(tmp_path: Path, module, sources: list[str]) -> tuple[Path, Path]:
    root = tmp_path / "repo"
    receipt = (
        root
        / "grant_submissions"
        / "funding_sprint_20260709"
        / "MISSIONWEAVE_DSIP_PRIVATE_FINALIZER_E_DRIVE_SYNC_RECEIPT_2026-07-17.json"
    )
    destination_root = tmp_path / "vault" / "missionweave"
    receipt.parent.mkdir(parents=True)
    destination_root.parent.mkdir(parents=True)

    for source_name in sources:
        source = root / source_name
        source.parent.mkdir(parents=True, exist_ok=True)
        source.write_text(f"bounded:{source_name}\n", encoding="utf-8")

    receipt.write_text(
        json.dumps(
            {
                "schema": "lumencore.bounded_mirror_receipt.v1",
                "generated_utc": "2026-07-17T00:00:00Z",
                "destination_root": destination_root.as_posix(),
                "artifact_count": len(sources),
                "all_sha256_matched_after_copy": True,
                "browser_navigation_performed": False,
                "private_input_mirrored": False,
                "private_assigned_number_artifacts_mirrored": False,
                "private_values_or_credentials_mirrored": False,
                "public_neutral_package_only": True,
                "artifacts": [{"source": source} for source in sources],
                "claim_boundary": "This receipt does not prove submission or award.",
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )

    module.ROOT = root
    module.RECEIPT = receipt
    module.DESTINATION_ROOT = destination_root
    module.RECEIPT_COPY = destination_root / "receipts" / receipt.name
    return receipt, destination_root


def test_builder_preserves_paths_and_verifies_hashes(tmp_path: Path) -> None:
    module = load_module()
    sources = [
        "code/ops/BUILD_MISSIONWEAVE_DSIP_ACTION_GATE.py",
        "grant_submissions/DLA26BZ03_NV011_MissionWeave/MISSIONWEAVE_DSIP_ACTION_GATE_2026-07-17.json",
    ]
    receipt, destination_root = configure_workspace(tmp_path, module, sources)

    payload = module.build_receipt(generated_utc="2026-07-18T00:00:00Z")
    module.write_and_mirror_receipt(payload)

    assert payload["artifact_count"] == len(payload["artifacts"]) == 2
    assert payload["generated_utc"] == "2026-07-18T00:00:00Z"
    assert payload["all_sha256_matched_after_copy"] is True
    for artifact in payload["artifacts"]:
        source = module.ROOT / artifact["source"]
        destination = destination_root / artifact["source"]
        assert destination.is_file()
        assert artifact["copy_sha256_matched"] is True
        assert artifact["sha256"] == hashlib.sha256(source.read_bytes()).hexdigest().upper()
        assert hashlib.sha256(destination.read_bytes()).hexdigest().upper() == artifact["sha256"]

    assert module.RECEIPT_COPY.read_bytes() == receipt.read_bytes()


def test_builder_rejects_private_package_artifacts(tmp_path: Path) -> None:
    module = load_module()
    sources = [
        "grant_submissions/DLA26BZ03_NV011_MissionWeave/private/"
        "MISSIONWEAVE_DSIP_ACTION.private.json"
    ]
    configure_workspace(tmp_path, module, sources)

    with pytest.raises(ValueError, match="Private MissionWeave artifact"):
        module.build_receipt(generated_utc="2026-07-18T00:00:00Z")
