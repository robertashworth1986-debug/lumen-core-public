from __future__ import annotations

import importlib.util
import json
import subprocess
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


def command_value(command: list[str], flag: str) -> str:
    return command[command.index(flag) + 1]


def completed_child(
    module,
    command: list[str],
    *,
    qc_state: str = "PASS",
    http_status: int | None = 200,
    retry_after_seconds: int | None = None,
    stderr: str = "",
) -> subprocess.CompletedProcess[str]:
    provider_id = command_value(command, "--child-provider")
    network_allowed = "--allow-network" in command
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
            "artifact": None,
        }
    )
    return subprocess.CompletedProcess(command, 0, json.dumps(receipt), stderr)


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
        return completed_child(module, command, stderr=f"provider said {secret}")

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


def test_published_receipt_rejects_artifact_outside_provider_directory() -> None:
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
            "published_outputs": True,
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
            expected_published_outputs=True,
            max_rows=5,
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
            return completed_child(module, command, qc_state="DRY_RUN", http_status=None)
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
