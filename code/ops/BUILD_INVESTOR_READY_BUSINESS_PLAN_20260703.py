from __future__ import annotations

import json
import math
from datetime import datetime, timedelta, timezone
from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.platypus import (
    ListFlowable,
    ListItem,
    PageBreak,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)


ROOT = Path(__file__).resolve().parents[2]
DASHBOARD_DATA = ROOT / "dashboard" / "data"
OUT_DIR = Path(r"C:\Users\Novac\iCloudDrive\Business plan")
DOCS = ROOT / "docs"

OUT_PDF = OUT_DIR / "LumenCore_Business_Plan_Investor_Ready_UPDATED_2026-07-03.pdf"
OUT_MD = DOCS / "LUMENCORE_BUSINESS_PLAN_INVESTOR_READY_UPDATED_2026-07-03.md"

INPUT_SCHEMAS = {
    "champion": ("champion_metric_gauntlet.json", "champion_metric_gauntlet_v2"),
    "locked": (
        "locked_source_baseline_replay_sweep.json",
        "locked_source_baseline_replay_sweep_v2",
    ),
    "dollar_ladder": (
        "field_validated_dollar_claim_ladder.json",
        "field_validated_dollar_claim_ladder_v2",
    ),
    "dollar_gate": ("dollar_claim_gate.json", "dollar_claim_gate_v2"),
    "valuation": (
        "valuation_proposal_target_packet.json",
        "valuation_proposal_target_packet_v3",
    ),
    "revenue": ("proof_to_revenue_engine.json", "proof_to_revenue_engine_v3"),
}


class ContractError(RuntimeError):
    """Raised when an input cannot support the current reviewer-safe contract."""


def read_json(path: Path) -> dict:
    if not path.is_file():
        raise FileNotFoundError(f"Required business-plan input is missing: {path}")
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ContractError(f"Cannot read required JSON input {path}: {exc}") from exc
    if not isinstance(payload, dict):
        raise ContractError(f"Required JSON input is not an object: {path}")
    return payload


def get_data(data_dir: Path = DASHBOARD_DATA) -> dict[str, dict]:
    return {
        key: read_json(data_dir / filename)
        for key, (filename, _schema) in INPUT_SCHEMAS.items()
    }


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise ContractError(message)


def _mapping(value: object, label: str) -> dict:
    _require(isinstance(value, dict), f"{label} must be an object")
    return value


def _number(value: object, label: str) -> float:
    _require(
        isinstance(value, (int, float)) and not isinstance(value, bool),
        f"{label} must be numeric",
    )
    result = float(value)
    _require(math.isfinite(result), f"{label} must be finite")
    return result


def _integer(value: object, label: str) -> int:
    result = _number(value, label)
    _require(result.is_integer(), f"{label} must be an integer")
    return int(result)


def _utc_timestamp(value: object, label: str) -> datetime:
    _require(isinstance(value, str) and value.strip(), f"{label} is missing")
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise ContractError(f"{label} is not an ISO-8601 timestamp") from exc
    _require(parsed.tzinfo is not None, f"{label} must include a timezone")
    return parsed.astimezone(timezone.utc)


def _price_range(value: object, label: str) -> tuple[int, int]:
    price = _mapping(value, label)
    low = _integer(price.get("low"), f"{label}.low")
    high = _integer(price.get("high"), f"{label}.high")
    _require(low >= 0 and high >= low, f"{label} is not a valid price range")
    return low, high


