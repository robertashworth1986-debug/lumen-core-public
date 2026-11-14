import importlib.util
import json
import pathlib
import sys
import tempfile
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "experiments" / "energy_multisource" / "run_energy_wedge_sweep.py"
REGISTRY = ROOT / "config" / "live_source_registry.json"

spec = importlib.util.spec_from_file_location("energy_wedge_sweep", SCRIPT)
mod = importlib.util.module_from_spec(spec)
assert spec.loader is not None
sys.modules[spec.name] = mod
spec.loader.exec_module(mod)


class EnergyMultiSourceTests(unittest.TestCase):
    def test_registry_public_sources_do_not_require_secrets(self):
        payload = json.loads(REGISTRY.read_text(encoding="utf-8"))
        rows = {row["source"]: row for row in payload["rows"]}
        for source in (
            "DOE_GDR_FORGE_1683",
            "DOE_GDR_FORGE_1109",
            "DOE_GDR_FORGE_1149",
            "NOAA_NDBC_WAVES",
            "USGS_GEOTHERMAL_OFR83250",
            "OEDI_AASG_EGS_WELLS",
        ):
            self.assertIn(source, rows)
            self.assertEqual(rows[source].get("auth_mode"), "public_no_key")
            self.assertEqual(rows[source].get("env"), "")

    def test_registration_alone_is_not_measured(self):
        payload = json.loads(REGISTRY.read_text(encoding="utf-8"))
        rows = {row["source"]: row for row in payload["rows"]}
        self.assertTrue(rows["DOE_GDR_FORGE_1683"].get("probe_ok"))
        self.assertFalse(rows["DOE_GDR_FORGE_1109"].get("probe_ok"))
        self.assertEqual(rows["USGS_GEOTHERMAL_OFR83250"].get("rows"), 0)

    def test_ndbc_parser_and_claim_boundary(self):
        lines = [
            "#YY MM DD hh mm WDIR WSPD GST WVHT DPD APD MWD PRES ATMP WTMP DEWP VIS PTDY TIDE",
            "2026 09 04 10 00 180 5.0 6.0 1.50 8.0 7.0 190 1015 25 26 20 10 0.1 1.0",
            "2026 09 04 11 00 185 5.5 6.5 1.60 8.2 7.1 195 1014 25 26 20 10 0.1 1.0",
        ]
        with tempfile.TemporaryDirectory() as tmp:
            path = pathlib.Path(tmp) / "test.txt"
            path.write_text("\n".join(lines) + "\n", encoding="utf-8")
            # Fewer than 30 samples must fail closed instead of fabricating a result.
            self.assertIsNone(mod.analyze_ndbc_file(path))

    def test_improvement_direction(self):
        self.assertAlmostEqual(mod.pct_improve(10.0, 9.0), 10.0)
        self.assertLess(mod.pct_improve(10.0, 11.0), 0.0)


if __name__ == "__main__":
    unittest.main()
