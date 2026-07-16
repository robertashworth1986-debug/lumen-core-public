from __future__ import annotations

import argparse
import csv
import importlib.util
import json
import math
from pathlib import Path
import sys

import numpy as np


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "code" / "frequency_cluster_truth_gauntlet.py"
PROTOCOL = ROOT / "config" / "frequency_cluster_truth_gauntlet_protocol_v1.json"
ERRATUM = (
    ROOT
    / "evidence"
    / "external_validation"
    / "frequency_cluster_protocol_timestamp_erratum_20260716.json"
)


def load_module():
    spec = importlib.util.spec_from_file_location("frequency_cluster_truth_gauntlet", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def load_protocol():
    return json.loads(PROTOCOL.read_text(encoding="utf-8"))


def test_protocol_blocks_execution_and_holdout_selection():
    module = load_module()
    protocol = load_protocol()
    receipt = module.validate_protocol(protocol)

    assert receipt["valid"] is True
    assert receipt["execution_disabled"] is True
    assert receipt["holdout_selection_disabled"] is True
    assert protocol["execution_authorized"] is False
    assert protocol["capital_at_risk_allowed"] is False
    assert protocol["holdout_used_for_selection"] is False
    assert protocol["null_and_adverse_results_retained"] is True
    assert protocol["directional_shadow_lane"]["orders_allowed"] is False


def test_frozen_protocol_timestamp_erratum_is_hash_linked_and_non_numeric():
    module = load_module()
    protocol = load_protocol()
    erratum = json.loads(ERRATUM.read_text(encoding="utf-8"))

    assert erratum["affected_protocol_sha256"] == module.sha256_file(PROTOCOL)
    assert erratum["recorded_value"] == protocol["frozen_utc"]
    assert erratum["intended_value"] == "2026-07-16T01:15:00Z"
    assert erratum["original_protocol_rewritten"] is False
    assert erratum["scoring_rules_changed"] is False
    assert erratum["numeric_outputs_changed"] is False


def test_holm_adjustment_is_monotone_in_sorted_p_value_order():
    module = load_module()
    raw = [0.04, 0.001, 0.02, 0.40]
    adjusted = module.holm_adjust(raw)
    ordered = sorted(range(len(raw)), key=lambda index: raw[index])

    assert all(0.0 <= value <= 1.0 for value in adjusted)
    assert [adjusted[index] for index in ordered] == sorted(
        adjusted[index] for index in ordered
    )
    assert adjusted[1] == 0.004


def write_synthetic_pair(path: Path, *, seed: int, rows: int = 701) -> None:
    rng = np.random.default_rng(seed)
    start_epoch = 1_704_067_200
    close = 100.0 + seed
    output: list[dict[str, object]] = []
    for index in range(rows):
        timestamp = start_epoch + index * 86400
        if index > 0:
            magnitude_bps = (
                115.0
                + 58.0 * math.sin(2.0 * math.pi * index / 10.0 + seed * 0.07)
                + 34.0 * math.cos(2.0 * math.pi * index / 30.0 - seed * 0.03)
                + rng.normal(0.0, 3.0)
            )
            direction = -1.0 if rng.random() < 0.5 else 1.0
            close *= math.exp(direction * max(8.0, magnitude_bps) / 10000.0)
        output.append(
            {
                "timestamp_utc": timestamp,
                "time_utc": "",
                "open": close,
                "high": close * 1.002,
                "low": close * 0.998,
                "close": close,
                "vwap": close,
                "volume": 1_000_000.0 + index * 10.0,
                "trade_count": 100,
            }
        )
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(output[0].keys()))
        writer.writeheader()
        writer.writerows(output)


def test_strong_synthetic_frequency_cohort_passes_and_hashes_verify(tmp_path):
    module = load_module()
    protocol = load_protocol()
    protocol["data"]["fixed_pair_universe"] = protocol["data"]["fixed_pair_universe"][:8]
    protocol["data"]["minimum_eligible_pairs"] = 6
    protocol["inference"]["pair_block_bootstrap_repetitions"] = 300
    protocol["inference"]["aggregate_pair_bootstrap_repetitions"] = 800
    protocol_path = tmp_path / "protocol.json"
    protocol_path.write_text(json.dumps(protocol, indent=2) + "\n", encoding="utf-8")

    input_dir = tmp_path / "inputs"
    for index, pair in enumerate(protocol["data"]["fixed_pair_universe"]):
        filename = f"kraken_{module.safe_pair_name(pair)}_1440m.csv"
        write_synthetic_pair(input_dir / filename, seed=100 + index)
    (input_dir / "retrieval_receipt.json").write_text(
        json.dumps(
            {
                "schema": "offline_fixture_receipt_v1",
                "provider": "offline_fixture",
                "public_endpoints_only": False,
                "authentication_used": False,
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )

    out_root = tmp_path / "out"
    summary = module.run_gauntlet(
        argparse.Namespace(
            protocol=str(protocol_path),
            out_root=str(out_root),
            input_dir=str(input_dir),
            timeout_seconds=1.0,
            pause_seconds=0.0,
        )
    )

    assert summary["aggregate"]["gate_pass"] is True
    assert summary["execution_authorized"] is False
    assert summary["source_authentic"] is False
    assert summary["independently_validated"] is False
    assert len(summary["selected_periods_days"]) == 3
    assert len(summary["aggregate"]["individually_promoted_pairs"]) >= 1

    run_dir = next(path for path in out_root.iterdir() if path.name.startswith("frequency_cluster_truth_gauntlet_"))
    manifest = json.loads((run_dir / "manifest.sha256.json").read_text(encoding="utf-8"))
    assert manifest["entry_count"] > 8
    for entry in manifest["entries"]:
        assert module.sha256_file(run_dir / entry["path"]) == entry["sha256"]

    duplicate = module.run_gauntlet(
        argparse.Namespace(
            protocol=str(protocol_path),
            out_root=str(out_root),
            input_dir=str(input_dir),
            timeout_seconds=1.0,
            pause_seconds=0.0,
        )
    )
    assert duplicate["decision"] == "DUPLICATE_SOURCE_SNAPSHOT_NOT_RESCORED"
    assert duplicate["holdout_rescored"] is False
    assert Path(duplicate["primary_scored_run"]) == run_dir
    identity_audit = json.loads(
        (out_root / "run_identity_audit.json").read_text(encoding="utf-8")
    )
    assert identity_audit["groups"][0]["scored_run_count"] == 1
    assert identity_audit["groups"][0]["duplicate_runs_are_independent_confirmations"] is False


def test_adverse_pair_family_cannot_pass_aggregate_gate():
    module = load_module()
    protocol = load_protocol()
    protocol["inference"]["aggregate_pair_bootstrap_repetitions"] = 200
    rows = []
    for index in range(6):
        rows.append(
            {
                "pair": f"PAIR{index}/USD",
                "candidate_mae": 1.10,
                "baseline_mae": {
                    "development_median": 1.00,
                    "online_ewma": 1.02,
                    "development_weekday_median": 1.01,
                    "matched_no_frequency": 1.00,
                },
                "worst_baseline_effect": -0.10,
                "effect_block_bootstrap_ci95": [-0.15, -0.05],
                "phase_shift_p_raw": 0.50,
            }
        )

    result = module.aggregate_pair_results(rows, protocol)

    assert result["gate_pass"] is False
    assert result["mean_worst_baseline_effect"] < 0.0
    assert result["individually_promoted_pairs"] == []
    assert all(row["individually_promoted"] is False for row in rows)
