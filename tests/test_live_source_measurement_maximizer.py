from __future__ import annotations

import importlib.util
import json
import os
import subprocess
import sys
import threading
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "code" / "ops" / "BUILD_LIVE_SOURCE_MEASUREMENT_MAXIMIZER.py"


def load_module():
    spec = importlib.util.spec_from_file_location("live_source_measurement_maximizer", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def write_policy(module, tmp_path: Path, provider_ids: list[str], **limit_overrides: int) -> Path:
    limits = {
        "max_concurrency": 2,
        "child_timeout_seconds": 5,
        "request_timeout_seconds": 2,
        "max_retries": 1,
        "retry_base_seconds": 0,
        "max_retry_delay_seconds": 1,
        "default_rate_limit_seconds": 60,
        "circuit_breaker_failures": 2,
        "max_rows": 5,
        "max_child_output_bytes": 4096,
    }
    limits.update(limit_overrides)
    payload = {
        "schema": module.POLICY_SCHEMA,
        "provider_allowlist": provider_ids,
        "limits": limits,
        "state_path": "run/live_source_orchestrator/test_state_v1.json",
        "execution_default": "dry_run",
        "network_default": False,
        "publish_outputs_default": False,
    }
    path = tmp_path / "policy.json"
    path.write_text(json.dumps(payload), encoding="utf-8")
    return path


def write_registry(module, tmp_path: Path, rows: list[dict] | None = None) -> Path:
    path = tmp_path / "registry.json"
    path.write_text(
        json.dumps({"schema": module.REGISTRY_ROWS_SCHEMA, "rows": rows or []}),
        encoding="utf-8",
    )
    return path


def configure_workspace(module, tmp_path: Path, monkeypatch) -> Path:
    root = tmp_path / "workspace"
    root.mkdir()
    replacements = {
        "ROOT": root,
        "OUT": root / "out",
        "OUT_OPS": root / "out" / "ops",
        "DATA_ROOT": root / "data" / "live_measured",
        "DOCS": root / "docs",
        "DASHBOARD_DATA": root / "dashboard" / "data",
        "RUN_ROOT": root / "run" / "live_source_orchestrator",
        "STAGING_ROOT": root / "run" / "live_source_orchestrator" / "staging",
        "PUBLICATION_ROOT": root / "out" / "ops" / "live_source_measurement_generations",
        "PUBLICATION_MANIFEST": root / "out" / "ops" / "live_source_measurement_publication_manifest.json",
        "PUBLICATION_LOCK": root / "run" / "live_source_orchestrator" / "publication.lock",
        "REGISTRY_JSON": root / "config" / "live_source_registry.json",
        "LIVE_SOURCES_JSON": root / "config" / "live_sources.json",
        "SOURCE_TRUTH_JSON": root / "out" / "source_truth_table.json",
        "OUT_JSON": root / "out" / "ops" / "live_source_measurement_maximizer_latest.json",
        "DASHBOARD_JSON": root / "dashboard" / "data" / "live_source_measurement_maximizer.json",
        "OUT_MD": root / "docs" / "LIVE_SOURCE_MEASUREMENT_MAXIMIZER.md",
    }
    for name, value in replacements.items():
        monkeypatch.setattr(module, name, value)
    return root


def minimal_subprocess_env() -> dict[str, str]:
    allowed = {"COMSPEC", "PATHEXT", "SYSTEMROOT", "TEMP", "TMP", "WINDIR"}
    return {name: value for name, value in os.environ.items() if name.upper() in allowed}


def staged_pass_result(module, provider_id: str, run_id: str) -> dict:
    paths = module.derive_child_job_paths(provider_id, run_id, 1, runtime_root=module.RUN_ROOT)
    paths["job_dir"].mkdir(parents=True)
    artifact_paths = {
        key: paths[key]
        for key in ("snapshot_json", "snapshot_latest_json", "snapshot_csv")
    }
    artifact = module.snapshot_provider(
        module.PROVIDER_BY_ID[provider_id],
        {
            "rows": [{"value": "fresh"}],
            "http_status": 200,
            "probe_ok": True,
            "probe_note": "test_publication",
        },
        run_id=run_id,
        attempt=1,
        artifact_paths=artifact_paths,
    )
    namespace = module.build_namespace_assignments([provider_id], run_id)[provider_id]
    child_receipt = module.seal_receipt(
        {
            "schema": module.RECEIPT_SCHEMA,
            "run_id": run_id,
            "provider_id": provider_id,
            "attempt": 1,
            "namespace": namespace,
            "network_allowed": True,
            "published_outputs": False,
            "credential_state": "NOT_REQUIRED",
            "qc_state": "PASS",
            "row_count": 1,
            "http_status": 200,
            "retry_after_seconds": None,
            "artifact": artifact,
        }
    )
    encoded_receipt = (json.dumps(child_receipt, sort_keys=True, separators=(",", ":")) + "\n").encode("utf-8")
    paths["receipt_json"].write_bytes(encoded_receipt)
    return {
        "provider_id": provider_id,
        "run_id": run_id,
        "namespace": namespace,
        "qc_state": "PASS",
        "attempts": 1,
        "child_receipt_sha256": child_receipt["receipt_sha256"],
        "child_receipt_bytes_sha256": module.sha256_bytes(encoded_receipt),
        "credential_state": "NOT_REQUIRED",
        "row_count": 1,
        "http_status": 200,
        "retry_after_seconds": None,
        "artifact": artifact,
    }


def command_value(command: list[str], flag: str) -> str:
    return command[command.index(flag) + 1]


def completed_child(
    module,
    command: list[str],
    *,
    env: dict[str, str],
    qc_state: str = "PASS",
    http_status: int | None = 200,
    retry_after_seconds: int | None = None,
    stderr: str = "",
) -> subprocess.CompletedProcess[bytes]:
    provider_id = command_value(command, "--child-provider")
    network_allowed = "--allow-network" in command
    authorization = json.loads(Path(env[module.CHILD_AUTH_FILE_ENV]).read_text(encoding="utf-8"))
    artifact = None
    if "--stage-artifact" in command:
        artifact = module.snapshot_provider(
            module.PROVIDER_BY_ID[provider_id],
            {
                "rows": [{"value": "fresh"}] if qc_state == "PASS" else [],
                "http_status": http_status,
                "probe_ok": qc_state == "PASS",
                "probe_note": "test_child",
            },
            run_id=command_value(command, "--run-id"),
            attempt=int(command_value(command, "--attempt")),
            artifact_paths={
                key: Path(authorization["paths"][key])
                for key in ("snapshot_json", "snapshot_latest_json", "snapshot_csv")
            },
        )
    receipt = module.seal_receipt(
        {
            "schema": module.RECEIPT_SCHEMA,
            "run_id": command_value(command, "--run-id"),
            "provider_id": provider_id,
            "attempt": int(command_value(command, "--attempt")),
            "namespace": {
                "cpu": command_value(command, "--cpu-namespace"),
                "gpu": command_value(command, "--gpu-namespace"),
            },
            "network_allowed": network_allowed,
            "published_outputs": False,
            "credential_state": "PRESENT" if network_allowed else "UNKNOWN",
            "qc_state": qc_state,
            "row_count": 1 if qc_state == "PASS" else 0,
            "http_status": http_status,
            "retry_after_seconds": retry_after_seconds,
            "artifact": artifact,
        }
    )
    encoded = (json.dumps(receipt, sort_keys=True, separators=(",", ":")) + "\n").encode("utf-8")
    Path(authorization["paths"]["receipt_json"]).write_bytes(encoded)
    return subprocess.CompletedProcess(command, 0, encoded, stderr.encode("utf-8"))


def test_sanitize_redacts_secret_values(monkeypatch) -> None:
    module = load_module()
    monkeypatch.setenv("FINNHUB_API_KEY", "super-secret-token")

    text = module.sanitize_text("url=https://x.test/?token=super-secret-token&email=a@b.com", ["FINNHUB_API_KEY"])

    assert "super-secret-token" not in text
    assert "a@b.com" not in text
    assert "[REDACTED]" in text


def test_merge_registry_preserves_existing_and_replaces_current_source() -> None:
    module = load_module()
    existing = {
        "rows": [
            {"source": "OLD_ONLY", "enabled": True, "measured": True, "rows": 1},
            {"source": "FRED", "enabled": True, "measured": False, "rows": 0},
        ]
    }
    merged = module.merge_registry(
        existing,
        [
            {
                "source": "FRED",
                "enabled": True,
                "measured": True,
                "rows": 4,
                "translated_value": {"hour": 1.0, "year": 8760.0},
            }
        ],
    )

    rows = {row["source"]: row for row in merged["rows"]}
    assert rows["OLD_ONLY"]["rows"] == 1
    assert rows["FRED"]["measured"] is True
    assert rows["FRED"]["rows"] == 4


def test_source_truth_contains_snapshot_hash_and_no_secret() -> None:
    module = load_module()
    registry = {
        "rows": [
            {
                "source": "FRED",
                "sector": "rates",
                "status": "MEASURED",
                "rows": 2,
                "enabled": True,
                "measured": True,
                "translated_value": {"hour": 12.0},
                "last_probe_utc": "2026-06-22T00:00:00+00:00",
                "probe_note": "ok",
                "snapshot_json": "data/live_measured/fred/fred_latest.json",
                "snapshot_sha256": "abc123",
            }
        ]
    }

    truth = module.source_truth_from_registry(registry)
    dumped = json.dumps(truth)

    assert truth["rows"][0]["source"] == "FRED"
    assert truth["rows"][0]["snapshot_sha256"] == "abc123"
    assert truth["rows"][0]["value_basis"] == "HEURISTIC_FROM_MEASURED_ROW_COUNT"
    assert "secret" not in dumped.lower()


def test_build_summary_counts_measured_sources_and_value_surface() -> None:
    module = load_module()
    rows = [
        {"source": "A", "sector": "rates", "enabled": True, "measured": True, "rows": 3, "translated_value": {"year": 10.0}},
        {"source": "B", "sector": "energy", "enabled": True, "measured": False, "rows": 0, "translated_value": {"year": 0.0}},
        {"source": "C", "sector": "market_data", "enabled": False, "measured": False, "rows": 0, "translated_value": {"year": 0.0}},
    ]

    summary = module.build_summary(rows)

    assert summary["enabled_sources"] == 2
    assert summary["measured_sources"] == 1
    assert summary["failed_or_thin_sources"] == 1
    assert summary["total_measured_rows"] == 3
    assert summary["estimated_annual_value_surface_usd"] == 10.0
    assert summary["estimated_annual_value_surface_basis"] == (
        "UNVALIDATED_HEURISTIC_NOT_REALIZED_OR_MEASURED_VALUE"
    )
    assert "realized savings" in summary["claim_boundary"]
    assert "not measured economic value" in summary["claim_boundary"]


def test_airnow_provider_is_registered_as_separate_air_quality_lane() -> None:
    module = load_module()
    providers = {row["source"]: row for row in module.PROVIDERS}

    assert "AIRNOW" in providers
    assert providers["AIRNOW"]["sector"] == "air_quality"
    assert providers["AIRNOW"]["env_names"] == ["AIRNOW_API_KEY"]
    assert providers["AIRNOW"]["collector"].__name__ == "rows_from_airnow"


def test_public_no_key_sources_expand_live_breadth_without_secret_dependency() -> None:
    module = load_module()
    providers = {row["source"]: row for row in module.PROVIDERS}

    expected = {
        "NWS_PUBLIC": "weather",
        "OPEN_METEO_PUBLIC": "weather",
        "TREASURY_FISCAL_PUBLIC": "rates",
        "SEC_PUBLIC": "market_data",
        "COINBASE_PUBLIC": "crypto_market",
        "WORLD_BANK_PUBLIC": "macro",
    }

    for source, sector in expected.items():
        assert source in providers
        assert providers[source]["sector"] == sector
        assert providers[source]["env_names"] == []


def test_nasa_collector_has_open_power_fallback(monkeypatch) -> None:
    module = load_module()
    monkeypatch.delenv("NASA_API_KEY", raising=False)

    assert module.rows_from_nasa.__name__ == "rows_from_nasa"


def test_fred_collector_requests_latest_observations(monkeypatch) -> None:
    module = load_module()
    monkeypatch.setenv("FRED_API_KEY", "a" * 32)
    requested_urls: list[str] = []

    def fake_request_json(url: str, *, timeout: int):
        requested_urls.append(url)
        return (
            200,
            {
                "observations": [
                    {"date": "2026-07-01", "value": "2.0"},
                    {"date": "2026-06-30", "value": "1.0"},
                ]
            },
            {},
        )

    monkeypatch.setattr(module, "request_json", fake_request_json)

    code, rows, note = module.rows_from_fred(max_rows=8, timeout=2)

    assert code == 200
    assert note == "fred_observations"
    assert len(rows) == 8
    assert len(requested_urls) == 4
    assert all("sort_order=desc" in url for url in requested_urls)
    assert {row["date"] for row in rows} == {"2026-07-01", "2026-06-30"}


def test_parent_defaults_to_dry_run_without_children_network_or_state(tmp_path) -> None:
    module = load_module()
    policy = write_policy(module, tmp_path, ["FRED"])
    registry = write_registry(module, tmp_path)
    state = tmp_path / "state.json"

    def forbidden_runner(*args, **kwargs):
        raise AssertionError("dry-run parent launched a child")

    receipt = module.orchestrate_providers(
        ["FRED"],
        policy_path=policy,
        registry_path=registry,
        state_path=state,
        runner=forbidden_runner,
    )
    repeated = module.orchestrate_providers(
        ["FRED"],
        policy_path=policy,
        registry_path=registry,
        state_path=state,
        runner=forbidden_runner,
    )

    assert receipt["status"] == "DRY_RUN"
    assert receipt["mode"] == "DRY_RUN"
    assert receipt["network_allowed"] is False
    assert receipt["summary"]["launched_child_processes"] == 0
    assert receipt["providers"][0]["qc_state"] == "DRY_RUN"
    assert not state.exists()
    assert module.verify_receipt_hash(receipt)
    assert repeated == receipt


def test_checked_in_policy_is_public_safe_fail_closed_and_covers_catalog() -> None:
    module = load_module()
    policy = module.load_orchestrator_policy()

    assert policy["execution_default"] == "dry_run"
    assert policy["network_default"] is False
    assert policy["publish_outputs_default"] is False
    assert set(policy["provider_allowlist"]) == set(module.PROVIDER_BY_ID)
    assert policy["resolved_state_path"].is_relative_to(module.ROOT / "run")


def test_parent_scopes_keys_to_child_env_and_keeps_them_out_of_receipts_and_state(tmp_path, monkeypatch) -> None:
    module = load_module()
    secret = "key-value-that-must-never-cross-parent-boundary"
    unrelated_secret = "unrelated-provider-secret"
    monkeypatch.setenv("FRED_API_KEY", secret)
    monkeypatch.setenv("SAM_API_KEY", unrelated_secret)
    policy = write_policy(module, tmp_path, ["FRED"], max_retries=0)
    registry = write_registry(module, tmp_path)
    state = tmp_path / "state.json"
    observed: list[tuple[list[str], dict]] = []

    def runner(command, **kwargs):
        observed.append((list(command), dict(kwargs)))
        return completed_child(module, command, env=kwargs["env"], stderr=f"provider said {secret}")

    receipt = module.orchestrate_providers(
        ["FRED"],
        policy_path=policy,
        registry_path=registry,
        state_path=state,
        execute=True,
        allow_network=True,
        run_id="secret-boundary-test",
        runner=runner,
        sleep_fn=lambda _: None,
        runtime_root=tmp_path / "runtime",
    )

    rendered = json.dumps(receipt)
    assert secret not in rendered
    assert unrelated_secret not in rendered
    assert secret not in state.read_text(encoding="utf-8")
    assert unrelated_secret not in state.read_text(encoding="utf-8")
    assert observed[0][0].count("--child-provider") == 1
    assert secret not in " ".join(observed[0][0])
    assert unrelated_secret not in " ".join(observed[0][0])
    assert observed[0][1]["env"]["FRED_API_KEY"] == secret
    assert "SAM_API_KEY" not in observed[0][1]["env"]
    assert receipt["providers"][0]["child_receipt_sha256"]


def test_staged_receipt_rejects_artifact_outside_provider_directory() -> None:
    module = load_module()
    provider_id = "FRED"
    run_id = "artifact-boundary-test"
    namespace = module.build_namespace_assignments([provider_id], run_id)[provider_id]
    receipt = module.seal_receipt(
        {
            "schema": module.RECEIPT_SCHEMA,
            "run_id": run_id,
            "provider_id": provider_id,
            "attempt": 1,
            "namespace": namespace,
            "network_allowed": True,
            "published_outputs": False,
            "credential_state": "PRESENT",
            "qc_state": "PASS",
            "row_count": 1,
            "http_status": 200,
            "retry_after_seconds": None,
            "artifact": {
                "snapshot_json": "docs/not-a-provider-snapshot.json",
                "snapshot_latest_json": "docs/not-a-provider-latest.json",
                "snapshot_csv": "docs/not-a-provider-snapshot.csv",
                "sha256": "0" * 64,
                "file_sha256": {
                    "snapshot_json": "0" * 64,
                    "snapshot_latest_json": "0" * 64,
                    "snapshot_csv": "0" * 64,
                },
            },
        }
    )

    with pytest.raises(module.ReceiptValidationError, match="provider data directory"):
        module.validate_child_receipt(
            receipt,
            allowlist=[provider_id],
            expected_provider_id=provider_id,
            expected_run_id=run_id,
            expected_attempt=1,
            expected_namespace=namespace,
            expected_network_allowed=True,
            expected_published_outputs=False,
            expected_staged_artifact=True,
            max_rows=5,
        )


def test_snapshot_artifact_receipt_verifies_files_and_detects_tampering(tmp_path, monkeypatch) -> None:
    module = load_module()
    monkeypatch.setattr(module, "ROOT", tmp_path)
    monkeypatch.setattr(module, "DATA_ROOT", tmp_path / "data" / "live_measured")
    provider = module.PROVIDER_BY_ID["FRED"]
    artifact_paths = {
        "snapshot_json": tmp_path / "data" / "live_measured" / "fred" / "snapshot.json",
        "snapshot_latest_json": tmp_path / "data" / "live_measured" / "fred" / "snapshot.latest.json",
        "snapshot_csv": tmp_path / "data" / "live_measured" / "fred" / "snapshot.csv",
    }
    artifact = module.snapshot_provider(
        provider,
        {
            "rows": [{"series_id": "TEST", "value": 1.0}],
            "http_status": 200,
            "probe_ok": True,
            "probe_note": "ok",
        },
        run_id="artifact-verification-test",
        attempt=1,
        artifact_paths=artifact_paths,
    )

    validated = module.verify_artifact_files(
        artifact,
        expected_provider_id="FRED",
        expected_paths=artifact_paths,
        expected_run_id="artifact-verification-test",
        expected_attempt=1,
        expected_row_count=1,
        expected_http_status=200,
        expected_qc_state="PASS",
    )
    assert validated["sha256"] == artifact["sha256"]
    assert set(validated["file_sha256"]) == {
        "snapshot_json",
        "snapshot_latest_json",
        "snapshot_csv",
    }

    snapshot_path = tmp_path / artifact["snapshot_json"]
    snapshot_path.write_text("{}", encoding="utf-8")
    with pytest.raises(module.ReceiptValidationError, match="hash-mismatched"):
        module.verify_artifact_files(
            artifact,
            expected_provider_id="FRED",
            expected_paths=artifact_paths,
        )


def test_invalid_provider_is_rejected_before_any_child_launch(tmp_path) -> None:
    module = load_module()
    policy = write_policy(module, tmp_path, ["FRED"])
    registry = write_registry(module, tmp_path)
    launched = False

    def runner(*args, **kwargs):
        nonlocal launched
        launched = True
        raise AssertionError("invalid provider reached the subprocess runner")

    with pytest.raises(ValueError, match="not allowlisted"):
        module.orchestrate_providers(
            ["NOT_ALLOWLISTED"],
            policy_path=policy,
            registry_path=registry,
            execute=True,
            runner=runner,
            runtime_root=tmp_path / "runtime",
        )

    assert launched is False


def test_child_timeout_is_bounded_retried_and_failed_closed(tmp_path) -> None:
    module = load_module()
    policy = write_policy(module, tmp_path, ["FRED"], max_retries=1)
    registry = write_registry(module, tmp_path)
    state = tmp_path / "state.json"
    calls = 0

    def runner(command, **kwargs):
        nonlocal calls
        calls += 1
        raise subprocess.TimeoutExpired(command, kwargs["timeout"])

    receipt = module.orchestrate_providers(
        ["FRED"],
        policy_path=policy,
        registry_path=registry,
        state_path=state,
        execute=True,
        allow_network=True,
        run_id="timeout-test",
        runner=runner,
        sleep_fn=lambda _: None,
        runtime_root=tmp_path / "runtime",
    )

    assert calls == 2
    assert receipt["status"] == "FAILED_CLOSED"
    assert receipt["providers"][0]["qc_state"] == "TIMEOUT"
    assert receipt["providers"][0]["attempts"] == 2
    assert receipt["summary"]["launched_child_processes"] == 2


def test_malformed_child_output_is_not_echoed_or_published(tmp_path, monkeypatch) -> None:
    module = load_module()
    secret = "secret-in-malformed-child-output"
    policy = write_policy(module, tmp_path, ["FRED"], max_retries=0)
    registry = write_registry(module, tmp_path)
    state = tmp_path / "state.json"

    def runner(command, **kwargs):
        return subprocess.CompletedProcess(command, 0, json.dumps({"unexpected_secret": secret}), secret)

    def forbidden_publish(*args, **kwargs):
        raise AssertionError("malformed child output reached publication")

    monkeypatch.setattr(module, "publish_measurement_outputs", forbidden_publish)
    receipt = module.orchestrate_providers(
        ["FRED"],
        policy_path=policy,
        registry_path=registry,
        state_path=state,
        execute=True,
        allow_network=True,
        publish_outputs=True,
        run_id="malformed-output-test",
        runner=runner,
        runtime_root=tmp_path / "runtime",
    )

    assert receipt["status"] == "FAILED_CLOSED"
    assert receipt["published_outputs"] is False
    assert receipt["providers"][0]["qc_state"] == "INVALID_RECEIPT"
    assert secret not in json.dumps(receipt)


def test_duplicate_cpu_or_gpu_namespaces_are_rejected() -> None:
    module = load_module()
    duplicate = "live-source/duplicate-test/fred/cpu"
    assignments = {
        "FRED": {"cpu": duplicate, "gpu": "live-source/duplicate-test/fred/gpu"},
        "EIA": {"cpu": duplicate, "gpu": "live-source/duplicate-test/eia/gpu"},
    }

    with pytest.raises(ValueError, match="disjoint"):
        module.validate_namespace_assignments(assignments)


def test_registry_schema_conflict_fails_before_children_launch(tmp_path) -> None:
    module = load_module()
    policy = write_policy(module, tmp_path, ["FRED"])
    registry = tmp_path / "registry.json"
    registry.write_text(
        json.dumps(
            {
                "rows": [{"source": "FRED", "enabled": True}],
                "sources": [{"source": "FRED", "enabled": False}],
            }
        ),
        encoding="utf-8",
    )

    def forbidden_runner(*args, **kwargs):
        raise AssertionError("conflicted registry reached child launch")

    with pytest.raises(module.RegistrySchemaError, match="conflict"):
        module.orchestrate_providers(
            ["FRED"],
            policy_path=policy,
            registry_path=registry,
            execute=True,
            runner=forbidden_runner,
        )


def test_registry_migration_preserves_and_marks_stale_providers() -> None:
    module = load_module()
    existing = {
        "sources": [
            {"source": "OLD_PROVIDER", "enabled": True, "measured": True, "rows": 9},
        ]
    }
    merged = module.merge_registry(
        existing,
        [{"source": "FRED", "enabled": True, "measured": False, "rows": 0}],
    )

    rows = {row["source"]: row for row in merged["rows"]}
    assert merged["schema"] == module.REGISTRY_ROWS_SCHEMA
    assert rows["OLD_PROVIDER"]["rows"] == 9
    assert rows["FRED"]["rows"] == 0
    assert merged["stale_provider_ids"] == ["OLD_PROVIDER"]
    assert merged["migration_boundary"]["input_schema"] == module.REGISTRY_LEGACY_SOURCES_SCHEMA


def test_receipt_hash_is_canonical_and_deterministic() -> None:
    module = load_module()
    first = module.seal_receipt({"schema": "test.v1", "b": [2, 1], "a": {"z": 3}})
    second = module.seal_receipt({"a": {"z": 3}, "b": [2, 1], "schema": "test.v1"})

    assert first["receipt_sha256"] == second["receipt_sha256"]
    assert module.verify_receipt_hash(first)
    assert module.verify_receipt_hash(second)


def test_rate_limit_state_persists_and_skips_provider_until_not_before(tmp_path) -> None:
    module = load_module()
    policy = write_policy(module, tmp_path, ["FRED"], max_retries=0)
    registry = write_registry(module, tmp_path)
    state = tmp_path / "state.json"
    reference = datetime(2026, 7, 18, 12, 0, tzinfo=timezone.utc)
    calls = 0

    def rate_limited_runner(command, **kwargs):
        nonlocal calls
        calls += 1
        return completed_child(
            module,
            command,
            env=kwargs["env"],
            qc_state="RETRYABLE_HTTP",
            http_status=429,
            retry_after_seconds=120,
        )

    first = module.orchestrate_providers(
        ["FRED"],
        policy_path=policy,
        registry_path=registry,
        state_path=state,
        execute=True,
        allow_network=True,
        run_id="rate-limit-first",
        runner=rate_limited_runner,
        now_fn=lambda: reference,
        runtime_root=tmp_path / "runtime",
    )

    def forbidden_runner(*args, **kwargs):
        raise AssertionError("persistently rate-limited provider was relaunched")

    second = module.orchestrate_providers(
        ["FRED"],
        policy_path=policy,
        registry_path=registry,
        state_path=state,
        execute=True,
        allow_network=True,
        run_id="rate-limit-second",
        runner=forbidden_runner,
        now_fn=lambda: reference + timedelta(seconds=30),
        runtime_root=tmp_path / "runtime",
    )

    persisted = json.loads(state.read_text(encoding="utf-8"))
    assert calls == 1
    assert first["providers"][0]["qc_state"] == "RETRYABLE_HTTP"
    assert persisted["providers"]["FRED"]["not_before_utc"] == "2026-07-18T12:02:00+00:00"
    assert second["providers"][0]["qc_state"] == "RATE_LIMITED"
    assert second["summary"]["launched_child_processes"] == 0


def test_each_child_command_has_one_provider_and_concurrency_is_bounded(tmp_path) -> None:
    module = load_module()
    providers = ["BLS", "EIA", "FRED"]
    policy = write_policy(module, tmp_path, providers, max_concurrency=2, max_retries=0)
    registry = write_registry(module, tmp_path)
    lock = threading.Lock()
    active = 0
    maximum_active = 0
    commands: list[list[str]] = []

    def runner(command, **kwargs):
        nonlocal active, maximum_active
        with lock:
            active += 1
            maximum_active = max(maximum_active, active)
            commands.append(list(command))
        time.sleep(0.03)
        try:
            return completed_child(
                module,
                command,
                env=kwargs["env"],
                qc_state="DRY_RUN",
                http_status=None,
            )
        finally:
            with lock:
                active -= 1

    receipt = module.orchestrate_providers(
        providers,
        policy_path=policy,
        registry_path=registry,
        execute=True,
        allow_network=False,
        run_id="bounded-concurrency-test",
        runner=runner,
        runtime_root=tmp_path / "runtime",
    )

    namespaces = {
        value
        for provider in receipt["providers"]
        for value in provider["namespace"].values()
    }
    assert len(commands) == len(providers)
    assert all(command.count("--child-provider") == 1 for command in commands)
    assert {command_value(command, "--child-provider") for command in commands} == set(providers)
    assert maximum_active <= 2
    assert len(namespaces) == len(providers) * 2


def test_direct_child_execution_is_rejected_by_real_subprocess(tmp_path) -> None:
    module = load_module()
    policy = write_policy(module, tmp_path, ["FRED"], max_retries=0)
    run_id = "direct-child-rejection"
    namespace = module.build_namespace_assignments(["FRED"], run_id)["FRED"]
    command = module.build_child_command(
        provider_id="FRED",
        policy_path=policy,
        run_id=run_id,
        attempt=1,
        namespace=namespace,
        max_rows=5,
        request_timeout_seconds=2,
        allow_network=True,
        stage_artifact=False,
    )

    completed = subprocess.run(
        command,
        capture_output=True,
        check=False,
        env=minimal_subprocess_env(),
        timeout=5,
    )

    assert completed.returncode == 2
    assert completed.stdout == b""
    assert b"rejected the request" in completed.stderr
    assert module.CHILD_AUTH_TOKEN_ENV not in " ".join(command)


def test_real_subprocess_gets_minimal_env_and_isolated_python_startup(tmp_path, monkeypatch) -> None:
    module = load_module()
    marker = tmp_path / "sitecustomize-loaded.txt"
    injection_dir = tmp_path / "pythonpath-injection"
    injection_dir.mkdir()
    (injection_dir / "sitecustomize.py").write_text(
        f"from pathlib import Path\nPath({str(marker)!r}).write_text('loaded', encoding='utf-8')\n",
        encoding="utf-8",
    )
    monkeypatch.setenv("FRED_API_KEY", "synthetic-provider-key")
    monkeypatch.setenv("LUMA_UNRELATED_SECRET", "must-not-cross")
    monkeypatch.setenv("PYTHONPATH", str(injection_dir))
    monkeypatch.setenv("PYTHONHOME", str(tmp_path / "hostile-python-home"))
    child_env = module.build_child_environment("FRED")
    code = (
        "import json, os, sys; "
        "print(json.dumps({'env_names': sorted(os.environ), 'sys_path': sys.path}))"
    )

    result = module._run_bounded_process(
        [sys.executable, "-I", "-B", "-c", code],
        env=child_env,
        timeout_seconds=5,
        max_output_bytes=16_384,
        cwd=tmp_path,
    )
    observed = json.loads(result["stdout"])

    assert result["returncode"] == 0
    assert result["overflow"] is False
    assert "FRED_API_KEY" in observed["env_names"]
    assert "LUMA_UNRELATED_SECRET" not in observed["env_names"]
    assert "PYTHONPATH" not in observed["env_names"]
    assert "PYTHONHOME" not in observed["env_names"]
    assert str(injection_dir) not in observed["sys_path"]
    assert not marker.exists()


def test_real_subprocess_stdout_and_stderr_are_bounded_before_capture() -> None:
    module = load_module()
    code = """
import os
import threading

payload = b"x" * 8192

def spam(fd):
    while True:
        os.write(fd, payload)

threads = [threading.Thread(target=spam, args=(1,)), threading.Thread(target=spam, args=(2,))]
for thread in threads:
    thread.start()
for thread in threads:
    thread.join()
"""
    started = time.monotonic()

    result = module._run_bounded_process(
        [sys.executable, "-I", "-B", "-c", code],
        env=minimal_subprocess_env(),
        timeout_seconds=8,
        max_output_bytes=4096,
    )

    assert result["overflow"] is True
    assert result["timed_out"] is False
    assert len(result["stdout"]) + len(result["stderr"]) <= 4096
    assert time.monotonic() - started < 8


def test_child_authorization_is_hmac_bound_and_one_use(tmp_path, monkeypatch) -> None:
    module = load_module()
    configure_workspace(module, tmp_path, monkeypatch)
    policy_path = write_policy(module, tmp_path, ["NWS_PUBLIC"], max_retries=0)
    policy = module.load_orchestrator_policy(policy_path)
    run_id = "one-use-authorization"
    namespace = module.build_namespace_assignments(["NWS_PUBLIC"], run_id)["NWS_PUBLIC"]
    control_env, paths = module.prepare_child_authorization(
        "NWS_PUBLIC",
        policy=policy,
        run_id=run_id,
        attempt=1,
        namespace=namespace,
        allow_network=False,
        stage_artifact=False,
        runtime_root=module.RUN_ROOT,
    )
    monkeypatch.setattr(module.os, "getppid", module.os.getpid)
    for name, value in control_env.items():
        monkeypatch.setenv(name, value)

    authorization, consumed_paths = module.consume_child_authorization(
        "NWS_PUBLIC",
        policy=policy,
        run_id=run_id,
        attempt=1,
        namespace=namespace,
        max_rows=policy["limits"]["max_rows"],
        request_timeout_seconds=policy["limits"]["request_timeout_seconds"],
        allow_network=False,
        stage_artifact=False,
        runtime_root=module.RUN_ROOT,
    )

    assert authorization["provider_id"] == "NWS_PUBLIC"
    assert consumed_paths == paths
    assert not paths["authorization_json"].exists()
    for name, value in control_env.items():
        monkeypatch.setenv(name, value)
    with pytest.raises(module.ChildAuthorizationError, match="already consumed"):
        module.consume_child_authorization(
            "NWS_PUBLIC",
            policy=policy,
            run_id=run_id,
            attempt=1,
            namespace=namespace,
            max_rows=policy["limits"]["max_rows"],
            request_timeout_seconds=policy["limits"]["request_timeout_seconds"],
            allow_network=False,
            stage_artifact=False,
            runtime_root=module.RUN_ROOT,
        )


def test_child_collection_does_not_read_env_files(tmp_path, monkeypatch) -> None:
    module = load_module()
    policy_path = write_policy(module, tmp_path, ["FRED"], max_retries=0)
    policy = module.load_orchestrator_policy(policy_path)
    monkeypatch.delenv("FRED_API_KEY", raising=False)

    def forbidden_env_read(*args, **kwargs):
        raise AssertionError("child collection attempted to read an env file")

    monkeypatch.setattr(module, "load_env_file", forbidden_env_read)
    monkeypatch.setitem(
        module.PROVIDER_BY_ID["FRED"],
        "collector",
        lambda max_rows, timeout: (200, [{"value": 1}], "synthetic"),
    )
    namespace = module.build_namespace_assignments(["FRED"], "no-env-file-read")["FRED"]

    receipt = module.build_provider_child_receipt(
        "FRED",
        policy=policy,
        run_id="no-env-file-read",
        attempt=1,
        namespace=namespace,
        max_rows=5,
        request_timeout_seconds=2,
        allow_network=True,
    )

    assert receipt["qc_state"] == "PASS"
    assert receipt["credential_state"] == "MISSING"


def test_real_subprocess_malformed_receipt_after_staging_fails_closed(tmp_path, monkeypatch) -> None:
    module = load_module()
    configure_workspace(module, tmp_path, monkeypatch)
    policy = write_policy(module, tmp_path, ["NWS_PUBLIC"], max_retries=0)
    registry = write_registry(module, tmp_path)
    state = tmp_path / "state.json"
    run_id = "malformed-after-staging"
    helper_code = """
import json
import os
from pathlib import Path

authorization = json.loads(Path(os.environ["LUMA_CHILD_AUTH_FILE"]).read_text(encoding="utf-8"))
for key in ("snapshot_json", "snapshot_latest_json", "snapshot_csv"):
    Path(authorization["paths"][key]).write_bytes(b"staged-before-malformed-receipt")
malformed = b'{"malformed":\\n'
Path(authorization["paths"]["receipt_json"]).write_bytes(malformed)
os.write(1, malformed)
"""

    def runner(command, **kwargs):
        return subprocess.run(
            [sys.executable, "-I", "-B", "-c", helper_code],
            capture_output=True,
            check=False,
            env=kwargs["env"],
            timeout=kwargs["timeout"],
        )

    def forbidden_publish(*args, **kwargs):
        raise AssertionError("malformed staged output reached publication")

    monkeypatch.setattr(module, "publish_measurement_outputs", forbidden_publish)
    receipt = module.orchestrate_providers(
        ["NWS_PUBLIC"],
        policy_path=policy,
        registry_path=registry,
        state_path=state,
        execute=True,
        allow_network=True,
        publish_outputs=True,
        run_id=run_id,
        runner=runner,
        runtime_root=module.RUN_ROOT,
    )
    paths = module.derive_child_job_paths("NWS_PUBLIC", run_id, 1, runtime_root=module.RUN_ROOT)

    assert receipt["status"] == "FAILED_CLOSED"
    assert receipt["providers"][0]["qc_state"] == "INVALID_RECEIPT"
    assert paths["snapshot_json"].exists()
    assert receipt["published_outputs"] is False
    assert not module.PUBLICATION_MANIFEST.exists()


@pytest.mark.parametrize("flag", ["--state-file", "--receipt-file"])
def test_cli_runtime_path_traversal_is_rejected_by_real_subprocess(tmp_path, flag) -> None:
    module = load_module()
    policy = write_policy(module, tmp_path, ["FRED"], max_retries=0)
    registry = write_registry(module, tmp_path)
    escaped = str(Path("run") / ".." / f"escaped-{flag[2:]}.json")
    command = [
        sys.executable,
        "-I",
        "-B",
        str(SCRIPT),
        "--policy",
        str(policy),
        "--registry",
        str(registry),
        "--provider",
        "FRED",
        flag,
        escaped,
    ]

    completed = subprocess.run(
        command,
        capture_output=True,
        check=False,
        env=minimal_subprocess_env(),
        timeout=5,
    )

    assert completed.returncode == 2
    assert completed.stdout == b""
    assert b"rejected the request" in completed.stderr


def test_cli_runtime_path_rejects_symlink_components(tmp_path, monkeypatch) -> None:
    module = load_module()
    root = configure_workspace(module, tmp_path, monkeypatch)
    run_root = root / "run"
    real_directory = run_root / "real"
    real_directory.mkdir(parents=True)
    linked_directory = run_root / "linked"
    try:
        linked_directory.symlink_to(real_directory, target_is_directory=True)
    except OSError as exc:
        pytest.skip(f"symlink creation is unavailable: {exc}")

    with pytest.raises(ValueError, match="symlink"):
        module.resolve_cli_runtime_path(linked_directory / "state.json", label="state file")


def test_all_rate_limited_run_does_not_publish_stale_registry_rows(tmp_path, monkeypatch) -> None:
    module = load_module()
    policy = write_policy(module, tmp_path, ["FRED"], max_retries=0)
    registry = write_registry(
        module,
        tmp_path,
        rows=[{"source": "FRED", "enabled": True, "measured": True, "rows": 999}],
    )
    state = tmp_path / "state.json"
    reference = datetime(2026, 7, 19, 12, 0, tzinfo=timezone.utc)
    state.write_text(
        json.dumps(
            {
                "schema": module.ORCHESTRATOR_STATE_SCHEMA,
                "providers": {
                    "FRED": {
                        "circuit_state": "OPEN",
                        "consecutive_failures": 2,
                        "not_before_utc": (reference + timedelta(minutes=5)).isoformat(),
                        "last_qc_state": "RETRYABLE_HTTP",
                        "last_http_status": 429,
                    }
                },
            }
        ),
        encoding="utf-8",
    )

    def forbidden(*args, **kwargs):
        raise AssertionError("rate-limited run attempted launch or publication")

    monkeypatch.setattr(module, "publish_measurement_outputs", forbidden)
    receipt = module.orchestrate_providers(
        ["FRED"],
        policy_path=policy,
        registry_path=registry,
        state_path=state,
        execute=True,
        allow_network=True,
        publish_outputs=True,
        run_id="all-rate-limited",
        runner=forbidden,
        now_fn=lambda: reference,
        runtime_root=tmp_path / "runtime",
    )

    assert receipt["status"] == "RATE_LIMITED"
    assert receipt["summary"]["quorum_status"] == "NONE_RATE_LIMITED"
    assert receipt["summary"]["fresh_receipt_providers"] == 0
    assert receipt["published_outputs"] is False


def test_partial_fresh_quorum_does_not_publish(tmp_path, monkeypatch) -> None:
    module = load_module()
    configure_workspace(module, tmp_path, monkeypatch)
    providers = ["NWS_PUBLIC", "OPEN_METEO_PUBLIC"]
    policy = write_policy(module, tmp_path, providers, max_retries=0)
    registry = write_registry(
        module,
        tmp_path,
        rows=[{"source": "OPEN_METEO_PUBLIC", "enabled": True, "measured": True, "rows": 50}],
    )
    state = tmp_path / "state.json"
    reference = datetime(2026, 7, 19, 12, 0, tzinfo=timezone.utc)
    state.write_text(
        json.dumps(
            {
                "schema": module.ORCHESTRATOR_STATE_SCHEMA,
                "providers": {
                    "OPEN_METEO_PUBLIC": {
                        "circuit_state": "OPEN",
                        "consecutive_failures": 2,
                        "not_before_utc": (reference + timedelta(minutes=5)).isoformat(),
                        "last_qc_state": "RETRYABLE_HTTP",
                        "last_http_status": 429,
                    }
                },
            }
        ),
        encoding="utf-8",
    )

    def runner(command, **kwargs):
        return completed_child(module, command, env=kwargs["env"])

    def forbidden_publish(*args, **kwargs):
        raise AssertionError("partial run reached canonical publication")

    monkeypatch.setattr(module, "publish_measurement_outputs", forbidden_publish)
    receipt = module.orchestrate_providers(
        providers,
        policy_path=policy,
        registry_path=registry,
        state_path=state,
        execute=True,
        allow_network=True,
        publish_outputs=True,
        run_id="partial-fresh-quorum",
        runner=runner,
        now_fn=lambda: reference,
        runtime_root=module.RUN_ROOT,
    )

    assert receipt["status"] == "PARTIAL"
    assert receipt["summary"]["quorum_status"] == "PARTIAL"
    assert receipt["summary"]["fresh_artifact_providers"] == 1
    assert receipt["summary"]["rate_limited_providers"] == 1
    assert receipt["published_outputs"] is False
    assert not module.PUBLICATION_MANIFEST.exists()


def test_manifest_commit_failure_leaves_canonical_pointer_and_aliases_unchanged(tmp_path, monkeypatch) -> None:
    module = load_module()
    configure_workspace(module, tmp_path, monkeypatch)
    run_id = "manifest-commit-failure"
    provider_result = staged_pass_result(module, "NWS_PUBLIC", run_id)
    sentinel = b"preexisting-canonical-bytes\n"
    canonical_aliases = [
        module.REGISTRY_JSON,
        module.LIVE_SOURCES_JSON,
        module.SOURCE_TRUTH_JSON,
        module.OUT_JSON,
        module.DASHBOARD_JSON,
        module.OUT_MD,
    ]
    for path in canonical_aliases:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(sentinel)
    original_atomic_write_json = module.atomic_write_json

    def failing_manifest_write(path, payload):
        if path == module.PUBLICATION_MANIFEST:
            raise OSError("synthetic manifest commit failure")
        return original_atomic_write_json(path, payload)

    monkeypatch.setattr(module, "atomic_write_json", failing_manifest_write)

    with pytest.raises(module.PublicationError, match="manifest commit failed"):
        module.publish_measurement_outputs(
            {"schema": module.REGISTRY_ROWS_SCHEMA, "rows": []},
            [provider_result],
            run_id=run_id,
        )

    assert not module.PUBLICATION_MANIFEST.exists()
    assert all(path.read_bytes() == sentinel for path in canonical_aliases)
    assert not (module.PUBLICATION_ROOT / run_id).exists()


def test_valid_generation_manifest_becomes_next_registry_input(tmp_path, monkeypatch) -> None:
    module = load_module()
    configure_workspace(module, tmp_path, monkeypatch)
    module.REGISTRY_JSON.parent.mkdir(parents=True)
    module.REGISTRY_JSON.write_text(
        json.dumps({"schema": module.REGISTRY_ROWS_SCHEMA, "rows": []}),
        encoding="utf-8",
    )
    run_id = "successful-generation"
    provider_result = staged_pass_result(module, "NWS_PUBLIC", run_id)

    publication = module.publish_measurement_outputs(
        {"schema": module.REGISTRY_ROWS_SCHEMA, "rows": []},
        [provider_result],
        run_id=run_id,
    )
    published_registry = module.read_live_source_registry()

    assert module.PUBLICATION_MANIFEST.exists()
    assert publication["publication_manifest_sha256"]
    assert published_registry["rows"][0]["source"] == "NWS_PUBLIC"
    assert published_registry["rows"][0]["rows"] == 1


def test_concurrent_state_updates_do_not_lose_circuit_failures(tmp_path) -> None:
    module = load_module()
    state = tmp_path / "concurrent-state.json"
    reference = datetime(2026, 7, 19, 12, 0, tzinfo=timezone.utc)
    limits = {"circuit_breaker_failures": 2, "default_rate_limit_seconds": 60}
    result = {
        "provider_id": "NWS_PUBLIC",
        "qc_state": "TIMEOUT",
        "retry_after_seconds": None,
        "http_status": None,
    }
    barrier = threading.Barrier(2)
    errors: list[Exception] = []

    def update() -> None:
        try:
            barrier.wait(timeout=2)
            module.update_rate_limit_state_file(
                state,
                [result],
                limits=limits,
                reference_utc=reference,
            )
        except Exception as exc:
            errors.append(exc)

    threads = [threading.Thread(target=update), threading.Thread(target=update)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join(timeout=5)

    persisted = module.load_rate_limit_state(state)
    assert errors == []
    assert all(not thread.is_alive() for thread in threads)
    assert persisted["providers"]["NWS_PUBLIC"]["consecutive_failures"] == 2
    assert persisted["providers"]["NWS_PUBLIC"]["circuit_state"] == "OPEN"


def test_query_text_is_redacted_and_public_headers_do_not_include_contact(monkeypatch) -> None:
    module = load_module()
    observed_headers: list[dict[str, str]] = []

    def fake_request(url, *, headers=None, **kwargs):
        observed_headers.append(dict(headers or {}))
        return 200, {"properties": {"periods": []}}, ""

    monkeypatch.setattr(module, "request_json", fake_request)
    module.rows_from_nws(1, 1)
    module.rows_from_sec_public(1, 1)

    redacted = module.sanitize_text("https://example.test/data?email=person@example.test&opaque=secret")
    assert redacted == "https://example.test/data?[REDACTED]"
    assert all("@" not in headers["User-Agent"] for headers in observed_headers)
    assert all("contact" not in headers["User-Agent"].lower() for headers in observed_headers)


def test_oversized_staged_snapshot_fails_before_any_artifact_write(tmp_path, monkeypatch) -> None:
    module = load_module()
    configure_workspace(module, tmp_path, monkeypatch)
    run_id = "oversized-staged-snapshot"
    paths = module.derive_child_job_paths("NWS_PUBLIC", run_id, 1, runtime_root=module.RUN_ROOT)
    paths["job_dir"].mkdir(parents=True)
    monkeypatch.setattr(module, "MAX_STAGED_ARTIFACT_BYTES", 1)

    with pytest.raises(module.OversizedJSONError):
        module.snapshot_provider(
            module.PROVIDER_BY_ID["NWS_PUBLIC"],
            {"rows": [{"value": "fresh"}], "http_status": 200, "probe_ok": True},
            run_id=run_id,
            attempt=1,
            artifact_paths={key: paths[key] for key in ("snapshot_json", "snapshot_latest_json", "snapshot_csv")},
        )

    assert not paths["snapshot_json"].exists()
    assert not paths["snapshot_latest_json"].exists()
    assert not paths["snapshot_csv"].exists()


def test_publication_rebinds_artifact_to_its_staged_receipt(tmp_path, monkeypatch) -> None:
    module = load_module()
    configure_workspace(module, tmp_path, monkeypatch)
    result = staged_pass_result(module, "NWS_PUBLIC", "receipt-binding-a")
    other = staged_pass_result(module, "NWS_PUBLIC", "receipt-binding-b")
    result["artifact"] = other["artifact"]

    with pytest.raises(module.PublicationError, match="artifact validation failed"):
        module.publish_measurement_outputs(
            {"schema": module.REGISTRY_ROWS_SCHEMA, "rows": []},
            [result],
            run_id="receipt-binding-a",
        )

    assert not module.PUBLICATION_MANIFEST.exists()


def test_half_open_reservation_allows_only_one_concurrent_probe(tmp_path) -> None:
    module = load_module()
    state = tmp_path / "half-open-state.json"
    reference = datetime(2026, 7, 19, 12, 0, tzinfo=timezone.utc)
    state.write_text(
        json.dumps(
            {
                "schema": module.ORCHESTRATOR_STATE_SCHEMA,
                "providers": {
                    "NWS_PUBLIC": {
                        "circuit_state": "OPEN",
                        "consecutive_failures": 2,
                        "not_before_utc": (reference - timedelta(seconds=1)).isoformat(),
                        "last_qc_state": "TIMEOUT",
                        "last_http_status": None,
                    }
                },
            }
        ),
        encoding="utf-8",
    )
    limits = {
        "default_rate_limit_seconds": 60,
        "max_retries": 1,
        "child_timeout_seconds": 5,
        "max_retry_delay_seconds": 1,
        "max_concurrency": 1,
    }
    barrier = threading.Barrier(2)
    eligible: list[set[str]] = []
    errors: list[Exception] = []

    def reserve() -> None:
        try:
            barrier.wait(timeout=2)
            _, selected, durable = module.reserve_provider_launches(
                state,
                ["NWS_PUBLIC"],
                limits=limits,
                reference_utc=reference,
            )
            assert durable is True
            eligible.append(selected)
        except Exception as exc:
            errors.append(exc)

    threads = [threading.Thread(target=reserve), threading.Thread(target=reserve)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join(timeout=5)

    persisted = module.load_rate_limit_state(state)
    assert errors == []
    assert all(not thread.is_alive() for thread in threads)
    assert sum("NWS_PUBLIC" in selected for selected in eligible) == 1
    assert persisted["providers"]["NWS_PUBLIC"]["circuit_state"] == "HALF_OPEN"


def test_concurrent_disjoint_publications_rebase_without_losing_rows(tmp_path, monkeypatch) -> None:
    module = load_module()
    configure_workspace(module, tmp_path, monkeypatch)
    registry = {"schema": module.REGISTRY_ROWS_SCHEMA, "rows": []}
    publications = [
        ("concurrent-nws", staged_pass_result(module, "NWS_PUBLIC", "concurrent-nws")),
        (
            "concurrent-open-meteo",
            staged_pass_result(module, "OPEN_METEO_PUBLIC", "concurrent-open-meteo"),
        ),
    ]
    barrier = threading.Barrier(2)
    errors: list[Exception] = []

    def publish(run_id, result) -> None:
        try:
            barrier.wait(timeout=2)
            module.publish_measurement_outputs(registry, [result], run_id=run_id)
        except Exception as exc:
            errors.append(exc)

    threads = [threading.Thread(target=publish, args=item) for item in publications]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join(timeout=10)

    publication = module._read_published_generation()
    assert errors == []
    assert all(not thread.is_alive() for thread in threads)
    assert publication is not None
    assert publication["manifest"]["provider_ids"] == ["NWS_PUBLIC", "OPEN_METEO_PUBLIC"]
    assert {row["source"] for row in publication["registry"]["rows"]} == {
        "NWS_PUBLIC",
        "OPEN_METEO_PUBLIC",
    }
    assert set(publication["manifest"]["files"]) == module.GENERATION_FIXED_FILES | {
        relative
        for provider_id in publication["manifest"]["provider_ids"]
        for relative in module._generation_artifact_files(provider_id).values()
    } | {
        module._generation_receipt_file(provider_id)
        for provider_id in publication["manifest"]["provider_ids"]
    }
    assert all(
        f"/{publication['manifest']['run_id']}/artifacts/" in row["snapshot_json"]
        for row in publication["registry"]["rows"]
    )


def test_first_publication_rereads_registry_path_under_lock(tmp_path, monkeypatch) -> None:
    module = load_module()
    configure_workspace(module, tmp_path, monkeypatch)
    run_id = "registry-lock-reread"
    registry_path = write_registry(
        module,
        tmp_path,
        rows=[{"source": "FRED", "enabled": False, "measured": False, "rows": 0}],
    )
    result = staged_pass_result(module, "NWS_PUBLIC", run_id)

    module.publish_measurement_outputs(
        {"schema": module.REGISTRY_ROWS_SCHEMA, "rows": []},
        [result],
        run_id=run_id,
        registry_path=registry_path,
    )
    publication = module._read_published_generation()

    assert publication is not None
    assert {row["source"] for row in publication["registry"]["rows"]} == {"FRED", "NWS_PUBLIC"}


def test_expired_closed_provider_is_atomically_reserved_for_full_execution_budget(tmp_path) -> None:
    module = load_module()
    state = tmp_path / "expired-closed-state.json"
    reference = datetime(2026, 7, 19, 12, 0, tzinfo=timezone.utc)
    state.write_text(
        json.dumps(
            {
                "schema": module.ORCHESTRATOR_STATE_SCHEMA,
                "providers": {
                    "NWS_PUBLIC": {
                        "circuit_state": "CLOSED",
                        "consecutive_failures": 1,
                        "not_before_utc": (reference - timedelta(seconds=1)).isoformat(),
                        "last_qc_state": "RETRYABLE_HTTP",
                        "last_http_status": 429,
                    }
                },
            }
        ),
        encoding="utf-8",
    )
    limits = {
        "max_retries": 2,
        "child_timeout_seconds": 5,
        "max_retry_delay_seconds": 7,
        "max_concurrency": 1,
        "default_rate_limit_seconds": 60,
    }

    first_state, first, first_durable = module.reserve_provider_launches(
        state,
        ["NWS_PUBLIC"],
        limits=limits,
        reference_utc=reference,
    )
    _, second, second_durable = module.reserve_provider_launches(
        state,
        ["NWS_PUBLIC"],
        limits=limits,
        reference_utc=reference,
    )

    lease_seconds = module.provider_reservation_lease_seconds(limits, 1)
    assert first == {"NWS_PUBLIC"}
    assert second == set()
    assert first_durable is True
    assert second_durable is True
    assert first_state["providers"]["NWS_PUBLIC"]["circuit_state"] == "HALF_OPEN"
    assert first_state["providers"]["NWS_PUBLIC"]["not_before_utc"] == (
        reference + timedelta(seconds=lease_seconds)
    ).isoformat()


def test_rate_limit_cooldown_uses_fresh_post_execution_timestamp(tmp_path) -> None:
    module = load_module()
    policy = write_policy(module, tmp_path, ["FRED"], max_retries=0)
    registry = write_registry(module, tmp_path)
    state = tmp_path / "fresh-cooldown-state.json"
    started = datetime(2026, 7, 19, 12, 0, tzinfo=timezone.utc)
    completed = started + timedelta(minutes=5)
    times = iter([started, completed])

    def runner(command, **kwargs):
        return completed_child(
            module,
            command,
            env=kwargs["env"],
            qc_state="RETRYABLE_HTTP",
            http_status=429,
            retry_after_seconds=120,
        )

    module.orchestrate_providers(
        ["FRED"],
        policy_path=policy,
        registry_path=registry,
        state_path=state,
        execute=True,
        allow_network=True,
        run_id="fresh-cooldown",
        runner=runner,
        now_fn=lambda: next(times),
        runtime_root=tmp_path / "runtime",
    )

    persisted = module.load_rate_limit_state(state)
    assert persisted["providers"]["FRED"]["not_before_utc"] == (
        completed + timedelta(seconds=120)
    ).isoformat()


def test_orchestrator_rejects_state_receipt_alias_before_mutation(tmp_path, monkeypatch) -> None:
    module = load_module()
    root = configure_workspace(module, tmp_path, monkeypatch)
    policy = write_policy(module, tmp_path, ["NWS_PUBLIC"])
    registry = write_registry(module, tmp_path)
    alias = root / "run" / "same.json"

    with pytest.raises(ValueError, match="receipt aliases state"):
        module.orchestrate_providers(
            ["NWS_PUBLIC"],
            policy_path=policy,
            registry_path=registry,
            state_path=alias,
            receipt_path=alias,
            run_id="path-alias",
            runtime_root=module.RUN_ROOT,
        )

    assert not alias.exists()


def test_publication_path_roles_reject_generation_and_staging_aliases(tmp_path, monkeypatch) -> None:
    module = load_module()
    configure_workspace(module, tmp_path, monkeypatch)
    run_id = "role-alias"
    monkeypatch.setattr(module, "PUBLICATION_MANIFEST", module.PUBLICATION_ROOT / run_id)
    with pytest.raises(ValueError, match="generation aliases publication_manifest"):
        module.validate_orchestrator_path_layout(run_id=run_id, staging_root=module.STAGING_ROOT)

    monkeypatch.setattr(module, "PUBLICATION_MANIFEST", module.OUT_OPS / "manifest.json")
    with pytest.raises(ValueError, match="publication_output aliases staging_root"):
        module.validate_orchestrator_path_layout(run_id=run_id, staging_root=module.PUBLICATION_ROOT)


def test_path_identity_resolves_symlink_aliases(tmp_path, monkeypatch) -> None:
    module = load_module()
    root = configure_workspace(module, tmp_path, monkeypatch)
    target = root / "run" / "real"
    target.mkdir(parents=True)
    linked = root / "run" / "linked"
    try:
        linked.symlink_to(target, target_is_directory=True)
    except OSError as exc:
        pytest.skip(f"symlink creation is unavailable: {exc}")

    with pytest.raises(ValueError, match="receipt aliases state"):
        module.validate_orchestrator_path_layout(
            run_id="symlink-alias",
            staging_root=module.STAGING_ROOT,
            state_path=target / "same.json",
            receipt_path=linked / "same.json",
        )


def test_optional_receipt_failure_preserves_committed_publication_ack(tmp_path, monkeypatch) -> None:
    module = load_module()
    root = configure_workspace(module, tmp_path, monkeypatch)
    policy = write_policy(module, tmp_path, ["NWS_PUBLIC"], max_retries=0)
    registry = write_registry(module, tmp_path)
    state = root / "run" / "state.json"
    receipt_path = root / "run" / "receipt.json"
    original_atomic_write_json = module.atomic_write_json

    def fail_only_receipt(path, payload):
        if path == receipt_path:
            raise OSError("synthetic optional receipt failure")
        return original_atomic_write_json(path, payload)

    monkeypatch.setattr(module, "atomic_write_json", fail_only_receipt)
    receipt = module.orchestrate_providers(
        ["NWS_PUBLIC"],
        policy_path=policy,
        registry_path=registry,
        state_path=state,
        receipt_path=receipt_path,
        execute=True,
        allow_network=True,
        publish_outputs=True,
        run_id="receipt-after-commit",
        runner=lambda command, **kwargs: completed_child(module, command, env=kwargs["env"]),
        runtime_root=module.RUN_ROOT,
    )

    assert receipt["status"] == "COMPLETE"
    assert receipt["published_outputs"] is True
    assert receipt["publication_state"] == "COMMITTED"
    assert receipt["receipt_persisted"] is False
    assert receipt["receipt_write_error"] == "RECEIPT_WRITE_FAILED"
    assert module.verify_receipt_hash(receipt)
    assert module._read_published_generation() is not None


def test_post_replace_manifest_error_is_acknowledged_without_rollback(tmp_path, monkeypatch) -> None:
    module = load_module()
    configure_workspace(module, tmp_path, monkeypatch)
    run_id = "manifest-post-replace-error"
    result = staged_pass_result(module, "NWS_PUBLIC", run_id)
    original_atomic_write_json = module.atomic_write_json

    def commit_then_raise(path, payload):
        durable = original_atomic_write_json(path, payload)
        if path == module.PUBLICATION_MANIFEST:
            raise OSError("synthetic error after manifest replacement")
        return durable

    monkeypatch.setattr(module, "atomic_write_json", commit_then_raise)
    publication = module.publish_measurement_outputs(
        {"schema": module.REGISTRY_ROWS_SCHEMA, "rows": []},
        [result],
        run_id=run_id,
    )

    assert publication["publication_state"] == "COMMITTED_DURABILITY_UNCERTAIN"
    assert (module.PUBLICATION_ROOT / run_id).is_dir()
    assert module._read_published_generation() is not None


def test_cleanup_failure_reports_recoverable_orphan_state(tmp_path, monkeypatch) -> None:
    module = load_module()
    root = configure_workspace(module, tmp_path, monkeypatch)
    policy = write_policy(module, tmp_path, ["NWS_PUBLIC"], max_retries=0)
    registry = write_registry(module, tmp_path)
    state = root / "run" / "state.json"
    run_id = "recoverable-orphan"
    original_atomic_write_json = module.atomic_write_json
    original_rmtree = module.shutil.rmtree

    def fail_manifest(path, payload):
        if path == module.PUBLICATION_MANIFEST:
            raise OSError("synthetic manifest failure")
        return original_atomic_write_json(path, payload)

    def fail_final_cleanup(path, *args, **kwargs):
        if Path(path) == module.PUBLICATION_ROOT / run_id:
            raise OSError("synthetic cleanup failure")
        return original_rmtree(path, *args, **kwargs)

    monkeypatch.setattr(module, "atomic_write_json", fail_manifest)
    monkeypatch.setattr(module.shutil, "rmtree", fail_final_cleanup)
    receipt = module.orchestrate_providers(
        ["NWS_PUBLIC"],
        policy_path=policy,
        registry_path=registry,
        state_path=state,
        execute=True,
        allow_network=True,
        publish_outputs=True,
        run_id=run_id,
        runner=lambda command, **kwargs: completed_child(module, command, env=kwargs["env"]),
        runtime_root=module.RUN_ROOT,
    )

    assert receipt["status"] == "FAILED_CLOSED"
    assert receipt["published_outputs"] is False
    assert receipt["publication_state"] == "ORPHANED_GENERATION"
    assert receipt["publication_orphan_path"].endswith(f"/{run_id}")
    assert (module.PUBLICATION_ROOT / run_id).is_dir()
    assert not module.PUBLICATION_MANIFEST.exists()


def test_published_registry_bytes_are_read_once_and_semantically_bound(tmp_path, monkeypatch) -> None:
    module = load_module()
    configure_workspace(module, tmp_path, monkeypatch)
    run_id = "exact-registry-bytes"
    result = staged_pass_result(module, "NWS_PUBLIC", run_id)
    module.publish_measurement_outputs(
        {"schema": module.REGISTRY_ROWS_SCHEMA, "rows": []},
        [result],
        run_id=run_id,
    )
    generation = module.PUBLICATION_ROOT / run_id
    registry_path = generation / "registry.json"
    original_read = module._read_regular_file_bounded
    registry_reads = 0

    def counting_read(path, **kwargs):
        nonlocal registry_reads
        if Path(path).resolve(strict=False) == registry_path.resolve(strict=False):
            registry_reads += 1
        return original_read(path, **kwargs)

    monkeypatch.setattr(module, "_read_regular_file_bounded", counting_read)
    publication = module._read_published_generation()
    assert publication is not None
    assert registry_reads == 1
    assert publication["registry"]["source_payload_sha256"] == module.sha256_bytes(
        registry_path.read_bytes()
    )

    registry_payload = json.loads(registry_path.read_bytes())
    registry_payload["rows"].append({"source": "OPEN_METEO_PUBLIC", "measured": False})
    registry_bytes = (json.dumps(registry_payload, indent=2, sort_keys=True) + "\n").encode("utf-8")
    registry_path.write_bytes(registry_bytes)
    manifest = json.loads(module.PUBLICATION_MANIFEST.read_text(encoding="utf-8"))
    manifest["files"]["registry.json"] = module.sha256_bytes(registry_bytes)
    manifest["manifest_sha256"] = module.sha256_payload(
        {key: value for key, value in manifest.items() if key != "manifest_sha256"}
    )
    module.PUBLICATION_MANIFEST.write_text(json.dumps(manifest), encoding="utf-8")

    with pytest.raises(module.RegistrySchemaError, match="measurement semantics"):
        module._read_published_generation()


def test_manifest_run_provider_and_inventory_semantics_are_enforced(tmp_path, monkeypatch) -> None:
    module = load_module()
    configure_workspace(module, tmp_path, monkeypatch)
    run_id = "manifest-semantics"
    result = staged_pass_result(module, "NWS_PUBLIC", run_id)
    module.publish_measurement_outputs(
        {"schema": module.REGISTRY_ROWS_SCHEMA, "rows": []},
        [result],
        run_id=run_id,
    )
    original = module.PUBLICATION_MANIFEST.read_bytes()

    for mutation, expected in [
        (lambda manifest: manifest.update({"run_id": "different-run"}), "canonical root"),
        (lambda manifest: manifest.update({"provider_ids": []}), "coverage disagrees"),
        (lambda manifest: manifest["files"].pop("dashboard.json"), "incomplete or contains extras"),
    ]:
        manifest = json.loads(original)
        mutation(manifest)
        manifest["manifest_sha256"] = module.sha256_payload(
            {key: value for key, value in manifest.items() if key != "manifest_sha256"}
        )
        module.PUBLICATION_MANIFEST.write_text(json.dumps(manifest), encoding="utf-8")
        with pytest.raises(module.RegistrySchemaError, match=expected):
            module._read_published_generation()


def test_provider_controlled_keys_are_redacted_and_csv_headers_are_safe(tmp_path, monkeypatch) -> None:
    module = load_module()
    configure_workspace(module, tmp_path, monkeypatch)
    run_id = "unsafe-provider-keys"
    paths = module.derive_child_job_paths("NWS_PUBLIC", run_id, 1, runtime_root=module.RUN_ROOT)
    paths["job_dir"].mkdir(parents=True)
    leaked = [
        "api_key=top-secret",
        "person@example.test",
        "https://example.test/data?token=top-secret",
        "=spreadsheet_formula",
    ]
    artifact = module.snapshot_provider(
        module.PROVIDER_BY_ID["NWS_PUBLIC"],
        {
            "rows": [
                {
                    leaked[0]: "value",
                    leaked[1]: "value",
                    leaked[2]: "value",
                    leaked[3]: "value",
                    "normal field": {"contact_email": "person@example.test"},
                }
            ],
            "http_status": 200,
            "probe_ok": True,
        },
        run_id=run_id,
        attempt=1,
        artifact_paths={key: paths[key] for key in ("snapshot_json", "snapshot_latest_json", "snapshot_csv")},
    )
    rendered = paths["snapshot_json"].read_text(encoding="utf-8") + paths["snapshot_csv"].read_text(
        encoding="utf-8"
    )
    snapshot = json.loads(paths["snapshot_json"].read_bytes())
    headers = next(module.csv.reader(module.io.StringIO(paths["snapshot_csv"].read_text(encoding="utf-8"))))

    assert all(value not in rendered for value in leaked[:3])
    assert "contact_email" not in rendered
    assert all(module.SAFE_CSV_FIELD.fullmatch(header) for header in headers)
    assert all(not header.startswith(("=", "+", "-", "@")) for header in headers)
    assert snapshot["rows"][0]["normal_field"] == {"redacted_field": "[REDACTED]"}
    assert artifact["file_sha256"]["snapshot_csv"] == module.sha256_file(paths["snapshot_csv"])
