from __future__ import annotations

import math
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "code"))

from hybrid_edge_v7 import (  # noqa: E402
    benjamini_hochberg,
    discover_datasets,
    evaluate_series_core,
    expanding_folds,
    iaaft_surrogate,
    phase_stability,
    select_past_only_model,
)


class HybridEdgeV7Tests(unittest.TestCase):
    def test_expanding_folds_are_chronological_and_untouched(self) -> None:
        folds = expanding_folds(
            200,
            n_splits=5,
            test_size=20,
            min_train=60,
        )
        self.assertEqual(len(folds), 5)
        self.assertEqual(folds[0].train_end, 100)
        self.assertEqual(folds[-1].test_end, 200)
        for fold in folds:
            self.assertLessEqual(fold.train_end, fold.test_start)
            self.assertEqual(fold.test_end - fold.test_start, 20)

    def test_phase_stability_distinguishes_stable_cycle(self) -> None:
        t = np.arange(240, dtype=float)
        stable = np.sin(2.0 * np.pi * t / 12.0)
        rng = np.random.default_rng(4)
        noise = rng.normal(size=240)
        stable_metric = phase_stability(stable)
        noise_metric = phase_stability(noise)
        self.assertGreater(stable_metric["phase_stability"], 0.9)
        self.assertGreater(
            stable_metric["spectral_concentration"],
            noise_metric["spectral_concentration"],
        )

    def test_iaaft_preserves_distribution_and_approximately_spectrum(self) -> None:
        rng = np.random.default_rng(8)
        values = rng.standard_t(df=5, size=256)
        surrogate = iaaft_surrogate(values, rng=np.random.default_rng(9))
        np.testing.assert_allclose(np.sort(values), np.sort(surrogate))
        original_power = np.abs(np.fft.rfft(values - values.mean()))
        surrogate_power = np.abs(np.fft.rfft(surrogate - surrogate.mean()))
        correlation = float(np.corrcoef(original_power, surrogate_power)[0, 1])
        self.assertGreater(correlation, 0.95)

    def test_bh_adjustment_is_monotone_in_rank(self) -> None:
        adjusted = benjamini_hochberg([0.01, 0.04, 0.03, None])
        self.assertAlmostEqual(float(adjusted[0]), 0.03)
        self.assertAlmostEqual(float(adjusted[1]), 0.04)
        self.assertAlmostEqual(float(adjusted[2]), 0.04)
        self.assertIsNone(adjusted[3])

    def test_selector_uses_only_train_and_returns_known_model(self) -> None:
        t = np.arange(180, dtype=float)
        values = (
            10.0
            + 0.02 * t
            + 2.0 * np.sin(2.0 * math.pi * t / 12.0)
        )
        selection = select_past_only_model(values[:140], seed=77)
        self.assertIn(
            selection["selected_model"],
            {
                "naive",
                "seasonal_naive",
                "ridge_ar_12",
                "ridge_ar_24",
                "mlp_ar_24",
                "harmonic_ridge",
                "sqrt_recency_harmonic",
                "ridge_ar_12_harmonic_residual",
                "ridge_ar_24_harmonic_residual",
            },
        )
        self.assertIn("phase_stability", selection)
        self.assertIn("inner_scores", selection)

    def test_abstained_folds_reuse_exact_baseline_forecast(self) -> None:
        rng = np.random.default_rng(44)
        values = np.cumsum(rng.normal(size=180))
        result = evaluate_series_core(
            values,
            n_splits=5,
            test_size=20,
            min_train=60,
            seed=91,
        )
        predictions = result["predictions"]
        abstained_folds = {
            int(row["fold"])
            for row in result["folds"]
            if row["selected_model"] == row["baseline_model"]
        }
        self.assertTrue(abstained_folds)
        for row in predictions:
            if int(row["fold"]) in abstained_folds:
                self.assertEqual(
                    row["baseline_prediction"],
                    row["hybrid_prediction"],
                )

    def test_correction_governor_bounds_advanced_forecast(self) -> None:
        values = np.arange(180, dtype=float)
        selection = {
            "baseline_model": "naive",
            "advanced_model": "harmonic_ridge",
            "selected_model": "harmonic_ridge",
            "advanced_allowed": True,
            "phase_stability": 0.9,
            "spectral_concentration": 0.5,
            "dominant_period": 12.0,
            "advanced_inner_gain_pct": 10.0,
            "advanced_inner_fold_win_rate": 1.0,
            "advanced_recent_inner_gain_pct": 10.0,
            "advanced_median_inner_gain_pct": 10.0,
        }

        def fake_forecast(
            model_name: str,
            train: np.ndarray,
            horizon: int,
            *,
            seed: int,
        ) -> np.ndarray:
            value = 1000.0 if model_name == "harmonic_ridge" else 0.0
            return np.full(horizon, value, dtype=float)

        with (
            patch("hybrid_edge_v7.select_past_only_model", return_value=selection),
            patch("hybrid_edge_v7.forecast_model", side_effect=fake_forecast),
        ):
            result = evaluate_series_core(
                values,
                n_splits=5,
                test_size=20,
                min_train=60,
                seed=12,
                correction_alpha=0.10,
                correction_clip_scale=0.50,
            )

        for row in result["predictions"]:
            self.assertLessEqual(
                abs(row["hybrid_prediction"] - row["baseline_prediction"]),
                0.05 + 1e-12,
            )

    def test_dataset_offset_selects_disjoint_round_robin_batch(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            raw_dir = Path(temp)
            for name in ("AV_A", "AV_B", "BLS_A", "BLS_B"):
                pd.DataFrame({"value": np.arange(20, dtype=float)}).to_csv(
                    raw_dir / f"{name}.csv",
                    index=False,
                )
            first = discover_datasets(
                raw_dir,
                requested=[],
                limit=2,
                offset=0,
                minimum_observations=10,
            )
            second = discover_datasets(
                raw_dir,
                requested=[],
                limit=2,
                offset=2,
                minimum_observations=10,
            )
        self.assertFalse({path.stem for path in first} & {path.stem for path in second})


if __name__ == "__main__":
    unittest.main()
