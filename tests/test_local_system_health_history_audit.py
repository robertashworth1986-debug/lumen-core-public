from __future__ import annotations

import hashlib
import importlib.util
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "code" / "ops" / "BUILD_LOCAL_SYSTEM_HEALTH_HISTORY_AUDIT.py"


def load_module():
    spec = importlib.util.spec_from_file_location("local_system_health_history_audit", SCRIPT)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def source_tree(tmp_path: Path) -> tuple[Path, Path, Path, Path, Path]:
    root = tmp_path / "private-source"
    runs = root / "runs"
    proofs = root / "proof"
    tools = root / "tools"
    runs.mkdir(parents=True)
    proofs.mkdir()
    tools.mkdir()
    ledger = root / "CHAIN_OF_CUSTODY_256.txt"
    collector = tools / "RUN_HYBRID.ps1"
    collector.write_text("# fixture: one-second point observation\n", encoding="utf-8")
    return root, runs, proofs, ledger, collector


def snapshot_payload(
    observed_at: datetime,
    *,
    cpu_pct: float = 20.0,
    mem_free_mb: float = 8_000.0,
    mem_total_mb: float = 32_000.0,
    system_free_gb: float = 500.0,
) -> dict:
    return {
        "utc": observed_at.astimezone(timezone.utc).strftime("%Y%m%dT%H%M%SZ"),
        "cpu_pct": cpu_pct,
        "mem_free_mb": mem_free_mb,
        "mem_total_mb": mem_total_mb,
        "uptime_s": 100,
        "disks": [
            {"drive": "C:", "freeGB": system_free_gb, "sizeGB": 1_000.0},
            {"drive": "E:", "freeGB": 300.0, "sizeGB": 500.0},
        ],
    }


