from __future__ import annotations

import hashlib
import json
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
REGISTRY = ROOT / "config" / "geometry_championship_v1_registry.json"
REPLAY = ROOT / "out" / "ops" / "top_geometry_live_replay_results_latest.json"
HARVEST = ROOT / "out" / "ops" / "live_evidence_max_harvest_latest.json"

OUT_JSON = ROOT / "out" / "ops" / "sector_validation_priority_board_latest.json"
DASHBOARD_JSON = ROOT / "dashboard" / "data" / "sector_validation_priority_board.json"
OUT_MD = ROOT / "docs" / f"SECTOR_VALIDATION_PRIORITY_BOARD_{date.today().isoformat()}.md"
MANIFEST = ROOT / "out" / "ops" / "sector_validation_priority_board_manifest_latest.json"

SCORE_WEIGHTS = {
    "official_data_access": 25,
    "loss_or_exposure_definition": 25,
    "current_luma_evidence": 20,
    "baseline_maturity": 15,
    "external_validator_access": 15,
}

SECTOR_SPECS: list[dict[str, Any]] = [
    {
        "sector_id": "electric_grid_reliability",
        "sector": "Electric-grid reliability, loss, and congestion",
        "score_components": {
            "official_data_access": 5,
            "loss_or_exposure_definition": 5,
            "current_luma_evidence": 4,
            "baseline_maturity": 4,
            "external_validator_access": 2,
        },
        "official_loss_surface": {
            "type": "physical_loss_and_reliability_exposure",
            "fact": "EIA estimates U.S. transmission and distribution losses averaged about 5% during 2018-2022; EIA separately reports an average of 11 interruption hours per customer in 2024.",
            "native_units": ["MWh lost", "SAIDI minutes", "SAIFI interruptions", "forecast error", "congestion dollars after operator data"],
            "sources": [
                {
                    "publisher": "U.S. Energy Information Administration",
                    "url": "https://www.eia.gov/tools/faqs/faq.php?id=105&t=3.",
                    "supports": "T&D loss-rate context",
                },
                {
                    "publisher": "U.S. Energy Information Administration",
                    "url": "https://www.eia.gov/todayinenergy/detail.php?id=66744",
                    "supports": "2024 interruption-duration context",
                },
            ],
            "not_a_claim": "The national loss and outage figures are sector context, not LumenCore-attributable savings.",
        },
        "current_data_route": ["EIA", "FRED", "NOAA_NCEI", "NWS_PUBLIC", "OPEN_METEO_PUBLIC"],
        "geometry_lanes": ["wave_resonance_timing", "time_series_model_routing", "resource_aware_scheduling", "mission_network_routing"],
        "protocol_baselines": ["persistence", "seasonal naive", "Kalman filter", "ARIMA", "operator forecast", "min-cost flow or SCOPF when topology is available"],
        "validation_wedge": {
            "experiment": "Freeze 30 consecutive daily or hourly windows from one utility, ISO/RTO, or laboratory feed and compare predeclared candidates with the full baseline set on native-unit loss.",
            "minimum_external_input": "Aligned load, generation, outage, and price or dispatch observations plus an operator-approved loss definition.",
            "pass_gate": "Positive holdout effect interval, global multiplicity correction, no material reliability regression, and an independent rerun by the data owner.",
            "external_receipt": "Signed validation memo, pilot data agreement, or operator rerun log.",
        },
    },
    {
        "sector_id": "maritime_port_flow",
        "sector": "Maritime port flow, routing, and resilience",
        "score_components": {
            "official_data_access": 5,
            "loss_or_exposure_definition": 5,
            "current_luma_evidence": 4,
            "baseline_maturity": 3,
            "external_validator_access": 2,
        },
        "official_loss_surface": {
            "type": "economic_throughput_exposure",
            "fact": "BTS reports that U.S. ports accounted for 41% of U.S. imports and exports in 2024, totaling more than $2.1 trillion.",
            "native_units": ["vessel waiting hours", "berth turnaround time", "route deviation", "throughput", "delay cost after terminal accounting"],
            "sources": [
                {
                    "publisher": "Bureau of Transportation Statistics",
                    "url": "https://rosap.ntl.bts.gov/view/dot/88517",
                    "supports": "2026 Port Performance Freight Statistics context",
                },
                {
                    "publisher": "NOAA and partner agencies",
                    "url": "https://marinecadastre.gov/accessais/",
                    "supports": "official AIS data access route",
                },
            ],
            "not_a_claim": "$2.1 trillion is trade throughput, not preventable loss and not LumenCore-attributable value.",
        },
        "current_data_route": ["AIS archive or partner stream", "NOAA_NCEI", "NWS_PUBLIC", "OPEN_METEO_PUBLIC"],
        "geometry_lanes": ["optimal_curve_transport", "branching_transport", "mission_network_routing", "wave_resonance_timing"],
        "protocol_baselines": ["great-circle route", "historical median ETA", "A*", "Dijkstra", "minimum spanning tree", "port-published berth sequence"],
        "validation_wedge": {
            "experiment": "Lock one port and one 60-day AIS/weather interval; predict ETA or flag congestion on untouched days and compare against route, persistence, and port-schedule baselines.",
            "minimum_external_input": "Port call timestamps, berth events, and one operator-defined delay or exception label.",
            "pass_gate": "Lower native-unit ETA or exception loss on untouched calls, corrected significance, and terminal or port-authority rerun.",
            "external_receipt": "Port/terminal validation letter, data-use agreement, or witnessed benchmark result.",
        },
    },
    {
        "sector_id": "aviation_delay_flow",
        "sector": "Aviation delay and surface/airspace flow",
        "score_components": {
            "official_data_access": 5,
            "loss_or_exposure_definition": 5,
            "current_luma_evidence": 2,
            "baseline_maturity": 4,
            "external_validator_access": 2,
        },
        "official_loss_surface": {
            "type": "historical_economic_loss",
            "fact": "FAA estimated the total cost of U.S. flight delays at $33.0 billion for 2019; BTS currently provides detailed on-time records through May 2026.",
            "native_units": ["arrival-delay minutes", "taxi-out minutes", "cancellation rate", "diversion rate", "cost after FAA-approved valuation"],
            "sources": [
                {
                    "publisher": "Federal Aviation Administration",
                    "url": "https://www.faa.gov/sites/faa.gov/files/air_traffic/by_the_numbers/Air_Traffic_by_the_Numbers_2022.pdf",
                    "supports": "2019 total-delay-cost estimate",
                },
                {
                    "publisher": "Bureau of Transportation Statistics",
                    "url": "https://www.transtats.bts.gov/ONTIME/",
                    "supports": "official on-time data route",
                },
            ],
            "not_a_claim": "The FAA estimate is a 2019 national total, not current addressable loss or LumenCore savings.",
        },
        "current_data_route": ["BTS On-Time", "FAA NAS status", "NWS_PUBLIC", "NOAA_NCEI", "OPEN_METEO_PUBLIC"],
        "geometry_lanes": ["wave_resonance_timing", "optimal_curve_transport", "resource_aware_scheduling", "multi_agent_coordination"],
        "protocol_baselines": ["historical airport-route median", "seasonal naive", "Kalman filter", "ARIMA", "scheduled block time", "FAA or airline operational baseline"],
        "validation_wedge": {
            "experiment": "Ingest one frozen BTS month, predeclare airport-route cohorts, and compare delay prediction or sequencing candidates on a later untouched month.",
            "minimum_external_input": "BTS on-time rows are enough for benchmark proof; an airport, airline, or FAA partner is required for operational validation.",
            "pass_gate": "Lower delay-minute loss across untouched airport-route cohorts, corrected significance, calibration, and no subgroup collapse.",
            "external_receipt": "Independent airport/airline/FAA technical review or witnessed replay.",
        },
    },
    {
        "sector_id": "data_center_energy_cooling",
        "sector": "Data-center energy and cooling",
        "score_components": {
            "official_data_access": 4,
            "loss_or_exposure_definition": 5,
            "current_luma_evidence": 3,
            "baseline_maturity": 4,
            "external_validator_access": 2,
        },
        "official_loss_surface": {
            "type": "electricity_demand_exposure",
            "fact": "DOE reports that data centers used about 4.4% of U.S. electricity in 2023 and projects 6.7%-12% by 2028.",
            "native_units": ["kWh", "PUE", "temperature excursion minutes", "pressure drop", "cooling energy", "demand-charge dollars after invoices"],
            "sources": [
                {
                    "publisher": "U.S. Department of Energy",
                    "url": "https://www.energy.gov/articles/doe-releases-new-report-evaluating-increase-electricity-demand-data-centers",
                    "supports": "2024 U.S. Data Center Energy Usage Report summary",
                }
            ],
            "not_a_claim": "Electricity share is demand exposure, not waste and not recoverable savings.",
        },
        "current_data_route": ["EIA", "NOAA_NCEI", "NWS_PUBLIC", "NREL when provider recovers", "facility telemetry partner"],
        "geometry_lanes": ["thermal_ventilation", "resource_aware_scheduling", "wave_resonance_timing", "time_series_model_routing"],
        "protocol_baselines": ["always-on", "fixed setpoint", "conventional HVAC network", "CFD reference", "persistence", "ASHRAE/operator rule set"],
        "validation_wedge": {
            "experiment": "Replay one facility's timestamped load, temperature, airflow, and cooling-control history with a locked counterfactual protocol before any live control.",
            "minimum_external_input": "Read-only BMS/DCIM telemetry, equipment limits, and operator-approved PUE or cooling-energy definition.",
            "pass_gate": "Lower energy proxy followed by lower metered kWh under safety constraints, corrected significance, and facility-engineer signoff.",
            "external_receipt": "Facility-engineer validation memo or sandbox pilot report.",
        },
    },
    {
        "sector_id": "water_distribution",
        "sector": "Water-distribution leak, pump, and resilience optimization",
        "score_components": {
            "official_data_access": 2,
            "loss_or_exposure_definition": 5,
            "current_luma_evidence": 3,
            "baseline_maturity": 5,
            "external_validator_access": 2,
        },
        "official_loss_surface": {
            "type": "physical_resource_loss",
            "fact": "EPA reports an estimated 2.1 trillion gallons of treated drinking water lost annually because of aging and leaky U.S. infrastructure.",
            "native_units": ["gallons lost", "leak-detection precision/recall", "pump kWh", "pressure violations", "repair-priority value after utility accounting"],
            "sources": [
                {
                    "publisher": "U.S. Environmental Protection Agency",
                    "url": "https://www.epa.gov/water-research/drought-resilience-and-water-conservation",
                    "supports": "national treated-water-loss context",
                },
                {
                    "publisher": "U.S. Environmental Protection Agency",
                    "url": "https://www.epa.gov/dwreginfo/drinking-water-distribution-system-tools-and-resources",
                    "supports": "distribution-system tools and resources",
                },
            ],
            "not_a_claim": "The national gallons figure is not a dollar value and is not LumenCore-attributable loss reduction.",
        },
        "current_data_route": ["USGS_WATER", "EPA benchmark data", "EPANET", "utility SCADA or AMI partner"],
        "geometry_lanes": ["branching_transport", "mission_network_routing", "time_series_model_routing", "field_guided_control"],
        "protocol_baselines": ["EPANET hydraulic reference", "minimum spanning tree", "pressure-threshold alarm", "persistence", "utility leak heuristic"],
        "validation_wedge": {
            "experiment": "Run a locked EPANET or recognized leak benchmark first, then replay one utility district-metered area with untouched leak/repair events.",
            "minimum_external_input": "Network model, pressure/flow history, repair events, and utility-approved water-loss definition.",
            "pass_gate": "Better leak or pump metric on untouched events with hydraulic constraints, corrected significance, and utility-engineer rerun.",
            "external_receipt": "Utility or water-research laboratory validation memo.",
        },
    },
]

