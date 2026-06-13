"""
HarborSentinel compact streaming pattern-of-life benchmark.

This is a deterministic synthetic validation harness for a grant prototype. It
does not represent operational maritime or air-surveillance performance.
"""
from __future__ import annotations

import argparse
import copy
import hashlib
import json
import math
import os
import platform
import subprocess
import sys
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd


ROOT = Path(
    os.environ.get("LUMA_ROOT", str(Path(__file__).resolve().parents[1]))
).expanduser().resolve()
OUT_ROOT = ROOT / "out" / "harbor_sentinel"
LEDGER = OUT_ROOT / "ledger.jsonl"
ANOMALY_TYPES = (
    "route_deviation",
    "loiter",
    "speed_burst",
    "sharp_turn",
    "beacon_silence",
    "beacon_spoof",
)


@dataclass
class TrackProfile:
    track_id: str
    domain: str
    beacon_sensor: str
    intercept_x: float
    intercept_y: float
    velocity_x: float
    velocity_y: float
    expected_speed: float
    position_scale: float
    speed_scale: float
    heading_scale: float
    disagreement_scale: float
    acceleration_scale: float
    last_x: float
    last_y: float
    last_speed: float
    missing_streak: int = 0

    @property
    def algorithmic_state_bytes(self) -> int:
        # Fifteen float64 values plus one int32 and compact identifiers.
        return 15 * 8 + 4 + len(self.track_id) + len(self.domain) + len(
            self.beacon_sensor
        )


def utc_tag() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def utc_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _robust_scale(values: np.ndarray, floor: float) -> float:
    values = np.asarray(values, dtype=float)
    median = float(np.median(values))
    mad = float(np.median(np.abs(values - median))) * 1.4826
    return max(mad, floor)


def _angle_difference(left: float, right: float) -> float:
    return abs((left - right + math.pi) % (2.0 * math.pi) - math.pi)


def _fused_position(row: pd.Series) -> tuple[float, float]:
    if bool(row["beacon_available"]):
        return (
            0.65 * float(row["radar_x"]) + 0.35 * float(row["beacon_x"]),
            0.65 * float(row["radar_y"]) + 0.35 * float(row["beacon_y"]),
        )
    return float(row["radar_x"]), float(row["radar_y"])


