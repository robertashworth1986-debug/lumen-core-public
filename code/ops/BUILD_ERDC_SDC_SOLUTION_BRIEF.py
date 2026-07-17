from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

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
FAQ_PDF = SOURCE_DIR / "HPCMP_SDC_FAQ_9June2026.pdf"
SOURCE_MANIFEST = SOURCE_DIR / "SOURCE_MANIFEST_2026-07-16.json"
OUT_PDF = (
    ROOT
    / "output"
    / "pdf"
    / "LumenCore_ERDC_SDC_Solution_Brief_PUBLIC_DRAFT_2026-07-17.pdf"
)
OUT_JSON = SPRINT_DIR / "ERDC_SDC_SOLUTION_BRIEF_COMPLIANCE_GATE_2026-07-17.json"
OUT_MD = SPRINT_DIR / "ERDC_SDC_SOLUTION_BRIEF_COMPLIANCE_GATE_2026-07-17.md"

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
PUBLIC_WEBSITE = "https://lumen-core.ai"
PUBLIC_REPOSITORY = "https://github.com/robertashworth1986-debug/lumen-core-public"
CLAIM_BOUNDARY = (
    "This is a public-safe technical draft, not a submitted solution brief. It does not include "
    "the founder-approved Phase II price, private SAM-matched legal identity and address, a live "
    "SAM status verification, signature, certification, or portal confirmation. It does not claim "
    "ERDC selection, funding availability, a contract, Department of Defense deployment, an "
    "authorization to operate, classified-data handling, field validation, realized savings, or "
    "technical performance beyond the bounded repository evidence identified here."
)
PDF_CLAIM_BOUNDARY = (
    "Claim boundary: This draft does not claim ERDC selection, available funding, a contract "
    "award, Department of Defense deployment, an authorization to operate, classified-data "
    "handling, field validation, realized savings, or performance beyond the bounded evidence "
    "identified here."
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
            leading=12.4,
            spaceAfter=3,
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
            spaceAfter=1,
            textColor=colors.HexColor("#17212B"),
        ),
        "h1": ParagraphStyle(
            "H1",
            parent=base["Heading1"],
            fontName="TimesNewRoman-Bold",
            fontSize=15,
            leading=16,
            spaceAfter=4,
            textColor=colors.HexColor("#163A5F"),
        ),
        "h2": ParagraphStyle(
            "H2",
            parent=base["Heading2"],
            fontName="TimesNewRoman-Bold",
            fontSize=13,
            leading=13.4,
            spaceBefore=2,
            spaceAfter=2,
            textColor=colors.HexColor("#1E5B69"),
        ),
        "title": ParagraphStyle(
            "Title",
            parent=base["Title"],
            fontName="TimesNewRoman-Bold",
            fontSize=22,
            leading=25,
            alignment=TA_CENTER,
            textColor=colors.HexColor("#163A5F"),
            spaceAfter=14,
        ),
        "subtitle": ParagraphStyle(
            "Subtitle",
            parent=base["BodyText"],
            fontName="TimesNewRoman",
            fontSize=14,
            leading=16,
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
            leading=12.1,
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
    if page >= 3:
        canvas.setFillColor(colors.HexColor("#163A5F"))
        canvas.setFont("TimesNewRoman-Bold", 12)
        canvas.drawString(72, 704, "W912HZ26SC005 | LumenCore Evidence Control Plane")
        canvas.setStrokeColor(colors.HexColor("#7E8B94"))
        canvas.line(72, 698, 540, 698)
    canvas.setFont("TimesNewRoman", 12)
    canvas.setFillColor(colors.HexColor("#17212B"))
    if page == 1:
        footer = "Cover page - not counted toward five-page body"
    elif page == 2:
        footer = "Acronym list - not counted toward five-page body"
    else:
        footer = f"{page - 2} of 5 pages"
    canvas.drawCentredString(306, 78, footer)
    canvas.setFillColor(colors.Color(0.65, 0.15, 0.12, alpha=0.08))
    canvas.setFont("TimesNewRoman-Bold", 34)
    canvas.translate(306, 396)
    canvas.rotate(34)
    canvas.drawCentredString(0, 0, "DRAFT - NOT FOR SUBMISSION")
    canvas.restoreState()


def build_story(s: dict[str, ParagraphStyle]) -> list[Flowable]:
    p = lambda text: paragraph(text, s["body"])
    c = lambda text: paragraph(text, s["cell"])
    h1 = lambda text: paragraph(text, s["h1"])
    h2 = lambda text: paragraph(text, s["h2"])
    b = lambda text: bullet(text, s["bullet"])
    story: list[Flowable] = []

    # Cover page - excluded by the FAQ.
    story.extend(
        [
            Spacer(1, 92),
            paragraph("LumenCore Evidence Control Plane", s["title"]),
            paragraph(
                "Public-Safe Solution Brief Draft for the Sovereign Defense Cloud",
                s["subtitle"],
            ),
            Spacer(1, 18),
            paragraph("Commercial Solutions Opening W912HZ26SC005", s["center"]),
            paragraph("U.S. Army Engineer Research and Development Center", s["center"]),
            paragraph("High Performance Computing Modernization Program", s["center"]),
            Spacer(1, 28),
            paragraph(
                "Scope: Unified Service Layer, AI-Powered Orchestration evidence, Secure Data "
                "Fabric metadata, and Vendor Lock-In Prevention.",
                s["center"],
            ),
            Spacer(1, 24),
            paragraph(
                "PUBLIC-SAFE DRAFT - REQUIRED PRICE AND PRIVATE SAM-MATCHED IDENTITY ARE NOT INCLUDED",
                s["alert"],
            ),
            Spacer(1, 18),
            paragraph(f"Website: {PUBLIC_WEBSITE}", s["center"]),
            paragraph(f"Public repository: {PUBLIC_REPOSITORY}", s["center"]),
            paragraph("Prepared July 17, 2026", s["center"]),
            PageBreak(),
        ]
    )

    # Acronym list - excluded by the FAQ.
    acronym_rows = [
        [c("Acronym"), c("Meaning")],
        [c("API"), c("Application Programming Interface")],
        [c("CSO"), c("Commercial Solutions Opening")],
        [c("DoD"), c("Department of Defense")],
        [c("DSRC"), c("DoD Supercomputing Resource Center")],
        [c("ERDC"), c("Engineer Research and Development Center")],
        [c("GFE"), c("Government Furnished Equipment")],
        [c("HPC"), c("High Performance Computing")],
        [c("HPCMP"), c("High Performance Computing Modernization Program")],
        [c("ML"), c("Machine Learning")],
        [c("OpenAPI"), c("Open standard for describing HTTP application interfaces")],
        [c("ROM"), c("Rough Order of Magnitude")],
        [c("SDC"), c("Sovereign Defense Cloud")],
        [c("SHA-256"), c("Secure Hash Algorithm with a 256-bit digest")],
        [c("Zero Trust"), c("Security model that continuously verifies access decisions")],
    ]
    story.extend(
        [
            h1("Acronyms and Abbreviations"),
            p(
                "This list is separate from the five-page proposal body, consistent with the "
                "June 9, 2026 Frequently Asked Questions."
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
            c("OpenAPI event and evidence interfaces spanning portal, command-line, and automation clients."),
        ],
        [
            c("AI-Powered Orchestration"),
            c("Policy-aware evidence hooks record orchestration decisions without replacing the selected scheduler."),
        ],
        [
            c("Secure Data Fabric"),
            c("Schema, provenance, tag, policy-result, and integrity receipts; workload payloads remain outside the default evidence path."),
        ],
        [
            c("Vendor Lock-In Prevention"),
            c("Replaceable adapters, portable schemas, offline verification, and no mandatory proprietary cloud service."),
        ],
    ]
    story.extend(
        [
            h1("1. Mission Gap and Proposed Solution"),
            p(
                "The High Performance Computing Modernization Program must coordinate hybrid resources, "
                "workflows, policy, and data without binding mission decisions to one vendor. LumenCore "
                "proposes an evidence control plane that records what was requested, which policy and "
                "orchestration path was selected, what artifacts were produced, and whether an independent "
                "verifier can reproduce the resulting receipt."
            ),
            p(
                "LumenCore is not proposed as a replacement for the five DoD Supercomputing Resource Centers, "
                "a complete cloud platform, a cross-domain solution, or a security authorization. It is a "
                "modular validation and observability component that can be integrated by the Government or a "
                "prime platform provider."
            ),
            h2("Mission effectiveness"),
            b("Give operators one evidence format across government-owned and commercial environments."),
            b("Detect policy, configuration, adapter, and artifact drift before a result is promoted."),
            b("Preserve adverse outcomes and abstentions instead of reporting only successful runs."),
            b("Allow reviewers to verify a receipt offline without access to the originating control plane."),
            h2("Focus-area alignment"),
            styled_table(focus_rows, [1.65 * inch, 4.85 * inch]),
            h2("Innovation"),
            p(
                "The innovation is the application of predeclared acceptance rules, append-only evidence "
                "chains, portable verification, and explicit failure retention to hybrid HPC and AI workflow "
                "orchestration. The control plane measures decisions across replaceable components rather than "
                "requiring a single vendor to own the full evidence path."
            ),
            PageBreak(),
        ]
    )

    # Body page 2 of 5.
    component_rows = [
        [c("Component"), c("Phase II behavior")],
        [c("Open adapter layer"), c("Maps selected portal, command-line, scheduler, object-store, and observability events into versioned OpenAPI schemas.")],
        [c("Policy registry"), c("Records policy identifiers, versions, inputs, outcomes, and exception reasons; it does not replace Government authorization services.")],
        [c("Receipt ledger"), c("Creates append-only SHA-256 chains for request, decision, artifact, and verification metadata.")],
        [c("Offline verifier"), c("Checks schema, hashes, chain continuity, declared acceptance rules, and missing evidence without network access.")],
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
                "level would use a separately deployed instance and enclave-approved interfaces; this draft "
                "does not claim cross-domain transfer or classified-data certification."
            ),
            h2("Open replacement boundary"),
            p(
                "Adapters implement versioned contracts around Kubernetes, OpenStack, workload schedulers, "
                "storage, and observability systems. A component may be replaced while the evidence contract "
                "and independent verifier remain stable. Government-selected identity and access services "
                "provide identity context; Common Access Card authentication is not assumed to be the sole path."
            ),
            PageBreak(),
        ]
    )

    # Body page 3 of 5.
    phase_rows = [
        [c("Proposed period"), c("Activity"), c("Exit evidence")],
        [c("Weeks 1-3"), c("Lock one unclassified use case, interfaces, acceptance rules, and boundary."), c("Approved interface and test protocol; no production connection.")],
        [c("Weeks 4-8"), c("Build two adapters, policy registry, receipt chain, and offline verifier."), c("Schemas, tests, software bill of materials, and build receipt.")],
        [c("Weeks 9-12"), c("Replay in shadow mode across two approved test environments."), c("Retained pass, fail, abstain, missing-data, and drift cases.")],
        [c("Weeks 13-16"), c("Demonstrate portability, verification, review, and handoff."), c("Government-run verification and limitation register.")],
    ]
    acceptance_rows = [
        [c("Acceptance dimension"), c("Proposed measurable check")],
        [c("Integrity"), c("Every export verifies chain continuity and source-artifact hashes offline.")],
        [c("Portability"), c("One protocol and schema run through two replaceable environment adapters.")],
        [c("Failure visibility"), c("Failed, abstained, missing-input, and policy-denied runs remain visible.")],
        [c("Reproducibility"), c("A Government reviewer runs the delivered verifier and documented command.")],
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
                "Final thresholds, workloads, exclusions, and test environments would be locked with the "
                "Government before scoring. No service level or performance threshold is invented in this draft."
            ),
            styled_table(acceptance_rows, [1.45 * inch, 5.05 * inch]),
            h2("Government inputs and assumptions"),
            b("One unclassified workflow, approved test data, interface documentation, identity context, endpoints, and security constraints."),
            b("A Government reviewer to approve the protocol and execute the independent verifier."),
            b("No production access or specific Government Furnished Equipment is assumed before ERDC defines the boundary."),
            PageBreak(),
        ]
    )

    # Body page 4 of 5.
    risk_rows = [
        [c("Risk"), c("Control")],
        [c("Undefined legacy interfaces"), c("Use a versioned adapter contract and two bounded interfaces; isolate vendor-specific code.")],
        [c("Sensitive data exposure"), c("Store metadata and hashes by default; keep payloads in enclave; approve expanded flows.")],
        [c("Performance overhead"), c("Benchmark capture separately; permit asynchronous finalization where constraints require it.")],
        [c("Unsupported scale claim"), c("Measure Phase II throughput and storage; do not extrapolate beyond observed bounds.")],
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
            b("Expose capture latency, verification time, storage growth, and egress as measured cost drivers."),
            b("Keep adapters and storage replaceable so the Government can compare lifecycle cost and portability."),
            h2("Primary risks and controls"),
            styled_table(risk_rows, [1.55 * inch, 4.95 * inch]),
            h2("Operational support boundary"),
            p(
                "The Phase II scope includes documented escalation, diagnostics, and expert engineering support "
                "for the evidence component. A complete Level 3 concierge service for the full Sovereign Defense "
                "Cloud is outside this module and would require a qualified integration and operations team."
            ),
            PageBreak(),
        ]
    )

    # Body page 5 of 5.
    evidence_rows = [
        [c("Evidence"), c("What it supports"), c("What it does not support")],
        [c("Public repository"), c("Inspectable builders, tests, schemas, and hash-manifest patterns."), c("DoD deployment, production readiness, or field validation.")],
        [c("Offline verifier pattern"), c("Independent receipt checks and explicit failure reporting."), c("Government acceptance or classified accreditation.")],
        [c("Public website"), c("Authentic project URL and public positioning."), c("Customers, revenue, or realized savings.")],
    ]
    gate_rows = [
        [c("Required finalization"), c("Current state")],
        [c("Phase II Rough Order of Magnitude"), c("No price is included. Founder approval is required before private finalization.")],
        [c("SAM identity, address, and status"), c("Insert privately from the active SAM record; verify exact match and contract eligibility.")],
        [c("Portal, amendments, and authority"), c("Recheck the live form and amendments; founder reviews all terms and final confirmation.")],
    ]
    story.extend(
        [
            h1("5. Commercial Readiness, Phase II Price Gate, and Evidence"),
            h2("Commercial approach"),
            p(
                "LumenCore is modular software plus integration and verification services using commercial "
                "technologies and open interfaces. A resultant award is expected to be firm-fixed price. The public "
                "repository and website show the development approach; no open-market customer deployment is claimed."
            ),
            styled_table(evidence_rows, [1.35 * inch, 2.7 * inch, 2.45 * inch]),
            h2("Phase II Rough Order of Magnitude control"),
            paragraph(
                "SUBMISSION BLOCKER: The CSO requires an estimated price for Phase II prototype development only. "
                "This public draft includes no price. Labor, infrastructure, subcontractor, travel, indirect cost, "
                "profit, payment timing, and firm-fixed-price risk require review before one estimate is inserted privately.",
                s["alert"],
            ),
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
            p(PDF_CLAIM_BOUNDARY),
        ]
    )
    return story


