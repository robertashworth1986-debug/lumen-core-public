from __future__ import annotations

import hashlib
import importlib.util
import json
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "code" / "ops" / "BUILD_DICE_LIVE_BREADTH_REPLAY.py"


def load_module():
    spec = importlib.util.spec_from_file_location("dice_live_breadth_replay", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def write_kraken_csv(path: Path, rows: int = 72) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    lines = ["time,open,high,low,close,vwap,volume,count"]
    price = 100.0
    for index in range(rows):
        drift = 1.0 + ((index % 7) - 3) * 0.001
        price *= drift
        high = price * (1.0 + 0.002 + (index % 3) * 0.001)
        low = price * (1.0 - 0.002)
        count = 0 if index % 19 == 0 else 5 + (index % 11)
        lines.append(
            f"2026-01-{1 + index // 24:02d}T{index % 24:02d}:00:00Z,"
            f"{price:.6f},{high:.6f},{low:.6f},{price:.6f},{price:.6f},"
            f"{1000 + index:.2f},{count}"
        )
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def write_eia_csv(path: Path, rows: int = 72) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    lines = ["period,respondent,respondent-name,type,type-name,value,value-units"]
    for index in range(rows):
        value = 25000 + (index % 24) * 180 + ((index % 5) - 2) * 22
        lines.append(
            f"2026-01-{1 + index // 24:02d}T{index % 24:02d},CISO,"
            f"California ISO,D,Demand,{value},megawatthours"
        )
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


class DiceLiveBreadthReplayTests(unittest.TestCase):
    def test_discovers_kraken_and_eia_sources_with_hashes(self) -> None:
        module = load_module()
        with tempfile.TemporaryDirectory() as temp_dir:
            temp = Path(temp_dir)
            module.KRAKEN_HISTORY_DIR = temp / "kraken"
            module.EIA_OUT_DIR = temp / "eia"
            write_kraken_csv(module.KRAKEN_HISTORY_DIR / "ohlc_TEST_USD.csv")
            write_eia_csv(module.EIA_OUT_DIR / "live_eia_ciso.csv")

            sources = module.discover_sources(max_kraken=1, max_eia=1)

        self.assertEqual(len(sources), 2)
        self.assertEqual({source["source_type"] for source in sources}, {"market_execution", "power_grid"})
        self.assertTrue(all(len(source["sha256"]) == 64 for source in sources))

    def test_build_replay_freezes_sources_and_keeps_claim_gate_closed(self) -> None:
        module = load_module()
        with tempfile.TemporaryDirectory() as temp_dir:
            temp = Path(temp_dir)
            module.KRAKEN_HISTORY_DIR = temp / "kraken"
            module.EIA_OUT_DIR = temp / "eia"
            write_kraken_csv(module.KRAKEN_HISTORY_DIR / "ohlc_TEST_USD.csv")
            write_eia_csv(module.EIA_OUT_DIR / "live_eia_ciso.csv")

            out_dir = temp / "run"
            summary = module.build_replay(
                out_dir=out_dir,
                max_kraken=1,
                max_eia=1,
                window_size=16,
                scenarios_per_source=2,
                agents=60,
                roles=6,
                task_multiplier=2,
            )

            self.assertEqual(summary["schema"], "dice_live_breadth_replay_v1")
            self.assertEqual(summary["source_manifest"]["source_count"], 2)
            self.assertEqual(summary["configuration"]["scenario_count"], 4)
            self.assertFalse(summary["claim_gate"]["ready_for_portal_upload"])
            self.assertFalse(summary["claim_gate"]["ready_for_submit"])
            self.assertFalse(summary["claim_gate"]["live_replay_proves_dice_metric_attainment"])
            self.assertFalse(summary["claim_gate"]["synthetic_primary_evidence"])
            self.assertEqual(
                summary["evidence_mode"],
                "primary_live_pulled_source_rows_with_deterministic_replay_labels",
            )
            self.assertEqual(summary["primary_evidence_source"], "frozen_live_pulled_rows")
            self.assertIn("secondary_control", summary["synthetic_role"])
            self.assertIn("Frozen live-pulled", summary["evidence_boundary"])
            self.assertEqual(
                summary["paired_metrics"]["safe_completion_rate"]["scenario_count"],
                4,
            )

            manifest = json.loads((out_dir / "manifest.sha256.json").read_text(encoding="utf-8"))
            for name, metadata in manifest["files"].items():
                actual = hashlib.sha256((out_dir / name).read_bytes()).hexdigest()
                self.assertEqual(actual, metadata["sha256"])

    def test_scorecard_blocks_overclaims_and_sensitive_leakage(self) -> None:
        module = load_module()
        with tempfile.TemporaryDirectory() as temp_dir:
            temp = Path(temp_dir)
            module.KRAKEN_HISTORY_DIR = temp / "kraken"
            module.EIA_OUT_DIR = temp / "eia"
            write_kraken_csv(module.KRAKEN_HISTORY_DIR / "ohlc_TEST_USD.csv")
            write_eia_csv(module.EIA_OUT_DIR / "live_eia_ciso.csv")

            summary = module.build_replay(
                out_dir=temp / "run",
                max_kraken=1,
                max_eia=1,
                window_size=16,
                scenarios_per_source=2,
                agents=60,
                roles=6,
                task_multiplier=2,
            )
            markdown = module.render_scorecard(summary)
            serialized = (json.dumps(summary) + markdown).lower()

        self.assertIn("live_replay_proves_dice_metric_attainment: false", markdown)
        self.assertIn("live_replay_proves_trading_profit: false", markdown)
        self.assertIn("synthetic_primary_evidence: false", markdown)
        self.assertIn("Primary evidence source: frozen_live_pulled_rows", markdown)
        self.assertNotIn('"ready_for_portal_upload": true', serialized)
        self.assertNotIn('"ready_for_submit": true', serialized)
        self.assertNotIn("sk-" + "proj", serialized)
        self.assertNotRegex(serialized, r"uei\s+[a-z0-9]{8,16}")
        self.assertNotRegex(serialized, r"cage/?ncage\s+[a-z0-9]{3,10}")

    def test_write_latest_outputs_can_be_redirected(self) -> None:
        module = load_module()
        with tempfile.TemporaryDirectory() as temp_dir:
            temp = Path(temp_dir)
            module.KRAKEN_HISTORY_DIR = temp / "kraken"
            module.EIA_OUT_DIR = temp / "eia"
            write_kraken_csv(module.KRAKEN_HISTORY_DIR / "ohlc_TEST_USD.csv")
            write_eia_csv(module.EIA_OUT_DIR / "live_eia_ciso.csv")
            summary = module.build_replay(
                out_dir=temp / "run",
                max_kraken=1,
                max_eia=1,
                window_size=16,
                scenarios_per_source=2,
                agents=60,
                roles=6,
                task_multiplier=2,
            )

            old_ops_out = module.OPS_OUT
            old_dice_dir = module.DICE_DIR
            old_ops_json = module.OPS_JSON
            old_ops_md = module.OPS_MD
            try:
                module.OPS_OUT = temp / "ops"
                module.DICE_DIR = temp / "grant_submissions" / "DICE_HR001126S0010"
                module.OPS_JSON = module.OPS_OUT / "dice_live_breadth_replay_latest.json"
                module.OPS_MD = module.DICE_DIR / "DICE_LIVE_BREADTH_REPLAY_2026-06-20.md"
                module.write_latest_outputs(summary)
                self.assertTrue(module.OPS_JSON.exists())
                self.assertTrue(module.OPS_MD.exists())
            finally:
                module.OPS_OUT = old_ops_out
                module.DICE_DIR = old_dice_dir
                module.OPS_JSON = old_ops_json
                module.OPS_MD = old_ops_md


if __name__ == "__main__":
    unittest.main()