def simulate_scenario(
    *,
    seed: int,
    tracks: int = 24,
    warmup_steps: int = 120,
    test_steps: int = 180,
    anomaly_fraction: float = 0.75,
    noise_multiplier: float = 1.0,
    test_noise_multiplier: float = 1.0,
    benign_beacon_dropout_probability: float = 0.0,
    benign_beacon_dropout_burst_fraction: float = 0.0,
) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    total_steps = warmup_steps + test_steps
    rows: list[dict[str, Any]] = []
    anomalous_tracks = int(round(tracks * anomaly_fraction))
    for index in range(tracks):
        track_id = f"T{index:03d}"
        domain = "maritime" if index % 2 == 0 else "air"
        beacon_sensor = "AIS" if domain == "maritime" else "ADS-B"
        start = rng.uniform(-80.0, 80.0, size=2)
        heading = float(rng.uniform(-math.pi, math.pi))
        direction = np.asarray([math.cos(heading), math.sin(heading)])
        normal = np.asarray([-direction[1], direction[0]])
        speed = float(
            rng.uniform(0.7, 2.0)
            if domain == "maritime"
            else rng.uniform(4.0, 8.0)
        )
        radar_noise = (
            0.22 if domain == "maritime" else 0.45
        ) * noise_multiplier
        beacon_noise = radar_noise * 0.65
        lane_amplitude = radar_noise * rng.uniform(1.0, 2.0)
        lane_period = float(rng.uniform(45.0, 90.0))
        lane_phase = float(rng.uniform(0.0, 2.0 * math.pi))

        anomaly_type = (
            ANOMALY_TYPES[index % len(ANOMALY_TYPES)]
            if index < anomalous_tracks
            else "none"
        )
        event_start = int(rng.integers(warmup_steps + 25, total_steps - 45))
        event_duration = int(rng.integers(22, 36))
        event_end = min(total_steps, event_start + event_duration)
        benign_dropout_start = -1
        benign_dropout_end = -1
        if (
            anomaly_type == "none"
            and benign_beacon_dropout_burst_fraction > 0.0
            and rng.random() < benign_beacon_dropout_burst_fraction
        ):
            benign_dropout_start = int(
                rng.integers(warmup_steps + 10, total_steps - 35)
            )
            benign_dropout_end = min(
                total_steps,
                benign_dropout_start + int(rng.integers(18, 31)),
            )
        event_origin = (
            start
            + direction * speed * event_start
            + normal
            * lane_amplitude
            * math.sin(2.0 * math.pi * event_start / lane_period + lane_phase)
        )
        turn_angle = math.radians(72.0)
        turned_direction = np.asarray(
            [
                math.cos(heading + turn_angle),
                math.sin(heading + turn_angle),
            ]
        )

        for timestamp in range(total_steps):
            observation_noise_multiplier = (
                test_noise_multiplier
                if timestamp >= warmup_steps
                else 1.0
            )
            observation_radar_noise = (
                radar_noise * observation_noise_multiplier
            )
            observation_beacon_noise = (
                beacon_noise * observation_noise_multiplier
            )
            lane = (
                normal
                * lane_amplitude
                * math.sin(
                    2.0 * math.pi * timestamp / lane_period + lane_phase
                )
            )
            true_position = start + direction * speed * timestamp + lane
            is_anomaly = (
                anomaly_type != "none"
                and event_start <= timestamp < event_end
            )
            if is_anomaly and anomaly_type == "route_deviation":
                progress = (timestamp - event_start + 1) / event_duration
                true_position = true_position + normal * radar_noise * (
                    16.0 + 18.0 * progress
                )
            elif is_anomaly and anomaly_type == "loiter":
                angle = 2.0 * math.pi * (timestamp - event_start) / 12.0
                true_position = event_origin + radar_noise * 2.0 * np.asarray(
                    [math.cos(angle), math.sin(angle)]
                )
            elif is_anomaly and anomaly_type == "speed_burst":
                elapsed = timestamp - event_start
                true_position = (
                    event_origin + direction * speed * 2.6 * elapsed + lane
                )
            elif is_anomaly and anomaly_type == "sharp_turn":
                elapsed = timestamp - event_start
                true_position = event_origin + turned_direction * speed * elapsed

            radar_position = true_position + rng.normal(
                0.0,
                observation_radar_noise,
                size=2,
            )
            benign_dropout = (
                not is_anomaly
                and (
                    (
                        benign_beacon_dropout_probability > 0.0
                        and rng.random()
                        < benign_beacon_dropout_probability
                    )
                    or (
                        benign_dropout_start
                        <= timestamp
                        < benign_dropout_end
                    )
                )
            )
            beacon_available = not (
                (is_anomaly and anomaly_type == "beacon_silence")
                or benign_dropout
            )
            beacon_position = true_position + rng.normal(
                0.0,
                observation_beacon_noise,
                size=2,
            )
            if is_anomaly and anomaly_type == "beacon_spoof":
                beacon_position = (
                    beacon_position
                    + normal * radar_noise * 35.0
                    + direction * radar_noise * 12.0
                )
            rows.append(
                {
                    "timestamp": timestamp,
                    "track_id": track_id,
                    "domain": domain,
                    "beacon_sensor": beacon_sensor,
                    "warmup": timestamp < warmup_steps,
                    "true_anomaly": bool(is_anomaly),
                    "anomaly_type": anomaly_type if is_anomaly else "none",
                    "event_start": event_start if anomaly_type != "none" else -1,
                    "radar_x": float(radar_position[0]),
                    "radar_y": float(radar_position[1]),
                    "beacon_available": beacon_available,
                    "beacon_x": (
                        float(beacon_position[0])
                        if beacon_available
                        else float("nan")
                    ),
                    "beacon_y": (
                        float(beacon_position[1])
                        if beacon_available
                        else float("nan")
                    ),
                }
            )
    return pd.DataFrame(rows)