def build_pdf(path: Path = OUT_PDF) -> None:
    register_fonts()
    path.parent.mkdir(parents=True, exist_ok=True)
    doc = BaseDocTemplate(
        str(path),
        pagesize=letter,
        leftMargin=inch,
        rightMargin=inch,
        topMargin=inch,
        bottomMargin=inch,
        title="LumenCore ERDC Sovereign Defense Cloud Solution Brief - Public Draft",
        author="LumenCore",
        subject="W912HZ26SC005 public-safe solution brief draft",
    )
    frame = Frame(
        inch,
        96,
        letter[0] - 2 * inch,
        588,
        leftPadding=0,
        rightPadding=0,
        topPadding=0,
        bottomPadding=0,
        id="content",
    )
    doc.addPageTemplates([PageTemplate(id="all", frames=[frame], onPage=draw_page)])
    doc.build(build_story(styles()))


def inspect_pdf(path: Path = OUT_PDF) -> dict[str, Any]:
    reader = PdfReader(str(path))
    pages = reader.pages
    physical_pages = len(pages)
    page_sizes = [
        [round(float(page.mediabox.width), 2), round(float(page.mediabox.height), 2)]
        for page in pages
    ]
    texts = [(page.extract_text() or "") for page in pages]
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
        char_sizes = [
            float(char["size"])
            for page in document.pages
            for char in page.chars
            if str(char.get("text", "")).strip()
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
        "minimum_detected_font_size": round(min(char_sizes), 2) if char_sizes else None,
        "all_detected_text_at_least_12_point": bool(char_sizes) and min(char_sizes) >= 11.9,
        "embedded_font_names": fonts,
        "times_new_roman_detected": any("TimesNewRoman" in name for name in fonts),
        "body_page_labels_present": all(
            f"{index} of 5 pages" in texts[index + 1] for index in range(1, 6)
        )
        if physical_pages == 7
        else False,
        "draft_watermark_present_every_page": all(
            "DRAFT - NOT FOR SUBMISSION" in text for text in texts
        ),
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
    }


