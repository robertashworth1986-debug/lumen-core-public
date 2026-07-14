from __future__ import annotations

import hashlib
import json
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
OUT_JSON = ROOT / "out" / "ops" / "ieee_acopf_baseline_smoke_latest.json"
DASHBOARD_JSON = ROOT / "dashboard" / "data" / "ieee_acopf_baseline_smoke.json"
OUT_MD = ROOT / "docs" / "IEEE_ACOPF_BASELINE_SMOKE_2026-07-13.md"

BOUNDARY = (
    "This is a local baseline-execution receipt on public IEEE-style fixtures. It does not show that "
    "LumenCore beats an optimum, improves a utility operation, creates savings, or is field validated."
)


def now_utc() -> str:
    return datetime.now(timezone.utc).isoformat()


def stable_sha256(payload: Any) -> str:
    return hashlib.sha256(json.dumps(payload, sort_keys=True, default=str).encode("utf-8")).hexdigest()


def build_payload() -> dict[str, Any]:
    import numpy
    import pandapower
    import pandapower as pp
    import pandapower.networks as pn
    import scipy

    cases = (
        ("case14", pn.case14),
        ("case30", pn.case30),
        ("case39", pn.case39),
        ("case118", pn.case118),
    )
    results: list[dict[str, Any]] = []
    for name, factory in cases:
        net = factory()
        started = time.perf_counter()
        try:
            pp.runopp(net, verbose=False)
            results.append(
                {
                    "network": name,
                    "bus_count": len(net.bus),
                    "line_count": len(net.line),
                    "converged": bool(net.OPF_converged),
                    "reported_objective": round(float(net.res_cost), 6),
                    "wall_seconds": round(time.perf_counter() - started, 6),
                }
            )
        except Exception as exc:  # pragma: no cover - retained in the receipt
            results.append(
                {
                    "network": name,
                    "bus_count": len(net.bus),
                    "line_count": len(net.line),
                    "converged": False,
                    "error_type": type(exc).__name__,
                    "error": str(exc)[:300],
                    "wall_seconds": round(time.perf_counter() - started, 6),
                }
            )

    payload: dict[str, Any] = {
        "schema": "ieee_acopf_baseline_smoke_v1",
        "generated_utc": now_utc(),
        "purpose": "Verify that the unchanged nonlinear AC-OPF reference engine executes locally before candidate routing.",
        "equation": "min sum_g C_g(P_g), subject to AC power balance and declared voltage, generator, and branch limits",
        "environment": {
            "pandapower": pandapower.__version__,
            "numpy": numpy.__version__,
            "scipy": scipy.__version__,
            "solver": "pandapower.runopp / PYPOWER AC OPF",
        },
        "summary": {
            "network_count": len(results),
            "converged_count": sum(1 for row in results if row["converged"]),
            "all_converged": all(row["converged"] for row in results),
            "candidate_execution_started": False,
            "baseline_execution_verified": all(row["converged"] for row in results),
            "field_validation_claim_allowed": False,
            "realized_savings_claim_allowed": False,
            "beats_optimum_claim_allowed": False,
        },
        "results": results,
        "claim_boundary": BOUNDARY,
        "protocol": "config/ieee_acopf_routing_protocol_v1.json",
    }
    payload["receipt_sha256"] = stable_sha256(payload)
    return payload


def render_markdown(payload: dict[str, Any]) -> str:
    lines = [
        "# IEEE AC-OPF Baseline Smoke Receipt",
        "",
        f"Generated UTC: `{payload['generated_utc']}`",
        "",
        payload["purpose"],
        "",
        "## Result",
        "",
        f"- Networks converged: `{payload['summary']['converged_count']}/{payload['summary']['network_count']}`",
        f"- Candidate execution started: `{str(payload['summary']['candidate_execution_started']).lower()}`",
        f"- Receipt SHA-256: `{payload['receipt_sha256']}`",
        "",
        "| Network | Buses | Lines | Converged | Reported objective | Wall seconds |",
        "|---|---:|---:|---|---:|---:|",
    ]
    for row in payload["results"]:
        lines.append(
            f"| {row['network']} | {row['bus_count']} | {row['line_count']} | "
            f"{str(row['converged']).lower()} | {row.get('reported_objective', '')} | {row['wall_seconds']} |"
        )
    lines.extend(
        [
            "",
            "## Claim Boundary",
            "",
            payload["claim_boundary"],
            "",
            "The reported objectives are fixture-specific and are not compared across networks.",
        ]
    )
    return "\n".join(lines) + "\n"


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def main() -> None:
    payload = build_payload()
    write_json(OUT_JSON, payload)
    write_json(DASHBOARD_JSON, payload)
    OUT_MD.parent.mkdir(parents=True, exist_ok=True)
    OUT_MD.write_text(render_markdown(payload), encoding="utf-8")
    print(json.dumps({"output": str(OUT_JSON), "summary": payload["summary"]}, indent=2))


if __name__ == "__main__":
    main()