def fit_profiles(frame: pd.DataFrame) -> dict[str, TrackProfile]:
    profiles: dict[str, TrackProfile] = {}
    warmup = frame[frame["warmup"]].copy()
    for track_id, group in warmup.groupby("track_id", sort=True):
        group = group.sort_values("timestamp")
        positions = np.asarray(
            [_fused_position(row) for _, row in group.iterrows()],
            dtype=float,
        )
        timestamps = group["timestamp"].to_numpy(dtype=float)
        design = np.column_stack([np.ones(len(timestamps)), timestamps])
        beta_x = np.linalg.lstsq(design, positions[:, 0], rcond=None)[0]
        beta_y = np.linalg.lstsq(design, positions[:, 1], rcond=None)[0]
        predicted = np.column_stack(
            [
                design @ beta_x,
                design @ beta_y,
            ]
        )
        residual_distance = np.linalg.norm(positions - predicted, axis=1)
        deltas = np.diff(positions, axis=0)
        speeds = np.linalg.norm(deltas, axis=1)
        headings = np.arctan2(deltas[:, 1], deltas[:, 0])
        expected_heading = math.atan2(float(beta_y[1]), float(beta_x[1]))
        heading_errors = np.asarray(
            [_angle_difference(value, expected_heading) for value in headings]
        )
        accelerations = np.abs(np.diff(speeds))
        available = group[group["beacon_available"]]
        disagreements = np.hypot(
            available["radar_x"] - available["beacon_x"],
            available["radar_y"] - available["beacon_y"],
        ).to_numpy(dtype=float)
        expected_speed = float(np.median(speeds))
        last_x, last_y = positions[-1]
        profiles[str(track_id)] = TrackProfile(
            track_id=str(track_id),
            domain=str(group.iloc[0]["domain"]),
            beacon_sensor=str(group.iloc[0]["beacon_sensor"]),
            intercept_x=float(beta_x[0]),
            intercept_y=float(beta_y[0]),
            velocity_x=float(beta_x[1]),
            velocity_y=float(beta_y[1]),
            expected_speed=expected_speed,
            position_scale=_robust_scale(residual_distance, 0.20),
            speed_scale=_robust_scale(speeds, max(0.05, expected_speed * 0.03)),
            heading_scale=_robust_scale(heading_errors, math.radians(2.0)),
            disagreement_scale=_robust_scale(disagreements, 0.10),
            acceleration_scale=_robust_scale(
                accelerations,
                max(0.05, expected_speed * 0.03),
            ),
            last_x=float(last_x),
            last_y=float(last_y),
            last_speed=expected_speed,
        )
    return profiles


