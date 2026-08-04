from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from xml.sax.saxutils import escape

import pdfplumber
from pypdf import PdfReader
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import (
    BaseDocTemplate,
    Flowable,
    Frame,
    PageBreak,
    PageTemplate,
    Paragraph,
    Spacer,
    Table,
    TableStyle,
)


ROOT = Path(__file__).resolve().parents[2]
SPRINT_DIR = ROOT / "grant_submissions" / "funding_sprint_20260709"
SOURCE_DIR = SPRINT_DIR / "source_attachments" / "W912HZ26SC005"
CSO_PDF = SOURCE_DIR / "CSO_HPCMP_SDC_30April2026_FINAL.pdf"
FAQ_PDF = SOURCE_DIR / "HPCMP_SDC_FAQ_20Jul2026.pdf"
SOURCE_MANIFEST = SOURCE_DIR / "SOURCE_MANIFEST_2026-07-29.json"
SOURCE_CUSTODY = SOURCE_DIR / "SOURCE_CUSTODY_2026-07-29.json"
SEMANTIC_REVIEW_LOCK = (
    SPRINT_DIR / "ERDC_SDC_INTERNAL_SEMANTIC_REVIEW_LOCK_2026-08-02.json"
)
EVIDENCE_ABLATION = (
    ROOT / "out" / "ops" / "erdc_sdc_evidence_ablation_latest.json"
)
OUT_PDF = (
    ROOT
    / "output"
    / "pdf"
    / "LumenCore_ERDC_SDC_Solution_Brief_PUBLIC_DRAFT_2026-07-29.pdf"
)
OUT_JSON = SPRINT_DIR / "ERDC_SDC_SOLUTION_BRIEF_COMPLIANCE_GATE_2026-07-29.json"
OUT_MD = SPRINT_DIR / "ERDC_SDC_SOLUTION_BRIEF_COMPLIANCE_GATE_2026-07-29.md"

FONT_DIR = Path("C:/Windows/Fonts")
FONT_FILES = {
    "TimesNewRoman": FONT_DIR / "times.ttf",
    "TimesNewRoman-Bold": FONT_DIR / "timesbd.ttf",
    "TimesNewRoman-Italic": FONT_DIR / "timesi.ttf",
    "TimesNewRoman-BoldItalic": FONT_DIR / "timesbi.ttf",
}
OFFICIAL_PROJECT_URL = (
    "https://www.erdcwerx.org/sovereign-defense-cloud-for-high-performance-computing/"
)
OFFICIAL_SUBMISSION_URL = (
    "https://submit.erdcwerx.org/submit/"
    "c94793e9-3b46-4f34-9d34-e6b07755af61/"
    "sovereign-defense-cloud-for-high-performance-computing-cso"
)
PUBLIC_WEBSITE = "https://lumen-core.ai"
PUBLIC_REPOSITORY = "https://github.com/robertashworth1986-debug/lumen-core-public"
ACRONYM_DEFINITIONS = (
    ("AI", "Artificial Intelligence"),
    ("API", "Application Programming Interface"),
    ("CAC", "Common Access Card"),
    ("CLI", "Command-Line Interface"),
    ("CPU", "Central Processing Unit"),
    ("CSO", "Commercial Solutions Opening"),
    ("DoD", "Department of Defense"),
    ("DSRC", "DoD Supercomputing Resource Center"),
    ("ERDC", "Engineer Research and Development Center"),
    ("GFE", "Government Furnished Equipment"),
    ("HPC", "High Performance Computing"),
    ("HPCMP", "High Performance Computing Modernization Program"),
    ("HTTP", "Hypertext Transfer Protocol"),
    ("JSON", "JavaScript Object Notation"),
    ("ML", "Machine Learning"),
    ("MOSA", "Modular Open Systems Approach"),
    ("OpenAPI", "Open standard for describing HTTP application interfaces"),
    ("ROM", "Rough Order of Magnitude"),
    ("SAM", "System for Award Management"),
    ("SDC", "Sovereign Defense Cloud"),
    ("SHA-256", "Secure Hash Algorithm with a 256-bit digest"),
    ("SLSA", "Supply-chain Levels for Software Artifacts"),
    ("Zero Trust", "Security model that continuously verifies access decisions"),
)
CLAIM_BOUNDARY = (
    "This is a public-safe technical draft, not a submitted solution brief. It does not include "
    "the founder-approved Phase II price, private SAM-matched legal identity and address, a live "
    "SAM status verification, signature, certification, or portal confirmation. It does not claim "
    "ERDC selection, funding availability, a contract, Department of Defense deployment, an "
    "authorization to operate, classified-data handling, field validation, customers, revenue, "
    "or realized savings, or technical performance beyond the bounded repository evidence identified here."
)
PDF_CLAIM_BOUNDARY = (
    "Claim boundary: No ERDC award, authorization, classified handling, field validation, "
    "customers, revenue, or realized savings; no performance beyond this bounded evidence is claimed."
)


def now_utc() -> str:
    return datetime.now(timezone.utc).isoformat()


