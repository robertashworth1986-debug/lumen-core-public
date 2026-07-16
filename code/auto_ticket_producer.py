"""Validate-only facade for the auto-ticket producer.

The historical adaptive scanner and ticket logic is preserved in
``auto_ticket_producer_legacy.py``. This public module keeps ticket generation
available for live-data evaluation while forcing every ticket to Kraken
validate-only mode and disabling automatic approval/fire behavior.
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any


_CODE_DIR = Path(__file__).resolve().parent
if str(_CODE_DIR) not in sys.path:
    sys.path.insert(0, str(_CODE_DIR))

import auto_ticket_producer_legacy as _legacy
from auto_ticket_producer_legacy import *  # noqa: E402,F401,F403


ORDER_PROMOTION_STAGE = "live_data_no_orders"
_ORIGINAL_EMIT_TICKETS = _legacy.emit_tickets


def _safe_runtime_config(
    runtime_cfg: dict[str, Any] | None,
) -> dict[str, Any]:
    if isinstance(runtime_cfg, dict):
        safe = dict(runtime_cfg)
    else:
        try:
            loaded = _legacy._read_runtime_config(
                default_threshold=None,
                default_enabled=True,
            )
            safe = dict(loaded) if isinstance(loaded, dict) else {}
        except Exception:
            safe = {}

    safe.update(
        {
            "enabled": True,
            "auto_fire_score": None,
            "max_auto_fires_per_cycle": 0,
            "max_auto_fires_per_cycle_moonshot": 0,
            "max_auto_fires_per_cycle_quickhit": 0,
            "max_auto_fires_per_cycle_swing": 0,
            "order_promotion_stage": ORDER_PROMOTION_STAGE,
        }
    )
    return safe


def emit_tickets(
    use_cached: bool,
    validate: bool,
    controller: str,
    bankroll: float,
    top_n: int,
    auto_fire_score: float | None = None,
    gateway_url: str = "http://127.0.0.1:8787",
    scan_max_age_sec: float = _legacy.SCAN_MAX_AGE_SEC_DEFAULT,
    runtime_cfg: dict | None = None,
) -> dict:
    """Generate research tickets, always validate-only and never auto-fire."""

    del validate, auto_fire_score
    summary = _ORIGINAL_EMIT_TICKETS(
        use_cached=use_cached,
        validate=True,
        controller=controller,
        bankroll=bankroll,
        top_n=top_n,
        auto_fire_score=None,
        gateway_url=gateway_url,
        scan_max_age_sec=scan_max_age_sec,
        runtime_cfg=_safe_runtime_config(runtime_cfg),
    )
    if isinstance(summary, dict):
        summary["validate_mode"] = True
        summary["auto_fire_score"] = None
        summary["auto_fired"] = []
        summary["auto_fired_count"] = 0
        summary["order_promotion_stage"] = ORDER_PROMOTION_STAGE
    return summary


# The preserved daemon resolves emit_tickets in its own module globals.
_legacy.emit_tickets = emit_tickets


def _validated_only_argv(argv: list[str]) -> list[str]:
    """Remove legacy CLI options that can request live or automatic firing."""

    out: list[str] = []
    index = 0
    while index < len(argv):
        arg = argv[index]
        if arg == "--live":
            index += 1
            continue
        if arg == "--auto-fire-score":
            index += 2
            continue
        if arg.startswith("--auto-fire-score="):
            index += 1
            continue
        out.append(arg)
        index += 1
    return out


def main() -> int:
    original_argv = list(sys.argv)
    sys.argv = [original_argv[0], *_validated_only_argv(original_argv[1:])]
    try:
        print(
            "[AUTO-TKT] safety facade active: validate-only tickets; "
            "automatic approval/fire disabled",
            flush=True,
        )
        return int(_legacy.main())
    finally:
        sys.argv = original_argv


if __name__ == "__main__":
    raise SystemExit(main())