def score_stream(
    frame: pd.DataFrame,
    profiles: dict[str, TrackProfile],
    *,
    threshold: float = 4.0,
) -> pd.DataFrame:
    alerts: list[dict[str, Any]] = []
    test = frame[~frame["warmup"]].sort_values(["timestamp", "track_id"])
    for _, row in test.iterrows():
        profile = profiles[str(row["track_id"])]
        x, y = _fused_position(row)
        timestamp = int(row["timestamp"])
        delta_x = x - profile.last_x
        delta_y = y - profile.last_y
        speed = math.hypot(delta_x, delta_y)
        heading = math.atan2(delta_y, delta_x)
        expected_heading = math.atan2(
            profile.velocity_y,
            profile.velocity_x,
        )
        expected_x = profile.intercept_x + profile.velocity_x * timestamp
        expected_y = profile.intercept_y + profile.velocity_y * timestamp
        route_score = (
            math.hypot(x - expected_x, y - expected_y)
            / profile.position_scale
        )
        speed_score = (
            abs(speed - profile.expected_speed) / profile.speed_scale
        )
        heading_score = (
            _angle_difference(heading, expected_heading)
            / profile.heading_scale
        )
        acceleration_score = (
            abs(speed - profile.last_speed) / profile.acceleration_scale
        )
        if bool(row["beacon_available"]):
            profile.missing_streak = 0
            disagreement_score = (
                math.hypot(
                    float(row["radar_x"]) - float(row["beacon_x"]),
                    float(row["radar_y"]) - float(row["beacon_y"]),
                )
                / profile.disagreement_scale
            )
        else:
            profile.missing_streak += 1
            disagreement_score = 0.0
        missing_score = profile.missing_streak / 1.5
        components = {
            "route_deviation": route_score,
            "speed_anomaly": speed_score,
            "heading_change": heading_score,
            "acceleration": acceleration_score,
            "sensor_disagreement": disagreement_score,
            "beacon_loss": missing_score,
        }
        reason, score = max(components.items(), key=lambda item: item[1])
        alert = score >= threshold
        exceeded = {
            name for name, value in components.items() if value >= threshold
        }
        behavioral_reasons = {
            "route_deviation",
            "speed_anomaly",
            "heading_change",
            "acceleration",
        }
        source_reasons = {"sensor_disagreement", "beacon_loss"}
        has_behavioral = bool(exceeded & behavioral_reasons)
        has_source = bool(exceeded & source_reasons)
        if alert and has_behavioral and has_source:
            alert_category = "combined"
        elif alert and has_behavioral:
            alert_category = "behavioral"
        elif alert and has_source:
            alert_category = "source_integrity"
        else:
            alert_category = ""
        threat_candidate = bool(
            alert and alert_category in {"behavioral", "combined"}
        )
        if not alert:
            review_priority = ""
        elif alert_category == "combined" or score >= threshold * 1.5:
            review_priority = "high"
        elif alert_category == "behavioral":
            review_priority = "medium"
        else:
            review_priority = "low"
        confidence = (
            float(1.0 - math.exp(-(score - threshold + 1.0) / 2.5))
            if alert
            else float(max(0.0, score / threshold) * 0.49)
        )
        baseline_score = max(speed_score, heading_score)
        alerts.append(
            {
                "timestamp": timestamp,
                "track_id": profile.track_id,
                "domain": profile.domain,
                "true_anomaly": bool(row["true_anomaly"]),
                "anomaly_type": str(row["anomaly_type"]),
                "event_start": int(row["event_start"]),
                "alert": alert,
                "alert_category": alert_category,
                "review_priority": review_priority,
                "threat_candidate": threat_candidate,
                "confidence": min(0.999, confidence),
                "reason": reason if alert else "",
                "score": score,
                "baseline_alert": baseline_score >= threshold,
                "baseline_score": baseline_score,
                "state_bytes": profile.algorithmic_state_bytes,
            }
        )
        profile.last_x = x
        profile.last_y = y
        profile.last_speed = speed
    return pd.DataFrame(alerts)


def _binary_metrics(actual: pd.Series, predicted: pd.Series) -> dict[str, float]:
    truth = actual.astype(bool).to_numpy()
    guess = predicted.astype(bool).to_numpy()
    tp = int(np.sum(truth & guess))
    fp = int(np.sum(~truth & guess))
    fn = int(np.sum(truth & ~guess))
    tn = int(np.sum(~truth & ~guess))
    precision = tp / (tp + fp) if tp + fp else 0.0
    recall = tp / (tp + fn) if tp + fn else 0.0
    f1 = (
        2.0 * precision * recall / (precision + recall)
        if precision + recall
        else 0.0
    )
    return {
        "true_positives": tp,
        "false_positives": fp,
        "false_negatives": fn,
        "true_negatives": tn,
        "precision": precision,
        "recall": recall,
        "f1": f1,
        "false_alerts_per_10000_normal_points": (
            fp / max(1, fp + tn) * 10_000.0
        ),
    }


