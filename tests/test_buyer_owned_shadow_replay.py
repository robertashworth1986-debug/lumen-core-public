from __future__ import annotations

import ast
import copy
import hashlib
import importlib.util
import json
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = ROOT / "code" / "ops" / "run_buyer_owned_shadow_replay.py"
SPEC = importlib.util.spec_from_file_location("shadow_replay", MODULE_PATH)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


def protocol() -> dict:
    return {
        "schema": "lumencore_buyer_owned_shadow_replay_v1",
        "version": "1.0.0",
        "run_label": "unit-test-shadow",
        "mode": "offline_replay",
        "decision_owner": "buyer decision owner",
        "primary_metric": "mae",
        "metric_direction": "lower_is_better",
        "execution_boundary": {
            "production_write_access": False,
            "actuation_allowed": False,
            "production_credentials_allowed": False,
            "recommendations_require_human_approval": True,
            "incumbent_fallback_required": True,
        },
        "acceptance": {
            "minimum_eligible_rows": 3,
            "minimum_candidate_coverage": 0.5,
            "minimum_relative_improvement": 0.1,
            "maximum_worst_row_error_increase": 0.0,
        },
        "economic_conversion": {"enabled": False},
        "claim_boundary": ["Internal replay only."],
    }


def cases() -> dict:
    return {
        "schema": "lumencore_buyer_owned_shadow_cases_v1",
        "version": "1.0.0",
        "rows": [
            {
                "row_id": "r1",
                "event_time_utc": "2026-01-01T00:00:00Z",
                "actual_available_at_utc": "2026-01-01T01:00:00Z",
                "incumbent_version": "inc-v1",
                "incumbent_output": 10.0,
                "outcome": 8.0,
            },
            {
                "row_id": "r2",
                "event_time_utc": "2026-01-01T01:00:00Z",
                "actual_available_at_utc": "2026-01-01T02:00:00Z",
                "incumbent_version": "inc-v1",
                "incumbent_output": 5.0,
                "outcome": 7.0,
            },
            {
                "row_id": "r3",
                "event_time_utc": "2026-01-01T02:00:00Z",
                "actual_available_at_utc": "2026-01-01T03:00:00Z",
                "incumbent_version": "inc-v1",
                "incumbent_output": 2.0,
                "outcome": 4.0,
            },
        ],
    }


def predictions() -> dict:
    return {
        "schema": "lumencore_buyer_owned_shadow_predictions_v1",
        "version": "1.0.0",
        "rows": [
            {
                "row_id": "r1",
                "prediction_time_utc": "2026-01-01T00:30:00Z",
                "candidate_version": "candidate-v1",
                "candidate_output": 8.0,
                "confidence": 0.9,
                "abstain": False,
                "reason": "candidate",
            },
            {
                "row_id": "r2",
                "prediction_time_utc": "2026-01-01T01:30:00Z",
                "candidate_version": "candidate-v1",
                "candidate_output": 7.0,
                "confidence": 0.8,
                "abstain": False,
                "reason": "candidate",
            },
            {
                "row_id": "r3",
                "prediction_time_utc": "2026-01-01T02:30:00Z",
                "candidate_version": "candidate-v1",
                "candidate_output": None,
                "confidence": 0.2,
                "abstain": True,
                "reason": "low confidence",
            },
        ],
    }


class BuyerOwnedShadowReplayTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.protocol_path = self.write("protocol.json", protocol())
        self.cases_path = self.write("cases.json", cases())
        self.predictions_path = self.write("predictions.json", predictions())

    def write(self, name: str, value: dict) -> Path:
        path = self.root / name
        path.write_text(json.dumps(value, sort_keys=True), encoding="utf-8")
        return path

    def evaluate(self) -> dict:
        return MODULE.evaluate_shadow_replay(
            self.protocol_path, self.cases_path, self.predictions_path
        )

    def test_deterministic_promote_receipt_and_self_hash(self) -> None:
        first = self.evaluate()
        second = self.evaluate()
        self.assertEqual(first, second)
        self.assertTrue(first["all_gates_pass"])
        self.assertEqual(first["recommended_decision"], "promote")
        claimed_hash = first.pop("receipt_sha256")
        actual_hash = hashlib.sha256(MODULE._canonical_json(first)).hexdigest()
        self.assertEqual(claimed_hash, actual_hash)

    def test_abstention_falls_back_exactly_and_stays_in_denominator(self) -> None:
        receipt = self.evaluate()
        row = next(item for item in receipt["rows"] if item["row_id"] == "r3")
        self.assertEqual(row["selected_source"], "incumbent_fallback")
        self.assertEqual(row["effective_output"], row["incumbent_output"])
        self.assertEqual(receipt["counts"]["eligible_rows"], 3)
        self.assertEqual(receipt["counts"]["abstentions"], 1)

    def test_frozen_inputs_are_not_modified(self) -> None:
        paths = [self.protocol_path, self.cases_path, self.predictions_path]
        before = [path.read_bytes() for path in paths]
        self.evaluate()
        self.assertEqual(before, [path.read_bytes() for path in paths])

    def test_prediction_at_outcome_time_fails_closed(self) -> None:
        value = predictions()
        value["rows"][0]["prediction_time_utc"] = "2026-01-01T01:00:00Z"
        self.predictions_path = self.write("predictions.json", value)
        with self.assertRaisesRegex(MODULE.ShadowReplayError, "not sealed"):
            self.evaluate()

    def test_outcome_field_in_candidate_payload_fails_closed(self) -> None:
        value = predictions()
        value["rows"][0]["outcome"] = 8.0
        self.predictions_path = self.write("predictions.json", value)
        with self.assertRaisesRegex(MODULE.ShadowReplayError, "keys mismatch"):
            self.evaluate()

    def test_missing_or_duplicate_prediction_fails_closed(self) -> None:
        missing = predictions()
        missing["rows"].pop()
        self.predictions_path = self.write("predictions.json", missing)
        with self.assertRaisesRegex(MODULE.ShadowReplayError, "missing prediction"):
            self.evaluate()
        duplicate = predictions()
        duplicate["rows"][2]["row_id"] = "r2"
        self.predictions_path = self.write("predictions.json", duplicate)
        with self.assertRaisesRegex(MODULE.ShadowReplayError, "duplicate prediction"):
            self.evaluate()

    def test_nonfinite_number_fails_closed(self) -> None:
        self.predictions_path.write_text(
            json.dumps(predictions()).replace("8.0", "NaN", 1),
            encoding="utf-8",
        )
        with self.assertRaisesRegex(MODULE.ShadowReplayError, "non-finite"):
            self.evaluate()

    def test_write_actuation_and_economics_fail_closed(self) -> None:
        for mutation, message in (
            (("execution_boundary", "production_write_access", True), "must be false"),
            (("execution_boundary", "actuation_allowed", True), "must be false"),
            (("economic_conversion", "enabled", True), "economic conversion"),
        ):
            value = protocol()
            group, key, setting = mutation
            value[group][key] = setting
            self.protocol_path = self.write("protocol.json", value)
            with self.assertRaisesRegex(MODULE.ShadowReplayError, message):
                self.evaluate()

    def test_adverse_result_is_retained_and_rejected(self) -> None:
        value = predictions()
        value["rows"][0]["candidate_output"] = 20.0
        value["rows"][1]["candidate_output"] = 20.0
        self.predictions_path = self.write("predictions.json", value)
        receipt = self.evaluate()
        self.assertFalse(receipt["all_gates_pass"])
        self.assertEqual(receipt["recommended_decision"], "reject")
        self.assertTrue(receipt["negative_result_register"])
        self.assertFalse(receipt["production_change_authorized"])

    def test_source_has_no_network_subprocess_trading_or_credential_imports(self) -> None:
        source = MODULE_PATH.read_text(encoding="utf-8")
        tree = ast.parse(source)
        imported = {
            alias.name.split(".")[0]
            for node in ast.walk(tree)
            if isinstance(node, (ast.Import, ast.ImportFrom))
            for alias in node.names
        }
        self.assertTrue(
            imported.isdisjoint(
                {"requests", "httpx", "urllib3", "socket", "subprocess", "alpaca"}
            )
        )
        lowered = source.casefold()
        for token in ("code.execution", "kraken", "api_key", "secret_key"):
            self.assertNotIn(token, lowered)

    def test_cli_writes_only_the_receipt(self) -> None:
        output = self.root / "receipt.json"
        result = MODULE.main(
            [
                "--protocol",
                str(self.protocol_path),
                "--cases",
                str(self.cases_path),
                "--predictions",
                str(self.predictions_path),
                "--output",
                str(output),
            ]
        )
        self.assertEqual(result, 0)
        receipt = json.loads(output.read_text(encoding="utf-8"))
        self.assertEqual(receipt["schema"], "lumencore_buyer_owned_shadow_receipt_v1")
        self.assertFalse(receipt["production_change_authorized"])


if __name__ == "__main__":
    unittest.main()
