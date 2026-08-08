"""Adversarial tests for bounded public-release incident classification."""

from __future__ import annotations

from copy import deepcopy
import hashlib
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = ROOT / "code" / "ops" / "CLASSIFY_PUBLIC_RELEASE_INCIDENT.py"
SPEC = importlib.util.spec_from_file_location("public_release_incident", MODULE_PATH)
assert SPEC and SPEC.loader
incident = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(incident)


def digest(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def git_oid(text: str) -> str:
    return hashlib.sha1(text.encode("utf-8")).hexdigest()


def make_manifest(names: list[str]) -> dict[str, object]:
    commit = "a" * 40
    return {
        "archive_sha256": digest("archive"),
        "file_count": len(names),
        "files": [
            {
                "archive_name": name,
                "bytes": 100 + index,
                "git_blob_oid": git_oid(name),
                "install_mode": "0644",
                "repo_path": f"dashboard/{name}",
                "sha256": digest(name),
            }
            for index, name in enumerate(names)
        ],
        "schema": "lumencore.public_site_release_manifest.v1",
        "source_commit": commit,
        "target_directory": "/opt/lumencore/dashboard",
    }


def make_audit(
    manifest: dict[str, object], statuses: dict[str, str] | None = None
) -> dict[str, object]:
    statuses = statuses or {}
    commit = str(manifest["source_commit"])
    rows: list[dict[str, object]] = []
    for file_row in manifest["files"]:  # type: ignore[index]
        name = str(file_row["archive_name"])
        expected = str(file_row["sha256"])
        status = statuses.get(name, "MATCH")
        common: dict[str, object] = {
            "archive_name": name,
            "expected_sha256": expected,
            "status": status,
            "url": incident.expected_live_url(name, commit),
        }
        if status == "ERROR":
            common["detail"] = "simulated HTTP failure"
        else:
            common.update(
                {
                    "actual_sha256": expected if status == "MATCH" else digest(name + "-drift"),
                    "bytes": int(file_row["bytes"]),
                    "content_type": "text/html",
                    "content_type_allowed": True,
                    "http_status": 200,
                }
            )
        rows.append(common)
    matches = sum(row["status"] == "MATCH" for row in rows)
    return {
        "base_url": "https://lumen-core.ai",
        "checked_at_utc": "2026-08-08T12:04:53Z",
        "expected_file_count": len(rows),
        "matched_file_count": matches,
        "release_verified": matches == len(rows),
        "results": rows,
        "schema": "lumencore.public_site_live_verification.v1",
        "source_commit": commit,
    }


class PublicReleaseIncidentTests(unittest.TestCase):
    def setUp(self) -> None:
        self.policy = incident.read_json(
            ROOT / "config" / "incident_response_and_continuity_v1.json"
        )
        self.names = list(self.policy["critical_surfaces"]) + [
            "assets/lumencore.css",
            "assets/luma_command_fabric.js",
            "robots.txt",
            "sitemap.xml",
            "site.webmanifest",
        ]
        self.manifest = make_manifest(self.names)

    def classify(self, statuses: dict[str, str] | None = None) -> dict[str, object]:
        return incident.classify(
            policy=deepcopy(self.policy),
            manifest=deepcopy(self.manifest),
            audit=make_audit(self.manifest, statuses),
        )

    def test_exact_release_is_none(self) -> None:
        receipt = self.classify()
        self.assertEqual(receipt["severity"], "NONE")
        self.assertEqual(receipt["decision"], "MONITOR")
        self.assertTrue(receipt["release_verified"])
        self.assertFalse(receipt["production_mutation_performed"])

    def test_critical_mismatch_is_sev2(self) -> None:
        receipt = self.classify({"operator_home.html": "MISMATCH"})
        self.assertEqual(receipt["severity"], "SEV-2")
        self.assertEqual(receipt["critical_affected"], ["operator_home.html"])

    def test_threshold_mismatch_is_sev2(self) -> None:
        receipt = self.classify(
            {
                "robots.txt": "MISMATCH",
                "sitemap.xml": "ERROR",
                "site.webmanifest": "MISMATCH",
            }
        )
        self.assertGreaterEqual(receipt["affected_ratio"], 0.2)
        self.assertEqual(receipt["severity"], "SEV-2")

    def test_limited_noncritical_error_is_sev3(self) -> None:
        manifest = make_manifest(self.names + ["manifest.json"])
        receipt = incident.classify(
            policy=deepcopy(self.policy),
            manifest=manifest,
            audit=make_audit(manifest, {"robots.txt": "ERROR"}),
        )
        self.assertEqual(receipt["severity"], "SEV-3")
        self.assertEqual(receipt["error_count"], 1)

    def test_duplicate_json_key_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "duplicate.json"
            path.write_text('{"schema_version":"1.0","schema_version":"1.0"}', encoding="utf-8")
            with self.assertRaisesRegex(incident.IncidentClassificationError, "duplicate"):
                incident.read_json(path)

    def test_nonfinite_json_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "nan.json"
            path.write_text('{"value":NaN}', encoding="utf-8")
            with self.assertRaisesRegex(incident.IncidentClassificationError, "non-finite"):
                incident.read_json(path)

    def test_manifest_and_audit_commit_mismatch_rejected(self) -> None:
        audit = make_audit(self.manifest)
        audit["source_commit"] = "b" * 40
        with self.assertRaisesRegex(incident.IncidentClassificationError, "source commit"):
            incident.classify(policy=self.policy, manifest=self.manifest, audit=audit)

    def test_unsafe_manifest_path_rejected(self) -> None:
        manifest = make_manifest(["../escape.html"])
        with self.assertRaisesRegex(incident.IncidentClassificationError, "unsafe"):
            incident.classify(policy=self.policy, manifest=manifest, audit=make_audit(manifest))

    def test_duplicate_result_rejected(self) -> None:
        audit = make_audit(self.manifest)
        audit["results"][1] = deepcopy(audit["results"][0])  # type: ignore[index]
        with self.assertRaisesRegex(incident.IncidentClassificationError, "duplicate"):
            incident.classify(policy=self.policy, manifest=self.manifest, audit=audit)

    def test_expected_hash_drift_rejected(self) -> None:
        audit = make_audit(self.manifest)
        audit["results"][0]["expected_sha256"] = "f" * 64  # type: ignore[index]
        with self.assertRaisesRegex(incident.IncidentClassificationError, "expected SHA-256"):
            incident.classify(policy=self.policy, manifest=self.manifest, audit=audit)

    def test_false_match_rejected(self) -> None:
        audit = make_audit(self.manifest)
        audit["results"][0]["actual_sha256"] = "f" * 64  # type: ignore[index]
        with self.assertRaisesRegex(incident.IncidentClassificationError, "inconsistent"):
            incident.classify(policy=self.policy, manifest=self.manifest, audit=audit)

    def test_summary_drift_rejected(self) -> None:
        audit = make_audit(self.manifest)
        audit["matched_file_count"] = 0
        with self.assertRaisesRegex(incident.IncidentClassificationError, "summary"):
            incident.classify(policy=self.policy, manifest=self.manifest, audit=audit)

    def test_noncanonical_domain_rejected(self) -> None:
        audit = make_audit(self.manifest)
        audit["base_url"] = "https://example.com"
        with self.assertRaisesRegex(incident.IncidentClassificationError, "base URL"):
            incident.classify(policy=self.policy, manifest=self.manifest, audit=audit)

    def test_noncanonical_timestamp_rejected(self) -> None:
        audit = make_audit(self.manifest)
        audit["checked_at_utc"] = "2026-08-08 12:04:53"
        with self.assertRaisesRegex(incident.IncidentClassificationError, "timezone"):
            incident.classify(policy=self.policy, manifest=self.manifest, audit=audit)

    def test_wrong_route_rejected(self) -> None:
        audit = make_audit(self.manifest)
        audit["results"][0]["url"] = (  # type: ignore[index]
            "https://lumen-core.ai/wrong?release=" + str(self.manifest["source_commit"])
        )
        with self.assertRaisesRegex(incident.IncidentClassificationError, "route mismatch"):
            incident.classify(policy=self.policy, manifest=self.manifest, audit=audit)

    def test_automatic_sev1_policy_rejected(self) -> None:
        policy = deepcopy(self.policy)
        policy["classification_contract"]["highest_automatic_severity"] = "SEV-1"
        with self.assertRaisesRegex(incident.IncidentClassificationError, "unsafe"):
            incident.classify(policy=policy, manifest=self.manifest, audit=make_audit(self.manifest))

    def test_automated_action_expansion_rejected(self) -> None:
        policy = deepcopy(self.policy)
        policy["automated_actions_allowed"].append("deploy production automatically")
        with self.assertRaisesRegex(incident.IncidentClassificationError, "automated action"):
            incident.classify(policy=policy, manifest=self.manifest, audit=make_audit(self.manifest))

    def test_missing_critical_surface_from_manifest_rejected(self) -> None:
        policy = deepcopy(self.policy)
        policy["critical_surfaces"].append("new-critical.html")
        with self.assertRaisesRegex(incident.IncidentClassificationError, "absent"):
            incident.classify(policy=policy, manifest=self.manifest, audit=make_audit(self.manifest))

    def test_missing_human_unlock_action_rejected(self) -> None:
        policy = deepcopy(self.policy)
        policy["human_authorization_required"].remove("deploy an exact public-site snapshot")
        with self.assertRaisesRegex(incident.IncidentClassificationError, "HumanUnlock"):
            incident.classify(policy=policy, manifest=self.manifest, audit=make_audit(self.manifest))

    def test_contractual_target_promotion_rejected(self) -> None:
        policy = deepcopy(self.policy)
        policy["planning_targets"]["contract_status"] = "enterprise_sla"
        with self.assertRaisesRegex(incident.IncidentClassificationError, "non-contractual"):
            incident.classify(policy=policy, manifest=self.manifest, audit=make_audit(self.manifest))

    def test_receipt_hash_is_stable(self) -> None:
        receipt = self.classify({"operator_home.html": "MISMATCH"})
        expected = receipt.pop("receipt_sha256")
        self.assertEqual(expected, incident.canonical_sha256(receipt))


if __name__ == "__main__":
    unittest.main()
