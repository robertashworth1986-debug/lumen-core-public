"""Build the current public-safe LumenCore research technical note.

The note replaces speculative legacy concept papers with a source-bound account
of the implemented benchmark ledger and frozen prospective protocol. It has no
publishing, upload, outreach, or submission capability.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
LEDGER_PATH = ROOT / "out" / "ops" / "source_native_family_baseline_ledger_latest.json"
PROTOCOL_PATH = ROOT / "config" / "time_series_source_native_prospective_protocol_v1.json"
PROTOCOL_STATUS_PATH = (
    ROOT / "out" / "ops" / "time_series_source_native_prospective_protocol_status.json"
)
ARC_SEAL_LOGO = ROOT / "assets" / "brand" / "lumaarc_eclipse_corona_concept_v1.png"

OUTPUT_MD = ROOT / "docs" / "LUMENCORE_SOURCE_NATIVE_BENCHMARK_WHITEPAPER_CURRENT.md"
OUTPUT_PDF = ROOT / "output" / "pdf" / "LumenCore_Source_Native_Benchmark_Whitepaper_CURRENT.pdf"
OUTPUT_MANIFEST = (
    ROOT / "out" / "ops" / "source_native_research_whitepaper_manifest_latest.json"
)

UPLOAD_DIR = ROOT / "out" / "ops" / "linkedin_master_pack" / "upload_ready" / "whitepaper"
UPLOAD_PDF = (
    UPLOAD_DIR
    / "LumenCore_Source_Native_Benchmark_Whitepaper_CURRENT_PUBLIC_SAFE_REVIEW_REQUIRED.pdf"
)
UPLOAD_README = UPLOAD_DIR / "CURRENT_WHITEPAPER_GOVERNANCE.md"
ARCHIVE_DIR = (
    ROOT
    / "out"
    / "ops"
    / "linkedin_master_pack"
    / "archive"
    / "unvalidated_theoretical_whitepapers"
)

ARCHIVED_WHITEPAPERS = (
    {
        "filename": "LumenLogic_Fresh_WhitePaper.docx",
        "status": "HISTORICAL_SPECULATIVE_DO_NOT_UPLOAD",
        "reason": (
            "Contains unvalidated sacred-geometry, bioresonance, bio-signature, "
            "30-50 percent cooling, and trillion-dollar market claims plus private "
            "contact details."
        ),
    },
    {
        "filename": "LumenCore_Wormhole_Field_Research_WhitePaper 2.pdf",
        "status": "HISTORICAL_SPECULATIVE_DO_NOT_UPLOAD",
        "reason": (
            "Contains unvalidated scalar-field, consciousness-field, zero-point, "
            "weather-control, planetary-defense, and wormhole-adjacent claims."
        ),
    },
    {
        "filename": "LumanCore_DataCenter_WhitePaper.pdf",
        "status": "HISTORICAL_SPECULATIVE_DO_NOT_UPLOAD",
        "reason": (
            "Contains unvalidated BioGeometry, thermal-load, EMI, hardware-reliability, "
            "human-cognition, and sustainability-benefit claims."
        ),
    },
)

BOUNDARY = (
    "This technical note reports local software, custody, benchmark, and protocol "
    "states. It is not peer review, independent validation, a performance claim, "
    "field validation, trading alpha, realized savings, enterprise value, a patent "
    "opinion, or deployment authority."
)


class WhitepaperError(ValueError):
    """Raised when a research-note invariant is not satisfied."""


def now_utc() -> datetime:
    return datetime.now(timezone.utc)


def read_json(path: Path) -> dict[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise WhitepaperError(f"Unreadable JSON: {path}") from exc
    if not isinstance(payload, dict):
        raise WhitepaperError(f"Expected a JSON object: {path}")
    return payload


def stable_hash(payload: Any) -> str:
    encoded = json.dumps(
        payload,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def file_receipt(path: Path) -> dict[str, Any]:
    try:
        relative = path.relative_to(ROOT).as_posix()
    except ValueError:
        relative = str(path)
    if not path.is_file():
        return {
            "path": relative,
            "exists": False,
            "bytes": 0,
            "sha256": None,
        }
    content = path.read_bytes()
    return {
        "path": relative,
        "exists": True,
        "bytes": len(content),
        "sha256": hashlib.sha256(content).hexdigest(),
    }


def verify_ledger_hash(ledger: dict[str, Any]) -> bool:
    expected = ledger.get("ledger_sha256")
    material = {
        "summary": ledger.get("summary"),
        "positive_subset_research_leads": ledger.get(
            "positive_subset_research_leads"
        ),
        "candidate_source_cards": ledger.get("candidate_source_cards"),
        "family_ledger": ledger.get("family_ledger"),
        "source_baseline_route_ledger": ledger.get(
            "source_baseline_route_ledger"
        ),
        "source_coverage_matrix": ledger.get("source_coverage_matrix"),
        "adapter_expansion_queue": ledger.get("adapter_expansion_queue"),
    }
    encoded = json.dumps(material, sort_keys=True, default=str).encode("utf-8")
    return expected == hashlib.sha256(encoded).hexdigest()


def build_payload(at: datetime | None = None) -> dict[str, Any]:
    at = at or now_utc()
    ledger = read_json(LEDGER_PATH)
    protocol = read_json(PROTOCOL_PATH)
    protocol_status = read_json(PROTOCOL_STATUS_PATH)
    summary = ledger.get("summary")
    if not isinstance(summary, dict):
        raise WhitepaperError("Ledger summary is missing")
    if not verify_ledger_hash(ledger):
        raise WhitepaperError("Source-native ledger hash verification failed")
    if protocol_status.get("verification_passed") is not True:
        raise WhitepaperError("Prospective protocol verification is not passing")
    if protocol.get("protocol_payload_sha256") != protocol_status.get(
        "protocol_payload_sha256"
    ):
        raise WhitepaperError("Prospective protocol hashes do not agree")

    candidate = protocol.get("candidate")
    endpoint = protocol.get("primary_endpoint")
    hypothesis = protocol.get("primary_hypothesis_family")
    sample_gates = protocol.get("sample_gates")
    if not all(
        isinstance(value, dict)
        for value in (candidate, endpoint, hypothesis, sample_gates)
    ):
        raise WhitepaperError("Prospective protocol sections are incomplete")

    archived = []
    for item in ARCHIVED_WHITEPAPERS:
        path = ARCHIVE_DIR / item["filename"]
        receipt = file_receipt(path)
        archived.append({**item, **receipt, "external_release_authorized": False})

    payload: dict[str, Any] = {
        "schema": "lumencore.source_native_research_whitepaper.v1",
        "generated_utc": at.astimezone(timezone.utc).isoformat(),
        "title": (
            "Source-Native Benchmarking for Nature-Inspired Time-Series Families: "
            "A Fail-Closed Experimental Protocol"
        ),
        "status": "CURRENT_PUBLIC_SAFE_HUMAN_REVIEW_REQUIRED",
        "peer_reviewed": False,
        "independently_validated": False,
        "external_release_authorized": False,
        "boundary": BOUNDARY,
        "abstract": (
            "LumenCore registers candidate computational families inspired by natural "
            "forms, but does not treat inspiration as evidence. This note reports a "
            "source-native benchmark ledger, the retrospective disposition of prior "
            "leads, and a frozen prospective protocol. The current ledger contains "
            f"{summary.get('registered_family_count')} registered families, "
            f"{summary.get('implementation_present_count')} implementations, and "
            f"{summary.get('executed_direct_source_baseline_comparison_count')} "
            "direct candidate-source-baseline comparisons. No candidate passes the "
            "promotion gate. The scientific contribution is therefore a reproducible "
            "comparison and falsification framework, not a performance champion."
        ),
        "current_snapshot": {
            "registered_family_count": summary.get("registered_family_count"),
            "implementation_present_count": summary.get(
                "implementation_present_count"
            ),
            "implementation_required_count": summary.get(
                "implementation_required_count"
            ),
            "family_in_direct_source_lane_count": summary.get(
                "family_in_direct_source_lane_count"
            ),
            "implemented_family_in_direct_source_lane_count": summary.get(
                "implemented_family_in_direct_source_lane_count"
            ),
            "direct_candidate_source_card_count": summary.get(
                "direct_candidate_source_card_count"
            ),
            "executed_comparison_count": summary.get(
                "executed_direct_source_baseline_comparison_count"
            ),
            "global_holm_positive_count": summary.get(
                "individual_comparison_global_holm_positive_count"
            ),
            "promotion_gate_pass_count": summary.get(
                "internal_source_native_promotion_gate_pass_count"
            ),
            "executable_direct_adapter_lane_count": summary.get(
                "lane_with_executable_direct_adapter_count"
            ),
            "market_signal_candidate_count": summary.get(
                "market_signal_candidate_count"
            ),
            "market_signal_source_count": summary.get(
                "market_signal_source_count"
            ),
            "market_signal_comparison_count": summary.get(
                "market_signal_comparison_count"
            ),
            "market_signal_inference_insufficient_count": summary.get(
                "market_signal_inference_insufficient_count"
            ),
            "market_signal_global_holm_positive_count": summary.get(
                "market_signal_global_holm_positive_count"
            ),
            "performance_claim_allowed": False,
        },
        "method": {
            "comparison_unit": (
                "Candidate-by-source cards evaluated against the baseline roster "
                "registered for that source, cadence, series, and horizon."
            ),
            "forecast_horizons": [1, 3, 5],
            "leakage_control": (
                "Expanding history ends immediately before each forecast origin."
            ),
            "independence_control": (
                "Inference clusters overlapping origins and horizons at the source-series "
                "level instead of treating every row as independent."
            ),
            "multiple_testing_control": (
                "Global Holm correction across the candidate-source-baseline comparison "
                "family; prior subset leads receive no preference."
            ),
            "source_native_baselines": protocol.get("registered_baselines"),
            "retained_outcomes": [
                "positive",
                "neutral",
                "negative",
                "inconclusive",
                "invalid",
            ],
        },
        "retrospective_result": {
            "direct_answer": ledger.get("direct_answer"),
            "retired_findings": ledger.get("retired_retrospective_findings"),
            "conclusion": (
                "The former FRED and TWELVE_DATA subset leads are retired because "
                "they do not survive source-series clustering and the complete "
                "source-native baseline gauntlet. Four fixed market-signal families "
                "were also run against four registered baselines on each of Kraken, "
                "TwelveData, and AlphaVantage. All 48 market comparisons are "
                "inferentially insufficient because each source currently supplies "
                "one source-series cluster. Across the ledger, zero comparisons "
                "survive the global correction and zero candidate-source cards pass "
                "promotion."
            ),
        },
        "prospective_protocol": {
            "protocol_id": protocol.get("protocol_id"),
            "protocol_status": protocol_status.get("protocol_status"),
            "promotion_decision": protocol_status.get("promotion_decision"),
            "eligible_future_observation_count": protocol_status.get(
                "eligible_future_observation_count"
            ),
            "candidate_registered_family_id": candidate.get(
                "registered_family_id"
            ),
            "candidate_scientific_estimator_id": candidate.get(
                "scientific_estimator_id"
            ),
            "candidate_description": candidate.get("description"),
            "primary_sources": protocol.get("primary_sources"),
            "contrast_count": hypothesis.get("contrast_count"),
            "correction": hypothesis.get("correction"),
            "familywise_alpha": hypothesis.get("familywise_alpha"),
            "primary_metric": endpoint.get("metric"),
            "primary_metric_formula": endpoint.get("formula"),
            "effect_floor": endpoint.get("effect_floor"),
            "uncertainty_method": endpoint.get("uncertainty_method"),
            "bootstrap_replications": endpoint.get("bootstrap_replications"),
            "sample_gates": sample_gates,
            "decision_rule": protocol.get("decision_rule"),
            "protocol_payload_sha256": protocol.get("protocol_payload_sha256"),
        },
        "scientific_contribution": [
            "A source-native baseline contract that prevents cross-source or cadence-mismatched promotion.",
            "A custody gate that binds exact source snapshots before benchmark acceptance.",
            "A clustered inference rule that avoids pseudoreplication from overlapping forecast origins and horizons.",
            "A full-family multiple-testing rule that prevents cherry-picking isolated wins.",
            "A future-only protocol with fixed endpoints, effect floor, sample gates, ablations, and falsification states.",
            "A cost-aware market-signal replay that uses identical timestamps, future-return rows, turnover costs, and source-specific baselines without granting a promotion from descriptive wins.",
            "A machine-readable claim boundary that keeps software proof separate from field, economic, or deployment claims.",
        ],
        "limitations": [
            (
                f"{summary.get('implementation_required_count')} of "
                f"{summary.get('registered_family_count')} registered families lack "
                "implementations."
            ),
            (
                f"Only {summary.get('lane_with_executable_direct_adapter_count')} "
                "lanes currently have executable direct measured adapters; "
                "the wider nature-inspired registry remains inventory, synthetic stress, "
                "or context until implemented."
            ),
            (
                f"All {summary.get('market_signal_inference_insufficient_count')} "
                "market-signal comparisons are inferentially insufficient under the "
                "predeclared five-cluster minimum; descriptive score differences are "
                "not alpha or edge."
            ),
            (
                "The prospective protocol has zero eligible future observations and "
                "cannot yet support a prospective accuracy conclusion."
            ),
            (
                "No result establishes universal superiority, field performance, "
                "trading alpha, realized savings, customer acceptance, or deployment "
                "authority."
            ),
        ],
        "canonical_source_receipts": [
            file_receipt(LEDGER_PATH),
            file_receipt(PROTOCOL_PATH),
            file_receipt(PROTOCOL_STATUS_PATH),
            file_receipt(ARC_SEAL_LOGO),
        ],
        "archived_legacy_whitepapers": archived,
    }
    required_counts = (
        "registered_family_count",
        "implementation_present_count",
        "implementation_required_count",
        "direct_candidate_source_card_count",
        "executed_comparison_count",
        "global_holm_positive_count",
        "promotion_gate_pass_count",
        "market_signal_candidate_count",
        "market_signal_source_count",
        "market_signal_comparison_count",
        "market_signal_inference_insufficient_count",
        "market_signal_global_holm_positive_count",
    )
    if any(
        not isinstance(payload["current_snapshot"].get(key), int)
        for key in required_counts
    ):
        raise WhitepaperError("Whitepaper snapshot contains non-integer counts")
    if not all(
        receipt["exists"] for receipt in payload["canonical_source_receipts"]
    ):
        raise WhitepaperError("A canonical whitepaper source is missing")
    if not all(item["exists"] for item in archived):
        raise WhitepaperError("A legacy whitepaper archive receipt is missing")
    payload["whitepaper_payload_sha256"] = stable_hash(payload)
    return payload


def render_markdown(payload: dict[str, Any]) -> str:
    snapshot = payload["current_snapshot"]
    prospective = payload["prospective_protocol"]
    method = payload["method"]
    lines = [
        f"# {payload['title']}",
        "",
        f"- Generated UTC: `{payload['generated_utc']}`",
        f"- Status: `{payload['status']}`",
        "- Peer reviewed: `false`",
        "- Independently validated: `false`",
        "- External release authorized: `false`",
        "",
        f"> {payload['boundary']}",
        "",
        "## Abstract",
        "",
        payload["abstract"],
        "",
        "## Research Question",
        "",
        (
            "Can a predeclared candidate family beat every accepted baseline for a "
            "specific source, series, cadence, and forecast horizon under prospective "
            "custody, clustered inference, an effect floor, and familywise error control?"
        ),
        "",
        "## Current Evidence Snapshot",
        "",
        f"- Registered families: `{snapshot['registered_family_count']}`",
        f"- Implementations present: `{snapshot['implementation_present_count']}`",
        f"- Missing implementations: `{snapshot['implementation_required_count']}`",
        f"- Candidate-source cards: `{snapshot['direct_candidate_source_card_count']}`",
        f"- Direct comparisons: `{snapshot['executed_comparison_count']}`",
        f"- Global Holm-positive comparisons: `{snapshot['global_holm_positive_count']}`",
        f"- Promoted champions: `{snapshot['promotion_gate_pass_count']}`",
        f"- Market-signal candidates: `{snapshot['market_signal_candidate_count']}`",
        f"- Market-signal sources: `{snapshot['market_signal_source_count']}`",
        f"- Market-signal comparisons: `{snapshot['market_signal_comparison_count']}`",
        f"- Market-signal inferentially insufficient: `{snapshot['market_signal_inference_insufficient_count']}`",
        "",
        "## Source-Native Method",
        "",
        f"- Comparison unit: {method['comparison_unit']}",
        f"- Horizons: `{method['forecast_horizons']}`",
        f"- Leakage control: {method['leakage_control']}",
        f"- Independence control: {method['independence_control']}",
        f"- Multiple-testing control: {method['multiple_testing_control']}",
        "- Baselines:",
    ]
    lines.extend(f"  - `{baseline}`" for baseline in method["source_native_baselines"])
    lines.extend(
        [
            "",
            "## Retrospective Result",
            "",
            payload["retrospective_result"]["conclusion"],
            "",
            "## Frozen Prospective Protocol",
            "",
            f"- Protocol: `{prospective['protocol_id']}`",
            f"- Status: `{prospective['protocol_status']}`",
            f"- Decision: `{prospective['promotion_decision']}`",
            f"- Eligible future observations: `{prospective['eligible_future_observation_count']}`",
            f"- Candidate label: `{prospective['candidate_registered_family_id']}`",
            f"- Scientific estimator: `{prospective['candidate_scientific_estimator_id']}`",
            f"- Metric: `{prospective['primary_metric']}`",
            f"- Formula: `{prospective['primary_metric_formula']}`",
            f"- Contrasts: `{prospective['contrast_count']}`",
            f"- Correction: `{prospective['correction']}`",
            f"- Protocol SHA-256: `{prospective['protocol_payload_sha256']}`",
            "",
            "## Scientific Contribution",
            "",
        ]
    )
    lines.extend(f"- {item}" for item in payload["scientific_contribution"])
    lines.extend(["", "## Limitations", ""])
    lines.extend(f"- {item}" for item in payload["limitations"])
    lines.extend(
        [
            "",
            "## Legacy Concept-Paper Disposition",
            "",
            (
                "The prior BioGeometry, scalar-field, bioresonance, cooling-savings, "
                "zero-point, weather-control, and wormhole-adjacent concept papers are "
                "preserved as historical speculative material and are blocked from "
                "upload or external scientific use."
            ),
            "",
            "## Receipt",
            "",
            f"- Whitepaper payload SHA-256: `{payload['whitepaper_payload_sha256']}`",
        ]
    )
    return "\n".join(lines)


def build_pdf(payload: dict[str, Any], output_path: Path) -> None:
    try:
        from reportlab.lib import colors
        from reportlab.lib.enums import TA_CENTER, TA_LEFT
        from reportlab.lib.pagesizes import letter
        from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
        from reportlab.lib.units import inch
        from reportlab.platypus import (
            Image,
            PageBreak,
            Paragraph,
            SimpleDocTemplate,
            Spacer,
            Table,
            TableStyle,
        )
    except ImportError as exc:
        raise WhitepaperError("reportlab is required to build the PDF") from exc

    output_path.parent.mkdir(parents=True, exist_ok=True)
    navy = colors.HexColor("#102A43")
    teal = colors.HexColor("#007C83")
    pale = colors.HexColor("#EAF4F5")
    line = colors.HexColor("#B8C7D1")
    muted = colors.HexColor("#516575")
    green = colors.HexColor("#1F7A4D")

    styles = getSampleStyleSheet()
    styles.add(
        ParagraphStyle(
            name="TitleLC",
            parent=styles["Title"],
            fontName="Helvetica-Bold",
            fontSize=22,
            leading=27,
            alignment=TA_CENTER,
            textColor=navy,
            spaceAfter=10,
        )
    )
    styles.add(
        ParagraphStyle(
            name="SubtitleLC",
            parent=styles["BodyText"],
            fontName="Helvetica",
            fontSize=11,
            leading=15,
            alignment=TA_CENTER,
            textColor=teal,
            spaceAfter=11,
        )
    )
    styles.add(
        ParagraphStyle(
            name="H1LC",
            parent=styles["Heading1"],
            fontName="Helvetica-Bold",
            fontSize=15,
            leading=18,
            textColor=navy,
            spaceBefore=8,
            spaceAfter=5,
        )
    )
    styles.add(
        ParagraphStyle(
            name="H2LC",
            parent=styles["Heading2"],
            fontName="Helvetica-Bold",
            fontSize=11,
            leading=14,
            textColor=teal,
            spaceBefore=6,
            spaceAfter=3,
        )
    )
    styles.add(
        ParagraphStyle(
            name="BodyLC",
            parent=styles["BodyText"],
            fontName="Helvetica",
            fontSize=9.4,
            leading=13.2,
            textColor=navy,
            spaceAfter=5,
        )
    )
    styles.add(
        ParagraphStyle(
            name="SmallLC",
            parent=styles["BodyText"],
            fontName="Helvetica",
            fontSize=7.8,
            leading=10.2,
            textColor=muted,
        )
    )
    styles.add(
        ParagraphStyle(
            name="TableHeaderLC",
            parent=styles["BodyText"],
            fontName="Helvetica-Bold",
            fontSize=8.1,
            leading=10.5,
            textColor=colors.white,
        )
    )
    styles.add(
        ParagraphStyle(
            name="BulletLC",
            parent=styles["BodyText"],
            fontName="Helvetica",
            fontSize=9,
            leading=12.3,
            leftIndent=14,
            firstLineIndent=-8,
            textColor=navy,
            spaceAfter=3,
        )
    )
    styles.add(
        ParagraphStyle(
            name="CalloutLC",
            parent=styles["BodyText"],
            fontName="Helvetica-Bold",
            fontSize=10,
            leading=14,
            textColor=green,
            alignment=TA_LEFT,
        )
    )

    prepared = payload["generated_utc"][:10]

    def footer(canvas, document):
        canvas.saveState()
        canvas.setStrokeColor(line)
        canvas.setLineWidth(0.5)
        canvas.line(0.65 * inch, 0.52 * inch, 7.85 * inch, 0.52 * inch)
        canvas.setFont("Helvetica", 7.1)
        canvas.setFillColor(muted)
        canvas.drawString(
            0.65 * inch,
            0.33 * inch,
            "Public-safe technical note | Not peer review or a performance claim",
        )
        canvas.drawRightString(
            7.85 * inch,
            0.33 * inch,
            f"Prepared {prepared} | Page {document.page}",
        )
        canvas.restoreState()

    document = SimpleDocTemplate(
        str(output_path),
        pagesize=letter,
        rightMargin=0.65 * inch,
        leftMargin=0.65 * inch,
        topMargin=0.55 * inch,
        bottomMargin=0.7 * inch,
        title=payload["title"],
        author="LumenCore",
        subject="Source-native benchmark and prospective validation protocol",
    )

    snapshot = payload["current_snapshot"]
    prospective = payload["prospective_protocol"]
    method = payload["method"]
    logo = Image(str(ARC_SEAL_LOGO), width=0.78 * inch, height=0.78 * inch)
    story = [
        Table(
            [[logo]],
            colWidths=[0.82 * inch],
            style=TableStyle(
                [
                    ("ALIGN", (0, 0), (-1, -1), "CENTER"),
                    ("LEFTPADDING", (0, 0), (-1, -1), 0),
                    ("RIGHTPADDING", (0, 0), (-1, -1), 0),
                    ("TOPPADDING", (0, 0), (-1, -1), 0),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
                ]
            ),
        ),
        Paragraph(payload["title"], styles["TitleLC"]),
        Paragraph(
            "LumenCore Technical Note - Current Public-Safe Review Draft",
            styles["SubtitleLC"],
        ),
        Table(
            [[Paragraph(payload["boundary"], styles["BodyLC"])]],
            colWidths=[6.9 * inch],
            style=TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, -1), pale),
                    ("BOX", (0, 0), (-1, -1), 0.8, teal),
                    ("LEFTPADDING", (0, 0), (-1, -1), 10),
                    ("RIGHTPADDING", (0, 0), (-1, -1), 10),
                    ("TOPPADDING", (0, 0), (-1, -1), 8),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 7),
                ]
            ),
        ),
        Paragraph("Abstract", styles["H1LC"]),
        Paragraph(payload["abstract"], styles["BodyLC"]),
        Paragraph("Research Question", styles["H1LC"]),
        Paragraph(
            (
                "Can a predeclared candidate family beat every accepted baseline for "
                "a specific source, series, cadence, and horizon under prospective "
                "custody, clustered inference, an effect floor, and familywise error "
                "control?"
            ),
            styles["CalloutLC"],
        ),
        Paragraph("Current Evidence Snapshot", styles["H1LC"]),
    ]

    snapshot_rows = [
        ("Registered families", snapshot["registered_family_count"]),
        ("Implementations present", snapshot["implementation_present_count"]),
        ("Missing implementations", snapshot["implementation_required_count"]),
        ("Direct candidate-source cards", snapshot["direct_candidate_source_card_count"]),
        ("Direct comparisons", snapshot["executed_comparison_count"]),
        ("Global Holm-positive comparisons", snapshot["global_holm_positive_count"]),
        ("Promoted champions", snapshot["promotion_gate_pass_count"]),
        ("Market-signal comparisons", snapshot["market_signal_comparison_count"]),
        (
            "Market comparisons inferentially insufficient",
            snapshot["market_signal_inference_insufficient_count"],
        ),
        (
            "Prospective eligible observations",
            prospective["eligible_future_observation_count"],
        ),
    ]
    snapshot_table = Table(
        [
            [
                Paragraph("State", styles["TableHeaderLC"]),
                Paragraph("Count", styles["TableHeaderLC"]),
            ],
            *[
                [
                    Paragraph(label, styles["BodyLC"]),
                    Paragraph(f"<b>{value}</b>", styles["BodyLC"]),
                ]
                for label, value in snapshot_rows
            ],
        ],
        colWidths=[5.65 * inch, 1.25 * inch],
        repeatRows=1,
    )
    snapshot_table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), navy),
                ("GRID", (0, 0), (-1, -1), 0.45, line),
                ("ALIGN", (1, 1), (1, -1), "CENTER"),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("LEFTPADDING", (0, 0), (-1, -1), 7),
                ("RIGHTPADDING", (0, 0), (-1, -1), 7),
                ("TOPPADDING", (0, 0), (-1, -1), 4),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
            ]
        )
    )
    story.extend(
        [
            snapshot_table,
            Spacer(1, 0.06 * inch),
            PageBreak(),
            Paragraph("1. Source-Native Experimental Design", styles["TitleLC"]),
            Paragraph("Why source-native baselines matter", styles["H1LC"]),
            Paragraph(
                (
                    "A candidate can appear strong when it is compared against an "
                    "inappropriate cadence, horizon, seasonal period, or baseline. "
                    "This protocol therefore treats the source contract as part of the "
                    "hypothesis. A family must win within each named source against the "
                    "complete accepted baseline roster before any broader promotion."
                ),
                styles["BodyLC"],
            ),
            Paragraph("Evaluation controls", styles["H1LC"]),
        ]
    )
    for item in (
        method["comparison_unit"],
        method["leakage_control"],
        method["independence_control"],
        method["multiple_testing_control"],
        "Positive, neutral, negative, inconclusive, and invalid outcomes are retained.",
    ):
        story.append(Paragraph(f"- {item}", styles["BulletLC"]))

    story.append(Paragraph("Registered baseline roster", styles["H1LC"]))
    baseline_cells = [
        Paragraph(f"- {baseline}", styles["BodyLC"])
        for baseline in method["source_native_baselines"]
    ]
    baseline_table = Table(
        [
            [baseline_cells[0], baseline_cells[1]],
            [baseline_cells[2], baseline_cells[3]],
            [baseline_cells[4], baseline_cells[5]],
            [baseline_cells[6], baseline_cells[7]],
        ],
        colWidths=[3.45 * inch, 3.45 * inch],
    )
    baseline_table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, -1), pale),
                ("GRID", (0, 0), (-1, -1), 0.4, line),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("LEFTPADDING", (0, 0), (-1, -1), 8),
                ("RIGHTPADDING", (0, 0), (-1, -1), 8),
                ("TOPPADDING", (0, 0), (-1, -1), 5),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
            ]
        )
    )
    story.extend(
        [
            baseline_table,
            Paragraph("Retrospective result", styles["H1LC"]),
            Paragraph(
                payload["retrospective_result"]["conclusion"],
                styles["BodyLC"],
            ),
            Table(
                [[Paragraph(
                    "Current conclusion: no alpha, edge, or champion is established.",
                    styles["CalloutLC"],
                )]],
                colWidths=[6.9 * inch],
                style=TableStyle(
                    [
                        ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#F4F8F5")),
                        ("BOX", (0, 0), (-1, -1), 0.8, green),
                        ("LEFTPADDING", (0, 0), (-1, -1), 10),
                        ("RIGHTPADDING", (0, 0), (-1, -1), 10),
                        ("TOPPADDING", (0, 0), (-1, -1), 7),
                        ("BOTTOMPADDING", (0, 0), (-1, -1), 7),
                    ]
                ),
            ),
            PageBreak(),
            Paragraph("2. Frozen Prospective Protocol", styles["TitleLC"]),
            Paragraph("Candidate identity", styles["H1LC"]),
            Paragraph(
                (
                    f"The registry label is <b>{prospective['candidate_registered_family_id']}</b>. "
                    f"The scientific estimator is <b>{prospective['candidate_scientific_estimator_id']}</b>: "
                    f"{prospective['candidate_description']} The estimator name prevents "
                    "the registry label from being mistaken for a validated fractional "
                    "Brownian motion model."
                ),
                styles["BodyLC"],
            ),
            Paragraph("Primary endpoint and multiplicity", styles["H1LC"]),
            Paragraph(
                (
                    f"The endpoint is {prospective['primary_metric']} "
                    f"({prospective['primary_metric_formula']}). The candidate must "
                    f"clear {prospective['contrast_count']} predeclared contrasts under "
                    f"{prospective['correction']} at familywise alpha "
                    f"{prospective['familywise_alpha']}. The maximum accepted rMAE is "
                    f"{prospective['effect_floor']['maximum_rMAE']}, corresponding to "
                    f"at least {prospective['effect_floor']['minimum_relative_improvement'] * 100:.0f} "
                    "percent relative improvement."
                ),
                styles["BodyLC"],
            ),
            Paragraph("Future-only sample gates", styles["H1LC"]),
        ]
    )
    daily = prospective["sample_gates"]["daily_arm"]
    monthly = prospective["sample_gates"]["monthly_arm"]
    for item in (
        (
            f"Daily arm: at least {daily['minimum_future_eligible_sessions_per_series']} "
            "future eligible sessions per series and "
            f"{daily['minimum_nonoverlapping_five_session_blocks']} nonoverlapping "
            "five-session blocks."
        ),
        (
            f"Monthly arm: at least {monthly['minimum_future_releases_per_series']} "
            "future releases per series."
        ),
        (
            f"Uncertainty: {prospective['uncertainty_method']} with "
            f"{prospective['bootstrap_replications']} frozen replications."
        ),
        "Sample gates cannot be reduced after freeze.",
    ):
        story.append(Paragraph(f"- {item}", styles["BulletLC"]))

    protocol_id_tokens = prospective["protocol_id"].split("_")
    protocol_id_display = prospective["protocol_id"]
    if len(protocol_id_tokens) > 2:
        protocol_id_display = (
            "_".join(protocol_id_tokens[:2])
            + "_<br/>"
            + "_".join(protocol_id_tokens[2:])
        )

    story.extend(
        [
            Paragraph("Current protocol state", styles["H1LC"]),
            Table(
                [
                    [
                        Paragraph("Protocol", styles["TableHeaderLC"]),
                        Paragraph("State", styles["TableHeaderLC"]),
                    ],
                    [
                        Paragraph(protocol_id_display, styles["BodyLC"]),
                        Paragraph(prospective["protocol_status"], styles["BodyLC"]),
                    ],
                    [
                        Paragraph("Promotion decision", styles["BodyLC"]),
                        Paragraph(prospective["promotion_decision"], styles["BodyLC"]),
                    ],
                    [
                        Paragraph("Eligible future observations", styles["BodyLC"]),
                        Paragraph(
                            str(prospective["eligible_future_observation_count"]),
                            styles["BodyLC"],
                        ),
                    ],
                ],
                colWidths=[2.2 * inch, 4.7 * inch],
                style=TableStyle(
                    [
                        ("BACKGROUND", (0, 0), (-1, 0), teal),
                        ("GRID", (0, 0), (-1, -1), 0.45, line),
                        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                        ("LEFTPADDING", (0, 0), (-1, -1), 7),
                        ("RIGHTPADDING", (0, 0), (-1, -1), 7),
                        ("TOPPADDING", (0, 0), (-1, -1), 5),
                        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
                    ]
                ),
            ),
            Paragraph("Decision states", styles["H1LC"]),
        ]
    )
    decision_rule = prospective["decision_rule"]
    for key in (
        "replicated_lead",
        "source_winner",
        "cross_source_promotion",
        "integrity_failure",
        "insufficient_sample",
        "primary_failure",
    ):
        story.append(
            Paragraph(f"- <b>{key}</b>: {decision_rule[key]}", styles["BulletLC"])
        )

    story.extend(
        [
            PageBreak(),
            Paragraph("3. Contribution, Limits, and Reproducibility", styles["TitleLC"]),
            Paragraph("Scientific contribution", styles["H1LC"]),
        ]
    )
    for item in payload["scientific_contribution"]:
        story.append(Paragraph(f"- {item}", styles["BulletLC"]))
    story.append(Paragraph("Limitations", styles["H1LC"]))
    for item in payload["limitations"]:
        story.append(Paragraph(f"- {item}", styles["BulletLC"]))
    story.extend(
        [
            Paragraph("Reproducibility receipts", styles["H1LC"]),
            Paragraph(
                (
                    "The ledger, prospective configuration, and prospective status "
                    "are bound below. Hashes establish byte identity and custody only; "
                    "they do not establish scientific correctness or external acceptance."
                ),
                styles["BodyLC"],
            ),
        ]
    )
    receipt_rows = []
    for receipt in payload["canonical_source_receipts"][:3]:
        receipt_rows.append(
            [
                Paragraph(receipt["path"], styles["SmallLC"]),
                Paragraph(str(receipt["bytes"]), styles["SmallLC"]),
                Paragraph(receipt["sha256"], styles["SmallLC"]),
            ]
        )
    receipt_table = Table(
        [
            [
                Paragraph("Artifact", styles["TableHeaderLC"]),
                Paragraph("Bytes", styles["TableHeaderLC"]),
                Paragraph("SHA-256", styles["TableHeaderLC"]),
            ],
            *receipt_rows,
        ],
        colWidths=[2.7 * inch, 0.65 * inch, 3.55 * inch],
        repeatRows=1,
    )
    receipt_table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), navy),
                ("GRID", (0, 0), (-1, -1), 0.4, line),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("LEFTPADDING", (0, 0), (-1, -1), 5),
                ("RIGHTPADDING", (0, 0), (-1, -1), 5),
                ("TOPPADDING", (0, 0), (-1, -1), 4),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
            ]
        )
    )
    story.extend(
        [
            receipt_table,
            Paragraph("Legacy concept-paper disposition", styles["H1LC"]),
            Paragraph(
                (
                    "Three older papers are preserved as historical speculative "
                    "concepts and blocked from upload. Their BioGeometry, scalar-field, "
                    "bioresonance, cooling-savings, zero-point, weather-control, and "
                    "wormhole-adjacent claims are not supported by the current "
                    "source-native benchmark evidence."
                ),
                styles["BodyLC"],
            ),
            Paragraph(
                f"Whitepaper payload SHA-256: {payload['whitepaper_payload_sha256']}",
                styles["SmallLC"],
            ),
        ]
    )
    document.build(story, onFirstPage=footer, onLaterPages=footer)


def render_upload_readme(payload: dict[str, Any]) -> str:
    lines = [
        "# Whitepaper Governance",
        "",
        f"- Status: `{payload['status']}`",
        "- External release authorized: `false`",
        f"- Current PDF: `{UPLOAD_PDF.name}`",
        f"- Payload SHA-256: `{payload['whitepaper_payload_sha256']}`",
        "",
        "The only current public-safe paper in this folder is the source-native benchmark technical note. It still requires recipient-specific claim review before external release.",
        "",
        "## Archived And Blocked",
        "",
    ]
    for item in payload["archived_legacy_whitepapers"]:
        lines.append(
            f"- `{item['filename']}` - `{item['status']}` - {item['reason']} "
            f"SHA-256 `{item['sha256']}`"
        )
    lines.extend(["", f"> {payload['boundary']}"])
    return "\n".join(lines)


def write_outputs(payload: dict[str, Any]) -> None:
    OUTPUT_MD.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_MANIFEST.parent.mkdir(parents=True, exist_ok=True)
    UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
    OUTPUT_MD.write_text(render_markdown(payload) + "\n", encoding="utf-8")
    build_pdf(payload, OUTPUT_PDF)
    shutil.copyfile(OUTPUT_PDF, UPLOAD_PDF)
    UPLOAD_README.write_text(
        render_upload_readme(payload) + "\n", encoding="utf-8"
    )

    manifest = {
        **payload,
        "generated_artifacts": [
            file_receipt(OUTPUT_MD),
            file_receipt(OUTPUT_PDF),
            file_receipt(UPLOAD_PDF),
            file_receipt(UPLOAD_README),
        ],
    }
    manifest["manifest_sha256"] = stable_hash(manifest)
    OUTPUT_MANIFEST.write_text(
        json.dumps(manifest, indent=2, ensure_ascii=True) + "\n",
        encoding="utf-8",
    )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--as-of-utc")
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    at = (
        datetime.fromisoformat(args.as_of_utc.replace("Z", "+00:00"))
        if args.as_of_utc
        else now_utc()
    )
    payload = build_payload(at)
    if not args.check:
        write_outputs(payload)
    print(
        json.dumps(
            {
                "schema": payload["schema"],
                "status": payload["status"],
                "promotion_gate_pass_count": payload["current_snapshot"][
                    "promotion_gate_pass_count"
                ],
                "external_release_authorized": payload[
                    "external_release_authorized"
                ],
                "payload_sha256": payload["whitepaper_payload_sha256"],
                "output_pdf": str(OUTPUT_PDF),
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
