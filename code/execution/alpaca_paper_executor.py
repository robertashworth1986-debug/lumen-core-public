"""Exact-host paper-trading facade for the historical Alpaca executor.

The complete executor is preserved byte-for-byte in
``alpaca_paper_executor_legacy.py``. This canonical import surface accepts only
Alpaca's paper-trading origin and public data origin, rejects redirects, and
fails before any authenticated request when an override is not exactly paper.
"""

from __future__ import annotations

import sys
import time
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit

import requests


_HERE = Path(__file__).resolve().parent
_CODE_DIR = _HERE.parent
for _path in (_CODE_DIR, _HERE):
    if str(_path) not in sys.path:
        sys.path.insert(0, str(_path))

try:
    from . import alpaca_paper_executor_legacy as _legacy
except ImportError:  # Direct script execution.
    import alpaca_paper_executor_legacy as _legacy


PAPER_TRADING_ORIGIN = "https://paper-api.alpaca.markets"
PAPER_DATA_ORIGIN = "https://data.alpaca.markets"
PAPER_SANDBOX_POLICY = "exact_host_no_redirects"
_ORIGINAL_LOAD_API_KEYS = _legacy.load_api_keys


class PaperEndpointError(RuntimeError):
    """Raised before authenticated I/O when an endpoint leaves the paper lane."""


def _normalize_exact_origin(value: Any, expected: str, label: str) -> str:
    candidate = str(value or "").strip() or expected
    try:
        parsed = urlsplit(candidate)
        explicit_port = parsed.port
    except ValueError as exc:
        raise PaperEndpointError(f"invalid {label} origin") from exc

    expected_parts = urlsplit(expected)
    if (
        parsed.scheme != "https"
        or parsed.hostname != expected_parts.hostname
        or explicit_port is not None
        or parsed.username is not None
        or parsed.password is not None
        or parsed.path not in ("", "/")
        or bool(parsed.query)
        or bool(parsed.fragment)
    ):
        raise PaperEndpointError(
            f"{label} must be the exact approved paper/data origin"
        )
    return expected


def normalize_paper_trading_base(value: Any = None) -> str:
    return _normalize_exact_origin(value, PAPER_TRADING_ORIGIN, "Alpaca paper trading")


def normalize_paper_data_base(value: Any = None) -> str:
    return _normalize_exact_origin(value, PAPER_DATA_ORIGIN, "Alpaca market data")


def load_api_keys() -> dict[str, str]:
    keys = dict(_ORIGINAL_LOAD_API_KEYS())
    keys["ALPACA_PAPER_BASE_URL"] = normalize_paper_trading_base(
        keys.get("ALPACA_PAPER_BASE_URL")
    )
    keys["ALPACA_DATA_BASE_URL"] = normalize_paper_data_base(
        keys.get("ALPACA_DATA_BASE_URL")
    )
    return keys


class AlpacaPaperClient(_legacy.AlpacaPaperClient):
    """Legacy paper client with an exact-origin and no-redirect boundary."""

    def __init__(
        self,
        api_key: str,
        api_secret: str,
        trading_base: str | None = None,
        data_base: str | None = None,
    ) -> None:
        safe_trading = normalize_paper_trading_base(trading_base)
        safe_data = normalize_paper_data_base(data_base)
        super().__init__(
            api_key,
            api_secret,
            trading_base=safe_trading,
            data_base=safe_data,
        )
        self.trading_base = safe_trading
        self.data_base = safe_data

    @staticmethod
    def _assert_request_url(method: str, url: str) -> None:
        candidate = str(url or "").strip()
        try:
            parsed = urlsplit(candidate)
            explicit_port = parsed.port
        except ValueError as exc:
            raise PaperEndpointError("invalid Alpaca request URL") from exc
        origin = f"{parsed.scheme}://{parsed.hostname}" if parsed.hostname else ""
        if explicit_port is not None:
            origin = f"{origin}:{explicit_port}"

        allowed = {PAPER_TRADING_ORIGIN, PAPER_DATA_ORIGIN}
        if origin not in allowed or parsed.scheme != "https" or parsed.username or parsed.password:
            raise PaperEndpointError("Alpaca request escaped the approved paper/data origins")
        if method.upper() in {"POST", "DELETE", "PATCH", "PUT"} and origin != PAPER_TRADING_ORIGIN:
            raise PaperEndpointError("authenticated trading mutations are restricted to the paper origin")

    def _request_json(
        self,
        method: str,
        url: str,
        *,
        params: Any = None,
        payload: dict | None = None,
    ) -> Any:
        self._assert_request_url(method, url)
        last_error: Exception | None = None
        for attempt in range(1, self.max_retries + 1):
            try:
                response = self.session.request(
                    method,
                    url,
                    params=params,
                    json=payload,
                    timeout=20,
                    allow_redirects=False,
                )
                if 300 <= int(response.status_code) < 400:
                    raise PaperEndpointError("redirects are blocked for paper-trading requests")
                response.raise_for_status()
                if response.text.strip():
                    body = response.json()
                    if not isinstance(body, (dict, list)):
                        raise PaperEndpointError("Alpaca response JSON has an unexpected type")
                    return body
                return {"status": "ok"}
            except PaperEndpointError:
                raise
            except requests.exceptions.RequestException as exc:
                last_error = exc
                if attempt < self.max_retries:
                    time.sleep(min(2 * attempt, 5))
                    continue
                raise
        if last_error is not None:
            raise last_error
        return {}


# The preserved main loop resolves these names in its own module globals.
_legacy.load_api_keys = load_api_keys
_legacy.AlpacaPaperClient = AlpacaPaperClient

# Export the rest of the historical public surface without overriding guards.
for _name in dir(_legacy):
    if _name.startswith("_") or _name in globals():
        continue
    globals()[_name] = getattr(_legacy, _name)


def main() -> int:
    _legacy.main()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
