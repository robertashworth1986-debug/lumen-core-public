from __future__ import annotations

import csv
import hashlib
import importlib.util
import json
import sqlite3
import zipfile
from pathlib import Path
from types import SimpleNamespace

import pytest

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "code" / "ops" / "BUILD_LUMENCORE_ESTATE_MASTER_INDEX.py"


def load_module():
    spec = importlib.util.spec_from_file_location(
        "lumencore_estate_master_index", SCRIPT
    )
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def sha256_bytes(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def write_csv(path: Path, fieldnames: list[str], rows: list[dict[str, object]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def build_fixture(tmp_path: Path):
    module = load_module()
    module.shutil.disk_usage = lambda _: SimpleNamespace(
        total=100 * 1024**3,
        used=40 * 1024**3,
        free=60 * 1024**3,
    )
    fixture_root = tmp_path / "manifests"
    fixture_root.mkdir(parents=True, exist_ok=True)
    scientific = fixture_root / "scientific.csv"
    fast = fixture_root / "fast.csv"
    canonical = fixture_root / "canonical.csv"
    intake = fixture_root / "curated.json"
    registry = fixture_root / "registry.json"
    explicit_pdf = fixture_root / "private NASA submission.pdf"
    explicit_pdf.write_bytes(b"%PDF-1.4\nexplicit fixture\n%%EOF\n")

    hash_a = "a" * 64
    hash_b = "b" * 64
    hash_c = "c" * 64
    manifest_fields = ["root", "path", "extension", "size", "last_write_utc", "sha256"]
    write_csv(
        fast,
        manifest_fields,
        [
            {
                "root": r"C:\PrivateLab",
                "path": r"C:\PrivateLab\routing\hybrid_router.py",
                "extension": ".py",
                "size": 10,
                "last_write_utc": "2026-06-17T10:00:00Z",
                "sha256": hash_a,
            },
            {
                "root": r"C:\PrivateLab",
                "path": r"C:\PrivateLab\hardware\fixture.stl",
                "extension": ".stl",
                "size": 20,
                "last_write_utc": "2026-06-17T10:00:00Z",
                "sha256": hash_b,
            },
            {
                "root": r"C:\PrivateLab",
                "path": r"C:\PrivateLab\field_work\photos.zip",
                "extension": ".zip",
                "size": 30,
                "last_write_utc": "2026-06-17T10:00:00Z",
                "sha256": "d" * 64,
            },
        ],
    )
    write_csv(
        scientific,
        manifest_fields,
        [
            {
                "root": r"C:\PrivateLab",
                "path": r"c:\privatelab\routing\HYBRID_ROUTER.py",
                "extension": ".py",
                "size": 10,
                "last_write_utc": "2026-06-17T11:00:00Z",
                "sha256": hash_a,
            },
            {
                "root": r"C:\PrivateLab",
                "path": r"C:\PrivateLab\hardware\fixture.stl",
                "extension": ".stl",
                "size": 21,
                "last_write_utc": "2026-06-17T11:00:00Z",
                "sha256": hash_c,
            },
            {
                "root": r"C:\PrivateLab",
                "path": r"C:\PrivateLab\field_work\site_visit_report.pdf",
                "extension": ".pdf",
                "size": 40,
                "last_write_utc": "2026-06-17T11:00:00Z",
                "sha256": "e" * 64,
            },
            {
                "root": str(ROOT),
                "path": str(ROOT / "metadata_overlap.json"),
                "extension": ".json",
                "size": 41,
                "last_write_utc": "2026-06-17T11:00:00Z",
                "sha256": "3" * 64,
            },
        ],
    )
    canonical_fields = [
        "relative_path",
        "extension",
        "size_bytes",
        "modified_utc",
        "asset_class",
        "custody_tier",
        "concept_tags",
        "hash_mode",
        "content_sha256",
        "metadata_sha256",
    ]
    write_csv(
        canonical,
        canonical_fields,
        [
            {
                "relative_path": "code/funding/proof_grant.py",
                "extension": ".py",
                "size_bytes": 50,
                "modified_utc": "2026-07-13T20:00:00Z",
                "asset_class": "source_code_or_automation",
                "custody_tier": "source_code_audit_ready",
                "concept_tags": "agency_protocol;proof_stack",
                "hash_mode": "content_sha256",
                "content_sha256": "f" * 64,
                "metadata_sha256": "",
            },
            {
                "relative_path": "metadata_overlap.json",
                "extension": ".json",
                "size_bytes": 41,
                "modified_utc": "2026-07-13T20:00:00Z",
                "asset_class": "structured_state_or_config",
                "custody_tier": "estate_inventory_hash_backed",
                "concept_tags": "",
                "hash_mode": "metadata_hash_only_large_file",
                "content_sha256": "",
                "metadata_sha256": "4" * 64,
            },
        ],
    )
    intake_payload = {
        "schema": "fixture_intake_v1",
        "generated_utc": "2026-06-22T00:00:00Z",
        "roots": [
            {
                "root": r"C:\PrivateLab",
                "exists": True,
                "seen": 20,
                "kept": 2,
                "skipped": 0,
                "truncated": True,
            }
        ],
        "records": [
            {
                "absolute_path": r"C:\PrivateLab\health\computer_health_watchdog.json",
                "root": r"C:\PrivateLab",
                "extension": ".json",
                "bytes": 60,
                "last_write_utc": "2026-06-22T00:00:00Z",
                "sha256": "1" * 64,
                "sha256_mode": "computed",
                "categories": ["frozen_provenance"],
                "grant_lanes": ["evidence_provenance"],
                "recommended_use": "review_later",
            },
            {
                "absolute_path": r"C:\PrivateLab\field_work\site_visit_photo.jpg",
                "root": r"C:\PrivateLab",
                "extension": ".jpg",
                "bytes": 70,
                "last_write_utc": "2026-06-22T00:00:00Z",
                "sha256": "2" * 64,
                "sha256_mode": "computed",
                "categories": ["geometry_hardware"],
                "grant_lanes": [],
                "recommended_use": "review_later",
            },
        ],
    }
    intake.write_text(json.dumps(intake_payload), encoding="utf-8")
    registry.write_text(
        json.dumps(
            [
                {
                    "root": r"C:\PrivateLab",
                    "role": r"C:\PrivateRole\secret",
                    "exists": True,
                    "file_count": 99,
                    "indicators": r"C:\Users\PrivatePerson\secret patent filename.pdf",
                },
                {
                    "root": str(ROOT),
                    "role": "ACTIVE_ENGINE",
                    "exists": True,
                    "file_count": 101014,
                    "indicators": r"C:\Users\PrivatePerson\credential.txt",
                },
                {
                    "root": r"C:\PrivateLab\hardware",
                    "role": "ACTIVE_LAB",
                    "exists": True,
                    "file_count": 5,
                    "indicators": r"C:\PrivateLab\hardware\private fixture.stl",
                },
            ]
        ),
        encoding="utf-8",
    )

    private_dir = tmp_path / "private"
    public_receipt = tmp_path / "public" / "receipt.json"
    dashboard_receipt = tmp_path / "dashboard" / "receipt.json"
    config = module.PrivateUniverseConfig(
        scientific_manifest=scientific,
        fast_manifest=fast,
        canonical_inventory=canonical,
        curated_intake=intake,
        root_registry=registry,
        private_output_dir=private_dir,
        public_receipt=public_receipt,
        dashboard_receipt=dashboard_receipt,
        explicit_files=[explicit_pdf, explicit_pdf],
        minimum_output_free_percent=0,
    )
    receipt = module.build_private_universe(config)
    return (
        module,
        config,
        receipt,
        {
            "scientific": scientific,
            "fast": fast,
            "canonical": canonical,
            "intake": intake,
            "registry": registry,
            "explicit_pdf": explicit_pdf,
        },
    )


def test_private_universe_deduplicates_and_preserves_every_observation(tmp_path):
    module, config, receipt, _ = build_fixture(tmp_path)

    assert receipt["summary"]["source_manifest_count"] == 5
    assert receipt["summary"]["explicit_file_count"] == 1
    assert receipt["summary"]["explicit_file_sha256_coverage_count"] == 1
    assert receipt["summary"]["source_observation_count"] == 12
    assert receipt["summary"]["unique_asset_count"] == 9
    assert receipt["summary"]["duplicate_observation_count"] == 3
    assert receipt["summary"]["historical_content_sha256_conflict_asset_count"] == 1

    connection = sqlite3.connect(config.database_path)
    try:
        assert (
            connection.execute("SELECT COUNT(*) FROM observations").fetchone()[0] == 12
        )
        selected = connection.execute(
            "SELECT selected_source_kind FROM assets WHERE normalized_path_key = ?",
            (r"c:\privatelab\hardware\fixture.stl",),
        ).fetchone()
        assert selected == ("scientific_index",)
        provenance = connection.execute(
            """
            SELECT source_kind, reported_sha256, hash_verification_status
            FROM observations
            WHERE asset_id = (
                SELECT asset_id FROM assets WHERE normalized_path_key = ?
            )
            ORDER BY source_kind
            """,
            (r"c:\privatelab\hardware\fixture.stl",),
        ).fetchall()
        assert provenance == [
            ("fast_index", "b" * 64, "historical_unverified"),
            ("scientific_index", "c" * 64, "historical_unverified"),
        ]
        domains = connection.execute(
            """
            SELECT source_kind, reported_hash_domain
            FROM observations
            WHERE asset_id = (
                SELECT asset_id FROM assets WHERE normalized_path_key = ?
            )
            ORDER BY source_kind
            """,
            (module.normalized_path_key(ROOT / "metadata_overlap.json"),),
        ).fetchall()
        assert domains == [
            ("canonical_estate_inventory", "metadata_sha256"),
            ("scientific_index", "content_sha256"),
        ]
        effective_root = connection.execute(
            """
            SELECT root_alias, relative_path FROM assets
            WHERE normalized_path_key = ?
            """,
            (r"c:\privatelab\hardware\fixture.stl",),
        ).fetchone()
        assert effective_root == (
            module.stable_root_alias(r"C:\PrivateLab\hardware"),
            "fixture.stl",
        )
        reported_roots = connection.execute(
            """
            SELECT DISTINCT reported_root_alias FROM observations
            WHERE asset_id = (
                SELECT asset_id FROM assets WHERE normalized_path_key = ?
            )
            """,
            (r"c:\privatelab\hardware\fixture.stl",),
        ).fetchall()
        assert reported_roots == [(module.stable_root_alias(r"C:\PrivateLab"),)]
        explicit = connection.execute("""
            SELECT source_kind, asset_bytes_read_for_sha256,
                   reported_historical_hashes_reverified
            FROM sources WHERE source_kind = 'explicit_user_supplied_current_file'
            """).fetchone()
        assert explicit == ("explicit_user_supplied_current_file", 1, 0)
    finally:
        connection.close()


def test_public_receipts_are_path_free_and_private_database_keeps_paths(tmp_path):
    module, config, receipt, _ = build_fixture(tmp_path)

    module.assert_public_private_universe_receipt_safe(receipt)
    dumped = json.dumps(receipt).lower()
    assert "c:\\" not in dumped
    assert "privateperson" not in dumped
    assert "hybrid_router.py" not in dumped
    assert "private nasa submission.pdf" not in dumped
    assert receipt["methodology"]["federation_mode"] == "zero_copy_manifest_federation"
    assert receipt["methodology"]["freshness"] == "mixed_freshness"
    assert receipt["methodology"]["full_live_reconciliation"] is False
    assert receipt["methodology"]["manifest_referenced_file_bytes_read"] is False
    assert receipt["methodology"]["explicit_file_bytes_read_for_sha256"] is True
    assert receipt["methodology"]["source_manifest_files_read_and_parsed"] is True
    assert (
        receipt["methodology"][
            "referenced_historical_asset_contents_parsed_or_extracted"
        ]
        is False
    )
    assert receipt["methodology"]["explicit_file_contents_parsed_or_extracted"] is False
    assert receipt["methodology"]["historical_hashes_reverified"] is False
    assert receipt["methodology"]["explicit_user_supplied_files_hashed"] is True
    preflight = receipt["methodology"]["output_volume_preflight"]
    assert preflight["gate_passed"] is True
    assert preflight["minimum_free_percent"] == 0.0
    assert preflight["nearest_existing_ancestor_checked_before_output_creation"] is True
    assert preflight["absolute_reserve_bytes"] > 0
    assert preflight["estimated_database_bytes"] > 0
    identity = receipt["transformation_identity"]
    assert len(identity["builder_sha256"]) == 64
    assert identity["manifest_post_import_rehash_passed"] is True
    assert identity["sqlite_quick_check"] == "ok"
    assert identity["staged_database_quick_check_passed"] is True
    assert identity["builder_git_state"]
    assert isinstance(identity["builder_git_dirty"], bool)
    assert (
        identity["builder_git_commit"] == "unavailable"
        or len(identity["builder_git_commit"]) == 40
    )
    assert identity["generation_id"] == receipt["generation_id"]
    assert receipt["private_index_custody"]["generation_id"] == receipt["generation_id"]
    assert receipt["methodology"]["sqlite_temp_store"] == "memory_not_system_volume"
    assert json.loads(config.public_receipt.read_text(encoding="utf-8")) == receipt
    assert json.loads(config.dashboard_receipt.read_text(encoding="utf-8")) == receipt

    connection = sqlite3.connect(config.database_path)
    try:
        private_paths = [
            row[0].lower()
            for row in connection.execute("SELECT absolute_path FROM assets")
        ]
        assert any("hybrid_router.py" in path for path in private_paths)
        assert any("private nasa submission.pdf" in path for path in private_paths)
    finally:
        connection.close()


def test_manifest_hashes_lanes_root_quality_and_archive_non_extraction(tmp_path):
    module, config, receipt, paths = build_fixture(tmp_path)

    source_summaries = {row["source_kind"]: row for row in receipt["source_summary"]}
    for kind, fixture_key in {
        "scientific_index": "scientific",
        "fast_index": "fast",
        "canonical_estate_inventory": "canonical",
        "curated_local_icloud_intake": "intake",
        "root_registry": "registry",
    }.items():
        expected = sha256_bytes(paths[fixture_key].read_bytes())
        assert source_summaries[kind]["source_sha256"] == expected
        assert source_summaries[kind]["historical_hashes_reverified"] is False

    required_lanes = {
        "hybrid_routing",
        "hardware_geometry",
        "additive_manufacturing_3d",
        "field_work_evidence",
        "computer_health_measurement",
        "media_documentation",
        "proof",
        "funding",
        "software",
    }
    assert required_lanes <= set(receipt["candidate_lane_counts"])
    assert receipt["summary"]["archive_reference_asset_count"] == 1
    assert receipt["methodology"]["archives_unpacked"] is False
    assert (
        "partial_curated_coverage_truncated"
        in receipt["root_summary"]["coverage_quality_counts"]
    )
    assert (
        receipt["root_summary"]["registry_role_counts"]["OTHER_PRIVATE_ROLE_REDACTED"]
        == 1
    )

    extraction_target = tmp_path / "must_not_be_extracted.txt"
    referenced_archive = tmp_path / "referenced.zip"
    with zipfile.ZipFile(referenced_archive, "w") as archive:
        archive.writestr(extraction_target.name, "not authorized to extract")
    before = referenced_archive.read_bytes()
    assert not extraction_target.exists()
    assert referenced_archive.read_bytes() == before
    assert not extraction_target.exists()

    private_receipt = json.loads(
        config.private_receipt_path.read_text(encoding="utf-8")
    )
    assert private_receipt["custody"]["archives_unpacked"] is False
    assert private_receipt["database_sha256"] == sha256_bytes(
        config.database_path.read_bytes()
    )
    assert (
        receipt["private_index_custody"]["database_sha256"]
        == private_receipt["database_sha256"]
    )
    assert (
        receipt["private_index_custody"]["database_bytes"]
        == config.database_path.stat().st_size
    )
    receipt_without_self_hash = dict(receipt)
    receipt_without_self_hash.pop("receipt_sha256")
    assert receipt["receipt_sha256"] == module.stable_sha256(receipt_without_self_hash)


def test_explicit_file_rejects_directories_without_traversal(tmp_path):
    module = load_module()
    directory = tmp_path / "not_a_file"
    directory.mkdir()

    try:
        module.require_regular_manifest(directory)
    except ValueError as exc:
        assert "regular, non-symlink file" in str(exc)
    else:
        raise AssertionError("Directory input should be rejected")


def test_private_universe_cli_accepts_repeated_explicit_files():
    module = load_module()
    args = module.parse_args(
        [
            "--private-universe",
            "--explicit-file",
            r"C:\Authorized\one.pdf",
            "--explicit-file",
            r"C:\Authorized\two.stl",
        ]
    )

    assert args.private_universe is True
    assert args.explicit_file == [
        Path(r"C:\Authorized\one.pdf"),
        Path(r"C:\Authorized\two.stl"),
    ]
    assert args.minimum_output_free_percent == 10.0


def test_output_volume_gate_runs_before_directory_creation(tmp_path, monkeypatch):
    module = load_module()
    output_directory = tmp_path / "not_created" / "private"

    class LowSpace:
        total = 1000
        used = 901
        free = 99

    monkeypatch.setattr(module.shutil, "disk_usage", lambda _: LowSpace())
    with pytest.raises(
        RuntimeError, match="output-volume preflight failed"
    ) as exc_info:
        module.check_private_output_volume(output_directory, 10.0)

    assert not output_directory.exists()
    assert str(output_directory).lower() not in str(exc_info.value).lower()


def test_second_run_preserves_prior_database_and_private_receipt(tmp_path):
    module, config, first_receipt, _ = build_fixture(tmp_path)
    first_database_sha256 = first_receipt["private_index_custody"]["database_sha256"]
    first_private_receipt_bytes = config.private_receipt_path.read_bytes()
    first_private_receipt_sha256 = sha256_bytes(first_private_receipt_bytes)

    second_receipt = module.build_private_universe(config)
    custody = second_receipt["private_index_custody"]
    assert custody["prior_latest_database_present"] is True
    assert custody["prior_latest_database_preserved"] is True
    assert custody["prior_latest_database_sha256"] == first_database_sha256
    assert custody["prior_latest_private_receipt_preserved"] is True
    assert (
        custody["prior_latest_private_receipt_sha256"] == first_private_receipt_sha256
    )
    assert custody["prior_latest_private_receipt_bytes"] == len(
        first_private_receipt_bytes
    )
    assert custody["database_sha256"] == sha256_bytes(config.database_path.read_bytes())
    assert second_receipt["receipt_sha256"] != first_receipt["receipt_sha256"]

    history = config.private_output_dir / module.PRIVATE_UNIVERSE_HISTORY_DIR_NAME
    assert len(list(history.glob("*.sqlite3"))) == 1
    assert len(list(history.glob("*.json"))) == 1


def test_failed_staged_sqlite_quick_check_blocks_all_four_outputs(
    tmp_path,
    monkeypatch,
):
    module, config, _, _ = build_fixture(tmp_path)
    final_artifacts = [
        config.database_path,
        config.private_receipt_path,
        config.public_receipt,
        config.dashboard_receipt,
    ]
    before = {path: path.read_bytes() for path in final_artifacts}

    def fail_quick_check(_):
        raise RuntimeError("injected quick_check failure")

    monkeypatch.setattr(module, "run_staged_sqlite_quick_check", fail_quick_check)
    with pytest.raises(RuntimeError, match="injected quick_check failure"):
        module.build_private_universe(config)

    assert {path: path.read_bytes() for path in final_artifacts} == before
    assert not (config.private_output_dir / module.PRIVATE_UNIVERSE_LOCK_NAME).exists()


def test_source_errors_do_not_disclose_private_paths(tmp_path):
    module = load_module()
    missing = tmp_path / "private user" / "secret source.csv"

    with pytest.raises(RuntimeError) as exc_info:
        module.read_source_file_identity(missing, "scientific_index")

    message = str(exc_info.value).lower()
    assert str(missing).lower() not in message
    assert "secret source.csv" not in message


@pytest.mark.parametrize(
    "attribute_name",
    [
        "FILE_ATTRIBUTE_REPARSE_POINT",
        "FILE_ATTRIBUTE_OFFLINE",
        "FILE_ATTRIBUTE_RECALL_ON_OPEN",
        "FILE_ATTRIBUTE_RECALL_ON_DATA_ACCESS",
    ],
)
def test_unsafe_windows_file_attributes_are_rejected(attribute_name):
    module = load_module()
    fallback = {
        "FILE_ATTRIBUTE_REPARSE_POINT": 0x00000400,
        "FILE_ATTRIBUTE_OFFLINE": 0x00001000,
        "FILE_ATTRIBUTE_RECALL_ON_OPEN": 0x00040000,
        "FILE_ATTRIBUTE_RECALL_ON_DATA_ACCESS": 0x00400000,
    }[attribute_name]
    attribute = getattr(module.stat, attribute_name, fallback)

    assert module.has_unsafe_windows_input_attributes(
        SimpleNamespace(st_file_attributes=attribute)
    )


def test_explicit_file_hash_fails_if_size_or_mtime_changes(tmp_path, monkeypatch):
    module = load_module()
    explicit_file = tmp_path / "explicit.pdf"
    explicit_file.write_bytes(b"fixture")
    before = SimpleNamespace(st_size=7, st_mtime_ns=1, st_mtime=1.0)
    after = SimpleNamespace(st_size=8, st_mtime_ns=2, st_mtime=2.0)
    states = iter([before, after])
    monkeypatch.setattr(module, "require_regular_manifest", lambda _: next(states))

    with pytest.raises(RuntimeError, match="ValueError") as exc_info:
        module.read_source_file_identity(
            explicit_file,
            "explicit_user_supplied_current_file",
            require_stable_during_hash=True,
        )

    assert str(explicit_file).lower() not in str(exc_info.value).lower()


def test_manifest_post_import_rehash_detects_changed_source(tmp_path):
    module = load_module()
    manifest = tmp_path / "manifest.csv"
    manifest.write_text("header\nvalue\n", encoding="utf-8")
    source = {
        "source_path": str(manifest),
        "source_sha256": "0" * 64,
    }

    with pytest.raises(RuntimeError, match="changed during import") as exc_info:
        module.verify_registered_manifest_inputs_unchanged({"scientific_index": source})

    assert str(manifest).lower() not in str(exc_info.value).lower()


@pytest.mark.parametrize(
    "database_name",
    [
        "..",
        "../escape.db",
        r"..\escape.db",
        r"C:\escape.db",
        "/escape.db",
        "nested/index.db",
        r"nested\index.db",
        "unsafe..db",
    ],
)
def test_database_name_cannot_escape_private_output(tmp_path, database_name):
    module = load_module()
    config = module.PrivateUniverseConfig(
        private_output_dir=tmp_path / "private",
        database_name=database_name,
    )

    with pytest.raises(ValueError, match="traversal-free basename"):
        module.validate_private_output_layout(config)


def test_cross_process_writer_lock_rejects_contention(tmp_path):
    module = load_module()
    lock_path = tmp_path / module.PRIVATE_UNIVERSE_LOCK_NAME

    with module.PrivateUniverseWriterLock(lock_path):
        with pytest.raises(RuntimeError, match="lock is already held"):
            with module.PrivateUniverseWriterLock(lock_path):
                pass

    assert not lock_path.exists()


def test_public_privacy_gate_checks_dictionary_keys():
    module = load_module()
    payload = {r"C:\Private\secret-filename.txt": {"safe": True}}

    with pytest.raises(ValueError, match="privacy gate"):
        module.assert_public_private_universe_receipt_safe(payload)


def test_publish_failure_restores_entire_prior_publish_set(tmp_path, monkeypatch):
    module = load_module()
    final_dir = tmp_path / "final"
    stage_dir = tmp_path / "stage"
    history_dir = tmp_path / "history"
    final_dir.mkdir()
    stage_dir.mkdir()
    history_dir.mkdir()
    keys = ("database", "private_receipt", "public_receipt", "dashboard_receipt")
    final_artifacts = {key: final_dir / f"{key}.bin" for key in keys}
    staged_artifacts = {key: stage_dir / f"{key}.bin" for key in keys}
    for key in keys:
        final_artifacts[key].write_bytes(f"old-{key}".encode())
        staged_artifacts[key].write_bytes(f"new-{key}".encode())
    prior_custody = {
        "prior_database_archive_path": str(history_dir / "prior.sqlite3"),
        "prior_private_receipt_archive_path": str(history_dir / "prior.json"),
    }
    real_replace = module.atomic_replace
    failed = False

    def fail_dashboard_once(source, destination):
        nonlocal failed
        if destination == final_artifacts["dashboard_receipt"] and not failed:
            failed = True
            raise OSError("injected publish failure")
        real_replace(source, destination)

    monkeypatch.setattr(module, "atomic_replace", fail_dashboard_once)
    with pytest.raises(RuntimeError, match="Prior publish set was restored"):
        module.publish_staged_private_universe_artifacts(
            staged_artifacts,
            final_artifacts,
            prior_custody,
        )

    for key in keys:
        assert final_artifacts[key].read_bytes() == f"old-{key}".encode()
    assert Path(prior_custody["prior_database_archive_path"]).exists()
    assert Path(prior_custody["prior_private_receipt_archive_path"]).exists()


def test_extended_unc_paths_normalize_without_losing_unc_identity():
    module = load_module()

    assert (
        module.normalize_windows_path(r"\\?\UNC\server\share\folder\file.txt")
        == r"\\server\share\folder\file.txt"
    )


def test_absolute_reserve_gate_is_independent_of_percentage(tmp_path, monkeypatch):
    module = load_module()

    class Space:
        total = 20_000
        used = 10_000
        free = 10_000

    monkeypatch.setattr(module.shutil, "disk_usage", lambda _: Space())
    with pytest.raises(RuntimeError, match="reserve preflight failed"):
        module.check_private_output_volume(
            tmp_path,
            10.0,
            {
                "manifest_input_bytes": 1,
                "explicit_input_bytes": 0,
                "estimated_database_bytes": 9_000,
                "absolute_reserve_bytes": 2_000,
                "required_free_bytes": 11_000,
            },
        )
