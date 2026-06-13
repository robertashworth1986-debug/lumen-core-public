from __future__ import annotations

import sys
import unittest
from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "code"))

from harbor_sentinel_benchmark import (  # noqa: E402
    evaluate_alerts,
    fit_profiles,
    score_stream,
    select_threshold,
    simulate_scenario,
)


class HarborSentinelBenchmarkTests(unittest.TestCase):
    def test_simulation_is_reproducible(self) -> None:
        left = simulate_scenario(
            seed=3,
            tracks=6,
            warmup_steps=60,
            test_steps=80,
        )
        right = simulate_scenario(
            seed=3,
            tracks=6,
            warmup_steps=60,
            test_steps=80,
        )
        pd.testing.assert_frame_equal(left, right)

    def test_stream_emits_explanations_and_compact_state(self) -> None:
        frame = simulate_scenario(
            seed=9,
            tracks=12,
            warmup_steps=80,
            test_steps=100,
            anomaly_fraction=1.0,
        )
        alerts = score_stream(frame, fit_profiles(frame))
        metrics = evaluate_alerts(alerts)
        self.assertGreater(metrics["detected_events"], 0)
        self.assertEqual(metrics["explanation_coverage"], 1.0)
        self.assertLessEqual(
            metrics["maximum_algorithmic_state_bytes_per_track"],
            256,
        )
        self.assertIn("threat_candidate", alerts.columns)
        self.assertIn("alert_category", alerts.columns)

    def test_source_only_alert_is_not_automatically_threat_candidate(self) -> None:
        frame = simulate_scenario(
            seed=21,
            tracks=5,
            warmup_steps=80,
            test_steps=100,
            anomaly_fraction=1.0,
        )
        alerts = score_stream(frame, fit_profiles(frame))
        source_only = alerts[
            (alerts["alert_category"] == "source_integrity")
            & alerts["alert"]
        ]
        self.assertFalse(source_only.empty)
        self.assertFalse(source_only["threat_candidate"].any())

    def test_beacon_silence_produces_beacon_loss_alert(self) -> None:
        frame = simulate_scenario(
            seed=21,
            tracks=5,
            warmup_steps=80,
            test_steps=100,
            anomaly_fraction=1.0,
        )
        alerts = score_stream(frame, fit_profiles(frame))
        silence = alerts[
            (alerts["anomaly_type"] == "beacon_silence")
            & (alerts["alert"])
        ]
        self.assertFalse(silence.empty)
        self.assertIn("beacon_loss", set(silence["reason"]))

    def test_nominal_tracks_are_never_labeled_anomalous(self) -> None:
        frame = simulate_scenario(
            seed=31,
            tracks=10,
            warmup_steps=60,
            test_steps=80,
            anomaly_fraction=0.5,
        )
        nominal_ids = set(
            frame.loc[frame["event_start"] == -1, "track_id"].unique()
        )
        self.assertTrue(nominal_ids)
        nominal = frame[frame["track_id"].isin(nominal_ids)]
        self.assertFalse(nominal["true_anomaly"].any())

    def test_evaluation_reports_every_anomaly_class(self) -> None:
        frame = simulate_scenario(
            seed=71,
            tracks=12,
            warmup_steps=80,
            test_steps=100,
            anomaly_fraction=1.0,
        )
        metrics = evaluate_alerts(
            score_stream(frame, fit_profiles(frame), threshold=8.0)
        )
        self.assertEqual(
            set(metrics["class_metrics"]),
            {
                "route_deviation",
                "loiter",
                "speed_burst",
                "sharp_turn",
                "beacon_silence",
                "beacon_spoof",
            },
        )

    def test_development_threshold_selection_is_deterministic(self) -> None:
        frames = [
            simulate_scenario(
                seed=seed,
                tracks=12,
                warmup_steps=70,
                test_steps=90,
            )
            for seed in (101, 102, 103)
        ]
        left = select_threshold(
            frames,
            [6.0, 8.0, 10.0],
            false_alert_cap_per_10000=150.0,
        )
        right = select_threshold(
            frames,
            [6.0, 8.0, 10.0],
            false_alert_cap_per_10000=150.0,
        )
        self.assertEqual(left, right)

    def test_benign_dropout_is_not_labeled_as_ground_truth_anomaly(self) -> None:
        frame = simulate_scenario(
            seed=91,
            tracks=8,
            warmup_steps=60,
            test_steps=80,
            anomaly_fraction=0.0,
            benign_beacon_dropout_probability=0.15,
        )
        self.assertFalse(frame["true_anomaly"].any())
        self.assertTrue((~frame["beacon_available"]).any())

    def test_benign_dropout_bursts_remain_nominal_ground_truth(self) -> None:
        frame = simulate_scenario(
            seed=92,
            tracks=8,
            warmup_steps=60,
            test_steps=80,
            anomaly_fraction=0.0,
            benign_beacon_dropout_burst_fraction=1.0,
        )
        self.assertFalse(frame["true_anomaly"].any())
        test = frame[~frame["warmup"]]
        missing_by_track = (
            (~test["beacon_available"]).groupby(test["track_id"]).sum()
        )
        self.assertTrue((missing_by_track >= 18).all())


if __name__ == "__main__":
    unittest.main()