def validate_contract(
    data: dict[str, dict],
    *,
    now: datetime | None = None,
    max_input_age: timedelta = timedelta(days=14),
) -> dict:
    """Validate and normalize the only claims this dated builder may publish."""

    current_time = (now or datetime.now(timezone.utc)).astimezone(timezone.utc)
    for key, (_filename, expected_schema) in INPUT_SCHEMAS.items():
        artifact = _mapping(data.get(key), key)
        _require(
            artifact.get("schema") == expected_schema,
            f"{key} has stale or unsupported schema {artifact.get('schema')!r}; "
            f"expected {expected_schema!r}",
        )
        generated = _utc_timestamp(artifact.get("generated_utc"), f"{key}.generated_utc")
        age = current_time - generated
        _require(age >= timedelta(0), f"{key} is dated in the future")
        _require(
            age <= max_input_age,
            f"{key} is stale ({age.days} days old; maximum is {max_input_age.days})",
        )

    champion = _mapping(data["champion"].get("summary"), "champion.summary")
    locked = _mapping(data["locked"].get("summary"), "locked.summary")
    ladder = _mapping(
        data["dollar_ladder"].get("current_truth"),
        "dollar_ladder.current_truth",
    )
    gate = _mapping(data["dollar_gate"].get("summary"), "dollar_gate.summary")
    valuation_truth = _mapping(
        data["valuation"].get("current_truth"),
        "valuation.current_truth",
    )
    valuation_state = _mapping(
        data["valuation"].get("valuation_state"),
        "valuation.valuation_state",
    )
    revenue = _mapping(data["revenue"].get("summary"), "revenue.summary")
    offers = _mapping(data["revenue"].get("commercial_offers"), "revenue.commercial_offers")
    model_evidence = _mapping(
        data["revenue"].get("current_model_evidence"),
        "revenue.current_model_evidence",
    )

    false_gates = {
        "champion.internal_champion": champion.get("internal_champion"),
        "champion.protocol_grade_internal_champion": champion.get(
            "protocol_grade_internal_champion"
        ),
        "champion.real_dollar_savings_claim_allowed": champion.get(
            "real_dollar_savings_claim_allowed"
        ),
        "locked.performance_superiority_claim_allowed": locked.get(
            "performance_superiority_claim_allowed"
        ),
        "locked.real_dollar_savings_claim_allowed": locked.get(
            "real_dollar_savings_claim_allowed"
        ),
        "ladder.current_performance_champion_present": ladder.get(
            "current_performance_champion_present"
        ),
        "ladder.modeled_dollar_projection_allowed_now": ladder.get(
            "modeled_dollar_projection_allowed_now"
        ),
        "ladder.enterprise_valuation_asserted_now": ladder.get(
            "enterprise_valuation_asserted_now"
        ),
        "valuation.internal_performance_champion_present": valuation_truth.get(
            "internal_performance_champion_present"
        ),
        "valuation.enterprise_valuation_asserted": valuation_state.get(
            "enterprise_valuation_asserted"
        ),
        "revenue.internal_performance_champion_present": revenue.get(
            "internal_performance_champion_present"
        ),
        "revenue.cross_sector_efficiency_claim_allowed": revenue.get(
            "cross_sector_efficiency_claim_allowed"
        ),
        "revenue.model_performance_marketing_allowed": revenue.get(
            "model_performance_marketing_allowed"
        ),
        "revenue.modeled_dollar_projection_allowed": revenue.get(
            "modeled_dollar_projection_allowed"
        ),
        "revenue.enterprise_valuation_asserted": revenue.get(
            "enterprise_valuation_asserted"
        ),
    }
    for label, value in false_gates.items():
        _require(value is False, f"{label} must be explicitly false")

    holm_promotions = _integer(
        locked.get("global_holm_positive_count"),
        "locked.summary.global_holm_positive_count",
    )
    _require(holm_promotions == 0, "Direct all-baseline global Holm promotions must be zero")
    _require(
        _integer(
            ladder.get("direct_all_baseline_global_holm_positive_count"),
            "dollar_ladder.current_truth.direct_all_baseline_global_holm_positive_count",
        )
        == holm_promotions,
        "Dollar ladder disagrees with the locked sweep on global Holm promotions",
    )

    sector_count = _integer(revenue.get("cross_sector_sector_count"), "revenue sector count")
    sector_gains = _integer(
        revenue.get("cross_sector_gain_proven_count"),
        "revenue proven sector gain count",
    )
    _require(
        (sector_gains, sector_count) == (0, 6),
        "Cross-sector contract must remain 0 proven gains across 6 sectors",
    )
    _require(
        (
            _integer(ladder.get("cross_sector_gain_proven_count"), "ladder sector gains"),
            _integer(ladder.get("cross_sector_sector_count"), "ladder sector count"),
        )
        == (sector_gains, sector_count),
        "Dollar ladder and revenue engine disagree on cross-sector results",
    )

    wins = _integer(champion.get("holdout_wins"), "champion holdout wins")
    holdouts = _integer(champion.get("holdout_count"), "champion holdout count")
    mean_delta = _number(
        champion.get("mean_delta_vs_named_baseline"),
        "champion mean delta",
    )
    baseline = champion.get("named_baseline")
    _require((wins, holdouts) == (482, 1525), "Kuramoto reference must be 482/1525")
    _require(
        math.isclose(mean_delta, -0.508191, abs_tol=0.000001),
        "Kuramoto reference mean delta must remain -0.508191",
    )
    _require(
        champion.get("champion_family") == "kuramoto_phase_coupling",
        "Measured reference candidate must be Kuramoto phase coupling",
    )
    _require(
        revenue.get("measured_reference_candidate") == "kuramoto_phase_coupling"
        and revenue.get("reference_candidate_was_protocol_selected") is False
        and valuation_truth.get("reference_candidate_was_protocol_selected") is False,
        "Kuramoto must remain a measured reference and not the development-selected candidate",
    )
    _require(
        revenue.get("development_selected_candidate") == "lissajous_phase_paths",
        "Development-selected candidate identity is missing or stale",
    )
    _require(
        revenue.get("internal_replay_named_baseline") == baseline
        and _integer(revenue.get("internal_replay_holdout_wins"), "revenue wins") == wins
        and _integer(revenue.get("internal_replay_holdout_count"), "revenue holdouts")
        == holdouts
        and math.isclose(
            _number(revenue.get("internal_replay_mean_delta"), "revenue mean delta"),
            mean_delta,
            abs_tol=0.000001,
        ),
        "Revenue engine disagrees with the measured Kuramoto reference",
    )

    zero_values = {
        "champion.safe_estimated_hourly_value_usd": champion.get(
            "safe_estimated_hourly_value_usd"
        ),
        "champion.safe_estimated_annual_value_usd": champion.get(
            "safe_estimated_annual_value_usd"
        ),
        "ladder.allowed_estimated_hourly_value_usd": ladder.get(
            "allowed_estimated_hourly_value_usd"
        ),
        "ladder.allowed_estimated_annual_value_usd": ladder.get(
            "allowed_estimated_annual_value_usd"
        ),
        "gate.allowed_estimated_hourly_value_usd": gate.get(
            "allowed_estimated_hourly_value_usd"
        ),
        "gate.allowed_estimated_annual_value_usd": gate.get(
            "allowed_estimated_annual_value_usd"
        ),
        "valuation.safe_estimated_hourly_value_usd": valuation_truth.get(
            "safe_estimated_hourly_value_usd"
        ),
        "valuation.safe_estimated_annual_value_usd": valuation_truth.get(
            "safe_estimated_annual_value_usd"
        ),
        "revenue.safe_estimated_hourly_value_usd": revenue.get(
            "safe_estimated_hourly_value_usd"
        ),
        "revenue.safe_estimated_annual_value_usd": revenue.get(
            "safe_estimated_annual_value_usd"
        ),
    }
    for label, value in zero_values.items():
        _require(_number(value, label) == 0.0, f"{label} must be zero")

    protocol_offer = _mapping(offers.get("source_native_protocol_review"), "protocol offer")
    implementation_offer = _mapping(
        offers.get("benchmark_implementation"),
        "benchmark implementation offer",
    )
    protocol_low, protocol_high = _price_range(
        protocol_offer.get("price_usd"),
        "protocol offer price",
    )
    implementation_low, implementation_high = _price_range(
        implementation_offer.get("price_usd"),
        "implementation offer price",
    )
    _require(
        (protocol_low, protocol_high) == (2500, 7500),
        "Protocol-review service range must be $2,500-$7,500",
    )
    _require(
        (implementation_low, implementation_high) == (7500, 25000),
        "Benchmark-implementation range must be $7,500-$25,000",
    )

    prooflock = _mapping(
        offers.get("product_process_discovery"),
        "ProofLock product-process offer",
    )
    _require(
        prooflock.get("name") == "ProofLock Opportunity Operations"
        and prooflock.get("product_process_scoping_allowed") is True
        and prooflock.get("model_performance_dependency") is False,
        "ProofLock must remain separately scopeable without geometry performance dependency",
    )
    prooflock_boundary = prooflock.get("claim_boundary")
    _require(
        isinstance(prooflock_boundary, str)
        and "does not inherit" in prooflock_boundary.lower(),
        "ProofLock must explicitly reject inherited geometry performance claims",
    )
    _require(
        model_evidence.get("candidate_family") == "kuramoto_phase_coupling"
        and model_evidence.get("candidate_was_protocol_selected") is False,
        "Revenue model evidence must identify Kuramoto as a non-selected reference",
    )

    return {
        "generated_utc": current_time.isoformat(),
        "performance_champion": None,
        "global_holm_promotions": holm_promotions,
        "sector_gains": sector_gains,
        "sector_count": sector_count,
        "reference": {
            "family": "kuramoto_phase_coupling",
            "label": "Kuramoto phase coupling",
            "wins": wins,
            "holdouts": holdouts,
            "mean_delta": mean_delta,
            "baseline": str(baseline),
            "development_selected": False,
        },
        "development_selected_candidate": "lissajous_phase_paths",
        "locked": {
            "routes": _integer(locked.get("adapter_backed_routes"), "locked route count"),
            "comparisons": _integer(
                locked.get("baseline_comparison_count"),
                "locked comparison count",
            ),
            "direct_routes": _integer(
                locked.get("direct_measured_routes_replayed"),
                "locked direct route count",
            ),
            "conditioned_routes": _integer(
                locked.get("source_conditioned_routes_replayed"),
                "locked conditioned route count",
            ),
            "numeric_rows": _integer(
                locked.get("numeric_samples_read"),
                "locked numeric sample count",
            ),
        },
        "claimable_modeled_dollar_outcome_usd": 0,
        "enterprise_valuation_asserted": False,
        "offers": {
            "protocol_review": (protocol_low, protocol_high),
            "benchmark_implementation": (implementation_low, implementation_high),
            "prooflock_name": str(prooflock["name"]),
            "prooflock_boundary": str(prooflock_boundary),
        },
    }


