from __future__ import annotations

import hashlib
import importlib.util
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "code" / "time_series_source_native_prospective_collector_v3.py"
PROTOCOL = ROOT / "config" / "time_series_source_native_prospective_protocol_v3.json"


def load_module():
    spec = importlib.util.spec_from_file_location("source_native_prospective_collector", SCRIPT)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def source_series(source: str = "FRED") -> dict:
    if source == "FRED":
        return {
            "source": "FRED",
            "source_contract_id": "fred-test-v1",
            "exchange_timezone": "UTC",
            "request_contract": {"output_type": 4, "realtime_chunk_days": 1460},
            "polling_contract": {"raw_response_retention_required": True},
            "series": [
                {
                    "series_id": "DGS10",
                    "cadence": "business_daily_observation_sequence",
                    "horizons": [1, 3, 5],
                    "minimum_history_count": 24,
                    "seasonal_period": 5,
                    "autoregressive_lag": 5,
                    "observation_start": "2026-01-01",
                    "alfred_initial_release_start": "2026-01-01",
                }
            ],
        }
    return {
        "source": "TWELVE_DATA",
        "source_contract_id": "twelve-test-v1",
        "exchange_timezone": "America/New_York",
        "polling_contract": {
            "not_before_exchange_local_time": "18:00:00",
            "raw_response_retention_required": True,
        },
        "request_contract": {"interval": "1day", "adjust": "splits"},
        "series": [
            {
                "series_id": "AAPL",
                "cadence": "exchange_business_daily_bar_sequence",
                "horizons": [1, 3, 5],
                "minimum_history_count": 24,
                "history_request_count": 30,
                "seasonal_period": 5,
                "autoregressive_lag": 5,
            }
        ],
    }


def make_test_protocol(source: str = "FRED") -> dict:
    return {
        "protocol_id": "TEST_TS_PROSPECTIVE_V3",
        "protocol_payload_sha256": "1" * 64,
        "freeze": {"freeze_utc": "2026-01-01T00:00:00Z"},
        "period_contract": {
            "first_confirmatory_period": {
                "period_id": "V3_CONFIRMATORY_P1",
                "target_period_start_inclusive": "2026-01-02",
                "target_period_end_inclusive": "2026-12-31",
                "fred_monthly_first_eligible_observation_month": "2026-02-01",
                "fred_monthly_last_eligible_observation_month": "2026-12-01",
            },
            "independent_replication_period": {
                "period_id": "V3_REPLICATION_P2",
                "target_period_start_inclusive": "2027-01-01",
                "target_period_end_inclusive": "2027-12-31",
                "fred_monthly_first_eligible_observation_month": "2027-01-01",
                "fred_monthly_last_eligible_observation_month": "2027-12-01",
            },
        },
        "candidate": {
            "registered_family_id": "fractal_brownian_surface",
            "scientific_estimator_id": "hurst_conditioned_multiscale_increment_heuristic_v1",
        },
        "sources": [source_series(source)],
        "registered_baselines": [
            "naive_last",
            "drift",
            "moving_average",
            "exponential_smoothing",
            "linear_trend",
            "seasonal_naive_source_period",
            "damped_holt_ets",
            "autoregressive_ridge_source_lag",
        ],
        "forecast_contract": {"prediction_decimal_places": 10},
        "implementation_bindings": {
            "model_file_sha256": "c" * 64,
            "collector_file_sha256": "d" * 64,
            "collector_path": "code/time_series_source_native_prospective_collector_v3.py",
            "analysis_path": "code/time_series_source_native_confirmatory_analysis_v3.py",
            "analysis_file_sha256": "e" * 64,
        },
        "ledger_contract": {
            "local_seal_without_external_anchor_state": "SEALED_LOCAL_ONLY_NOT_CONFIRMATORY",
            "settlement_schema": "time_series_source_native_settlement.v3",
        },
        "external_anchor_contract": {
            "pinned_trust": {
                "root_pem_path": "config/trust/freetsa_2026/cacert.pem",
                "root_pem_sha256": "2151b61137ffa86bf664691ba67e7da0b19f98c758e3d228d5d8ebf27e044438",
                "tsa_certificate_path": "config/trust/freetsa_2026/tsa.crt",
                "tsa_certificate_file_sha256": "8bfb0305bb64e2571ca507552ef3245cb1c2fee8728e0ff8689225081ea13467",
            }
        },
        "claim_boundary": "Synthetic custody test only; no performance claim.",
    }


