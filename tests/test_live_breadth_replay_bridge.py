from __future__ import annotations

import importlib.util
import json
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "code" / "ops" / "BUILD_LIVE_BREADTH_REPLAY_BRIDGE.py"


def load_module():
    spec = importlib.util.spec_from_file_location("live_breadth_replay_bridge", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


class LiveBreadthReplayBridgeTests(unittest.TestCase):
    def test_bridge_counts_live_sources_and_keeps_claim_gate_closed(self) -> None:
        module = load_module()
        payload = module.build_bridge()

        self.assertEqual(payload["schema"], "live_breadth_replay_bridge_v1")
        self.assertGreater(payload["live_breadth_rollup"]["provider_count"], 0)
        self.assertGreater(payload["live_breadth_rollup"]["measured_count"], 0)
        self.assertFalse(payload["claim_gate"]["ready_for_portal_upload"])
        self.assertFalse(payload["claim_gate"]["ready_for_submit"])
        self.assertFalse(payload["claim_gate"]["live_data_proves_grant_merit"])
        self.assertFalse(payload["claim_gate"]["live_data_proves_trading_profit"])

    def test_dice_lane_requires_live_replay_not_direct_proof(self) -> None:
        module = load_module()
        payload = module.build_bridge()
        lanes = {row["grant_lane"]: row for row in payload["grant_lanes"]}

        self.assertIn("DICE", lanes)
        self.assertEqual(lanes["DICE"]["claim_status"], "live_data_not_direct_DICE_proof")
        self.assertEqual(lanes["DICE"]["best_use_of_live_breadth"], "primary_frozen_live_replay_with_synthetic_controls")
        self.assertIn("secondary control lane", lanes["DICE"]["why_synthetic_still_matters"])
        self.assertIn("task graphs", lanes["DICE"]["next_replay_adapter"])
        self.assertIn("KRAKEN", lanes["DICE"]["candidate_live_sources"])
        self.assertIn("EIA", lanes["DICE"]["candidate_live_sources"])

    def test_markdown_names_live_first_evidence_ladder_and_blocks_overclaims(self) -> None:
        module = load_module()
        payload = module.build_bridge()
        markdown = module.render_markdown(payload)
        serialized = (json.dumps(payload) + markdown).lower()

        self.assertIn("live breadth is the promoted evidence lane", markdown.lower())
        self.assertIn("live_source_manifest_and_hash", markdown)
        self.assertIn("synthetic_primary_evidence: false", markdown)
        self.assertIn("frozen_live_replay_hash_manifested", markdown)
        self.assertIn("live_data_proves_grant_merit: false", markdown)
        self.assertIn("live_data_proves_trading_profit: false", markdown)
        self.assertFalse(payload["claim_gate"]["synthetic_primary_evidence"])
        self.assertNotIn('"ready_for_portal_upload": true', serialized)
        self.assertNotIn('"ready_for_submit": true', serialized)
        self.assertNotIn("sk-" + "proj", serialized)
        self.assertNotRegex(serialized, r"uei\s+[a-z0-9]{8,16}")
        self.assertNotRegex(serialized, r"cage/?ncage\s+[a-z0-9]{3,10}")

    def test_write_bridge_outputs_files(self) -> None:
        module = load_module()
        payload = module.build_bridge()
        with tempfile.TemporaryDirectory() as temp_dir:
            old_out = module.OUT
            old_grants = module.GRANTS
            old_json = module.OUT_JSON
            old_md = module.OUT_MD
            try:
                module.OUT = Path(temp_dir) / "out"
                module.GRANTS = Path(temp_dir) / "grant_submissions"
                module.OUT_JSON = module.OUT / "live_breadth_replay_bridge_latest.json"
                module.OUT_MD = module.GRANTS / "LIVE_BREADTH_REPLAY_BRIDGE_2026-06-20.md"
                module.write_bridge(payload)
                self.assertTrue(module.OUT_JSON.exists())
                self.assertTrue(module.OUT_MD.exists())
            finally:
                module.OUT = old_out
                module.GRANTS = old_grants
                module.OUT_JSON = old_json
                module.OUT_MD = old_md


if __name__ == "__main__":
    unittest.main()