def _styles() -> dict[str, ParagraphStyle]:
    base = getSampleStyleSheet()
    return {
        "title": ParagraphStyle(
            "Title",
            parent=base["Title"],
            fontName="Helvetica-Bold",
            fontSize=28,
            leading=32,
            alignment=TA_CENTER,
            textColor=colors.HexColor("#122A46"),
            spaceAfter=8,
        ),
        "subtitle": ParagraphStyle(
            "Subtitle",
            parent=base["Normal"],
            fontSize=12,
            leading=16,
            alignment=TA_CENTER,
            textColor=colors.HexColor("#44546A"),
            spaceAfter=12,
        ),
        "h1": ParagraphStyle(
            "Heading1",
            parent=base["Heading1"],
            fontName="Helvetica-Bold",
            fontSize=15,
            leading=19,
            textColor=colors.HexColor("#122A46"),
            spaceBefore=8,
            spaceAfter=6,
        ),
        "h2": ParagraphStyle(
            "Heading2",
            parent=base["Heading2"],
            fontName="Helvetica-Bold",
            fontSize=11.5,
            leading=15,
            textColor=colors.HexColor("#1E6FD9"),
            spaceBefore=7,
            spaceAfter=4,
        ),
        "body": ParagraphStyle(
            "Body",
            parent=base["BodyText"],
            fontName="Helvetica",
            fontSize=9.5,
            leading=13.5,
            textColor=colors.HexColor("#24364B"),
            spaceAfter=6,
        ),
        "small": ParagraphStyle(
            "Small",
            parent=base["BodyText"],
            fontSize=7.5,
            leading=10,
            textColor=colors.HexColor("#667085"),
        ),
    }