def evaluate_alerts(alerts: pd.DataFrame) -> dict[str, Any]:
    detector = _binary_metrics(alerts["true_anomaly"], alerts["alert"])
    threat_candidate = _binary_metrics(
        alerts["true_anomaly"],
        alerts["threat_candidate"],
    )
    baseline = _binary_metrics(
        alerts["true_anomaly"],
        alerts["baseline_alert"],
    )
    event_rows = alerts[alerts["true_anomaly"]].copy()
    event_group_columns = ["track_id", "event_start"]
    if "scenario" in event_rows.columns:
        event_group_columns.insert(0, "scenario")
    event_delays: list[int] = []
    detected_events = 0
    events = 0
    for _, group in event_rows.groupby(event_group_columns):
        events += 1
        detected = group[group["alert"]]
        if not detected.empty:
            detected_events += 1
            event_delays.append(
                int(detected["timestamp"].min() - group["event_start"].iloc[0])
            )
    alert_rows = alerts[alerts["alert"]]
    source_integrity_rows = alerts[
        alerts["alert_category"].eq("source_integrity")
    ]
    behavioral_rows = alerts[
        alerts["alert_category"].eq("behavioral")
    ]
    combined_rows = alerts[alerts["alert_category"].eq("combined")]
    class_metrics: dict[str, dict[str, Any]] = {}
    for anomaly_type in ANOMALY_TYPES:
        class_truth = alerts["anomaly_type"].eq(anomaly_type)
        class_result = _binary_metrics(class_truth, alerts["alert"])
        class_events = event_rows[event_rows["anomaly_type"].eq(anomaly_type)]
        class_delays: list[int] = []
        class_detected = 0
        class_event_count = 0
        for _, group in class_events.groupby(event_group_columns):
            class_event_count += 1
            detected = group[group["alert"]]
            if not detected.empty:
                class_detected += 1
                class_delays.append(
                    int(
                        detected["timestamp"].min()
                        - group["event_start"].iloc[0]
                    )
                )
        class_metrics[anomaly_type] = {
            **class_result,
            "event_count": class_event_count,
            "detected_events": class_detected,
            "event_recall": (
                class_detected / class_event_count
                if class_event_count
                else 0.0
            ),
            "median_detection_delay_steps": (
                float(np.median(class_delays)) if class_delays else None
            ),
            "threat_candidate_point_recall": float(
                alerts.loc[class_truth, "threat_candidate"].mean()
            ),
        }
    return {
        "detector": detector,
        "threat_candidate": threat_candidate,
        "baseline": baseline,
        "event_count": events,
        "detected_events": detected_events,
        "event_recall": detected_events / events if events else 0.0,
        "median_detection_delay_steps": (
            float(np.median(event_delays)) if event_delays else None
        ),
        "explanation_coverage": (
            float((alert_rows["reason"].str.len() > 0).mean())
            if not alert_rows.empty
            else 0.0
        ),
        "maximum_algorithmic_state_bytes_per_track": int(
            alerts["state_bytes"].max()
        ),
        "alert_category_counts": {
            "source_integrity": int(len(source_integrity_rows)),
            "behavioral": int(len(behavioral_rows)),
            "combined": int(len(combined_rows)),
        },
        "class_metrics": class_metrics,
    }


def select_threshold(
    frames: list[pd.DataFrame],
    candidates: list[float],
    *,
    false_alert_cap_per_10000: float,
) -> dict[str, Any]:
    rows: list[dict[str, float]] = []
    for threshold in candidates:
        scenario_metrics = []
        for frame in frames:
            alerts = score_stream(
                frame,
                copy.deepcopy(fit_profiles(frame)),
                threshold=threshold,
            )
            scenario_metrics.append(evaluate_alerts(alerts)["detector"])
        f1_mean = float(np.mean([row["f1"] for row in scenario_metrics]))
        false_alert_mean = float(
            np.mean(
                [
                    row["false_alerts_per_10000_normal_points"]
                    for row in scenario_metrics
                ]
            )
        )
        rows.append(
            {
                "threshold": float(threshold),
                "f1_mean": f1_mean,
                "false_alerts_per_10000_mean": false_alert_mean,
            }
        )
    eligible = [
        row
        for row in rows
        if row["false_alerts_per_10000_mean"]
        <= false_alert_cap_per_10000
    ]
    pool = eligible or rows
    selected = max(
        pool,
        key=lambda row: (
            row["f1_mean"],
            -row["false_alerts_per_10000_mean"],
            row["threshold"],
        ),
    )
    return {
        "selected_threshold": selected["threshold"],
        "false_alert_cap_per_10000": false_alert_cap_per_10000,
        "candidate_results": rows,
        "selection_rule": (
            "maximize mean development F1 subject to the false-alert cap; "
            "if no threshold satisfies the cap, maximize F1 and then minimize "
            "false alerts"
        ),
    }


def _git_state() -> dict[str, Any]:
    try:
        commit = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=ROOT,
            capture_output=True,
            text=True,
            check=True,
        ).stdout.strip()
        dirty = bool(
            subprocess.run(
                ["git", "status", "--short"],
                cwd=ROOT,
                capture_output=True,
                text=True,
                check=True,
            ).stdout.strip()
        )
        return {"commit": commit, "dirty": dirty}
    except Exception as exc:
        return {"error": str(exc)}