def rel(path: Path) -> str:
    return path.relative_to(ROOT).as_posix()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def stable_hash(payload: Any) -> str:
    return hashlib.sha256(
        json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()


def evidence_ablation_receipt() -> dict[str, Any]:
    payload = json.loads(EVIDENCE_ABLATION.read_text(encoding="utf-8"))
    results = {
        row.get("profile_id"): row
        for row in payload.get("results", [])
        if isinstance(row, dict)
    }
    full = results.get("lumencore_full", {})
    attacks = full.get("control_attack_detection", {})
    baseline_sources = {
        row.get("id"): row
        for row in payload.get("baseline_sources", [])
        if isinstance(row, dict)
    }
    receipt = {
        "path": rel(EVIDENCE_ABLATION),
        "sha256": sha256_file(EVIDENCE_ABLATION),
        "schema": payload.get("schema"),
        "generated_utc": payload.get("generated_utc"),
        "status": payload.get("status"),
        "protocol_sha256": payload.get("protocol_sha256"),
        "workflow_count": payload.get("synthetic_workflows", {}).get("count"),
        "adverse_count": payload.get("synthetic_workflows", {}).get(
            "adverse_count"
        ),
        "artifact_count": payload.get("synthetic_workflows", {}).get(
            "artifact_count"
        ),
        "full_attack_detected_count": attacks.get("detected_count"),
        "full_attack_case_count": attacks.get("case_count"),
        "full_adverse_outcome_recall": full.get("adverse_outcome_recall"),
        "full_artifact_bytes_rehash_rate": full.get(
            "artifact_bytes_rehash_rate"
        ),
        "full_predeclared_gate_execution_pass": full.get(
            "predeclared_gate_execution_pass"
        ),
        "full_posthoc_promotion_change_detected": full.get(
            "posthoc_promotion_change_detected"
        ),
        "all_checks_pass": payload.get("all_checks_pass"),
        "promotion_or_performance_claim_allowed": payload.get(
            "promotion_or_performance_claim_allowed"
        ),
        "opentelemetry_version": baseline_sources.get(
            "opentelemetry_logs_1_59", {}
        ).get("version"),
        "slsa_version": baseline_sources.get(
            "slsa_build_provenance_1_2", {}
        ).get("version"),
        "claim_boundary": payload.get("claim_boundary"),
    }
    receipt["receipt_checks_pass"] = (
        receipt["schema"] == "lumencore.erdc_sdc_evidence_ablation.v2"
        and receipt["status"]
        == "SYNTHETIC_CONTROL_ABLATION_PASS_EXTERNAL_TRUST_ROOT_HPCMP_AND_INDEPENDENT_VALIDATION_REQUIRED"
        and receipt["workflow_count"] == 48
        and receipt["full_attack_detected_count"]
        == receipt["full_attack_case_count"]
        == 7
        and receipt["full_adverse_outcome_recall"] == 1.0
        and receipt["full_artifact_bytes_rehash_rate"] == 1.0
        and receipt["full_predeclared_gate_execution_pass"] is True
        and receipt["full_posthoc_promotion_change_detected"] is True
        and receipt["all_checks_pass"] is True
        and receipt["promotion_or_performance_claim_allowed"] is False
        and receipt["opentelemetry_version"] == "1.59.0"
        and receipt["slsa_version"] == "1.2"
        and isinstance(receipt["claim_boundary"], str)
        and bool(receipt["claim_boundary"].strip())
    )
    return receipt


def evidence_ablation_sentence(receipt: dict[str, Any]) -> str:
    return (
        f"{receipt['workflow_count']} deterministic synthetic workflows; full controls "
        f"detected {receipt['full_attack_detected_count']}/"
        f"{receipt['full_attack_case_count']} declared tamper cases with complete adverse-case "
        "retention and synthetic artifact-byte rehash; each ablation lost a declared control "
        "relative to a separately pinned local anchor."
    )


def register_fonts() -> None:
    for name, path in FONT_FILES.items():
        if not path.is_file():
            raise FileNotFoundError(f"Required Times New Roman font is missing: {path}")
        if name not in pdfmetrics.getRegisteredFontNames():
            pdfmetrics.registerFont(TTFont(name, str(path)))
    pdfmetrics.registerFontFamily(
        "TimesNewRoman",
        normal="TimesNewRoman",
        bold="TimesNewRoman-Bold",
        italic="TimesNewRoman-Italic",
        boldItalic="TimesNewRoman-BoldItalic",
    )


def styles() -> dict[str, ParagraphStyle]:
    base = getSampleStyleSheet()
    return {
        "body": ParagraphStyle(
            "Body",
            parent=base["BodyText"],
            fontName="TimesNewRoman",
            fontSize=12,
            leading=12,
            spaceAfter=1,
            alignment=TA_LEFT,
            textColor=colors.HexColor("#17212B"),
        ),
        "bullet": ParagraphStyle(
            "Bullet",
            parent=base["BodyText"],
            fontName="TimesNewRoman",
            fontSize=12,
            leading=12.4,
            leftIndent=13,
            firstLineIndent=-7,
            bulletFontName="TimesNewRoman",
            bulletFontSize=12,
            spaceAfter=0,
            textColor=colors.HexColor("#17212B"),
        ),
        "h1": ParagraphStyle(
            "H1",
            parent=base["Heading1"],
            fontName="TimesNewRoman-Bold",
            fontSize=12,
            leading=12,
            spaceAfter=2,
            textColor=colors.HexColor("#163A5F"),
        ),
        "h2": ParagraphStyle(
            "H2",
            parent=base["Heading2"],
            fontName="TimesNewRoman-Bold",
            fontSize=12,
            leading=12,
            spaceBefore=1,
            spaceAfter=1,
            textColor=colors.HexColor("#1E5B69"),
        ),
        "title": ParagraphStyle(
            "Title",
            parent=base["Title"],
            fontName="TimesNewRoman-Bold",
            fontSize=12,
            leading=14,
            alignment=TA_CENTER,
            textColor=colors.HexColor("#163A5F"),
            spaceAfter=14,
        ),
        "subtitle": ParagraphStyle(
            "Subtitle",
            parent=base["BodyText"],
            fontName="TimesNewRoman",
            fontSize=12,
            leading=14,
            alignment=TA_CENTER,
            textColor=colors.HexColor("#1E5B69"),
            spaceAfter=8,
        ),
        "center": ParagraphStyle(
            "Center",
            parent=base["BodyText"],
            fontName="TimesNewRoman",
            fontSize=12,
            leading=13.2,
            alignment=TA_CENTER,
            textColor=colors.HexColor("#17212B"),
        ),
        "alert": ParagraphStyle(
            "Alert",
            parent=base["BodyText"],
            fontName="TimesNewRoman-Bold",
            fontSize=12,
            leading=12.4,
            borderColor=colors.HexColor("#A63A2B"),
            borderWidth=1,
            borderPadding=5,
            backColor=colors.HexColor("#FFF4F1"),
            textColor=colors.HexColor("#7A271A"),
            spaceAfter=4,
        ),
        "cell": ParagraphStyle(
            "Cell",
            parent=base["BodyText"],
            fontName="TimesNewRoman",
            fontSize=12,
            leading=12,
            spaceAfter=0,
            alignment=TA_LEFT,
            textColor=colors.HexColor("#17212B"),
        ),
    }


def paragraph(text: str, style: ParagraphStyle) -> Paragraph:
    return Paragraph(text, style)


def bullet(text: str, style: ParagraphStyle) -> Paragraph:
    return Paragraph(text, style, bulletText="-")


def styled_table(
    rows: list[list[Any]],
    widths: list[float],
    header: bool = True,
) -> Table:
    table = Table(rows, colWidths=widths, hAlign="LEFT", repeatRows=1 if header else 0)
    commands: list[tuple[Any, ...]] = [
        ("FONTNAME", (0, 0), (-1, -1), "TimesNewRoman"),
        ("FONTSIZE", (0, 0), (-1, -1), 12),
        ("LEADING", (0, 0), (-1, -1), 13.2),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("GRID", (0, 0), (-1, -1), 0.6, colors.HexColor("#7E8B94")),
        ("LEFTPADDING", (0, 0), (-1, -1), 4),
        ("RIGHTPADDING", (0, 0), (-1, -1), 4),
        ("TOPPADDING", (0, 0), (-1, -1), 3),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
    ]
    if header:
        commands.extend(
            [
                ("FONTNAME", (0, 0), (-1, 0), "TimesNewRoman-Bold"),
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#DDE8EF")),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.HexColor("#163A5F")),
            ]
        )
    table.setStyle(TableStyle(commands))
    return table


class ArchitectureDiagram(Flowable):
    def __init__(self) -> None:
        super().__init__()
        self.width = 468
        self.height = 145

    def draw(self) -> None:
        canvas = self.canv
        stages = [
            ("Portal / CLI / API", "Open interfaces"),
            ("Adapter + Policy", "Identity context"),
            ("Receipt Ledger", "Hash + provenance"),
            ("Reviewer Export", "Verify offline"),
        ]
        box_width = 105
        gap = 16
        y = 66
        for index, (line1, line2) in enumerate(stages):
            x = index * (box_width + gap)
            canvas.setFillColor(colors.HexColor("#EAF1F5"))
            canvas.setStrokeColor(colors.HexColor("#356C7D"))
            canvas.roundRect(x, y, box_width, 48, 4, stroke=1, fill=1)
            canvas.setFillColor(colors.HexColor("#17212B"))
            canvas.setFont("TimesNewRoman-Bold", 12)
            canvas.drawCentredString(x + box_width / 2, y + 29, line1)
            canvas.setFont("TimesNewRoman", 12)
            canvas.drawCentredString(x + box_width / 2, y + 13, line2)
            if index < len(stages) - 1:
                canvas.setStrokeColor(colors.HexColor("#356C7D"))
                canvas.line(x + box_width, y + 24, x + box_width + gap - 3, y + 24)
                canvas.line(x + box_width + gap - 7, y + 28, x + box_width + gap - 3, y + 24)
                canvas.line(x + box_width + gap - 7, y + 20, x + box_width + gap - 3, y + 24)
        canvas.setFillColor(colors.HexColor("#F2F5F7"))
        canvas.setStrokeColor(colors.HexColor("#7E8B94"))
        canvas.rect(0, 12, self.width, 36, stroke=1, fill=1)
        canvas.setFillColor(colors.HexColor("#17212B"))
        canvas.setFont("TimesNewRoman", 12)
        canvas.drawCentredString(
            self.width / 2,
            26,
            "Replaceable adapters: Kubernetes | OpenStack | scheduler | object store | observability",
        )


def draw_page(canvas, doc) -> None:
    page = canvas.getPageNumber()
    canvas.saveState()
    canvas.setFont("TimesNewRoman", 12)
    canvas.setFillColor(colors.HexColor("#17212B"))
    if page == 1:
        footer = "1 of 7 pages - Cover page (excluded from five-page body)"
    elif page == 2:
        footer = "2 of 7 pages - Acronym list (excluded from five-page body)"
    else:
        footer = f"{page} of 7 pages - Body {page - 2} of 5"
    canvas.drawCentredString(306, 78, footer)
    canvas.setFillColor(colors.Color(0.65, 0.15, 0.12, alpha=0.08))
    canvas.setFont("TimesNewRoman-Bold", 34)
    canvas.translate(306, 396)
    canvas.rotate(34)
    canvas.drawCentredString(0, 0, "DRAFT - NOT FOR SUBMISSION")
    canvas.restoreState()


def draw_private_page(canvas, doc) -> None:
    page = canvas.getPageNumber()
    canvas.saveState()
    canvas.setFont("TimesNewRoman", 12)
    canvas.setFillColor(colors.HexColor("#17212B"))
    if page == 1:
        footer = "1 of 7 pages - Cover page (excluded from five-page body)"
    elif page == 2:
        footer = "2 of 7 pages - Acronym list (excluded from five-page body)"
    else:
        footer = f"{page} of 7 pages - Body {page - 2} of 5"
    canvas.drawCentredString(306, 78, footer)
    canvas.restoreState()


def build_story(
    s: dict[str, ParagraphStyle],
    evidence: dict[str, Any] | None = None,
    private_context: dict[str, Any] | None = None,
) -> list[Flowable]:
    evidence = evidence or evidence_ablation_receipt()
    private_candidate = private_context is not None
    private_context = private_context or {}
    p = lambda text: paragraph(text, s["body"])
    c = lambda text: paragraph(text, s["cell"])
    h1 = lambda text: paragraph(text, s["h1"])
    h2 = lambda text: paragraph(text, s["h2"])
    b = lambda text: bullet(text, s["bullet"])
    cover_subtitle = (
        "Private Final Candidate for the Sovereign Defense Cloud"
        if private_candidate
        else "Public-Safe Solution Brief Draft for the Sovereign Defense Cloud"
    )
    if private_candidate:
        cover_alert = (
            "PRIVATE FINAL CANDIDATE - HUMAN REVIEW REQUIRED"
            f"<br/>Offeror: {escape(str(private_context['legal_entity_name']))}"
            f"<br/>Address: {escape(str(private_context['solution_address']))}"
            f"<br/>Contact: {escape(str(private_context['proposal_contact_name']))}"
            f" | {escape(str(private_context['proposal_contact_email']))}"
            "<br/>Phase II ROM: founder-approved estimate included in the body"
        )
        delivery_boundary = escape(str(private_context["delivery_statement"]))
        rom_state = (
            "Founder-approved Phase II estimate included below; Phase III and IV are excluded."
        )
        identity_state = (
            "Private input records a current proposal contact and founder-verified active "
            "SAM all-awards legal-name and solution-address match."
        )
        rom_control_text = (
            "Phase II prototype-development-only estimated price: "
            f"{escape(str(private_context['rom_display']))}. The private gate verified arithmetic, "
            "declared cost-basis controls, Phase III/IV exclusion, and founder approval. "
            "This is not a Government price determination or award."
        )
        closing_boundary = (
            "Claim boundary: Not uploaded or submitted; no ERDC selection, funding, award, "
            "deployment, authorization to operate, classified handling, field validation, "
            "customers, revenue, savings, or performance beyond bounded evidence is claimed."
        )
    else:
        cover_alert = (
            "PUBLIC-SAFE DRAFT - REQUIRED PRICE AND PRIVATE SAM-MATCHED IDENTITY ARE NOT INCLUDED"
        )
        delivery_boundary = (
            "The founder is the proposed technical lead for the evidence module and public code. The "
            "Government or selected prime owns authorized interfaces, access, security, and integration; "
            "an evaluator role is requested but no independent evaluator is committed. Surrogate development "
            "uses contractor-furnished commodity CPU, local storage, and open software; no HPC allocation or "
            "cloud capacity is claimed. Staffing, compute, support, and transition commitments must be bound "
            "in the private Phase II price and accepted boundary before work begins. This module excludes User "
            "Experience Modernization and Level 3 concierge support; either addition requires committed domain "
            "experts and priced scope."
        )
        rom_state = "No price is included; a reviewed private estimate is required."
        identity_state = (
            "Insert privately; verify exact match, all-awards status, and proposal email."
        )
        rom_control_text = (
            "SUBMISSION BLOCKER: The CSO requires an estimated price for Phase II prototype development only. "
            "This public draft includes no price. Labor, infrastructure, support, indirect cost, profit, payment "
            "timing, and firm-fixed-price risk require review before one estimate is inserted privately."
        )
        closing_boundary = PDF_CLAIM_BOUNDARY
    story: list[Flowable] = []

    # Cover page - excluded by the FAQ.
    story.extend(
        [
            Spacer(1, 92),
            paragraph("LumenCore Evidence Control Plane", s["title"]),
            paragraph(cover_subtitle, s["subtitle"]),
            Spacer(1, 18),
            paragraph("Commercial Solutions Opening W912HZ26SC005", s["center"]),
            paragraph("U.S. Army Engineer Research and Development Center", s["center"]),
            paragraph("High Performance Computing Modernization Program", s["center"]),
            Spacer(1, 28),
            paragraph(
                "Primary scope: Unified Service Layer and Vendor Lock-In Prevention. "
                "Integration boundaries: AI-Powered Orchestration evidence and Secure Data "
                "Fabric metadata.",
                s["center"],
            ),
            Spacer(1, 24),
            paragraph(cover_alert, s["alert"]),
            Spacer(1, 18),
            paragraph(f"Website: {PUBLIC_WEBSITE}", s["center"]),
            paragraph(f"Public repository: {PUBLIC_REPOSITORY}", s["center"]),
            paragraph("Prepared July 29, 2026", s["center"]),
            PageBreak(),
        ]
    )

    # Acronym list - excluded by the FAQ.
    acronym_rows = [
        [c("Acronym"), c("Meaning")],
        *[[c(acronym), c(meaning)] for acronym, meaning in ACRONYM_DEFINITIONS],
    ]
    story.extend(
        [
            h1("Acronyms and Abbreviations"),
            p(
                "This list is separate from the five-page proposal body, consistent with the "
                "July 20, 2026 Frequently Asked Questions."
            ),
            styled_table(acronym_rows, [1.25 * inch, 5.25 * inch]),
            Spacer(1, 8),
            p(
                "All substantive pages that follow use the full term at first use where practical. "
                "Tables and diagrams are included in the five-page body count."
            ),
            PageBreak(),
        ]
    )

    # Body page 1 of 5.
    focus_rows = [
        [c("Focus area"), c("LumenCore contribution")],
        [
            c("Unified Service Layer"),
            c("Primary proposed pattern: versioned event and evidence contracts for portal, command-line, and automation clients; HTTP interfaces would be described with OpenAPI."),
        ],
        [
            c("AI-Powered Orchestration"),
            c("Integration boundary: policy-aware evidence hooks record orchestration decisions without replacing the selected scheduler."),
        ],
        [
            c("Secure Data Fabric"),
            c("Integration boundary: schema, provenance, tag, policy-result, and integrity receipts; workload payloads remain outside the default evidence path."),
        ],
        [
            c("Vendor Lock-In Prevention"),
            c("Primary: replaceable adapters, portable schemas, offline verification, and no mandatory proprietary cloud service."),
        ],
    ]
    story.extend(
        [
            h1("1. Mission Gap and Proposed Solution"),
            p(
                "The High Performance Computing Modernization Program must coordinate hybrid resources, "
                "workflows, policy, and data without binding mission decisions to one vendor. LumenCore "
                "proposes an evidence control plane that records what was requested, which policy and "
                "orchestration path was selected, what artifacts were produced, and whether the delivered "
                "offline verifier can reproduce the resulting receipt."
            ),
            p(
                "LumenCore is not proposed as a replacement for the five DoD Supercomputing Resource Centers, "
                "a complete cloud platform, a cross-domain solution, or a security authorization. It is a "
                "modular validation and observability component that can be integrated by the Government or a "
                "prime platform provider."
            ),
            h2("Mission effectiveness"),
            b("Give operators one evidence format across government-owned and commercial environments."),
            b("Designed to flag policy, configuration, adapter, and artifact drift before a result is promoted."),
            b("Preserve adverse outcomes and abstentions instead of reporting only successful runs."),
            b("Allow reviewers to verify a receipt offline without access to the originating control plane."),
            h2("Focus-area alignment"),
            styled_table(focus_rows, [1.65 * inch, 4.85 * inch]),
            h2("Innovation"),
            p(
                "OpenTelemetry Logs Data Model 1.59.0 and SLSA Build Provenance 1.2 with in-toto "
                "Statement v1 are complementary interoperability contexts, not ranked competitors. "
                "The bounded LumenCore mechanism composes locally hash-linked event integrity, a "
                "hashed predeclared gate set, adverse-outcome retention, and offline verification at "
                "the workflow decision boundary. The local experiment scores only LumenCore full-control "
                "and ablation profiles. This is a mechanism distinction, not a superiority claim."
            ),
            h2("Evaluation alignment"),
            b("Innovation and feasibility: predeclared gates, adverse-case retention, offline verification, and a sixteen-week plan with measurable exits."),
            b("Scalability and vendor lock-in prevention: partitioned receipts, open contracts, and replaceable adapters with no mandatory proprietary cloud."),
            b("Commercial readiness and cost efficiency: commercial software and bounded services with fixed-window cost denominators; no savings are claimed."),
            b("Impact and utility: fewer unverifiable promotions is the proposed mission effect; the user path is one evidence flow plus an offline reviewer packet."),
            PageBreak(),
        ]
    )

    # Body page 2 of 5.
    component_rows = [
        [c("Component"), c("Phase II behavior")],
        [c("Open adapter layer"), c("Would map selected portal, command-line, scheduler, object-store, and observability events into versioned JSON event contracts; HTTP interfaces would be described with OpenAPI.")],
        [c("Policy registry"), c("Records policy identifiers, versions, inputs, outcomes, and exception reasons; it does not replace Government authorization services.")],
        [c("Receipt ledger"), c("Builds locally hash-linked SHA-256 chains for request, decision, artifact, and verification metadata; the terminal root is supplied separately to the verifier.")],
        [c("Offline verifier"), c("Checks schema, rehashes included artifact bytes, verifies chain continuity and declared rules, and reports missing evidence without network access.")],
        [c("Reviewer export"), c("Produces bounded machine-readable and human-readable packets with limitations and failed checks retained.")],
    ]
    story.extend(
        [
            h1("2. Modular Architecture and Data Boundary"),
            ArchitectureDiagram(),
            styled_table(component_rows, [1.55 * inch, 4.95 * inch]),
            h2("Data minimization and sovereignty"),
            p(
                "The default evidence path stores control metadata, schema references, policy results, hashes, "
                "timestamps, and artifact locators. Mission data and model payloads remain in the authorized "
                "environment unless the Government defines a narrower approved data flow. Each classification "
                "level would use a separately deployed instance and enclave-approved interfaces with absolute "
                "data separation. This draft does not claim cross-domain transfer or classified-data certification."
            ),
            h2("Open replacement boundary"),
            p(
                "Proposed adapters would implement versioned contracts around Kubernetes, OpenStack, workload schedulers, "
                "storage, and observability systems using widely adopted protocols such as OpenAPI and "
                "Government-selected storage interfaces. A component or cloud may be replaced while the "
                "evidence contract, workload portability, and offline verifier remain stable. Government-selected "
                "identity and access services provide identity context; Common Access Card authentication is "
                "not assumed to be the sole path."
            ),
            PageBreak(),
        ]
    )

    # Body page 3 of 5.
    phase_rows = [
        [c("Proposed period"), c("Activity"), c("Exit evidence")],
        [c("Weeks 1-3"), c("Lock one unclassified use case, interfaces, acceptance rules, and boundary."), c("Approved interface and test protocol; no production connection.")],
        [c("Weeks 4-8"), c("Build two adapters, policy registry, receipt chain, and offline verifier."), c("Schemas, tests, software bill of materials, and build receipt.")],
        [c("Weeks 9-12"), c("Replay in advisory, human-in-the-loop shadow mode across two approved test environments."), c("Retained pass, fail, abstain, missing-data, override, and drift cases.")],
        [c("Weeks 13-16"), c("Demonstrate cloud-agnostic portability, verification, phased handoff, and rollback."), c("Government-run verification, manual override, and limitation register.")],
    ]
    acceptance_rows = [
        [c("Acceptance dimension"), c("Proposed measurable check")],
        [c("Integrity"), c("Detect all declared policy, deletion, ordering, digest, and gate mutations; any miss fails the controlled experiment.")],
        [c("Portability"), c("One protocol and schema run through two replaceable environment adapters.")],
        [c("Failure visibility"), c("Retain 100% of required fail, abstain, missing-input, policy-denied, and override cases; any omission fails.")],
        [c("Reproducibility"), c("A Government reviewer reruns the delivered verifier from a clean environment; any receipt mismatch fails.")],
        [c("Cost efficiency"), c("Against one selected baseline and fixed window, report bytes/event, capture and verify latency, storage/day, review minutes, and egress bytes.")],
    ]
    story.extend(
        [
            h1("3. Phase II Prototype Plan and Feasibility"),
            p(
                "The following sixteen-week plan is a proposal assumption for Phase II prototype development, "
                "not an ERDC-promised schedule. Phase III demonstration and Phase IV implementation costs and "
                "activities are excluded from the required Phase II-only price basis."
            ),
            styled_table(phase_rows, [1.0 * inch, 3.1 * inch, 2.4 * inch]),
            h2("Proposed acceptance protocol"),
            p(
                "The local precursor uses 48 deterministic synthetic workflows and seven tamper cases across "
                "one full-control and three ablation profiles, with a separate local anchor. OpenTelemetry 1.59.0 "
                "and SLSA 1.2/in-toto v1 are unranked context. This is not an HPCMP workload, external trust root, "
                "independent validation, or superiority evidence. Phase II would prelock the workflow, Government "
                "comparator, exclusions, window, and overhead budget. AI remains advisory with manual override."
            ),
            styled_table(acceptance_rows, [1.45 * inch, 5.05 * inch]),
            h2("Government inputs and assumptions"),
            b("One unclassified representative workflow, approved data and interfaces, identity context, endpoints, and security constraints."),
            b("One approved comparator, two test environments, fixed window, and Government-controlled trust anchor or signing path."),
            b("A Government reviewer approves the protocol and overhead budget and runs the verifier; no production access or GFE is assumed."),
            PageBreak(),
        ]
    )

    # Body page 4 of 5.
    risk_rows = [
        [c("Risk"), c("Control")],
        [c("Undefined legacy interfaces"), c("Use a versioned adapter contract and two bounded interfaces; isolate vendor-specific code.")],
        [c("Sensitive data exposure"), c("Store metadata and hashes by default; keep payloads in enclave; approve expanded flows.")],
        [c("Performance overhead"), c("Benchmark capture separately; permit asynchronous finalization where constraints require it.")],
        [c("Control or overhead failure"), c("Stop and roll back on any declared attack miss, adverse-case omission, verifier mismatch, or Government-set overhead breach.")],
        [c("Security accreditation"), c("Deliver review evidence; do not represent the prototype as authorized to operate.")],
    ]
    story.extend(
        [
            h1("4. Security, Scalability, Operations, and Risk"),
            h2("Zero Trust integration boundary"),
            p(
                "LumenCore consumes identity, device, workload, policy, and environment context supplied by "
                "Government-approved services and records the decision evidence. It does not issue credentials, "
                "replace access-control authorities, or treat one authenticator as sufficient for every user. "
                "Each receipt can bind the applicable policy version, decision result, exception, and verifier outcome."
            ),
            h2("Classification and enclave pattern"),
            p(
                "The architecture can be considered for Unclassified, Secret, Top Secret, and caveated "
                "environments through separate enclave deployments and approved interfaces. Phase II should "
                "begin unclassified. This is an architectural pattern only; no classified handling, cross-domain "
                "transfer, Special Access Program support, or Sensitive Compartmented Information accreditation is claimed."
            ),
            h2("Scalability and cost control"),
            b("Partition receipts by enclave, mission, tenant, and retention policy without changing the verifier schema."),
            b("Use content hashes and locators instead of duplicating large HPC artifacts in the evidence ledger."),
            b("Report capture and verify latency, bytes per event, storage growth per day, operator-review minutes, and egress bytes over the same fixed window as the selected baseline."),
            b("Keep adapters and storage replaceable so the Government can compare lifecycle cost and portability."),
            b("Exercise both workload portability and bounded burst behavior without coupling the design to one cloud."),
            h2("Primary risks and controls"),
            styled_table(risk_rows, [1.55 * inch, 4.95 * inch]),
            h2("Delivery, compute, and support boundary"),
            p(delivery_boundary),
            PageBreak(),
        ]
    )

    # Body page 5 of 5.
    evidence_rows = [
        [c("Evidence"), c("What it supports"), c("What it does not support")],
        [c("Repository and local draft"), c("Public patterns; the exact July 29 receipt remains local pending publication."), c("External reproducibility, deployment, production readiness, or field validation.")],
        [c("Offline verifier pattern"), c("Offline receipt checks and explicit failure reporting."), c("Independent validation, Government acceptance, or classified accreditation.")],
        [
            c("Synthetic control ablation"),
            c(evidence_ablation_sentence(evidence)),
            c("An external trust root, HPCMP performance, Government acceptance, independent validation, or superiority over the purpose-bounded standards."),
        ],
    ]
    gate_rows = [
        [c("Required finalization"), c("Current state")],
        [c("Phase II Rough Order of Magnitude"), c(rom_state)],
        [c("SAM identity and contact"), c(identity_state)],
        [c("Portal and authority"), c("Recheck Submittable, amendments, terms, and final confirmation.")],
    ]
    story.extend(
        [
            h1("5. Commercial Readiness, Phase II Price Gate, and Evidence"),
            h2("Commercial readiness and operator utility"),
            p(
                "LumenCore is modular software plus integration and verification services built from commercial "
                "technologies and open interfaces. Operator utility is one portal, command-line, or application "
                "interface evidence workflow plus an offline reviewer packet. The named profiles are unranked "
                "contexts, the SDC module is unproven, and any resultant award is expected to be firm-fixed price."
            ),
            styled_table(evidence_rows, [1.35 * inch, 2.7 * inch, 2.45 * inch]),
            h2("Phase II Rough Order of Magnitude control"),
            paragraph(rom_control_text, s["alert"]),
            h2("Final submission gates"),
            styled_table(gate_rows, [2.0 * inch, 4.5 * inch]),
            h2("Bounded next decision"),
            p(
                "If ERDC considers the module promising, the requested next step is a short technical clarification "
                "or solution pitch to lock one representative unclassified workflow, the integration boundary, "
                "Government-run acceptance checks, and the appropriate contract or agreement path."
            ),
            p(f"Official project source: {OFFICIAL_PROJECT_URL}"),
            p("Funding is not currently available; this market-research lane does not guarantee an award."),
            p(closing_boundary),
        ]
    )
    return story


def build_pdf(
    path: Path = OUT_PDF,
    evidence: dict[str, Any] | None = None,
    private_context: dict[str, Any] | None = None,
) -> None:
    evidence = evidence or evidence_ablation_receipt()
    register_fonts()
    path.parent.mkdir(parents=True, exist_ok=True)
    doc = BaseDocTemplate(
        str(path),
        pagesize=letter,
        leftMargin=inch,
        rightMargin=inch,
        topMargin=inch,
        bottomMargin=inch,
        title=(
            "LumenCore ERDC Sovereign Defense Cloud Solution Brief - Private Final Candidate"
            if private_context is not None
            else "LumenCore ERDC Sovereign Defense Cloud Solution Brief - Public Draft"
        ),
        author="LumenCore",
        subject=(
            "W912HZ26SC005 private final solution brief candidate"
            if private_context is not None
            else "W912HZ26SC005 public-safe solution brief draft"
        ),
    )
    frame = Frame(
        inch,
        90,
        letter[0] - 2 * inch,
        630,
        leftPadding=0,
        rightPadding=0,
        topPadding=0,
        bottomPadding=0,
        id="content",
    )
    doc.addPageTemplates(
        [
            PageTemplate(
                id="all",
                frames=[frame],
                onPage=draw_private_page if private_context is not None else draw_page,
            )
        ]
    )
    doc.build(build_story(styles(), evidence, private_context))


def inspect_pdf(
    path: Path = OUT_PDF,
    evidence: dict[str, Any] | None = None,
    *,
    document_mode: str = "PUBLIC_DRAFT",
) -> dict[str, Any]:
    evidence = evidence or evidence_ablation_receipt()
    reader = PdfReader(str(path))
    pages = reader.pages
    physical_pages = len(pages)
    page_sizes = [
        [round(float(page.mediabox.width), 2), round(float(page.mediabox.height), 2)]
        for page in pages
    ]
    texts = [(page.extract_text() or "") for page in pages]
    normalized_text = " ".join("\n".join(texts).split())
    normalized_page_text = [" ".join(text.split()) for text in texts]
    normalized_evidence_marker = " ".join(
        evidence_ablation_sentence(evidence).split()
    )
    with pdfplumber.open(path) as document:
        content_chars_by_page = [
            [
                char
                for char in page.chars
                if str(char.get("text", "")).strip()
                and float(char.get("size", 0)) < 30
            ]
            for page in document.pages
        ]
        content_char_sizes = [
            float(char["size"])
            for chars in content_chars_by_page
            for char in chars
        ]
        fonts = sorted(
            {
                str(char.get("fontname", ""))
                for page in document.pages
                for char in page.chars
                if str(char.get("text", "")).strip()
            }
        )
    content_bounds = [
        {
            "left": round(min(float(char["x0"]) for char in chars), 2),
            "right": round(max(float(char["x1"]) for char in chars), 2),
            "top": round(min(float(char["top"]) for char in chars), 2),
            "bottom": round(max(float(char["bottom"]) for char in chars), 2),
        }
        for chars in content_chars_by_page
    ]
    return {
        "path": rel(path),
        "exists": path.is_file(),
        "bytes": path.stat().st_size,
        "sha256": sha256_file(path),
        "semantic_sha256": stable_hash(
            {
                "page_sizes_points": page_sizes,
                "normalized_page_text": normalized_page_text,
            }
        ),
        "physical_page_count": physical_pages,
        "cover_pages": 1,
        "acronym_pages": 1,
        "body_page_count": max(physical_pages - 2, 0),
        "page_sizes_points": page_sizes,
        "all_pages_letter_portrait": all(size == [612.0, 792.0] for size in page_sizes),
        "content_bounds_points_from_top_left": content_bounds,
        "all_non_watermark_text_within_one_inch_margins": all(
            bounds["left"] >= 71.9
            and bounds["right"] <= 540.1
            and bounds["top"] >= 71.9
            and bounds["bottom"] <= 720.1
            for bounds in content_bounds
        ),
        "minimum_detected_font_size": (
            round(min(content_char_sizes), 2) if content_char_sizes else None
        ),
        "maximum_detected_content_font_size": (
            round(max(content_char_sizes), 2) if content_char_sizes else None
        ),
        "all_detected_text_at_least_12_point": (
            bool(content_char_sizes) and min(content_char_sizes) >= 11.9
        ),
        "all_detected_content_text_12_point": (
            bool(content_char_sizes)
            and min(content_char_sizes) >= 11.9
            and max(content_char_sizes) <= 12.1
        ),
        "embedded_font_names": fonts,
        "times_new_roman_detected": any("TimesNewRoman" in name for name in fonts),
        "all_physical_page_labels_present": all(
            f"{index} of 7 pages" in texts[index - 1]
            for index in range(1, 8)
        )
        if physical_pages == 7
        else False,
        "body_page_labels_present": all(
            f"Body {index} of 5" in texts[index + 1] for index in range(1, 6)
        )
        if physical_pages == 7
        else False,
        "draft_watermark_present_every_page": all(
            "DRAFT - NOT FOR SUBMISSION" in text for text in texts
        ),
        "draft_watermark_absent_every_page": all(
            "DRAFT - NOT FOR SUBMISSION" not in text for text in texts
        ),
        "private_candidate_marker_present": (
            bool(texts)
            and "PRIVATE FINAL CANDIDATE - HUMAN REVIEW REQUIRED" in texts[0]
        ),
        "document_mode": document_mode,
        "required_content_markers_present": all(
            marker in "\n".join(texts)
            for marker in (
                "W912HZ26SC005",
                "Mission Gap and Proposed Solution",
                "Modular Architecture and Data Boundary",
                "Phase II Prototype Plan and Feasibility",
                "Security, Scalability, Operations, and Risk",
                "Phase II Rough Order of Magnitude control",
                "Funding",
            )
        ),
        "required_acronym_entries_present": (
            len(texts) >= 2
            and all(
                acronym in texts[1] and meaning in texts[1]
                for acronym, meaning in ACRONYM_DEFINITIONS
            )
        ),
        "evidence_ablation_marker_present": (
            normalized_evidence_marker in normalized_text
        ),
    }


def source_integrity() -> dict[str, Any]:
    manifest = json.loads(SOURCE_MANIFEST.read_text(encoding="utf-8"))
    custody = json.loads(SOURCE_CUSTODY.read_text(encoding="utf-8"))
    files = []
    for row in manifest["files"]:
        path = ROOT / row["path"]
        actual_hash = sha256_file(path)
        actual_bytes = path.stat().st_size
        files.append(
            {
                "path": row["path"],
                "expected_sha256": row["sha256"],
                "actual_sha256": actual_hash,
                "sha256_match": actual_hash == row["sha256"],
                "expected_bytes": row["bytes"],
                "actual_bytes": actual_bytes,
                "bytes_match": actual_bytes == row["bytes"],
                "expected_pages": row["expected_pages"],
                "actual_pages": len(PdfReader(str(path)).pages),
                "page_count_match": len(PdfReader(str(path)).pages)
                == row["expected_pages"],
                "official_url": row["official_url"],
            }
        )
    custody_sources = []
    for row in custody.get("source_documents", []):
        pdf_path = ROOT / row["pdf_path"]
        text_path = ROOT / row["text_path"]
        custody_sources.append(
            {
                "pdf_path": row["pdf_path"],
                "pdf_sha256_match": sha256_file(pdf_path) == row["pdf_sha256"],
                "text_path": row["text_path"],
                "text_exists": text_path.is_file(),
                "text_sha256_match": (
                    text_path.is_file()
                    and sha256_file(text_path) == row["text_sha256"]
                ),
                "extraction": row.get("extraction"),
            }
        )
    live_snapshot = custody.get("live_page_snapshot", {})
    live_snapshot_path = ROOT / live_snapshot.get("path", "")
    custody_checks_pass = (
        custody.get("schema") == "lumencore.erdc_sdc_source_custody.v1"
        and custody.get("opportunity_number") == "W912HZ26SC005"
        and len(custody_sources) == 2
        and all(
            row["pdf_sha256_match"]
            and row["text_exists"]
            and row["text_sha256_match"]
            and row["extraction"] == "pdftotext -layout"
            for row in custody_sources
        )
        and live_snapshot_path.is_file()
        and sha256_file(live_snapshot_path) == live_snapshot.get("sha256")
        and live_snapshot.get("route") == "COMMERCIAL_SOLUTION"
        and live_snapshot.get("deadline_text") == "4:00 pm CT on August 7, 2026"
        and live_snapshot.get("question_cutoff_text") == "July 31, 2026"
    )
    return {
        "manifest_schema": manifest.get("schema"),
        "manifest_as_of_date": manifest.get("as_of_date"),
        "current_attachment_set_complete": manifest.get(
            "current_attachment_set_complete"
        ),
        "manifest_path": rel(SOURCE_MANIFEST),
        "manifest_sha256": sha256_file(SOURCE_MANIFEST),
        "source_custody_path": rel(SOURCE_CUSTODY),
        "source_custody_sha256": sha256_file(SOURCE_CUSTODY),
        "source_custody_schema": custody.get("schema"),
        "source_custody_checks_pass": custody_checks_pass,
        "custody_sources": custody_sources,
        "live_page_snapshot": live_snapshot,
        "files": files,
        "all_source_checks_pass": all(
            row["sha256_match"] and row["bytes_match"] and row["page_count_match"]
            for row in files
        )
        and manifest.get("schema") == "lumencore.erdc_sdc_source_manifest.v2"
        and manifest.get("as_of_date") == "2026-07-29"
        and manifest.get("current_attachment_set_complete") is True
        and custody_checks_pass,
    }


def requirements() -> list[dict[str, Any]]:
    return [
        {"id": "FORMAT_01", "requirement": "Five-page maximum proposal body", "status": "PASS", "evidence": "PDF has five numbered body pages plus excluded cover and acronym pages."},
        {"id": "FORMAT_02", "requirement": "Letter, portrait, single-sided, page X of Y", "status": "PASS", "evidence": "All seven physical pages are 612 by 792 points and carry physical-page X of 7 plus body-page labels where applicable."},
        {"id": "FORMAT_03", "requirement": "Minimum one-inch margins", "status": "PASS", "evidence": "PDF character-coordinate inspection verifies all non-watermark text remains within a 72-point boundary."},
        {"id": "FORMAT_04", "requirement": "12-point Times New Roman, including tables and diagrams", "status": "PASS", "evidence": "Embedded Windows Times New Roman files; PDF inspection requires all substantive text to remain 12 point."},
        {"id": "FORMAT_05", "requirement": "English PDF under 20 MB", "status": "PASS", "evidence": "Generated PDF is English, Acrobat-readable, and size-checked."},
        {"id": "DISCLOSURE_01", "requirement": "No classified or proprietary information", "status": "PASS", "evidence": "Public-safe architecture and boundaries only; no private identity, patent claims, credentials, or classified data."},
        {"id": "TECH_01", "requirement": "Describe solution and mission effectiveness", "status": "PASS", "evidence": "Body pages 1 and 2 define the evidence control plane, mission gap, components, and focus-area alignment."},
        {"id": "TECH_02", "requirement": "Explain innovation and feasibility", "status": "PASS_BOUNDED", "evidence": "Body pages 1, 3, and 4 distinguish the mechanism, define the prototype, name acceptance checks and falsifiers, and preserve the HPCMP and independent-validation boundary."},
        {"id": "TECH_03", "requirement": "Provide URL and convincing evidence", "status": "LOCAL_ONLY_EXTERNAL_REPRODUCIBILITY_REQUIRED", "evidence": "Public website and repository are listed, but the exact July 29 builder, receipt, and proposal gate remain local until a reviewed commit is published. Field validation is not claimed."},
        {"id": "BASELINE_01", "requirement": "Name current purpose-matched interoperability contexts", "status": "PASS_BOUNDED", "evidence": "Body pages 1, 3, and 5 name OpenTelemetry Logs Data Model 1.59.0 and SLSA Build Provenance 1.2 with in-toto Statement v1 as unranked interoperability contexts and reject universal ranking."},
        {"id": "ABLATION_01", "requirement": "Show the claimed control contribution through ablation", "status": "PASS_BOUNDED", "evidence": "The bound local surrogate covers 48 deterministic workflows and seven declared attacks; the full profile detects 7 of 7 relative to a separately supplied local anchor while each no-chain, no-predeclaration, or no-failure-retention profile loses a declared control. It is not an HPCMP or independent result."},
        {"id": "TRUST_01", "requirement": "Bind the protocol and receipt to a trust root outside the mutable evidence packet", "status": "EXTERNAL_TRUST_ROOT_REQUIRED", "evidence": "The local experiment supplies an anchor separately from the receipt, but it is not a Government-controlled signature, timestamp, or external trust service."},
        {"id": "METRIC_01", "requirement": "Define quantitative checks, cost denominators, and falsifiers", "status": "PASS_BOUNDED", "evidence": "Body pages 3 and 4 require complete declared-attack detection, complete adverse-case retention, clean reviewer replay, fixed-window baseline comparison, explicit cost drivers, and stop/rollback on a miss or Government-set overhead breach."},
        {"id": "EVAL_01", "requirement": "Address innovation, feasibility, scalability, vendor lock-in prevention, commercial readiness, cost efficiency, impact, and utility", "status": "PASS_BOUNDED", "evidence": "Body pages 1 through 5 map the proposed mechanism, prototype plan, scaling controls, replaceable interfaces, commercial components, fixed-window cost denominators, mission-effectiveness checks, and operator/reviewer workflow. No demonstrated HPCMP savings or return on investment is claimed."},
        {"id": "EXEC_01", "requirement": "Bind delivery roles, compute, support, and transition commitments", "status": "PRIVATE_FINALIZATION_REQUIRED", "evidence": "Body page 4 identifies the founder as proposed technical lead and bounds commodity surrogate compute; Government or prime integration, evaluator commitment, production compute, staffing, support, and transition ownership remain to be bound in the private Phase II plan and price."},
        {"id": "ROM_01", "requirement": "One estimated price for Phase II prototype only", "status": "PRIVATE_FINALIZATION_REQUIRED", "evidence": "Body page 5 preserves the required section but intentionally includes no unapproved amount."},
        {"id": "SAM_01", "requirement": "Active SAM all-awards contract registration and matching solution address", "status": "PRIVATE_FINALIZATION_REQUIRED", "evidence": "Public draft withholds identity and address; live SAM all-awards status, contract eligibility, and exact match must be verified before upload."},
        {"id": "CONTACT_01", "requirement": "Current accurate proposal contact email", "status": "PRIVATE_FINALIZATION_REQUIRED", "evidence": "Public draft intentionally omits private contact data; insert and verify in the private final copy."},
        {"id": "ACCOUNT_01", "requirement": "Working Submittable account and access to the complete live form", "status": "HUMAN_ACCOUNT_ACCESS_REQUIRED", "evidence": "The public submission landing page requires a free Submittable account or supported federated sign-in; complete form access has not been verified."},
        {"id": "PORTAL_01", "requirement": "Submit through ERDCWERX form before the safest current cutoff of 4:00 PM CT August 7, 2026", "status": "HUMAN_FINAL_ACTION_REQUIRED", "evidence": "The original CSO PDF says 1700 EST while the current live page says 4:00 PM CT; use the current live page's earlier practical cutoff. No portal submission is represented."},
        {"id": "FAQ_01", "requirement": "ROM excludes Phase III and IV", "status": "PASS", "evidence": "Body page 3 and price gate scope Phase II only."},
        {"id": "FAQ_02", "requirement": "Consider all classification levels without assuming CAC-only access", "status": "PASS_BOUNDED", "evidence": "Per-enclave architecture and identity-context boundary are described without claiming accreditation or cross-domain transfer."},
        {"id": "FAQ_03", "requirement": "MOSA and nonproprietary standards prevent vendor lock-in", "status": "PASS_BOUNDED", "evidence": "Body pages 1 and 2 define focused-module MOSA boundaries, replaceable adapters, open contracts, and portable verification."},
        {"id": "FAQ_04", "requirement": "AI remains human-in-the-loop with manual override", "status": "PASS_BOUNDED", "evidence": "Body page 3 keeps AI advisory and requires explicit parameters, manual override, and retained evidence for bounded administrative automation."},
        {"id": "FAQ_05", "requirement": "Absolute data separation and cloud-agnostic portability", "status": "PASS_BOUNDED", "evidence": "Body pages 2 and 4 define separate enclave deployment, absolute data separation, replaceable clouds, workload portability, and bounded burst behavior."},
        {"id": "FAQ_06", "requirement": "Legacy interoperability with phased low-risk migration", "status": "PASS_BOUNDED", "evidence": "Body pages 3 and 4 define shadow-mode prototype work, rollback evidence, legacy transition boundaries, and phased handoff."},
        {"id": "FAQ_07", "requirement": "Do not imply uncommitted Level 3 concierge support", "status": "PASS_BOUNDED", "evidence": "The primary scope excludes User Experience Modernization; body page 4 states that any Level 3 concierge scope requires committed domain experts and corresponding Phase II pricing."},
        {"id": "FUNDING_01", "requirement": "Do not imply current funds or guaranteed award", "status": "PASS", "evidence": "Cover, compliance gate, and claim boundary state funding is not currently available and no award is guaranteed."},
    ]


def semantic_review_lock(
    pdf: dict[str, Any],
    sources: dict[str, Any],
    evidence: dict[str, Any],
) -> dict[str, Any]:
    if not SEMANTIC_REVIEW_LOCK.is_file():
        return {
            "path": rel(SEMANTIC_REVIEW_LOCK),
            "present": False,
            "valid_for_current_artifacts": False,
            "classification": "INTERNAL_MODEL_ASSISTED_NOT_INDEPENDENT",
        }

    lock = json.loads(SEMANTIC_REVIEW_LOCK.read_text(encoding="utf-8"))
    checks = lock.get("checks", {})
    required_checks = (
        "official_cso_and_faq_crosswalk_complete",
        "all_seven_pages_visually_reviewed",
        "claims_bounded_to_evidence",
        "openapi_language_is_prospective",
        "level_3_concierge_scope_is_explicitly_excluded",
        "five_body_page_limit_confirmed",
        "private_and_human_submission_gates_preserved",
    )
    valid = (
        lock.get("schema") == "lumencore.erdc_sdc_internal_semantic_review.v1"
        and lock.get("opportunity_number") == "W912HZ26SC005"
        and lock.get("classification")
        == "INTERNAL_MODEL_ASSISTED_NOT_INDEPENDENT"
        and lock.get("reviewed_document_semantic_sha256")
        == pdf.get("semantic_sha256")
        and lock.get("reviewed_source_manifest_sha256")
        == sources.get("manifest_sha256")
        and lock.get("reviewed_source_custody_sha256")
        == sources.get("source_custody_sha256")
        and lock.get("reviewed_evidence_ablation_sha256")
        == evidence.get("sha256")
        and all(checks.get(name) is True for name in required_checks)
    )
    return {
        "path": rel(SEMANTIC_REVIEW_LOCK),
        "sha256": sha256_file(SEMANTIC_REVIEW_LOCK),
        "present": True,
        "schema": lock.get("schema"),
        "reviewed_utc": lock.get("reviewed_utc"),
        "classification": lock.get("classification"),
        "valid_for_current_artifacts": valid,
        "independent_review": False,
        "reviewed_document_semantic_sha256": lock.get(
            "reviewed_document_semantic_sha256"
        ),
    }


def build_payload(
    pdf: dict[str, Any],
    sources: dict[str, Any],
    evidence: dict[str, Any] | None = None,
) -> dict[str, Any]:
    evidence = evidence or evidence_ablation_receipt()
    rows = requirements()
    semantic_review = semantic_review_lock(pdf, sources, evidence)
    blockers = [
        row
        for row in rows
        if row["status"]
        in {
            "PRIVATE_FINALIZATION_REQUIRED",
            "HUMAN_ACCOUNT_ACCESS_REQUIRED",
            "HUMAN_FINAL_ACTION_REQUIRED",
            "LOCAL_ONLY_EXTERNAL_REPRODUCIBILITY_REQUIRED",
            "EXTERNAL_TRUST_ROOT_REQUIRED",
        }
    ]
    format_and_marker_checks_pass = all(
        (
            pdf["physical_page_count"] == 7,
            pdf["body_page_count"] == 5,
            pdf["all_pages_letter_portrait"],
            pdf["all_non_watermark_text_within_one_inch_margins"],
            pdf["all_detected_text_at_least_12_point"],
            pdf["all_detected_content_text_12_point"],
            pdf["times_new_roman_detected"],
            pdf["all_physical_page_labels_present"],
            pdf["body_page_labels_present"],
            pdf["draft_watermark_present_every_page"],
            pdf["required_content_markers_present"],
            pdf["evidence_ablation_marker_present"],
            pdf["required_acronym_entries_present"],
            pdf["bytes"] < 20 * 1024 * 1024,
            sources["all_source_checks_pass"],
            evidence["receipt_checks_pass"],
        )
    )
    payload: dict[str, Any] = {
        "schema": "lumencore.erdc_sdc_solution_brief_compliance_gate.v1",
        "generated_utc": now_utc(),
        "opportunity_number": "W912HZ26SC005",
        "deadline": {
            "controlling_cso_pdf_text": "1700 EST, 07 AUG 2026",
            "current_live_page_text": "4:00 PM CT on August 7, 2026",
            "safest_operational_cutoff": "4:00 PM CT on August 7, 2026",
            "reconciliation_rule": (
                "Preserve both source texts and complete before the current live "
                "page's earlier practical cutoff."
            ),
            "question_submission_cutoff": "July 31, 2026",
            "official_project_url": OFFICIAL_PROJECT_URL,
            "official_submission_url": OFFICIAL_SUBMISSION_URL,
            "live_page_reviewed_date": "2026-07-29",
        },
        "status": (
            "CURRENT_PUBLIC_DRAFT_INTERNAL_SEMANTIC_REVIEW_PASS_PRIVATE_FINALIZATION_REQUIRED"
            if format_and_marker_checks_pass
            and semantic_review["valid_for_current_artifacts"]
            else "CURRENT_PUBLIC_DRAFT_FORMAT_AND_MARKER_CHECKS_PASS_SEMANTIC_EVIDENCE_AND_PRIVATE_FINALIZATION_REQUIRED"
            if format_and_marker_checks_pass
            else "CURRENT_PUBLIC_DRAFT_FAILED_REVIEW_REQUIRED"
        ),
        "submission_ready": False,
        "format_and_marker_checks_pass": format_and_marker_checks_pass,
        "semantic_review_complete": semantic_review["valid_for_current_artifacts"],
        "semantic_review": semantic_review,
        "funding_currently_available": False,
        "response_type": "RFI_STYLE_CSO_SOLUTION_BRIEF_EVALUATION_LANE",
        "pdf": pdf,
        "source_integrity": sources,
        "evidence_ablation": evidence,
        "requirements": rows,
        "summary": {
            "requirement_count": len(rows),
            "pass_or_bounded_pass_count": sum(
                1 for row in rows if row["status"] in {"PASS", "PASS_BOUNDED"}
            ),
            "finalization_blocker_count": len(blockers),
            "finalization_blocker_ids": [row["id"] for row in blockers],
            "external_send_allowed_without_human": False,
            "final_portal_submit_allowed_without_human": False,
            "pricing_allowed_without_founder_approval": False,
            "legal_identity_publish_allowed": False,
            "browser_navigation_performed": False,
            "internal_red_team_only": True,
            "independent_review_complete": False,
        },
        "required_private_finalization": [
            "Approve one Phase II-only firm-fixed-price Rough Order of Magnitude estimate.",
            "Bind named Phase II delivery roles, staffing, production compute or cloud access, support, evaluator, integration, and transition ownership without inventing commitments.",
            "Insert the exact active SAM legal entity name and matching address in a private copy.",
            "Insert and verify the current proposal contact email in the private copy.",
            "Reverify active SAM all-awards contract registration and review current ERDCWERX questions and answers.",
            "Sign in to the required Submittable account and inspect the complete current form.",
            "Review the final private PDF, portal fields, representations, terms, and submission confirmation.",
        ],
        "claim_boundary": CLAIM_BOUNDARY,
        "outputs": {"pdf": rel(OUT_PDF), "json": rel(OUT_JSON), "markdown": rel(OUT_MD)},
    }
    payload["gate_sha256"] = stable_hash(payload)
    return payload


def render_markdown(payload: dict[str, Any]) -> str:
    pdf = payload["pdf"]
    summary = payload["summary"]
    lines = [
        "# ERDC SDC Solution Brief Compliance Gate - 2026-07-29",
        "",
        "The public-safe brief now binds a purpose-bounded comparator, local control ablation, proposed quantitative falsifiers, cost denominators, and honest delivery boundaries. It is not submission-ready until the Phase II price and execution commitments are approved, private SAM/contact facts are inserted and reverified, and the complete authenticated portal form is reviewed.",
        "",
        "## Gate Summary",
        "",
        f"- Status: `{payload['status']}`",
        f"- Submission ready: `{str(payload['submission_ready']).lower()}`",
        f"- Funding currently available: `{str(payload['funding_currently_available']).lower()}`",
        f"- Safest operational deadline: `{payload['deadline']['safest_operational_cutoff']}`",
        f"- Original CSO PDF deadline text: `{payload['deadline']['controlling_cso_pdf_text']}`",
        f"- Current live page deadline text: `{payload['deadline']['current_live_page_text']}`",
        f"- Question submission cutoff: `{payload['deadline']['question_submission_cutoff']}`",
        f"- PDF pages: `{pdf['physical_page_count']}` physical; `{pdf['body_page_count']}` counted body pages",
        f"- PDF bytes: `{pdf['bytes']}`",
        f"- PDF SHA-256: `{pdf['sha256']}`",
        f"- Minimum detected font size: `{pdf['minimum_detected_font_size']}`",
        f"- Times New Roman detected: `{str(pdf['times_new_roman_detected']).lower()}`",
        f"- Letter portrait: `{str(pdf['all_pages_letter_portrait']).lower()}`",
        f"- One-inch text margins: `{str(pdf['all_non_watermark_text_within_one_inch_margins']).lower()}`",
        f"- Body page labels present: `{str(pdf['body_page_labels_present']).lower()}`",
        f"- Format and marker checks pass: `{str(payload['format_and_marker_checks_pass']).lower()}`",
        f"- Semantic review complete: `{str(payload['semantic_review_complete']).lower()}`",
        f"- Semantic review classification: `{payload['semantic_review']['classification']}`",
        f"- Semantic review lock: `{payload['semantic_review']['path']}`",
        f"- Source checks pass: `{str(payload['source_integrity']['all_source_checks_pass']).lower()}`",
        f"- Evidence ablation checks pass: `{str(payload['evidence_ablation']['receipt_checks_pass']).lower()}`",
        f"- Evidence ablation SHA-256: `{payload['evidence_ablation']['sha256']}`",
        f"- Evidence protocol SHA-256: `{payload['evidence_ablation']['protocol_sha256']}`",
        f"- Synthetic workflows: `{payload['evidence_ablation']['workflow_count']}`",
        f"- Full-control attacks detected: `{payload['evidence_ablation']['full_attack_detected_count']}/{payload['evidence_ablation']['full_attack_case_count']}`",
        f"- Adverse-outcome recall: `{payload['evidence_ablation']['full_adverse_outcome_recall']}`",
        f"- Synthetic artifact byte rehash rate: `{payload['evidence_ablation']['full_artifact_bytes_rehash_rate']}`",
        f"- Finalization blockers: `{summary['finalization_blocker_count']}`",
        f"- External send without human: `{str(summary['external_send_allowed_without_human']).lower()}`",
        f"- Final portal submit without human: `{str(summary['final_portal_submit_allowed_without_human']).lower()}`",
        f"- Session-browser navigation performed: `{str(summary['browser_navigation_performed']).lower()}`",
        f"- Gate SHA-256: `{payload['gate_sha256']}`",
        "",
        "## Compliance Matrix",
        "",
        "| ID | Status | Requirement | Evidence |",
        "|---|---|---|---|",
    ]
    for row in payload["requirements"]:
        lines.append(
            f"| `{row['id']}` | `{row['status']}` | {row['requirement']} | {row['evidence']} |"
        )
    lines.extend(["", "## Required Private Finalization", ""])
    for item in payload["required_private_finalization"]:
        lines.append(f"- {item}")
    lines.extend(["", "## Source Integrity", ""])
    for row in payload["source_integrity"]["files"]:
        lines.append(
            f"- `{row['path']}`: hash=`{str(row['sha256_match']).lower()}` bytes=`{str(row['bytes_match']).lower()}` pages=`{str(row['page_count_match']).lower()}`"
        )
    lines.extend(["", "## Claim Boundary", "", payload["claim_boundary"], ""])
    return "\n".join(lines)


def main() -> None:
    evidence = evidence_ablation_receipt()
    build_pdf(evidence=evidence)
    pdf = inspect_pdf(evidence=evidence)
    sources = source_integrity()
    payload = build_payload(pdf, sources, evidence)
    OUT_JSON.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    OUT_MD.write_text(render_markdown(payload), encoding="utf-8")
    print(
        json.dumps(
            {
                "status": payload["status"],
                "submission_ready": payload["submission_ready"],
                "physical_pages": pdf["physical_page_count"],
                "body_pages": pdf["body_page_count"],
                "minimum_font_size": pdf["minimum_detected_font_size"],
                "pdf_bytes": pdf["bytes"],
                "source_checks_pass": sources["all_source_checks_pass"],
                "pdf": rel(OUT_PDF),
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
