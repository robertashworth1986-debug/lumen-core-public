from __future__ import annotations

import importlib.util
import json
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
VERIFIER_PATH = (
    ROOT / "code" / "ops" / "VERIFY_EIA_GRID_HOURLY_HYBRID_V3_CUSTODY.py"
)
BUILDER_PATH = ROOT / "tests" / "fixture_builders" / "eia_v3_custody_fixture.py"
POLICY_PATH = (
    ROOT / "config" / "eia_grid_hourly_hybrid_confirmation_custody_watchdog_v1.json"
)
SPEC_PATH = (
    ROOT
    / "tests"
    / "fixtures"
    / "eia_v3_custody_watchdog"
    / "valid_accumulating_spec.json"
)


def load_module(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


VERIFIER = load_module(VERIFIER_PATH, "eia_v3_custody_watchdog")
BUILDER = load_module(BUILDER_PATH, "eia_v3_custody_fixture_builder")


class EiaV3CustodyWatchdogTests(unittest.TestCase):
    def setUp(self) -> None:
        self.policy = json.loads(POLICY_PATH.read_text(encoding="utf-8"))
        self.spec = json.loads(SPEC_PATH.read_text(encoding="utf-8"))

    def verify_scenario(
        self,
        scenario: str = "valid",
        *,
        as_of_utc: str | None = None,
        policy_path: Path = POLICY_PATH,
    ) -> dict:
        with tempfile.TemporaryDirectory() as temporary:
            fixture = Path(temporary) / "fixture"
            BUILDER.build_fixture(fixture, self.spec, self.policy, scenario=scenario)
            return VERIFIER.verify_snapshot(
                input_dir=fixture,
                as_of_utc=as_of_utc or self.spec["as_of_utc"],
                policy_path=policy_path,
            )

    @staticmethod
    def reason_codes(receipt: dict) -> set[str]:
        return {reason["code"] for reason in receipt["reasons"]}

    def test_valid_accumulating_state_is_ok_and_performance_free(self) -> None:
        first = self.verify_scenario()
        second = self.verify_scenario()
        self.assertEqual(first, second)
        self.assertEqual(first["classification"], "OK")
        self.assertTrue(first["custody_valid"])
        self.assertEqual(first["counts"]["prediction_panels"], 3)
        self.assertEqual(first["counts"]["settlement_panels"], 2)
        self.assertEqual(first["counts"]["unsettled_panels"], 1)
        self.assertFalse(first["sample_readiness"]["operational_shakeout_168_hours"])
        self.assertFalse(first["sample_readiness"]["confirmatory_sample_ready"])
        self.assertFalse(first["automatic_promotion_allowed"])
        self.assertFalse(first["performance_evaluated"])
        self.assertFalse(first["performance_fields_exposed"])
        rendered = json.dumps(first, sort_keys=True).casefold()
        for forbidden in (
            "actual_mwh",
            "prediction_mwh",
            "absolute_error",
            "scaled_error",
            "model_score",
            "win_rate",
        ):
            self.assertNotIn(forbidden, rendered)

    def test_broken_prediction_chain_fails_closed(self) -> None:
        receipt = self.verify_scenario("broken_chain")
        self.assertEqual(receipt["classification"], "FAIL")
        self.assertIn("BROKEN_PREDICTION_CHAIN", self.reason_codes(receipt))

    def test_duplicate_prediction_period_fails_closed(self) -> None:
        receipt = self.verify_scenario("duplicate_period")
        self.assertEqual(receipt["classification"], "FAIL")
        self.assertIn("DUPLICATE_PREDICTION_TARGET", self.reason_codes(receipt))

    def test_duplicate_settlement_period_fails_closed(self) -> None:
        receipt = self.verify_scenario("duplicate_settlement_period")
        self.assertEqual(receipt["classification"], "FAIL")
        self.assertIn("DUPLICATE_SETTLEMENT_TARGET", self.reason_codes(receipt))

    def test_target_before_first_allowed_period_fails_closed(self) -> None:
        receipt = self.verify_scenario("before_first_allowed")
        self.assertEqual(receipt["classification"], "FAIL")
        self.assertIn(
            "TARGET_BEFORE_FIRST_ALLOWED_PERIOD", self.reason_codes(receipt)
        )

    def test_missing_target_period_is_exact_warn_not_promotion(self) -> None:
        receipt = self.verify_scenario("missing_target_period")
        self.assertEqual(receipt["classification"], "WARN")
        self.assertEqual(receipt["counts"]["missing_prediction_periods"], 1)
        self.assertIn("MISSING_PREDICTION_TARGET_PERIODS", self.reason_codes(receipt))
        self.assertFalse(receipt["automatic_promotion_allowed"])

    def test_missing_authority_fails_closed(self) -> None:
        receipt = self.verify_scenario("missing_authority")
        self.assertEqual(receipt["classification"], "FAIL")
        self.assertIn("MISSING_OR_CHANGED_AUTHORITY", self.reason_codes(receipt))

    def test_invalid_lead_time_fails_closed(self) -> None:
        receipt = self.verify_scenario("invalid_lead")
        self.assertEqual(receipt["classification"], "FAIL")
        self.assertIn("INVALID_SEAL_LEAD", self.reason_codes(receipt))

    def test_actual_present_at_seal_fails_closed(self) -> None:
        receipt = self.verify_scenario("actual_present_at_seal")
        self.assertEqual(receipt["classification"], "FAIL")
        self.assertIn("ACTUAL_PRESENT_AT_SEAL", self.reason_codes(receipt))

    def test_backfill_fails_closed(self) -> None:
        receipt = self.verify_scenario("backfill")
        self.assertEqual(receipt["classification"], "FAIL")
        self.assertIn("BACKFILL_DETECTED", self.reason_codes(receipt))

    def test_stale_status_and_receipt_are_explicit_but_not_corruption(self) -> None:
        receipt = self.verify_scenario(
            as_of_utc="2026-08-03T00:30:00Z",
        )
        self.assertEqual(receipt["classification"], "STALE")
        self.assertTrue(receipt["custody_valid"])
        self.assertIn("STATUS_STALE", self.reason_codes(receipt))
        self.assertIn("OPERATIONAL_RECEIPT_STALE", self.reason_codes(receipt))

    def test_count_mismatch_fails_closed(self) -> None:
        receipt = self.verify_scenario("count_mismatch")
        self.assertEqual(receipt["classification"], "FAIL")
        self.assertIn("COUNT_MISMATCH", self.reason_codes(receipt))

    def test_score_leakage_fails_before_receipt_can_echo_values(self) -> None:
        receipt = self.verify_scenario("score_leakage")
        self.assertEqual(receipt["classification"], "FAIL")
        self.assertIn("SCORE_LEAKAGE_DETECTED", self.reason_codes(receipt))
        self.assertNotIn("0.5", json.dumps(receipt, sort_keys=True))

    def test_parent_v2_binding_mismatch_fails_closed(self) -> None:
        receipt = self.verify_scenario("parent_binding_mismatch")
        self.assertEqual(receipt["classification"], "FAIL")
        self.assertIn(
            "SETTLEMENT_PREDICTION_BINDING_MISMATCH", self.reason_codes(receipt)
        )

    def test_automatic_promotion_flag_fails_closed(self) -> None:
        receipt = self.verify_scenario("automatic_promotion")
        self.assertEqual(receipt["classification"], "FAIL")
        self.assertIn("AUTOMATIC_PROMOTION_ENABLED", self.reason_codes(receipt))

    def test_unsettled_backlog_and_lag_are_public_safe_warns(self) -> None:
        spec = dict(self.spec)
        spec["prediction_panel_count"] = 5
        spec["settlement_panel_count"] = 2
        spec["generated_utc"] = "2026-08-02T20:15:00Z"
        with tempfile.TemporaryDirectory() as temporary:
            fixture = Path(temporary) / "fixture"
            BUILDER.build_fixture(fixture, spec, self.policy)
            receipt = VERIFIER.verify_snapshot(
                input_dir=fixture,
                as_of_utc="2026-08-02T20:30:00Z",
                policy_path=POLICY_PATH,
            )
        self.assertEqual(receipt["classification"], "WARN")
        self.assertIn("UNSETTLED_BACKLOG", self.reason_codes(receipt))
        self.assertIn("UNSETTLED_LAG", self.reason_codes(receipt))
        self.assertEqual(receipt["counts"]["unsettled_panels"], 3)

    def test_weakened_threshold_policy_fails_closed(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            fixture = root / "fixture"
            BUILDER.build_fixture(fixture, self.spec, self.policy)
            weakened = json.loads(json.dumps(self.policy))
            weakened["protocol_contract"]["minimum_seal_lead_seconds"] = 3599
            weakened_path = root / "weakened-policy.json"
            weakened_path.write_text(
                json.dumps(weakened, indent=2, sort_keys=True) + "\n",
                encoding="utf-8",
            )
            receipt = VERIFIER.verify_snapshot(
                input_dir=fixture,
                as_of_utc=self.spec["as_of_utc"],
                policy_path=weakened_path,
            )
        self.assertEqual(receipt["classification"], "FAIL")
        self.assertIn("POLICY_DRIFT_OR_WEAKENING", self.reason_codes(receipt))

    def test_sample_readiness_thresholds_are_exact_and_non_promoting(self) -> None:
        readiness_167 = VERIFIER._sample_readiness(167, 90, self.policy)
        readiness_168 = VERIFIER._sample_readiness(168, 90, self.policy)
        readiness_719 = VERIFIER._sample_readiness(719, 90, self.policy)
        readiness_720 = VERIFIER._sample_readiness(720, 90, self.policy)
        readiness_2159 = VERIFIER._sample_readiness(2159, 90, self.policy)
        readiness_2160_89 = VERIFIER._sample_readiness(2160, 89, self.policy)
        readiness_2160_90 = VERIFIER._sample_readiness(2160, 90, self.policy)
        self.assertFalse(readiness_167["operational_shakeout_168_hours"])
        self.assertTrue(readiness_168["operational_shakeout_168_hours"])
        self.assertFalse(readiness_719["preliminary_720_hours"])
        self.assertTrue(readiness_720["preliminary_720_hours"])
        self.assertFalse(readiness_2159["confirmatory_2160_hours"])
        self.assertFalse(readiness_2160_89["confirmatory_sample_ready"])
        self.assertTrue(readiness_2160_90["confirmatory_sample_ready"])
        self.assertFalse(self.policy["protocol_contract"]["automatic_promotion_allowed"])

    def test_complete_day_counter_requires_all_24_distinct_utc_hours(self) -> None:
        start = datetime(2026, 8, 4, tzinfo=timezone.utc)
        complete = {
            (start + timedelta(hours=hour)).strftime("%Y-%m-%dT%H")
            for hour in range(24)
        }
        incomplete = {
            (start + timedelta(days=1, hours=hour)).strftime("%Y-%m-%dT%H")
            for hour in range(23)
        }
        self.assertEqual(VERIFIER._complete_utc_days(complete | incomplete), 1)

    def test_public_safe_summary_contains_only_operational_state(self) -> None:
        receipt = self.verify_scenario()
        summary = VERIFIER.render_summary(receipt).casefold()
        self.assertIn("classification", summary)
        self.assertIn("complete utc days", summary)
        self.assertIn("performance evaluated: `false`", summary)
        self.assertNotIn("actual_mwh", summary)
        self.assertNotIn("prediction_mwh", summary)
        self.assertNotIn("model_score", summary)


if __name__ == "__main__":
    unittest.main()
