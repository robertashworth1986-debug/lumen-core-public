from pathlib import Path
import copy
import importlib.util
import json
import os
import re
import subprocess
import sys
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]
WORKFLOW_DIR = ROOT / ".github" / "workflows"
ACTION_USE_RE = re.compile(
    r"^\s*(?:-\s*)?uses:\s*([^#\s]+)(?:\s+#\s*(\S.*))?$",
    re.MULTILINE,
)
FULL_COMMIT_RE = re.compile(r"^[0-9a-f]{40}$")
WHITESPACE_SCRIPT = ROOT / "code" / "ops" / "VERIFY_CHANGED_WHITESPACE.py"
SPEC = importlib.util.spec_from_file_location("changed_whitespace", WHITESPACE_SCRIPT)
assert SPEC and SPEC.loader
WHITESPACE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(WHITESPACE)


class ChangedWhitespaceTests(unittest.TestCase):
    """Real Git objects in disposable repos; no provider, user repo or service changes."""

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.repo = Path(self.temp.name)
        self.git("init", "-b", "main")
        self.git("config", "user.name", "Whitespace fixture")
        self.git("config", "user.email", "fixture@example.invalid")
        self.git("config", "core.autocrlf", "false")
        self.git("config", "core.hooksPath", str(self.repo / "no-hooks"))
        self.base = self.commit_file("base.txt", "base\n")
        self.git("checkout", "-b", "candidate")
        self.head = self.commit_file("candidate.txt", "candidate\n")
        self.git("checkout", "main")
        self.main = self.commit_file("inherited.md", "main-only hard break  \n")
        self.git("merge", "--no-ff", "--no-edit", "candidate")
        self.merge = self.git("rev-parse", "HEAD")
        self.event = {"number": 259, "pull_request": {
            "head": {"sha": self.head}, "base": {"sha": self.base}}}

    def git(self, *args, check=True):
        result = subprocess.run(["git", *args], cwd=self.repo, text=True,
                                capture_output=True, timeout=15, check=False)
        if check:
            self.assertEqual(result.returncode, 0, (args, result.stdout, result.stderr))
            return result.stdout.strip()
        return result

    def commit_file(self, name, text):
        (self.repo / name).write_bytes(text.encode("utf-8"))
        self.git("add", "--", name)
        self.git("commit", "-m", "fixture change")
        return self.git("rev-parse", "HEAD")

    def comparison(self, event=None, sha=None, ref="refs/pull/259/merge", kind="pull_request"):
        return WHITESPACE.select_comparison(self.repo, kind,
            self.event if event is None else event, self.merge if sha is None else sha, ref)

    def run_gate(self, event=None, kind="pull_request", sha=None, ref="refs/pull/259/merge"):
        event_path = self.repo / "event.json"
        event_path.write_text(json.dumps(self.event if event is None else event), encoding="utf-8")
        env = dict(os.environ, GITHUB_EVENT_PATH=str(event_path), GITHUB_EVENT_NAME=kind,
                   GITHUB_SHA=self.merge if sha is None else sha, GITHUB_REF=ref)
        return subprocess.run([sys.executable, "-B", str(WHITESPACE_SCRIPT)], cwd=self.repo,
                              env=env, text=True, capture_output=True, timeout=20, check=False)

    def replace_merge_tree(self, filename, text):
        (self.repo / filename).write_bytes(text.encode("utf-8"))
        self.git("add", "--", filename)
        tree = self.git("write-tree")
        self.merge = self.git("commit-tree", tree, "-p", self.main, "-p", self.head,
                              "-m", "synthetic tested merge")
        self.git("update-ref", "HEAD", self.merge)

    def test_unchanged_main_whitespace_is_not_attributed_to_pr(self):
        old = self.git("diff", "--check", f"{self.base}...{self.merge}", check=False)
        self.assertEqual(old.returncode, 2)
        self.assertIn("inherited.md:1: trailing whitespace", old.stdout)
        result = self.run_gate()
        self.assertEqual(result.returncode, 0, result.stderr)
        context = json.loads(result.stdout)
        self.assertEqual(context["comparison"], [self.main, self.merge])
        self.assertFalse(context["event_base_matches_parent"])

    def test_pr_introduced_whitespace_still_fails_with_exact_git_status(self):
        self.git("checkout", "candidate")
        self.head = self.commit_file("new.txt", "new whitespace  \n")
        self.event["pull_request"]["head"]["sha"] = self.head
        self.git("checkout", "main")
        tree_result = self.git("merge-tree", "--write-tree", self.main, self.head)
        self.merge = self.git("commit-tree", tree_result.splitlines()[0], "-p", self.main,
                              "-p", self.head, "-m", "tested merge with PR defect")
        self.git("update-ref", "HEAD", self.merge)
        result = self.run_gate()
        self.assertEqual(result.returncode, 2)
        self.assertIn("new.txt:1: trailing whitespace", result.stdout)
        self.assertNotIn("inherited.md:1: trailing whitespace", result.stdout)

    def test_merge_resolution_and_changed_main_file_whitespace_are_checked(self):
        for filename in ("resolution.txt", "inherited.md"):
            with self.subTest(filename=filename):
                self.replace_merge_tree(filename, "new merge contribution  \n")
                result = self.run_gate()
                self.assertEqual(result.returncode, 2)
                self.assertIn(f"{filename}:1: trailing whitespace", result.stdout)

    def test_wrong_checkout_event_head_or_ref_refuses_before_diff(self):
        wrong = copy.deepcopy(self.event)
        wrong["pull_request"]["head"]["sha"] = self.base
        for event, sha, ref in ((wrong, self.merge, "refs/pull/259/merge"),
                                (self.event, self.head, "refs/pull/259/merge"),
                                (self.event, self.merge, "refs/pull/260/merge")):
            with self.subTest(event=event, sha=sha, ref=ref):
                result = self.run_gate(event, sha=sha, ref=ref)
                self.assertEqual(result.returncode, 2)
                self.assertIn("WHITESPACE_GATE_CONTEXT_INVALID", result.stderr)
                self.assertEqual(result.stdout, "")

    def test_nonmerge_and_wrong_parent_order_refuse(self):
        tree = self.git("rev-parse", "HEAD^{tree}")
        for parents in ((self.main,), (self.head, self.main),
                        (self.main, self.head, self.base)):
            with self.subTest(parents=parents):
                args = [item for parent in parents for item in ("-p", parent)]
                self.merge = self.git("commit-tree", tree, *args, "-m", "wrong parents")
                self.git("update-ref", "HEAD", self.merge)
                result = self.run_gate()
                self.assertEqual(result.returncode, 2)
                self.assertIn("WHITESPACE_GATE_CONTEXT_INVALID", result.stderr)

    def test_missing_parent_object_refuses(self):
        # This is a disposable loose-object store, never the user checkout.
        object_path = self.repo / ".git" / "objects" / self.main[:2] / self.main[2:]
        self.assertTrue(object_path.is_file())
        object_path.chmod(0o600)
        object_path.unlink()
        result = self.run_gate()
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("WHITESPACE_GATE_CONTEXT_INVALID", result.stderr)
        self.assertEqual(result.stdout, "")

    def test_missing_malformed_and_unsupported_context_refuse(self):
        for event in ({}, {"number": True}, {"number": 259, "pull_request": {}},
                      {"number": 259, "pull_request": {"head": {"sha": "HEAD"}}}):
            with self.subTest(event=event):
                self.assertEqual(self.run_gate(event).returncode, 2)
        result = self.run_gate(kind="workflow_dispatch")
        self.assertEqual(result.returncode, 2)
        self.assertIn("unsupported whitespace event", result.stderr)
        with self.assertRaises(WHITESPACE.ContextError):
            json.loads('{"number": 259, "number": 260}', object_pairs_hook=WHITESPACE.unique_object)

    def test_push_preserves_before_comparison_and_failure(self):
        before = self.merge
        after = self.commit_file("push.txt", "bad push  \n")
        event = {"before": before, "after": after, "ref": "refs/heads/main", "deleted": False}
        result = self.run_gate(event, kind="push", sha=after, ref="refs/heads/main")
        self.assertEqual(result.returncode, 2)
        self.assertIn("push.txt:1: trailing whitespace", result.stdout)
        before = after
        after = self.commit_file("push.txt", "clean push\n")
        event.update(before=before, after=after)
        result = self.run_gate(event, kind="push", sha=after, ref="refs/heads/main")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(json.loads(result.stdout)["comparison"], [f"{before}...{after}"])

    def test_push_missing_objects_or_identity_refuse(self):
        valid = {"before": self.main, "after": self.merge, "ref": "refs/heads/main", "deleted": False}
        for key, value in (("before", "0" * 40), ("before", "1" * 40),
                           ("after", self.head), ("ref", "refs/heads/other"), ("deleted", True)):
            with self.subTest(key=key, value=value):
                event = dict(valid, **{key: value})
                result = self.run_gate(event, kind="push", ref="refs/heads/main")
                self.assertEqual(result.returncode, 2)
                self.assertIn("WHITESPACE_GATE_CONTEXT_INVALID", result.stderr)

    def test_both_workflows_use_shared_enforcing_gate(self):
        for name in ("repository-trust.yml", "institutional-readiness.yml"):
            text = (WORKFLOW_DIR / name).read_text(encoding="utf-8")
            step = text.split("      - name: Reject whitespace errors\n", 1)[1].split("\n\n", 1)[0]
            self.assertEqual(step.strip(), "run: python code/ops/VERIFY_CHANGED_WHITESPACE.py")
            self.assertNotIn("continue-on-error", step)
            self.assertIn("fetch-depth: 0", text)
        trust = (WORKFLOW_DIR / "repository-trust.yml").read_text(encoding="utf-8")
        self.assertEqual(trust.count("      - 'code/ops/VERIFY_CHANGED_WHITESPACE.py'"), 2)