def snapshot(
    module,
    *,
    source: str = "FRED",
    count: int = 30,
    fetched_at: str = "2026-01-30T12:00:00Z",
    custody_mode: str = "TEST_FIXTURE",
    raw_response_text: str | None = None,
) -> dict:
    start = datetime(2026, 1, 1, tzinfo=timezone.utc)
    observations = []
    for index in range(count):
        period = (start + timedelta(days=index)).date().isoformat()
        row = {"period": period, "value": 100.0 + index * 0.25}
        if source == "FRED":
            row["first_vintage_date"] = period
        observations.append(row)
    payload = {
        "schema": "time_series_source_native_source_snapshot.v3",
        "fetched_at_utc": fetched_at,
        "source": source,
        "custody_mode": custody_mode,
        "request_contract_sha256": "a" * 64,
        "source_response_sha256": "b" * 64,
        "series": [
            {
                "series_id": "DGS10" if source == "FRED" else "AAPL",
                "observations": observations,
            }
        ],
    }
    if raw_response_text is not None:
        digest = hashlib.sha256(raw_response_text.encode("utf-8")).hexdigest()
        payload["_raw_source_responses"] = [
            {
                "series_id": payload["series"][0]["series_id"],
                "response_sha256": digest,
                "response_text": raw_response_text,
                "http_status": 200,
                "response_headers": {"content-type": "application/json"},
                "response_metadata_sha256": module.canonical_sha256(
                    {
                        "http_status": 200,
                        "response_headers": {"content-type": "application/json"},
                    }
                ),
            }
        ]
    return payload


def test_real_v3_protocol_is_self_bound_and_supersedes_zero_observations() -> None:
    module = load_module()
    protocol = json.loads(PROTOCOL.read_text(encoding="utf-8"))
    errors = module.validate_protocol(protocol)

    assert errors == []
    assert protocol["supersession"]["prior_eligible_observation_count"] == 0
    assert protocol["supersession"]["outcome_dependent_change"] is False
    assert protocol["forecast_contract"]["horizons"] == [1, 3, 5]
    assert protocol["ledger_contract"]["external_anchor_required"] is True


def test_cycle_seals_then_settles_horizons_without_replacement(tmp_path: Path) -> None:
    module = load_module()
    protocol = make_test_protocol()
    model = module.load_model_module()
    initial = snapshot(module)

    first = module.run_cycle(
        protocol=protocol,
        snapshots=[initial],
        out_dir=tmp_path,
        sealed_at=datetime(2026, 1, 30, 12, 1, tzinfo=timezone.utc),
        model=model,
        allow_test_fixture=True,
    )
    assert first["cycle"]["after"]["prediction_count"] == 3
    assert first["cycle"]["after"]["settlement_count"] == 0
    assert first["cycle"]["external_anchor_request"]["prediction_count"] == 3
    assert first["cycle"]["external_anchor_request"][
        "local_request_is_independent_time_proof"
    ] is False
    assert first["status"]["pending_external_anchor_request_count"] == 1

    later = snapshot(
        module,
        count=35,
        fetched_at="2026-02-06T12:00:00Z",
    )
    second = module.run_cycle(
        protocol=protocol,
        snapshots=[later],
        out_dir=tmp_path,
        sealed_at=datetime(2026, 2, 6, 12, 0, tzinfo=timezone.utc),
        model=model,
        allow_test_fixture=True,
    )
    predictions, prediction_terminal = module.load_chain(
        module.output_paths(tmp_path)["predictions"]
    )
    settlements, settlement_terminal = module.load_chain(
        module.output_paths(tmp_path)["settlements"]
    )

    assert second["cycle"]["after"]["prediction_count"] == 6
    assert second["cycle"]["after"]["settlement_count"] == 3
    assert len({row["prediction_key"] for row in predictions}) == 6
    assert {row["target_period"] for row in settlements} == {
        "2026-01-31",
        "2026-02-02",
        "2026-02-04",
    }
    assert all(row["primary_scoring_eligible"] is False for row in predictions)
    assert all(row["execution_parameters"]["prediction_decimal_places"] == 10 for row in predictions)
    assert all(row["runtime_fingerprint"]["python_version"] for row in predictions)
    assert all(row["model_file_sha256"] == "c" * 64 for row in predictions)
    assert all(row["origin_completeness_proof"]["passed"] is True for row in predictions)
    assert all(row["external_anchor_verified"] is False for row in settlements)
    assert prediction_terminal == predictions[-1]["record_sha256"]
    assert settlement_terminal == settlements[-1]["record_sha256"]
    assert second["status"]["performance_claim_allowed"] is False