def _write_manifest(run_dir: Path) -> Path:
    files: dict[str, dict[str, Any]] = {}
    for path in sorted(run_dir.iterdir()):
        if path.is_file() and path.name != "manifest.sha256.json":
            files[path.name] = {
                "sha256": sha256_file(path),
                "bytes": path.stat().st_size,
            }
    manifest_path = run_dir / "manifest.sha256.json"
    manifest_path.write_text(
        json.dumps(
            {
                "schema": "harbor_sentinel_manifest_v1",
                "generated_utc": utc_iso(),
                "files": files,
            },
            indent=2,
        ),
        encoding="utf-8",
    )
    return manifest_path


def _append_ledger(entry: dict[str, Any]) -> None:
    LEDGER.parent.mkdir(parents=True, exist_ok=True)
    previous_hash = ""
    if LEDGER.exists():
        lines = [
            line
            for line in LEDGER.read_text(encoding="utf-8").splitlines()
            if line.strip()
        ]
        if lines:
            previous_hash = json.loads(lines[-1])["entry_sha256"]
    payload = {**entry, "previous_entry_sha256": previous_hash}
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    payload["entry_sha256"] = hashlib.sha256(encoded.encode()).hexdigest()
    with LEDGER.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(payload) + "\n")


def run(args: argparse.Namespace) -> Path:
    run_tag = args.output_tag or utc_tag()
    run_dir = OUT_ROOT / run_tag
    run_dir.mkdir(parents=True, exist_ok=False)
    scenario_rows: list[dict[str, Any]] = []
    all_alerts: list[pd.DataFrame] = []
    for scenario in range(args.scenarios):
        seed = args.seed + scenario * 10_007
        frame = simulate_scenario(
            seed=seed,
            tracks=args.tracks,
            warmup_steps=args.warmup_steps,
            test_steps=args.test_steps,
            anomaly_fraction=args.anomaly_fraction,
        )
        profiles = fit_profiles(frame)
        alerts = score_stream(frame, profiles, threshold=args.threshold)
        metrics = evaluate_alerts(alerts)
        scenario_rows.append(
            {
                "scenario": scenario,
                "seed": seed,
                "precision": metrics["detector"]["precision"],
                "recall": metrics["detector"]["recall"],
                "f1": metrics["detector"]["f1"],
                "false_alerts_per_10000": metrics["detector"][
                    "false_alerts_per_10000_normal_points"
                ],
                "baseline_f1": metrics["baseline"]["f1"],
                "event_recall": metrics["event_recall"],
                "median_detection_delay_steps": metrics[
                    "median_detection_delay_steps"
                ],
                "explanation_coverage": metrics["explanation_coverage"],
                "maximum_state_bytes": metrics[
                    "maximum_algorithmic_state_bytes_per_track"
                ],
            }
        )
        alerts.insert(0, "scenario", scenario)
        all_alerts.append(alerts)
    scenario_frame = pd.DataFrame(scenario_rows)
    alert_frame = pd.concat(all_alerts, ignore_index=True)
    scenario_frame.to_csv(run_dir / "scenario_summary.csv", index=False)
    alert_frame.to_csv(run_dir / "alerts.csv", index=False)

    summary = {
        "schema": "harbor_sentinel_synthetic_benchmark_v1",
        "run_utc": run_tag,
        "generated_utc": utc_iso(),
        "evidence_boundary": (
            "Synthetic software benchmark only; no operational sensor, harbor, "
            "SSDS, or field-validation claim."
        ),
        "configuration": {
            "scenarios": args.scenarios,
            "tracks_per_scenario": args.tracks,
            "warmup_steps": args.warmup_steps,
            "test_steps": args.test_steps,
            "anomaly_fraction": args.anomaly_fraction,
            "threshold": args.threshold,
            "seed": args.seed,
            "anomaly_types": list(ANOMALY_TYPES),
        },
        "aggregate": {
            "precision_mean": float(scenario_frame["precision"].mean()),
            "precision_min": float(scenario_frame["precision"].min()),
            "recall_mean": float(scenario_frame["recall"].mean()),
            "recall_min": float(scenario_frame["recall"].min()),
            "f1_mean": float(scenario_frame["f1"].mean()),
            "f1_min": float(scenario_frame["f1"].min()),
            "baseline_f1_mean": float(scenario_frame["baseline_f1"].mean()),
            "f1_lift_over_baseline_pct": float(
                (
                    scenario_frame["f1"].mean()
                    - scenario_frame["baseline_f1"].mean()
                )
                / max(1e-12, scenario_frame["baseline_f1"].mean())
                * 100.0
            ),
            "event_recall_mean": float(
                scenario_frame["event_recall"].mean()
            ),
            "median_detection_delay_steps": float(
                scenario_frame["median_detection_delay_steps"].median()
            ),
            "false_alerts_per_10000_mean": float(
                scenario_frame["false_alerts_per_10000"].mean()
            ),
            "explanation_coverage_mean": float(
                scenario_frame["explanation_coverage"].mean()
            ),
            "maximum_algorithmic_state_bytes_per_track": int(
                scenario_frame["maximum_state_bytes"].max()
            ),
        },
        "platform": platform.platform(),
        "python": sys.version,
        "git": _git_state(),
    }
    summary_path = run_dir / "summary.json"
    summary_path.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    aggregate = summary["aggregate"]
    (run_dir / "SCORECARD.md").write_text(
        "\n".join(
            [
                "# HarborSentinel Synthetic Scorecard",
                "",
                f"Run UTC: `{run_tag}`",
                "",
                "## Evidence Boundary",
                "",
                summary["evidence_boundary"],
                "",
                "## Aggregate Results",
                "",
                f"- Scenarios: {args.scenarios}",
                f"- Tracks per scenario: {args.tracks}",
                f"- Mean precision: {aggregate['precision_mean']:.3f}",
                f"- Mean recall: {aggregate['recall_mean']:.3f}",
                f"- Mean F1: {aggregate['f1_mean']:.3f}",
                f"- Mean baseline F1: {aggregate['baseline_f1_mean']:.3f}",
                f"- F1 lift over baseline: {aggregate['f1_lift_over_baseline_pct']:.1f}%",
                f"- Mean event recall: {aggregate['event_recall_mean']:.3f}",
                "- Median detection delay: "
                f"{aggregate['median_detection_delay_steps']:.1f} steps",
                "- Mean false alerts per 10,000 normal points: "
                f"{aggregate['false_alerts_per_10000_mean']:.1f}",
                "- Explanation coverage: "
                f"{aggregate['explanation_coverage_mean']:.3f}",
                "- Maximum compact state per track: "
                f"{aggregate['maximum_algorithmic_state_bytes_per_track']} bytes",
                "",
                "## Grant Relevance",
                "",
                "The prototype maintains compact per-track state, fuses beacon "
                "and radar-like observations, emits a reason and confidence for "
                "each alert, and requires no retained historical database during "
                "streaming inference. Operational claims require representative "
                "sensor data, integration testing, and independent evaluation.",
                "",
            ]
        ),
        encoding="utf-8",
    )
    manifest_path = _write_manifest(run_dir)
    _append_ledger(
        {
            "run_utc": run_tag,
            "generated_utc": summary["generated_utc"],
            "scenarios": args.scenarios,
            "f1_mean": aggregate["f1_mean"],
            "manifest_sha256": sha256_file(manifest_path),
            "summary_sha256": sha256_file(summary_path),
        }
    )
    (OUT_ROOT / "latest.txt").write_text(run_tag + "\n", encoding="utf-8")
    return run_dir


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Run the HarborSentinel synthetic pattern-of-life benchmark."
    )
    parser.add_argument("--output-tag", default="")
    parser.add_argument("--scenarios", type=int, default=30)
    parser.add_argument("--tracks", type=int, default=24)
    parser.add_argument("--warmup-steps", type=int, default=120)
    parser.add_argument("--test-steps", type=int, default=180)
    parser.add_argument("--anomaly-fraction", type=float, default=0.75)
    parser.add_argument("--threshold", type=float, default=8.0)
    parser.add_argument("--seed", type=int, default=20260613)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    run_dir = run(args)
    summary = json.loads((run_dir / "summary.json").read_text(encoding="utf-8"))
    print(json.dumps({"run_dir": str(run_dir), **summary["aggregate"]}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
