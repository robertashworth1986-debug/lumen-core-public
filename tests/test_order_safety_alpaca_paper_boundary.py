from __future__ import annotations

import os
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

import requests


ROOT = Path(__file__).resolve().parents[1]
CODE = ROOT / "code"
if str(CODE) not in sys.path:
    sys.path.insert(0, str(CODE))

from execution import alpaca_paper_executor as paper  # noqa: E402


class FakeResponse:
    def __init__(self, status_code: int, payload=None, text: str = "") -> None:
        self.status_code = status_code
        self._payload = payload if payload is not None else {}
        self.text = text

    def raise_for_status(self) -> None:
        if self.status_code >= 400:
            raise RuntimeError(f"HTTP {self.status_code}")

    def json(self):
        return self._payload


class FakeSession:
    def __init__(self, response: FakeResponse) -> None:
        self.response = response
        self.calls = []
        self.headers = {}

    def request(self, method, url, **kwargs):
        self.calls.append({"method": method, "url": url, **kwargs})
        return self.response


class AlpacaPaperBoundaryTests(unittest.TestCase):
    def test_exact_origins_are_the_only_allowed_values(self) -> None:
        for value in (None, "", paper.PAPER_TRADING_ORIGIN, paper.PAPER_TRADING_ORIGIN + "/"):
            with self.subTest(value=value):
                self.assertEqual(
                    paper.normalize_paper_trading_base(value),
                    paper.PAPER_TRADING_ORIGIN,
                )

        rejected = (
            "http://paper-api.alpaca.markets",
            "https://api.alpaca.markets",
            "https://paper-api.alpaca.markets.evil.example",
            "https://user@paper-api.alpaca.markets",
            "https://paper-api.alpaca.markets:443",
            "https://paper-api.alpaca.markets/v2",
            "https://paper-api.alpaca.markets?redirect=1",
            "https://paper-api.alpaca.markets#fragment",
        )
        for value in rejected:
            with self.subTest(value=value):
                with self.assertRaises(paper.PaperEndpointError):
                    paper.normalize_paper_trading_base(value)

    def test_generic_base_override_cannot_select_production(self) -> None:
        with patch.dict(
            os.environ,
            {
                "ALPACA_API_KEY": "paper-key",
                "ALPACA_API_SECRET": "paper-secret",
                "ALPACA_BASE_URL": "https://api.alpaca.markets",
            },
            clear=True,
        ):
            with self.assertRaises(paper.PaperEndpointError):
                paper.load_api_keys()

        with patch.dict(
            os.environ,
            {
                "ALPACA_API_KEY": "paper-key",
                "ALPACA_API_SECRET": "paper-secret",
                "ALPACA_PAPER_BASE_URL": paper.PAPER_TRADING_ORIGIN,
                "ALPACA_BASE_URL": "https://api.alpaca.markets",
            },
            clear=True,
        ):
            keys = paper.load_api_keys()
        self.assertEqual(keys["ALPACA_PAPER_BASE_URL"], paper.PAPER_TRADING_ORIGIN)

    def test_client_rejects_bad_base_before_session_creation(self) -> None:
        with self.assertRaises(paper.PaperEndpointError):
            paper.AlpacaPaperClient(
                "paper-key",
                "paper-secret",
                trading_base="https://api.alpaca.markets",
            )

    def test_redirects_are_blocked_and_not_followed(self) -> None:
        client = paper.AlpacaPaperClient("paper-key", "paper-secret")
        client.session = FakeSession(FakeResponse(302))
        with self.assertRaises(paper.PaperEndpointError):
            client.get_account()
        self.assertEqual(len(client.session.calls), 1)
        self.assertFalse(client.session.calls[0]["allow_redirects"])
        self.assertEqual(client.session.calls[0]["url"], paper.PAPER_TRADING_ORIGIN + "/v2/account")

    def test_mutations_cannot_target_data_origin(self) -> None:
        client = paper.AlpacaPaperClient("paper-key", "paper-secret")
        fake = FakeSession(FakeResponse(200, payload={"ok": True}, text="{}"))
        client.session = fake
        with self.assertRaises(paper.PaperEndpointError):
            client._request_json(
                "POST",
                paper.PAPER_DATA_ORIGIN + "/v2/orders",
                payload={"symbol": "AAPL"},
            )
        self.assertEqual(fake.calls, [])

    def test_mocked_order_submission_remains_on_exact_paper_origin(self) -> None:
        client = paper.AlpacaPaperClient("paper-key", "paper-secret")
        fake = FakeSession(
            FakeResponse(
                200,
                payload={"id": "paper-order"},
                text='{"id":"paper-order"}',
            )
        )
        client.session = fake
        result = client.submit_buy("AAPL", 25.0)
        self.assertEqual(result["id"], "paper-order")
        self.assertEqual(len(fake.calls), 1)
        self.assertEqual(fake.calls[0]["url"], paper.PAPER_TRADING_ORIGIN + "/v2/orders")
        self.assertFalse(fake.calls[0]["allow_redirects"])

    def test_lost_submission_response_never_replays_an_accepted_paper_buy(self) -> None:
        client = paper.AlpacaPaperClient("paper-key", "paper-secret")
        accepted_orders = []

        class LostResponseSession:
            def request(self, method, url, **kwargs):
                # The broker accepts the order, then the response is lost. A
                # repeated request would append another accepted order here.
                accepted_orders.append(kwargs["json"])
                raise requests.exceptions.Timeout("fixture: response lost after acceptance")

        client.session = LostResponseSession()
        with patch.object(paper.time, "sleep") as sleep:
            with self.assertRaises(requests.exceptions.Timeout):
                client.submit_buy("AAPL", 25)
        self.assertEqual(len(accepted_orders), 1)
        sleep.assert_not_called()

    def test_failed_private_mutations_never_retry_but_account_reads_do(self) -> None:
        client = paper.AlpacaPaperClient("paper-key", "paper-secret")

        class RetrySession:
            def __init__(self):
                self.calls = []

            def request(self, method, url, **kwargs):
                self.calls.append((method, url))
                if len(self.calls) == 1:
                    raise requests.exceptions.ConnectionError("fixture: ambiguous disconnect")
                return FakeResponse(200, payload={"equity": "1000"}, text='{"equity":"1000"}')

        for method in ("POST", "DELETE", "PATCH", "PUT"):
            with self.subTest(method=method):
                fake = RetrySession()
                client.session = fake
                with patch.object(paper.time, "sleep") as sleep:
                    with self.assertRaises(requests.exceptions.ConnectionError):
                        client._request_json(method, paper.PAPER_TRADING_ORIGIN + "/v2/orders")
                self.assertEqual(len(fake.calls), 1)
                sleep.assert_not_called()

        fake = RetrySession()
        client.session = fake
        with patch.object(paper.time, "sleep") as sleep:
            self.assertEqual(client.get_account(), {"equity": "1000"})
        self.assertEqual(len(fake.calls), 2)
        sleep.assert_called_once()


if __name__ == "__main__":
    unittest.main()
