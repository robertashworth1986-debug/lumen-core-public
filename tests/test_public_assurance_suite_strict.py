from __future__ import annotations

import copy
import importlib.util
import tempfile
import textwrap
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]


def load_module(name: str, relative_path: str):
    spec = importlib.util.spec_from_file_location(name, ROOT / relative_path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


STRICT = load_module(
    "public_assurance_suite_strict",
    "code/ops/run_public_assurance_suite_strict.py",
)
INDEPENDENCE = load_module(
    "external_independence_contract",
    "code/ops/validate_external_independence_contract.py",
)


class ExternalIndependenceContractTests(unittest.TestCase):
    def canonical_payload(self) -> dict:
        return INDEPENDENCE.BASE.load_docket(
            ROOT / "config" / "external_replication_docket_v1.json"
        )

    def assigned_payload(self) -> dict:
        payload = self.canonical_payload()
        payload["status"] = "preregistered"
        payload["gates"]["evaluator_assigned"] = True
        payload["independence"].update(
            {
                "evaluator_name": "Taylor Reviewer",
                "organization": "Independent Evaluation Laboratory",
                "role": "Principal evaluator",
                "relationship": "independent external evaluator",
                "conflict_disclosure": "No financial or governance relationship",
                "data_control": "Evaluator controls source access",
                "run_control": "Evaluator controls execution",
                "analysis_control": "Evaluator controls scoring and analysis",
                "publication_permission": "Evaluator may publish all outcomes",
            }
        )
        return payload

    def validate_assigned(self, payload: dict) -> dict:
        # These tests isolate the additional independence semantics. The base
        # docket's complete preregistration contract is covered separately in
        # test_external_replication_docket.py.
        with mock.patch.object(
            INDEPENDENCE.BASE,
            "validate_docket",
            return_value={"status": "preregistered"},
        ):
            return INDEPENDENCE.validate_independence_contract(payload)

    def test_unassigned_template_is_consistent_but_not_external_validation(self) -> None:
        receipt = INDEPENDENCE.validate_independence_contract(
            self.canonical_payload()
        )
        self.assertTrue(receipt["independence_contract_valid"])
        self.assertEqual(receipt["status"], "template_unassigned")
        self.assertFalse(receipt["safe_for_external_validation_claim"])

    def test_assigned_independent_evaluator_contract_is_consistent(self) -> None:
        receipt = self.validate_assigned(self.assigned_payload())
        self.assertTrue(receipt["evaluator_assignment_consistent"])

    def test_founder_affiliation_fails_closed(self) -> None:
        payload = self.assigned_payload()
        payload["independence"]["organization"] = "LumenCore Review Lab"
        with self.assertRaisesRegex(
            INDEPENDENCE.IndependenceError, "affiliation marker"
        ):
            self.validate_assigned(payload)

    def test_undisclosed_conflict_fails_closed(self) -> None:
        payload = self.assigned_payload()
        payload["independence"]["conflict_disclosure"] = "not disclosed"
        with self.assertRaisesRegex(
            INDEPENDENCE.IndependenceError, "actual disclosure"
        ):
            self.validate_assigned(payload)

    def test_founder_control_statement_fails_closed(self) -> None:
        payload = self.assigned_payload()
        payload["independence"]["run_control"] = (
            "Founder controls execution"
        )
        with self.assertRaisesRegex(
            INDEPENDENCE.IndependenceError,
            "affiliation marker|independent-laboratory control",
        ):
            self.validate_assigned(payload)


class StrictAssuranceRunnerTests(unittest.TestCase):
    def fixture_check(self, root: Path) -> dict:
        source = root / "fixture.txt"
        source.write_text("fixed source\n", encoding="utf-8")
        script = root / "check.py"
        script.write_text(
            textwrap.dedent(
                """
                import json
                print(json.dumps({"valid": True, "state": "hold"}))
                """
            ),
            encoding="utf-8",
        )
        return {
            "check_id": "fixture",
            "command": ("{python}", "check.py"),
            "sources": ("fixture.txt", "check.py"),
            "expected": {"valid": True, "state": "hold"},
        }

    def test_strict_suite_binds_pre_and_post_source_identity(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            receipt = STRICT.run_strict_suite(
                root,
                commit="a" * 40,
                checks=(self.fixture_check(root),),
                timeout_seconds=5,
            )
            self.assertTrue(receipt["valid"])
            self.assertTrue(receipt["source_pre_post_match"])
            self.assertEqual(receipt["strict_runner_version"], "1.0.0")

    def test_case_insensitive_source_collision_fails_closed(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            spec = self.fixture_check(root)
            (root / "FIXTURE.txt").write_text("other\n", encoding="utf-8")
            colliding = copy.deepcopy(spec)
            colliding["sources"] = ("fixture.txt", "FIXTURE.txt")
            with self.assertRaisesRegex(
                STRICT.StrictAssuranceError,
                "case-insensitive source-path collision",
            ):
                STRICT.run_strict_suite(
                    root,
                    checks=(colliding,),
                    timeout_seconds=5,
                )


class PublicExternalReviewSurfaceTests(unittest.TestCase):
    def test_external_review_surface_is_bounded_and_actionable(self) -> None:
        page = (ROOT / "dashboard" / "external_review.html").read_text(
            encoding="utf-8"
        )
        self.assertIn("external-replication-docket-v1", page)
        self.assertIn("Current state: HOLD / template unassigned", page)
        self.assertIn("No external evaluator", page)
        self.assertIn("run_public_assurance_suite_strict.py", page)
        self.assertNotIn("independently validated", page.casefold())

    def test_paid_offer_routes_to_external_review_protocol(self) -> None:
        page = (ROOT / "dashboard" / "proof_to_pilot.html").read_text(
            encoding="utf-8"
        )
        self.assertIn('href="/external_review.html"', page)

    def test_deploy_smoke_requires_external_review_surface(self) -> None:
        workflow = (ROOT / ".github" / "workflows" / "deploy.yml").read_text(
            encoding="utf-8"
        )
        self.assertIn("lumen-core.ai/external_review.html", workflow)
        self.assertIn("external-replication-docket-v1", workflow)


if __name__ == "__main__":
    unittest.main()
