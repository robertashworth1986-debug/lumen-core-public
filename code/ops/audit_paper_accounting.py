#!/usr/bin/env python3
"""Offline cash/equity reconciliation for a deliberately narrow paper ledger.

No broker connection, credentials, orders, advice or live-mode conversion.
Long-only, single-currency, fully funded synthetic spot fills. No margin,
shorts, derivatives, tax-lot accounting or inference of real broker balances.
"""
from __future__ import annotations
from datetime import datetime, timezone
from decimal import Decimal, localcontext
import re
from typing import Any


def require(ok: bool, message: str) -> None:
    if not ok:
        raise ValueError(message)


def amount(value: Any, positive: bool = False) -> Decimal:
    require(isinstance(value, str) and bool(re.fullmatch(r"(?:0|[1-9][0-9]{0,15})(?:\.[0-9]{1,12})?", value)), "Amount must be a bounded nonnegative decimal string")
    result = Decimal(value)
    require(not positive or result > 0, "Amount must be positive")
    return result


def utc(value: Any) -> datetime:
    require(isinstance(value, str), "UTC timestamp required")
    result = datetime.fromisoformat(value.replace("Z", "+00:00"))
    require(result.tzinfo is not None and result.utcoffset().total_seconds() == 0, "UTC timestamp required")
    return result.astimezone(timezone.utc)


def audit_paper_ledger(data: dict) -> dict:
    expected = {"schema", "mode", "currency", "initial_cash", "as_of_utc", "max_mark_age_seconds", "events", "marks", "reported_cash"}
    require(isinstance(data, dict) and set(data) == expected, "Unexpected ledger schema fields")
    require(data["schema"] == "lumencore.paper_accounting.v1" and data["mode"] == "paper", "Paper-only schema required")
    require(data["currency"] == "USD", "Single USD quote currency only")
    cutoff = utc(data["as_of_utc"])
    max_age = data["max_mark_age_seconds"]
    require(type(max_age) is int and 0 <= max_age <= 86400, "Invalid mark-age policy")
    events = data["events"]; marks = data["marks"]
    require(isinstance(events, list) and len(events) <= 100_000 and isinstance(marks, dict) and len(marks) <= 10000, "Invalid or oversized ledger")
    with localcontext() as context:
        # Input bounds, product bounds and maximum event count fit this precision.
        context.prec = 80
        initial = amount(data["initial_cash"]); cash = initial
        flows = Decimal(0); fees = Decimal(0); positions: dict[str, Decimal] = {}
        ids = set(); previous = None; trades = 0
        for event in events:
            require(isinstance(event, dict), "Event must be an object")
            base = {"id", "time_utc", "type"}
            kind = event.get("type")
            require(kind in {"deposit", "withdrawal", "buy", "sell", "fee"}, "Unsupported event type")
            wanted = base | ({"instrument", "quantity", "price", "fee"} if kind in {"buy", "sell"} else {"amount"})
            require(set(event) == wanted, "Unexpected event fields")
            identity = event["id"]
            require(isinstance(identity, str) and bool(re.fullmatch(r"[A-Za-z0-9_.:-]{1,100}", identity)) and identity not in ids, "Duplicate/invalid event ID")
            ids.add(identity); when = utc(event["time_utc"])
            require((previous is None or when >= previous) and when <= cutoff, "Unordered or future event")
            previous = when
            if kind in {"deposit", "withdrawal", "fee"}:
                value = amount(event["amount"], True)
                cash += value if kind == "deposit" else -value
                if kind == "deposit": flows += value
                elif kind == "withdrawal": flows -= value
                else: fees += value
            else:
                symbol = event["instrument"]
                require(isinstance(symbol, str) and bool(re.fullmatch(r"[A-Z0-9._-]{1,40}", symbol)), "Invalid instrument")
                quantity = amount(event["quantity"], True); price = amount(event["price"], True)
                fee = amount(event["fee"]); held = positions.get(symbol, Decimal(0))
                if kind == "buy":
                    cash -= quantity * price + fee; positions[symbol] = held + quantity
                else:
                    require(held >= quantity, "Short position not supported")
                    cash += quantity * price - fee; positions[symbol] = held - quantity
                fees += fee; trades += 1
            require(cash >= 0, "Unfunded paper ledger")
        require(cash == amount(data["reported_cash"]), "Cash reconciliation mismatch")
        open_positions = {symbol: quantity for symbol, quantity in positions.items() if quantity}
        require(set(marks) == set(open_positions), "Missing or extraneous marks")
        value = Decimal(0)
        for symbol, quantity in open_positions.items():
            mark = marks[symbol]
            require(isinstance(mark, dict) and set(mark) == {"price", "time_utc"}, "Invalid mark")
            when = utc(mark["time_utc"])
            age = (cutoff - when).total_seconds()
            require(0 <= age <= max_age, "Stale or future mark")
            value += quantity * amount(mark["price"], True)
        equity = cash + value
        return {"schema": "lumencore.paper_accounting_receipt.v1", "status": "RECONCILED_WITHIN_DECLARED_PAPER_MODEL",
                "currency": "USD", "cash": str(cash), "equity": str(equity),
                "net_external_flows": str(flows), "fees": str(fees),
                "net_paper_pnl": str(equity - initial - flows),
                "open_positions": {k: str(v) for k, v in open_positions.items()},
                "events": len(events), "paper_fills": trades,
                "live_authorized": False, "broker_reconciled": False,
                "boundary": "Algebraic consistency of supplied paper records only; source authenticity, execution realism, slippage and actual account performance are not established."}