def _p(text: str, style: ParagraphStyle) -> Paragraph:
    return Paragraph(text, style)


def _table(rows: list[tuple[str, str]], st: dict[str, ParagraphStyle]) -> Table:
    body = [[_p(f"<b>{label}</b>", st["body"]), _p(value, st["body"])] for label, value in rows]
    table = Table(body, colWidths=[2.05 * inch, 4.35 * inch], hAlign="LEFT")
    table.setStyle(
        TableStyle(
            [
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("GRID", (0, 0), (-1, -1), 0.35, colors.HexColor("#D7DEE8")),
                ("BACKGROUND", (0, 0), (0, -1), colors.HexColor("#F2F6FA")),
                ("LEFTPADDING", (0, 0), (-1, -1), 6),
                ("RIGHTPADDING", (0, 0), (-1, -1), 6),
                ("TOPPADDING", (0, 0), (-1, -1), 5),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
            ]
        )
    )
    return table


def _bullets(items: list[str], st: dict[str, ParagraphStyle]) -> ListFlowable:
    return ListFlowable(
        [ListItem(_p(item, st["body"])) for item in items],
        bulletType="bullet",
        leftIndent=18,
        bulletFontSize=7,
    )


def build_story(contract: dict) -> list:
    st = _styles()
    ref = contract["reference"]
    locked = contract["locked"]
    protocol_low, protocol_high = contract["offers"]["protocol_review"]
    implementation_low, implementation_high = contract["offers"][
        "benchmark_implementation"
    ]

    story: list = [
        Spacer(1, 0.65 * inch),
        _p("LumenCore", st["title"]),
        _p("Business Plan and Investor Diligence Brief", st["subtitle"]),
        _p("Fail-closed evidence edition", st["subtitle"]),
        Spacer(1, 0.15 * inch),
        _table(
            [
                ("Company", "LumenCore"),
                ("Current evidence stage", "Measured nonpromotion plus conditioned-synthetic research leads"),
                ("Performance champion", "None"),
                ("Claimable modeled outcome", "$0"),
                ("Enterprise valuation", "Not asserted"),
                ("Commercial posture", "Price bounded technical work, not algorithmic performance"),
            ],
            st,
        ),
        Spacer(1, 0.2 * inch),
        _p(
            "<b>Evidence boundary:</b> No current geometry family is a performance champion. "
            "LumenCore does not currently claim sector efficiency, field performance, realized "
            "savings, buyer ROI, trading edge, or enterprise value from the research results.",
            st["body"],
        ),
        PageBreak(),
        _p("Executive Summary", st["h1"]),
        _p(
            "LumenCore is building a governed evidence workflow for source-native benchmarking. "
            "The platform maps each source and task to appropriate incumbent baselines, freezes "
            "chronology and inputs, records positive and negative results, and keeps commercial "
            "language inside the evidence that actually cleared its gates.",
            st["body"],
        ),
        _p(
            "The current research result is a nonpromotion. That is useful diligence evidence, "
            "not a performance product claim. The immediate commercial path is paid technical "
            "review and reproducible benchmark implementation. ProofLock Opportunity Operations "
            "is a separate product-process discovery lane and inherits no geometry performance claim.",
            st["body"],
        ),
        _p("Canonical Evidence State", st["h1"]),
        _table(
            [
                ("Performance champion", "None"),
                (
                    "Global promotion gate",
                    f"{contract['global_holm_promotions']} direct all-baseline globally Holm-positive promotions",
                ),
                (
                    "Cross-sector result",
                    f"{contract['sector_gains']}/{contract['sector_count']} proven sector gains",
                ),
                (
                    "Measured reference",
                    f"{ref['label']}: {ref['wins']}/{ref['holdouts']} paired measured holdouts "
                    f"against {ref['baseline']}; mean delta {ref['mean_delta']:.6f}",
                ),
                ("Selection status", "Kuramoto is a measured reference, not the development-selected candidate"),
                (
                    "Development selection",
                    f"{contract['development_selected_candidate']} is tracked separately and is not a champion",
                ),
                ("Claimable modeled dollar outcome", "$0"),
                ("Enterprise valuation", "Not asserted"),
            ],
            st,
        ),
        _p("Benchmark Coverage", st["h2"]),
        _table(
            [
                ("Compatibility-qualified routes", f"{locked['routes']:,}"),
                ("Named-baseline comparisons", f"{locked['comparisons']:,}"),
                ("Direct measured routes", f"{locked['direct_routes']:,}"),
                ("Conditioned-synthetic routes", f"{locked['conditioned_routes']:,}"),
                ("Performance rows inspected", f"{locked['numeric_rows']:,}"),
                (
                    "Interpretation",
                    "Coverage and custody support reviewability; they do not establish superiority or value",
                ),
            ],
            st,
        ),
        PageBreak(),
        _p("Commercial Model", st["h1"]),
        _p(
            "LumenCore can price the work required to make a source-native comparison reviewable. "
            "These service ranges are not modeled savings, enterprise value, or proof that a geometry "
            "method improves an operating system.",
            st["body"],
        ),
        _table(
            [
                (
                    "Source-native protocol review",
                    f"${protocol_low:,}-${protocol_high:,}: source-task mapping, baseline registration, "
                    "chronology review, evidence audit, and claim-boundary review",
                ),
                (
                    "Benchmark implementation",
                    f"${implementation_low:,}-${implementation_high:,}: custom implementation after "
                    "data rights, native metrics, baselines, and acceptance criteria are locked",
                ),
                (
                    contract["offers"]["prooflock_name"],
                    "Separately scopeable product-process discovery; pricing follows buyer workflow "
                    "discovery and it inherits no geometry performance, savings, or award claim",
                ),
            ],
            st,
        ),
        _p("ProofLock Opportunity Operations", st["h2"]),
        _p(
            "ProofLock can be evaluated as a human-controlled opportunity workflow for finding, "
            "qualifying, assembling, preflighting, and receipting funding opportunities. Final "
            "certifications and submissions remain human-controlled. Its product value must be "
            "measured against the buyer's current workflow and does not depend on a geometry result.",
            st["body"],
        ),
        _p("Current Valuation Boundary", st["h1"]),
        _p(
            "No enterprise valuation is asserted in this plan. Any financing valuation requires "
            "independent diligence, external validation, customer evidence, revenue evidence, and "
            "negotiation. Repository volume, hashes, benchmark breadth, and service price ranges are "
            "not substitutes for enterprise valuation.",
            st["body"],
        ),
        _p("Near-Term Evidence Milestones", st["h1"]),
        _bullets(
            [
                "Obtain an external owner's source, incumbent baseline, native metric, holdout, and acceptance criteria before any prospective evaluation.",
                "Preserve negative and null results alongside positive research leads.",
                "Run future promotion tests only under frozen, source-specific, all-baseline protocols with multiplicity control.",
                "Measure ProofLock against a buyer's existing opportunity workflow without importing geometry claims.",
                "Treat hashes as custody evidence and software tests as implementation evidence, not performance evidence.",
            ],
            st,
        ),
        _p("Reviewer Questions Answered", st["h1"]),
        _table(
            [
                ("What is proven now?", "A governed benchmark and evidence workflow can be inspected and scoped"),
                ("What is not proven?", "Performance superiority, sector gains, modeled value, realized savings, and enterprise value"),
                ("What happened to Kuramoto?", "It remains a negative measured reference and was not development-selected"),
                ("What can be sold now?", "Bounded protocol-review and benchmark-implementation work"),
                ("What is separate?", "ProofLock Opportunity Operations product-process discovery"),
            ],
            st,
        ),
        Spacer(1, 0.12 * inch),
        _p(
            f"Contract validated {contract['generated_utc']}. Inputs older than 14 days or inconsistent "
            "with the canonical claim gates stop this build.",
            st["small"],
        ),
    ]
    return story


