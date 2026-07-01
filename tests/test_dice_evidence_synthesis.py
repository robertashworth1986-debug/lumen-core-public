from __future__ import annotations

import importlib.util
import json
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "code" / "ops" / "BUILD_DICE_EVIDENCE_SYNTHESIS.py"


def load_module():
    spec = importlib.util.spec_from_file_location("dice_evidence_synthesis", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


class DiceEvidenceSynthesisTests(unittest.TestCase):
    def test_synthesis_includes_both_dice_evidence_lanes(self) -> None:
        module = load_module()
        payload = module.build_synthesis()

        self.assertEqual(payload["schema"], "dice_evidence_synthesis_v1")
        lanes = {row["lane"]: row for row in payload["source_runs"]}
        self.assertIn("preliminary_peer_mesh", lanes)
        self.assertIn("constraint_contract", lanes)
        self.assertIn("live_breadth_replay", lanes)
        self.assertIn("live_breadth_provenance_annex", lanes)
        self.assertFalse(payload["claim_gate"]["ready_for_portal_upload"])
        self.assertFalse(payload["claim_gate"]["ready_for_submit"])

    def test_preliminary_metrics_are_exactly_sourced(self) -> None:
        module = load_module()
        payload = module.build_synthesis()
        prelim = next(row for row in payload["source_runs"] if row["lane"] == "preliminary_peer_mesh")
        metrics = {row["metric"]: row for row in prelim["metrics"]}

        self.assertAlmostEqual(metrics["message_reduction_pct"]["mean"], 31.522522272906645)
        self.assertAlmostEqual(metrics["recovery_message_reduction_pct"]["mean"], 40.09997745348595)
        self.assertAlmostEqual(metrics["role_coherence_rate_points"]["mean"], 6.448913853243203)
        self.assertIn("Synthetic discrete-event software benchmark only", prelim["evidence_boundary"])

    def test_constraint_contract_names_robust_gains_and_failure_modes(self) -> None:
        module = load_module()
        payload = module.build_synthesis()
        contract = next(row for row in payload["source_runs"] if row["lane"] == "constraint_contract")

        self.assertEqual(contract["validation_condition_count"], 5)
        self.assertTrue(contract["robust_observations"]["safe_completion_delta_positive_all_conditions"])
        self.assertTrue(contract["robust_observations"]["constraint_violation_delta_negative_all_conditions"])
        self.assertTrue(contract["robust_observations"]["messages_per_safe_completion_delta_negative_all_conditions"])
        self.assertIn("monitor_shift", contract["known_failure_modes"]["false_rejection_ge_10pct_conditions"])
        self.assertIn("high_collusion_25pct", contract["known_failure_modes"]["false_rejection_ge_10pct_conditions"])
        self.assertIn("high_collusion_25pct", contract["known_failure_modes"]["compromised_assignment_worse_conditions"])

    def test_live_replay_lane_is_bounded_and_not_a_dice_proof(self) -> None:
        module = load_module()
        payload = module.build_synthesis()
        live = next(row for row in payload["source_runs"] if row["lane"] == "live_breadth_replay")
        metrics = {row["metric"]: row for row in live["metrics"]}

        self.assertIn("live", live["evidence_boundary"].lower())
        self.assertFalse(live["claim_gate"]["ready_for_portal_upload"])
        self.assertFalse(live["claim_gate"]["ready_for_submit"])
        self.assertFalse(live["claim_gate"]["live_replay_proves_dice_metric_attainment"])
        self.assertFalse(live["claim_gate"]["live_replay_proves_trading_profit"])
        self.assertFalse(live["claim_gate"]["synthetic_primary_evidence"])
        self.assertEqual(live["primary_evidence_source"], "frozen_live_pulled_rows")
        self.assertIn("primary_live_pulled", live["evidence_mode"])
        self.assertIn("source_count", live)
        self.assertIn("safe_completion_rate", metrics)

    def test_live_breadth_annex_is_bounded_and_promotes_only_measured_signal(self) -> None:
        module = load_module()
        payload = module.build_synthesis()
        annex = next(row for row in payload["source_runs"] if row["lane"] == "live_breadth_provenance_annex")

        self.assertEqual(annex["primary_evidence_mode"], "live_measured_delta_rows")
        self.assertGreater(annex["live_measured_hourly_value_usd"], 0)
        self.assertGreater(annex["live_measured_annual_value_usd"], 0)
        self.assertGreaterEqual(annex["context_only_annual_value_usd"], annex["live_measured_annual_value_usd"])
        self.assertFalse(annex["claim_gate"]["ready_for_portal_upload"])
        self.assertFalse(annex["claim_gate"]["ready_for_submit"])
        self.assertFalse(annex["claim_gate"]["grant_merit_proven"])
        self.assertFalse(annex["claim_gate"]["field_performance_proven"])
        self.assertFalse(annex["claim_gate"]["trading_profit_proven"])
        self.assertFalse(annex["claim_gate"]["context_only_promoted_as_live_proof"])

    def test_markdown_preserves_claim_boundaries_and_no_sensitive_leakage(self) -> None:
        module = load_module()
        payload = module.build_synthesis()
        markdown = module.render_markdown(payload)
        serialized = (json.dumps(payload) + markdown).lower()

        self.assertIn("## What This Supports", markdown)
        self.assertIn("## What This Does Not Support", markdown)
        self.assertIn("## Live-Breadth Replay Lane", markdown)
        self.assertIn("Primary evidence source: frozen_live_pulled_rows", markdown)
        self.assertIn("## Provenance-Gated Live-Breadth Annex", markdown)
        self.assertIn("synthetic_primary_evidence: false", markdown)
        self.assertIn("context_only_promoted_as_live_proof: false", markdown)
        self.assertIn("Do not claim DICE performance has been proven.", markdown)
        self.assertIn("ready_for_portal_upload: false", markdown)
        self.assertIn("live-breadth replay proves field performance", markdown)
        self.assertNotRegex(serialized, r"uei\s+[a-z0-9]{8,16}")
        self.assertNotRegex(serialized, r"cage/?ncage\s+[a-z0-9]{3,10}")
        self.assertNotIn("sk-" + "proj", serialized)
        self.assertNotIn('"ready_for_portal_upload": true', serialized)

    def test_write_synthesis_outputs_files(self) -> None:
        module = load_module()
        payload = module.build_synthesis()
        with tempfile.TemporaryDirectory() as temp_dir:
            old_out = module.OUT
            old_dice_dir = module.DICE_DIR
            old_json = module.OUT_JSON
            old_md = module.OUT_MD
            try:
                module.OUT = Path(temp_dir) / "out"
                module.DICE_DIR = Path(temp_dir) / "grant_submissions" / "DICE_HR001126S0010"
                module.OUT_JSON = module.OUT / "dice_evidence_synthesis_latest.json"
                module.OUT_MD = module.DICE_DIR / "DICE_EVIDENCE_SYNTHESIS_2026-06-20.md"
                module.write_synthesis(payload)
                self.assertTrue(module.OUT_JSON.exists())
                self.assertTrue(module.OUT_MD.exists())
            finally:
                module.OUT = old_out
                module.DICE_DIR = old_dice_dir
                module.OUT_JSON = old_json
                module.OUT_MD = old_md


if __name__ == "__main__":
    unittest.main()
