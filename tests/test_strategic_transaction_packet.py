import copy
import importlib.util
import tempfile
import unittest
from pathlib import Path


VERIFIER_PATH = Path("code/ops/VERIFY_STRATEGIC_TRANSACTION_PACKET.py")
PACKET_PATH = Path("config/strategic_transaction_packet_v1.json")
GRAPH_PATH = Path("config/evidence_graph_v1.json")

spec = importlib.util.spec_from_file_location(
    "verify_strategic_transaction_packet",
    VERIFIER_PATH,
)
if spec is None or spec.loader is None:
    raise RuntimeError(f"unable to load verifier from {VERIFIER_PATH}")
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)

load_json_strict = module.load_json_strict
verify_packet = module.verify_packet


class StrategicTransactionPacketTests(unittest.TestCase):
    def setUp(self):
        self.packet = load_json_strict(PACKET_PATH)
        self.graph = load_json_strict(GRAPH_PATH, max_bytes=2_000_000)

    def test_current_packet_passes(self):
        result = verify_packet(self.packet, self.graph)
        self.assertTrue(result["valid"])
        self.assertEqual(result["transaction_option_count"], 5)
        self.assertFalse(result["binding_sale_authorized"])
        self.assertFalse(result["ip_transfer_authorized"])
        self.assertFalse(result["public_asking_price"])

    def test_binding_sale_authorization_rejected(self):
        packet = copy.deepcopy(self.packet)
        packet["founder_control"]["binding_sale_authorized"] = True
        with self.assertRaisesRegex(ValueError, "founder control"):
            verify_packet(packet, self.graph)

    def test_ip_transfer_authorization_rejected(self):
        packet = copy.deepcopy(self.packet)
        packet["founder_control"]["ip_transfer_authorized"] = True
        with self.assertRaisesRegex(ValueError, "founder control"):
            verify_packet(packet, self.graph)

    def test_public_asking_price_rejected(self):
        packet = copy.deepcopy(self.packet)
        packet["asking_price"]["public"] = True
        packet["asking_price"]["amount"] = 1_000_000
        packet["asking_price"]["currency"] = "USD"
        with self.assertRaisesRegex(ValueError, "public asking price"):
            verify_packet(packet, self.graph)

    def test_unknown_graph_node_rejected(self):
        packet = copy.deepcopy(self.packet)
        packet["public_assets"][0]["graph_node_id"] = "unknown-node"
        with self.assertRaisesRegex(ValueError, "unknown evidence node"):
            verify_packet(packet, self.graph)

    def test_graph_state_mismatch_rejected(self):
        packet = copy.deepcopy(self.packet)
        packet["public_assets"][0]["evidence_state"] = "external_complete"
        with self.assertRaisesRegex(ValueError, "state mismatch"):
            verify_packet(packet, self.graph)

    def test_duplicate_transaction_option_rejected(self):
        packet = copy.deepcopy(self.packet)
        packet["transaction_options"].append(
            copy.deepcopy(packet["transaction_options"][0])
        )
        with self.assertRaisesRegex(ValueError, "duplicate transaction option id"):
            verify_packet(packet, self.graph)

    def test_missing_transaction_structure_rejected(self):
        packet = copy.deepcopy(self.packet)
        packet["transaction_options"].pop()
        with self.assertRaisesRegex(ValueError, "canonical set"):
            verify_packet(packet, self.graph)

    def test_option_without_non_transfer_boundary_rejected(self):
        packet = copy.deepcopy(self.packet)
        packet["transaction_options"][0]["does_not_authorize"] = [
            "unsupported_warranties"
        ]
        with self.assertRaisesRegex(ValueError, "non-transfer boundary"):
            verify_packet(packet, self.graph)

    def test_missing_claim_boundary_rejected(self):
        packet = copy.deepcopy(self.packet)
        packet["claim_boundaries"].remove("no_revenue_claim")
        with self.assertRaisesRegex(ValueError, "claim boundaries"):
            verify_packet(packet, self.graph)

    def test_unofficial_contact_domain_rejected(self):
        packet = copy.deepcopy(self.packet)
        packet["public_contact_path"] = "https://example.com/buy"
        with self.assertRaisesRegex(ValueError, "official HTTPS LumenCore domain"):
            verify_packet(packet, self.graph)

    def test_duplicate_json_key_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "duplicate.json"
            path.write_text('{"schema_version":"1.0","schema_version":"1.0"}', encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "duplicate JSON key"):
                load_json_strict(path)

    def test_non_finite_json_number_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "nan.json"
            path.write_text('{"amount":NaN}', encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "non-finite JSON number"):
                load_json_strict(path)


if __name__ == "__main__":
    unittest.main()