def render_markdown(contract: dict) -> str:
    ref = contract["reference"]
    locked = contract["locked"]
    protocol_low, protocol_high = contract["offers"]["protocol_review"]
    implementation_low, implementation_high = contract["offers"][
        "benchmark_implementation"
    ]
    lines = [
        "# LumenCore Business Plan and Investor Diligence Brief",
        "",
        "## Current Contract",
        "",
        "- Performance champion: **none**",
        f"- Direct all-baseline global Holm promotions: **{contract['global_holm_promotions']}**",
        f"- Proven cross-sector gains: **{contract['sector_gains']}/{contract['sector_count']}**",
        f"- Kuramoto measured reference: **{ref['wins']}/{ref['holdouts']}** paired holdouts against `{ref['baseline']}`",
        f"- Kuramoto mean delta: **{ref['mean_delta']:.6f}**",
        "- Kuramoto selection status: measured negative reference, not development-selected",
        f"- Development-selected candidate tracked separately: `{contract['development_selected_candidate']}`; not a champion",
        "- Claimable modeled dollar outcome: **$0**",
        "- Enterprise valuation: **not asserted**",
        "",
        "LumenCore does not currently claim performance superiority, sector efficiency, field performance, realized savings, buyer ROI, trading edge, or enterprise value from the geometry research lane.",
        "",
        "## Business Position",
        "",
        "LumenCore is a governed evidence workflow for source-native benchmarking. It maps each source and task to appropriate incumbent baselines, freezes chronology and inputs, records positive and negative results, and keeps commercial language inside cleared evidence gates.",
        "",
        "## Benchmark Coverage",
        "",
        f"- Compatibility-qualified routes: `{locked['routes']}`",
        f"- Named-baseline comparisons: `{locked['comparisons']}`",
        f"- Direct measured routes: `{locked['direct_routes']}`",
        f"- Conditioned-synthetic routes: `{locked['conditioned_routes']}`",
        f"- Performance rows inspected: `{locked['numeric_rows']}`",
        "",
        "Coverage, hashes, and custody improve reviewability. They do not establish superiority, savings, or enterprise value.",
        "",
        "## Allowed Commercial Offers",
        "",
        f"- Source-native protocol review: **${protocol_low:,}-${protocol_high:,}**",
        f"- Optional benchmark implementation: **${implementation_low:,}-${implementation_high:,}** after data rights, native metrics, baselines, and acceptance criteria are locked",
        f"- **{contract['offers']['prooflock_name']}**: separately scopeable product-process discovery; pricing follows workflow discovery",
        "",
        "Service prices describe work. They are not modeled outcomes, ROI, realized savings, or enterprise valuation.",
        "",
        "## ProofLock Boundary",
        "",
        contract["offers"]["prooflock_boundary"],
        "",
        "ProofLock must be evaluated against the buyer's existing opportunity workflow. It inherits no geometry performance, savings, award, or field-validation claim.",
        "",
        "## Current Valuation Boundary",
        "",
        "No enterprise valuation is asserted. Any financing valuation requires independent diligence, external validation, customer evidence, revenue evidence, and negotiation.",
        "",
        "## Next Evidence Gates",
        "",
        "1. Lock an external owner's source, incumbent baseline, native metric, holdout, and acceptance criteria.",
        "2. Preserve negative and null results alongside research leads.",
        "3. Require frozen source-specific all-baseline testing with multiplicity control before promotion.",
        "4. Measure ProofLock independently against a buyer's current workflow.",
        "",
        f"Contract validated: `{contract['generated_utc']}`",
        "",
    ]
    return "\n".join(lines)


