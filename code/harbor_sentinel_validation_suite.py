"""Development/validation and stress suite for HarborSentinel.

The suite selects one threshold on development-only synthetic scenarios, then
freezes that threshold for disjoint validation and stress conditions. It is a
software feasibility benchmark, not operational or field evidence.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import platform
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from harbor_sentinel_benchmark import (
    ANOMALY_TYPES,
    evaluate_alerts,
    fit_profiles,
    score_stream,
    select_threshold,
    simulate_scenario,
)


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUT = ROOT / "out" / "harbor_sentinel_validation"
EVIDENCE_BOUNDARY = (
    "Synthetic software benchmark only. Inputs are generated AIS/ADS-B and "
    "radar-like observations, not operational sensor data. Results do not "
    "establish harbor, SSDS, adversarial, classified-environment, or field "
    "performance. Runtime measurements are machine-specific observations."
)


@dataclass(frozen=True)
class Condition:
    name: str
    tracks: int
    test_noise_multiplier: float
    benign_beacon_dropout_probability: float
    benign_beacon_dropout_burst_fraction: float


CONDITIONS = (
    Condition("nominal_24_tracks", 24, 1.0, 0.0, 0.0),
    Condition("congested_96_tracks", 96, 1.0, 0.0, 0.0),
    Condition("sensor_shift_1_5x", 24, 1.5, 0.0, 0.0),
    Condition("benign_point_dropout_2pct", 24, 1.0, 0.02, 0.0),
    Condition("benign_burst_dropout_20pct", 24, 1.0, 0.0, 0.20),
    Condition("combined_stress", 96, 1.5, 0.02, 0.20),
    Condition("severe_combined_stress", 192, 2.5, 0.05, 0.35),
)

SCORE_CONFIG = {
    "source_loss_threshold": 5.0,
    "enable_scene_degradation_gate": True,
    "degradation_onset": 2.25,
    "degradation_slope": 0.55,
    "degradation_cap": 2.25,
}
SCORE_CONFIG_NOTE = (
    "The v2 score stream estimates scene-wide source degradation from the "
    "median normalized radar/beacon disagreement at each timestamp, without "
    "using ground-truth labels. Behavioral scores and sensor-disagreement "
    "scores are down-weighted when the whole scene indicates a sensor-noise "
    "shift. Beacon loss uses a separate source-integrity review gate and does "
    "not by itself become a behavior-based threat candidate."
)


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _aggregate_condition(
    condition: Condition,
    *,
    scenarios: int,
    base_seed: int,
    threshold: float,
    score_config: dict[str, Any],
    warmup_steps: int,
    test_steps: int,
    anomaly_fraction: float,
) -> tuple[dict[str, Any], list[dict[str, Any]], list[dict[str, Any]]]:
    alerts_by_scenario: list[pd.DataFrame] = []
    scenario_rows: list[dict[str, Any]] = []
    source_lane_rows: list[dict[str, Any]] = []
    started = time.perf_counter()
    for scenario in range(scenarios):
        seed = base_seed + scenario * 10_007
        frame = simulate_scenario(
            seed=seed,
            tracks=condition.tracks,
            warmup_steps=warmup_steps,
            test_steps=test_steps,
            anomaly_fraction=anomaly_fraction,
            test_noise_multiplier=condition.test_noise_multiplier,
            benign_beacon_dropout_probability=(
                condition.benign_beacon_dropout_probability
            ),
            benign_beacon_dropout_burst_fraction=(
                condition.benign_beacon_dropout_burst_fraction
            ),
        )
        source_lane_rows.extend(
            _source_lane_rows(condition.name, scenario, seed, frame)
        )
        alerts = score_stream(
            frame,
            fit_profiles(frame),
            threshold=threshold,
            **score_config,
        )
        alerts.insert(0, "scenario", scenario)
        metrics = evaluate_alerts(alerts)
        alerts_by_scenario.append(alerts)
        scenario_rows.append(
            {
                "condition": condition.name,
                "scenario": scenario,
                "seed": seed,
                "tracks": condition.tracks,
                "precision": metrics["detector"]["precision"],
                "recall": metrics["detector"]["recall"],
                "f1": metrics["detector"]["f1"],
                "baseline_f1": metrics["baseline"]["f1"],
                "false_alerts_per_10000": metrics["detector"][
                    "false_alerts_per_10000_normal_points"
                ],
                "event_recall": metrics["event_recall"],
                "median_detection_delay_steps": metrics[
                    "median_detection_delay_steps"
                ],
            }
        )
    elapsed = time.perf_counter() - started
    all_alerts = pd.concat(alerts_by_scenario, ignore_index=True)
    aggregate = evaluate_alerts(all_alerts)
    processed_points = int(len(all_alerts))
    degradation = {
        "median_source_degradation_index": float(
            all_alerts["source_degradation_index"].median()
        ),
        "p95_source_degradation_index": float(
            all_alerts["source_degradation_index"].quantile(0.95)
        ),
        "median_source_degradation_factor": float(
            all_alerts["source_degradation_factor"].median()
        ),
        "p95_source_degradation_factor": float(
            all_alerts["source_degradation_factor"].quantile(0.95)
        ),
        "max_source_degradation_factor": float(
            all_alerts["source_degradation_factor"].max()
        ),
        "note": (
            "Scene-level source-quality diagnostic computed from observations "
            "only; no ground-truth anomaly labels are used."
        ),
    }
    class_detection = {}
    for anomaly_type, metrics in aggregate["class_metrics"].items():
        class_detection[anomaly_type] = {
            "point_recall": metrics["recall"],
            "event_count": metrics["event_count"],
            "event_recall": metrics["event_recall"],
            "median_detection_delay_steps": metrics[
                "median_detection_delay_steps"
            ],
            "threat_candidate_point_recall": metrics[
                "threat_candidate_point_recall"
            ],
        }
    result = {
        "configuration": {
            "tracks": condition.tracks,
            "test_noise_multiplier": condition.test_noise_multiplier,
            "benign_beacon_dropout_probability": (
                condition.benign_beacon_dropout_probability
            ),
            "benign_beacon_dropout_burst_fraction": (
                condition.benign_beacon_dropout_burst_fraction
            ),
            "scenarios": scenarios,
        },
        "detector": aggregate["detector"],
        "threat_candidate": aggregate["threat_candidate"],
        "fixed_kinematic_comparator": aggregate["baseline"],
        "event_recall": aggregate["event_recall"],
        "median_detection_delay_steps": aggregate[
            "median_detection_delay_steps"
        ],
        "explanation_coverage": aggregate["explanation_coverage"],
        "maximum_algorithmic_state_bytes_per_track": aggregate[
            "maximum_algorithmic_state_bytes_per_track"
        ],
        "class_detection": class_detection,
        "alert_category_counts": aggregate["alert_category_counts"],
        "source_degradation": degradation,
        "source_lane_coverage": _aggregate_source_lane_rows(source_lane_rows),
        "runtime_observation": {
            "elapsed_seconds": elapsed,
            "processed_test_points": processed_points,
            "test_points_per_second": (
                processed_points / elapsed if elapsed else None
            ),
            "note": "Machine-specific Python prototype timing; not a latency SLA.",
        },
    }
    return result, scenario_rows, source_lane_rows


def _source_lane_rows(
    condition: str,
    scenario: int,
    seed: int,
    frame: pd.DataFrame,
) -> list[dict[str, Any]]:
    test = frame[~frame["warmup"]].copy()
    rows: list[dict[str, Any]] = []
    lane_specs = (
        (
            "generated_ais_like_surface",
            "AIS-like cooperative beacon",
            test["domain"].eq("maritime"),
            "Generated surface cooperative-source observations; not public AIS files.",
        ),
        (
            "generated_adsb_like_air",
            "ADS-B-like cooperative beacon",
            test["domain"].eq("air"),
            "Generated air cooperative-source observations; not licensed ADS-B files.",
        ),
        (
            "generated_notional_radar_like_contact",
            "Notional radar-like observation",
            pd.Series(True, index=test.index),
            "Generated radar-like observations paired with every test track point.",
        ),
    )
    for lane, source_family, mask, note in lane_specs:
        lane_frame = test[mask]
        if lane == "generated_notional_radar_like_contact":
            available = int(len(lane_frame))
        else:
            available = int(lane_frame["beacon_available"].sum())
        observations = int(len(lane_frame))
        rows.append(
            {
                "condition": condition,
                "scenario": scenario,
                "seed": seed,
                "source_lane": lane,
                "source_family": source_family,
                "observations": observations,
                "available_observations": available,
                "availability_rate": (
                    available / observations if observations else 0.0
                ),
                "unique_tracks": int(lane_frame["track_id"].nunique()),
                "synthetic_only": True,
                "authorized_operational_data": False,
                "note": note,
            }
        )
    return rows


def _aggregate_source_lane_rows(rows: list[dict[str, Any]]) -> dict[str, Any]:
    coverage: dict[str, Any] = {}
    if not rows:
        return coverage
    frame = pd.DataFrame(rows)
    for lane, group in frame.groupby("source_lane", sort=True):
        observations = int(group["observations"].sum())
        available = int(group["available_observations"].sum())
        coverage[lane] = {
            "source_family": str(group["source_family"].iloc[0]),
            "observations": observations,
            "available_observations": available,
            "availability_rate": (
                available / observations if observations else 0.0
            ),
            "max_unique_tracks_per_scenario": int(group["unique_tracks"].max()),
            "synthetic_only": True,
            "authorized_operational_data": False,
            "note": str(group["note"].iloc[0]),
        }
    return coverage


def run_suite(
    *,
    out_dir: Path,
    development_scenarios: int = 20,
    validation_scenarios: int = 30,
    warmup_steps: int = 120,
    test_steps: int = 180,
    anomaly_fraction: float = 0.75,
    development_seed_base: int = 1_600_000,
    validation_seed_base: int = 1_900_000,
) -> dict[str, Any]:
    out_dir.mkdir(parents=True, exist_ok=False)

    development_frames = [
        simulate_scenario(
            seed=development_seed_base + scenario * 10_007,
            tracks=24,
            warmup_steps=warmup_steps,
            test_steps=test_steps,
            anomaly_fraction=anomaly_fraction,
        )
        for scenario in range(development_scenarios)
    ]
    threshold_selection = select_threshold(
        development_frames,
        [5.0, 6.0, 7.0, 8.0, 9.0, 10.0, 12.0],
        false_alert_cap_per_10000=100.0,
        **SCORE_CONFIG,
    )
    threshold = float(threshold_selection["selected_threshold"])

    conditions: dict[str, Any] = {}
    scenario_rows: list[dict[str, Any]] = []
    source_lane_rows: list[dict[str, Any]] = []
    for index, condition in enumerate(CONDITIONS):
        condition_result, rows, lane_rows = _aggregate_condition(
            condition,
            scenarios=validation_scenarios,
            base_seed=validation_seed_base + index * 1_000_000,
            threshold=threshold,
            score_config=SCORE_CONFIG,
            warmup_steps=warmup_steps,
            test_steps=test_steps,
            anomaly_fraction=anomaly_fraction,
        )
        conditions[condition.name] = condition_result
        scenario_rows.extend(rows)
        source_lane_rows.extend(lane_rows)

    summary = {
        "schema": "harbor_sentinel_validation_suite_v2",
        "generated_utc": datetime.now(timezone.utc).isoformat(),
        "evidence_boundary": EVIDENCE_BOUNDARY,
        "representative_source_lanes": {
            "mode": "generated feasibility inputs only",
            "minimum_topic_source_set_modeled": [
                "AIS-like cooperative surface beacon",
                "ADS-B-like cooperative air beacon",
                "notional radar-like contacts",
            ],
            "boundary": (
                "This run does not acquire NOAA AIS, OpenSky ADS-B, Navy "
                "radar, SSDS, or government-furnished operational data."
            ),
        },
        "score_configuration": {
            **SCORE_CONFIG,
            "note": SCORE_CONFIG_NOTE,
        },
        "development": {
            "scenarios": development_scenarios,
            "seed_base": development_seed_base,
            "threshold_selection": threshold_selection,
        },
        "validation": {
            "scenarios_per_condition": validation_scenarios,
            "seed_base": validation_seed_base,
            "threshold_frozen_from_development": threshold,
            "warmup_steps": warmup_steps,
            "test_steps": test_steps,
            "anomaly_fraction": anomaly_fraction,
            "conditions": conditions,
        },
        "platform": platform.platform(),
        "python": platform.python_version(),
        "limitations": [
            "No operational or government-furnished sensor data.",
            "No SSDS integration or operator-in-the-loop evaluation.",
            "No real adversary, electronic warfare, or cybersecurity validation.",
            "The comparator is a fixed kinematic rule, not a claimed state-of-the-art system.",
            "The compact-state count excludes Python runtime and integration overhead.",
        ],
    }

    summary_path = out_dir / "summary.json"
    summary_path.write_text(json.dumps(summary, indent=2), encoding="utf-8")

    scenario_path = out_dir / "scenario_summary.csv"
    with scenario_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(scenario_rows[0]))
        writer.writeheader()
        writer.writerows(scenario_rows)

    source_lane_path = out_dir / "source_lane_summary.csv"
    with source_lane_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(source_lane_rows[0]))
        writer.writeheader()
        writer.writerows(source_lane_rows)

    nominal = conditions["nominal_24_tracks"]
    combined = conditions["combined_stress"]
    severe = conditions["severe_combined_stress"]
    class_lines = [
        (
            f"- {name}: event recall "
            f"{nominal['class_detection'][name]['event_recall']:.3f}; "
            f"median delay "
            f"{nominal['class_detection'][name]['median_detection_delay_steps']}"
        )
        for name in ANOMALY_TYPES
    ]
    scorecard_path = out_dir / "SCORECARD.md"
    scorecard_path.write_text(
        "\n".join(
            [
                "# HarborSentinel Validation and Stress Scorecard",
                "",
                f"Evidence boundary: {EVIDENCE_BOUNDARY}",
                "",
                "## Development Gate",
                "",
                f"- Development scenarios: {development_scenarios}",
                f"- Frozen threshold: {threshold:.1f}",
                "- Selection rule: maximize development F1 subject to no more "
                "than 100 false alerts per 10,000 normal points.",
                "- Source-quality calibration: scene-wide median "
                "radar/beacon disagreement gates behavior confidence under "
                "detected sensor-noise shift.",
                "- Beacon-loss review gate: five consecutive missing "
                "cooperative observations generate source-integrity review "
                "without automatically creating a threat candidate.",
                "- Source lanes represented in this generated run: AIS-like "
                "surface cooperative beacon, ADS-B-like air cooperative "
                "beacon, and notional radar-like contacts.",
                "",
                "## Disjoint Nominal Validation",
                "",
                f"- Precision: {nominal['detector']['precision']:.3f}",
                f"- Recall: {nominal['detector']['recall']:.3f}",
                f"- F1: {nominal['detector']['f1']:.3f}",
                "- Fixed kinematic comparator F1: "
                f"{nominal['fixed_kinematic_comparator']['f1']:.3f}",
                "- False alerts per 10,000 normal points: "
                f"{nominal['detector']['false_alerts_per_10000_normal_points']:.1f}",
                "- Behavior-based threat-candidate false alerts per 10,000 "
                "normal points: "
                f"{nominal['threat_candidate']['false_alerts_per_10000_normal_points']:.1f}",
                f"- Event recall: {nominal['event_recall']:.3f}",
                "- Median detection delay: "
                f"{nominal['median_detection_delay_steps']} steps",
                "",
                "## Nominal Class Detection",
                "",
                *class_lines,
                "",
                "## Combined Congestion/Noise/Dropout Stress",
                "",
                f"- Tracks per scenario: {combined['configuration']['tracks']}",
                f"- Precision: {combined['detector']['precision']:.3f}",
                f"- Recall: {combined['detector']['recall']:.3f}",
                f"- F1: {combined['detector']['f1']:.3f}",
                "- False alerts per 10,000 normal points: "
                f"{combined['detector']['false_alerts_per_10000_normal_points']:.1f}",
                "- Behavior-based threat-candidate false alerts per 10,000 "
                "normal points: "
                f"{combined['threat_candidate']['false_alerts_per_10000_normal_points']:.1f}",
                f"- Event recall: {combined['event_recall']:.3f}",
                "- Median source-degradation factor: "
                f"{combined['source_degradation']['median_source_degradation_factor']:.2f}",
                "",
                "## Severe Breakdown Test",
                "",
                f"- Tracks per scenario: {severe['configuration']['tracks']}",
                f"- Review-alert precision: {severe['detector']['precision']:.3f}",
                f"- Review-alert F1: {severe['detector']['f1']:.3f}",
                "- Review false alerts per 10,000 normal points: "
                f"{severe['detector']['false_alerts_per_10000_normal_points']:.1f}",
                "- Behavior-based threat-candidate false alerts per 10,000 "
                "normal points: "
                f"{severe['threat_candidate']['false_alerts_per_10000_normal_points']:.1f}",
                "- Median source-degradation factor: "
                f"{severe['source_degradation']['median_source_degradation_factor']:.2f}",
                "",
                "## Generated Source-Lane Coverage",
                "",
                "- Boundary: generated feasibility inputs only; no NOAA AIS, "
                "OpenSky ADS-B, Navy radar, SSDS, or government-furnished "
                "operational data are included.",
                "- Nominal AIS-like availability: "
                f"{nominal['source_lane_coverage']['generated_ais_like_surface']['availability_rate']:.3f}",
                "- Nominal ADS-B-like availability: "
                f"{nominal['source_lane_coverage']['generated_adsb_like_air']['availability_rate']:.3f}",
                "- Nominal radar-like contact availability: "
                f"{nominal['source_lane_coverage']['generated_notional_radar_like_contact']['availability_rate']:.3f}",
                "- Severe-stress AIS-like availability: "
                f"{severe['source_lane_coverage']['generated_ais_like_surface']['availability_rate']:.3f}",
                "- Severe-stress ADS-B-like availability: "
                f"{severe['source_lane_coverage']['generated_adsb_like_air']['availability_rate']:.3f}",
                "",
                "## Interpretation",
                "",
                "These results test threshold separation and software behavior "
                "under generated congestion, noise, and benign transmitter "
                "dropout. Source-integrity alerts are separated from "
                "behavior-based threat candidates because transmitter loss or "
                "sensor disagreement alone does not identify hostile intent. "
                "The v2 source-quality gate is a synthetic feasibility result, "
                "not an operational degraded-sensor claim, and must be repeated "
                "on representative public and authorized government data.",
                "",
            ]
        ),
        encoding="utf-8",
    )

    files = {}
    for path in (summary_path, scenario_path, source_lane_path, scorecard_path):
        files[path.name] = {
            "bytes": path.stat().st_size,
            "sha256": _sha256(path),
        }
    (out_dir / "manifest.sha256.json").write_text(
        json.dumps(
            {
                "schema": "harbor_sentinel_validation_manifest_v1",
                "generated_utc": summary["generated_utc"],
                "files": files,
            },
            indent=2,
        ),
        encoding="utf-8",
    )
    return summary


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT)
    parser.add_argument("--development-scenarios", type=int, default=20)
    parser.add_argument("--validation-scenarios", type=int, default=30)
    parser.add_argument("--development-seed-base", type=int, default=1_600_000)
    parser.add_argument("--validation-seed-base", type=int, default=1_900_000)
    args = parser.parse_args()
    summary = run_suite(
        out_dir=args.out,
        development_scenarios=max(3, args.development_scenarios),
        validation_scenarios=max(3, args.validation_scenarios),
        development_seed_base=args.development_seed_base,
        validation_seed_base=args.validation_seed_base,
    )
    nominal = summary["validation"]["conditions"]["nominal_24_tracks"]
    combined = summary["validation"]["conditions"]["combined_stress"]
    print(
        json.dumps(
            {
                "threshold": summary["validation"][
                    "threshold_frozen_from_development"
                ],
                "nominal_f1": nominal["detector"]["f1"],
                "nominal_false_alerts_per_10000": nominal["detector"][
                    "false_alerts_per_10000_normal_points"
                ],
                "combined_stress_f1": combined["detector"]["f1"],
                "combined_stress_false_alerts_per_10000": combined[
                    "detector"
                ]["false_alerts_per_10000_normal_points"],
                "severe_stress_f1": summary["validation"]["conditions"][
                    "severe_combined_stress"
                ]["detector"]["f1"],
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