class RepositoryTrustPolicyTests(unittest.TestCase):
    def test_scheduled_workflows_cannot_write_repository_history(self):
        failures = []
        workflow_paths = [
            *WORKFLOW_DIR.glob("*.yml"),
            *WORKFLOW_DIR.glob("*.yaml"),
        ]
        forbidden_commands = re.compile(
            r"(?m)^\s*git\s+(?:add|commit|push|pull)\b"
        )
        for path in sorted(workflow_paths):
            text = path.read_text(encoding="utf-8")
            trigger, _, _ = text.partition("\npermissions:")
            if re.search(r"(?m)^\s{2}schedule:\s*$", trigger) is None:
                continue
            if re.search(r"(?m)^\s*contents:\s*write\s*$", text):
                failures.append(f"{path.name}: scheduled workflow grants contents: write")
            if forbidden_commands.search(text):
                failures.append(f"{path.name}: scheduled workflow mutates Git history")

        self.assertEqual(failures, [], "\n".join(failures))

    def test_public_resume_and_generator_keep_claims_inside_evidence_boundary(self):
        resume = (ROOT / "RESUME_LUMENCORE.md").read_text(encoding="utf-8").casefold()
        generator = (ROOT / "code" / "lumalinkedin_resume_engine_v1.py").read_text(
            encoding="utf-8"
        ).casefold()

        unsafe_public_claims = (
            "annual modeled value",
            "modeled annual value",
            "router edge",
            "harmonic win rate",
            "institutional-grade",
            "government-grade",
            "production-ready",
            "proven packages",
            "monetizable",
            "cross-sector avoided cost",
            "federal-ready",
            "investor-grade",
            "$52,331,333,340",
        )
        for phrase in unsafe_public_claims:
            self.assertNotIn(phrase, resume)
            self.assertNotIn(phrase, generator)

        required_boundaries = (
            "independent validation",
            "not established",
            "live-order authority",
            "final external submission authority",
            "swe infrastructure specialist / ai trainer",
        )
        for phrase in required_boundaries:
            self.assertIn(phrase, resume)

    def test_resume_outreach_is_claim_bounded_and_requires_current_run_approval(self):
        dispatcher = (ROOT / "code" / "email_resume_dispatcher.py").read_text(
            encoding="utf-8"
        ).casefold()
        runner = (ROOT / "code" / "ops" / "RUN_EMAIL_RESUME_DISPATCHER.ps1").read_text(
            encoding="utf-8"
        ).casefold()
        pdf_builder = (ROOT / "code" / "build_elite_resume_pdf.py").read_text(
            encoding="utf-8"
        ).casefold()

        for phrase in (
            "master valuation proxy usd:",
            "valuation increment usd:",
            "opportunity fit score:",
        ):
            self.assertNotIn(phrase, dispatcher)

        self.assertIn("--send-approved", dispatcher)
        self.assertIn("--send-approved requires --once", dispatcher)
        self.assertIn("human_send_approval_required", dispatcher)
        self.assertIn("approvedsend", runner)
        self.assertIn("-approvedsend requires -once", runner)
        self.assertIn("--send-approved", runner)
        self.assertNotIn("elite resume</title>", pdf_builder)
        self.assertNotIn(r"c:\lumatrader\institutional_stack_v2", pdf_builder)
        self.assertIn("path(__file__).resolve().parents[1]", pdf_builder)
        self.assertIn('root / "output" / "pdf"', pdf_builder)
        self.assertIn("--no-legacy-copy", pdf_builder)

    def test_security_policy_is_bounded_and_has_private_reporting(self):
        text = (ROOT / "SECURITY.md").read_text(encoding="utf-8")
        lowered = text.casefold()

        self.assertIn("security/advisories/new", text)
        self.assertIn("no response-time guarantee", lowered)
        self.assertIn("a valid hash or signed artifact establishes identity or custody", lowered)
        self.assertIn("must not contain production credentials", lowered)
        for stale_claim in (
            "the live system handles real money",
            "acknowledgement within **48 hours**",
            "resolution timeline communicated within **5 business days**",
            "kraken execution dashboard | ✅ active",
            "evidence ledger api | ✅ active",
        ):
            self.assertNotIn(stale_claim, lowered)

    def test_contribution_policy_preserves_evidence_and_authority_boundaries(self):
        text = (ROOT / "CONTRIBUTING.md").read_text(encoding="utf-8")
        lowered = text.casefold()

        self.assertIn("evidence before claims", lowered)
        self.assertIn("negative results", lowered)
        self.assertIn("historical evidence packets and receipts should not be rewritten", lowered)
        self.assertIn("legal actions outside the code change", lowered)
        self.assertNotIn("production-grade institutional intelligence platform", lowered)
        self.assertNotIn("the live dashboards, evidence ledger, and site infrastructure", lowered)

    def test_every_external_workflow_action_is_immutably_pinned(self):
        failures = []
        action_count = 0

        workflow_paths = [
            *WORKFLOW_DIR.glob("*.yml"),
            *WORKFLOW_DIR.glob("*.yaml"),
        ]
        for path in sorted(workflow_paths):
            text = path.read_text(encoding="utf-8")
            for match in ACTION_USE_RE.finditer(text):
                action = match.group(1)
                comment = match.group(2)
                if action.startswith("./"):
                    continue
                action_count += 1
                if "@" not in action:
                    failures.append(f"{path.name}: missing action ref: {action}")
                    continue
                _, ref = action.rsplit("@", 1)
                if FULL_COMMIT_RE.fullmatch(ref) is None:
                    failures.append(
                        f"{path.name}: external action is not pinned to a full commit: {action}"
                    )
                if not comment:
                    failures.append(
                        f"{path.name}: pinned action lacks a human-readable version comment: {action}"
                    )

        self.assertGreater(action_count, 0)
        self.assertEqual(failures, [], "\n".join(failures))


if __name__ == "__main__":
    unittest.main()