def test_late_fred_seal_is_not_settled(tmp_path: Path) -> None:
    module = load_module()
    protocol = make_test_protocol()
    model = module.load_model_module()
    paths = module.output_paths(tmp_path)
    initial = module.normalize_snapshot(snapshot(module), protocol)
    module.seal_snapshot(
        protocol=protocol,
        snapshot=initial,
        predictions_path=paths["predictions"],
        sealed_at=datetime(2026, 2, 1, 12, 0, tzinfo=timezone.utc),
        model=model,
        allow_test_fixture=True,
    )
    later = module.normalize_snapshot(
        snapshot(module, count=31, fetched_at="2026-02-02T12:00:00Z"), protocol
    )
    result = module.settle_snapshot(
        protocol=protocol,
        snapshot=later,
        predictions_path=paths["predictions"],
        settlements_path=paths["settlements"],
    )

    assert result["settled_record_count"] == 0
    assert result["late_or_unproven_release_order_skipped_count"] == 1


def test_twelve_data_requires_prior_exchange_local_date() -> None:
    module = load_module()
    source = source_series("TWELVE_DATA")
    prediction = {
        "source": "TWELVE_DATA",
        "sealed_at_utc": "2026-02-02T14:00:00Z",
    }
    same_day = module.release_order_proof(
        prediction,
        {"period": "2026-02-02", "value": 1.0},
        source,
        actual_observed_at_utc="2026-02-02T23:00:00Z",
    )
    next_day = module.release_order_proof(
        prediction,
        {"period": "2026-02-03", "value": 1.0},
        source,
        actual_observed_at_utc="2026-02-03T23:00:00Z",
    )
    missed_same_session = module.release_order_proof(
        prediction,
        {"period": "2026-02-03", "value": 1.0},
        source,
        actual_observed_at_utc="2026-02-04T23:00:00Z",
    )

    assert same_day["passed"] is False
    assert next_day["passed"] is True
    assert missed_same_session["passed"] is False
    assert missed_same_session["first_seen_same_session"] is False


def test_twelve_data_rejects_incomplete_same_session_origin() -> None:
    module = load_module()
    protocol = make_test_protocol("TWELVE_DATA")
    source = source_series("TWELVE_DATA")
    before_close = module.normalize_snapshot(
        snapshot(
            module,
            source="TWELVE_DATA",
            fetched_at="2026-01-30T19:00:00Z",
        ),
        protocol,
    )
    after_close = module.normalize_snapshot(
        snapshot(
            module,
            source="TWELVE_DATA",
            fetched_at="2026-01-30T23:01:00Z",
        ),
        protocol,
    )
    prior_session = module.normalize_snapshot(
        snapshot(
            module,
            source="TWELVE_DATA",
            fetched_at="2026-01-31T14:00:00Z",
        ),
        protocol,
    )

    before = module.origin_completeness_proof(
        snapshot=before_close,
        source=source,
        observations=before_close["series"][0]["observations"],
    )
    after = module.origin_completeness_proof(
        snapshot=after_close,
        source=source,
        observations=after_close["series"][0]["observations"],
    )
    prior = module.origin_completeness_proof(
        snapshot=prior_session,
        source=source,
        observations=prior_session["series"][0]["observations"],
    )

    assert before["passed"] is False
    assert after["same_session_after_close"] is True
    assert after["passed"] is True
    assert prior["prior_session"] is True
    assert prior["passed"] is True


def test_production_cycle_rejects_fixture_before_writing(tmp_path: Path) -> None:
    module = load_module()
    protocol = make_test_protocol()

    with pytest.raises(ValueError, match="production custody ledger"):
        module.run_cycle(
            protocol=protocol,
            snapshots=[snapshot(module)],
            out_dir=tmp_path,
            sealed_at=datetime(2026, 1, 30, 12, 1, tzinfo=timezone.utc),
            model=module.load_model_module(),
        )

    assert not module.output_paths(tmp_path)["predictions"].exists()
    assert not module.output_paths(tmp_path)["runs"].exists()
    assert not module.output_paths(tmp_path)["anchor_requests"].exists()


def test_preflight_blocks_all_appends_when_later_snapshot_is_invalid(tmp_path: Path) -> None:
    module = load_module()
    protocol = make_test_protocol()
    first = snapshot(module, raw_response_text='{"ok":1}')
    invalid = snapshot(module, count=31, raw_response_text='{"ok":2}')
    invalid["_raw_source_responses"][0]["response_sha256"] = "0" * 64

    with pytest.raises(ValueError, match="raw provider response hash mismatch"):
        module.run_cycle(
            protocol=protocol,
            snapshots=[first, invalid],
            out_dir=tmp_path,
            sealed_at=datetime(2026, 1, 31, 12, 1, tzinfo=timezone.utc),
            model=module.load_model_module(),
            allow_test_fixture=True,
        )

    paths = module.output_paths(tmp_path)
    assert not paths["predictions"].exists()
    assert not paths["settlements"].exists()
    assert not paths["runs"].exists()
    assert not paths["anchor_requests"].exists()