TOP_FIVE_QUESTIONS = [
    "What is the strongest claim in my stack that would survive adversarial independent replication, and what exact evidence would falsify it?",
    "Which one sector gives the shortest path from official data to a paid, partner-validated native-unit loss reduction, and what is the 30-day experiment?",
    "Run a preregistered gauntlet on every executable geometry against every protocol baseline using frozen development data, untouched holdout data, uncertainty, and global multiple-comparison control. Which champion survives?",
    "What is missing between today's evidence and a named agency or operator signing a validation letter, pilot agreement, or purchase path, and who is the next specific human gate?",
    "Audit the whole estate for the single highest-value bottleneck across proof, IP, compliance, customer access, and funding; fix that bottleneck and produce the receipt before optimizing anything else.",
]


def now_utc() -> str:
    return datetime.now(timezone.utc).isoformat()


def load_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def relative(path: Path) -> str:
    return path.relative_to(ROOT).as_posix()


def input_receipt(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {"path": relative(path), "present": False}
    return {
        "path": relative(path),
        "present": True,
        "bytes": path.stat().st_size,
        "sha256": sha256_file(path),
    }


def weighted_score(components: dict[str, int]) -> float:
    return round(sum((components[key] / 5.0) * weight for key, weight in SCORE_WEIGHTS.items()), 2)


def replay_card_summary(card: dict[str, Any]) -> dict[str, Any]:
    paired = card.get("paired_inference", {})
    gauntlet = card.get("baseline_gauntlet", {})
    return {
        "lane": card.get("lane"),
        "candidate": card.get("candidate_family_id"),
        "named_baseline": card.get("named_baseline"),
        "mean_score_delta_vs_named_baseline": card.get("candidate_score_delta_vs_named_baseline"),
        "bootstrap_mean_delta_ci95": paired.get("bootstrap_mean_delta_ci95"),
        "paired_unit_count": paired.get("paired_unit_count"),
        "raw_two_sided_sign_test_p_value": paired.get("raw_two_sided_sign_test_p_value"),
        "holm_adjusted_p_value": paired.get("holm_adjusted_p_value"),
        "statistically_positive_after_named_card_holm": paired.get("statistically_positive_after_holm", False),
        "registered_baseline_mean_wins": gauntlet.get("mean_score_win_count"),
        "registered_baseline_count": gauntlet.get("registered_baseline_count"),
        "registered_baseline_global_holm_positive_count": gauntlet.get("global_holm_positive_count"),
        "beats_all_registered_baselines_after_global_holm": gauntlet.get("candidate_beats_all_registered_baselines_after_global_holm", False),
        "external_approval_claim": False,
    }


def geometry_execution_audit(registry: dict[str, Any], replay: dict[str, Any]) -> dict[str, Any]:
    families = registry.get("families", [])
    status_counts: dict[str, int] = {}
    lane_counts: dict[str, int] = {}
    for family in families:
        status = str(family.get("status", "unknown"))
        lane = str(family.get("lane", "unknown"))
        status_counts[status] = status_counts.get(status, 0) + 1
        lane_counts[lane] = lane_counts.get(lane, 0) + 1

    replay_lanes = {str(card.get("lane")) for card in replay.get("replay_cards", [])}
    return {
        "registered_family_count": len(families),
        "registered_lane_count": len(registry.get("lanes", {})),
        "registry_status_counts": dict(sorted(status_counts.items())),
        "registry_lane_counts": dict(sorted(lane_counts.items())),
        "current_executable_adapter_count": replay.get("summary", {}).get("adapter_replay_count", 0),
        "current_executable_replay_lanes": sorted(replay_lanes),
        "current_registered_baseline_comparison_count": replay.get("summary", {}).get("registered_baseline_comparison_count", 0),
        "all_140_executed_under_one_locked_protocol": False,
        "claim_boundary": "Registry membership and a benchmark hypothesis are not executable evidence. Each family needs a real implementation, a lane-specific input contract, compute-budget parity, frozen development data, untouched holdout data, and protocol baselines before it can enter a champion claim.",
        "promotion_sequence": [
            "Freeze lane, metric, baseline set, data split, compute budget, and failure criteria.",
            "Implement and unit-test each candidate behind one lane-specific adapter contract.",
            "Screen on development data only; do not promote from development rank.",
            "Evaluate surviving candidates once on untouched holdout windows.",
            "Apply paired uncertainty and one global multiplicity correction across the declared family.",
            "Require an external data owner or laboratory to rerun the surviving champion.",
        ],
    }


def build_payload() -> dict[str, Any]:
    registry = load_json(REGISTRY)
    replay = load_json(REPLAY)
    harvest = load_json(HARVEST)
    cards_by_lane = {
        str(card.get("lane")): replay_card_summary(card)
        for card in replay.get("replay_cards", [])
        if card.get("lane")
    }

    sectors: list[dict[str, Any]] = []
    for spec in SECTOR_SPECS:
        row = json.loads(json.dumps(spec))
        row["priority_score_100"] = weighted_score(row["score_components"])
        row["current_champion_receipts"] = [
            cards_by_lane[lane] for lane in row["geometry_lanes"] if lane in cards_by_lane
        ]
        row["promotion_state"] = "external_validation_required"
        row["realized_savings_claim_allowed"] = False
        sectors.append(row)

    sectors.sort(key=lambda row: (-row["priority_score_100"], row["sector_id"]))
    for rank, row in enumerate(sectors, start=1):
        row["rank"] = rank

    evidence_chain = {
        "inputs": {
            "geometry_registry": input_receipt(REGISTRY),
            "top_geometry_replay": input_receipt(REPLAY),
            "live_evidence_harvest": input_receipt(HARVEST),
        },
        "snapshot_chain_sha256": replay.get("summary", {}).get("snapshot_chain_sha256"),
    }
    evidence_chain["chain_sha256"] = hashlib.sha256(
        json.dumps(evidence_chain, sort_keys=True).encode("utf-8")
    ).hexdigest()

    harvest_summary = harvest.get("summary", {})
    replay_summary = replay.get("summary", {})
    return {
        "schema": "sector_validation_priority_board.v1",
        "generated_utc": now_utc(),
        "purpose": "Prioritize sectors by official data, measurable loss, current evidence, baseline maturity, and external-validation access without converting sector scale into an unsupported LumenCore value claim.",
        "scoring": {
            "weights": SCORE_WEIGHTS,
            "component_scale": "0-5; weighted to 100; prioritization judgment, not scientific evidence or valuation",
        },
        "summary": {
            "sector_count": len(sectors),
            "top_sector": sectors[0]["sector"],
            "registered_geometry_family_count": len(registry.get("families", [])),
            "current_executable_adapter_count": replay_summary.get("adapter_replay_count", 0),
            "registered_baseline_comparison_count": replay_summary.get("registered_baseline_comparison_count", 0),
            "named_card_holm_positive_count": replay_summary.get("holm_positive_card_count", 0),
            "measured_live_source_count": harvest_summary.get("measured_sources", 0),
            "fresh_measured_row_count": harvest_summary.get("total_measured_rows", 0),
            "live_context_replay_row_count": replay_summary.get("total_live_context_rows_evaluated", 0),
            "ready_for_real_dollar_claim": False,
            "ready_for_unbeatable_claim": False,
        },
        "sectors": sectors,
        "geometry_execution_audit": geometry_execution_audit(registry, replay),
        "top_five_questions": TOP_FIVE_QUESTIONS,
        "global_promotion_gate": [
            "candidate beats every predeclared protocol baseline on untouched holdout data",
            "paired effect interval is positive in the declared direction",
            "global multiple-comparison correction passes",
            "result repeats across independent frozen windows",
            "external partner or laboratory reproduces the run",
            "improvement is expressed in native operational units before any dollar conversion",
        ],
        "claim_boundary": "The board prioritizes validation work. It does not prove market size, addressable revenue, realized savings, field performance, safety, procurement eligibility, grant award, patent scope, or trading performance.",
        "evidence_chain": evidence_chain,
    }


def render_markdown(payload: dict[str, Any]) -> str:
    summary = payload["summary"]
    lines = [
        "# Sector Validation Priority Board",
        "",
        f"Generated: `{payload['generated_utc']}`",
        "",
        "## Decision",
        "",
        f"The shortest current path is **{summary['top_sector']}**. This is a prioritization decision, not a valuation or savings claim.",
        "",
        "## Proof Posture",
        "",
        f"- Registered families: `{summary['registered_geometry_family_count']}` across `{payload['geometry_execution_audit']['registered_lane_count']}` lanes.",
        f"- Executable live-context adapters: `{summary['current_executable_adapter_count']}`.",
        f"- Registered-baseline comparisons in the current replay: `{summary['registered_baseline_comparison_count']}`.",
        f"- Named cards positive after Holm correction: `{summary['named_card_holm_positive_count']}`.",
        f"- Fresh measured sources / rows: `{summary['measured_live_source_count']}` / `{summary['fresh_measured_row_count']}`.",
        f"- Live-context replay rows: `{summary['live_context_replay_row_count']}`.",
        "- Real-dollar and unbeatable claim gates: **closed**.",
        "",
        "## Ranked Sectors",
        "",
        "| Rank | Sector | Score / 100 | Current receipt | 30-day native-unit wedge |",
        "|---:|---|---:|---|---|",
    ]
    for row in payload["sectors"]:
        receipts = row["current_champion_receipts"]
        if receipts:
            receipt = ", ".join(
                f"`{item['candidate']}` vs `{item['named_baseline']}`: delta `{item['mean_score_delta_vs_named_baseline']}`; "
                f"named-card Holm-positive `{item['statistically_positive_after_named_card_holm']}`; "
                f"registered mean wins `{item['registered_baseline_mean_wins']}/{item['registered_baseline_count']}`; "
                f"global-Holm wins `{item['registered_baseline_global_holm_positive_count']}/{item['registered_baseline_count']}`"
                for item in receipts[:2]
            )
        else:
            receipt = "No current executable receipt"
        wedge = row["validation_wedge"]["experiment"].replace("|", "/")
        lines.append(f"| {row['rank']} | {row['sector']} | {row['priority_score_100']:.2f} | {receipt} | {wedge} |")

    lines.extend(["", "## Sector Boundaries", ""])
    for row in payload["sectors"]:
        lines.extend(
            [
                f"### {row['rank']}. {row['sector']}",
                "",
                f"- Official context: {row['official_loss_surface']['fact']}",
                f"- Boundary: {row['official_loss_surface']['not_a_claim']}",
                f"- Protocol baselines: {', '.join(row['protocol_baselines'])}.",
                f"- External receipt required: {row['validation_wedge']['external_receipt']}",
                "- Official sources:",
            ]
        )
        for source in row["official_loss_surface"]["sources"]:
            lines.append(f"  - [{source['publisher']}]({source['url']}): {source['supports']}.")

    audit = payload["geometry_execution_audit"]
    lines.extend(
        [
            "",
            "## 140-Family Audit",
            "",
            f"`{audit['registered_family_count']}` families are registered, but only `{audit['current_executable_adapter_count']}` current live-context adapters exist. The full 140-family locked-protocol gauntlet has **not** run.",
            "",
            audit["claim_boundary"],
            "",
            "Promotion sequence:",
            "",
        ]
    )
    for index, step in enumerate(audit["promotion_sequence"], start=1):
        lines.append(f"{index}. {step}")

    lines.extend(["", "## Five Questions", ""])
    for index, question in enumerate(payload["top_five_questions"], start=1):
        lines.append(f"{index}. {question}")

    lines.extend(
        [
            "",
            "## Audit Receipt",
            "",
            f"- Evidence-chain SHA-256: `{payload['evidence_chain']['chain_sha256']}`",
            f"- Snapshot-chain SHA-256: `{payload['evidence_chain']['snapshot_chain_sha256']}`",
            "",
            f"> Claim boundary: {payload['claim_boundary']}",
            "",
        ]
    )
    return "\n".join(lines)


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def main() -> int:
    payload = build_payload()
    write_json(OUT_JSON, payload)
    write_json(DASHBOARD_JSON, payload)
    OUT_MD.parent.mkdir(parents=True, exist_ok=True)
    OUT_MD.write_text(render_markdown(payload), encoding="utf-8")

    manifest_payload = {
        "schema": "sector_validation_priority_board_manifest.v1",
        "generated_utc": now_utc(),
        "artifacts": [
            {"path": relative(path), "bytes": path.stat().st_size, "sha256": sha256_file(path)}
            for path in (OUT_JSON, DASHBOARD_JSON, OUT_MD)
        ],
    }
    manifest_payload["manifest_chain_sha256"] = hashlib.sha256(
        json.dumps(manifest_payload["artifacts"], sort_keys=True).encode("utf-8")
    ).hexdigest()
    write_json(MANIFEST, manifest_payload)

    print(f"wrote={relative(OUT_JSON)}")
    print(f"wrote={relative(DASHBOARD_JSON)}")
    print(f"wrote={relative(OUT_MD)}")
    print(f"wrote={relative(MANIFEST)}")
    print(f"top_sector={payload['summary']['top_sector']}")
    print(f"evidence_chain_sha256={payload['evidence_chain']['chain_sha256']}")
    print(f"manifest_chain_sha256={manifest_payload['manifest_chain_sha256']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