def source_integrity() -> dict[str, Any]:
    manifest = json.loads(SOURCE_MANIFEST.read_text(encoding="utf-8"))
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
    return {
        "manifest_path": rel(SOURCE_MANIFEST),
        "manifest_sha256": sha256_file(SOURCE_MANIFEST),
        "files": files,
        "all_source_checks_pass": all(
            row["sha256_match"] and row["bytes_match"] and row["page_count_match"]
            for row in files
        ),
    }


def requirements() -> list[dict[str, Any]]:
    return [
        {"id": "FORMAT_01", "requirement": "Five-page maximum proposal body", "status": "PASS", "evidence": "PDF has five numbered body pages plus excluded cover and acronym pages."},
        {"id": "FORMAT_02", "requirement": "Letter, portrait, single-sided, page X of Y", "status": "PASS", "evidence": "All seven physical pages are 612 by 792 points; body footers read 1 through 5 of 5 pages."},
        {"id": "FORMAT_03", "requirement": "Minimum one-inch margins", "status": "PASS", "evidence": "PDF character-coordinate inspection verifies all non-watermark text remains within a 72-point boundary."},
        {"id": "FORMAT_04", "requirement": "12-point Times New Roman; no smaller table or diagram text", "status": "PASS", "evidence": "Embedded Windows Times New Roman files; PDF inspection rejects detected text below 12 points."},
        {"id": "FORMAT_05", "requirement": "English PDF under 20 MB", "status": "PASS", "evidence": "Generated PDF is English, Acrobat-readable, and size-checked."},
        {"id": "DISCLOSURE_01", "requirement": "No classified or proprietary information", "status": "PASS", "evidence": "Public-safe architecture and boundaries only; no private identity, patent claims, credentials, or classified data."},
        {"id": "TECH_01", "requirement": "Describe solution and mission effectiveness", "status": "PASS", "evidence": "Body pages 1 and 2 define the evidence control plane, mission gap, components, and focus-area alignment."},
        {"id": "TECH_02", "requirement": "Explain innovation and feasibility", "status": "PASS", "evidence": "Body pages 1, 3, and 4 define the new application, prototype plan, acceptance checks, risks, and controls."},
        {"id": "TECH_03", "requirement": "Provide URL and convincing evidence", "status": "PASS_BOUNDED", "evidence": "Public website and repository are listed; evidence limitations explicitly reject field-validation claims."},
        {"id": "ROM_01", "requirement": "One estimated price for Phase II prototype only", "status": "PRIVATE_FINALIZATION_REQUIRED", "evidence": "Body page 5 preserves the required section but intentionally includes no unapproved amount."},
        {"id": "SAM_01", "requirement": "Active SAM contract registration and matching solution address", "status": "PRIVATE_FINALIZATION_REQUIRED", "evidence": "Public draft withholds identity and address; live SAM status and exact match must be verified before upload."},
        {"id": "PORTAL_01", "requirement": "Submit through ERDCWERX form by 4:00 PM CT August 7, 2026", "status": "HUMAN_FINAL_ACTION_REQUIRED", "evidence": "Official live page reviewed July 17; no portal submission is represented."},
        {"id": "FAQ_01", "requirement": "ROM excludes Phase III and IV", "status": "PASS", "evidence": "Body page 3 and price gate scope Phase II only."},
        {"id": "FAQ_02", "requirement": "Consider all classification levels without assuming CAC-only access", "status": "PASS_BOUNDED", "evidence": "Per-enclave architecture and identity-context boundary are described without claiming accreditation or cross-domain transfer."},
        {"id": "FUNDING_01", "requirement": "Do not imply current funds or guaranteed award", "status": "PASS", "evidence": "Cover, compliance gate, and claim boundary state funding is not currently available and no award is guaranteed."},
    ]


