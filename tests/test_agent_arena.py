import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CODE = ROOT / "code"
if str(CODE) not in sys.path:
    sys.path.insert(0, str(CODE))

from agent_arena import (
    EVIDENCE_BOUNDARY,
    canonical_json,
    load_config,
    run_arena,
    run_floor,
    sha256_text,
    verify_bundle,
)


class AgentArenaTests(unittest.TestCase):
    def setUp(self):
        self.config = ROOT / "config" / "agent_arena_v1.json"

    def test_config_is_locked_and_has_one_holdout(self):
        config = load_config(self.config)
        self.assertEqual(config["evidence_boundary"], EVIDENCE_BOUNDARY)
        self.assertEqual(sum(bool(x["holdout"]) for x in config["floors"]), 1)
        self.assertEqual(len(config["agent_roles"]), 5)
        self.assertGreaterEqual(len(config["seeds"]), 10)

    def test_arena_writes_and_verifies_hash_chained_bundle(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            out = Path(temp_dir)
            result = run_arena(
                out_dir=out,
                config_path=self.config,
                generated_utc="2026-08-06T00:00:00+00:00",
            )
            self.assertEqual(result["evidence_boundary"], EVIDENCE_BOUNDARY)
            self.assertIn("locked_baseline", result["aggregate"])
            self.assertIn("specialist_team_with_red_team", result["aggregate"])
            self.assertEqual(len(result["event_chain_root_sha256"]), 64)
            self.assertTrue((out / "manifest.sha256.json").is_file())
            verified = verify_bundle(out)
            self.assertEqual(verified["status"], "VERIFIED")
            self.assertGreater(verified["event_lines"], 10)

    def test_same_lock_and_timestamp_are_reproducible_except_git_identity(self):
        with tempfile.TemporaryDirectory() as first, tempfile.TemporaryDirectory() as second:
            a = run_arena(
                out_dir=Path(first),
                config_path=self.config,
                generated_utc="2026-08-06T00:00:00+00:00",
            )
            b = run_arena(
                out_dir=Path(second),
                config_path=self.config,
                generated_utc="2026-08-06T00:00:00+00:00",
            )
            a = dict(a)
            b = dict(b)
            a.pop("git_commit", None)
            b.pop("git_commit", None)
            self.assertEqual(canonical_json(a), canonical_json(b))
            self.assertEqual(
                (Path(first) / "events.jsonl").read_bytes(),
                (Path(second) / "events.jsonl").read_bytes(),
            )

    def test_tampering_fails_closed(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            out = Path(temp_dir)
            run_arena(
                out_dir=out,
                config_path=self.config,
                generated_utc="2026-08-06T00:00:00+00:00",
            )
            summary = out / "summary.json"
            summary.write_text(summary.read_text(encoding="utf-8") + " ", encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "byte-count mismatch|sha256 mismatch"):
                verify_bundle(out)

    def test_malformed_external_agent_proposal_fails_closed(self):
        config = load_config(self.config)
        from agent_arena import _floor_from_config

        floor = _floor_from_config(config["floors"][0])

        def malicious(role, observation, bounds):
            if role == "router":
                return {"routing": float("nan")}
            return {}

        with self.assertRaisesRegex(ValueError, "must be finite"):
            run_floor(floor, config["seeds"][0], config, malicious)

    def test_undeclared_agent_control_fails_closed(self):
        config = load_config(self.config)
        from agent_arena import _floor_from_config

        floor = _floor_from_config(config["floors"][0])

        def malicious(role, observation, bounds):
            return {"secret_override": 999.0}

        with self.assertRaisesRegex(ValueError, "undeclared controls"):
            run_floor(floor, config["seeds"][0], config, malicious)

    def test_event_hash_definition_is_unambiguous(self):
        event = {"z": 1, "a": "x", "previous_event_sha256": "0" * 64}
        self.assertEqual(
            sha256_text(canonical_json(event)),
            sha256_text('{"a":"x","previous_event_sha256":"' + "0" * 64 + '","z":1}'),
        )


if __name__ == "__main__":
    unittest.main()