def write_snapshot(
    runs: Path,
    observed_at: datetime,
    *,
    payload: dict | None = None,
    suffix: str = "",
    sidecar: bool = True,
    sidecar_hash: str | None = None,
) -> Path:
    token = observed_at.astimezone(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    path = runs / f"meso_sys_{token}{suffix}.json"
    path.write_text(json.dumps(payload or snapshot_payload(observed_at), indent=2), encoding="utf-8")
    if sidecar:
        (runs / f"{path.name}.sha256.txt").write_text(sidecar_hash or sha256(path), encoding="utf-8")
    return path


def write_proof(proofs: Path, observed_at: datetime, *, suffix: str = "", content: bytes = b"proof") -> Path:
    token = observed_at.astimezone(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    path = proofs / f"MESO_SYS_{token}{suffix}.zip"
    path.write_bytes(content)
    return path


def ledger_row(event_at: datetime, snapshot: Path, proof: Path, snapshot_hash: str, proof_hash: str) -> str:
    token = event_at.astimezone(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    return (
        f"{token}|MESO_SYS|PATH={snapshot} SHA={snapshot_hash} "
        f"ZIP={proof} ZIP_SHA={proof_hash}"
    )


def tree_hashes(root: Path) -> dict[str, str]:
    return {
        path.relative_to(root).as_posix(): sha256(path)
        for path in sorted(root.rglob("*"))
        if path.is_file()
    }


def test_audit_detects_integrity_defects_is_public_safe_and_does_not_mutate_sources(tmp_path: Path):
    module = load_module()
    root, runs, proofs, ledger, collector = source_tree(tmp_path)
    first_time = datetime(2026, 1, 1, tzinfo=timezone.utc)
    first = write_snapshot(runs, first_time)
    first_proof = write_proof(proofs, first_time + timedelta(seconds=2))
    second = write_snapshot(runs, first_time + timedelta(days=1), sidecar=False)
    broken = runs / "meso_sys_20260103T000000Z.json"
    broken.write_bytes(b"")
    orphan_proof = proofs / "MESO_SYS_20260103T000002Z.zip"
    orphan_proof.write_bytes(b"")
    ledger.write_text(
        ledger_row(first_time + timedelta(seconds=2), first, first_proof, sha256(first), sha256(first_proof))
        + "\n",
        encoding="utf-8",
    )

    before = tree_hashes(root)
    payload = module.build_payload(
        runs,
        proofs,
        ledger,
        collector,
        generated_at=datetime(2026, 7, 14, 12, tzinfo=timezone.utc),
    )
    after = tree_hashes(root)

    assert before == after
    assert payload["schema"] == "luma.local_system_health_history_audit.v1"
    assert payload["integrity"]["status"] == "defects_present"
    assert payload["integrity"]["counts"] == {
        "snapshot_files": 3,
        "valid_snapshots": 2,
        "snapshot_sidecars": 1,
        "proof_archives": 2,
        "ledger_meso_records": 1,
        "complete_ledger_receipts": 1,
        "defect_count": 8,
    }
    assert payload["integrity"]["defect_counts"] == {
        "proof_unledgered": 1,
        "proof_zero_bytes": 1,
        "snapshot_json_invalid": 1,
        "snapshot_sidecar_missing": 2,
        "snapshot_unledgered": 2,
        "snapshot_zero_bytes": 1,
    }
    assert payload["summary"]["valid_snapshot_count"] == 2
    assert payload["source_manifest"]["snapshot_set"]["record_count"] == 3
    assert payload["source_manifest"]["proof_set"]["record_count"] == 2
    assert len(payload["source_manifest"]["snapshot_set"]["manifest_sha256"]) == 64
    assert len(payload["source_manifest"]["custody_ledger"]["sha256"]) == 64
    assert len(payload["source_manifest"]["legacy_collector"]["sha256"]) == 64
    assert len(payload["source_manifest_sha256"]) == 64
    assert len(payload["audit_receipt_sha256"]) == 64

    encoded = json.dumps(payload, sort_keys=True).lower()
    assert str(root).lower() not in encoded
    assert "c:\\" not in encoded
    assert "novac" not in encoded
    assert '"drive"' not in encoded
    assert second.name not in encoded

    with pytest.raises(ValueError, match="inside the repository"):
        module.write_json(tmp_path / "outside-repository.json", payload)


def test_trailing_windows_are_exact_and_keep_point_samples_separate_from_degradation(tmp_path: Path):
    module = load_module()
    _, runs, proofs, ledger, collector = source_tree(tmp_path)
    first_time = datetime(2026, 1, 1, tzinfo=timezone.utc)
    ledger_rows = []
    for index in range(181):
        observed_at = first_time + timedelta(days=index)
        snapshot = write_snapshot(
            runs,
            observed_at,
            payload=snapshot_payload(
                observed_at,
                cpu_pct=20.0,
                mem_free_mb=8_000.0,
                mem_total_mb=32_000.0,
                system_free_gb=1_000.0 - index,
            ),
        )
        proof_time = observed_at + timedelta(seconds=2)
        proof = write_proof(proofs, proof_time, content=f"proof-{index}".encode("ascii"))
        ledger_rows.append(ledger_row(proof_time, snapshot, proof, sha256(snapshot), sha256(proof)))
    ledger.write_text("\n".join(ledger_rows) + "\n", encoding="utf-8")

    generated_at = datetime(2026, 7, 14, 12, tzinfo=timezone.utc)
    payload = module.build_payload(runs, proofs, ledger, collector, generated_at=generated_at)

    assert payload["integrity"]["status"] == "verified"
    assert payload["integrity"]["counts"]["complete_ledger_receipts"] == 181
    assert payload["summary"]["valid_snapshot_count"] == 181
    assert payload["summary"]["active_utc_date_count"] == 181
    assert payload["summary"]["expected_hour_bucket_count"] == 4_321
    assert payload["summary"]["observed_hour_bucket_count"] == 181

    expected = {
        "30": (31, 721, 850.0, -30.0),
        "90": (91, 2_161, 910.0, -90.0),
        "180": (181, 4_321, 1_000.0, -180.0),
    }
    for horizon, (snapshots, expected_hours, first_free, delta_free) in expected.items():
        row = payload["trailing_windows"][horizon]
        assert row["snapshot_count"] == snapshots
        assert row["active_utc_date_count"] == snapshots
        assert row["observed_hour_bucket_count"] == snapshots
        assert row["expected_hour_bucket_count"] == expected_hours
        assert row["cpu_point_samples"]["sample_seconds_each"] == 1
        assert row["cpu_point_samples"]["median_percent"] == 20.0
        assert row["cpu_point_samples"]["p95_percent"] == 20.0
        assert row["cpu_point_samples"]["sustained_utilization_claim_allowed"] is False
        assert row["memory_free"]["median_percent"] == 25.0
        assert row["memory_free"]["p10_percent"] == 25.0
        assert row["volume_free_space"]["system_volume"]["first_free_gb"] == first_free
        assert row["volume_free_space"]["system_volume"]["last_free_gb"] == 820.0
        assert row["volume_free_space"]["system_volume"]["delta_free_gb"] == delta_free
        assert row["hardware_degradation_claim_allowed"] is False

    assert payload["measurement_boundary"]["duration_coverage_calculable"] is False
    assert payload["claim_controls"]["hardware_degradation_claim_allowed"] is False
    assert "one-second sample" in payload["claim_boundary"]
    assert "SMART or NVMe wear" in payload["claim_boundary"]

    second_payload = module.build_payload(
        runs,
        proofs,
        ledger,
        collector,
        generated_at=generated_at + timedelta(hours=1),
    )
    assert second_payload["source_manifest_sha256"] == payload["source_manifest_sha256"]
    assert second_payload["audit_receipt_sha256"] != payload["audit_receipt_sha256"]


def test_hash_mismatches_and_duplicate_snapshot_times_are_explicit(tmp_path: Path):
    module = load_module()
    _, runs, proofs, ledger, collector = source_tree(tmp_path)
    observed_at = datetime(2026, 4, 1, tzinfo=timezone.utc)
    first = write_snapshot(runs, observed_at)
    second = write_snapshot(
        runs,
        observed_at + timedelta(seconds=1),
        payload=snapshot_payload(observed_at),
        sidecar_hash="f" * 64,
    )
    first_proof = write_proof(proofs, observed_at + timedelta(seconds=2), content=b"first")
    second_proof = write_proof(proofs, observed_at + timedelta(seconds=3), content=b"second")
    ledger.write_text(
        "\n".join(
            [
                ledger_row(
                    observed_at + timedelta(seconds=2),
                    first,
                    first_proof,
                    "0" * 64,
                    sha256(first_proof),
                ),
                ledger_row(
                    observed_at + timedelta(seconds=3),
                    second,
                    second_proof,
                    sha256(second),
                    "0" * 64,
                ),
            ]
        )
        + "\n",
        encoding="utf-8",
    )

    payload = module.build_payload(runs, proofs, ledger, collector)
    counts = payload["integrity"]["defect_counts"]

    assert counts["snapshot_sidecar_hash_mismatch"] == 1
    assert counts["ledger_snapshot_hash_mismatch"] == 1
    assert counts["ledger_proof_hash_mismatch"] == 1
    assert counts["snapshot_timestamp_duplicate"] == 1
    assert payload["integrity"]["counts"]["complete_ledger_receipts"] == 0
