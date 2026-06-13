import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CODE = ROOT / "code"
if str(CODE) not in sys.path:
    sys.path.insert(0, str(CODE))

from dice_preliminary_benchmark import EVIDENCE_BOUNDARY, run_benchmark


class DicePreliminaryBenchmarkTests(unittest.TestCase):
    def test_benchmark_writes_bounded_reproducible_artifacts(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            out = Path(temp_dir)
            result = run_benchmark(
                out_dir=out,
                seeds=3,
                agents=60,
                tasks=120,
                roles=6,
            )

            self.assertEqual(result["evidence_boundary"], EVIDENCE_BOUNDARY)
            self.assertEqual(result["configuration"]["seeds"], 3)
            self.assertIn("centralized_baseline", result["aggregate"])
            self.assertIn(
                "peer_auction_with_local_control",
                result["aggregate"],
            )
            self.assertTrue((out / "trials.csv").exists())
            self.assertTrue((out / "SCORECARD.md").exists())

            manifest = json.loads(
                (out / "manifest.sha256.json").read_text(encoding="utf-8")
            )
            self.assertEqual(
                set(manifest["files"]),
                {"trials.csv", "summary.json", "SCORECARD.md"},
            )
            for metadata in manifest["files"].values():
                self.assertEqual(len(metadata["sha256"]), 64)


if __name__ == "__main__":
    unittest.main()
