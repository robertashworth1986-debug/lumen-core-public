import importlib.util
import sys
import tempfile
import unittest
from pathlib import Path


MODULE_PATH = Path(__file__).resolve().parents[1] / "architecture_validation_engine.py"
SPEC = importlib.util.spec_from_file_location("architecture_validation_engine", MODULE_PATH)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
sys.modules[SPEC.name] = MODULE
SPEC.loader.exec_module(MODULE)


class ArchitectureEngineTests(unittest.TestCase):
    def seed(self):
        return {
            "architectures": [{
                "id": "test_arch",
                "name": "Test Architecture",
                "aliases": ["Test Architecture", "TestArch"],
                "role": "test",
                "current_evidence_class": ["synthetic"],
                "patent_sensitive": False,
                "public_boundary": "simulation only",
            }]
        }

    def test_detects_code_test_and_evidence_markers(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            (root / "code").mkdir()
            (root / "tests").mkdir()
            (root / "code" / "test_arch.py").write_text(
                "Test Architecture baseline locked metric SHA256 manifest "
                "negative result claim boundary deterministic validation seed source dataset",
                encoding="utf-8",
            )
            (root / "tests" / "test_test_arch.py").write_text(
                "TestArch reproducible test", encoding="utf-8"
            )
            result = MODULE.scan([root], self.seed(), 100_000, True)
            record = result["architectures"][0]
            self.assertEqual(record["status"], "detected")
            self.assertIn("code", record["validation"]["categories"])
            self.assertIn("test", record["validation"]["categories"])
            self.assertGreaterEqual(record["validation"]["score"], 60)

    def test_negated_risk_is_boundary_not_unbounded_claim(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            (root / "doc.md").write_text(
                "Test Architecture is not flight-ready and does not claim guaranteed ROI.",
                encoding="utf-8",
            )
            result = MODULE.scan([root], self.seed(), 100_000, False)
            validation = result["architectures"][0]["validation"]
            self.assertEqual(validation["claim_risk"], "controlled")
            self.assertEqual(validation["unbounded_risk_phrases"], [])

    def test_positive_risk_is_flagged(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            (root / "pitch.md").write_text(
                "Test Architecture delivers guaranteed performance.",
                encoding="utf-8",
            )
            result = MODULE.scan([root], self.seed(), 100_000, False)
            validation = result["architectures"][0]["validation"]
            self.assertEqual(validation["claim_risk"], "high")
            self.assertIn("guaranteed performance", validation["unbounded_risk_phrases"])

    def test_engine_is_read_only(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            source = root / "source.py"
            source.write_text("TestArch baseline", encoding="utf-8")
            before = source.read_bytes()
            MODULE.scan([root], self.seed(), 100_000, True)
            self.assertEqual(before, source.read_bytes())


if __name__ == "__main__":
    unittest.main()
