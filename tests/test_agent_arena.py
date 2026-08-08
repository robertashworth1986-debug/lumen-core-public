import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
CODE = ROOT / "code"
if str(CODE) not in sys.path:
    sys.path.insert(0, str(CODE))

from agent_arena import (
    EVIDENCE_BOUNDARY,
    _git_state,
    _floor_from_config,
    canonical_json,
    load_config,
    merkle_root,
    paired_statistics,
    run_arena,
    run_floor,
    select_champion,
    sha256_text,
    verify_bundle,
)


class AgentArenaV5Tests(unittest.TestCase):
    def setUp(self):
        self.config_path = ROOT / "config" / "agent_arena_v5.json"

    def test_v2_to_v5_capabilities_are_locked(self):
        cfg = load_config(self.config_path)
        self.assertEqual(cfg["evidence_boundary"], EVIDENCE_BOUNDARY)
        self.assertEqual(set(cfg["capability_stages"]), {"v2", "v3", "v4", "v5"})
        self.assertEqual(len(cfg["agent_roles"]), 7)
        self.assertGreaterEqual(len(cfg["candidate_profiles"]), 4)
        self.assertGreaterEqual(sum(bool(x["holdout"]) for x in cfg["floors"]), 2)
        self.assertTrue(set(cfg["selection_seeds"]).isdisjoint(cfg["holdout_seeds"]))

    def test_full_arena_writes_and_verifies_v5_bundle(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            out = Path(temp_dir)
            summary = run_arena(
                out_dir=out,
                config_path=self.config_path,
                generated_utc="2026-08-06T23:00:00+00:00",
            )
            self.assertIn(summary["champion_profile"], summary["selection_summary"])
            self.assertEqual(summary["holdout_statistics"]["paired_trials"], 16)
            self.assertEqual(len(summary["event_chain_root_sha256"]), 64)
            self.assertEqual(len(summary["event_merkle_root_sha256"]), 64)
            self.assertTrue((out / "execution_receipt.json").is_file())
            verified = verify_bundle(out)
            self.assertEqual(verified["status"], "INTEGRITY_VERIFIED_UNSIGNED")
            self.assertEqual(verified["champion_profile"], summary["champion_profile"])
            self.assertEqual(summary["acceptance_gate"]["status"], "FAIL")
            self.assertGreater(summary["holdout_aggregate"][summary["champion_profile"]]["constraint_violations_total"], 0)
            self.assertEqual(summary["trust_assurance"]["status"], "NOT_DEMONSTRATED")

    def test_deterministic_core_replays_identically(self):
        with tempfile.TemporaryDirectory() as first, tempfile.TemporaryDirectory() as second:
            a = run_arena(
                Path(first),
                self.config_path,
                generated_utc="2026-08-06T23:00:00+00:00",
            )
            b = run_arena(
                Path(second),
                self.config_path,
                generated_utc="2026-08-06T23:00:00+00:00",
            )
            self.assertEqual(a["champion_profile"], b["champion_profile"])
            self.assertEqual(a["event_chain_root_sha256"], b["event_chain_root_sha256"])
            self.assertEqual(a["event_merkle_root_sha256"], b["event_merkle_root_sha256"])
            self.assertEqual((Path(first) / "events.jsonl").read_bytes(), (Path(second) / "events.jsonl").read_bytes())

    def test_manifest_tampering_fails_closed(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            out = Path(temp_dir)
            run_arena(out, self.config_path, generated_utc="2026-08-06T23:00:00+00:00")
            summary = out / "summary.json"
            summary.write_text(summary.read_text(encoding="utf-8") + " ", encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "byte-count mismatch|sha256 mismatch"):
                verify_bundle(out)

    def test_execution_receipt_tampering_fails_closed(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            out = Path(temp_dir)
            run_arena(out, self.config_path, generated_utc="2026-08-06T23:00:00+00:00")
            receipt_path = out / "execution_receipt.json"
            receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
            receipt["champion_profile"] = "forged"
            receipt_path.write_text(json.dumps(receipt, indent=2, sort_keys=True) + "\n", encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "execution receipt hash mismatch|custody mismatch"):
                verify_bundle(out)

    def test_self_rehashed_forged_receipt_fails_custody(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            out = Path(temp_dir)
            run_arena(out, self.config_path, generated_utc="2026-08-06T23:00:00+00:00")
            receipt_path = out / "execution_receipt.json"
            receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
            receipt["git_commit"] = "0" * 40
            receipt["platform"] = "forged-platform"
            receipt["evidence_boundary"] = "External validation established."
            body = {key: value for key, value in receipt.items() if key != "receipt_sha256"}
            receipt["receipt_sha256"] = sha256_text(canonical_json(body))
            receipt_path.write_text(json.dumps(receipt, indent=2, sort_keys=True) + "\n", encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "execution receipt custody mismatch"):
                verify_bundle(out)

    def test_release_bundle_rejects_custom_in_process_provider(self):
        def substitute_provider(role, observation, bounds):
            return {name: high for name, (_, high) in bounds.items()}

        with tempfile.TemporaryDirectory() as temp_dir:
            with self.assertRaisesRegex(ValueError, "only the committed deterministic_provider"):
                run_arena(
                    Path(temp_dir),
                    self.config_path,
                    provider=substitute_provider,
                    generated_utc="2026-08-06T23:00:00+00:00",
                )

    def test_invalid_scenario_semantics_fail_closed(self):
        base = json.loads(self.config_path.read_text(encoding="utf-8"))
        mutations = {
            "baseline bounds": lambda cfg: cfg["baseline_plan"].__setitem__("routing", 999),
            "negative telemetry noise": lambda cfg: cfg["floors"][0].__setitem__("telemetry_noise", -2),
            "negative selection weight": lambda cfg: cfg["champion_selection"].__setitem__("mean_score_weight", -1),
            "invalid trim threshold": lambda cfg: cfg["candidate_profiles"]["balanced"].__setitem__("trim_threshold", 99),
        }
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "scenario.json"
            for name, mutate in mutations.items():
                with self.subTest(name=name):
                    cfg = json.loads(json.dumps(base))
                    mutate(cfg)
                    path.write_text(json.dumps(cfg), encoding="utf-8")
                    with self.assertRaises(ValueError):
                        load_config(path)

    def test_provider_observation_blinds_holdout_and_attack_metadata(self):
        cfg = load_config(self.config_path)
        floor = _floor_from_config(next(x for x in cfg["floors"] if x["holdout"]))
        seen = []

        def inspecting_provider(role, observation, bounds):
            seen.append(set(observation))
            return {}

        run_floor(floor, cfg["holdout_seeds"][0], cfg, "balanced", inspecting_provider)
        forbidden = {"floor_id", "label", "holdout", "seed", "attack_mode", "compromised_observation"}
        self.assertTrue(seen)
        self.assertTrue(all(keys.isdisjoint(forbidden) for keys in seen))

    def test_dirty_git_source_fails_closed(self):
        with mock.patch("agent_arena.subprocess.check_output", return_value=" M code/agent_arena.py\n"):
            with self.assertRaisesRegex(ValueError, "clean Git worktree"):
                _git_state()

    def test_nan_agent_proposal_fails_closed(self):
        cfg = load_config(self.config_path)
        floor = _floor_from_config(next(x for x in cfg["floors"] if not x["holdout"]))

        def malicious(role, observation, bounds):
            return {"routing": float("nan")} if role == "router" else {}

        with self.assertRaisesRegex(ValueError, "must be finite"):
            run_floor(floor, cfg["selection_seeds"][0], cfg, "balanced", malicious)

    def test_undeclared_agent_control_fails_closed(self):
        cfg = load_config(self.config_path)
        floor = _floor_from_config(next(x for x in cfg["floors"] if not x["holdout"]))

        def malicious(role, observation, bounds):
            return {"secret_override": 999.0}

        with self.assertRaisesRegex(ValueError, "undeclared controls"):
            run_floor(floor, cfg["selection_seeds"][0], cfg, "balanced", malicious)

    def test_champion_selection_cannot_see_holdout(self):
        cfg = load_config(self.config_path)
        selection_floor = _floor_from_config(next(x for x in cfg["floors"] if not x["holdout"]))
        rows = []
        for profile in cfg["candidate_profiles"]:
            for seed in cfg["selection_seeds"][:3]:
                result, _ = run_floor(selection_floor, seed, cfg, profile)
                rows.append(result)
        champion_a, summary_a = select_champion(rows, cfg)
        mutated = json.loads(json.dumps(cfg))
        for floor in mutated["floors"]:
            if floor["holdout"]:
                floor["demand"] = 999.0
                floor["failure_rate"] = 0.95
        champion_b, summary_b = select_champion(rows, mutated)
        self.assertEqual(champion_a, champion_b)
        self.assertEqual(canonical_json(summary_a), canonical_json(summary_b))

    def test_byzantine_floor_records_trust_and_accepted_roles(self):
        cfg = load_config(self.config_path)
        floor = _floor_from_config(next(x for x in cfg["floors"] if x["attack_mode"] == "byzantine_controls" and not x["holdout"]))
        result, trace = run_floor(floor, cfg["selection_seeds"][0], cfg, "robust_consensus")
        self.assertEqual(result.attack_mode, "byzantine_controls")
        self.assertTrue(trace["trust_scores"])
        self.assertTrue(trace["accepted_roles"])
        self.assertLessEqual(set(trace["accepted_roles"]), set(cfg["agent_roles"]))

    def test_bootstrap_statistics_are_deterministic_and_ordered(self):
        cfg = load_config(self.config_path)
        floors = [_floor_from_config(x) for x in cfg["floors"] if x["holdout"]]
        baseline = []
        candidate = []
        from agent_arena import baseline_result

        for seed in cfg["holdout_seeds"][:3]:
            for floor in floors:
                baseline.append(baseline_result(floor, seed, cfg))
                row, _ = run_floor(floor, seed, cfg, "robust_consensus")
                candidate.append(row)
        first = paired_statistics(baseline, candidate, cfg)
        second = paired_statistics(baseline, candidate, cfg)
        self.assertEqual(canonical_json(first), canonical_json(second))
        low, high = first["score_delta"]["floor_cluster_bootstrap_ci"]
        self.assertLessEqual(low, high)
        self.assertEqual(first["energy_delta"]["adverse_tail"], "upper")
        self.assertEqual(first["score_delta"]["adverse_tail"], "lower")

    def test_merkle_root_is_order_sensitive(self):
        a = [sha256_text("a"), sha256_text("b"), sha256_text("c")]
        b = [a[1], a[0], a[2]]
        self.assertNotEqual(merkle_root(a), merkle_root(b))
        self.assertEqual(merkle_root(a), merkle_root(list(a)))

    def test_event_hash_definition_remains_canonical(self):
        event = {"z": 1, "a": "x", "previous_event_sha256": "0" * 64}
        self.assertEqual(
            sha256_text(canonical_json(event)),
            sha256_text('{"a":"x","previous_event_sha256":"' + "0" * 64 + '","z":1}'),
        )


if __name__ == "__main__":
    unittest.main()
