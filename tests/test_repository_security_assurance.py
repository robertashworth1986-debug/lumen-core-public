from __future__ import annotations

import importlib.util
import json
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location(
    "repository_security_assurance",
    ROOT / "code" / "ops" / "VERIFY_REPOSITORY_SECURITY_ASSURANCE.py",
)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


class RepositorySecurityAssuranceTests(unittest.TestCase):
    def canonical_payload(self) -> dict:
        return MODULE.read_json(
            ROOT / "config" / "repository_security_assurance_v1.json"
        )

    def verify_payload(self, payload: dict) -> dict:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "register.json"
            path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
            return MODULE.verify_register(
                root=ROOT,
                register_path=path,
                verified_utc="2026-08-08T14:20:00Z",
            )

    def test_current_repository_emits_bounded_receipt(self) -> None:
        receipt = self.verify_payload(self.canonical_payload())
        self.assertTrue(receipt["valid"])
        self.assertEqual(receipt["schema_version"], "1.1")
        self.assertEqual(receipt["production_decision"], "HOLD")
        self.assertEqual(receipt["control_count"], 8)
        self.assertEqual(receipt["claim_boundary_count"], 11)
        self.assertFalse(receipt["workflow_boundaries"]["automatic_merge"])
        self.assertFalse(receipt["workflow_boundaries"]["runtime_scan"])
        self.assertTrue(
            receipt["workflow_boundaries"]["secret_scanning_enabled"]
        )
        self.assertTrue(
            receipt["workflow_boundaries"][
                "secret_scanning_push_protection_enabled"
            ]
        )
        self.assertEqual(
            receipt["workflow_boundaries"]["open_secret_scanning_alert_count"],
            1,
        )
        self.assertFalse(
            receipt["workflow_boundaries"]["provider_rotation_confirmed"]
        )
        self.assertFalse(
            receipt["workflow_boundaries"][
                "default_branch_protection_enforced"
            ]
        )
        dependency_contract = receipt["dashboard_dependency_contract"]
        self.assertEqual(
            dependency_contract["locked_versions"]["animejs"], "4.5.0"
        )
        self.assertEqual(
            dependency_contract["locked_versions"]["three"], "0.185.1"
        )
        self.assertEqual(
            dependency_contract["compatibility_decision"],
            "REMOVE_UNUSED_INCOMPATIBLE_MODEL_VIEWER_AND_ACCEPT_STRICT_THREE_0_185_1_GRAPH",
        )
        self.assertEqual(
            dependency_contract["install_policy"],
            "STRICT_NPM_PEER_RESOLUTION_NO_FORCE_OR_LEGACY_BYPASS",
        )
        self.assertTrue(
            dependency_contract["animejs_three_adapter_smoke_required"]
        )
        self.assertTrue(dependency_contract["incompatible_model_viewer_absent"])
        self.assertEqual(
            dependency_contract["runtime_claim_boundary"],
            "DECLARED_NPM_GRAPH_VALIDATED_WITHOUT_CLAIMING_DEPLOYED_VISUAL_ASSET_REPLACEMENT",
        )
        self.assertEqual(len(receipt["receipt_sha256"]), 64)

    def test_remote_observation_preserves_open_security_gates(self) -> None:
        receipt = self.verify_payload(self.canonical_payload())
        observation = receipt["remote_observation"]
        self.assertEqual(observation["open_alerts"]["secret_scanning"], 1)
        triage = observation["secret_scanning_triage"]
        self.assertEqual(triage["resolved_false_positive_alert_count"], 28)
        self.assertEqual(triage["verified_historical_location_count"], 51)
        self.assertEqual(triage["current_tracked_occurrence_count"], 0)
        self.assertFalse(
            triage["remaining_alert"]["provider_rotation_confirmed"]
        )
        self.assertFalse(
            triage["remaining_alert"]["git_history_remediation_confirmed"]
        )
        self.assertFalse(
            observation["default_branch_protection"]["main_protected"]
        )

    def test_false_positive_count_cannot_be_inflated(self) -> None:
        payload = self.canonical_payload()
        payload["remote_observation"]["secret_scanning_triage"][
            "resolved_false_positive_alert_count"
        ] = 29
        with self.assertRaisesRegex(
            MODULE.SecurityAssuranceError, "false-positive alert count"
        ):
            self.verify_payload(payload)

    def test_provider_rotation_cannot_be_promoted_without_receipt(self) -> None:
        payload = self.canonical_payload()
        payload["remote_observation"]["secret_scanning_triage"][
            "remaining_alert"
        ]["provider_rotation_confirmed"] = True
        with self.assertRaisesRegex(
            MODULE.SecurityAssuranceError, "historical provider gate"
        ):
            self.verify_payload(payload)

    def test_branch_protection_gap_cannot_be_promoted_locally(self) -> None:
        payload = self.canonical_payload()
        payload["remote_observation"]["default_branch_protection"][
            "main_protected"
        ] = True
        with self.assertRaisesRegex(
            MODULE.SecurityAssuranceError, "branch-protection gap"
        ):
            self.verify_payload(payload)

    def test_duplicate_json_key_is_rejected(self) -> None:
        source = (ROOT / "config" / "repository_security_assurance_v1.json").read_text(
            encoding="utf-8"
        )
        duplicate = source.replace(
            '  "schema_version": "1.1",',
            '  "schema_version": "1.1",\n  "schema_version": "1.1",',
            1,
        )
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "duplicate.json"
            path.write_text(duplicate, encoding="utf-8")
            with self.assertRaisesRegex(MODULE.SecurityAssuranceError, "duplicate"):
                MODULE.read_json(path)

    def test_non_finite_json_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "nonfinite.json"
            path.write_text('{"value": NaN}', encoding="utf-8")
            with self.assertRaisesRegex(MODULE.SecurityAssuranceError, "non-finite"):
                MODULE.read_json(path)

    def test_status_promotion_is_rejected(self) -> None:
        payload = self.canonical_payload()
        payload["controls"][0]["status"] = "externally_audited"
        with self.assertRaisesRegex(MODULE.SecurityAssuranceError, "promotion"):
            self.verify_payload(payload)

    def test_missing_claim_boundary_is_rejected(self) -> None:
        payload = self.canonical_payload()
        payload["claim_boundaries"].remove("no_penetration_test")
        with self.assertRaisesRegex(MODULE.SecurityAssuranceError, "claim boundaries"):
            self.verify_payload(payload)

    def test_path_traversal_is_rejected(self) -> None:
        payload = self.canonical_payload()
        payload["controls"][0]["evidence_paths"][0] = "../SECURITY.md"
        with self.assertRaisesRegex(MODULE.SecurityAssuranceError, "repository-relative"):
            self.verify_payload(payload)

    def test_codeql_action_must_be_immutable(self) -> None:
        text = (ROOT / ".github" / "workflows" / "codeql.yml").read_text(
            encoding="utf-8"
        )
        text = text.replace(
            f"github/codeql-action/init@{MODULE.CODEQL_SHA}",
            "github/codeql-action/init@v4",
        )
        with self.assertRaisesRegex(MODULE.SecurityAssuranceError, "CodeQL"):
            MODULE.verify_codeql_workflow(text)

    def test_codeql_security_events_permission_is_required(self) -> None:
        text = (ROOT / ".github" / "workflows" / "codeql.yml").read_text(
            encoding="utf-8"
        )
        text = text.replace("security-events: write", "security-events: read")
        with self.assertRaisesRegex(MODULE.SecurityAssuranceError, "security-events"):
            MODULE.verify_codeql_workflow(text)

    def test_dependency_gate_threshold_cannot_be_weakened(self) -> None:
        text = (ROOT / ".github" / "workflows" / "dependency-review.yml").read_text(
            encoding="utf-8"
        )
        text = text.replace("fail-on-severity: high", "fail-on-severity: critical")
        with self.assertRaisesRegex(MODULE.SecurityAssuranceError, "fail-on-severity"):
            MODULE.verify_dependency_review_workflow(text)

    def test_dependency_review_remains_read_only(self) -> None:
        text = (ROOT / ".github" / "workflows" / "dependency-review.yml").read_text(
            encoding="utf-8"
        ) + "\n  pull-requests: write\n"
        with self.assertRaisesRegex(MODULE.SecurityAssuranceError, "read-only"):
            MODULE.verify_dependency_review_workflow(text)

    def test_all_declared_ecosystems_are_required(self) -> None:
        text = (ROOT / ".github" / "dependabot.yml").read_text(encoding="utf-8")
        text = text.replace("package-ecosystem: docker", "package-ecosystem: omitted")
        with self.assertRaisesRegex(MODULE.SecurityAssuranceError, "docker"):
            MODULE.verify_dependabot_config(text)

    def test_known_dashboard_dependency_versions_are_locked(self) -> None:
        package = MODULE.read_json(ROOT / "dashboard" / "package.json")
        lock = MODULE.read_json(ROOT / "dashboard" / "package-lock.json")
        contract = MODULE.verify_dashboard_dependencies(package, lock)
        self.assertEqual(contract["manifest_ranges"]["animejs"], "^4.5.0")
        self.assertEqual(contract["manifest_ranges"]["three"], "^0.185.1")
        self.assertEqual(
            contract["peer_contracts"]["postprocessing"]["three"],
            ">= 0.168.0 < 0.186.0",
        )
        self.assertNotIn("@google/model-viewer", package["dependencies"])

    def test_dashboard_manifest_and_lock_root_must_match(self) -> None:
        package = MODULE.read_json(ROOT / "dashboard" / "package.json")
        lock = MODULE.read_json(ROOT / "dashboard" / "package-lock.json")
        lock["packages"][""]["dependencies"]["animejs"] = "^4.4.1"
        with self.assertRaisesRegex(
            MODULE.SecurityAssuranceError, "manifest and lockfile root|diverge"
        ):
            MODULE.verify_dashboard_dependencies(package, lock)

    def test_animejs_downgrade_is_rejected(self) -> None:
        package = MODULE.read_json(ROOT / "dashboard" / "package.json")
        lock = MODULE.read_json(ROOT / "dashboard" / "package-lock.json")
        lock["packages"]["node_modules/animejs"]["version"] = "4.4.1"
        with self.assertRaisesRegex(MODULE.SecurityAssuranceError, "animejs"):
            MODULE.verify_dashboard_dependencies(package, lock)

    def test_three_downgrade_is_rejected(self) -> None:
        package = MODULE.read_json(ROOT / "dashboard" / "package.json")
        lock = MODULE.read_json(ROOT / "dashboard" / "package-lock.json")
        package["dependencies"]["three"] = "^0.183.2"
        lock["packages"][""]["dependencies"]["three"] = "^0.183.2"
        lock["packages"]["node_modules/three"]["version"] = "0.183.2"
        with self.assertRaisesRegex(MODULE.SecurityAssuranceError, "three"):
            MODULE.verify_dashboard_dependencies(package, lock)

    def test_animejs_manifest_range_drift_is_rejected(self) -> None:
        package = MODULE.read_json(ROOT / "dashboard" / "package.json")
        lock = MODULE.read_json(ROOT / "dashboard" / "package-lock.json")
        package["dependencies"]["animejs"] = "^4.4.1"
        lock["packages"][""]["dependencies"]["animejs"] = "^4.4.1"
        with self.assertRaisesRegex(MODULE.SecurityAssuranceError, "animejs"):
            MODULE.verify_dashboard_dependencies(package, lock)

    def test_postprocessing_three_peer_upper_bound_drift_is_rejected(self) -> None:
        package = MODULE.read_json(ROOT / "dashboard" / "package.json")
        lock = MODULE.read_json(ROOT / "dashboard" / "package-lock.json")
        lock["packages"]["node_modules/postprocessing"]["peerDependencies"][
            "three"
        ] = ">= 0.168.0 < 0.185.0"
        with self.assertRaisesRegex(MODULE.SecurityAssuranceError, "postprocessing"):
            MODULE.verify_dashboard_dependencies(package, lock)

    def test_expected_three_peer_package_removal_is_rejected(self) -> None:
        package = MODULE.read_json(ROOT / "dashboard" / "package.json")
        lock = MODULE.read_json(ROOT / "dashboard" / "package-lock.json")
        del lock["packages"]["node_modules/postprocessing"]["peerDependencies"][
            "three"
        ]
        with self.assertRaisesRegex(MODULE.SecurityAssuranceError, "peer package set"):
            MODULE.verify_dashboard_dependencies(package, lock)

    def test_model_viewer_manifest_reintroduction_is_rejected(self) -> None:
        package = MODULE.read_json(ROOT / "dashboard" / "package.json")
        lock = MODULE.read_json(ROOT / "dashboard" / "package-lock.json")
        package["dependencies"]["@google/model-viewer"] = "^4.3.1"
        with self.assertRaisesRegex(
            MODULE.SecurityAssuranceError, "model-viewer.*reintroduced"
        ):
            MODULE.verify_dashboard_dependencies(package, lock)

    def test_model_viewer_lock_reintroduction_is_rejected(self) -> None:
        package = MODULE.read_json(ROOT / "dashboard" / "package.json")
        lock = MODULE.read_json(ROOT / "dashboard" / "package-lock.json")
        lock["packages"]["node_modules/@google/model-viewer"] = {
            "version": "4.3.1",
            "peerDependencies": {"three": "^0.183.0"},
        }
        with self.assertRaisesRegex(
            MODULE.SecurityAssuranceError, "model-viewer.*lock.*reintroduced"
        ):
            MODULE.verify_dashboard_dependencies(package, lock)

    def test_unexpected_three_peer_package_is_rejected(self) -> None:
        package = MODULE.read_json(ROOT / "dashboard" / "package.json")
        lock = MODULE.read_json(ROOT / "dashboard" / "package-lock.json")
        lock["packages"]["node_modules/unreviewed-three-plugin"] = {
            "version": "1.0.0",
            "peerDependencies": {"three": ">=0.1.0"},
        }
        with self.assertRaisesRegex(
            MODULE.SecurityAssuranceError, "unexpected.*Three.js peer package"
        ):
            MODULE.verify_dashboard_dependencies(package, lock)

    def test_animejs_three_adapter_peer_contract_cannot_drift(self) -> None:
        package = MODULE.read_json(ROOT / "dashboard" / "package.json")
        lock = MODULE.read_json(ROOT / "dashboard" / "package-lock.json")
        lock["packages"]["node_modules/animejs"]["peerDependencies"][
            "three"
        ] = ">=0.185.0"
        with self.assertRaisesRegex(MODULE.SecurityAssuranceError, "animejs.*three"):
            MODULE.verify_dashboard_dependencies(package, lock)

    def test_dashboard_registry_provenance_is_required(self) -> None:
        package = MODULE.read_json(ROOT / "dashboard" / "package.json")
        lock = MODULE.read_json(ROOT / "dashboard" / "package-lock.json")
        lock["packages"]["node_modules/animejs"]["resolved"] = (
            "https://example.invalid/animejs-4.5.0.tgz"
        )
        with self.assertRaisesRegex(MODULE.SecurityAssuranceError, "source drift"):
            MODULE.verify_dashboard_dependencies(package, lock)

    def test_dashboard_sha512_integrity_is_required(self) -> None:
        package = MODULE.read_json(ROOT / "dashboard" / "package.json")
        lock = MODULE.read_json(ROOT / "dashboard" / "package-lock.json")
        lock["packages"]["node_modules/three"]["integrity"] = "sha512-not-base64"
        with self.assertRaisesRegex(MODULE.SecurityAssuranceError, "integrity"):
            MODULE.verify_dashboard_dependencies(package, lock)

    def test_security_workflow_uses_strict_peer_resolution(self) -> None:
        text = (
            ROOT / ".github" / "workflows" / "repository-security-assurance.yml"
        ).read_text(encoding="utf-8")
        MODULE.verify_repository_security_workflow(text)
        weakened = text.replace(
            MODULE.STRICT_NPM_CI_COMMAND,
            "npm ci --legacy-peer-deps --ignore-scripts --no-audit --no-fund",
        )
        with self.assertRaisesRegex(
            MODULE.SecurityAssuranceError, "peer resolution"
        ):
            MODULE.verify_repository_security_workflow(weakened)

    def test_security_workflow_rejects_environment_legacy_peer_mode(self) -> None:
        text = (
            ROOT / ".github" / "workflows" / "repository-security-assurance.yml"
        ).read_text(encoding="utf-8")
        weakened = text.replace(
            "working-directory: dashboard",
            "working-directory: dashboard\n        env:\n          NPM_CONFIG_LEGACY_PEER_DEPS: true",
        )
        with self.assertRaisesRegex(MODULE.SecurityAssuranceError, "bypass"):
            MODULE.verify_repository_security_workflow(weakened)

    def test_security_workflow_rejects_environment_force_mode(self) -> None:
        text = (
            ROOT / ".github" / "workflows" / "repository-security-assurance.yml"
        ).read_text(encoding="utf-8")
        weakened = text.replace(
            "working-directory: dashboard",
            "working-directory: dashboard\n        env:\n          NPM_CONFIG_FORCE: true",
        )
        with self.assertRaisesRegex(MODULE.SecurityAssuranceError, "bypass"):
            MODULE.verify_repository_security_workflow(weakened)

    def test_security_workflow_rejects_alternate_force_order_and_decoy(self) -> None:
        text = (
            ROOT / ".github" / "workflows" / "repository-security-assurance.yml"
        ).read_text(encoding="utf-8")
        weakened = text.replace(
            MODULE.STRICT_NPM_CI_COMMAND,
            f"# {MODULE.STRICT_NPM_CI_COMMAND}\n          npm --force ci --ignore-scripts --no-audit --no-fund",
        )
        with self.assertRaisesRegex(MODULE.SecurityAssuranceError, "peer resolution"):
            MODULE.verify_repository_security_workflow(weakened)

    def test_security_workflow_rejects_static_verification_time(self) -> None:
        text = (
            ROOT / ".github" / "workflows" / "repository-security-assurance.yml"
        ).read_text(encoding="utf-8")
        weakened = text.replace(
            "--json-out out/repository-security-assurance/receipt.json",
            "--verified-utc 2026-08-31T20:41:02Z "
            "--json-out out/repository-security-assurance/receipt.json",
        )
        with self.assertRaisesRegex(MODULE.SecurityAssuranceError, "execution time"):
            MODULE.verify_repository_security_workflow(weakened)

    def test_security_workflow_watches_npmrc_and_modernization_inputs(self) -> None:
        text = (
            ROOT / ".github" / "workflows" / "repository-security-assurance.yml"
        ).read_text(encoding="utf-8")
        for watched_path in (
            "      - '.npmrc'\n",
            "      - 'dashboard/.npmrc'\n",
            "      - 'code/ops/RUN_STACK_MODERNIZATION_SWEEP.ps1'\n",
        ):
            weakened = text.replace(watched_path, "", 1)
            with self.subTest(watched_path=watched_path):
                with self.assertRaisesRegex(MODULE.SecurityAssuranceError, "watch"):
                    MODULE.verify_repository_security_workflow(weakened)

    def test_security_workflow_node_action_must_be_immutable(self) -> None:
        text = (
            ROOT / ".github" / "workflows" / "repository-security-assurance.yml"
        ).read_text(encoding="utf-8")
        weakened = text.replace(
            f"actions/setup-node@{MODULE.SETUP_NODE_SHA} # v7.0.0",
            "actions/setup-node@v7",
        )
        with self.assertRaisesRegex(MODULE.SecurityAssuranceError, "setup-node"):
            MODULE.verify_repository_security_workflow(weakened)

    def test_declared_graph_does_not_claim_vendored_visual_asset_upgrade(self) -> None:
        dossier = (ROOT / "docs" / "REPOSITORY_SECURITY_ASSURANCE.md").read_text(
            encoding="utf-8"
        )
        public_loader = (ROOT / "dashboard" / "assets" / "lumencore.js").read_text(
            encoding="utf-8"
        )
        vendor_readme = (
            ROOT / "dashboard" / "assets" / "vendor" / "README.md"
        ).read_text(encoding="utf-8")
        prooflock_three = (
            ROOT
            / "dashboard"
            / "build_week"
            / "prooflock_console"
            / "three.core.min.js"
        ).read_text(encoding="utf-8")
        modernization = (
            ROOT / "code" / "ops" / "RUN_STACK_MODERNIZATION_SWEEP.ps1"
        ).read_text(encoding="utf-8")

        self.assertIn("declared npm-graph repair", dossier)
        self.assertIn("three@0.160.1", public_loader)
        self.assertIn("Three.js `0.160.1`", vendor_readme)
        self.assertIn('"184"', prooflock_three)
        self.assertNotIn("three@0.185.1", public_loader)
        self.assertNotIn("@google/model-viewer", modernization)

    def test_vulnerable_echarts_lock_is_rejected(self) -> None:
        package = MODULE.read_json(ROOT / "dashboard" / "package.json")
        lock = MODULE.read_json(ROOT / "dashboard" / "package-lock.json")
        lock["packages"]["node_modules/echarts"]["version"] = "6.0.0"
        with self.assertRaisesRegex(MODULE.SecurityAssuranceError, "echarts"):
            MODULE.verify_dashboard_dependencies(package, lock)

    def test_vulnerable_form_data_override_is_rejected(self) -> None:
        package = MODULE.read_json(ROOT / "dashboard" / "package.json")
        lock = MODULE.read_json(ROOT / "dashboard" / "package-lock.json")
        package["overrides"]["form-data"] = "4.0.5"
        with self.assertRaisesRegex(MODULE.SecurityAssuranceError, "form-data"):
            MODULE.verify_dashboard_dependencies(package, lock)

    def test_security_policy_must_retain_exception_expiry(self) -> None:
        text = (ROOT / "SECURITY.md").read_text(encoding="utf-8")
        text = text.replace("expiration date", "review date")
        with self.assertRaisesRegex(MODULE.SecurityAssuranceError, "expiration date"):
            MODULE.verify_security_policy(text)

    def test_dossier_must_retain_zero_vulnerability_boundary(self) -> None:
        text = (ROOT / "docs" / "REPOSITORY_SECURITY_ASSURANCE.md").read_text(
            encoding="utf-8"
        )
        text = text.replace(
            "does not mean zero vulnerabilities", "establishes zero vulnerabilities"
        )
        with self.assertRaisesRegex(MODULE.SecurityAssuranceError, "zero vulnerabilities"):
            MODULE.verify_dossier(text)


if __name__ == "__main__":
    unittest.main()