def test_live_snapshot_retains_raw_provider_response_by_hash(tmp_path: Path) -> None:
    module = load_module()
    protocol = make_test_protocol("TWELVE_DATA")
    supplied = snapshot(
        module,
        source="TWELVE_DATA",
        custody_mode="LIVE_PROVIDER_RESPONSE",
    )
    raw_payload = {
        "meta": {
            "symbol": "AAPL",
            "interval": "1day",
            "exchange_timezone": "America/New_York",
        },
        "values": [
            {"datetime": row["period"], "close": str(row["value"])}
            for row in supplied["series"][0]["observations"]
        ],
    }
    raw = json.dumps(raw_payload, sort_keys=True, separators=(",", ":"))
    metadata = {
        "http_status": 200,
        "response_headers": {"content-type": "application/json"},
    }
    retained = {
        "series_id": "AAPL",
        "response_sha256": hashlib.sha256(raw.encode("utf-8")).hexdigest(),
        "response_text": raw,
        **metadata,
        "response_metadata_sha256": module.canonical_sha256(metadata),
    }
    supplied["_raw_source_responses"] = [retained]
    fetched_at = module.parse_utc(supplied["fetched_at_utc"])
    supplied["request_contract_sha256"] = module.canonical_sha256(
        module.expected_safe_request_contracts(protocol, "TWELVE_DATA", fetched_at)
    )
    supplied["source_response_sha256"] = module.canonical_sha256(
        [module.response_receipt(retained)]
    )
    normalized = module.normalize_snapshot(supplied, protocol)
    paths = module.output_paths(tmp_path)
    written = module.persist_raw_source_responses(
        supplied["_raw_source_responses"], paths["raw_responses"]
    )

    assert normalized["raw_response_retention_verified"] is True
    assert len(written) == 2
    assert len(normalized["raw_response_sha256s"]) == 1
    assert len(normalized["raw_response_metadata_sha256s"]) == 1
    body_path = next(path for path in written if not path.name.endswith(".metadata.json"))
    assert hashlib.sha256(body_path.read_bytes()).hexdigest() == body_path.stem


def test_fred_realtime_windows_are_bounded_contiguous_and_terminal() -> None:
    module = load_module()
    windows = module.fred_realtime_windows(
        "2020-01-01",
        as_of_date=datetime(2026, 8, 1, tzinfo=timezone.utc).date(),
        chunk_days=1460,
    )

    assert windows[0][0] == "2020-01-01"
    assert windows[-1][1] == "9999-12-31"
    for (previous_start, previous_end), (next_start, _) in zip(windows, windows[1:]):
        expected = datetime.fromisoformat(previous_end).date() + timedelta(days=1)
        assert datetime.fromisoformat(next_start).date() == expected
        assert (
            datetime.fromisoformat(previous_end).date()
            - datetime.fromisoformat(previous_start).date()
        ).days + 1 <= 1460


def test_snapshot_rejects_credential_like_metadata() -> None:
    module = load_module()
    supplied = snapshot(module)
    supplied["api_key"] = "must-not-be-serialized"

    with pytest.raises(ValueError, match="credential-like metadata"):
        module.normalize_snapshot(supplied, make_test_protocol())


def test_production_cli_has_no_local_snapshot_ingress() -> None:
    module = load_module()

    with pytest.raises(SystemExit):
        module.parse_args(["cycle", "--snapshot", "fixture.json"])


def test_raw_http_metadata_tampering_is_rejected() -> None:
    module = load_module()
    supplied = snapshot(module, raw_response_text='{"ok":true}')
    supplied["_raw_source_responses"][0]["http_status"] = 500

    with pytest.raises(ValueError, match="HTTP status is not 200"):
        module.normalize_snapshot(supplied, make_test_protocol())


def test_prediction_chain_detects_tampering(tmp_path: Path) -> None:
    module = load_module()
    path = tmp_path / "chain.jsonl"
    first = module.append_chain_record(path, {"value": 1}, module.ZERO_HASH)
    module.append_chain_record(path, {"value": 2}, first["record_sha256"])
    rows = path.read_text(encoding="utf-8").splitlines()
    altered = json.loads(rows[0])
    altered["value"] = 99
    rows[0] = json.dumps(altered, sort_keys=True, separators=(",", ":"))
    path.write_text("\n".join(rows) + "\n", encoding="utf-8")

    with pytest.raises(ValueError, match="record hash mismatch"):
        module.load_chain(path)