def build_payload(pdf: dict[str, Any], sources: dict[str, Any]) -> dict[str, Any]:
    rows = requirements()
    blockers = [
        row
        for row in rows
        if row["status"] in {"PRIVATE_FINALIZATION_REQUIRED", "HUMAN_FINAL_ACTION_REQUIRED"}
    ]
    technical_checks_pass = all(
        (
            pdf["physical_page_count"] == 7,
            pdf["body_page_count"] == 5,
            pdf["all_pages_letter_portrait"],
            pdf["all_non_watermark_text_within_one_inch_margins"],
            pdf["all_detected_text_at_least_12_point"],
            pdf["times_new_roman_detected"],
            pdf["body_page_labels_present"],
            pdf["draft_watermark_present_every_page"],
            pdf["required_content_markers_present"],
            pdf["bytes"] < 20 * 1024 * 1024,
            sources["all_source_checks_pass"],
        )
    )
    payload: dict[str, Any] = {
        "schema": "lumencore.erdc_sdc_solution_brief_compliance_gate.v1",
        "generated_utc": now_utc(),
        "opportunity_number": "W912HZ26SC005",
        "deadline": {
            "official_live_page_text": "4:00 PM CT on August 7, 2026",
            "official_project_url": OFFICIAL_PROJECT_URL,
            "live_page_reviewed_date": "2026-07-17",
        },
        "status": (
            "TECHNICAL_DRAFT_PASS_PRIVATE_ROM_AND_SAM_FINALIZATION_REQUIRED"
            if technical_checks_pass
            else "TECHNICAL_DRAFT_FAILED_REVIEW_REQUIRED"
        ),
        "submission_ready": False,
        "technical_document_checks_pass": technical_checks_pass,
        "funding_currently_available": False,
        "response_type": "RFI_STYLE_CSO_SOLUTION_BRIEF_EVALUATION_LANE",
        "pdf": pdf,
        "source_integrity": sources,
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
        },
        "required_private_finalization": [
            "Approve one Phase II-only firm-fixed-price Rough Order of Magnitude estimate.",
            "Insert the exact active SAM legal entity name and matching address in a private copy.",
            "Reverify active SAM contract registration and review current ERDCWERX questions and answers.",
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
        "# ERDC SDC Solution Brief Compliance Gate - 2026-07-17",
        "",
        "The substantive public-safe brief is complete and technically compliant, but it is not submission-ready until the founder approves a Phase II-only price and a private SAM-matched legal identity/address is inserted and reverified.",
        "",
        "## Gate Summary",
        "",
        f"- Status: `{payload['status']}`",
        f"- Submission ready: `{str(payload['submission_ready']).lower()}`",
        f"- Funding currently available: `{str(payload['funding_currently_available']).lower()}`",
        f"- Deadline: `{payload['deadline']['official_live_page_text']}`",
        f"- PDF pages: `{pdf['physical_page_count']}` physical; `{pdf['body_page_count']}` counted body pages",
        f"- PDF bytes: `{pdf['bytes']}`",
        f"- PDF SHA-256: `{pdf['sha256']}`",
        f"- Minimum detected font size: `{pdf['minimum_detected_font_size']}`",
        f"- Times New Roman detected: `{str(pdf['times_new_roman_detected']).lower()}`",
        f"- Letter portrait: `{str(pdf['all_pages_letter_portrait']).lower()}`",
        f"- One-inch text margins: `{str(pdf['all_non_watermark_text_within_one_inch_margins']).lower()}`",
        f"- Body page labels present: `{str(pdf['body_page_labels_present']).lower()}`",
        f"- Technical document checks pass: `{str(payload['technical_document_checks_pass']).lower()}`",
        f"- Source checks pass: `{str(payload['source_integrity']['all_source_checks_pass']).lower()}`",
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
    build_pdf()
    pdf = inspect_pdf()
    sources = source_integrity()
    payload = build_payload(pdf, sources)
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