def write_markdown(contract: dict, output_path: Path = OUT_MD) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(render_markdown(contract), encoding="utf-8")


def build_pdf(
    *,
    data_dir: Path = DASHBOARD_DATA,
    output_pdf: Path = OUT_PDF,
    output_md: Path = OUT_MD,
    now: datetime | None = None,
) -> tuple[Path, Path]:
    data = get_data(data_dir)
    contract = validate_contract(data, now=now)

    output_pdf.parent.mkdir(parents=True, exist_ok=True)
    write_markdown(contract, output_md)
    doc = SimpleDocTemplate(
        str(output_pdf),
        pagesize=letter,
        rightMargin=0.72 * inch,
        leftMargin=0.72 * inch,
        topMargin=0.62 * inch,
        bottomMargin=0.6 * inch,
        title="LumenCore Business Plan and Investor Diligence Brief",
        author="Robert Ashworth",
    )

    def page(canvas, doc_obj):
        canvas.saveState()
        canvas.setFont("Helvetica", 7.5)
        canvas.setFillColor(colors.HexColor("#667085"))
        canvas.drawString(
            0.72 * inch,
            0.36 * inch,
            "LumenCore investor diligence brief - fail-closed evidence edition",
        )
        canvas.drawRightString(7.78 * inch, 0.36 * inch, f"Page {doc_obj.page}")
        canvas.restoreState()

    doc.build(build_story(contract), onFirstPage=page, onLaterPages=page)
    return output_pdf, output_md


if __name__ == "__main__":
    pdf_path, markdown_path = build_pdf()
    print(pdf_path)
    print(markdown_path)
