import importlib.util
import unittest
from pathlib import Path


MODULE_PATH = Path("code/ops/BUILD_REPOSITORY_BRANCH_CENSUS.py")
spec = importlib.util.spec_from_file_location("branch_census", MODULE_PATH)
if spec is None or spec.loader is None:
    raise RuntimeError(f"unable to load {MODULE_PATH}")
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)

classify_branches = module.classify_branches
validate_dispositions = module.validate_dispositions
validate_registry = module.validate_registry


class RepositoryBranchCensusTests(unittest.TestCase):
    def setUp(self):
        self.registry = {
            "schema_version": "1.0",
            "repository": "robertashworth1986-debug/lumen-core-public",
            "default_branch": "main",
            "observed_pr_heads": [
                {"number": 10, "state": "open", "head": "feature/open"},
                {"number": 9, "state": "merged", "head": "feature/merged"},
                {"number": 8, "state": "closed_unmerged", "head": "feature/closed"},
            ],
        }
        self.dispositions = {
            "schema_version": "1.0",
            "repository": "robertashworth1986-debug/lumen-core-public",
            "dispositions": {
                "merged_alias_or_ancestor": [],
                "preserve_and_port_selected_artifacts": ["orphan/no-pr"],
                "preserve_historical_no_direct_merge": [],
            },
            "rationales": {"orphan/no-pr": "Preserve and inspect."},
            "rules": {
                "new_unclassified_branch_allowed": False,
                "direct_merge_of_preserve_historical_no_direct_merge_allowed": False,
                "direct_merge_of_preserve_and_port_selected_artifacts_allowed": False,
                "selected_port_requires_current_owner_and_tests": True,
            },
        }

    def test_valid_registry_and_exact_branch_classification(self):
        entries = validate_registry(self.registry)
        dispositions = validate_dispositions(self.dispositions)
        result = classify_branches(
            {
                "main": "a" * 40,
                "feature/open": "b" * 40,
                "feature/merged": "c" * 40,
                "orphan/no-pr": "d" * 40,
            },
            entries,
            "main",
            dispositions,
        )
        self.assertEqual(result["missing_open_pr_heads"], [])
        self.assertEqual(result["non_pr_branches"], ["orphan/no-pr"])
        self.assertEqual(result["unclassified_non_pr_branches"], [])
        self.assertEqual(result["deleted_historical_pr_heads"], ["feature/closed"])

    def test_new_unclassified_branch_fails_closed(self):
        entries = validate_registry(self.registry)
        dispositions = validate_dispositions(self.dispositions)
        with self.assertRaisesRegex(ValueError, "must exactly cover non-PR branches"):
            classify_branches(
                {
                    "main": "a" * 40,
                    "feature/open": "b" * 40,
                    "orphan/no-pr": "c" * 40,
                    "orphan/new": "d" * 40,
                },
                entries,
                "main",
                dispositions,
            )

    def test_stale_disposition_fails_closed(self):
        entries = validate_registry(self.registry)
        dispositions = validate_dispositions(self.dispositions)
        with self.assertRaisesRegex(ValueError, "stale"):
            classify_branches(
                {"main": "a" * 40, "feature/open": "b" * 40},
                entries,
                "main",
                dispositions,
            )

    def test_missing_open_pr_head_fails_closed(self):
        entries = validate_registry(self.registry)
        with self.assertRaisesRegex(ValueError, "open PR head branches missing"):
            classify_branches({"main": "a" * 40}, entries, "main")

    def test_missing_default_branch_fails_closed(self):
        entries = validate_registry(self.registry)
        with self.assertRaisesRegex(ValueError, "default branch"):
            classify_branches({"feature/open": "b" * 40}, entries, "main")

    def test_duplicate_pr_number_rejected(self):
        registry = dict(self.registry)
        registry["observed_pr_heads"] = list(self.registry["observed_pr_heads"]) + [
            {"number": 10, "state": "closed_unmerged", "head": "duplicate/number"}
        ]
        with self.assertRaisesRegex(ValueError, "duplicate PR number"):
            validate_registry(registry)

    def test_duplicate_head_branch_rejected(self):
        registry = dict(self.registry)
        registry["observed_pr_heads"] = list(self.registry["observed_pr_heads"]) + [
            {"number": 11, "state": "closed_unmerged", "head": "feature/open"}
        ]
        with self.assertRaisesRegex(ValueError, "duplicate PR head branch"):
            validate_registry(registry)

    def test_unsafe_branch_name_rejected(self):
        registry = dict(self.registry)
        registry["observed_pr_heads"] = [
            {"number": 10, "state": "open", "head": "../unsafe"}
        ]
        with self.assertRaisesRegex(ValueError, "safe branch name"):
            validate_registry(registry)

    def test_duplicate_branch_disposition_rejected(self):
        dispositions = dict(self.dispositions)
        dispositions["dispositions"] = {
            "merged_alias_or_ancestor": ["orphan/no-pr"],
            "preserve_and_port_selected_artifacts": ["orphan/no-pr"],
            "preserve_historical_no_direct_merge": [],
        }
        with self.assertRaisesRegex(ValueError, "multiple dispositions"):
            validate_dispositions(dispositions)

    def test_rationale_coverage_required(self):
        dispositions = dict(self.dispositions)
        dispositions["rationales"] = {}
        with self.assertRaisesRegex(ValueError, "rationales must exactly cover"):
            validate_dispositions(dispositions)


if __name__ == "__main__":
    unittest.main()
